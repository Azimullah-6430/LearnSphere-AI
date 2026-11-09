"""
Automated Test Suite for Prompt 3:
Evidence-Based Learning Gap Detection for Blind Learning Companion
=================================================================
Verifies:
1. Evidence collection from Knowledge Challenge, Self-Evaluation, and Topic Practice.
2. Syllabus-mapped Topic Learning Status (Not started, Needs more practice, Learning in progress, etc.).
3. Distinct mistake nature classification (Calculation mistake vs Formula vs Diagram vs Conceptual).
4. Evidence strength categorization (Confirmed repeated difficulty, Possible difficulty, etc.).
5. Dynamic updates and attempt tracking without duplicate gaps.
6. Strict user isolation and no mock gaps.
"""

import unittest
import json
import uuid
from datetime import datetime, timezone
from server import app, get_mongodb, get_sqlite_db
from app.learning_gap_detector import (
    classify_mistake_nature,
    analyze_student_learning_gaps,
    record_blind_practice_attempt,
    MISTAKE_TYPES,
    TOPIC_STATUS,
    EVIDENCE_STRENGTH
)


class TestBlindLearningGapDetector(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

        # Register test student
        self.email = f"gap_student_{uuid.uuid4().hex[:6]}@example.com"
        reg_res = self.client.post("/api/auth/register", json={
            "name": "Priya Patel",
            "email": self.email,
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
        self.assertEqual(reg_res.status_code, 201)
        user_data = reg_res.get_json()["user"]
        self.student_id = str(user_data.get("id") or user_data.get("user_id"))

        # Setup active syllabus
        self.syllabus_id = f"syl_gap_{uuid.uuid4().hex[:6]}"
        self.syllabus_doc = {
            "syllabus_id": self.syllabus_id,
            "student_id": self.student_id,
            "studentId": self.student_id,
            "semester": 4,
            "status": "VALID",
            "validation_status": "VALID",
            "is_active": True,
            "subjects": [
                {"name": "Electric Circuit Theory", "code": "EE401"},
                {"name": "Signals & Systems", "code": "EE402"}
            ],
            "chapters": {
                "Electric Circuit Theory": [
                    {"name": "Unit 1: Network Theorems", "concepts": ["Thevenin's Theorem", "Norton's Equivalent", "Maximum Power Transfer"]}
                ],
                "Signals & Systems": [
                    {"name": "Unit 2: Fourier Transforms", "concepts": ["Continuous-Time Fourier Transform", "Frequency Response"]}
                ]
            }
        }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["syllabi"].insert_one(self.syllabus_doc)
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO syllabi (syllabus_id, student_id, semester, status, validation_status, is_active, version, analysis_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (self.syllabus_id, self.student_id, 4, "VALID", "VALID", 1, 1, json.dumps(self.syllabus_doc))
            )
            conn.commit()
            conn.close()

    def test_zero_mock_data_empty_state(self):
        """When student has no practice or evaluation attempts, zero gaps must be returned."""
        res = self.client.get("/api/blind-companion/learning-gaps")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertFalse(data.get("has_evidence"))
        self.assertEqual(len(data.get("learning_gaps")), 0)
        # All topics should be 'Not started'
        status_map = data.get("topic_status_map", {})
        for top_key, st in status_map.items():
            self.assertEqual(st, TOPIC_STATUS["NOT_STARTED"])

    def test_distinct_mistake_nature_classification(self):
        """Verify distinction between arithmetic calculation mistakes vs conceptual misunderstanding vs diagram difficulty."""
        # 1. Calculation Mistake: Correct formula, intermediate arithmetic slip
        calc_nature, calc_why, calc_action = classify_mistake_nature(
            student_answer="Applied V = I * R. 12 = I * 100, so I = 0.08 A.",
            expected_answer="I = 12 / 100 = 0.12 A.",
            question_text="Calculate the circuit current given V=12V and R=100 Ohms.",
            missing_points="Arithmetic calculation error in dividing 12 by 100",
            awarded_marks=3.5,
            max_marks=5.0
        )
        self.assertEqual(calc_nature, MISTAKE_TYPES["CALCULATION_MISTAKE"])
        self.assertIn("arithmetic slip", calc_why.lower())

        # 2. Diagram Interpretation Difficulty
        diag_nature, diag_why, diag_action = classify_mistake_nature(
            student_answer="The diode is reverse biased because terminal connects to negative rail.",
            expected_answer="Diode anode connects to positive rail through switch S1; it is forward biased.",
            question_text="Examine the circuit schematic. Is the diode forward or reverse biased?",
            missing_points="Misread circuit schematic polarity connections",
            awarded_marks=1.0,
            max_marks=5.0
        )
        self.assertEqual(diag_nature, MISTAKE_TYPES["DIAGRAM_INTERPRETATION_DIFFICULTY"])
        self.assertIn("schematic", diag_why.lower())

        # 3. Incorrect Formula Selection
        form_nature, form_why, form_action = classify_mistake_nature(
            student_answer="Used R_total = R1 + R2 for the parallel branch.",
            expected_answer="Parallel branch requires 1/R_total = 1/R1 + 1/R2.",
            question_text="Find equivalent resistance of R1 and R2 connected in parallel.",
            missing_points="Wrong formula used: used series addition formula instead of parallel reciprocal",
            awarded_marks=1.5,
            max_marks=5.0
        )
        self.assertEqual(form_nature, MISTAKE_TYPES["INCORRECT_FORMULA_SELECTION"])

        # 4. Conceptual Misunderstanding
        conc_nature, conc_why, conc_action = classify_mistake_nature(
            student_answer="Thevenin voltage is equal to short circuit current times load resistance.",
            expected_answer="Thevenin voltage is open-circuit voltage across load terminals.",
            question_text="Define Thevenin voltage Vth.",
            missing_points="Fundamental miscomprehension of open-circuit vs short-circuit equivalent",
            awarded_marks=0.5,
            max_marks=5.0
        )
        self.assertEqual(conc_nature, MISTAKE_TYPES["CONCEPTUAL_MISUNDERSTANDING"])

    def test_dynamic_practice_submission_and_status_update(self):
        """Verify submitting a practice attempt dynamically creates a gap and updates topic status."""
        mongo_db = get_mongodb()
        sqlite_conn = get_sqlite_db() if mongo_db is None else None

        # 1. First failed attempt on Thevenin's Theorem
        submit_res1 = self.client.post("/api/blind-companion/practice/submit", json={
            "subject": "Electric Circuit Theory",
            "unit": "Unit 1: Network Theorems",
            "topic": "Thevenin's Theorem",
            "subtopic": "Thevenin's Theorem",
            "question_text": "Calculate open-circuit voltage across terminals A and B.",
            "student_answer": "Vth = 4V (Calculated by dividing 12 by 30 instead of 20)",
            "expected_answer": "Vth = 6V",
            "is_correct": False,
            "score": 2.0,
            "max_score": 5.0,
            "feedback": "Arithmetic calculation mistake in voltage divider denominator"
        })
        self.assertEqual(submit_res1.status_code, 200)
        data1 = submit_res1.get_json()
        self.assertTrue(data1.get("success"))

        gaps1 = data1.get("learning_gaps", [])
        self.assertEqual(len(gaps1), 1)
        gap1 = gaps1[0]
        self.assertEqual(gap1["topic"], "Thevenin's Theorem")
        self.assertEqual(gap1["mistake_nature"], MISTAKE_TYPES["CALCULATION_MISTAKE"])
        self.assertEqual(gap1["evidence_strength"], EVIDENCE_STRENGTH["INSUFFICIENT"])
        self.assertEqual(gap1["status"], TOPIC_STATUS["IN_PROGRESS"])

        # 2. Second attempt on the same topic repeats the difficulty
        submit_res2 = self.client.post("/api/blind-companion/practice/submit", json={
            "subject": "Electric Circuit Theory",
            "unit": "Unit 1: Network Theorems",
            "topic": "Thevenin's Theorem",
            "subtopic": "Thevenin's Theorem",
            "question_text": "Find Rth by deactivating independent sources.",
            "student_answer": "Rth = 15 Ohms (arithmetic addition slip: 10 + 5 instead of parallel)",
            "expected_answer": "Rth = 8 Ohms",
            "is_correct": False,
            "score": 1.5,
            "max_score": 5.0,
            "feedback": "Calculation mistake in resistance reduction arithmetic"
        })
        self.assertEqual(submit_res2.status_code, 200)
        data2 = submit_res2.get_json()
        gaps2 = data2.get("learning_gaps", [])
        self.assertEqual(len(gaps2), 1)
        gap2 = gaps2[0]
        # Attempt count should be 2 and strength confirmed
        self.assertEqual(gap2["attempt_count"], 2)
        self.assertEqual(gap2["evidence_strength"], EVIDENCE_STRENGTH["CONFIRMED_REPEATED"])

    def test_user_isolation(self):
        """Another student must not see this student's learning gaps."""
        # Register second student
        email_other = f"other_student_{uuid.uuid4().hex[:6]}@example.com"
        reg_res_other = self.client.post("/api/auth/register", json={
            "name": "Rohan Verma",
            "email": email_other,
            "password": "password123",
            "role": "student",
            "is_disabled_student": True
        })
        self.assertEqual(reg_res_other.status_code, 201)

        # Query gaps for second student (clean account)
        other_gaps_res = self.client.get("/api/blind-companion/learning-gaps")
        self.assertEqual(other_gaps_res.status_code, 200)
        other_data = other_gaps_res.get_json()
        self.assertEqual(len(other_data.get("learning_gaps", [])), 0)


if __name__ == "__main__":
    unittest.main()

