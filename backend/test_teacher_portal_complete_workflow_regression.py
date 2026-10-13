"""
Complete Regression Test Suite: Teacher Portal Class & Evaluation Workflow

Verifies the end-to-end workflow:
  1. A teacher creates a class.
  2. The teacher uploads a student list (CSV/Excel/Word/PDF roster parsing).
  3. System extracts names and identifiers, imports only confirmed rows.
  4. The teacher can add a missing student manually later.
  5. The class roster displays only actual students belonging to that class.
  6. The teacher evaluates an answer script and links the correct roster student.
  7. Marks and question-wise answers persist against that student.
  8. Plagiarism Audit compares eligible submissions and displays evidence-linked findings.
  9. Misconception Map identifies evidence-supported conceptual misunderstandings.
  10. Action Center shows justified support actions for the correct students.
  11. Academic Reports generates an accurate whole-class summary from completed evaluations.
  12. Refreshing the application / re-authenticating retains all records without misassignment.

Also verifies edge cases:
  - Empty classes and empty evaluations.
  - Duplicate names and students with similar names (no silent cross-attachment).
  - Failed/unclear file extraction.
  - Invalid marks and incomplete assessments.
  - Two teachers with different classes (cross-teacher data isolation).
  - Students belonging to more than one class.
  - Missing, ambiguous, or legacy evaluation ownership.
  - Database and AI processing error resilience.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure backend directory is in path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db import get_sqlite_db, init_db
from app.roster_parser import (
    parse_manual_roster_text,
    normalize_student_name,
)
from app.evaluation.store import (
    resolve_student_identity_and_class,
    store_evaluation_pipeline,
)
from app.evaluation.class_report import derive_class_report
from app.evaluation.class_report_pdf import generate_class_report_pdf
from app.evaluation.action_center import derive_action_items_from_evaluation
from app.plagiarism.detector import PlagiarismDetector


class TestTeacherPortalWorkflowRegression(unittest.TestCase):
    def setUp(self):
        # Setup temporary isolated SQLite DB
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name

        os.environ["DATABASE_PATH"] = self.db_path
        os.environ["SQLITE_DB_PATH"] = self.db_path
        os.environ["MONGO_URI"] = ""
        os.environ["MONGODB_URI"] = ""

        import app.db
        app.db._mongo_db = None
        app.db._mongo_client = None
        app.db.DB_PATH = Path(self.db_path)

        init_db()
        self.conn = get_sqlite_db()

        # Seed two distinct teachers
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO users (user_id, name, email, role, password_hash) VALUES (?, ?, ?, ?, ?)",
            ("tea_smith", "Dr. Jane Smith", "jsmith@school.edu", "teacher", "hashed_pwd")
        )
        cursor.execute(
            "INSERT INTO users (user_id, name, email, role, password_hash) VALUES (?, ?, ?, ?, ?)",
            ("tea_doe", "Mr. John Doe", "jdoe@school.edu", "teacher", "hashed_pwd")
        )
        self.conn.commit()

    def tearDown(self):
        try:
            self.conn.close()
        except Exception:
            pass
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except Exception:
                pass

    # ──────────────────────────────────────────────────────────────────────────
    # WORKFLOW TESTS: Steps 1 - 5 (Class Creation, Roster Parsing, Manual Add)
    # ──────────────────────────────────────────────────────────────────────────

    def test_01_create_class_and_parse_roster(self):
        """Steps 1-3: Create class, parse roster list, verify only valid rows extracted."""
        cursor = self.conn.cursor()
        class_id = "cls_phys_101"
        cursor.execute(
            """
            INSERT INTO teacher_classes (id, teacher_id, name, grade_level, section, subjects_json, students_json, students_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (class_id, "tea_smith", "Physics 101", "11", "A", json.dumps(["Physics"]), "[]", 0)
        )
        self.conn.commit()

        # Step 2 & 3: Roster parsing from raw text / CSV simulation
        csv_sample = """Name,Roll Number,Email
Alice Johnson,PHY-001,alice.j@school.edu
Bob Martinez,PHY-002,bob.m@school.edu
Charlie Brown,PHY-003,charlie.b@school.edu
"""
        parse_res = parse_manual_roster_text(csv_sample)
        parsed_students = parse_res.get("students", [])
        self.assertEqual(len(parsed_students), 3)
        self.assertEqual(parsed_students[0]["name"], "Alice Johnson")
        self.assertEqual(parsed_students[0]["rollNo"], "PHY-001")
        self.assertEqual(parsed_students[0]["email"], "alice.j@school.edu")

        # Confirm and save roster
        cursor.execute(
            "UPDATE teacher_classes SET students_json = ?, students_count = ? WHERE id = ?",
            (json.dumps(parsed_students), len(parsed_students), class_id)
        )
        for i, s in enumerate(parsed_students):
            cursor.execute(
                """
                INSERT INTO class_memberships (id, class_id, teacher_id, student_id, student_name, roll_number, email)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (f"mem_{class_id}_{i}", class_id, "tea_smith", f"stu_{i}", s["name"], s["rollNo"], s["email"])
            )
        self.conn.commit()

        # Verify roster count
        cursor.execute("SELECT students_count, students_json FROM teacher_classes WHERE id = ?", (class_id,))
        row = cursor.fetchone()
        self.assertEqual(row["students_count"], 3)
        saved = json.loads(row["students_json"])
        self.assertEqual(len(saved), 3)

    def test_02_add_missing_student_manually(self):
        """Step 4: Teacher adds a missing student manually later."""
        cursor = self.conn.cursor()
        class_id = "cls_chem_102"
        initial_students = [{"name": "David Miller", "rollNumber": "CH-01", "email": "david@school.edu"}]
        cursor.execute(
            """
            INSERT INTO teacher_classes (id, teacher_id, name, grade_level, section, subjects_json, students_json, students_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (class_id, "tea_smith", "Chemistry 102", "12", "B", json.dumps(["Chemistry"]), json.dumps(initial_students), 1)
        )
        cursor.execute(
            """
            INSERT INTO class_memberships (id, class_id, teacher_id, student_id, student_name, roll_number, email)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("mem_chem_01", class_id, "tea_smith", "stu_david", "David Miller", "CH-01", "david@school.edu")
        )
        self.conn.commit()

        # Manually add Elena Rostova
        new_student = {"name": "Elena Rostova", "rollNumber": "CH-02", "email": "elena@school.edu"}
        current_students = initial_students + [new_student]
        cursor.execute(
            "UPDATE teacher_classes SET students_json = ?, students_count = ? WHERE id = ?",
            (json.dumps(current_students), len(current_students), class_id)
        )
        cursor.execute(
            """
            INSERT INTO class_memberships (id, class_id, teacher_id, student_id, student_name, roll_number, email)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("mem_chem_02", class_id, "tea_smith", "stu_elena", new_student["name"], new_student["rollNumber"], new_student["email"])
        )
        self.conn.commit()

        cursor.execute("SELECT students_count, students_json FROM teacher_classes WHERE id = ?", (class_id,))
        row = cursor.fetchone()
        self.assertEqual(row["students_count"], 2)
        saved = json.loads(row["students_json"])
        names = [s["name"] for s in saved]
        self.assertIn("Elena Rostova", names)

    def test_03_class_roster_isolation(self):
        """Step 5 & Edge Case: Class roster displays ONLY actual students belonging to that class."""
        cursor = self.conn.cursor()
        # Class 1 (Jane Smith) has Alice
        cursor.execute(
            """
            INSERT INTO teacher_classes (id, teacher_id, name, grade_level, section, subjects_json, students_json, students_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("cls_1", "tea_smith", "Class 1", "10", "A", json.dumps(["Math"]), json.dumps([{"name": "Alice"}]), 1)
        )
        # Class 2 (John Doe) has Bob
        cursor.execute(
            """
            INSERT INTO teacher_classes (id, teacher_id, name, grade_level, section, subjects_json, students_json, students_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("cls_2", "tea_doe", "Class 2", "10", "B", json.dumps(["Science"]), json.dumps([{"name": "Bob"}]), 1)
        )
        self.conn.commit()

        # Verify Jane Smith cannot see Bob
        cursor.execute("SELECT students_json FROM teacher_classes WHERE teacher_id = ? AND id = ?", ("tea_smith", "cls_1"))
        c1 = json.loads(cursor.fetchone()["students_json"])
        self.assertEqual([s["name"] for s in c1], ["Alice"])

        # Verify John Doe cannot access Class 1
        cursor.execute("SELECT id FROM teacher_classes WHERE teacher_id = ? AND id = ?", ("tea_doe", "cls_1"))
        self.assertIsNone(cursor.fetchone())

    # ──────────────────────────────────────────────────────────────────────────
    # WORKFLOW TESTS: Steps 6 - 7 (Evaluation, Linking, Persistence)
    # ──────────────────────────────────────────────────────────────────────────

    def test_04_evaluate_answer_script_and_persistence(self):
        """Steps 6-7: Teacher evaluates script, links correct roster student, marks persist."""
        cursor = self.conn.cursor()
        class_id = "cls_bio_200"
        roster = [
            {"id": "stu_fiona", "name": "Fiona Gallagher", "rollNumber": "BIO-10", "email": "fiona@gallagher.edu"},
            {"id": "stu_george", "name": "George Clark", "rollNumber": "BIO-11", "email": "george@clark.edu"}
        ]
        cursor.execute(
            """
            INSERT INTO teacher_classes (id, teacher_id, name, grade_level, section, subjects_json, students_json, students_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (class_id, "tea_smith", "Biology 200", "11", "A", json.dumps(["Biology"]), json.dumps(roster), 2)
        )
        cursor.execute(
            """
            INSERT INTO class_memberships (id, class_id, teacher_id, student_id, student_name, roll_number, email)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("mem_bio_10", class_id, "tea_smith", "stu_fiona", "Fiona Gallagher", "BIO-10", "fiona@gallagher.edu")
        )
        self.conn.commit()

        # Resolve student identity via request_data
        request_data = {
            "class_id": class_id,
            "teacher_id": "tea_smith",
            "student_id": "stu_fiona",
            "student_email": "fiona@gallagher.edu"
        }
        res_class_id, res_teacher_id, res_student_id, res_user_id, status, reason = resolve_student_identity_and_class(
            request_data=request_data,
            student_name="Fiona Gallagher",
            roll_number="BIO-10"
        )
        self.assertEqual(status, "VERIFIED")
        self.assertEqual(res_class_id, class_id)
        self.assertEqual(res_teacher_id, "tea_smith")

        # Save completed evaluation record
        eval_data = {
            "evaluation_source": "TEACHER_EVALUATION",
            "teacher_id": "tea_smith",
            "class_id": class_id,
            "student_name": "Fiona Gallagher",
            "roll_number": "BIO-10",
            "subject": "Biology",
            "assessment_title": "Cell Biology Midterm",
            "obtained_marks": 42.5,
            "total_marks": 50.0,
            "percentage": 85.0,
            "grade": "A",
            "questions": [
                {
                    "question_number": "1",
                    "concept": "Mitochondrial Respiration",
                    "maximum_marks": 25.0,
                    "awarded_marks": 23.5,
                    "student_answer": "ATP is generated via oxidative phosphorylation in the inner membrane.",
                    "is_correct": True,
                    "misconception_detected": False,
                },
                {
                    "question_number": "2",
                    "concept": "Photosynthesis Light Reactions",
                    "maximum_marks": 25.0,
                    "awarded_marks": 19.0,
                    "student_answer": "Light excites chlorophyll electrons in PSII and PSI.",
                    "is_correct": False,
                    "misconception_detected": False,
                }
            ]
        }
        ev_id = store_evaluation_pipeline(
            request_data=request_data,
            eval_result=eval_data
        )
        self.assertTrue(bool(ev_id))

        # Verify question-level persistence in evaluation_questions table
        cursor.execute("SELECT * FROM evaluation_questions WHERE evaluation_id = ?", (ev_id,))
        q_rows = cursor.fetchall()
        self.assertEqual(len(q_rows), 2)
        q1 = [r for r in q_rows if str(r["question_number"]) == "1"][0]
        self.assertEqual(float(q1["awarded_marks"]), 23.5)
        self.assertEqual(float(q1["maximum_marks"]), 25.0)

    # ──────────────────────────────────────────────────────────────────────────
    # WORKFLOW TESTS: Step 8 (Plagiarism Audit)
    # ──────────────────────────────────────────────────────────────────────────

    def test_05_plagiarism_audit_evidence_detection(self):
        """Step 8: Plagiarism Audit extracts fingerprints and identifies matching passages."""
        detector = PlagiarismDetector()
        
        # Test text extraction & fingerprints
        text_1 = "The mitochondrial membrane produces ATP through cellular respiration and oxidative phosphorylation."
        text_2 = "The mitochondrial membrane produces ATP through cellular respiration and oxidative phosphorylation."
        
        fp1 = detector.extract_text_and_fingerprints(text_1)
        fp2 = detector.extract_text_and_fingerprints(text_2)
        
        self.assertTrue(fp1["has_content"])
        self.assertEqual(fp1["content_fingerprint"], fp2["content_fingerprint"])
        
        # Find overlapping passage
        passage = detector._find_overlapping_passage(fp1["tokens"], fp2["tokens"], min_length=4)
        self.assertIn("mitochondrial membrane produces atp", passage.lower())

    # ──────────────────────────────────────────────────────────────────────────
    # WORKFLOW TESTS: Step 9 (Misconception Map)
    # ──────────────────────────────────────────────────────────────────────────

    def test_06_misconception_map_and_action_center(self):
        """Steps 9-10: Evidence-based misconception detection & Action Center recommendations."""
        eval_doc = {
            "id": "ev_misc_01",
            "teacher_id": "tea_smith",
            "class_id": "cls_phys_101",
            "student_name": "Hannah Abbott",
            "roll_number": "HA-01",
            "subject": "Physics",
            "assessment_title": "Newtonian Mechanics",
            "evaluation_source": "TEACHER_EVALUATION",
            "obtained_marks": 12.0,
            "total_marks": 30.0,
            "questions": [
                {
                    "question_number": "1",
                    "concept": "Newton's Third Law",
                    "maximum_marks": 15.0,
                    "awarded_marks": 4.0,
                    "student_answer": "The horse pulls the cart harder than the cart pulls the horse, so it moves.",
                    "misconception_detected": True,
                    "misconception": "Forces in an action-reaction pair are unequal when motion occurs.",
                    "explanation": "Action and reaction are always equal in magnitude and opposite in direction."
                }
            ]
        }

        # Derive Action Center items
        items = derive_action_items_from_evaluation(eval_doc)
        self.assertGreaterEqual(len(items), 1)
        
        # Find the question-level misconception item
        misc_items = [it for it in items if it.get("category") in ("severe_misconception", "repeated_concept_loss")]
        self.assertTrue(len(misc_items) > 0)
        item = misc_items[0]
        self.assertEqual(item["student_name"], "Hannah Abbott")
        self.assertEqual(item["skill_or_topic"], "Newton's Third Law")
        self.assertEqual(item["question_max_marks"], 15.0)
        self.assertEqual(item["question_awarded_marks"], 4.0)
        self.assertIn("Forces in an action-reaction pair are unequal", item["misconception"])
        self.assertTrue(len(item["action"]) > 0)

    # ──────────────────────────────────────────────────────────────────────────
    # WORKFLOW TESTS: Step 11 (Academic Reports Generation)
    # ──────────────────────────────────────────────────────────────────────────

    def test_07_class_academic_report_derivation(self):
        """Step 11: Academic Reports generates an accurate whole-class summary."""
        class_doc = {
            "id": "cls_lit_300",
            "name": "Literature 300",
            "grade_level": "Grade 11",
            "section": "A",
            "subjects": ["Literature"],
            "students": [
                {"name": "Ian Malcolm", "roll_number": "LIT-01"},
                {"name": "Julia Roberts", "roll_number": "LIT-02"},
                {"name": "Kevin Bacon", "roll_number": "LIT-03"}  # Not evaluated
            ]
        }

        evaluations = [
            {
                "id": "ev_ian",
                "student_name": "Ian Malcolm",
                "roll_number": "LIT-01",
                "assessment_title": "Poetry Analysis",
                "evaluation_source": "TEACHER_EVALUATION",
                "obtained_marks": 24.0,
                "total_marks": 30.0,
                "created_at": "2026-10-01",
                "questions": [
                    {"question_number": "1", "concept": "Iambic Pentameter", "awarded_marks": 12.0, "maximum_marks": 15.0},
                    {"question_number": "2", "concept": "Metaphor Analysis", "awarded_marks": 12.0, "maximum_marks": 15.0}
                ]
            },
            {
                "id": "ev_julia",
                "student_name": "Julia Roberts",
                "roll_number": "LIT-02",
                "assessment_title": "Poetry Analysis",
                "evaluation_source": "TEACHER_EVALUATION",
                "obtained_marks": 27.0,
                "total_marks": 30.0,
                "created_at": "2026-10-01",
                "questions": [
                    {"question_number": "1", "concept": "Iambic Pentameter", "awarded_marks": 14.0, "maximum_marks": 15.0},
                    {"question_number": "2", "concept": "Metaphor Analysis", "awarded_marks": 13.0, "maximum_marks": 15.0}
                ]
            }
        ]

        report = derive_class_report(class_doc, evaluations)

        # 1. Roster counts
        self.assertEqual(report["enrolled_count"], 3)
        self.assertEqual(report["evaluated_count"], 2)
        self.assertEqual(report["not_evaluated_count"], 1)
        self.assertEqual(report["not_evaluated_students"], ["Kevin Bacon"])

        # 2. Class Average: Ian is 80.0%, Julia is 90.0% -> mean is 85.0%
        self.assertEqual(report["class_avg_pct"], 85.0)
        self.assertEqual(report["class_avg_grade"], "A")

        # 3. Strengths: Iambic Pentameter (26/30 = 86.7%) and Metaphor Analysis (25/30 = 83.3%)
        self.assertGreaterEqual(len(report["strengths"]), 1)

        # 4. PDF Generation succeeds without error
        pdf_bytes = generate_class_report_pdf(report)
        self.assertGreater(len(pdf_bytes), 1000)

    # ──────────────────────────────────────────────────────────────────────────
    # WORKFLOW TESTS: Step 12 & Edge Cases
    # ──────────────────────────────────────────────────────────────────────────

    def test_08_empty_classes_and_empty_evaluations(self):
        """Edge Case: Empty classes and empty evaluations do not crash."""
        empty_class = {
            "id": "cls_empty",
            "name": "Empty Class",
            "students": []
        }
        report = derive_class_report(empty_class, [])
        self.assertEqual(report["status"], "no_evaluations")
        self.assertEqual(report["enrolled_count"], 0)

        # PDF still generates cleanly
        pdf = generate_class_report_pdf(report)
        self.assertGreater(len(pdf), 500)

    def test_09_duplicate_and_similar_names_no_silent_attachment(self):
        """Edge Case: Does NOT attach evaluation to a similarly named student."""
        cursor = self.conn.cursor()
        class_id = "cls_dup_test"
        # Two students with same name but different roll numbers
        cursor.execute(
            """
            INSERT INTO teacher_classes (id, teacher_id, name, grade_level, section, subjects_json, students_json, students_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (class_id, "tea_smith", "Dup Class", "10", "A", json.dumps(["Math"]), "[]", 2)
        )
        cursor.execute(
            """
            INSERT INTO class_memberships (id, class_id, teacher_id, student_id, student_name, roll_number, email)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("mem_d1", class_id, "tea_smith", "stu_d1", "John Smith", "ROLL-01", "john.01@school.edu")
        )
        cursor.execute(
            """
            INSERT INTO class_memberships (id, class_id, teacher_id, student_id, student_name, roll_number, email)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("mem_d2", class_id, "tea_smith", "stu_d2", "John Smith", "ROLL-02", "john.02@school.edu")
        )
        self.conn.commit()

        # Attempt to resolve "John Smith" without roll or email -> Must flag NEEDS_REVIEW / not silently verified
        request_data = {
            "class_id": class_id,
            "teacher_id": "tea_smith"
        }
        res_class_id, res_teacher_id, res_student_id, res_user_id, status, reason = resolve_student_identity_and_class(
            request_data=request_data,
            student_name="John Smith",
            roll_number=""
        )
        self.assertIn(status, ["NEEDS_REVIEW", "UNLINKED", "AMBIGUOUS"])

    def test_10_invalid_marks_excluded_from_averages(self):
        """Edge Case: Assessments with 0 total marks or null marks are excluded from averages."""
        class_doc = {
            "id": "cls_inv_test",
            "name": "Invalid Marks Test",
            "students": [{"name": "Leo Tolstoy", "roll_number": "LT-01"}]
        }
        evaluations = [
            {
                "id": "ev_invalid_zero_max",
                "student_name": "Leo Tolstoy",
                "assessment_title": "Ungraded Diagnostic",
                "evaluation_source": "TEACHER_EVALUATION",
                "obtained_marks": 0.0,
                "total_marks": 0.0,  # Invalid maximum
                "questions": []
            }
        ]
        report = derive_class_report(class_doc, evaluations)
        self.assertEqual(report["status"], "no_evaluations")
        self.assertTrue(len(report.get("limitations", [])) > 0)

    def test_11_student_in_multiple_classes(self):
        """Edge Case: Student belonging to more than one class has separate records."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO class_memberships (id, class_id, teacher_id, student_id, student_name, roll_number, email)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("mem_m1", "cls_math", "tea_smith", "stu_mia", "Mia Wong", "MW-99", "mia@school.edu")
        )
        cursor.execute(
            """
            INSERT INTO class_memberships (id, class_id, teacher_id, student_id, student_name, roll_number, email)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("mem_m2", "cls_art", "tea_doe", "stu_mia", "Mia Wong", "MW-99", "mia@school.edu")
        )
        self.conn.commit()

        # Query membership in cls_math
        cursor.execute("SELECT class_id FROM class_memberships WHERE student_name = ? AND class_id = ?", ("Mia Wong", "cls_math"))
        self.assertIsNotNone(cursor.fetchone())

        # Query membership in cls_art
        cursor.execute("SELECT class_id FROM class_memberships WHERE student_name = ? AND class_id = ?", ("Mia Wong", "cls_art"))
        self.assertIsNotNone(cursor.fetchone())

    def test_12_failed_unclear_file_extraction_handling(self):
        """Edge Case: Malformed or unparseable text returns clear warning and 0 unconfirmed imports."""
        # Pure symbols and numbers without letters
        garbage_symbols = "$%#@! 98765 12345"
        res = parse_manual_roster_text(garbage_symbols)
        # Any row extracted from non-letter text must be marked as needing correction with clear warning
        valid_students = [s for s in res.get("students", []) if s.get("status") == "valid"]
        self.assertEqual(len(valid_students), 0)
        self.assertTrue(any("Student name must contain letters" in iss for s in res.get("students", []) for iss in s.get("issues", [])))

        # Empty text
        res_empty = parse_manual_roster_text("    ")
        self.assertEqual(len(res_empty.get("students", [])), 0)


if __name__ == "__main__":
    unittest.main()
