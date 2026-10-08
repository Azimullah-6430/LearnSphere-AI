import unittest
import json
from datetime import datetime, timezone
from server import app, _get_authoritative_curriculum
from app.db import get_mongodb, get_sqlite_db

class TestKnowledgeChallengeCurriculum(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.timestamp = int(datetime.now(timezone.utc).timestamp())
        self.student_email = f"kc_student_{self.timestamp}@learnsphere.edu"
        self.password = "SecurePassword123!"

        # Register user: B.Tech IT, Semester 5
        reg_res = self.app.post("/api/auth/register", json={
            "name": "KC Test Student",
            "email": self.student_email,
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
            "email": self.student_email,
            "password": self.password
        })
        self.assertEqual(login_res.status_code, 200)

        # Insert valid semester 5 curriculum
        self.syllabus_id = f"syl_sem5_kc_{self.timestamp}"
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["syllabi"].insert_one({
                "syllabus_id": self.syllabus_id,
                "student_id": self.student_id,
                "studentId": self.student_id,
                "semester": 5,
                "degree": "B.Tech Information Technology",
                "department": "Information Technology",
                "curriculumStatus": "VALID",
                "validation_status": "VALID",
                "status": "VALID",
                "is_active": True,
                "subjects": [
                    {
                        "subject_id": "IT501",
                        "code": "IT501",
                        "name": "Database Management Systems",
                        "type": "Theory Core",
                        "credits": 4
                    },
                    {
                        "subject_id": "IT502",
                        "code": "IT502",
                        "name": "Computer Networks & Protocols",
                        "type": "Theory Core",
                        "credits": 4
                    }
                ],
                "chapters": {
                    "Database Management Systems": [
                        {"name": "Unit 1: Relational Model & SQL", "concepts": ["Relational Algebra", "SQL Queries", "Normal Forms"]},
                        {"name": "Unit 2: Transaction Processing", "concepts": ["ACID Properties", "Concurrency Control", "Locking"]}
                    ],
                    "Computer Networks & Protocols": [
                        {"name": "Unit 1: Physical & Data Link Layer", "concepts": ["Framing", "Error Detection", "Flow Control"]}
                    ]
                },
                "updated_at": datetime.now(timezone.utc),
                "version": 1
            })
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO syllabi (syllabus_id, student_id, semester, status, validation_status, is_active, version, analysis_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self.syllabus_id,
                    self.student_id,
                    5,
                    "VALID",
                    "VALID",
                    1,
                    1,
                    json.dumps({
                        "subjects": [
                            {"subject_id": "IT501", "code": "IT501", "name": "Database Management Systems", "type": "Theory Core", "credits": 4},
                            {"subject_id": "IT502", "code": "IT502", "name": "Computer Networks & Protocols", "type": "Theory Core", "credits": 4}
                        ],
                        "chapters": {
                            "Database Management Systems": [
                                {"name": "Unit 1: Relational Model & SQL", "concepts": ["Relational Algebra", "SQL Queries", "Normal Forms"]}
                            ]
                        }
                    })
                )
            )
            conn.commit()
            conn.close()

    def tearDown(self):
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["users"].delete_many({"$or": [{"user_id": self.student_id}, {"email": self.student_email}]})
            mongo_db["syllabi"].delete_many({"$or": [{"student_id": self.student_id}, {"studentId": self.student_id}]})
            mongo_db["knowledge_challenges"].delete_many({"student_id": self.student_id})

    def test_knowledge_challenge_authoritative_retrieval(self):
        """Knowledge challenge quiz endpoint retrieves only validated subjects and topics."""
        res = self.app.get(f"/api/challenge/quiz?subject=Database+Management+Systems&subject_id=IT501&difficulty=Medium")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("subject_id"), "IT501")
        self.assertIn("Database Management Systems", data.get("subjects", []))
        self.assertIn("Relational Algebra", data.get("topics", []))
        
        quiz = data.get("quiz", {})
        questions = quiz.get("questions", [])
        self.assertEqual(len(questions), 5)
        for q in questions:
            self.assertEqual(q.get("subject_id"), "IT501")
            self.assertTrue(bool(q.get("question")))
            self.assertTrue(bool(q.get("correct_answer")))
            self.assertTrue(bool(q.get("explanation")))

    def test_knowledge_challenge_blank_when_no_valid_curriculum(self):
        """When no valid curriculum exists, quiz endpoint returns 400 with empty subjects & topics."""
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["syllabi"].delete_many({"$or": [{"student_id": self.student_id}, {"studentId": self.student_id}]})
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM syllabi WHERE student_id=?", (self.student_id,))
            conn.commit()
            conn.close()

        res = self.app.get("/api/challenge/quiz?subject=Database+Management+Systems")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertEqual(data.get("subjects"), [])
        self.assertEqual(data.get("topics"), [])

    def test_knowledge_challenge_tracks_submission(self):
        """Challenge submission tracks subjectId, topicId, question, student answer, correct answer, score, timestamp."""
        res = self.app.post("/api/challenge/submit", json={
            "subject": "Database Management Systems",
            "subject_id": "IT501",
            "topic_id": "top_IT501_1",
            "question": "What is the primary objective of relational algebra?",
            "student_answer": "To provide a theoretical foundation for relational queries.",
            "correct_answer": "To provide a theoretical foundation for relational queries.",
            "explanation": "Relational algebra defines formal procedural query operators.",
            "difficulty": "Medium",
            "score": 90,
            "total_questions": 100
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("subject_id"), "IT501")
        self.assertEqual(data.get("topic_id"), "top_IT501_1")
        self.assertEqual(data.get("score"), 90)
        self.assertTrue(bool(data.get("timestamp")))

if __name__ == "__main__":
    unittest.main()
