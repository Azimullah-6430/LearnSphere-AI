import unittest
import json
import uuid
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from server import app, get_mongodb, get_sqlite_db

class TestBlindStudentPortalIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db = get_mongodb()

        # 1. Register a teacher using teacher_client
        cls.teacher_client = app.test_client()
        cls.teacher_email = f"teacher_iso_{uuid.uuid4().hex[:6]}@example.com"
        reg_t = cls.teacher_client.post('/api/auth/register', json={
            "email": cls.teacher_email,
            "password": "Password123!",
            "name": "Prof. Alan Isolation",
            "role": "teacher"
        })
        assert reg_t.status_code == 201

        # 2. Register a non-disabled student using normal_client
        cls.normal_client = app.test_client()
        cls.normal_email = f"normal_student_{uuid.uuid4().hex[:6]}@example.com"
        reg_n = cls.normal_client.post('/api/auth/register', json={
            "email": cls.normal_email,
            "password": "Password123!",
            "name": "Normal Student",
            "role": "student",
            "is_disabled_student": False,
            "blind_companion_enabled": False
        })
        assert reg_n.status_code == 201

        # 3. Register a blind/disabled student using blind_client
        cls.blind_client = app.test_client()
        cls.blind_email = f"blind_student_{uuid.uuid4().hex[:6]}@example.com"
        reg_b = cls.blind_client.post('/api/auth/register', json={
            "email": cls.blind_email,
            "password": "Password123!",
            "name": "Sam Blind Learner",
            "role": "student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Physics",
            "semester": 2,
            "is_disabled_student": True,
            "blind_companion_enabled": True
        })
        assert reg_b.status_code == 201
        cls.blind_user = reg_b.get_json()["user"]
        cls.blind_id = str(cls.blind_user.get("id") or cls.blind_user.get("user_id"))

        # Set up uploaded authoritative syllabus for the blind student
        cls.subject = "Applied Physics"
        cls.unit = "Optics and Wave Mechanics"
        cls.topic = "Total Internal Reflection"

        syl_doc = {
            "syllabus_id": f"syl_{uuid.uuid4().hex[:6]}",
            "student_id": cls.blind_id,
            "studentId": cls.blind_id,
            "semester": 2,
            "current_semester": 2,
            "status": "VALID",
            "validation_status": "VALID",
            "is_active": True,
            "subjects": [
                {"name": cls.subject, "code": "PH101"}
            ],
            "chapters": {
                cls.subject: [
                    {
                        "name": cls.unit,
                        "concepts": [cls.topic, "Snell's Law", "Brewster's Angle"]
                    }
                ]
            }
        }
        if db is not None:
            db.syllabi.insert_one(syl_doc)

    def test_01_user_disabled_status_isolation(self):
        """Verify normal student has blind_companion_enabled False, and blind student has True"""
        # Normal student profile
        res_n = self.normal_client.get('/api/auth/me')
        user_n = res_n.get_json().get("user", {})
        self.assertFalse(bool(user_n.get("is_disabled_student")))
        self.assertFalse(bool(user_n.get("blind_companion_enabled")))

        # Blind student profile
        res_b = self.blind_client.get('/api/auth/me')
        user_b = res_b.get_json().get("user", {})
        self.assertTrue(bool(user_b.get("is_disabled_student") or user_b.get("blind_companion_enabled")))

    def test_02_learning_gap_recording_and_retrieval(self):
        """Blind student can record practice attempt and retrieve authentic diagnosed learning gaps"""
        # Submit a low score practice attempt demonstrating a learning gap
        sub_res = self.blind_client.post('/api/blind-companion/practice/submit', json={
            "subject": self.subject,
            "unit": self.unit,
            "topic": self.topic,
            "score": 1.0,
            "max_score": 5.0,
            "is_correct": False,
            "question_text": "What happens when light strikes the interface beyond the critical angle?",
            "student_answer": "It refracts into the second medium",
            "expected_answer": "Total internal reflection occurs without any refraction",
            "feedback": "Incorrect. Confuses refraction with total internal reflection beyond the critical angle."
        })
        self.assertEqual(sub_res.status_code, 200)

        # Retrieve diagnosed gaps
        gaps_res = self.blind_client.get('/api/blind-companion/learning-gaps')
        self.assertEqual(gaps_res.status_code, 200)
        gaps_data = gaps_res.get_json()
        self.assertTrue(gaps_data.get("success"))
        gaps = gaps_data.get("learning_gaps", [])
        self.assertTrue(len(gaps) > 0)
        matching = [g for g in gaps if g.get("topic") == self.topic]
        self.assertTrue(len(matching) > 0)

    def test_03_adaptive_learning_path_prioritization(self):
        """Adaptive learning path prioritizes diagnosed learning gaps for authentic recovery"""
        path_res = self.blind_client.get(f'/api/blind-companion/learning-path?subject={self.subject}')
        self.assertEqual(path_res.status_code, 200)
        path_data = path_res.get_json()
        self.assertTrue(path_data.get("success"))
        steps = path_data.get("steps") or path_data.get("learning_path", {}).get("steps", [])
        self.assertTrue(len(steps) > 0)
        self.assertEqual(path_data.get("focus_topic"), self.topic)

    def test_04_teacher_portal_strict_isolation(self):
        """Teacher data and notifications are strictly unaffected by student blind companion actions"""
        # Check teacher notifications
        t_notifs = self.teacher_client.get('/api/notifications')
        self.assertEqual(t_notifs.status_code, 200)
        notifs_list = t_notifs.get_json().get("notifications", [])
        for n in notifs_list:
            self.assertNotIn("Blind Learning Companion", n.get("title", ""))
            self.assertNotIn(self.blind_email, n.get("message", ""))

    def test_05_reality_lab_safety_detection_simulation(self):
        """Simulate safety hazard keywords detection for electricity, chemicals, heat, and sharp objects"""
        test_activity_text = "Heat the acidic solution over the bunsen burner using a scalpel to slice the leaf."
        
        detected_hazards = []
        if any(w in test_activity_text.lower() for w in ["acid", "chemical", "flammable"]):
            detected_hazards.append("Chemical")
        if any(w in test_activity_text.lower() for w in ["heat", "burner", "flame", "boiling"]):
            detected_hazards.append("Thermal/Heat")
        if any(w in test_activity_text.lower() for w in ["voltage", "electric", "circuit", "wire"]):
            detected_hazards.append("Electrical")
        if any(w in test_activity_text.lower() for w in ["scalpel", "blade", "sharp", "knife"]):
            detected_hazards.append("Sharp Instruments")

        self.assertIn("Chemical", detected_hazards)
        self.assertIn("Thermal/Heat", detected_hazards)
        self.assertIn("Sharp Instruments", detected_hazards)
        self.assertNotIn("Electrical", detected_hazards)

if __name__ == '__main__':
    unittest.main()
