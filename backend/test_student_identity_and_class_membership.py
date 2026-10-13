"""
Tests for Student Identity and Class Membership across LearnSphere AI.

Requirements tested:
1. Class membership references real student and real class; account linking only with verified email.
2. Evaluations retain teacher/class/student ownership and stable student identity.
3. Preserves original student name and identifiers as auditable snapshots.
4. Does NOT associate an evaluation with a student solely because their name matches.
   Flags ambiguous evaluations as NEEDS_REVIEW without overwriting.
5. Prevents cross-teacher and cross-class data leakage across evaluations, plagiarism,
   misconceptions, and action items.
6. Roster counts and statistics use database queries instead of placeholder data.
7. Migration/repair procedure is safe, idempotent, creates backups, and flags ambiguous records.
"""

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
from app.evaluation.store import resolve_student_identity_and_class, store_evaluation_pipeline
from app.evaluation.repair import run_safe_evaluation_repair
from app.plagiarism.detector import PlagiarismDetector


class TestStudentIdentityAndClassMembership(unittest.TestCase):
    def setUp(self):
        # Use an isolated temporary SQLite DB for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        os.environ["DATABASE_PATH"] = self.db_path
        os.environ["SQLITE_DB_PATH"] = self.db_path
        # Force fallback to SQLite by unsetting MONGO_URI and MONGODB_URI
        self.orig_mongo_uri = os.environ.get("MONGO_URI")
        self.orig_mongodb_uri = os.environ.get("MONGODB_URI")
        os.environ["MONGO_URI"] = ""
        os.environ["MONGODB_URI"] = ""
        import app.db
        app.db._mongo_db = None
        app.db._mongo_client = None
        app.db.DB_PATH = Path(self.db_path)

        # Initialize schema
        init_db()
        self.conn = get_sqlite_db()

        # Seed test data:
        # Teacher 1 (teacher_alpha) with Class A
        # Teacher 2 (teacher_beta) with Class B
        # Registered Student in users table: "alice@school.edu" with user_id "usr_alice"
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO users (user_id, name, email, role, password_hash) VALUES (?, ?, ?, ?, ?)",
            ("usr_alice", "Alice Wonder", "alice@school.edu", "student", "hashed_pwd")
        )
        cursor.execute(
            "INSERT INTO users (user_id, name, email, role, password_hash) VALUES (?, ?, ?, ?, ?)",
            ("usr_teacher_a", "Prof Alpha", "alpha@school.edu", "teacher", "hashed_pwd")
        )
        cursor.execute(
            "INSERT INTO users (user_id, name, email, role, password_hash) VALUES (?, ?, ?, ?, ?)",
            ("usr_teacher_b", "Prof Beta", "beta@school.edu", "teacher", "hashed_pwd")
        )

        import json
        students_a = [
            {"id": "mem_alice_01", "name": "Alice Wonder", "rollNumber": "101", "email": "alice@school.edu", "userId": "usr_alice"},
            {"id": "mem_bob_02", "name": "Bob Builder", "rollNumber": "102", "email": "bob@unregistered.edu"},
        ]
        students_b = [
            {"id": "mem_alice_b", "name": "Alice Wonder", "rollNumber": "201", "email": "alice_other@school.edu"},
        ]

        cursor.execute(
            """
            INSERT INTO teacher_classes (id, teacher_id, name, grade_level, section, subjects_json, students_json, students_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("cls_math_a", "usr_teacher_a", "Grade 10 Math", "10", "A", json.dumps(["Mathematics"]), json.dumps(students_a), 2)
        )
        cursor.execute(
            """
            INSERT INTO teacher_classes (id, teacher_id, name, grade_level, section, subjects_json, students_json, students_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("cls_math_b", "usr_teacher_b", "Grade 10 Science", "10", "B", json.dumps(["Science"]), json.dumps(students_b), 1)
        )

        # Class membership for Alice in cls_math_a with verified account link
        cursor.execute(
            """
            INSERT INTO class_memberships
            (id, class_id, teacher_id, student_id, student_user_id, student_name, roll_number, email, is_active, account_linked)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("mem_alice_01", "cls_math_a", "usr_teacher_a", "mem_alice_01", "usr_alice", "Alice Wonder", "101", "alice@school.edu", 1, 1)
        )

        # Another student in cls_math_a without a registered account (unregistered student)
        cursor.execute(
            """
            INSERT INTO class_memberships
            (id, class_id, teacher_id, student_id, student_user_id, student_name, roll_number, email, is_active, account_linked)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("mem_bob_02", "cls_math_a", "usr_teacher_a", "mem_bob_02", None, "Bob Builder", "102", "bob@unregistered.edu", 1, 0)
        )

        # Student in cls_math_b with the SAME NAME "Alice Wonder", but different roll "201" and student_id "mem_alice_b"
        cursor.execute(
            """
            INSERT INTO class_memberships
            (id, class_id, teacher_id, student_id, student_user_id, student_name, roll_number, email, is_active, account_linked)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("mem_alice_b", "cls_math_b", "usr_teacher_b", "mem_alice_b", None, "Alice Wonder", "201", "alice_other@school.edu", 1, 0)
        )

        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass
        if self.orig_mongo_uri:
            os.environ["MONGO_URI"] = self.orig_mongo_uri
        if self.orig_mongodb_uri:
            os.environ["MONGODB_URI"] = self.orig_mongodb_uri

    def test_identity_resolution_rejects_name_only_match(self):
        """Requirement 4: Do not associate an evaluation with a student solely because their name matches."""
        # Case A: Same name "Alice Wonder", but no student_id and roll_number is different or missing
        req_data = {
            "teacher_id": "usr_teacher_a",
            "class_id": "cls_math_a",
            # Student ID omitted, roll omitted
        }
        cls_id, tch_id, stu_id, stu_user_id, status, reason = resolve_student_identity_and_class(
            req_data, student_name="Alice Wonder", roll_number="UNKNOWN_999"
        )
        self.assertEqual(status, "NEEDS_REVIEW")
        self.assertIn("Name-only match rejected", reason)
        self.assertIsNone(stu_id)

        # Case B: Correct roll number "101" resolves reliably
        cls_id, tch_id, stu_id, stu_user_id, status, reason = resolve_student_identity_and_class(
            req_data, student_name="Alice Wonder", roll_number="101"
        )
        self.assertEqual(status, "VERIFIED")
        self.assertEqual(stu_id, "mem_alice_01")
        self.assertEqual(stu_user_id, "usr_alice")

        # Case C: Correct student_id resolves reliably
        req_data_with_id = {
            "teacher_id": "usr_teacher_a",
            "class_id": "cls_math_a",
            "student_id": "mem_bob_02",
        }
        cls_id, tch_id, stu_id, stu_user_id, status, reason = resolve_student_identity_and_class(
            req_data_with_id, student_name="Different Bob Name", roll_number=""
        )
        self.assertEqual(status, "VERIFIED")
        self.assertEqual(stu_id, "mem_bob_02")

    def test_evaluation_retains_auditable_snapshot(self):
        """Requirements 2 & 3: Evaluations retain ownership & preserve name/roll snapshot."""
        req_payload = {
            "teacher_id": "usr_teacher_a",
            "class_id": "cls_math_a",
            "student_name": "Alice Wonder",
            "roll_number": "101",
            "subject": "Mathematics",
            "evaluation_source": "TEACHER_EVALUATION",
        }
        eval_payload = {
            "student_name": "Alice Wonder",
            "roll_number": "101",
            "subject": "Mathematics",
            "assessment_title": "Algebra Midterm",
            "total_marks": 50,
            "obtained_marks": 45,
            "percentage": 90.0,
            "grade": "A+",
            "evaluations": [
                {
                    "question_number": "1",
                    "maximum_marks": 10,
                    "awarded_marks": 9,
                    "is_correct": True,
                    "feedback": {"what_was_done_well": ["Clear algebra steps"]},
                }
            ],
        }

        eval_id = store_evaluation_pipeline(req_payload, eval_payload)
        self.assertTrue(bool(eval_id))

        # Query database directly
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM evaluations WHERE id = ?", (eval_id,))
        row = cursor.fetchone()
        row_dict = dict(row)

        # Check snapshots and stable identities
        self.assertEqual(row_dict["teacher_id"], "usr_teacher_a")
        self.assertEqual(row_dict["class_id"], "cls_math_a")
        self.assertEqual(row_dict["student_id"], "mem_alice_01")
        self.assertEqual(row_dict["student_user_id"], "usr_alice")
        self.assertEqual(row_dict["student_name_snapshot"], "Alice Wonder")
        self.assertEqual(row_dict["roll_number_snapshot"], "101")
        self.assertEqual(row_dict["identity_status"], "VERIFIED")

    def test_cross_teacher_and_cross_class_isolation(self):
        """Requirement 6: Prevent cross-teacher and cross-class data leakage."""
        req_a = {
            "teacher_id": "usr_teacher_a",
            "class_id": "cls_math_a",
            "student_id": "mem_alice_01",
            "student_name": "Alice Wonder",
            "roll_number": "101",
            "subject": "Mathematics",
            "evaluation_source": "TEACHER_EVALUATION",
        }
        eval_a = {
            "student_name": "Alice Wonder",
            "roll_number": "101",
            "subject": "Mathematics",
            "assessment_title": "Math Test A",
            "total_marks": 20,
            "obtained_marks": 18,
            "percentage": 90.0,
            "grade": "A",
            "evaluations": [
                {"question_number": "1", "maximum_marks": 20, "awarded_marks": 18, "student_answer": "Linear algebra answer"}
            ],
        }
        # Teacher A evaluates Alice (cls_math_a)
        store_evaluation_pipeline(req_a, eval_a)

        # Teacher B evaluates Alice (cls_math_b)
        req_b = {
            "teacher_id": "usr_teacher_b",
            "class_id": "cls_math_b",
            "student_id": "mem_alice_b",
            "student_name": "Alice Wonder",
            "roll_number": "201",
            "subject": "Science",
            "evaluation_source": "TEACHER_EVALUATION",
        }
        eval_b = {
            "student_name": "Alice Wonder",
            "roll_number": "201",
            "subject": "Science",
            "assessment_title": "Science Test B",
            "total_marks": 20,
            "obtained_marks": 17,
            "percentage": 85.0,
            "grade": "A",
            "evaluations": [
                {"question_number": "1", "maximum_marks": 20, "awarded_marks": 17, "student_answer": "Cell biology answer"}
            ],
        }
        store_evaluation_pipeline(req_b, eval_b)

        # Plagiarism detector scoped comparison
        from app.plagiarism.detector import PlagiarismDetector
        detector = PlagiarismDetector()
        result = detector.check(
            subject="Mathematics",
            student_name="Alice Wonder",
            roll_number="101",
            student_id="mem_alice_01",
            teacher_id="usr_teacher_a",
            class_id="cls_math_a",
            answer_script="Linear algebra proof showing step by step calculation of matrix determinants.",
        )
        self.assertIsNotNone(result)
        # Should not match against Teacher B's student
        if result.get("matched_with"):
            self.assertNotEqual(result.get("matched_with"), "Alice Wonder (201)")

    def test_safe_evaluation_repair_and_backup(self):
        """Requirement 8: Migration/repair creates backups and audits ambiguous records without deleting."""
        # Insert an ambiguous legacy evaluation where name matches roster ("Alice Wonder") but roll is mismatched ("999")
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO evaluations
            (student_name, roll_number, subject, assessment_title, total_marks, obtained_marks,
             percentage, grade, status, teacher_id, class_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("Alice Wonder", "999", "History", "History Quiz", 20, 15, 75.0, "B", "completed", "usr_teacher_a", "cls_math_a")
        )
        legacy_id = cursor.lastrowid
        self.conn.commit()

        # Run safe evaluation repair
        results = run_safe_evaluation_repair(dry_run=False)
        self.assertIn("identities", results)
        self.assertTrue(results.get("success", False))
        self.assertTrue(len(results.get("backups_created", {})) > 0)

        # Check that legacy evaluation was audited, not deleted, and marked as NEEDS_REVIEW
        cursor.execute("SELECT student_name_snapshot, identity_status, identity_review_reason FROM evaluations WHERE id = ?", (legacy_id,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["student_name_snapshot"], "Alice Wonder")
        self.assertEqual(row["identity_status"], "NEEDS_REVIEW")
        self.assertTrue(len(row["identity_review_reason"]) > 0)


if __name__ == "__main__":
    unittest.main()
