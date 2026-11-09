"""
Test Isolation and Persistence of Blind Learning Companion
Verifies:
1. Non-disabled students register with is_disabled_student=False and blind_companion_enabled=False.
2. Disabled students register with is_disabled_student=True, disability_type='blind_or_low_vision', and blind_companion_enabled=True.
3. Profile updates correctly persist blind_companion_enabled and custom settings.
4. Data remains strictly user-isolated.
"""

import unittest
import json
import uuid
from server import app


class TestBlindCompanionIsolation(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_normal_student_registration_isolation(self):
        """Non-disabled student must have blind companion disabled and is_disabled_student=False."""
        email = f"normal_student_{uuid.uuid4().hex[:6]}@example.com"
        res = self.client.post("/api/auth/register", json={
            "name": "Normal Student",
            "email": email,
            "password": "password123",
            "role": "student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Computer Science",
            "semester": 4,
            # Disabled flags not set or false
            "is_disabled_student": False
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        user = data.get("user")
        self.assertFalse(user.get("is_disabled_student"))
        self.assertFalse(user.get("blind_companion_enabled"))

    def test_disabled_student_registration_enabled(self):
        """Disabled student registering with is_disabled_student=True must have companion enabled."""
        email = f"disabled_student_{uuid.uuid4().hex[:6]}@example.com"
        res = self.client.post("/api/auth/register", json={
            "name": "Accessible Learner",
            "email": email,
            "password": "password123",
            "role": "student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Information Technology",
            "semester": 6,
            "is_disabled_student": True,
            "disability_type": "blind_or_low_vision",
            "blind_companion_enabled": True
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        user = data.get("user")
        self.assertTrue(user.get("is_disabled_student"))
        self.assertEqual(user.get("disability_type"), "blind_or_low_vision")
        self.assertTrue(user.get("blind_companion_enabled"))
        settings = user.get("blind_companion_settings")
        self.assertIsInstance(settings, dict)
        self.assertTrue(settings.get("audio_first"))

    def test_profile_update_and_settings_persistence(self):
        """User can update blind companion settings and toggle state via /api/user/profile."""
        email = f"student_settings_{uuid.uuid4().hex[:6]}@example.com"
        # 1. Register student
        reg_res = self.client.post("/api/auth/register", json={
            "name": "Settings Tester",
            "email": email,
            "password": "password123",
            "role": "student",
            "level": "school",
            "classLevel": 12,
            "is_disabled_student": True
        })
        self.assertEqual(reg_res.status_code, 201)

        # 2. Update blind companion settings
        custom_settings = {
            "audio_first": True,
            "text_to_speech": True,
            "voice_questions": True,
            "voice_navigation": False,
            "audio_speed": 1.5,
            "explanation_mode": "simple",
            "spoken_diagrams": True,
            "keyboard_nav": True
        }
        update_res = self.client.put("/api/user/profile", json={
            "blind_companion_enabled": True,
            "blind_companion_settings": custom_settings
        })
        self.assertEqual(update_res.status_code, 200)
        u_data = update_res.get_json()
        self.assertTrue(u_data.get("success"))
        updated_user = u_data.get("user")
        self.assertTrue(updated_user.get("blind_companion_enabled"))
        self.assertEqual(updated_user.get("blind_companion_settings", {}).get("audio_speed"), 1.5)
        self.assertEqual(updated_user.get("blind_companion_settings", {}).get("explanation_mode"), "simple")


if __name__ == "__main__":
    unittest.main()
