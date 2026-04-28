"""Step 3 — Compute per-class subject averages (c9/c10/c11_total_avg)."""


def _avg_and_flag(vals_map):
    missing = [s for s, v in vals_map.items() if v is None]
    vals = [v for v in vals_map.values() if v is not None]
    avg  = sum(vals) / len(vals) if vals else None
    flag = ("missing:" + ",".join(missing)) if missing else "ok"
    return avg, flag


def compute_averages(conn):
    cur = conn.cursor()

    # C9: math + science
    cur.execute("SELECT application_id, norm_c9_math_marks, norm_c9_science_marks FROM filter_application")
    for app_id, math, sci in cur.fetchall():
        avg, flag = _avg_and_flag({"math": math, "science": sci})
        cur.execute(
            "UPDATE filter_application SET c9_total_avg=?, c9_total_avg_flag=? WHERE application_id=?",
            (avg, flag, app_id)
        )

    # C10: math + science
    cur.execute("SELECT application_id, norm_c10_math_marks, norm_c10_science_marks FROM filter_application")
    for app_id, math, sci in cur.fetchall():
        avg, flag = _avg_and_flag({"math": math, "science": sci})
        cur.execute(
            "UPDATE filter_application SET c10_total_avg=?, c10_total_avg_flag=? WHERE application_id=?",
            (avg, flag, app_id)
        )

    # C11: physics + chemistry + math + biology (include whichever exist)
    cur.execute("""
        SELECT application_id, norm_c11_physics_marks, norm_c11_chemistry_marks,
               norm_c11_math_marks, norm_c11_biology_marks
        FROM filter_application
    """)
    c11_subjects = ["physics", "chemistry", "math", "biology"]
    for row in cur.fetchall():
        app_id = row[0]
        avg, flag = _avg_and_flag(dict(zip(c11_subjects, row[1:])))
        cur.execute(
            "UPDATE filter_application SET c11_total_avg=?, c11_total_avg_flag=? WHERE application_id=?",
            (avg, flag, app_id)
        )

    conn.commit()
    print("  Done.")
