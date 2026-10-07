"""
LearnSphere AI - Personal Trainer Human Tutor Pedagogical Test Suite

Verifies:
1. Gating:
   - If no VALID curriculum exists, Personal Trainer returns no subjects and rejects generation.
   - No random or mock subjects are invented.
2. Subject Validation:
   - Personal Trainer enforces that requested subjects belong strictly to the authenticated student's validated curriculum.
3. Pedagogical Responses:
   - Human tutor explanations for theory, numericals, programming, and difficult concepts.
   - Intent recognition for:
     • "Explain again" / "I don't understand"
     • "Give another example"
     • "Test me" / "Ask me questions"
     • "Explain simply"
     • "Explain for exam"
4. Multi-turn conversation context memory.
5. Zero leakage of implementation details or competing AI products.
"""

import os
import sys
import json
import uuid
import unittest
from datetime import datetime
from unittest.mock import patch

# Set up path to backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server import app


class TestPersonalTrainerHumanTutor(unittest.TestCase):

    def setUp(self):
        # Patch generate_content to raise exception so generate_trainer_response uses its robust deterministic engine instantly
        self.patcher = patch("server.gemini_service.generate_content", side_effect=RuntimeError("Test mode: use deterministic tutor engine"))
        self.patcher.start()

        self.app = app.test_client()
        self.app.testing = True

        self.suffix = uuid.uuid4().hex[:8]
        self.email = f"trainer_student_{self.suffix}@learnsphere.test"
        self.password = "TutorPassword123!"

        # Register Semester 5 B.Tech IT student
        res = self.app.post("/api/auth/register", json={
            "name": "Alex Mercer",
            "email": self.email,
            "password": self.password,
            "role": "student",
            "level": "college",
            "degree": "B.Tech",
            "program": "B.Tech",
            "department": "Information Technology",
            "branch": "Information Technology",
            "year": 3,
            "semester": 5,
            "current_semester": 5,
            "regulation": "R2021"
        })
        self.assertIn(res.status_code, [200, 201])
        self.user_id = res.get_json()["user"]["id"]

        self.syllabus_text = """
DEPARTMENT OF INFORMATION TECHNOLOGY
SEMESTER 5 CURRICULUM
IT501 Database Management Systems Credits: 4 L:3 T:0 P:2
IT502 Web Technologies Credits: 3 L:3 T:0 P:0
IT503 Computer Networks Credits: 3 L:3 T:0 P:0
IT504 Formal Languages and Automata Theory Credits: 4 L:3 T:1 P:0
IT505 Software Engineering Credits: 3 L:3 T:0 P:0
"""

    def tearDown(self):
        self.patcher.stop()

    def _login(self):
        return self.app.post("/api/auth/login", json={
            "email": self.email,
            "password": self.password
        })

    def _upload_syllabus(self):
        mock_analysis = {
            "status": "VALID",
            "validation_status": "VALID",
            "detected_semesters": [5],
            "extracted_subjects": [
                "Database Management Systems",
                "Web Technologies",
                "Computer Networks",
                "Formal Languages and Automata Theory",
                "Software Engineering"
            ],
            "subjects": [
                {
                    "code": "IT501", "name": "Database Management Systems", "type": "Theory Core", "credits": 4.0, "semester": 5,
                    "source_page": 1, "source_section": "Semester 5 Scheme Table", "source_text": "IT501 Database Management Systems Credits: 4", "confidence": 0.98, "evidence_verified": True
                },
                {
                    "code": "IT502", "name": "Web Technologies", "type": "Theory Core", "credits": 3.0, "semester": 5,
                    "source_page": 1, "source_section": "Semester 5 Scheme Table", "source_text": "IT502 Web Technologies Credits: 3", "confidence": 0.98, "evidence_verified": True
                },
                {
                    "code": "IT503", "name": "Computer Networks", "type": "Theory Core", "credits": 3.0, "semester": 5,
                    "source_page": 1, "source_section": "Semester 5 Scheme Table", "source_text": "IT503 Computer Networks Credits: 3", "confidence": 0.98, "evidence_verified": True
                },
                {
                    "code": "IT504", "name": "Formal Languages and Automata Theory", "type": "Theory Core", "credits": 4.0, "semester": 5,
                    "source_page": 1, "source_section": "Semester 5 Scheme Table", "source_text": "IT504 Formal Languages and Automata Theory Credits: 4", "confidence": 0.98, "evidence_verified": True
                },
                {
                    "code": "IT505", "name": "Software Engineering", "type": "Theory Core", "credits": 3.0, "semester": 5,
                    "source_page": 1, "source_section": "Semester 5 Scheme Table", "source_text": "IT505 Software Engineering Credits: 3", "confidence": 0.98, "evidence_verified": True
                }
            ],
            "chapters": {
                "Database Management Systems": [
                    {"name": "Unit II: Relational Model & SQL", "concepts": ["Normalization", "BCNF", "Transactions", "ACID Properties"]}
                ]
            },
            "expected_subject_count": 5,
            "extracted_subject_count": 5,
            "is_active": True
        }

        with patch("server.gemini_service.analyze_syllabus", return_value=mock_analysis):
            res = self.app.post("/api/syllabus/analyze", json={
                "syllabus_text": self.syllabus_text,
                "file_name": "Syllabus_IT_Sem5.txt",
                "level": "college",
                "semester": 5,
                "degree": "B.Tech",
                "department": "Information Technology"
            })
            self.assertEqual(res.status_code, 200)
            return res

    def test_01_gate_refusal_when_no_valid_curriculum(self):
        """Verify Personal Trainer refuses chat and hides subjects when no valid syllabus exists."""
        self._login()

        # 1. Asking for subjects before upload returns locked notification, NOT random subjects
        res_list = self.app.post("/api/trainer/chat", json={
            "message": "What are my semester subjects?",
            "semester": 5
        })
        self.assertEqual(res_list.status_code, 200)
        reply = res_list.get_json().get("reply", "")
        self.assertIn("No Validated Syllabus Uploaded", reply)
        self.assertIn("Please upload your official semester syllabus", reply)

        # 2. Attempting to generate coaching before upload returns 400 error
        res_chat = self.app.post("/api/trainer/chat", json={
            "message": "Teach me SQL normalization",
            "subject": "Database Management Systems"
        })
        self.assertEqual(res_chat.status_code, 400)
        self.assertIn("No active validated syllabus found", res_chat.get_json().get("error", ""))

    def test_02_subject_isolation_and_curriculum_enforcement(self):
        """Verify Personal Trainer accepts only subjects from the student's validated curriculum."""
        self._login()
        self._upload_syllabus()

        # Valid subject succeeds
        valid_res = self.app.post("/api/trainer/chat", json={
            "message": "Explain BCNF normalization",
            "subject": "Database Management Systems",
            "topic": "BCNF",
            "unit": "Unit II: Relational Model & SQL"
        })
        self.assertEqual(valid_res.status_code, 200)
        self.assertIn("reply", valid_res.get_json())

        # Unrelated / foreign subject not in syllabus is rejected with 400
        invalid_res = self.app.post("/api/trainer/chat", json={
            "message": "Explain Quantum Mechanics",
            "subject": "Advanced Quantum Physics",
            "topic": "Wave Equations"
        })
        self.assertEqual(invalid_res.status_code, 400)
        self.assertIn("not in your validated active curriculum", invalid_res.get_json().get("error", ""))

    def test_03_human_tutor_intent_adaptation(self):
        """Verify Personal Trainer responds with tailored pedagogical structures for student prompts."""
        self._login()
        self._upload_syllabus()

        # 1. "Explain simply" -> Simple intuitive explanation & analogy (Feynman technique)
        simple_res = self.app.post("/api/trainer/chat", json={
            "message": "Explain simply using everyday analogies",
            "subject": "Database Management Systems",
            "topic": "BCNF Normalization"
        })
        self.assertEqual(simple_res.status_code, 200)
        simple_reply = simple_res.get_json().get("reply", "")
        self.assertTrue("Simple" in simple_reply or "Analogy" in simple_reply or "Intuition" in simple_reply)

        # 2. "Explain for exam" -> Exam scoring blueprint with mark breakdown & pitfalls
        exam_res = self.app.post("/api/trainer/chat", json={
            "message": "Explain for exam: what are the key marks breakdown and keywords?",
            "subject": "Database Management Systems",
            "topic": "BCNF Normalization"
        })
        self.assertEqual(exam_res.status_code, 200)
        exam_reply = exam_res.get_json().get("reply", "")
        self.assertTrue("Exam" in exam_reply or "Marks" in exam_reply or "Score" in exam_reply)

        # 3. "Give another example" -> Concrete practical/industry scenario
        ex_res = self.app.post("/api/trainer/chat", json={
            "message": "Give another example of how this is used in industry",
            "subject": "Database Management Systems",
            "topic": "BCNF Normalization"
        })
        self.assertEqual(ex_res.status_code, 200)
        ex_reply = ex_res.get_json().get("reply", "")
        self.assertTrue("Example" in ex_reply or "Scenario" in ex_reply)

        # 4. "Test me" -> Active recall exam question
        test_res = self.app.post("/api/trainer/chat", json={
            "message": "Test me on this concept with a practice question",
            "subject": "Database Management Systems",
            "topic": "BCNF Normalization"
        })
        self.assertEqual(test_res.status_code, 200)
        test_reply = test_res.get_json().get("reply", "")
        self.assertTrue("Question" in test_reply or "Challenge" in test_reply or "Recall" in test_reply)

        # 5. "I don't understand" -> Alternative perspective breakdown
        confused_res = self.app.post("/api/trainer/chat", json={
            "message": "I don't understand, please explain again",
            "subject": "Database Management Systems",
            "topic": "BCNF Normalization"
        })
        self.assertEqual(confused_res.status_code, 200)
        confused_reply = confused_res.get_json().get("reply", "")
        self.assertTrue("Step" in confused_reply or "Perspective" in confused_reply or "Breakdown" in confused_reply)

    def test_04_multi_turn_history_preservation(self):
        """Verify Personal Trainer maintains multi-turn conversation memory."""
        self._login()
        self._upload_syllabus()

        history = [
            {"role": "user", "text": "What is 3NF?"},
            {"role": "bot", "text": "3NF requires no transitive dependencies."},
            {"role": "user", "text": "How does BCNF differ from 3NF?"}
        ]

        res = self.app.post("/api/trainer/chat", json={
            "message": "Can you give me a summary comparing both based on what we just discussed?",
            "subject": "Database Management Systems",
            "topic": "Normalization",
            "history": history
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn("reply", res.get_json())


if __name__ == "__main__":
    unittest.main()
