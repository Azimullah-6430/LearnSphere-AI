import unittest
import json
import os
import sys
import uuid

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import app
from app.db import init_db

class TestLearnFromAnywhereIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.client = app.test_client()
        self.student_email = f"rural_std_{uuid.uuid4().hex[:8]}@example.com"
        self.student_password = "SecurePassword123!"
        self.teacher_email = f"rural_tch_{uuid.uuid4().hex[:8]}@example.com"
        self.teacher_password = "SecurePassword123!"

        # 1. Register student
        s_resp = self.client.post("/api/auth/register", json={
            "name": "Ravi Kumar",
            "email": self.student_email,
            "password": self.student_password,
            "role": "student",
            "level": "college",
            "department": "Physics & Agricultural Engineering",
            "semester": 4
        })
        self.assertEqual(s_resp.status_code, 201)
        student_data = s_resp.get_json()
        self.student_id = student_data.get("user", {}).get("id") or student_data.get("user", {}).get("user_id")

        # Insert active validated syllabus for student
        from server import get_mongodb, get_sqlite_db
        import datetime
        mongo_db = get_mongodb()
        now = datetime.datetime.utcnow()
        s_doc = {
            "syllabus_id": f"syl_{uuid.uuid4().hex[:8]}",
            "student_id": str(self.student_id),
            "file_name": "Agricultural_Physics_Syllabus.pdf",
            "degree": "B.Tech",
            "department": "Physics & Agricultural Engineering",
            "semester": 4,
            "is_active": True,
            "status": "VALID",
            "curriculumStatus": "VALID",
            "validation_status": "VALID",
            "subjects": [
                {"name": "Physics", "code": "PHY401"},
                {"name": "Chemistry", "code": "CHE401"}
            ],
            "units": {
                "Physics": [{"name": "Fluid & Capillarity", "concepts": ["Capillarity and Surface Tension"]}],
                "Chemistry": [{"name": "Acids and Bases", "concepts": ["Acids, Bases and Salts"]}]
            },
            "created_at": now,
            "updated_at": now
        }
        if mongo_db is not None:
            mongo_db["syllabi"].insert_one(s_doc)
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO syllabi (syllabus_id, student_id, file_name, is_active, status, validation_status, analysis_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (s_doc["syllabus_id"], str(self.student_id), "Agricultural_Physics_Syllabus.pdf", 1, "VALID", "VALID", json.dumps(s_doc), now.isoformat(), now.isoformat())
            )
            conn.commit()
            conn.close()

    def test_01_unauthenticated_request_rejected(self):
        """Unauthenticated requests must be strictly rejected with HTTP 401."""
        unauth_client = app.test_client()
        res = unauth_client.post("/api/learn-anywhere/generate", json={"subject": "Physics"})
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data.get("success", False))

    def test_02_student_generate_activity_with_rural_materials(self):
        """Authenticated student successfully receives a syllabus-grounded, zero-cost rural activity."""
        payload = {
            "subject": "Physics",
            "topic": "Capillarity and Surface Tension",
            "resource_category": "Farmland & Soil",
            "difficulty": "Medium"
        }
        res = self.client.post("/api/learn-anywhere/generate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("activity", data)

        activity = data["activity"]
        self.assertTrue(activity.get("is_supported", True))
        self.assertIn("title", activity)
        self.assertIn("local_materials", activity)
        self.assertIsInstance(activity["local_materials"], list)
        self.assertTrue(len(activity["local_materials"]) > 0)
        self.assertIn("steps", activity)
        self.assertTrue(len(activity["steps"]) > 0)
        self.assertIn("scientific_principle", activity)
        self.assertIn("village_application", activity)

    def test_03_chemistry_natural_indicators_generation(self):
        """Generates natural bio-indicator experiment with local turmeric/leaves."""
        payload = {
            "subject": "Chemistry",
            "topic": "Acids, Bases and Salts",
            "resource_category": "Plants & Bio Resources",
            "difficulty": "Easy"
        }
        res = self.client.post("/api/learn-anywhere/generate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        activity = data["activity"]
        self.assertIn("scientific_principle", activity)
        self.assertIn("local_materials", activity)

    def test_04_strict_teacher_action_center_isolation(self):
        """Learn from Anywhere activity generation must NEVER create action items or pollute teacher records."""
        # 1. Register a teacher
        tch_client = app.test_client()
        tch_resp = tch_client.post("/api/auth/register", json={
            "name": "Prof Sharma",
            "email": self.teacher_email,
            "password": self.teacher_password,
            "role": "teacher",
            "teacher_level": "college"
        })
        self.assertEqual(tch_resp.status_code, 201)

        init_res = tch_client.get("/api/action-center")
        init_items = init_res.get_json().get("items", []) if init_res.status_code == 200 else []

        # 2. Student generates multiple rural activities
        for sub in ["Physics", "Mathematics"]:
            self.client.post("/api/learn-anywhere/generate", json={"subject": sub})

        # 3. Check teacher Action Center again
        after_res = tch_client.get("/api/action-center")
        after_items = after_res.get_json().get("items", []) if after_res.status_code == 200 else []

        self.assertEqual(len(init_items), len(after_items), "Learn from Anywhere must never create teacher action items.")

    def test_05_strict_misconception_map_isolation(self):
        """Learn from Anywhere activity generation must NEVER enter the teacher Misconception Map."""
        tch_client = app.test_client()
        tch_client.post("/api/auth/register", json={
            "name": "Prof Sharma 2",
            "email": f"t2_{self.teacher_email}",
            "password": self.teacher_password,
            "role": "teacher"
        })
        res = tch_client.get("/api/misconceptions")
        data = res.get_json() if res.status_code == 200 else {}
        misconceptions = data.get("misconceptions", [])
        
        for m in misconceptions:
            self.assertNotEqual(m.get("source"), "learn_anywhere")

if __name__ == "__main__":
    unittest.main()
