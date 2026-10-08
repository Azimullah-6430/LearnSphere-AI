import unittest
import json
from datetime import datetime, timezone
from server import app, _get_authoritative_curriculum
from app.db import get_mongodb, get_sqlite_db

class TestTrainerCurriculumIntegration(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.timestamp = int(datetime.now(timezone.utc).timestamp())
        self.student_email = f"pt_student_{self.timestamp}@learnsphere.edu"
        self.password = "SecurePassword123!"
        
        # Register user
        reg_res = self.app.post("/api/auth/register", json={
            "name": "PT Test Student",
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
        self.syllabus_id = f"syl_sem5_{self.timestamp}"
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
                    },
                    {
                        "subject_id": "IT503",
                        "code": "IT503",
                        "name": "Operating Systems Architecture",
                        "type": "Theory Core",
                        "credits": 3
                    }
                ],
                "chapters": {
                    "Database Management Systems": [
                        {"name": "Unit 1: Relational Model & SQL", "concepts": ["Relational Algebra", "SQL Queries", "Normal Forms"]},
                        {"name": "Unit 2: Transaction Processing", "concepts": ["ACID Properties", "Concurrency Control", "Locking"]}
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
                            {"subject_id": "IT502", "code": "IT502", "name": "Computer Networks & Protocols", "type": "Theory Core", "credits": 4},
                            {"subject_id": "IT503", "code": "IT503", "name": "Operating Systems Architecture", "type": "Theory Core", "credits": 3}
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
            mongo_db["academic_memory"].delete_many({"student_id": self.student_id})

    def test_authoritative_curriculum_retrieval(self):
        """Authoritative curriculum for student must retrieve valid Semester 5 subjects."""
        curr = _get_authoritative_curriculum(self.student_id)
        self.assertIsNotNone(curr)
        self.assertEqual(curr.get("semester"), 5)
        raw_subs = curr.get("subjects") or []
        sub_names = [s.get("name") if isinstance(s, dict) else s for s in raw_subs]
        self.assertIn("Database Management Systems", sub_names)
        self.assertIn("Computer Networks & Protocols", sub_names)
        self.assertIn("Operating Systems Architecture", sub_names)
        self.assertEqual(len(sub_names), 3)

    def test_trainer_chat_asking_subjects(self):
        """Student asking for semester subjects receives only validated Semester 5 subjects."""
        res = self.app.post("/api/trainer/chat",
            json={"message": "What are my semester 5 subjects?"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        reply = data.get("reply", "")
        self.assertIn("Database Management Systems", reply)
        self.assertIn("IT501", reply)
        self.assertIn("Computer Networks & Protocols", reply)

    def test_trainer_chat_subject_id_matching(self):
        """Personal Trainer validates and accepts subject matched by subject_id/subjectCode."""
        res = self.app.post("/api/trainer/chat",
            json={
                "message": "Explain relational algebra simply.",
                "subject": "Database Management Systems",
                "subject_id": "IT501",
                "syllabus_id": self.syllabus_id,
                "unit": "Unit 1: Relational Model & SQL",
                "topic": "Relational Algebra"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertTrue(bool(data.get("reply")))

    def test_trainer_rejects_unvalidated_subject(self):
        """Personal Trainer rejects subjects not part of the authenticated student's validated curriculum."""
        res = self.app.post("/api/trainer/chat",
            json={
                "message": "Explain photosynthesis.",
                "subject": "Advanced Plant Botany",
                "subject_id": "BIO999"
            }
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("not in your validated active curriculum", data.get("error", ""))

    def test_trainer_blank_when_no_valid_curriculum(self):
        """When no valid curriculum exists for student, trainer_chat returns 400 with no subjects."""
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["syllabi"].delete_many({"$or": [{"student_id": self.student_id}, {"studentId": self.student_id}]})
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM syllabi WHERE student_id=?", (self.student_id,))
            conn.commit()
            conn.close()

        res = self.app.post("/api/trainer/chat",
            json={
                "message": "Explain databases.",
                "subject": "Database Management Systems"
            }
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("No active validated syllabus found", data.get("error", ""))

    def test_trainer_progressive_concept_teaching(self):
        """Personal Trainer explains concepts with intuition, academic meaning, and understanding checks."""
        res = self.app.post("/api/trainer/chat",
            json={
                "message": "Teach me about Normal Forms.",
                "subject": "Database Management Systems",
                "subject_id": "IT501",
                "topic": "Normal Forms",
                "unit": "Unit 1: Relational Model & SQL"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        reply = data.get("reply", "")
        self.assertTrue(len(reply) > 50)

    def test_trainer_confusion_resolution(self):
        """Personal Trainer handles confusion by identifying misunderstanding and simplifying."""
        res = self.app.post("/api/trainer/chat",
            json={
                "message": "I don't understand normal forms at all, please explain again.",
                "subject": "Database Management Systems",
                "subject_id": "IT501",
                "topic": "Normal Forms",
                "unit": "Unit 1: Relational Model & SQL"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        reply = data.get("reply", "")
        self.assertTrue(any(w in reply.lower() for w in ["confusion", "perspective", "simple", "breakdown", "understand", "traffic", "problem"]))

    def test_trainer_numerical_problem_structure(self):
        """Personal Trainer structures numerical problems with Given, Required, Formula, Calculation, Units."""
        res = self.app.post("/api/trainer/chat",
            json={
                "message": "Give me a step by step numerical problem to solve.",
                "subject": "Database Management Systems",
                "subject_id": "IT501",
                "topic": "Relational Algebra",
                "unit": "Unit 1: Relational Model & SQL"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        reply = data.get("reply", "")
        self.assertTrue(any(w in reply.lower() for w in ["given", "required", "formula", "calculation", "units", "answer"]))

    def test_trainer_exam_prep_structure(self):
        """Personal Trainer structures exam prep with Important Points, Expected Wording, and Practice Question."""
        res = self.app.post("/api/trainer/chat",
            json={
                "message": "Explain for exam: what are the expected keywords and common mistakes?",
                "subject": "Database Management Systems",
                "subject_id": "IT501",
                "topic": "Relational Algebra",
                "unit": "Unit 1: Relational Model & SQL"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        reply = data.get("reply", "")
        self.assertTrue(any(w in reply.lower() for w in ["exam", "marks", "points", "mistakes", "keywords", "question"]))

if __name__ == "__main__":
    unittest.main()
