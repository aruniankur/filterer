"""
Step 1 — Parse CSV and insert raw rows into filter_application.
Drops and recreates the table on every run.
"""

import csv


# CSV column header → internal short key
HEADER_MAP = {
    "Application ID":                          "app_id",
    "Program Type":                            "program_type",
    "Admin Notes":                             "admin_notes",
    "Applicant Name":                          "name",
    "Applicant Email":                         "email",
    "Section A - Gender":                      "gender",
    "Section B - Location Type":               "location_type",
    "Section C - Board":                       "sec_c_board",
    "Section C - Class Transition":            "transition",
    "Section C - Current Class":               "current_class",
    "Section C - Institution Type":            "institution_type",
    "Section C - Medium":                      "medium",
    "Section C - School Location Type":        "school_location",
    "Section C - School State":                "school_state",
    "Section D - Class 9 Board":               "c9_board",
    "Section D - Class 9 Board State":         "c9_board_state",
    "Section D - Class 9 Percentage":          "c9_pct",
    "Section D - Class 9 Science Marks":       "c9_sci_m",
    "Section D - Class 9 Science Max":         "c9_sci_x",
    "Section D - Class 9 Mathematics Marks":   "c9_math_m",
    "Section D - Class 9 Mathematics Max":     "c9_math_x",
    "Section D - Class 10 Board":              "c10_board",
    "Section D - Class 10 Board State":        "c10_board_state",
    "Section D - Class 10 Percentage":         "c10_pct",
    "Section D - Class 10 Science Marks":      "c10_sci_m",
    "Section D - Class 10 Science Max":        "c10_sci_x",
    "Section D - Class 10 Mathematics Marks":  "c10_math_m",
    "Section D - Class 10 Mathematics Max":    "c10_math_x",
    "Section D - Class 11 Board":              "c11_board",
    "Section D - Class 11 Board State":        "c11_board_state",
    "Section D - Class 11 Percentage":         "c11_pct",
    "Section D - Class 11 Physics Marks":      "c11_phy_m",
    "Section D - Class 11 Physics Max":        "c11_phy_x",
    "Section D - Class 11 Chemistry Marks":    "c11_che_m",
    "Section D - Class 11 Chemistry Max":      "c11_che_x",
    "Section D - Class 11 Mathematics Marks":  "c11_math_m",
    "Section D - Class 11 Mathematics Max":    "c11_math_x",
    "Section D - Class 11 Biology Marks":      "c11_bio_m",
    "Section D - Class 11 Biology Max":        "c11_bio_x",
    "Section E - Coaching Classes":            "coaching",
    "Section E - Father Education":            "father_edu",
    "Section E - First Gen Learner":           "first_gen",
    "Section E - Internet Access":             "internet",
    "Section E - Mother Education":            "mother_edu",
}


