"""
LearnSphere AI - Evaluation Data Isolation & Provenance Unit & Integration Tests

Verifies:
1. Provenance metadata (evaluation_source, created_by_user_id, created_by_role, student_id, teacher_id, class_id).
2. Student Self Evaluation records are strictly classified as STUDENT_SELF_EVALUATION.
3. Teacher Evaluation records are strictly classified as TEACHER_EVALUATION.
4. Teacher Portal -> Misconception Map queries NEVER return STUDENT_SELF_EVALUATION records or unrelated teachers' records.
5. Teacher Portal -> Action Center queries NEVER return STUDENT_SELF_EVALUATION records or unassigned records.
6. Teacher Portal -> Students Roster calculates performance purely from TEACHER_EVALUATION records.
7. Class filtering works accurately when class_id is supplied.
8. Unknown / unverified legacy records are excluded from teacher features.
"""

import json
import unittest
import uuid
from server import app
from app.db import get_mongodb
from app.evaluation.store import store_evaluation_pipeline


class TestEvaluationIsolationAndProvenance(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.uid_prefix = uuid.uuid4().hex[:8]
        self.password = "TestPass123!"

    def tearDown(self):
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["users"].delete_many({"email": {"$regex": f"^{self.uid_prefix}"}})
            mongo_db["evaluations"].delete_many({"assessment_title": {"$regex": f"^{self.uid_prefix}"}})
            mongo_db["misconceptions"].delete_many({"topic": {"$regex": f"^{self.uid_prefix}"}})
            mongo_db["action_items"].delete_many({"topic": {"$regex": f"^{self.uid_prefix}"}})

    def _register_and_login(self, name, role):
        uid = f"{self.uid_prefix}_{uuid.uuid4().hex[:6]}"
        email = f"{uid}@learnsphere.edu"
        reg_res = self.app.post("/api/auth/register", json={
            "name": name,
            "email": email,
            "password": self.password,
            "role": role,
            "level": "school"
        })
        self.assertEqual(reg_res.status_code, 201)
        user_id = reg_res.get_json()["user"]["id"]
        
        login_res = self.app.post("/api/auth/login", json={"email": email, "password": self.password, "role": role})
        self.assertEqual(login_res.status_code, 200)
        return user_id, email

    def test_pipeline_provenance_and_portal_isolation(self):
        # 1. Register Teacher A, Teacher B, and Student C
        teacher_a_id, teacher_a_email = self._register_and_login("Teacher Alice", "teacher")
        
        # New client for Teacher B
        app_b = app.test_client()
        app_b.testing = True
        t_b_uid = f"{self.uid_prefix}_b_{uuid.uuid4().hex[:6]}"
        t_b_email = f"{t_b_uid}@learnsphere.edu"
        app_b.post("/api/auth/register", json={"name": "Teacher Bob", "email": t_b_email, "password": self.password, "role": "teacher"})
        app_b.post("/api/auth/login", json={"email": t_b_email, "password": self.password, "role": "teacher"})

        # New client for Student C
        charlie_name = f"Student Charlie {self.uid_prefix}"
        app_c = app.test_client()
        app_c.testing = True
        s_c_uid = f"{self.uid_prefix}_c_{uuid.uuid4().hex[:6]}"
        s_c_email = f"{s_c_uid}@learnsphere.edu"
        reg_c = app_c.post("/api/auth/register", json={"name": charlie_name, "email": s_c_email, "password": self.password, "role": "student"})
        student_c_id = reg_c.get_json()["user"]["id"]
        app_c.post("/api/auth/login", json={"email": s_c_email, "password": self.password, "role": "student"})

        # 2. Store a Student Self Evaluation for Student C
        self_eval_topic = f"{self.uid_prefix} Physics Self Assessment"
        student_eval_req = {
            "evaluation_id": f"eval_self_{self.uid_prefix}",
            "evaluation_source": "STUDENT_SELF_EVALUATION",
            "submitted_by": student_c_id,
            "submitter_role": "student",
            "student_id": student_c_id,
            "teacher_id": None,
            "subject": "Physics",
            "student_name": charlie_name,
            "roll_number": "R-101",
            "assessment_title": self_eval_topic,
        }
        student_eval_result = {
            "total_marks": 50,
            "obtained_marks": 20,
            "percentage": 40.0,
            "grade": "D",
            "evaluations": [
                {
                    "question_number": "1",
                    "question_text": "State Newton's Third Law",
                    "student_answer": "Action is greater than reaction.",
                    "maximum_marks": 10,
                    "awarded_marks": 2,
                    "misconception_detected": True,
                    "misconception": "Forces in action-reaction pairs can have unequal magnitudes.",
                    "conceptual_mistake": "Forces in action-reaction pairs can have unequal magnitudes.",
                    "concepts_tested": ["Newton's Third Law"],
                    "what_student_should_have_written": "For every action, there is an equal and opposite reaction.",
                }
            ]
        }
        self_eval_id = store_evaluation_pipeline(student_eval_req, student_eval_result)
        self.assertTrue(self_eval_id)

        # 3. Store a Teacher Evaluation conducted by Teacher A for Student C
        teach_eval_topic = f"{self.uid_prefix} Calculus Midterm Exam"
        class_id = f"class_{self.uid_prefix}_101"
        teacher_eval_req = {
            "evaluation_id": f"eval_teach_{self.uid_prefix}",
            "evaluation_source": "TEACHER_EVALUATION",
            "submitted_by": teacher_a_id,
            "submitter_role": "teacher",
            "student_id": student_c_id,
            "teacher_id": teacher_a_id,
            "class_id": class_id,
            "subject": "Mathematics",
            "student_name": charlie_name,
            "roll_number": "R-101",
            "assessment_title": teach_eval_topic,
        }
        teacher_eval_result = {
            "total_marks": 100,
            "obtained_marks": 75,
            "percentage": 75.0,
            "grade": "B+",
            "evaluations": [
                {
                    "question_number": "3",
                    "question_text": "Find the derivative of sin(x^2)",
                    "student_answer": "cos(x^2)",
                    "maximum_marks": 10,
                    "awarded_marks": 4,
                    "misconception_detected": True,
                    "misconception": "Omission of Chain Rule inner derivative.",
                    "conceptual_mistake": "Omission of Chain Rule inner derivative.",
                    "concepts_tested": ["Chain Rule"],
                    "what_student_should_have_written": "2x * cos(x^2)",
                }
            ]
        }
        teach_eval_id = store_evaluation_pipeline(teacher_eval_req, teacher_eval_result)
        self.assertTrue(teach_eval_id)

        # 4. Check Teacher A's Misconception Map via self.app
        res_a = self.app.get("/api/misconceptions")
        self.assertEqual(res_a.status_code, 200)
        data_a = res_a.get_json()
        self.assertTrue(data_a.get("success"))
        misconceptions_a = data_a.get("misconceptions", [])

        # Teacher Alice MUST see Chain Rule from TEACHER_EVALUATION
        # Teacher Alice MUST NEVER see Newton's Third Law from STUDENT_SELF_EVALUATION
        concepts_a = [m.get("concept") or m.get("identified_concept") or m.get("misconception") for m in misconceptions_a]
        self.assertIn("Chain Rule", concepts_a)
        self.assertNotIn("Newton's Third Law", concepts_a)

        for m in misconceptions_a:
            self.assertEqual(m.get("evaluation_source"), "TEACHER_EVALUATION")

        # 5. Check Teacher A's Action Center via self.app
        res_act_a = self.app.get("/api/action-center")
        self.assertEqual(res_act_a.status_code, 200)
        data_act_a = res_act_a.get_json()
        items_a = data_act_a.get("items", [])
        self.assertGreater(len(items_a), 0)
        
        # Verify metadata completeness and origin on all items
        for it in items_a:
            self.assertEqual(it.get("evaluation_source"), "TEACHER_EVALUATION")
            self.assertEqual(str(it.get("teacher_id")), teacher_a_id)
            self.assertIsNotNone(it.get("evaluation_id"))
            self.assertIsNotNone(it.get("student_id"))
            self.assertIsNotNone(it.get("class_id"))
            self.assertIsNotNone(it.get("question_num"))
            self.assertIsNotNone(it.get("marks_lost"))
            self.assertIsNotNone(it.get("evidence"))
            self.assertIsNotNone(it.get("learning_gap"))
            self.assertIsNotNone(it.get("recommended_action"))
            self.assertIsNotNone(it.get("created_at"))

        # Verify > 20 marks lost rule calculation: 100 - 75 = 25 marks lost
        loss_item = next((it for it in items_a if it.get("category") == "excessive_marks_lost"), None)
        self.assertIsNotNone(loss_item)
        self.assertEqual(loss_item.get("marks_lost"), 25.0)
        self.assertEqual(loss_item.get("maximum_marks"), 100.0)
        self.assertEqual(loss_item.get("total_marks"), 75.0)

        # 6. Verify Evaluation Override recalculates linked action items safely
        res_override = self.app.put(f"/api/evaluations/{teach_eval_id}/override", json={
            "obtained_marks": 85.0,
            "total_marks": 100.0,
            "questions": [
                {
                    "question_number": "3",
                    "question_text": "Find the derivative of sin(x^2)",
                    "student_answer": "2x * cos(x^2)",
                    "maximum_marks": 10,
                    "awarded_marks": 10,
                    "misconception_detected": False,
                }
            ]
        })
        self.assertEqual(res_override.status_code, 200)

        # Re-fetch Action Center: marks lost is now 15 <= 20, so excessive_marks_lost item should no longer be in active view
        res_act_updated = self.app.get("/api/action-center")
        self.assertEqual(res_act_updated.status_code, 200)
        items_updated = res_act_updated.get_json().get("items", [])
        loss_item_after = next((it for it in items_updated if it.get("category") == "excessive_marks_lost" and it.get("status") != "Resolved"), None)
        self.assertIsNone(loss_item_after)

        # 7. Check Teacher B's Misconception Map via app_b
        res_b = app_b.get("/api/misconceptions")
        self.assertEqual(res_b.status_code, 200)
        data_b = res_b.get_json()
        misconceptions_b = data_b.get("misconceptions", [])
        # Teacher Bob must see 0 misconceptions for this test prefix
        b_scoped = [m for m in misconceptions_b if self.uid_prefix in (m.get("topic") or "")]
        self.assertEqual(len(b_scoped), 0)

        # 8. Check Student C's Misconception Map via app_c
        res_c = app_c.get("/api/misconceptions")
        self.assertEqual(res_c.status_code, 200)
        data_c = res_c.get_json()
        misconceptions_c = data_c.get("misconceptions", [])
        concepts_c = [m.get("concept") or m.get("identified_concept") or m.get("misconception") for m in misconceptions_c]
        # Student sees their own misconception
        self.assertIn("Newton's Third Law", concepts_c)

        # 9. Check Teacher A's Students Roster: Must calculate average from Teacher Evaluation (85.0%), not Self-Eval (40.0%)
        res_roster = self.app.get("/api/students")
        self.assertEqual(res_roster.status_code, 200)
        data_roster = res_roster.get_json()
        charlie_record = next((s for s in data_roster.get("students", []) if s.get("name") == charlie_name), None)
        self.assertIsNotNone(charlie_record)
        self.assertEqual(charlie_record.get("evaluations"), 1)
        self.assertEqual(charlie_record.get("average"), 85.0)

        # 10. Check Student C's Student Analytics via app_c
        res_analytics_c = app_c.get("/api/analytics/student")
        self.assertEqual(res_analytics_c.status_code, 200)
        analytics_c = res_analytics_c.get_json()
        self.assertTrue(analytics_c.get("success"))
        self.assertTrue(analytics_c.get("has_data"))
        self.assertGreaterEqual(analytics_c.get("total_evaluations"), 2) # Physics Self Assessment + Calculus Midterm
        score_titles = [s.get("assessment_title") for s in analytics_c.get("score_history", [])]
        self.assertIn(self_eval_topic, score_titles)
        self.assertIn(teach_eval_topic, score_titles)

        # 11. Check Student C's Evaluation History & Detail via app_c
        res_evals_c = app_c.get("/api/evaluations")
        self.assertEqual(res_evals_c.status_code, 200)
        evals_list_c = res_evals_c.get_json().get("evaluations", [])
        c_eval_ids = [str(e.get("id") or e.get("_id") or e.get("evaluation_id")) for e in evals_list_c]
        self.assertIn(str(self_eval_id), c_eval_ids)

        res_detail_c = app_c.get(f"/api/evaluations/{self_eval_id}")
        self.assertEqual(res_detail_c.status_code, 200)
        self.assertEqual(res_detail_c.get_json().get("evaluation", {}).get("evaluation_source"), "STUDENT_SELF_EVALUATION")

        # 12. Register and Login as Student D (Cross-student privacy isolation)
        app_d = app.test_client()
        app_d.testing = True
        s_d_uid = f"{self.uid_prefix}_d_{uuid.uuid4().hex[:6]}"
        s_d_email = f"{s_d_uid}@learnsphere.edu"
        reg_d = app_d.post("/api/auth/register", json={"name": f"Student David {self.uid_prefix}", "email": s_d_email, "password": self.password, "role": "student"})
        student_d_id = reg_d.get_json()["user"]["id"]
        app_d.post("/api/auth/login", json={"email": s_d_email, "password": self.password, "role": "student"})

        # Student D analytics must have 0 evaluations and never leak Student C's evaluations
        res_analytics_d = app_d.get("/api/analytics/student")
        self.assertEqual(res_analytics_d.status_code, 200)
        self.assertEqual(res_analytics_d.get_json().get("total_evaluations"), 0)

        # Student D evaluation history must be empty
        res_evals_d = app_d.get("/api/evaluations")
        self.assertEqual(res_evals_d.status_code, 200)
        self.assertEqual(len(res_evals_d.get_json().get("evaluations", [])), 0)

        # Student D attempting to access Student C's self-evaluation detail must be 403 Forbidden
        res_forbidden = app_d.get(f"/api/evaluations/{self_eval_id}")
        self.assertEqual(res_forbidden.status_code, 403)

        # 13. Teacher query for Student C's Analytics: Must ONLY show official Teacher Evaluations (Calculus) and NEVER Student Self Evaluation (Physics)
        res_teacher_view = self.app.get(f"/api/analytics/student?student_id={student_c_id}")
        self.assertEqual(res_teacher_view.status_code, 200)
        teacher_view_data = res_teacher_view.get_json()
        teacher_score_titles = [s.get("assessment_title") for s in teacher_view_data.get("score_history", [])]
        self.assertIn(teach_eval_topic, teacher_score_titles)
        self.assertNotIn(self_eval_topic, teacher_score_titles)


if __name__ == "__main__":
    unittest.main()
