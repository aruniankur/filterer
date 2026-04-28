"""Step 9 — Print verification table."""


def print_verification(conn):
    cur = conn.cursor()
    print("\n" + "═" * 100)
    print("  VERIFICATION TABLE")
    print("═" * 100)

    cur.execute("""
        SELECT
            class_transition, assigned_board_category, category,
            COUNT(*) as total,
            COUNT(c9_total_avg), COUNT(c10_total_avg), COUNT(c11_total_avg),
            COUNT(c9_percentile), COUNT(c10_percentile), COUNT(c11_percentile),
            COUNT(academic_score),
            ROUND(MIN(academic_score),2), ROUND(AVG(academic_score),2), ROUND(MAX(academic_score),2),
            SUM(CASE WHEN c9_science_swapped=1 OR c9_math_swapped=1
                       OR c10_science_swapped=1 OR c10_math_swapped=1
                       OR c11_physics_swapped=1 OR c11_chemistry_swapped=1
                       OR c11_math_swapped=1 OR c11_biology_swapped=1
                     THEN 1 ELSE 0 END),
            ROUND(AVG(background_score),2),
            ROUND(MIN(final_score),2), ROUND(AVG(final_score),2), ROUND(MAX(final_score),2)
        FROM filter_application
        GROUP BY class_transition, assigned_board_category, category
        ORDER BY class_transition, assigned_board_category, category
    """)
    hdr = (f"{'Transition':<12} {'Board':<7} {'Cat':>3} {'Total':>6} "
           f"{'c9avg':>6} {'c10avg':>6} {'c11avg':>6} {'c9pct':>6} {'c10pct':>6} {'c11pct':>6} "
           f"{'AcSc':>6} {'Swaps':>6} {'BgAvg':>7} "
           f"{'FnMin':>7} {'FnAvg':>7} {'FnMax':>7}")
    print(hdr)
    print("─" * 110)
    for r in cur.fetchall():
        print(f"{str(r[0]):<12} {str(r[1]):<7} {str(r[2]):>3} {r[3]:>6} "
              f"{r[4]:>6} {r[5]:>6} {r[6]:>6} {r[7]:>6} {r[8]:>6} {r[9]:>6} "
              f"{r[10]:>6} {r[14]:>6} {str(r[15]):>7} "
              f"{str(r[16]):>7} {str(r[17]):>7} {str(r[18]):>7}")
    print("─" * 110)

    cur.execute("""
        SELECT COUNT(*), COUNT(final_score),
               ROUND(MIN(final_score),2), ROUND(AVG(final_score),2), ROUND(MAX(final_score),2)
        FROM filter_application
    """)
    t = cur.fetchone()
    print(f"{'TOTAL':<12} {'':<7} {'':<3} {t[0]:>6} "
          f"{'':>6} {'':>6} {'':>6} {'':>6} {'':>6} {'':>6} "
          f"{'':>6} {'':>6} {'':>7} "
          f"{str(t[2]):>7} {str(t[3]):>7} {str(t[4]):>7}  (final_score: {t[1]} rows)")

    print("\n── Swap counts ──")
    for cls, subj in [("c9","science"),("c9","math"),("c10","science"),("c10","math"),
                       ("c11","physics"),("c11","chemistry"),("c11","math"),("c11","biology")]:
        col = f"{cls}_{subj}_swapped"
        cur.execute(f"SELECT SUM({col}) FROM filter_application")
        cnt = cur.fetchone()[0] or 0
        print(f"  {col:<28} {cnt:>3}  {'█' * min(cnt, 40)}")
