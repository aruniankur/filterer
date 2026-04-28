"""Step 4 — Assign A/B category based on which class averages are present."""


def assign_category(conn):
    conn.execute("""
        UPDATE filter_application SET category = CASE
            WHEN class_transition='10_to_11' AND c9_total_avg IS NOT NULL AND c10_total_avg IS NOT NULL THEN 'A'
            WHEN class_transition='10_to_11' AND c9_total_avg IS NOT NULL AND c10_total_avg IS NULL     THEN 'B'
            WHEN class_transition='11_to_12' AND c10_total_avg IS NOT NULL AND c11_total_avg IS NOT NULL THEN 'A'
            WHEN class_transition='11_to_12' AND c10_total_avg IS NOT NULL AND c11_total_avg IS NULL     THEN 'B'
            ELSE NULL
        END
    """)
    conn.commit()
    print("  Done.")
