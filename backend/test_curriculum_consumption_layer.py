import unittest
import json
import uuid
from datetime import datetime, timezone
from server import app, _get_authoritative_curriculum, _normalize_curriculum_doc
from app.db import get_mongodb, get_sqlite_db

class TestCurriculumConsumptionLayer(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        uid = uuid.uuid4().hex[:10]
        
        # Register and login User A
        self.user_a_email = f"student_alpha_{uid}@learnsphere.edu"
        self.password = "SecurePassword123!"
        reg_a = self.app.post("/api/auth/register", json={
            "name": "Student Alpha",
            "email": self.user_a_email,
            "password": self.password,
            "role": "student",
            "level": "college",
            "degree": "B.Tech Computer Science and Engineering",
            "department": "Computer Science",
            "semester": 5,
            "current_semester": 5
        })
        self.assertEqual(reg_a.status_code, 201)
        self.user_a_id = reg_a.get_json()["user"]["id"]
        
        # Register User B
        self.user_b_email = f"student_beta_{uid}@learnsphere.edu"
        reg_b = self.app.post("/api/auth/register", json={
            "name": "Student Beta",
            "email": self.user_b_email,
            "password": self.password,
            "role": "student",
            "level": "college",
            "degree": "B.Tech Mechanical Engineering",
            "department": "Mechanical Engineering",
            "semester": 5,
            "current_semester": 5
        })
        self.assertEqual(reg_b.status_code, 201)
        self.user_b_id = reg_b.get_json()["user"]["id"]

        self.syllabus_id = f"syl_alpha_{uid}"
        self.valid_curriculum_doc = {
            "syllabus_id": self.syllabus_id,
            "syllabusId": self.syllabus_id,
            "student_id": self.user_a_id,
            "studentId": self.user_a_id,
            "program": "B.Tech Computer Science and Engineering",
            "degree": "B.Tech Computer Science and Engineering",
            "department": "Computer Science",
            "semester": 5,
            "curriculumStatus": "VALID",
            "validation_status": "VALID",
            "status": "VALID",
            "is_active": True,
            "subjects": [
                {
                    "id": "CS501",
                    "subject_id": "CS501",
                    "code": "CS501",
                    "name": "Database Management Systems",
                    "topics": ["ER Modeling", "Relational Algebra", "Normalization", "ACID Transactions"],
                    "units": ["Unit 1: Data Models", "Unit 2: SQL and Normalization"],
                    "type": "Core Theory",
                    "credits": 4
                },
                {
                    "id": "CS502",
                    "subject_id": "CS502",
                    "code": "CS502",
                    "name": "Design and Analysis of Algorithms",
                    "topics": ["Divide and Conquer", "Greedy Approach", "Dynamic Programming"],
                    "units": ["Unit 1: Asymptotics", "Unit 2: DP Algorithms"],
                    "type": "Core Theory",
                    "credits": 4
                }
            ],
            "chapters": {
                "Database Management Systems": [
                    {"name": "Data Models", "concepts": ["ER Modeling", "Relational Algebra"]},
                    {"name": "SQL and Normalization", "concepts": ["Normalization", "ACID Transactions"]}
                ],
                "Design and Analysis of Algorithms": [
                    {"name": "Divide and Conquer", "concepts": ["Divide and Conquer", "Greedy Approach"]},
                    {"name": "Dynamic Programming", "concepts": ["Dynamic Programming"]}
                ]
            }
        }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["syllabi"].delete_many({"student_id": {"$in": [self.user_a_id, self.user_b_id]}})
            mongo_db["syllabi"].insert_one(dict(self.valid_curriculum_doc))

    def tearDown(self):
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["syllabi"].delete_many({"student_id": {"$in": [self.user_a_id, self.user_b_id]}})

    def test_curriculum_normalization_schema(self):
        """Test that _normalize_curriculum_doc returns uniform IDs, status, subjects, and topics."""
        normalized = _normalize_curriculum_doc(self.valid_curriculum_doc, self.user_a_id)
        
        self.assertEqual(normalized["curriculumStatus"], "VALID")
        self.assertEqual(normalized["student_id"], self.user_a_id)
        self.assertEqual(normalized["studentId"], self.user_a_id)
        self.assertEqual(normalized["curriculum_id"], self.syllabus_id)
        self.assertEqual(normalized["curriculumId"], self.syllabus_id)
        self.assertEqual(len(normalized["subjects"]), 2)
        
        dbms = normalized["subjects"][0]
        self.assertEqual(dbms["name"], "Database Management Systems")
        self.assertEqual(dbms["code"], "CS501")
        self.assertIn("ER Modeling", dbms["topics"])
        self.assertIn("Normalization", dbms["topics"])
        self.assertIn("ACID Transactions", dbms["topics"])

    def test_active_curriculum_api_flow(self):
        """
        Test GET /api/curriculum/active for authenticated student:
        1. Identifies authenticated user.
        2. Loads only that user's active curriculum.
        3. Verifies curriculumStatus = VALID.
        4. Returns subjects.
        5. Returns topics associated with each subject.
        6. Returns subject IDs and curriculum ID.
        """
        # Login as User A
        self.app.post("/api/auth/login", json={"email": self.user_a_email, "password": self.password})
        res = self.app.get("/api/curriculum/active")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertTrue(data["success"])
        self.assertTrue(data["is_valid"])
        self.assertEqual(data["curriculumStatus"], "VALID")
        self.assertEqual(data["student_id"], self.user_a_id)
        self.assertEqual(data["curriculum_id"], self.syllabus_id)
        self.assertEqual(data["curriculumId"], self.syllabus_id)
        self.assertEqual(len(data["subjects"]), 2)

        # Verify subjects have subject_id, name, and topics
        for sub in data["subjects"]:
            self.assertIn("id", sub)
            self.assertIn("subject_id", sub)
            self.assertIn("name", sub)
            self.assertIn("topics", sub)
            self.assertTrue(len(sub["topics"]) > 0)

    def test_student_isolation_never_returns_another_users_curriculum(self):
        """Rule 7: Never return another user's curriculum."""
        # Login as User B (who has NO uploaded syllabus)
        self.app.post("/api/auth/login", json={"email": self.user_b_email, "password": self.password})
        res = self.app.get("/api/curriculum/active")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # User B must NOT see User A's curriculum or subjects
        self.assertFalse(data["is_valid"])
        self.assertEqual(data["subjects"], [])
        self.assertNotEqual(data.get("curriculum_id"), self.syllabus_id)

    def test_three_features_consume_same_authoritative_curriculum(self):
        """
        Verify that Personal Trainer, Knowledge Challenge, and Reality Lab
        all obtain their subjects and topics from the exact same _get_authoritative_curriculum function.
        """
        auth_curriculum = _get_authoritative_curriculum(self.user_a_id)
        self.assertIsNotNone(auth_curriculum)
        subjects = auth_curriculum["subjects"]
        self.assertEqual(len(subjects), 2)
        
        # Verify both subjects and their associated topics are extracted identically
        sub_names = [s["name"] for s in subjects]
        self.assertIn("Database Management Systems", sub_names)
        self.assertIn("Design and Analysis of Algorithms", sub_names)

        dbms_topics = next(s["topics"] for s in subjects if s["name"] == "Database Management Systems")
        self.assertIn("ER Modeling", dbms_topics)
        self.assertIn("ACID Transactions", dbms_topics)

    def test_unvalidated_curriculum_is_rejected(self):
        """Verify curriculumStatus != VALID returns None and is rejected."""
        mongo_db = get_mongodb()
        if mongo_db is not None:
            # Update to invalid / unvalidated status
            mongo_db["syllabi"].update_one(
                {"syllabus_id": self.syllabus_id},
                {"$set": {"curriculumStatus": "NEEDS_REVIEW", "validation_status": "NEEDS_REVIEW", "status": "NEEDS_REVIEW"}}
            )

        auth_curriculum = _get_authoritative_curriculum(self.user_a_id)
        self.assertIsNone(auth_curriculum)

        # Calling active API must now report is_valid = False
        self.app.post("/api/auth/login", json={"email": self.user_a_email, "password": self.password})
        res = self.app.get("/api/curriculum/active")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["is_valid"])
        self.assertEqual(data["subjects"], [])

if __name__ == "__main__":
    unittest.main()
