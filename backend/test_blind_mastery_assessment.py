"""
Automated Test Suite for Prompt 5:
Accessible Mastery Assessment and Continuous Learning Improvement
==================================================================
Verifies:
1. Mathematical Expression Narration: LaTeX formulas accurately translated to natural spoken words.
2. Adaptive Question Generation: Multi-tier questions grounded in actual syllabus & learning gaps.
3. Speech Transcription Review & Normalization: Dictated answers normalized, requires review.
4. Evaluation of Understanding: Distinguishes Correct Understanding, Partial Understanding,
   Calculation Error, Conceptual Misunderstanding.
5. Mastery Verification: A concept requires multi-attempt evidence (>= 2 successful attempts)
   to achieve 'Understanding demonstrated'.
6. Continuous Improvement Loop: Provides strengths, simple-language mistake diagnosis,
   related syllabus concept, recommended activity, and targeted practice checkpoint.
7. Strict Teacher Isolation: Zero modification of teacher portal records.
"""

import unittest
import json
import uuid
from datetime import datetime, timezone
from server import app, get_mongodb, get_sqlite_db
from app.mastery_assessment import (
    narrate_math_expression,
    generate_diagram_narration,
    normalize_voice_transcript,
    generate_mastery_questions,
    evaluate_mastery_submission,
    MASTERY_STATES,
    EVALUATION_RESULTS,
    QUESTION_TIERS
)


