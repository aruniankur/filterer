"""Step 2 — Normalize marks [0,100] and detect mark/max swaps."""

SUBJECTS = [
    ("c9",  "science",   "c9_science_marks",    "c9_science_max"),
    ("c9",  "math",      "c9_math_marks",        "c9_math_max"),
    ("c10", "science",   "c10_science_marks",    "c10_science_max"),
    ("c10", "math",      "c10_math_marks",       "c10_math_max"),
    ("c11", "physics",   "c11_physics_marks",    "c11_physics_max"),
    ("c11", "chemistry", "c11_chemistry_marks",  "c11_chemistry_max"),
    ("c11", "math",      "c11_math_marks",       "c11_math_max"),
    ("c11", "biology",   "c11_biology_marks",    "c11_biology_max"),
]


def normalize_marks(conn):
    cur = conn.cursor()
    for cls, subj, marks_col, max_col in SUBJECTS:
        swapped = f"{cls}_{subj}_swapped"
        norm    = f"norm_{cls}_{subj}_marks"
        cur.execute(f"""
            UPDATE filter_application SET {swapped} =
                CASE WHEN {marks_col} IS NOT NULL AND {max_col} IS NOT NULL AND {marks_col} > {max_col}
                     THEN 1 ELSE 0 END
        """)
        cur.execute(f"""
            UPDATE filter_application SET {norm} =
                CASE WHEN {marks_col} IS NOT NULL AND {max_col} IS NOT NULL AND MAX({marks_col},{max_col}) > 0
                     THEN MIN({marks_col},{max_col}) / MAX({marks_col},{max_col}) * 100.0
                     ELSE NULL END
        """)
    conn.commit()
    print("  Done.")
