"""Step 5 — Compute board+transition-specific percentiles."""

from collections import defaultdict


def _percentile_ranks(scores):
    """scores: list of (app_id, value). Returns {app_id: percentile}."""
    sorted_s = sorted(scores, key=lambda x: x[1])
    n = len(sorted_s)
    result = {}
    i = 0
    while i < n:
        j = i
        while j < n and sorted_s[j][1] == sorted_s[i][1]:
            j += 1
        pct = j / n * 100.0
        for k in range(i, j):
            result[sorted_s[k][0]] = pct
        i = j
    return result


def compute_percentiles(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT application_id, class_transition, assigned_board_category,
               c9_total_avg, c10_total_avg, c11_total_avg
        FROM filter_application
    """)
    all_rows = cur.fetchall()

    groups = defaultdict(list)
    for row in all_rows:
        groups[(row[1], row[2])].append(row)

    updates = {}
    for (transition, board), g_rows in groups.items():
        if transition == "10_to_11":
            for col_idx, pct_col in [(3, "c9_percentile"), (4, "c10_percentile")]:
                eligible = [(r[0], r[col_idx]) for r in g_rows if r[col_idx] is not None]
                if eligible:
                    for app_id, pct in _percentile_ranks(eligible).items():
                        updates.setdefault(app_id, {})[pct_col] = pct
        elif transition == "11_to_12":
            for col_idx, pct_col in [(4, "c10_percentile"), (5, "c11_percentile")]:
                eligible = [(r[0], r[col_idx]) for r in g_rows if r[col_idx] is not None]
                if eligible:
                    for app_id, pct in _percentile_ranks(eligible).items():
                        updates.setdefault(app_id, {})[pct_col] = pct

    for app_id, cols in updates.items():
        set_clause = ", ".join(f"{col}=?" for col in cols)
        cur.execute(
            f"UPDATE filter_application SET {set_clause} WHERE application_id=?",
            list(cols.values()) + [app_id]
        )
    conn.commit()
    print(f"  Updated percentiles for {len(updates)} rows.")
