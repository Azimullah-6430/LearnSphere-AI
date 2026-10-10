"""
Learn Anywhere Activity History Test Suite
Validates:
- Automatic history recording on activity generation.
- Paginated listing of student history records.
- Strict authenticated student ownership checks on GET, PUT, and DELETE operations.
- Teacher access rejection (403 Forbidden).
- Curriculum replacement & versioning flags ('is_current_curriculum': False for old syllabi).
- Reflection updates and record deletion.
"""

import json
import unittest
from datetime import datetime

from server import app, get_mongodb, get_sqlite_db


class TestLearnAnywhereHistory(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = app.test_client()

        self.student_a_id = "stu_history_a_101"
        self.student_b_id = "stu_history_b_202"
        self.teacher_id = "tea_history_999"

        self.syllabus_v1_id = "syl_v1_physics"
        self.syllabus_v2_id = "syl_v2_chemistry"

        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db.users.delete_many({"_id": {"$in": [self.student_a_id, self.student_b_id, self.teacher_id]}})
            mongo_db.users.delete_many({"id": {"$in": [self.student_a_id, self.student_b_id, self.teacher_id]}})
            mongo_db.syllabi.delete_many({"user_id": {"$in": [self.student_a_id, self.student_b_id]}})
            mongo_db.learn_anywhere_history.delete_many({"user_id": {"$in": [self.student_a_id, self.student_b_id]}})
            mongo_db.learn_anywhere_progress.delete_many({"user_id": {"$in": [self.student_a_id, self.student_b_id]}})

            mongo_db.users.insert_many([
                {"_id": self.student_a_id, "id": self.student_a_id, "user_id": self.student_a_id, "email": "stua@learn.edu", "role": "student", "full_name": "Student A", "grade_level": 10},
                {"_id": self.student_b_id, "id": self.student_b_id, "user_id": self.student_b_id, "email": "stub@learn.edu", "role": "student", "full_name": "Student B", "grade_level": 10},
                {"_id": self.teacher_id, "id": self.teacher_id, "user_id": self.teacher_id, "email": "teacher@learn.edu", "role": "teacher", "full_name": "Teacher Alpha"}
            ])

            mongo_db.syllabi.insert_one({
                "_id": self.syllabus_v1_id,
                "syllabus_id": self.syllabus_v1_id,
                "user_id": self.student_a_id,
                "student_id": self.student_a_id,
                "studentId": self.student_a_id,
                "is_active": True,
                "isActive": True,
                "validation_status": "VALID",
                "validationStatus": "VALID",
                "status": "VALID",
                "document_name": "Physics 10th Standard Syllabus (V1)",
                "subjects": [{"name": "Physics", "topics": ["Optics and Lenses", "Refraction"]}],
                "created_at": datetime.utcnow()
            })
        else:
            sqlite_db = get_sqlite_db()
            if sqlite_db:
                with sqlite_db:
                    sqlite_db.execute("""
                        CREATE TABLE IF NOT EXISTS learn_anywhere_history (
                            id TEXT PRIMARY KEY,
                            user_id TEXT NOT NULL,
                            activity_id TEXT NOT NULL,
                            syllabus_id TEXT,
                            curriculum_reference TEXT,
                            title TEXT,
                            subject TEXT,
                            topic TEXT,
                            completion_status TEXT,
                            attempts_json TEXT,
                            reflections TEXT,
                            activity_json TEXT,
                            created_at TEXT,
                            updated_at TEXT
                        )
                    """)
                    sqlite_db.execute("DELETE FROM learn_anywhere_history WHERE user_id IN (?, ?)", (self.student_a_id, self.student_b_id))

    def tearDown(self):
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db.users.delete_many({"_id": {"$in": [self.student_a_id, self.student_b_id, self.teacher_id]}})
            mongo_db.users.delete_many({"id": {"$in": [self.student_a_id, self.student_b_id, self.teacher_id]}})
            mongo_db.syllabi.delete_many({"user_id": {"$in": [self.student_a_id, self.student_b_id]}})
            mongo_db.learn_anywhere_history.delete_many({"user_id": {"$in": [self.student_a_id, self.student_b_id]}})
            mongo_db.learn_anywhere_progress.delete_many({"user_id": {"$in": [self.student_a_id, self.student_b_id]}})

    def test_01_activity_generation_persists_to_history(self):
        """Verify generating an activity saves record in learn_anywhere_history."""
        with app.test_request_context():
            with self.client.session_transaction() as sess:
                sess["user_id"] = self.student_a_id
                sess["user"] = {"id": self.student_a_id, "user_id": self.student_a_id, "role": "student"}

            resp = self.client.post("/api/learn-anywhere/generate", json={
                "subject": "Physics",
                "topic": "Optics and Lenses",
                "syllabus_id": self.syllabus_v1_id
            })

            self.assertEqual(resp.status_code, 200, f"Generate activity failed: {resp.get_json()}")
            data = resp.get_json()
            self.assertTrue(data.get("success"))
            activity = data.get("activity")
            self.assertIsNotNone(activity)
            act_id = activity.get("activity_id")

            # Verify saved in history endpoint
            hist_resp = self.client.get("/api/learn-anywhere/history")
            self.assertEqual(hist_resp.status_code, 200)
            hist_data = hist_resp.get_json()
            self.assertTrue(hist_data.get("success"))
            records = hist_data.get("history")
            self.assertGreaterEqual(len(records), 1)

            target_rec = next((r for r in records if r["activity_id"] == act_id), None)
            self.assertIsNotNone(target_rec)
            self.assertEqual(target_rec["subject"], "Physics")
            self.assertEqual(target_rec["topic"], "Optics and Lenses")
            self.assertEqual(target_rec["syllabus_id"], self.syllabus_v1_id)
            self.assertTrue(target_rec["is_current_curriculum"])
            self.assertEqual(target_rec["curriculum_status"], "Current Curriculum")

    def test_02_strict_student_ownership_verification(self):
        """Verify Student B cannot access or modify Student A's activity history."""
        # 1. Create history item for Student A directly
        mongo_db = get_mongodb()
        now = datetime.utcnow()
        act_id = "act_stu_a_secret_123"

        if mongo_db is not None:
            mongo_db.learn_anywhere_history.insert_one({
                "activity_id": act_id,
                "user_id": self.student_a_id,
                "syllabus_id": self.syllabus_v1_id,
                "curriculum_reference": "Physics 10th Standard",
                "title": "Solar Refraction Experiment",
                "subject": "Physics",
                "topic": "Optics and Lenses",
                "created_at": now,
                "updated_at": now,
                "completion_status": "in_progress",
                "attempts": [],
                "reflections": "Original student reflection",
                "activity": {"title": "Solar Refraction Experiment"}
            })

        # Student B attempts GET item
        with app.test_request_context():
            with self.client.session_transaction() as sess:
                sess["user_id"] = self.student_b_id
                sess["user"] = {"id": self.student_b_id, "user_id": self.student_b_id, "role": "student"}

            b_get = self.client.get(f"/api/learn-anywhere/history/{act_id}")
            self.assertEqual(b_get.status_code, 404)

            # Student B attempts PUT (update reflection)
            b_put = self.client.put(f"/api/learn-anywhere/history/{act_id}", json={
                "reflections": "Hacked reflection by student B"
            })
            self.assertEqual(b_put.status_code, 404)

            # Student B attempts DELETE
            b_del = self.client.delete(f"/api/learn-anywhere/history/{act_id}")
            self.assertEqual(b_del.status_code, 404)

        # Confirm Student A's item remains untouched
        with app.test_request_context():
            with self.client.session_transaction() as sess:
                sess["user_id"] = self.student_a_id
                sess["user"] = {"id": self.student_a_id, "user_id": self.student_a_id, "role": "student"}

            a_get = self.client.get(f"/api/learn-anywhere/history/{act_id}")
            self.assertEqual(a_get.status_code, 200)
            a_item = a_get.get_json()["item"]
            self.assertEqual(a_item["reflections"], "Original student reflection")

    def test_03_teacher_access_denied(self):
        """Verify teachers receive 403 Forbidden when accessing Learn from Anywhere history."""
        with app.test_request_context():
            with self.client.session_transaction() as sess:
                sess["user_id"] = self.teacher_id
                sess["user"] = {"id": self.teacher_id, "user_id": self.teacher_id, "role": "teacher"}

            t_get_all = self.client.get("/api/learn-anywhere/history")
            self.assertEqual(t_get_all.status_code, 403)

            t_get_one = self.client.get("/api/learn-anywhere/history/act_123")
            self.assertEqual(t_get_one.status_code, 403)

            t_put = self.client.put("/api/learn-anywhere/history/act_123", json={"reflections": "test"})
            self.assertEqual(t_put.status_code, 403)

            t_del = self.client.delete("/api/learn-anywhere/history/act_123")
            self.assertEqual(t_del.status_code, 403)

    def test_04_curriculum_replacement_flagging(self):
        """Verify that when a student's syllabus is replaced, old activities are flagged as 'Previous Curriculum'."""
        mongo_db = get_mongodb()
        now = datetime.utcnow()
        old_act_id = "act_old_syllabus_1"

        if mongo_db is not None:
            # 1. Insert history item with old syllabus ID v1
            mongo_db.learn_anywhere_history.insert_one({
                "activity_id": old_act_id,
                "user_id": self.student_a_id,
                "syllabus_id": self.syllabus_v1_id,
                "curriculum_reference": "Physics 10th Standard Syllabus (V1)",
                "title": "Prism Dispersal Demo",
                "subject": "Physics",
                "topic": "Optics and Lenses",
                "created_at": now,
                "updated_at": now,
                "completion_status": "completed",
                "attempts": [],
                "reflections": "",
                "activity": {"title": "Prism Dispersal Demo"}
            })

            # 2. Replace Student A's active syllabus with v2
            mongo_db.syllabi.delete_many({"$or": [{"user_id": self.student_a_id}, {"student_id": self.student_a_id}]})
            mongo_db.syllabi.insert_one({
                "_id": self.syllabus_v2_id,
                "syllabus_id": self.syllabus_v2_id,
                "user_id": self.student_a_id,
                "student_id": self.student_a_id,
                "studentId": self.student_a_id,
                "is_active": True,
                "isActive": True,
                "validation_status": "VALID",
                "validationStatus": "VALID",
                "status": "VALID",
                "document_name": "Chemistry 11th Standard Syllabus (V2)",
                "subjects": [{"name": "Chemistry", "topics": ["Acids and Bases"]}],
                "created_at": datetime.utcnow()
            })

        # Fetch history for Student A under new syllabus
        with app.test_request_context():
            with self.client.session_transaction() as sess:
                sess["user_id"] = self.student_a_id
                sess["user"] = {"id": self.student_a_id, "user_id": self.student_a_id, "role": "student"}

            resp = self.client.get("/api/learn-anywhere/history")
            self.assertEqual(resp.status_code, 200)
            items = resp.get_json()["history"]

            target = next((i for i in items if i["activity_id"] == old_act_id), None)
            self.assertIsNotNone(target)
            self.assertFalse(target["is_current_curriculum"])
            self.assertEqual(target["curriculum_status"], "Previous Curriculum")

    def test_05_update_reflection_and_delete_record(self):
        """Verify student can write reflections and delete their own history records."""
        mongo_db = get_mongodb()
        now = datetime.utcnow()
        act_id = "act_reflections_test_99"

        if mongo_db is not None:
            mongo_db.learn_anywhere_history.insert_one({
                "activity_id": act_id,
                "user_id": self.student_a_id,
                "syllabus_id": self.syllabus_v1_id,
                "title": "Soil pH Test",
                "subject": "Chemistry",
                "topic": "Acids and Bases",
                "created_at": now,
                "updated_at": now,
                "completion_status": "in_progress",
                "attempts": [],
                "reflections": "",
                "activity": {"title": "Soil pH Test"}
            })

        with app.test_request_context():
            with self.client.session_transaction() as sess:
                sess["user_id"] = self.student_a_id
                sess["user"] = {"id": self.student_a_id, "user_id": self.student_a_id, "role": "student"}

            # Update reflection
            put_resp = self.client.put(f"/api/learn-anywhere/history/{act_id}", json={
                "reflections": "Tested farm soil with turmeric indicator. Turned reddish in alkaline water!"
            })
            self.assertEqual(put_resp.status_code, 200)

            # Check update persisted
            get_resp = self.client.get(f"/api/learn-anywhere/history/{act_id}")
            self.assertEqual(get_resp.status_code, 200)
            rec = get_resp.get_json()["item"]
            self.assertIn("turmeric indicator", rec["reflections"])

            # Delete record
            del_resp = self.client.delete(f"/api/learn-anywhere/history/{act_id}")
            self.assertEqual(del_resp.status_code, 200)

            # Verify deleted
            get_after_del = self.client.get(f"/api/learn-anywhere/history/{act_id}")
            self.assertEqual(get_after_del.status_code, 404)


if __name__ == "__main__":
    unittest.main()
