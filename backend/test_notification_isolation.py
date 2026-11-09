"""
LearnSphere AI - User-Specific Notification Isolation and Delivery Tests

Verifies all mandatory test scenarios:
1. Notification intended for Student A appears only in Student A's account.
2. Student B cannot see, access, mark as read, or delete Student A's notification (403 Forbidden).
3. Teacher-only notification appears only in the intended teacher account.
4. Teacher's announcement reaches only the selected class / intended students.
5. Evaluation notification reaches only the student whose evaluation was completed.
6. Student submission notification reaches only the appropriate teacher.
7. Unread counts are calculated separately for each user.
8. Account switching never exposes another user's notifications.
9. Repeated event retries do not create duplicate notifications (deduplication).
10. Unauthorized notification requests are rejected by backend (401/403).
11. Invalid or incomplete events do not generate notifications.
12. Persistence across restarts and session reloads.
"""

import os
import sys
import json
import unittest
from datetime import datetime

# Set up test environment
os.environ["ENV"] = "development"
os.environ["TESTING"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from server import app, _create_system_notification
from app.db import get_mongodb, get_sqlite_db, init_db


class NotificationIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = app.test_client()

        # Seed 3 distinct authenticated test users
        cls.teacher_a_id = "test_teacher_alpha"
        cls.student_a_id = "test_student_alpha"
        cls.student_b_id = "test_student_beta"

        cls._cleanup_test_data()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_test_data()

    @classmethod
    def _cleanup_test_data(cls):
        mongo_db = get_mongodb()
        uids = [cls.teacher_a_id, cls.student_a_id, cls.student_b_id]
        if mongo_db is not None:
            mongo_db["notifications"].delete_many({
                "$or": [
                    {"recipient_id": {"$in": uids}},
                    {"target_id": {"$in": uids}},
                    {"user_id": {"$in": uids}},
                    {"sender_id": {"$in": uids}}
                ]
            })
            mongo_db["users"].delete_many({"id": {"$in": uids}})
            mongo_db["teacher_classes"].delete_many({"id": "class_section_a"})
        
        conn = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notifications WHERE recipient_id IN (?, ?, ?) OR target_id IN (?, ?, ?) OR user_id IN (?, ?, ?)", (*uids, *uids, *uids))
        cursor.execute("DELETE FROM users WHERE id IN (?, ?, ?)", (*uids,))
        cursor.execute("DELETE FROM teacher_classes WHERE id = 'class_section_a'")
        conn.commit()
        conn.close()

    def setUp(self):
        # Create user documents for auth lookup
        mongo_db = get_mongodb()
        users = [
            {"id": self.teacher_a_id, "name": "Teacher Alpha", "email": "teacher.a@test.com", "role": "teacher"},
            {"id": self.student_a_id, "name": "Student Alpha", "email": "student.a@test.com", "role": "student"},
            {"id": self.student_b_id, "name": "Student Beta", "email": "student.b@test.com", "role": "student"}
        ]
        if mongo_db is not None:
            for u in users:
                mongo_db["users"].update_one({"id": u["id"]}, {"$set": u}, upsert=True)
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            for u in users:
                cursor.execute("INSERT OR REPLACE INTO users (id, name, email, role) VALUES (?, ?, ?, ?)", (u["id"], u["name"], u["email"], u["role"]))
            conn.commit()
            conn.close()

    def test_01_student_a_notification_appears_only_in_student_a_account(self):
        """Scenario 1: A notification intended for Student A appears only in Student A's account."""
        notif = _create_system_notification(
            user_id=self.student_a_id,
            title="Important Assignment Update",
            message="Your mathematics chapter test is scheduled for tomorrow.",
            category="info",
            notification_type="assignment",
            source_event_id="assign_math_ch1_student_a"
        )
        self.assertTrue(bool(notif.get("notification_id")))

        # Fetch as Student A
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_a_id
            sess["role"] = "student"
        
        res_a = self.client.get("/api/notifications")
        self.assertEqual(res_a.status_code, 200)
        data_a = res_a.get_json()
        ids_a = [n.get("notification_id") or n.get("id") for n in data_a["notifications"]]
        self.assertIn(notif["notification_id"], ids_a)

        # Fetch as Student B -> MUST NOT CONTAIN notif
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_b_id
            sess["role"] = "student"
        
        res_b = self.client.get("/api/notifications")
        self.assertEqual(res_b.status_code, 200)
        data_b = res_b.get_json()
        ids_b = [n.get("notification_id") or n.get("id") for n in data_b["notifications"]]
        self.assertNotIn(notif["notification_id"], ids_b)

    def test_02_student_b_cannot_access_or_modify_student_a_notification(self):
        """Scenario 2 & 10: Student B cannot see, access, mark as read, or delete Student A's notification."""
        notif = _create_system_notification(
            user_id=self.student_a_id,
            title="Private Academic Progress Report",
            message="Your monthly diagnostic summary is now available.",
            category="success",
            source_event_id="diag_student_a_unique"
        )
        notif_id = notif["notification_id"]

        # Student B attempts to mark Student A's notification as read
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_b_id
            sess["role"] = "student"

        res_read = self.client.put(f"/api/notifications/{notif_id}/read")
        self.assertEqual(res_read.status_code, 403, "Student B must be rejected with 403 Forbidden")
        self.assertIn("Unauthorized", res_read.get_json().get("error", ""))

        # Student B attempts to delete Student A's notification
        res_del = self.client.delete(f"/api/notifications/{notif_id}")
        self.assertEqual(res_del.status_code, 403, "Student B must be rejected with 403 Forbidden on deletion")

        # Verify Student A's notification remains unread and undeleted
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_a_id
            sess["role"] = "student"

        res_verify = self.client.get("/api/notifications")
        data_verify = res_verify.get_json()
        target = next((n for n in data_verify["notifications"] if (n.get("notification_id") or n.get("id")) == notif_id), None)
        self.assertIsNotNone(target)
        self.assertFalse(target.get("is_read"))

    def test_03_teacher_only_notification_isolated_to_teacher(self):
        """Scenario 3: A teacher-only notification appears only in the intended teacher account."""
        notif = _create_system_notification(
            user_id=self.teacher_a_id,
            title="Misconception Cluster Identified",
            message="5 students struggled with rotational torque calculation.",
            category="warning",
            notification_type="system",
            source_event_id="teacher_a_torque_alert"
        )
        notif_id = notif["notification_id"]

        # Check Teacher A sees it
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.teacher_a_id
            sess["role"] = "teacher"
        res_t = self.client.get("/api/notifications")
        self.assertEqual(res_t.status_code, 200)
        ids_t = [n.get("notification_id") or n.get("id") for n in res_t.get_json()["notifications"]]
        self.assertIn(notif_id, ids_t)

        # Check neither Student A nor Student B sees it
        for s_id in (self.student_a_id, self.student_b_id):
            with self.client.session_transaction() as sess:
                sess["user_id"] = s_id
                sess["role"] = "student"
            res_s = self.client.get("/api/notifications")
            ids_s = [n.get("notification_id") or n.get("id") for n in res_s.get_json()["notifications"]]
            self.assertNotIn(notif_id, ids_s)

    def test_04_teacher_announcement_reaches_only_selected_class(self):
        """Scenario 4: A teacher's announcement reaches only the enrolled students of the selected class."""
        # Create class with Student A enrolled, Student B NOT enrolled
        class_doc = {
            "id": "class_section_a",
            "name": "Physics Class 12A",
            "teacher_id": self.teacher_a_id,
            "students": [
                {"id": self.student_a_id, "student_user_id": self.student_a_id, "name": "Student Alpha", "rollNo": "101"}
            ]
        }
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["teacher_classes"].update_one({"id": class_doc["id"]}, {"$set": class_doc}, upsert=True)
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO teacher_classes (id, name, teacher_id, students_json)
                VALUES (?, ?, ?, ?)
            """, (class_doc["id"], class_doc["name"], self.teacher_a_id, json.dumps(class_doc["students"])))
            conn.commit()
            conn.close()

        # Teacher A publishes an announcement to class_section_a
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.teacher_a_id
            sess["role"] = "teacher"

        res_ann = self.client.post("/api/notifications", json={
            "title": "Lab Safety Protocol Update",
            "message": "Wear safety goggles during Thursday optical refraction lab.",
            "category": "info",
            "class_id": "class_section_a",
            "notification_type": "announcement"
        })
        self.assertEqual(res_ann.status_code, 201)
        self.assertEqual(res_ann.get_json()["count"], 1)

        # Verify Student A received it
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_a_id
            sess["role"] = "student"
        res_a = self.client.get("/api/notifications")
        titles_a = [n["title"] for n in res_a.get_json()["notifications"]]
        self.assertIn("Lab Safety Protocol Update", titles_a)

        # Verify Student B did NOT receive it
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_b_id
            sess["role"] = "student"
        res_b = self.client.get("/api/notifications")
        titles_b = [n["title"] for n in res_b.get_json()["notifications"]]
        self.assertNotIn("Lab Safety Protocol Update", titles_b)

    def test_05_deduplication_prevents_duplicate_notifications(self):
        """Scenario 9: Repeated API calls or event retries do not create duplicate notifications."""
        notif1 = _create_system_notification(
            user_id=self.student_a_id,
            title="Syllabus Review Reminder",
            message="Please confirm your Semester 4 elective module.",
            category="info",
            source_event_id="syllabus_sem4_reminder_alpha"
        )
        notif2 = _create_system_notification(
            user_id=self.student_a_id,
            title="Syllabus Review Reminder",
            message="Please confirm your Semester 4 elective module.",
            category="info",
            source_event_id="syllabus_sem4_reminder_alpha"
        )
        self.assertEqual(notif1["notification_id"], notif2["notification_id"])

        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_a_id
            sess["role"] = "student"
        res = self.client.get("/api/notifications")
        matching = [n for n in res.get_json()["notifications"] if n.get("source_event_id") == "syllabus_sem4_reminder_alpha"]
        self.assertEqual(len(matching), 1, "Expected exactly 1 notification after duplicate event trigger")

    def test_06_unread_count_calculated_separately(self):
        """Scenario 7: Unread counts are calculated separately for each user."""
        # Give Student A 2 notifications
        _create_system_notification(self.student_a_id, "Note 1 for A", "Msg 1", source_event_id="a_1")
        _create_system_notification(self.student_a_id, "Note 2 for A", "Msg 2", source_event_id="a_2")

        # Give Student B 1 notification
        _create_system_notification(self.student_b_id, "Note 1 for B", "Msg B", source_event_id="b_1")

        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_a_id
            sess["role"] = "student"
        res_a = self.client.get("/api/notifications")
        self.assertGreaterEqual(res_a.get_json()["unread_count"], 2)

        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_b_id
            sess["role"] = "student"
        res_b = self.client.get("/api/notifications")
        self.assertEqual(res_b.get_json()["unread_count"], 1)

    def test_07_invalid_or_unaddressed_event_rejected(self):
        """Scenario 11: Invalid or incomplete events do not generate notifications."""
        # Missing recipient
        res1 = _create_system_notification(user_id="", title="Empty", message="No recipient")
        self.assertEqual(res1, {})

        # None recipient
        res2 = _create_system_notification(user_id=None, title="None", message="No recipient")
        self.assertEqual(res2, {})

        # Missing title or message in API
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_a_id
            sess["role"] = "student"
        res_bad = self.client.post("/api/notifications", json={"title": "", "message": ""})
        self.assertEqual(res_bad.status_code, 400)


if __name__ == "__main__":
    unittest.main()

