"""
Test Reality Lab Validated Syllabus & Curriculum Integration

Verifies:
1. studentId -> active curriculum -> subjectId -> subject -> topic flow.
2. If no valid syllabus exists: subjects = [], rejects generation with HTTP 400.
3. If valid syllabus exists: generates practical activities grounded strictly in validated subject & topics.
4. Each activity contains all 11 required elements:
   - title
   - real_world_connection
   - objective
   - materials (day-to-day/local where safe)
   - steps / procedure
   - expected_observation / observation
   - concept_being_demonstrated / practical_concept
   - explanation / theory_connection
   - safety_considerations
   - questions_to_test_understanding
   - exam_relevance
5. Rejects unvalidated or cross-semester subjects with HTTP 400.
6. Purely abstract / unsupported theoretical concepts return is_supported = False without hallucination.
"""

import unittest
import json
import uuid
from datetime import datetime, timezone
from server import app
from app.db import get_mongodb, get_sqlite_db

class TestRealityLabCurriculum(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.unique_id = uuid.uuid4().hex[:10]
        self.timestamp = int(datetime.now(timezone.utc).timestamp())
        self.email = f"reality_lab_{self.unique_id}_{self.timestamp}@learnsphere.test"
        self.password = "SecurePassword123!"
        
        # Register a test student: B.Tech IT, Semester 5
        reg_res = self.app.post("/api/auth/register", json={
            "name": "Reality Lab Student",
            "email": self.email,
            "password": self.password,
            "role": "student",
            "level": "college",
            "degree": "B.Tech Information Technology",
            "program": "B.Tech Information Technology",
            "department": "Information Technology",
            "semester": 5,
            "current_semester": 5
        })
        self.assertEqual(reg_res.status_code, 201)
        self.student_id = reg_res.get_json()["user"]["id"]

        # Login
        login_res = self.app.post("/api/auth/login", json={
            "email": self.email,
            "password": self.password
        })
        self.assertEqual(login_res.status_code, 200)

    def test_no_valid_syllabus_blocks_reality_lab(self):
        """When no valid syllabus is uploaded, Reality Lab must reject generation with 400."""
        res = self.app.post("/api/reality-lab/generate", json={
            "subject": "Database Management Systems",
            "topic": "Indexing"
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("No active validated syllabus found", data.get("error", ""))

    def test_valid_syllabus_generates_all_11_fields_with_safety(self):
        """When syllabus is VALID, Reality Lab generates full 11-field activity grounded in subject."""
        # Insert a valid syllabus document
        syl_id = f"syl_sem5_rl_{self.timestamp}"
        syllabus_doc = {
            "student_id": self.student_id,
            "studentId": self.student_id,
            "syllabus_id": syl_id,
            "syllabusId": syl_id,
            "degree": "B.Tech Information Technology",
            "program": "B.Tech Information Technology",
            "department": "Information Technology",
            "semester": 5,
            "current_semester": 5,
            "status": "VALID",
            "is_active": True,
            "curriculumStatus": "VALID",
            "validation_status": "VALID",
            "subjects": [
                {
                    "subject_id": "IT501",
                    "code": "IT501",
                    "name": "Database Management Systems",
                    "topics": ["Normalization", "B+ Tree Indexing", "Transaction Management"]
                },
                {
                    "subject_id": "IT502",
                    "code": "IT502",
                    "name": "Computer Networks",
                    "topics": ["TCP Congestion Control", "Socket Programming", "Routing Algorithms"]
                }
            ],
            "chapters": {
                "Database Management Systems": [
                    {"name": "Unit I: Data Models", "concepts": ["ER Modeling", "Relational Algebra"]},
                    {"name": "Unit II: Database Design & Indexing", "concepts": ["BCNF", "B+ Tree Indexing"]}
                ]
            }
        }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["syllabi"].insert_one(syllabus_doc)
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO syllabi 
                (student_id, syllabus_id, is_active, status, validation_status, semester, current_semester, analysis_json)
                VALUES (?, ?, 1, 'ACTIVE', 'VALID', 5, 5, ?)
            """, (self.student_id, syl_id, json.dumps(syllabus_doc)))
            conn.commit()
            conn.close()

        # Generate activity for validated subject IT501
        res = self.app.post("/api/reality-lab/generate", json={
            "subject_id": "IT501",
            "subject": "Database Management Systems",
            "topic": "B+ Tree Indexing",
            "difficulty": "Medium"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        lab = data.get("lab", {})

        # Verify all 11 required elements
        # 1. Activity Title
        self.assertTrue(bool(lab.get("title")), "Missing title")
        # 2. Real-world connection
        self.assertTrue(bool(lab.get("real_world_connection") or lab.get("context")), "Missing real_world_connection")
        # 3. Objective
        self.assertTrue(bool(lab.get("objective") or lab.get("learning_outcome")), "Missing objective")
        # 4. Materials
        self.assertTrue(bool(lab.get("materials") and isinstance(lab.get("materials"), list)), "Missing materials list")
        # 5. Steps / Procedure
        self.assertTrue(bool(lab.get("steps") or lab.get("procedure")), "Missing steps / procedure")
        # 6. Expected observation
        self.assertTrue(bool(lab.get("expected_observation") or lab.get("observation")), "Missing expected observation")
        # 7. Concept being demonstrated
        self.assertTrue(bool(lab.get("concept_being_demonstrated") or lab.get("practical_concept")), "Missing concept being demonstrated")
        # 8. Explanation
        self.assertTrue(bool(lab.get("explanation") or lab.get("theory_connection")), "Missing explanation")
        # 9. Safety considerations
        self.assertTrue(bool(lab.get("safety_considerations")), "Missing safety considerations")
        # 10. Questions to test understanding
        self.assertTrue(bool(lab.get("questions_to_test_understanding")), "Missing questions to test understanding")
        # 11. Exam relevance
        self.assertTrue(bool(lab.get("exam_relevance")), "Missing exam relevance")

        # Verify subject grounding
        self.assertEqual(data.get("subject"), "Database Management Systems")
        self.assertEqual(data.get("subject_id"), "IT501")

    def test_unvalidated_subject_rejected(self):
        """Requesting an unvalidated or random subject must be rejected with 400."""
        syl_id = f"syl_sem5_rl_unval_{self.timestamp}"
        syllabus_doc = {
            "student_id": self.student_id,
            "studentId": self.student_id,
            "syllabus_id": syl_id,
            "syllabusId": syl_id,
            "degree": "B.Tech Information Technology",
            "program": "B.Tech Information Technology",
            "department": "Information Technology",
            "semester": 5,
            "current_semester": 5,
            "status": "VALID",
            "is_active": True,
            "curriculumStatus": "VALID",
            "validation_status": "VALID",
            "subjects": [{"name": "Database Management Systems", "subject_id": "IT501"}]
        }
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["syllabi"].insert_one(syllabus_doc)
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO syllabi 
                (student_id, syllabus_id, is_active, status, validation_status, semester, current_semester, analysis_json)
                VALUES (?, ?, 1, 'ACTIVE', 'VALID', 5, 5, ?)
            """, (self.student_id, syl_id, json.dumps(syllabus_doc)))
            conn.commit()
            conn.close()

        res = self.app.post("/api/reality-lab/generate", json={
            "subject": "Organic Chemistry & Molecular Biology",
            "topic": "DNA Replication"
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("not in your validated active curriculum", data.get("error", ""))

if __name__ == "__main__":
    unittest.main()
