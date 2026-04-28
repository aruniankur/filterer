"""
Step 8 — Compute final score.

Final Score = FINAL_ACADEMIC_WEIGHT * academic_score
            + FINAL_BACKGROUND_WEIGHT * background_score

Both scores must be non-NULL for a final_score to be computed.
"""

import config


def compute_final_score(conn):
    cur = conn.cursor()

    # Ensure column exists
    cur.execute("PRAGMA table_info(filter_application)")
    if "final_score" not in {r[1] for r in cur.fetchall()}:
        cur.execute("ALTER TABLE filter_application ADD COLUMN final_score REAL")
        conn.commit()

    cur.execute(f"""
        UPDATE filter_application
        SET final_score = CASE
            WHEN academic_score IS NOT NULL AND background_score IS NOT NULL
                THEN ROUND(
                    {config.FINAL_ACADEMIC_WEIGHT}   * academic_score
                  + {config.FINAL_BACKGROUND_WEIGHT} * background_score,
                    4
                )
            ELSE NULL
        END
    """)
    conn.commit()

    cur.execute("""
        SELECT COUNT(final_score),
               ROUND(MIN(final_score), 2),
               ROUND(AVG(final_score), 2),
               ROUND(MAX(final_score), 2)
        FROM filter_application
    """)
    cnt, mn, avg, mx = cur.fetchone()
    print(f"  Done. Scored={cnt}  Min={mn}  Avg={avg}  Max={mx}")
