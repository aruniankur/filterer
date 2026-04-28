#!/usr/bin/env python3
"""
pipeline_csv.py — Orchestrator.

Runs all steps in order. To tune weights/constants, edit config.py only.
To modify step logic, edit the corresponding file in steps/.
"""

import argparse
import csv
import sqlite3
from pathlib import Path
import pandas as pd
import config as config
from steps.load_csv         import load_csv
from steps.normalize        import normalize_marks
from steps.averages         import compute_averages
from steps.category         import assign_category
from steps.percentiles      import compute_percentiles
from steps.academic_score   import compute_academic_score
from steps.background_score import compute_background_score
from steps.final_score      import compute_final_score
from steps.verify           import print_verification


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

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        headers = [d[0] for d in cur.description]
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"  Exported {len(rows)} rows -> {out_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Run the filter application pipeline.")
    parser.add_argument(
        "csv",
        nargs="?",
        default=None,
        help="Path to the input CSV file. Defaults to the path set in config.py.",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv) if args.csv else config.CSV
    if not csv_path.exists():
        parser.error(f"CSV file not found: {csv_path}")

    print(f"  Using CSV: {csv_path}")

    config.DB.parent.mkdir(parents=True, exist_ok=True)  # create dir if missing
    conn = sqlite3.connect(config.DB)  # sqlite3 creates the .db file if it doesn't exist

    print("\n── Step 1: Create table & load CSV ──")
    load_csv(conn, csv_path)

    print("\n── Step 2: Normalize marks + detect swaps ──")
    normalize_marks(conn)

    print("\n── Step 3: Compute c9/c10/c11 total averages ──")
    compute_averages(conn)

    print("\n── Step 4: Assign category (A/B) ──")
    assign_category(conn)

    print("\n── Step 5: Compute percentiles ──")
    compute_percentiles(conn)

    print("\n── Step 6: Compute academic score ──")
    compute_academic_score(conn)

    print("\n── Step 7: Compute background score ──")
    compute_background_score(conn)

    print("\n── Step 8: Compute final score ──")
    compute_final_score(conn)

    print_verification(conn)

    print("\n── Step 9: Export transition CSVs ──")
    _export_transition_csv(conn, csv_path.parent / "filter_application_10_to_11.csv", "10_to_11")
    _export_transition_csv(conn, csv_path.parent / "filter_application_11_to_12.csv", "11_to_12")
    

    df1 = pd.read_csv(csv_path.parent / "filter_application_10_to_11.csv")
    df2 = pd.read_csv(csv_path.parent / "filter_application_11_to_12.csv")

    merged = pd.concat([df1, df2], ignore_index=True)

    merged.to_csv("webpage/merged_all.csv", index=False)

    conn.close()
    print("\n✓ Pipeline complete.")


if __name__ == "__main__":
    main()
