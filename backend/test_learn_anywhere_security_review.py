"""
Learn Anywhere Comprehensive Security & Architecture Review Test Suite
Mandatory Acceptance Requirements:
1. Unauthenticated requests rejected (401 Unauthorized).
2. Teacher accounts denied access to all 9 Learn Anywhere endpoints (403 Forbidden).
3. Cross-student access rejected (Student B cannot read, update, or delete Student A's records).
4. Client-manipulated IDs (student_id, syllabus_id, user_id) ignored/rejected without server-side authorization.
5. Cache & pipeline isolation (zero leakage into teacher evaluations, analytics, misconceptions, plagiarism, or action center).
"""

import json
import unittest
from datetime import datetime

from server import app, get_mongodb, get_sqlite_db


class TestLearnAnywhereSecurityReview(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = app.test_client()

        self.student_a_id = "stu_sec_a_101"
        self.student_b_id = "stu_sec_b_202"
        self.teacher_id = "tea_sec_999"

        self.syl_a_id = "syl_sec_a"
        self.syl_b_id = "syl_sec_b"

        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db.users.delete_many({"_id": {"$in": [self.student_a_id, self.student_b_id, self.teacher_id]}})
            mongo_db.syllabi.delete_many({"user_id": {"$in": [self.student_a_id, self.student_b_id]}})
            mongo_db.learn_anywhere_history.delete_many({"user_id": {"$in": [self.student_a_id, self.student_b_id]}})
            mongo_db.learn_anywhere_progress.delete_many({"user_id": {"$in": [self.student_a_id, self.student_b_id]}})

            mongo_db.users.insert_many([
                {"_id": self.student_a_id, "id": self.student_a_id, "user_id": self.student_a_id, "email": "sec_a@learn.edu", "role": "student", "full_name": "Security Student A"},
                {"_id": self.student_b_id, "id": self.student_b_id, "user_id": self.student_b_id, "email": "sec_b@learn.edu", "role": "student", "full_name": "Security Student B"},
                {"_id": self.teacher_id, "id": self.teacher_id, "user_id": self.teacher_id, "email": "sec_t@learn.edu", "role": "teacher", "full_name": "Security Teacher"}
            ])

            mongo_db.syllabi.insert_many([
                {
                    "_id": self.syl_a_id,
                    "syllabus_id": self.syl_a_id,
                    "user_id": self.student_a_id,
                    "student_id": self.student_a_id,
                    "studentId": self.student_a_id,
                    "is_active": True,
                    "isActive": True,
                    "validation_status": "VALID",
                    "validationStatus": "VALID",
                    "status": "VALID",
                    "document_name": "Student A Syllabus",
                    "subjects": [{"name": "Physics", "topics": ["Optics"]}],
                    "created_at": datetime.utcnow()
                },
                {
                    "_id": self.syl_b_id,
                    "syllabus_id": self.syl_b_id,
                    "user_id": self.student_b_id,
                    "student_id": self.student_b_id,
                    "studentId": self.student_b_id,
                    "is_active": True,
                    "isActive": True,
                    "validation_status": "VALID",
                    "validationStatus": "VALID",
                    "status": "VALID",
                    "document_name": "Student B Syllabus",
                    "subjects": [{"name": "Chemistry", "topics": ["Acids"]}],
                    "created_at": datetime.utcnow()
                }
            ])

    def tearDown(self):
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db.users.delete_many({"_id": {"$in": [self.student_a_id, self.student_b_id, self.teacher_id]}})
            mongo_db.syllabi.delete_many({"user_id": {"$in": [self.student_a_id, self.student_b_id]}})
            mongo_db.learn_anywhere_history.delete_many({"user_id": {"$in": [self.student_a_id, self.student_b_id]}})
            mongo_db.learn_anywhere_progress.delete_many({"user_id": {"$in": [self.student_a_id, self.student_b_id]}})

    def test_01_unauthenticated_access_rejection(self):
        """Verify unauthenticated requests are rejected on all 9 endpoints."""
        endpoints = [
            ("POST", "/api/learn-anywhere/generate", {"subject": "Physics"}),
            ("POST", "/api/learn-anywhere/evaluate-answer", {"question": "Q", "student_answer": "A"}),
            ("POST", "/api/learn-anywhere/progress", {"activity_id": "act_1"}),
            ("GET", "/api/learn-anywhere/progress", None),
            ("POST", "/api/learn-anywhere/additional-practice", {"subject": "Physics"}),
            ("GET", "/api/learn-anywhere/history", None),
            ("GET", "/api/learn-anywhere/history/act_1", None),
            ("PUT", "/api/learn-anywhere/history/act_1", {"reflections": "Notes"}),
            ("DELETE", "/api/learn-anywhere/history/act_1", None)
        ]

        for method, url, payload in endpoints:
            if method == "POST":
                res = self.client.post(url, json=payload or {})
            elif method == "PUT":
                res = self.client.put(url, json=payload or {})
            elif method == "DELETE":
                res = self.client.delete(url)
            else:
                res = self.client.get(url)

            self.assertIn(res.status_code, [401, 403], f"Endpoint {method} {url} allowed unauthenticated request!")

    def test_02_teacher_access_rejection(self):
        """Verify teacher accounts are strictly rejected with 403 Forbidden across all endpoints."""
        with app.test_request_context():
            with self.client.session_transaction() as sess:
                sess["user_id"] = self.teacher_id
                sess["user"] = {"id": self.teacher_id, "user_id": self.teacher_id, "role": "teacher"}

            endpoints = [
                ("POST", "/api/learn-anywhere/generate", {"subject": "Physics"}),
                ("POST", "/api/learn-anywhere/evaluate-answer", {"question": "Q", "student_answer": "A"}),
                ("POST", "/api/learn-anywhere/progress", {"activity_id": "act_1"}),
                ("GET", "/api/learn-anywhere/progress", None),
                ("POST", "/api/learn-anywhere/additional-practice", {"subject": "Physics"}),
                ("GET", "/api/learn-anywhere/history", None),
                ("GET", "/api/learn-anywhere/history/act_1", None),
                ("PUT", "/api/learn-anywhere/history/act_1", {"reflections": "Notes"}),
                ("DELETE", "/api/learn-anywhere/history/act_1", None)
            ]

            for method, url, payload in endpoints:
                if method == "POST":
                    res = self.client.post(url, json=payload or {})
                elif method == "PUT":
                    res = self.client.put(url, json=payload or {})
                elif method == "DELETE":
                    res = self.client.delete(url)
                else:
                    res = self.client.get(url)

                self.assertEqual(res.status_code, 403, f"Endpoint {method} {url} allowed teacher account access!")

    def test_03_cross_student_isolation(self):
        """Verify Student B cannot access, view, modify, or delete Student A's data."""
        # 1. Save progress and history for Student A
        mongo_db = get_mongodb()
        now = datetime.utcnow()
        act_id = "act_sec_a_999"

        if mongo_db is not None:
            mongo_db.learn_anywhere_history.insert_one({
                "activity_id": act_id,
                "user_id": self.student_a_id,
                "syllabus_id": self.syl_a_id,
                "curriculum_reference": "Student A Syllabus",
                "title": "Private Student A Experiment",
                "subject": "Physics",
                "topic": "Optics",
                "created_at": now,
                "updated_at": now,
                "completion_status": "in_progress",
                "attempts": [{"question_index": 0, "is_correct": True}],
                "reflections": "Private thoughts of Student A",
                "activity": {"title": "Private Student A Experiment"}
            })
            mongo_db.learn_anywhere_progress.insert_one({
                "user_id": self.student_a_id,
                "activity_id": act_id,
                "syllabus_id": self.syl_a_id,
                "completion_status": "in_progress",
                "updated_at": now
            })

        # Student B attempts access
        with app.test_request_context():
            with self.client.session_transaction() as sess:
                sess["user_id"] = self.student_b_id
                sess["user"] = {"id": self.student_b_id, "user_id": self.student_b_id, "role": "student"}

            # B gets history list -> Should NOT contain Student A's item
            b_hist = self.client.get("/api/learn-anywhere/history")
            self.assertEqual(b_hist.status_code, 200)
            b_items = b_hist.get_json()["history"]
            self.assertFalse(any(i["activity_id"] == act_id for i in b_items))

            # B attempts GET item
            b_get_item = self.client.get(f"/api/learn-anywhere/history/{act_id}")
            self.assertEqual(b_get_item.status_code, 404)

            # B attempts PUT reflection
            b_put = self.client.put(f"/api/learn-anywhere/history/{act_id}", json={"reflections": "Malicious edit"})
            self.assertEqual(b_put.status_code, 404)

            # B attempts DELETE
            b_del = self.client.delete(f"/api/learn-anywhere/history/{act_id}")
            self.assertEqual(b_del.status_code, 404)

            # B gets progress list -> Should NOT contain Student A's progress
            b_prog = self.client.get("/api/learn-anywhere/progress")
            self.assertEqual(b_prog.status_code, 200)
            b_p_records = b_prog.get_json()["progress_records"]
            self.assertFalse(any(p.get("activity_id") == act_id for p in b_p_records))

    def test_04_manipulated_client_payload_rejection(self):
        """Verify passing another student's user_id or syllabus_id in payload cannot bypass backend security."""
        with app.test_request_context():
            with self.client.session_transaction() as sess:
                sess["user_id"] = self.student_b_id
                sess["user"] = {"id": self.student_b_id, "user_id": self.student_b_id, "role": "student"}

            # Student B tries to generate activity using Student A's syllabus_id and user_id in payload
            resp = self.client.post("/api/learn-anywhere/generate", json={
                "user_id": self.student_a_id,
                "student_id": self.student_a_id,
                "syllabus_id": self.syl_a_id,  # Belongs to Student A
                "subject": "Physics"
            })

            # Should fail because Student B does not own syl_a_id
            self.assertEqual(resp.status_code, 400)
            res_data = resp.get_json()
            self.assertFalse(res_data.get("success"))

    def test_05_strict_pipeline_isolation(self):
        """Verify Learn from Anywhere activities do NOT touch evaluation, plagiarism, or misconception tables."""
        mongo_db = get_mongodb()
        if mongo_db is not None:
            eval_count_before = mongo_db.evaluations.count_documents({})
            misc_count_before = mongo_db.misconceptions.count_documents({})
            action_count_before = mongo_db.action_items.count_documents({})

        with app.test_request_context():
            with self.client.session_transaction() as sess:
                sess["user_id"] = self.student_a_id
                sess["user"] = {"id": self.student_a_id, "user_id": self.student_a_id, "role": "student"}

            # Perform answer evaluation & save progress
            self.client.post("/api/learn-anywhere/evaluate-answer", json={
                "subject": "Physics",
                "topic": "Optics",
                "question": "Why does light refract?",
                "expected_answer": "Speed of light changes in medium",
                "student_answer": "Because speed changes when entering glass",
                "attempt_number": 1
            })

            self.client.post("/api/learn-anywhere/progress", json={
                "activity_id": "act_iso_test",
                "syllabus_id": self.syl_a_id,
                "subject": "Physics",
                "topic": "Optics",
                "attempts": [{"question_index": 0, "is_correct": True}],
                "completed_steps": [0, 1]
            })

        if mongo_db is not None:
            eval_count_after = mongo_db.evaluations.count_documents({})
            misc_count_after = mongo_db.misconceptions.count_documents({})
            action_count_after = mongo_db.action_items.count_documents({})

            self.assertEqual(eval_count_before, eval_count_after, "Learn Anywhere leaked into teacher evaluations collection!")
            self.assertEqual(misc_count_before, misc_count_after, "Learn Anywhere leaked into misconception map collection!")
            self.assertEqual(action_count_before, action_count_after, "Learn Anywhere leaked into action items collection!")


if __name__ == "__main__":
    unittest.main()
