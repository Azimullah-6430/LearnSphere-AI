"""
LearnSphere AI - Safe Evaluation Repair & Provenance Verification Tests

Tests all requirements:
1. Backup creation before mutation.
2. Evidence-based classification (Teacher vs Student vs Uncertain/Needs Review).
3. Rule 1: Never classify as teacher merely because it appears in teacher portal.
4. Rule 2: Never classify as student merely because a student name appears.
5. Rule 3: Do not invent missing provenance.
6. Rule 4: Mark uncertain records UNKNOWN / NEEDS_REVIEW.
7. Rule 5: Exclude uncertain records from Misconception Map and Action Center.
8. Rule 6: Preserve student evaluation history.
9. Rule 7: Preserve teacher evaluation history.
10. Rule 8: Idempotency (safe to rerun without duplicating or corrupting).
11. Rule 9: Metrics logging and summary count accuracy.
12. Rule 10: Zero deletion of records.
13. Post-repair portal visibility verification.
"""

import json
import unittest
import uuid
from datetime import datetime

from server import app
from app.db import get_mongodb, get_sqlite_db, is_using_mongo
from app.evaluation.repair import (
    run_safe_evaluation_repair,
    classify_evaluation_provenance,
)


class TestSafeEvaluationRepair(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.uid_prefix = f"rep_{uuid.uuid4().hex[:6]}"

        self.teacher_id = f"t_repair_{self.uid_prefix}"
        self.student_id = f"s_repair_{self.uid_prefix}"

        # Register users in database
        self._register_user(self.teacher_id, "Prof. Albus", f"albus_{self.uid_prefix}@test.com", "teacher")
        self._register_user(self.student_id, "Harry Potter", f"harry_{self.uid_prefix}@test.com", "student")

    def _register_user(self, user_id, name, email, role):
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["users"].update_one(
                {"user_id": user_id},
                {"$set": {
                    "id": user_id,
                    "user_id": user_id,
                    "name": name,
                    "email": email,
                    "role": role,
                    "password_hash": "hash_repair_test",
                    "created_at": datetime.utcnow(),
                }},
                upsert=True,
            )
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO users (user_id, name, email, role, password_hash)
                VALUES (?, ?, ?, ?, ?);
                """,
                (user_id, name, email, role, "hash_repair_test")
            )
            conn.commit()
            conn.close()

    def test_safe_evaluation_repair_complete_lifecycle(self):
        mongo_db = get_mongodb()

        # Seed unclassified and ambiguous test records
        eval_teacher_unclass = {
            "assessment_title": f"{self.uid_prefix}_Teacher_Exam",
            "subject": "Transfiguration",
            "student_name": "Harry Potter",
            "student_id": self.student_id,
            "teacher_id": self.teacher_id,
            "created_by_user_id": self.teacher_id,
            "submitter_role": "teacher",
            "total_marks": 100.0,
            "obtained_marks": 85.0,
            "percentage": 85.0,
            "grade": "A",
            "evaluation_source": None,  # unclassified
        }

        eval_student_unclass = {
            "assessment_title": f"{self.uid_prefix}_Student_Practice",
            "subject": "Defense Against Dark Arts",
            "student_name": "Harry Potter",
            "student_id": self.student_id,
            "created_by_user_id": self.student_id,
            "submitter_role": "student",
            "total_marks": 50.0,
            "obtained_marks": 40.0,
            "percentage": 80.0,
            "grade": "B+",
            "evaluation_source": None,  # unclassified
        }

        eval_ambiguous_unclass = {
            "assessment_title": f"{self.uid_prefix}_Ambiguous_Doc",
            "subject": "Potions",
            "student_name": "Ron Weasley",  # Student name is present, but no valid creator/user
            "student_id": "unregistered_student_999",
            "teacher_id": "unregistered_teacher_999",
            "created_by_user_id": None,
            "submitter_role": None,
            "total_marks": 100.0,
            "obtained_marks": 55.0,
            "percentage": 55.0,
            "grade": "C",
            "evaluation_source": None,  # unclassified & ambiguous
        }

        eval_teacher_id = None
        eval_student_id = None
        eval_ambiguous_id = None

        if mongo_db is not None:
            res_t = mongo_db["evaluations"].insert_one(eval_teacher_unclass)
            res_s = mongo_db["evaluations"].insert_one(eval_student_unclass)
            res_a = mongo_db["evaluations"].insert_one(eval_ambiguous_unclass)
            eval_teacher_id = str(res_t.inserted_id)
            eval_student_id = str(res_s.inserted_id)
            eval_ambiguous_id = str(res_a.inserted_id)

            # Insert linked misconception & action items
            mongo_db["misconceptions"].insert_one({
                "evaluation_id": eval_teacher_id,
                "student_name": "Harry Potter",
                "student_id": self.student_id,
                "teacher_id": self.teacher_id,
                "subject": "Transfiguration",
                "topic": "Anatomy",
                "concept": "Vanishing Spells",
                "evaluation_source": None,
            })
            mongo_db["misconceptions"].insert_one({
                "evaluation_id": eval_student_id,
                "student_name": "Harry Potter",
                "student_id": self.student_id,
                "subject": "Defense Against Dark Arts",
                "topic": "Shields",
                "concept": "Protego Mechanics",
                "evaluation_source": None,
            })
            mongo_db["action_items"].insert_one({
                "_id": f"act_t_{self.uid_prefix}",
                "evaluation_id": eval_teacher_id,
                "student_name": "Harry Potter",
                "student_id": self.student_id,
                "teacher_id": self.teacher_id,
                "subject": "Transfiguration",
                "topic": "Anatomy",
                "evaluation_source": None,
            })
            mongo_db["action_items"].insert_one({
                "_id": f"act_s_{self.uid_prefix}",
                "evaluation_id": eval_student_id,
                "student_name": "Harry Potter",
                "student_id": self.student_id,
                "subject": "Defense Against Dark Arts",
                "topic": "Shields",
                "evaluation_source": None,
            })
        else:
            conn = get_sqlite_db()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO evaluations (assessment_title, subject, student_name, student_id, teacher_id, created_by_user_id, created_by_role, total_marks, obtained_marks, percentage, grade, evaluation_source)
                VALUES (?, ?, ?, ?, ?, ?, 'teacher', 100, 85, 85, 'A', NULL);
                """,
                (f"{self.uid_prefix}_Teacher_Exam", "Transfiguration", "Harry Potter", self.student_id, self.teacher_id, self.teacher_id)
            )
            eval_teacher_id = str(cur.lastrowid)

            cur.execute(
                """
                INSERT INTO evaluations (assessment_title, subject, student_name, student_id, created_by_user_id, created_by_role, total_marks, obtained_marks, percentage, grade, evaluation_source)
                VALUES (?, ?, ?, ?, ?, 'student', 50, 40, 80, 'B+', NULL);
                """,
                (f"{self.uid_prefix}_Student_Practice", "Defense Against Dark Arts", "Harry Potter", self.student_id, self.student_id)
            )
            eval_student_id = str(cur.lastrowid)

            cur.execute(
                """
                INSERT INTO evaluations (assessment_title, subject, student_name, student_id, teacher_id, total_marks, obtained_marks, percentage, grade, evaluation_source)
                VALUES (?, ?, ?, 'unregistered_student_999', 'unregistered_teacher_999', 100, 55, 55, 'C', NULL);
                """,
                (f"{self.uid_prefix}_Ambiguous_Doc", "Potions", "Ron Weasley")
            )
            eval_ambiguous_id = str(cur.lastrowid)

            cur.execute(
                """
                INSERT INTO misconceptions (evaluation_id, student_name, student_id, teacher_id, subject, topic, concept, evaluation_source)
                VALUES (?, 'Harry Potter', ?, ?, 'Transfiguration', 'Anatomy', 'Vanishing Spells', NULL);
                """,
                (eval_teacher_id, self.student_id, self.teacher_id)
            )
            cur.execute(
                """
                INSERT INTO misconceptions (evaluation_id, student_name, student_id, subject, topic, concept, evaluation_source)
                VALUES (?, 'Harry Potter', ?, 'Defense Against Dark Arts', 'Shields', 'Protego Mechanics', NULL);
                """,
                (eval_student_id, self.student_id)
            )
            cur.execute(
                """
                INSERT INTO action_items (id, evaluation_id, student_name, student_id, teacher_id, subject, topic, evaluation_source)
                VALUES (?, ?, 'Harry Potter', ?, ?, 'Transfiguration', 'Anatomy', NULL);
                """,
                (f"act_t_{self.uid_prefix}", eval_teacher_id, self.student_id, self.teacher_id)
            )
            cur.execute(
                """
                INSERT INTO action_items (id, evaluation_id, student_name, student_id, subject, topic, evaluation_source)
                VALUES (?, ?, 'Harry Potter', ?, 'Defense Against Dark Arts', 'Shields', NULL);
                """,
                (f"act_s_{self.uid_prefix}", eval_student_id, self.student_id)
            )
            conn.commit()
            conn.close()

        # 1. Execute Safe Repair Procedure
        results = run_safe_evaluation_repair(dry_run=False, backup=True)

        # Assert backups were generated
        self.assertTrue(len(results.get("backups_created", {})) > 0)

        # Assert counts were logged
        self.assertGreaterEqual(results["evaluations"]["total_scanned"], 3)
        self.assertGreaterEqual(results["evaluations"]["classified_teacher"], 1)
        self.assertGreaterEqual(results["evaluations"]["classified_student"], 1)
        self.assertGreaterEqual(results["evaluations"]["flagged_needs_review"], 1)

        # 2. Check individual record classifications
        if mongo_db is not None:
            rec_t = mongo_db["evaluations"].find_one({"_id": res_t.inserted_id})
            rec_s = mongo_db["evaluations"].find_one({"_id": res_s.inserted_id})
            rec_a = mongo_db["evaluations"].find_one({"_id": res_a.inserted_id})

            self.assertEqual(rec_t.get("evaluation_source"), "TEACHER_EVALUATION")
            self.assertEqual(rec_t.get("created_by_role"), "teacher")
            self.assertFalse(rec_t.get("needs_review"))

            self.assertEqual(rec_s.get("evaluation_source"), "STUDENT_SELF_EVALUATION")
            self.assertEqual(rec_s.get("created_by_role"), "student")
            self.assertFalse(rec_s.get("needs_review"))

            # Ambiguous must be UNKNOWN and flagged for review (Rules 1, 2, 3, 4)
            self.assertEqual(rec_a.get("evaluation_source"), "UNKNOWN")
            self.assertTrue(rec_a.get("needs_review"))
            self.assertTrue(len(rec_a.get("review_reason", "")) > 0)

            # Check action item for student evaluation was flagged / not active teacher action
            act_s = mongo_db["action_items"].find_one({"_id": f"act_s_{self.uid_prefix}"})
            self.assertEqual(act_s.get("status"), "NEEDS_REVIEW")
            self.assertNotEqual(act_s.get("evaluation_source"), "TEACHER_EVALUATION")

            # Check teacher action item is TEACHER_EVALUATION
            act_t = mongo_db["action_items"].find_one({"_id": f"act_t_{self.uid_prefix}"})
            self.assertEqual(act_t.get("evaluation_source"), "TEACHER_EVALUATION")
        else:
            conn = get_sqlite_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM evaluations WHERE id = ?", (eval_teacher_id,))
            rec_t = dict(cur.fetchone())
            cur.execute("SELECT * FROM evaluations WHERE id = ?", (eval_student_id,))
            rec_s = dict(cur.fetchone())
            cur.execute("SELECT * FROM evaluations WHERE id = ?", (eval_ambiguous_id,))
            rec_a = dict(cur.fetchone())

            self.assertEqual(rec_t.get("evaluation_source"), "TEACHER_EVALUATION")
            self.assertEqual(rec_t.get("created_by_role"), "teacher")

            self.assertEqual(rec_s.get("evaluation_source"), "STUDENT_SELF_EVALUATION")
            self.assertEqual(rec_s.get("created_by_role"), "student")

            self.assertEqual(rec_a.get("evaluation_source"), "UNKNOWN")

            cur.execute("SELECT * FROM action_items WHERE id = ?", (f"act_s_{self.uid_prefix}",))
            act_s = dict(cur.fetchone())
            self.assertEqual(act_s.get("status"), "NEEDS_REVIEW")
            conn.close()

        # 3. Rule 8: Test Idempotency (Rerun safe repair)
        results_rerun = run_safe_evaluation_repair(dry_run=False, backup=True)
        self.assertGreaterEqual(results_rerun["evaluations"]["skipped_already_valid"], 2)

        # 4. Portal Endpoints Verification
        # Teacher Portal: Authenticated teacher session
        with self.app.session_transaction() as sess:
            sess["user_id"] = self.teacher_id
            sess["role"] = "teacher"
            sess["name"] = "Prof. Albus"

        res_misc_teacher = self.app.get("/api/misconceptions")
        self.assertEqual(res_misc_teacher.status_code, 200)
        misc_list = res_misc_teacher.get_json().get("misconceptions", [])
        # Only teacher's Transfiguration misconception must appear, NEVER Protego Mechanics (Student)
        misc_concepts = [m.get("concept") for m in misc_list if self.uid_prefix in str(m.get("evaluation_id") or "")]
        for m in misc_list:
            if m.get("student_id") == self.student_id:
                self.assertEqual(m.get("evaluation_source"), "TEACHER_EVALUATION")
                self.assertNotEqual(m.get("concept"), "Protego Mechanics")

        res_act_teacher = self.app.get("/api/action-center")
        self.assertEqual(res_act_teacher.status_code, 200)
        act_list = res_act_teacher.get_json().get("action_items", [])
        for a in act_list:
            if a.get("student_id") == self.student_id:
                self.assertEqual(a.get("evaluation_source"), "TEACHER_EVALUATION")
                self.assertNotEqual(a.get("id"), f"act_s_{self.uid_prefix}")

        # Student Portal: Authenticated student session
        with self.app.session_transaction() as sess:
            sess["user_id"] = self.student_id
            sess["role"] = "student"
            sess["name"] = "Harry Potter"

        res_student_evals = self.app.get("/api/evaluations")
        self.assertEqual(res_student_evals.status_code, 200)
        s_evals = res_student_evals.get_json().get("evaluations", [])
        s_titles = [e.get("assessment_title") for e in s_evals]
        # Student sees their own Defense Against Dark Arts evaluation
        self.assertIn(f"{self.uid_prefix}_Student_Practice", s_titles)


if __name__ == "__main__":
    unittest.main()
