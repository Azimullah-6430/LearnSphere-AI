"""
LearnSphere AI - End-to-End Evaluation Isolation & Provenance Regression Suite

This test suite executes the complete regression testing requirements:
- TEST A: Student evaluation submission, persistence, analytics visibility, and strict exclusion from teacher features.
- TEST B: Teacher evaluation grading, TEACHER_EVALUATION provenance, Misconception Map ingestion, and Action Center derivation.
- TEST C: User and Cross-Role Isolation (Student A vs Student B, Teacher A vs Teacher B, ID tampering / unauthorized access prevention).
- TEST D: Existing and legacy records preservation, UNKNOWN/NEEDS_REVIEW exclusion, and migration idempotency.
- TEST E: Auxiliary views, summary counts, roster metrics, dashboard analytics, and secure PDF export authorization.
"""

import io
import json
import unittest
import uuid
from datetime import datetime

from server import app
from app.db import get_mongodb, get_sqlite_db
from app.evaluation.store import store_evaluation_pipeline
from app.evaluation.repair import run_safe_evaluation_repair


class TestE2EEvaluationIsolation(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.uid_prefix = f"e2e_{uuid.uuid4().hex[:6]}"
        self.password = "SecurePass123!"

    def tearDown(self):
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["users"].delete_many({"email": {"$regex": f"^{self.uid_prefix}"}})
            mongo_db["evaluations"].delete_many({"assessment_title": {"$regex": f"^{self.uid_prefix}"}})
            mongo_db["misconceptions"].delete_many({"topic": {"$regex": f"^{self.uid_prefix}"}})
            mongo_db["action_items"].delete_many({"topic": {"$regex": f"^{self.uid_prefix}"}})

    def _create_authenticated_client(self, name: str, role: str):
        client = app.test_client()
        client.testing = True
        u_id = f"{self.uid_prefix}_{uuid.uuid4().hex[:6]}"
        email = f"{u_id}@e2e-test.edu"

        reg_res = client.post("/api/auth/register", json={
            "name": name,
            "email": email,
            "password": self.password,
            "role": role,
            "level": "school",
            "classLevel": "Class 10",
        })
        self.assertEqual(reg_res.status_code, 201, f"Failed to register user {name}: {reg_res.get_json()}")
        user_id = reg_res.get_json()["user"]["id"]

        login_res = client.post("/api/auth/login", json={
            "email": email,
            "password": self.password,
            "role": role,
        })
        self.assertEqual(login_res.status_code, 200, f"Failed to login user {name}: {login_res.get_json()}")

        return client, user_id, email

    # ══════════════════════════════════════════════════════════════════════════
    # TEST A — Student Evaluation
    # ══════════════════════════════════════════════════════════════════════════
    def test_A_student_evaluation_flow_and_teacher_exclusion(self):
        # 1. Log in as a student
        student_client, student_id, student_email = self._create_authenticated_client("Alice Student", "student")
        teacher_client, teacher_id, _ = self._create_authenticated_client("Prof. Snape", "teacher")

        # 2. Submit a Self Evaluation
        assessment_title = f"{self.uid_prefix} Student Self Eval - Mechanics"
        eval_payload = {
            "evaluation_source": "STUDENT_SELF_EVALUATION",
            "student_id": student_id,
            "student_name": "Alice Student",
            "roll_number": "R-101",
            "subject": "Physics",
            "assessment_title": assessment_title,
        }
        eval_result = {
            "total_marks": 50.0,
            "obtained_marks": 25.0,
            "percentage": 50.0,
            "grade": "C",
            "overall_feedback": "Good attempt at physics questions.",
            "evaluations": [
                {
                    "question_number": "1",
                    "question_text": "Define Acceleration",
                    "student_answer": "Rate of change of position",
                    "maximum_marks": 10.0,
                    "awarded_marks": 3.0,
                    "misconception_detected": True,
                    "conceptual_mistake": "Confuses velocity with acceleration",
                    "missing_points": ["Must mention rate of change of velocity"],
                    "attempted": True,
                },
                {
                    "question_number": "2",
                    "question_text": "F = ma calculations",
                    "student_answer": "F = 10 * 2 = 20N",
                    "maximum_marks": 40.0,
                    "awarded_marks": 22.0,
                    "attempted": True,
                }
            ]
        }

        eval_id = store_evaluation_pipeline(
            request_data=eval_payload,
            eval_result=eval_result,
        )
        self.assertTrue(eval_id)

        # 3. Verify the result is saved in MongoDB / DB with STUDENT_SELF_EVALUATION
        mongo_db = get_mongodb()
        if mongo_db is not None:
            doc = mongo_db["evaluations"].find_one({"assessment_title": assessment_title})
            self.assertIsNotNone(doc)
            self.assertEqual(doc.get("evaluation_source"), "STUDENT_SELF_EVALUATION")
            self.assertEqual(doc.get("student_id"), student_id)
            self.assertEqual(doc.get("created_by_role"), "student")
        else:
            conn = get_sqlite_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM evaluations WHERE assessment_title = ?", (assessment_title,))
            row = dict(cur.fetchone())
            self.assertEqual(row.get("evaluation_source"), "STUDENT_SELF_EVALUATION")
            self.assertEqual(row.get("student_id"), student_id)
            conn.close()

        # 4. Verify it appears in that student's Student Analytics and evaluation history
        res_history = student_client.get("/api/evaluations")
        self.assertEqual(res_history.status_code, 200)
        eval_list = res_history.get_json().get("evaluations", [])
        self.assertTrue(any(e.get("assessment_title") == assessment_title for e in eval_list))

        res_analytics = student_client.get("/api/analytics/student")
        self.assertEqual(res_analytics.status_code, 200)
        student_stats = res_analytics.get_json()
        self.assertGreaterEqual(student_stats.get("total_evaluations", 0), 1)

        # 5. Verify it does NOT appear in Teacher Portal Misconception Map
        res_teacher_misc = teacher_client.get("/api/misconceptions")
        self.assertEqual(res_teacher_misc.status_code, 200)
        teacher_miscs = res_teacher_misc.get_json().get("misconceptions", [])
        for m in teacher_miscs:
            self.assertNotEqual(m.get("student_id"), student_id, "Student self-eval leaked into teacher Misconception Map!")
            self.assertNotEqual(m.get("concept"), "Confuses velocity with acceleration")

        # 6. Verify it does NOT appear in Teacher Portal Action Center
        res_teacher_act = teacher_client.get("/api/action-center")
        self.assertEqual(res_teacher_act.status_code, 200)
        teacher_acts = res_teacher_act.get_json().get("action_items", [])
        for a in teacher_acts:
            self.assertNotEqual(a.get("student_id"), student_id, "Student self-eval created item in teacher Action Center!")

    # ══════════════════════════════════════════════════════════════════════════
    # TEST B — Teacher Evaluation
    # ══════════════════════════════════════════════════════════════════════════
    def test_B_teacher_evaluation_flow_and_action_center_derivation(self):
        # 1. Log in as an authorized teacher
        teacher_client, teacher_id, _ = self._create_authenticated_client("Prof. McGonagall", "teacher")
        _, student_id, _ = self._create_authenticated_client("Bob Student", "student")

        # 2. Evaluate a student's answer script as teacher
        assessment_title = f"{self.uid_prefix} Midterm Formal Exam"
        eval_payload = {
            "evaluation_source": "TEACHER_EVALUATION",
            "teacher_id": teacher_id,
            "created_by_user_id": teacher_id,
            "created_by_role": "teacher",
            "submitter_role": "teacher",
            "student_id": student_id,
            "student_name": "Bob Student",
            "class_id": "Class 10A",
            "subject": "Mathematics",
            "assessment_title": assessment_title,
        }
        eval_result = {
            "total_marks": 100.0,
            "obtained_marks": 65.0,  # Lost 35 marks (> 20 marks lost!)
            "percentage": 65.0,
            "grade": "B",
            "overall_feedback": "Needs work on quadratic equations.",
            "evaluations": [
                {
                    "question_number": "Q1",
                    "question_text": "Derive Quadratic Formula",
                    "student_answer": "x = (-b +- sqrt(b^2 - 4ac))/2",
                    "maximum_marks": 50.0,
                    "awarded_marks": 15.0,  # Lost 35 marks
                    "misconception_detected": True,
                    "conceptual_mistake": "Denominator missing factor 2a",
                    "missing_points": ["Forgot 2a in denominator"],
                    "attempted": True,
                }
            ]
        }

        eval_id = store_evaluation_pipeline(
            request_data=eval_payload,
            eval_result=eval_result,
        )
        self.assertTrue(eval_id)

        # 3. Verify the result is saved as TEACHER_EVALUATION
        mongo_db = get_mongodb()
        if mongo_db is not None:
            doc = mongo_db["evaluations"].find_one({"assessment_title": assessment_title})
            self.assertIsNotNone(doc)
            self.assertEqual(doc.get("evaluation_source"), "TEACHER_EVALUATION")
            self.assertEqual(doc.get("teacher_id"), teacher_id)
            self.assertEqual(doc.get("created_by_role"), "teacher")
            self.assertEqual(doc.get("class_id"), "Class 10A")

        # 4. Verify evidence-supported misconceptions appear in Misconception Map for this teacher
        res_misc = teacher_client.get("/api/misconceptions?class_id=Class 10A")
        self.assertEqual(res_misc.status_code, 200)
        misc_list = res_misc.get_json().get("misconceptions", [])
        matching_misc = [m for m in misc_list if m.get("concept") == "Denominator missing factor 2a"]
        self.assertTrue(len(matching_misc) >= 1)
        self.assertEqual(matching_misc[0].get("evaluation_source"), "TEACHER_EVALUATION")
        self.assertEqual(matching_misc[0].get("teacher_id"), teacher_id)

        # 5. Verify valid teacher-side learning gaps created Action Center items
        res_act = teacher_client.get("/api/action-center?class_id=Class 10A")
        self.assertEqual(res_act.status_code, 200)
        act_items = res_act.get_json().get("action_items", [])
        loss_items = [a for a in act_items if a.get("student_id") == student_id]
        self.assertTrue(len(loss_items) >= 1)

        # 6. Verify all items trace back to the correct source evaluation
        for item in loss_items:
            self.assertEqual(item.get("evaluation_source"), "TEACHER_EVALUATION")
            self.assertEqual(item.get("teacher_id"), teacher_id)
            self.assertEqual(str(item.get("evaluation_id")), str(eval_id))
            self.assertGreaterEqual(float(item.get("marks_lost", 0)), 20.0)

    # ══════════════════════════════════════════════════════════════════════════
    # TEST C — User & Cross-Role Isolation
    # ══════════════════════════════════════════════════════════════════════════
    def test_C_cross_user_and_cross_teacher_isolation(self):
        student_a, student_a_id, _ = self._create_authenticated_client("Student A", "student")
        student_b, student_b_id, _ = self._create_authenticated_client("Student B", "student")

        teacher_a, teacher_a_id, _ = self._create_authenticated_client("Teacher Alpha", "teacher")
        teacher_b, teacher_b_id, _ = self._create_authenticated_client("Teacher Beta", "teacher")

        # 1. Create evaluation for Student A
        eval_id_a = store_evaluation_pipeline(
            request_data={
                "evaluation_source": "STUDENT_SELF_EVALUATION",
                "student_id": student_a_id,
                "student_name": "Student A",
                "subject": "Chemistry",
                "assessment_title": f"{self.uid_prefix} Chem Self Test A",
            },
            eval_result={"total_marks": 100, "obtained_marks": 90, "evaluations": []}
        )

        # 2. Student B must NOT access Student A's evaluations
        res_b_list = student_b.get("/api/evaluations")
        self.assertEqual(res_b_list.status_code, 200)
        self.assertEqual(len(res_b_list.get_json().get("evaluations", [])), 0)

        # Direct access to Student A's evaluation ID via URL must return 403 Forbidden
        res_b_detail = student_b.get(f"/api/evaluations/{eval_id_a}")
        self.assertEqual(res_b_detail.status_code, 403)

        # Direct PDF export access via URL must return 403 Forbidden
        res_b_pdf = student_b.get(f"/api/evaluations/{eval_id_a}/pdf")
        self.assertEqual(res_b_pdf.status_code, 403)

        # 3. Create Teacher Evaluation under Teacher A
        eval_id_teach_a = store_evaluation_pipeline(
            request_data={
                "evaluation_source": "TEACHER_EVALUATION",
                "teacher_id": teacher_a_id,
                "created_by_user_id": teacher_a_id,
                "created_by_role": "teacher",
                "submitter_role": "teacher",
                "student_id": student_a_id,
                "student_name": "Student A",
                "class_id": "Class Alpha",
                "subject": "History",
                "assessment_title": f"{self.uid_prefix} History Alpha Exam",
            },
            eval_result={"total_marks": 100, "obtained_marks": 75, "evaluations": []}
        )

        # Teacher B must NOT access Teacher A's evaluation
        res_teach_b_detail = teacher_b.get(f"/api/evaluations/{eval_id_teach_a}")
        self.assertEqual(res_teach_b_detail.status_code, 403)

        res_teach_b_pdf = teacher_b.get(f"/api/evaluations/{eval_id_teach_a}/pdf")
        self.assertEqual(res_teach_b_pdf.status_code, 403)

        # Teacher A CAN access their own evaluation and PDF
        res_teach_a_detail = teacher_a.get(f"/api/evaluations/{eval_id_teach_a}")
        self.assertEqual(res_teach_a_detail.status_code, 200)

        res_teach_a_pdf = teacher_a.get(f"/api/evaluations/{eval_id_teach_a}/pdf")
        self.assertEqual(res_teach_a_pdf.status_code, 200)
        self.assertEqual(res_teach_a_pdf.headers.get("Content-Type"), "application/pdf")

    # ══════════════════════════════════════════════════════════════════════════
    # TEST D — Existing Records & Migration Safety
    # ══════════════════════════════════════════════════════════════════════════
    def test_D_existing_records_preservation_and_migration_safety(self):
        teacher_client, teacher_id, _ = self._create_authenticated_client("Prof. Flitwick", "teacher")
        student_client, student_id, _ = self._create_authenticated_client("Cedric Diggory", "student")

        # Seed unclassified / legacy records
        mongo_db = get_mongodb()
        title_legacy_student = f"{self.uid_prefix} Legacy Student Doc"
        title_ambiguous = f"{self.uid_prefix} Legacy Ambiguous Doc"

        if mongo_db is not None:
            # Verified student legacy record
            mongo_db["evaluations"].insert_one({
                "assessment_title": title_legacy_student,
                "subject": "Charms",
                "student_name": "Cedric Diggory",
                "student_id": student_id,
                "created_by_user_id": student_id,
                "submitter_role": "student",
                "total_marks": 100,
                "obtained_marks": 95,
                "percentage": 95.0,
                "grade": "A",
                "evaluation_source": None,
            })
            # Ambiguous record with no verifiable teacher or creator
            mongo_db["evaluations"].insert_one({
                "assessment_title": title_ambiguous,
                "subject": "Astronomy",
                "student_name": "Mystery Pupil",
                "student_id": "ghost_id_999",
                "teacher_id": "fake_teacher_999",
                "total_marks": 100,
                "obtained_marks": 60,
                "percentage": 60.0,
                "grade": "C",
                "evaluation_source": None,
            })

        # Run Migration / Repair Procedure
        repair_res = run_safe_evaluation_repair(dry_run=False, backup=True)
        self.assertTrue(len(repair_res.get("backups_created", {})) > 0)

        # Verify legitimate student history is preserved
        res_student = student_client.get("/api/evaluations")
        self.assertEqual(res_student.status_code, 200)
        s_evals = res_student.get_json().get("evaluations", [])
        self.assertTrue(any(e.get("assessment_title") == title_legacy_student for e in s_evals))

        # Verify ambiguous record is NOT in teacher's evaluations list
        res_teacher = teacher_client.get("/api/evaluations")
        self.assertEqual(res_teacher.status_code, 200)
        t_evals = res_teacher.get_json().get("evaluations", [])
        self.assertFalse(any(e.get("assessment_title") == title_ambiguous for e in t_evals))

        # Verify migration is safe to rerun (idempotent)
        rerun_res = run_safe_evaluation_repair(dry_run=False, backup=True)
        self.assertGreaterEqual(rerun_res["evaluations"]["skipped_already_valid"], 1)

    # ══════════════════════════════════════════════════════════════════════════
    # TEST E — Other Views & Metrics Scoping
    # ══════════════════════════════════════════════════════════════════════════
    def test_E_other_views_counts_charts_and_roster(self):
        teacher_client, teacher_id, _ = self._create_authenticated_client("Prof. Sprout", "teacher")
        student_client, student_id, _ = self._create_authenticated_client("Neville Longbottom", "student")

        # 1. Create a Student Self Evaluation (Score = 30%)
        store_evaluation_pipeline(
            request_data={
                "evaluation_source": "STUDENT_SELF_EVALUATION",
                "student_id": student_id,
                "student_name": "Neville Longbottom",
                "subject": "Herbology",
                "assessment_title": f"{self.uid_prefix} Herbology Self Quiz",
            },
            eval_result={"total_marks": 100, "obtained_marks": 30, "evaluations": []}
        )

        # 2. Create an Official Teacher Evaluation (Score = 90%)
        store_evaluation_pipeline(
            request_data={
                "evaluation_source": "TEACHER_EVALUATION",
                "teacher_id": teacher_id,
                "created_by_user_id": teacher_id,
                "created_by_role": "teacher",
                "submitter_role": "teacher",
                "student_id": student_id,
                "student_name": "Neville Longbottom",
                "class_id": "Class Greenhouse",
                "subject": "Herbology",
                "assessment_title": f"{self.uid_prefix} Herbology Official Practical",
            },
            eval_result={"total_marks": 100, "obtained_marks": 90, "evaluations": []}
        )

        # 3. Check Teacher Students Roster: Must calculate performance average strictly from TEACHER_EVALUATION (90%), NOT Self Evaluation (30%)
        res_roster = teacher_client.get("/api/students")
        self.assertEqual(res_roster.status_code, 200)
        students = res_roster.get_json().get("students", [])
        neville_rec = next((s for s in students if s.get("student_id") == student_id or s.get("id") == student_id or s.get("name") == "Neville Longbottom"), None)
        self.assertIsNotNone(neville_rec)
        self.assertEqual(neville_rec.get("averageScore", neville_rec.get("average")), 90.0)
        self.assertEqual(neville_rec.get("evaluations"), 1)

        # 4. Check Teacher Dashboard Analytics: Must only count TEACHER_EVALUATION
        res_dash = teacher_client.get("/api/analytics/dashboard")
        self.assertEqual(res_dash.status_code, 200)
        dash_data = res_dash.get_json()
        self.assertEqual(dash_data.get("role"), "teacher")
        self.assertEqual(dash_data.get("total_evaluations"), 1)


if __name__ == "__main__":
    unittest.main()
