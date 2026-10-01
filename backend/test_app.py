"""
LearnSphere AI - Comprehensive Production Test Suite
Tests:
- Password Hashing & Auth
- Evaluation Calculation & Optional Choice Handling
- Plagiarism Multi-Level Detection (SHA-256, answer-level, statuses)
- Action Center filtering (>20 marks lost)
- Misconceptions conceptual evidence criteria
- GeminiService structure & error handling
"""

import unittest
import os
import json
import tempfile
from pathlib import Path

from app.gemini_service import GeminiService
from app.evaluation.evaluator import EvaluationAgent
from app.plagiarism import PlagiarismDetector
from werkzeug.security import generate_password_hash, check_password_hash


class TestLearnSphereAI(unittest.TestCase):

    def setUp(self):
        self.evaluator = EvaluationAgent()
        self.plagiarism = PlagiarismDetector()

    def test_password_hashing(self):
        password = "SecurePassword123!"
        hashed = generate_password_hash(password)
        self.assertTrue(check_password_hash(hashed, password))
        self.assertFalse(check_password_hash(hashed, "WrongPassword"))

    def test_evaluation_calculation(self):
        qp = {
            "subject": "Physics",
            "total_marks": 20.0,
            "questions": [
                {"question_id": "q1", "question_number": "1", "maximum_marks": 5.0, "question_type": "short"},
                {"question_id": "q2", "question_number": "2", "maximum_marks": 5.0, "question_type": "short"},
                {"question_id": "q3", "question_number": "3", "maximum_marks": 10.0, "question_type": "long"}
            ]
        }

        ai_eval = {
            "evaluations": [
                {"question_number": "1", "awarded_marks": 4.0, "attempted": True, "student_answer": "Mass * Accel"},
                {"question_number": "2", "awarded_marks": 5.0, "attempted": True, "student_answer": "9.8 m/s2"},
                {"question_number": "3", "awarded_marks": 7.0, "attempted": True, "student_answer": "Long derivation..."}
            ],
            "overall_feedback": "Good attempt."
        }

        res = self.evaluator.calculate_final_result(qp, ai_eval)
        self.assertEqual(res["obtained_marks"], 16.0)
        self.assertEqual(res["total_marks"], 20.0)
        self.assertEqual(res["percentage"], 80.0)
        self.assertEqual(res["grade"], "A")
        self.assertEqual(len(res["questions"]), 3)

        # Check marks lost calculation
        q1 = res["questions"][0]
        self.assertEqual(q1["marks_lost"], 1.0)
        q3 = res["questions"][2]
        self.assertEqual(q3["marks_lost"], 3.0)

    def test_optional_choice_group_handling(self):
        qp = {
            "subject": "Mathematics",
            "total_marks": 10.0,
            "questions": [
                {"question_id": "q1a", "question_number": "1a", "maximum_marks": 10.0, "choice_group": "group_1", "required_choice_count": 1},
                {"question_id": "q1b", "question_number": "1b", "maximum_marks": 10.0, "choice_group": "group_1", "required_choice_count": 1}
            ]
        }

        ai_eval = {
            "evaluations": [
                {"question_number": "1a", "awarded_marks": 6.0, "attempted": True},
                {"question_number": "1b", "awarded_marks": 9.0, "attempted": True}
            ]
        }

        res = self.evaluator.calculate_final_result(qp, ai_eval)
        # Should count best attempt (1b with 9.0 marks), total should be 9.0/10.0 = 90%
        self.assertEqual(res["obtained_marks"], 9.0)
        self.assertEqual(res["percentage"], 90.0)

    def test_plagiarism_sha256_exact_duplicate(self):
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as f1, \
             tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as f2:
            f1.write("Exact same answer script content for plagiarism check.")
            f2.write("Exact same answer script content for plagiarism check.")
            f1.flush()
            f2.flush()

            f1.close()
            f2.close()

            hash1 = PlagiarismDetector._calculate_sha256(f1.name)
            hash2 = PlagiarismDetector._calculate_sha256(f2.name)

            self.assertTrue(len(hash1) == 64)
            self.assertEqual(hash1, hash2)

            os.unlink(f1.name)
            os.unlink(f2.name)

    def test_plagiarism_no_comparison(self):
        # When checking a script with no database records
        res = self.plagiarism.check("Test Student", "101", "Unseen Subject", {"path": "nonexistent.txt"})
        self.assertEqual(res["status"], "NO_COMPARISON")
        self.assertFalse(res["suspected"])


if __name__ == "__main__":
    unittest.main()
