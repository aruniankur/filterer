"""Step 6 — Compute weighted academic score from percentiles."""

import config as config


def compute_academic_score(conn):
    conn.execute(f"""
        UPDATE filter_application SET academic_score = CASE
            WHEN class_transition='10_to_11' AND category='A'
                 AND c9_percentile IS NOT NULL AND c10_percentile IS NOT NULL
                THEN {config.W_C9_A} * c9_percentile + {config.W_C10_A} * c10_percentile
            WHEN class_transition='10_to_11' AND category='B'
                 AND c9_percentile IS NOT NULL
                THEN {config.W_CAT_B_10_11} * c9_percentile
            WHEN class_transition='11_to_12' AND category='A'
                 AND c10_percentile IS NOT NULL AND c11_percentile IS NOT NULL
                THEN {config.W_C10_A2} * c10_percentile + {config.W_C11_A} * c11_percentile
            WHEN class_transition='11_to_12' AND category='B'
                 AND c10_percentile IS NOT NULL
                THEN {config.W_CAT_B_11_12} * c10_percentile
            ELSE NULL
        END
    """)
    conn.commit()
    print("  Done.")