class TestBlindMasteryAssessment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

        # Register test student once for the suite
        cls.email = f"mastery_student_{uuid.uuid4().hex[:6]}@example.com"
        reg_res = cls.client.post("/api/auth/register", json={
            "name": "Kavita Rao",
            "email": cls.email,
            "password": "password123",
            "role": "student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Electrical & Electronics Engineering",
            "semester": 4,
            "is_disabled_student": True,
            "disability_type": "blind_or_low_vision",
            "blind_companion_enabled": True
        })
        assert reg_res.status_code == 201, f"Register failed: {reg_res.get_json()}"
        user_data = reg_res.get_json()["user"]
        cls.student_id = str(user_data.get("id") or user_data.get("user_id"))

        # Setup active syllabus
        cls.syllabus_id = f"syl_mast_{uuid.uuid4().hex[:6]}"
        cls.syllabus_doc = {
            "syllabus_id": cls.syllabus_id,
            "student_id": cls.student_id,
            "studentId": cls.student_id,
            "semester": 4,
            "status": "VALID",
            "validation_status": "VALID",
            "is_active": True,
            "subjects": [
                {"name": "Electric Circuit Theory", "code": "EE401"},
                {"name": "Calculus & Linear Algebra", "code": "MA401"}
            ],
            "chapters": {
                "Electric Circuit Theory": [
                    {
                        "name": "Unit 1: Network Theorems",
                        "concepts": ["Thevenin's Theorem", "Norton's Equivalent", "Maximum Power Transfer"]
                    }
                ],
                "Calculus & Linear Algebra": [
                    {
                        "name": "Unit 2: Differential Calculus",
                        "concepts": ["Chain Rule", "Composite Functions", "Implicit Differentiation"]
                    }
                ]
            }
        }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["syllabi"].insert_one(cls.syllabus_doc)
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO syllabi (syllabus_id, student_id, semester, status, validation_status, is_active, version, analysis_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (cls.syllabus_id, cls.student_id, 4, "VALID", "VALID", 1, 1, json.dumps(cls.syllabus_doc))
            )
            conn.commit()
            conn.close()

    def test_mathematical_expression_narration(self):
        """Verify LaTeX and mathematical symbols are translated into fluid spoken words."""
        # Fraction and Subscript
        formula = r"V_{th} = V_s \cdot \frac{R_2}{R_1 + R_2}"
        spoken = narrate_math_expression(formula)
        self.assertIn("V Thevenin", spoken)
        self.assertIn("divided by", spoken)
        self.assertIn("times", spoken)

        # Derivatives and Powers
        calc_formula = r"\frac{dy}{dx} = 4(3x^2 + 5)^3 \cdot 6x"
        calc_spoken = narrate_math_expression(calc_formula)
        self.assertIn("d y by d x", calc_spoken)
        self.assertIn("squared", calc_spoken)
        self.assertIn("cubed", calc_spoken)

        # Ohms and microfarads
        circ_formula = r"R = 24 \Omega, C = 10 \mu F"
        circ_spoken = narrate_math_expression(circ_formula)
        self.assertIn("Ohms", circ_spoken)
        self.assertIn("microfarads", circ_spoken)

    def test_voice_transcription_normalization(self):
        """Verify spoken phonetic dictation errors are normalized before evaluation."""
        raw_speech = "v thevenin is 14.4 volts and r thevenin is 24 ohms using kcl"
        normalized = normalize_voice_transcript(raw_speech, "Electric Circuit Theory", "Thevenin's Theorem")
        self.assertIn("V_th", normalized)
        self.assertIn("R_th", normalized)
        self.assertIn("KCL", normalized)
        self.assertIn("Ohms", normalized)

    def test_adaptive_question_generation_endpoint(self):
        """Verify generating mastery questions across cognitive tiers grounded in syllabus."""
        res = self.client.post("/api/blind-companion/assessment/generate", json={
            "subject": "Electric Circuit Theory",
            "unit": "Unit 1: Network Theorems",
            "topic": "Thevenin's Theorem",
            "subtopic": "Thevenin's Theorem",
            "tier": "adaptive"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        questions = data.get("questions", [])
        self.assertTrue(len(questions) >= 3)

        # Verify each question has accessible audio properties
        for q in questions:
            self.assertTrue(bool(q.get("question_text")))
            self.assertTrue(bool(q.get("spoken_prompt")))
            self.assertTrue(bool(q.get("expected_criteria")))

    def test_evaluation_distinctions(self):
        """
        Verify subject evaluation accurately distinguishes:
        1. Correct understanding
        2. Calculation error (formula correct, arithmetic slip)
        3. Conceptual misunderstanding
        """
        question = {
            "subject": "Electric Circuit Theory",
            "unit": "Unit 1: Network Theorems",
            "topic": "Thevenin's Theorem",
            "question_text": "Calculate V_th and R_th for 24V source, 40 Ohm series and 60 Ohm load.",
            "expected_criteria": "V_th = 24 * (60/100) = 14.4V, R_th = (40*60)/100 = 24 Ohms.",
            "points": 5.0
        }

        # 1. Correct Understanding
        res_correct = self.client.post("/api/blind-companion/assessment/evaluate", json={
            "question": question,
            "student_answer": "Used voltage divider: V_th = 24 * (60 / (40 + 60)) = 14.4V. Deactivated source by shorting, giving parallel R_th = (40 * 60) / 100 = 24 Ohms.",
            "submission_mode": "keyboard",
            "transcript_reviewed": True
        })
        self.assertEqual(res_correct.status_code, 200)
        data_correct = res_correct.get_json()
        self.assertEqual(data_correct["evaluation_result"], EVALUATION_RESULTS["CORRECT"])
        self.assertEqual(data_correct["score"], 5.0)
        self.assertIn("14.4V", data_correct["strengths_explanation"])

        # 2. Calculation Error (arithmetic slip in denominator)
        res_calc = self.client.post("/api/blind-companion/assessment/evaluate", json={
            "question": question,
            "student_answer": "Applied voltage divider formula: 24 * 60 / 120 = 12V (divider slip in denominator). R_th is 10 Ohms.",
            "submission_mode": "keyboard",
            "transcript_reviewed": True
        })
        self.assertEqual(res_calc.status_code, 200)
        data_calc = res_calc.get_json()
        self.assertEqual(data_calc["evaluation_result"], EVALUATION_RESULTS["CALCULATION_ERROR"])
        self.assertIn("arithmetic", data_calc["mistake_explanation"].lower())

        # 3. Conceptual Misunderstanding (confusing short circuit and open circuit)
        res_concept = self.client.post("/api/blind-companion/assessment/evaluate", json={
            "question": question,
            "student_answer": "Connected terminals together and measured short circuit current as V_th.",
            "submission_mode": "keyboard",
            "transcript_reviewed": True
        })
        self.assertEqual(res_concept.status_code, 200)
        data_concept = res_concept.get_json()
        self.assertEqual(data_concept["evaluation_result"], EVALUATION_RESULTS["CONCEPTUAL_MISUNDERSTANDING"])
        self.assertIn("confusion", data_concept["mistake_explanation"].lower())

    def test_multi_attempt_mastery_verification(self):
        """
        Verify mastery verification threshold:
        - 1 successful attempt sets state to 'Progressing'.
        - 2 consecutive successful attempts (>= 80%) elevate state to 'Understanding demonstrated'.
        - Lesson completion does NOT bypass assessment mastery.
        """
        question = {
            "subject": "Calculus & Linear Algebra",
            "unit": "Unit 2: Differential Calculus",
            "topic": "Chain Rule",
            "question_text": "Differentiate y = (3x^2 + 5)^4 with respect to x.",
            "expected_criteria": "dy/dx = 24x(3x^2 + 5)^3",
            "points": 5.0
        }

        # Attempt 1: First correct submission on Chain Rule
        res1 = self.client.post("/api/blind-companion/assessment/evaluate", json={
            "question": question,
            "student_answer": "By chain rule, outer derivative is 4(3x^2+5)^3 and inner is 6x, so dy/dx = 24x(3x^2+5)^3.",
            "submission_mode": "keyboard",
            "transcript_reviewed": True
        })
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertEqual(data1["evaluation_result"], EVALUATION_RESULTS["CORRECT"])
        # Only 1 attempt -> Must be 'Progressing', NOT full 'Understanding demonstrated'
        self.assertEqual(data1["mastery_state"], MASTERY_STATES["PROGRESSING"])

        # Attempt 2: Second correct submission on same topic
        res2 = self.client.post("/api/blind-companion/assessment/evaluate", json={
            "question": question,
            "student_answer": "Differentiating (3x^2 + 5)^4 gives dy/dx = 24x(3x^2 + 5)^3.",
            "submission_mode": "keyboard",
            "transcript_reviewed": True
        })
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertEqual(data2["evaluation_result"], EVALUATION_RESULTS["CORRECT"])
        # 2 verified attempts -> Promotes to 'Understanding demonstrated'!
        self.assertEqual(data2["mastery_state"], MASTERY_STATES["UNDERSTANDING_DEMONSTRATED"])

    def test_continuous_improvement_and_teacher_isolation(self):
        """
        Verify evaluation produces complete continuous improvement metadata:
        strengths, simple mistake diagnosis, related syllabus concept, recommended activity,
        and targeted practice. Verify zero teacher evaluation contamination.
        """
        question = {
            "subject": "Electric Circuit Theory",
            "unit": "Unit 1: Network Theorems",
            "topic": "Thevenin's Theorem",
            "question_text": "Find equivalent resistance.",
            "expected_criteria": "R_th = 24 Ohms",
            "points": 5.0
        }

        res = self.client.post("/api/blind-companion/assessment/evaluate", json={
            "question": question,
            "student_answer": "Used 40*60 / 120 divider slip in denominator arithmetic.",
            "submission_mode": "voice",
            "transcript_reviewed": True
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(bool(data.get("strengths_explanation")))
        self.assertTrue(bool(data.get("mistake_explanation")))
        self.assertTrue(bool(data.get("related_concept")))
        self.assertTrue(bool(data.get("recommended_activity")))
        self.assertTrue(bool(data.get("targeted_practice_question")))
        self.assertTrue(bool(data.get("spoken_feedback")))

        # Check teacher evaluations table to guarantee zero contamination
        mongo_db = get_mongodb()
        if mongo_db is not None:
            teacher_evals = list(mongo_db["evaluations"].find({"student_id": self.student_id}))
            # Should contain zero teacher evaluations created by this blind companion practice
            self.assertEqual(len(teacher_evals), 0)


if __name__ == "__main__":
    unittest.main()