def _safe_float(val):
    if val is None:
        return None
    s = str(val).strip()
    if s in ("", "NA", "N/A", "na"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_board_category(raw):
    if not raw:
        return None
    b = str(raw).strip().upper()
    if not b or b in ("NA", "N/A"):
        return None
    if "CBSE" in b or "CENTRAL BOARD" in b:
        return "CBSE"
    if "ICSE" in b or "ISC" in b or "CISCE" in b:
        return "ICSE"
    return "Other"


def _assign_board_and_rule(transition, sec_c_board, b9_raw, b10_raw, b11_raw, pct9, pct10, pct11):
    b9  = _to_board_category(b9_raw  or sec_c_board)
    b10 = _to_board_category(b10_raw or sec_c_board)
    b11 = _to_board_category(b11_raw or sec_c_board)
    has9, has10, has11 = pct9 is not None, pct10 is not None, pct11 is not None

    if transition == "10_to_11":
        if has9 and has10:
            return (b9, "10_to_11_same_9_10") if b9 and b9 == b10 else ("Other", "10_to_11_mismatch_9_10")
        if has9:
            return (b9 or "Other"), "10_to_11_only_9"
        return None, "10_to_11_no_9_mark"

    if transition == "11_to_12":
        if has10 and has11:
            return (b10, "11_to_12_same_10_11") if b10 and b10 == b11 else ("Other", "11_to_12_mismatch_10_11")
        if has10:
            return (b10 or "Other"), "11_to_12_only_10"
        return None, "11_to_12_no_10_mark"

    return None, "unsupported_transition"


def load_csv(conn, csv_path):
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS filter_application")
    cur.execute("""
    CREATE TABLE filter_application (
        -- identity
        application_id      TEXT PRIMARY KEY,
        program_type        TEXT,
        admin_notes         TEXT,
        applicant_name      TEXT,
        applicant_email     TEXT,
        -- section A/B/C
        gender              TEXT,
        location_type       TEXT,
        sec_c_board         TEXT,
        class_transition    TEXT,
        current_class       TEXT,
        institution_type    TEXT,
        medium              TEXT,
        school_location     TEXT,
        school_state        TEXT,
        -- section E
        coaching_classes    TEXT,
        father_education    TEXT,
        first_gen_learner   TEXT,
        internet_access     TEXT,
        mother_education    TEXT,
        -- class 9 raw
        c9_board            TEXT,
        c9_board_state      TEXT,
        c9_science_marks    REAL,
        c9_science_max      REAL,
        c9_math_marks       REAL,
        c9_math_max         REAL,
        c9_percentage       REAL,
        -- class 10 raw
        c10_board           TEXT,
        c10_board_state     TEXT,
        c10_science_marks   REAL,
        c10_science_max     REAL,
        c10_math_marks      REAL,
        c10_math_max        REAL,
        c10_percentage      REAL,
        -- class 11 raw
        c11_board           TEXT,
        c11_board_state     TEXT,
        c11_physics_marks   REAL,
        c11_physics_max     REAL,
        c11_chemistry_marks REAL,
        c11_chemistry_max   REAL,
        c11_math_marks      REAL,
        c11_math_max        REAL,
        c11_biology_marks   REAL,
        c11_biology_max     REAL,
        c11_percentage      REAL,
        -- computed: board assignment
        assigned_board_category TEXT,
        rule_applied            TEXT,
        -- computed: swap flags
        c9_science_swapped    INTEGER DEFAULT 0,
        c9_math_swapped       INTEGER DEFAULT 0,
        c10_science_swapped   INTEGER DEFAULT 0,
        c10_math_swapped      INTEGER DEFAULT 0,
        c11_physics_swapped   INTEGER DEFAULT 0,
        c11_chemistry_swapped INTEGER DEFAULT 0,
        c11_math_swapped      INTEGER DEFAULT 0,
        c11_biology_swapped   INTEGER DEFAULT 0,
        -- computed: normalized marks
        norm_c9_science_marks    REAL,
        norm_c9_math_marks       REAL,
        norm_c10_science_marks   REAL,
        norm_c10_math_marks      REAL,
        norm_c11_physics_marks   REAL,
        norm_c11_chemistry_marks REAL,
        norm_c11_math_marks      REAL,
        norm_c11_biology_marks   REAL,
        -- computed: averages
        c9_total_avg       REAL,
        c9_total_avg_flag  TEXT,
        c10_total_avg      REAL,
        c10_total_avg_flag TEXT,
        c11_total_avg      REAL,
        c11_total_avg_flag TEXT,
        -- computed: category
        category           TEXT,
        -- computed: percentiles
        c9_percentile      REAL,
        c10_percentile     REAL,
        c11_percentile     REAL,
        -- computed: scores
        academic_score     REAL,
        background_score   REAL,
        final_score        REAL
    )
    """)
    conn.commit()

    inserts = []
    skipped_ids = []   # admin_notes == "2" → exclude from pipeline, save to CSV
    no_notes_ids = []  # admin_notes == ""  → include in pipeline, save to CSV

    with open(csv_path, encoding="utf-8-sig") as f:  # utf-8-sig strips BOM (﻿) if present
        for row in csv.DictReader(f):
            r = {v: row.get(k, "").strip() for k, v in HEADER_MAP.items()}
            notes = r.get("admin_notes", "").strip()

            # admin_notes == "2": record app_id and skip
            if notes == "2":
                skipped_ids.append(r["app_id"])
                continue

            # admin_notes == "": include in pipeline but track separately
            if notes == "":
                no_notes_ids.append(r["app_id"])

            # admin_notes == "1" or blank: include in pipeline
            pct9  = _safe_float(r["c9_pct"])
            pct10 = _safe_float(r["c10_pct"])
            pct11 = _safe_float(r["c11_pct"])
            board_cat, rule = _assign_board_and_rule(
                r["transition"], r["sec_c_board"],
                r["c9_board"], r["c10_board"], r["c11_board"],
                pct9, pct10, pct11
            )
            inserts.append((
                r["app_id"], r["program_type"], notes, r["name"], r["email"],
                r["gender"], r["location_type"], r["sec_c_board"],
                r["transition"], r["current_class"], r["institution_type"],
                r["medium"], r["school_location"], r["school_state"],
                r["coaching"], r["father_edu"], r["first_gen"], r["internet"], r["mother_edu"],
                r["c9_board"], r["c9_board_state"],
                _safe_float(r["c9_sci_m"]),  _safe_float(r["c9_sci_x"]),
                _safe_float(r["c9_math_m"]), _safe_float(r["c9_math_x"]),
                pct9,
                r["c10_board"], r["c10_board_state"],
                _safe_float(r["c10_sci_m"]),  _safe_float(r["c10_sci_x"]),
                _safe_float(r["c10_math_m"]), _safe_float(r["c10_math_x"]),
                pct10,
                r["c11_board"], r["c11_board_state"],
                _safe_float(r["c11_phy_m"]),  _safe_float(r["c11_phy_x"]),
                _safe_float(r["c11_che_m"]),  _safe_float(r["c11_che_x"]),
                _safe_float(r["c11_math_m"]), _safe_float(r["c11_math_x"]),
                _safe_float(r["c11_bio_m"]),  _safe_float(r["c11_bio_x"]),
                pct11,
                board_cat, rule,
            ))

    # Write excluded (admin_notes == "2") application IDs to a CSV
    skipped_path = csv_path.parent / "excluded_admin_notes_2.csv"
    with open(skipped_path, "w", newline="", encoding="utf-8") as sf:
        writer = csv.writer(sf)
        writer.writerow(["application_id"])
        writer.writerows([[aid] for aid in skipped_ids])
    if skipped_ids:
        print(f"  Excluded {len(skipped_ids)} rows (admin_notes=2) → {skipped_path.name}")

    # Write no-notes (admin_notes == "") application IDs to a CSV
    no_notes_path = csv_path.parent / "no_admin_notes.csv"
    with open(no_notes_path, "w", newline="", encoding="utf-8") as nf:
        writer = csv.writer(nf)
        writer.writerow(["application_id"])
        writer.writerows([[aid] for aid in no_notes_ids])
    if no_notes_ids:
        print(f"  Flagged  {len(no_notes_ids)} rows (admin_notes empty) → {no_notes_path.name}")

    cur.executemany("""
        INSERT INTO filter_application (
            application_id, program_type, admin_notes, applicant_name, applicant_email,
            gender, location_type, sec_c_board, class_transition, current_class, institution_type,
            medium, school_location, school_state,
            coaching_classes, father_education, first_gen_learner, internet_access, mother_education,
            c9_board, c9_board_state,
            c9_science_marks, c9_science_max, c9_math_marks, c9_math_max, c9_percentage,
            c10_board, c10_board_state,
            c10_science_marks, c10_science_max, c10_math_marks, c10_math_max, c10_percentage,
            c11_board, c11_board_state,
            c11_physics_marks, c11_physics_max, c11_chemistry_marks, c11_chemistry_max,
            c11_math_marks, c11_math_max, c11_biology_marks, c11_biology_max, c11_percentage,
            assigned_board_category, rule_applied
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, inserts)
    conn.commit()
    print(f"  Inserted {len(inserts)} rows from CSV.")
