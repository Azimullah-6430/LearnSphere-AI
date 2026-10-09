"""
Comprehensive Verification Test Suite for:
1. Academic Memory (Create, Read, Delete individual, Clear all)
2. Dynamic Notifications (Real generation, Read, Mark Read, Delete, Clear all)
3. Streaks Calculation (Same-day retention, Consecutive-day increment, Missed-day break/reset)
4. Strong Authentication (Password validation, Role isolation, Session security)
"""

import unittest
import json
import uuid
from datetime import datetime, timedelta, timezone
from server import app, _update_user_streak, _create_system_notification
from app.db import get_sqlite_db, init_db

class TestAcademicMemoryNotificationsStreaks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.app = app.test_client()
        self.test_email = f"test_student_{uuid.uuid4().hex[:8]}@example.com"
        self.test_password = "SecurePassword123!"
        self.test_name = "Test Student"
        
        # Register a test student
        resp = self.app.post("/api/auth/register", json={
            "name": self.test_name,
            "email": self.test_email,
            "password": self.test_password,
            "role": "student",
            "level": "college",
            "department": "Computer Science",
            "semester": 4
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.user_id = data["user"]["id"]

    def test_streak_calculation_logic(self):
        """Test daily streak counting, consecutive incrementation, and missed-day streak breaking."""
        IST = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(IST)
        today = now_ist.strftime("%Y-%m-%d")
        yesterday = (now_ist - timedelta(days=1)).strftime("%Y-%m-%d")
        three_days_ago = (now_ist - timedelta(days=3)).strftime("%Y-%m-%d")

        # 1. Initial streak should be 1
        user_doc = {
            "streak_count": 1,
            "last_active_date": today,
            "longest_streak": 1,
            "active_days": [today]
        }
        res = _update_user_streak(self.user_id, user_doc)
        self.assertEqual(res["streak_count"], 1)

        # 2. Consecutive day login: yesterday -> today should increment streak to 2
        user_doc_consecutive = {
            "streak_count": 1,
            "last_active_date": yesterday,
            "longest_streak": 1,
            "active_days": [yesterday]
        }
        res = _update_user_streak(self.user_id, user_doc_consecutive)
        self.assertEqual(res["streak_count"], 2)
        self.assertEqual(res["longest_streak"], 2)
        self.assertEqual(res["last_active_date"], today)

        # 3. Same day repeated login: should retain current streak
        user_doc_same_day = {
            "streak_count": 5,
            "last_active_date": today,
            "longest_streak": 5,
            "active_days": [today]
        }
        res = _update_user_streak(self.user_id, user_doc_same_day)
        self.assertEqual(res["streak_count"], 5)

        # 4. Missed day login: three_days_ago -> today should break streak and reset to 1
        user_doc_broken = {
            "streak_count": 12,
            "last_active_date": three_days_ago,
            "longest_streak": 12,
            "active_days": [three_days_ago]
        }
        res = _update_user_streak(self.user_id, user_doc_broken)
        self.assertEqual(res["streak_count"], 1)
        self.assertEqual(res["longest_streak"], 12)  # longest streak preserved
        self.assertEqual(res["last_active_date"], today)

    def test_streak_api_endpoint(self):
        """Test /api/user/streak endpoint."""
        resp = self.app.get("/api/user/streak")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(data["streak"], 1)
        self.assertIn("active_days", data)

    def test_academic_memory_crud_and_delete(self):
        """Test academic memory creation, retrieval, review, and deletion."""
        # 1. Create a memory card
        create_resp = self.app.post("/api/memory/cards", json={
            "subject": "Mathematics",
            "topic": "Eigenvalues & Eigenvectors",
            "mastery": 85,
            "retention_rate": 80
        })
        self.assertEqual(create_resp.status_code, 201)
        create_data = create_resp.get_json()
        self.assertTrue(create_data["success"])
        card_id = create_data["id"]

        # 2. Get memory cards
        get_resp = self.app.get("/api/memory/cards")
        self.assertEqual(get_resp.status_code, 200)
        cards = get_resp.get_json()["cards"]
        self.assertTrue(any(c.get("topic") == "Eigenvalues & Eigenvectors" for c in cards))

        # 3. Review memory card
        rev_resp = self.app.post("/api/memory/review", json={"id": card_id})
        self.assertEqual(rev_resp.status_code, 200)
        self.assertTrue(rev_resp.get_json()["success"])

        # 4. Delete single memory card
        del_resp = self.app.delete(f"/api/memory/cards/{card_id}")
        self.assertEqual(del_resp.status_code, 200)
        self.assertTrue(del_resp.get_json()["success"])

        # Verify deletion
        get_after_del = self.app.get("/api/memory/cards")
        cards_after = get_after_del.get_json()["cards"]
        self.assertFalse(any(str(c.get("id") or c.get("_id")) == str(card_id) for c in cards_after))

        # 5. Create multiple and clear all
        self.app.post("/api/memory/cards", json={"subject": "Physics", "topic": "Thermodynamics", "mastery": 60})
        self.app.post("/api/memory/cards", json={"subject": "Chemistry", "topic": "Organic Synthesis", "mastery": 75})
        
        clear_resp = self.app.delete("/api/memory/cards")
        self.assertEqual(clear_resp.status_code, 200)
        self.assertTrue(clear_resp.get_json()["success"])

    def test_dynamic_notifications_crud_and_delete(self):
        """Test real dynamic notifications, mark as read, and deletion."""
        # 1. Get notifications (triggers initial real dynamic notifications)
        get_resp = self.app.get("/api/notifications")
        self.assertEqual(get_resp.status_code, 200)
        notes = get_resp.get_json()["notifications"]
        self.assertGreaterEqual(len(notes), 1)

        # 2. Create custom notification
        create_resp = self.app.post("/api/notifications", json={
            "title": "Evaluation Completed",
            "message": "Your Operating Systems exam scored 92%.",
            "category": "success",
            "action_url": "/app/analytics"
        })
        self.assertEqual(create_resp.status_code, 201)
        notif_id = create_resp.get_json()["notification"]["id"]

        # 3. Mark notification as read
        read_resp = self.app.put(f"/api/notifications/{notif_id}/read")
        self.assertEqual(read_resp.status_code, 200)
        self.assertTrue(read_resp.get_json()["success"])

        # 4. Mark all as read
        read_all_resp = self.app.put("/api/notifications/read-all")
        self.assertEqual(read_all_resp.status_code, 200)
        self.assertTrue(read_all_resp.get_json()["success"])

        # 5. Delete specific notification
        del_resp = self.app.delete(f"/api/notifications/{notif_id}")
        self.assertEqual(del_resp.status_code, 200)
        self.assertTrue(del_resp.get_json()["success"])

        # 6. Clear all notifications
        clear_resp = self.app.delete("/api/notifications")
        self.assertEqual(clear_resp.status_code, 200)
        self.assertTrue(clear_resp.get_json()["success"])

    def test_strong_auth_and_session(self):
        """Verify password hashing, login authentication, and role checking."""
        # Incorrect password must fail with 401
        wrong_resp = self.app.post("/api/auth/login", json={
            "email": self.test_email,
            "password": "WrongPassword999!"
        })
        self.assertEqual(wrong_resp.status_code, 401)
        self.assertFalse(wrong_resp.get_json()["success"])

        # Wrong portal role must fail with 403
        wrong_role = self.app.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password,
            "role": "teacher"  # student trying to log into teacher portal
        })
        self.assertEqual(wrong_role.status_code, 403)

        # Correct login succeeds and returns user with streak
        login_resp = self.app.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password,
            "role": "student"
        })
        self.assertEqual(login_resp.status_code, 200)
        user = login_resp.get_json()["user"]
        self.assertEqual(user["email"], self.test_email)
        self.assertGreaterEqual(user["streak_count"], 1)

if __name__ == "__main__":
    unittest.main()
