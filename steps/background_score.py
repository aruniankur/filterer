"""Step 7 — Compute socio-economic background score."""

import config as config


def _gender(v):
    return config.BG_GENDER_FEMALE if (v or '').strip().lower() == 'female' else config.BG_GENDER_MALE

def _location(v):
    v = (v or '').strip().lower()
    if 'village' in v:                        return config.BG_LOC_VILLAGE
    if 'rural' in v:                          return config.BG_LOC_RURAL
    if 'semi-urban' in v:                     return config.BG_LOC_SEMI_URBAN
    if 'small town' in v:                     return config.BG_LOC_SMALL_TOWN
    if 'medium town' in v or 'district' in v: return config.BG_LOC_MEDIUM_TOWN
    if 'big city' in v or 'metro' in v:       return config.BG_LOC_BIG_CITY
    return 0

def _institution(v):
    v = (v or '').strip().lower()
    if v == 'government': return config.BG_INST_GOVERNMENT
    if 'aided' in v:      return config.BG_INST_AIDED
    return config.BG_INST_PRIVATE

def _internet(v):
    v = (v or '').strip().lower()
    if v == 'no':       return config.BG_INTERNET_NO
    if v == 'limited':  return config.BG_INTERNET_LIMITED
    if v == 'reliable': return config.BG_INTERNET_RELIABLE
    return config.BG_INTERNET_BLANK

def _firstgen(v):
    return config.BG_FIRSTGEN_YES if (v or '').strip().lower() == 'yes' else config.BG_FIRSTGEN_NO


def compute_background_score(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT application_id, gender, location_type, institution_type,
               internet_access, first_gen_learner
        FROM filter_application
    """)
    updates = []
    for app_id, gender, location, institution, internet, firstgen in cur.fetchall():
        raw = _gender(gender) + _location(location) + _institution(institution) + _internet(internet) + _firstgen(firstgen)
        score = round(min(raw / config.BG_MAX_RAW * 100, config.BG_SOFT_CAP), 4)
        updates.append((score, app_id))

    cur.executemany(
        "UPDATE filter_application SET background_score=? WHERE application_id=?",
        updates
    )
    conn.commit()

    cur.execute("""
        SELECT ROUND(MIN(background_score),2), ROUND(AVG(background_score),2),
               ROUND(MAX(background_score),2),
               SUM(CASE WHEN background_score=? THEN 1 ELSE 0 END)
        FROM filter_application
    """, (config.BG_SOFT_CAP,))
    mn, avg, mx, capped = cur.fetchone()
    print(f"  Done. Min={mn}  Avg={avg}  Max={mx}  Capped@{config.BG_SOFT_CAP}={capped}")
