#!/usr/bin/env python3
"""Flask UI for running the pipeline and viewing results."""

from pathlib import Path
import sqlite3
import csv

from flask import Flask, render_template, request

import config
from steps.load_csv import load_csv
from steps.normalize import normalize_marks
from steps.averages import compute_averages
from steps.category import assign_category
from steps.percentiles import compute_percentiles
from steps.academic_score import compute_academic_score
from steps.background_score import compute_background_score
from steps.final_score import compute_final_score
from steps.verify import print_verification


app = Flask(__name__)


def _export_transition_csv(conn, out_path, transition):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM filter_application
        WHERE class_transition = ?
        ORDER BY final_score IS NULL, final_score DESC
        """,
        (transition,),
    )
    rows = cur.fetchall()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        headers = [d[0] for d in cur.description]
        writer.writerow(headers)
        writer.writerows(rows)


def run_pipeline(csv_path):
    config.DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB)

    load_csv(conn, csv_path)
    normalize_marks(conn)
    compute_averages(conn)
    assign_category(conn)
    compute_percentiles(conn)
    compute_academic_score(conn)
    compute_background_score(conn)
    compute_final_score(conn)
    print_verification(conn)

    _export_transition_csv(conn, csv_path.parent / "filter_application_10_to_11.csv", "10_to_11")
    _export_transition_csv(conn, csv_path.parent / "filter_application_11_to_12.csv", "11_to_12")

    conn.close()


@app.route("/")
def index():
    csv_path = Path(request.args.get("csv") or config.CSV)
    refresh = request.args.get("refresh") == "1"
    transition = request.args.get("transition") or "all"
    try:
        weight = float(request.args.get("weight", config.FINAL_ACADEMIC_WEIGHT))
    except ValueError:
        weight = config.FINAL_ACADEMIC_WEIGHT
    weight = max(0.0, min(1.0, weight))
    background_weight = 1.0 - weight

    def _clamp01(val, default):
        try:
            parsed = float(val)
        except (TypeError, ValueError):
            parsed = default
        return max(0.0, min(1.0, parsed))

    w_c9_a = _clamp01(request.args.get("w_c9_a"), config.W_C9_A)
    w_c10_a = 1.0 - w_c9_a
    w_cat_b_10_11 = _clamp01(request.args.get("w_cat_b_10_11"), config.W_CAT_B_10_11)

    w_c10_a2 = _clamp01(request.args.get("w_c10_a2"), config.W_C10_A2)
    w_c11_a = 1.0 - w_c10_a2
    w_cat_b_11_12 = _clamp01(request.args.get("w_cat_b_11_12"), config.W_CAT_B_11_12)

    prev_weight = _clamp01(request.args.get("prev_weight"), weight)
    prev_background_weight = 1.0 - prev_weight
    prev_w_c9_a = _clamp01(request.args.get("prev_w_c9_a"), w_c9_a)
    prev_w_c10_a = 1.0 - prev_w_c9_a
    prev_w_cat_b_10_11 = _clamp01(request.args.get("prev_w_cat_b_10_11"), w_cat_b_10_11)
    prev_w_c10_a2 = _clamp01(request.args.get("prev_w_c10_a2"), w_c10_a2)
    prev_w_c11_a = 1.0 - prev_w_c10_a2
    prev_w_cat_b_11_12 = _clamp01(request.args.get("prev_w_cat_b_11_12"), w_cat_b_11_12)

    if not csv_path.exists():
        return f"CSV file not found: {csv_path}", 400

    if refresh or not config.DB.exists():
        run_pipeline(csv_path)

    conn = sqlite3.connect(config.DB)
    cur = conn.cursor()

    where_clause = ""
    where_params = []
    if transition in {"10_to_11", "11_to_12"}:
        where_clause = "WHERE class_transition = ?"
        where_params.append(transition)

    cur.execute(
        f"""
        SELECT *
        FROM filter_application
        {where_clause}
        """,
        where_params,
    )
    full_rows = cur.fetchall()
    full_headers = [d[0] for d in cur.description]

    def _calc_academic(row, c9_weight, cat_b_10_11, c10_weight, cat_b_11_12):
        transition_val = row.get("class_transition")
        category_val = row.get("category")
        c9_pct = row.get("c9_percentile")
        c10_pct = row.get("c10_percentile")
        c11_pct = row.get("c11_percentile")

        if transition_val == "10_to_11":
            if category_val == "A" and c9_pct is not None and c10_pct is not None:
                return round(c9_weight * c9_pct + (1.0 - c9_weight) * c10_pct, 4)
            if category_val == "B" and c9_pct is not None:
                return round(cat_b_10_11 * c9_pct, 4)
        if transition_val == "11_to_12":
            if category_val == "A" and c10_pct is not None and c11_pct is not None:
                return round(c10_weight * c10_pct + (1.0 - c10_weight) * c11_pct, 4)
            if category_val == "B" and c10_pct is not None:
                return round(cat_b_11_12 * c10_pct, 4)
        return None

    def _calc_final(academic_val, bg_val, acad_weight):
        if academic_val is None or bg_val is None:
            return None
        return round(acad_weight * academic_val + (1.0 - acad_weight) * bg_val, 4)

    def _assign_ranks(rows, score_key):
        scored = [
            (row.get("application_id"), row.get(score_key))
            for row in rows
            if row.get(score_key) is not None
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        ranks = {}
        rank = 0
        prev_score = None
        for app_id, score_val in scored:
            if prev_score is None or score_val != prev_score:
                rank += 1
                prev_score = score_val
            ranks[app_id] = rank
        return ranks

    rows_data = []
    for row in full_rows:
        row_dict = dict(zip(full_headers, row))
        academic_new = _calc_academic(row_dict, w_c9_a, w_cat_b_10_11, w_c10_a2, w_cat_b_11_12)
        final_new = _calc_final(academic_new, row_dict.get("background_score"), weight)
        academic_prev = _calc_academic(row_dict, prev_w_c9_a, prev_w_cat_b_10_11, prev_w_c10_a2, prev_w_cat_b_11_12)
        final_prev = _calc_final(academic_prev, row_dict.get("background_score"), prev_weight)
        row_dict["academic_score_calc"] = academic_new
        row_dict["final_score_calc"] = final_new
        row_dict["academic_score_prev"] = academic_prev
        row_dict["final_score_prev"] = final_prev
        rows_data.append(row_dict)

    new_ranks = _assign_ranks(rows_data, "final_score_calc")
    prev_ranks = _assign_ranks(rows_data, "final_score_prev")
    for row in rows_data:
        app_id = row.get("application_id")
        new_rank = new_ranks.get(app_id)
        prev_rank = prev_ranks.get(app_id)
        row["new_rank"] = new_rank
        row["prev_rank"] = prev_rank
        if new_rank is None or prev_rank is None:
            row["rank_change"] = None
        else:
            row["rank_change"] = prev_rank - new_rank

    plot_points = [
        {
            "application_id": row.get("application_id"),
            "applicant_name": row.get("applicant_name"),
            "prev_rank": row.get("prev_rank"),
            "new_rank": row.get("new_rank"),
        }
        for row in rows_data
        if row.get("prev_rank") is not None and row.get("new_rank") is not None
    ]

    rows_data.sort(
        key=lambda row: (row.get("final_score_calc") is None, -(row.get("final_score_calc") or 0))
    )

    display_headers = [
        "application_id",
        "program_type",
        "admin_notes",
        "applicant_name",
        "applicant_email",
        "class_transition",
        "current_class",
        "category",
        "c9_percentile",
        "c10_percentile",
        "c11_percentile",
        "academic_score_calc",
        "background_score",
        "final_score_calc",
        "prev_rank",
        "new_rank",
        "rank_change",
    ]

    display_rows = [[row.get(h) for h in display_headers] for row in rows_data]
    full_row_dicts = rows_data

    score_headers = ["academic_score_calc", "background_score", "final_score_calc"]
    total = len(rows_data)
    scored = sum(1 for row in rows_data if row.get("final_score_calc") is not None)

    conn.close()

    return render_template(
        "index.html",
        headers=display_headers,
        rows=display_rows,
        full_rows=full_row_dicts,
        score_headers=score_headers,
        transition=transition,
        weight=weight,
        background_weight=background_weight,
        w_c9_a=w_c9_a,
        w_c10_a=w_c10_a,
        w_cat_b_10_11=w_cat_b_10_11,
        w_c10_a2=w_c10_a2,
        w_c11_a=w_c11_a,
        w_cat_b_11_12=w_cat_b_11_12,
        prev_weight=prev_weight,
        prev_w_c9_a=prev_w_c9_a,
        prev_w_cat_b_10_11=prev_w_cat_b_10_11,
        prev_w_c10_a2=prev_w_c10_a2,
        prev_w_cat_b_11_12=prev_w_cat_b_11_12,
        plot_points=plot_points,
        total=total,
        scored=scored,
        csv_name=csv_path.name,
    )


if __name__ == "__main__":
    app.run(debug=True)
