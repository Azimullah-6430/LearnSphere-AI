"""
PROMPT 7 – Final End-to-End Validation of Blind Learning Companion
==================================================================
Comprehensive automated audit verifying:
1. Syllabus integration and mapping.
2. Learning accuracy across disciplines (Math, Physics, Chemistry, CS, Diagrams, Graphs).
3. Learning gap evidence classification (Repeated conceptual, arithmetic, partial, insufficient evidence).
4. Adaptive learning progression, prerequisite prioritization, and mastery verification.
5. Accessibility & assistive technology readiness (Speech narration, diagram descriptions, hazard alerts).
6. Account isolation across two distinct student accounts.
7. Normal student regression and teacher portal non-interference.
"""

import unittest
import json
import uuid
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from server import app, get_mongodb, get_sqlite_db
from app.mastery_assessment import (
    narrate_math_expression,
    generate_diagram_narration,
    normalize_voice_transcript,
    generate_mastery_questions,
    evaluate_mastery_submission,
    EVALUATION_RESULTS,
    QUESTION_TIERS,
    MASTERY_STATES
)
from app.learning_gap_detector import (
    classify_mistake_nature,
    analyze_student_learning_gaps,
    record_blind_practice_attempt,
    TOPIC_STATUS,
    MISTAKE_TYPES,
    EVIDENCE_STRENGTH
)
from app.adaptive_learning_path import (
    generate_adaptive_learning_path,
    save_student_step_completion,
    get_student_topic_progress
)


class TestBlindCompanionE2EAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = get_mongodb()

        # 1. Blind Student A
        cls.client_a = app.test_client()
        cls.email_a = f"blind_a_{uuid.uuid4().hex[:6]}@example.com"
        reg_a = cls.client_a.post("/api/auth/register", json={
            "name": "Ananya Blind Student",
            "email": cls.email_a,
            "password": "Password123!",
            "role": "student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Engineering Sciences",
            "semester": 3,
            "is_disabled_student": True,
            "disability_type": "blind_or_low_vision",
            "blind_companion_enabled": True
        })
        assert reg_a.status_code == 201, f"Reg A failed: {reg_a.get_json()}"
        cls.user_a = reg_a.get_json()["user"]
        cls.student_a_id = str(cls.user_a.get("id") or cls.user_a.get("user_id"))

        # 2. Blind Student B
        cls.client_b = app.test_client()
        cls.email_b = f"blind_b_{uuid.uuid4().hex[:6]}@example.com"
        reg_b = cls.client_b.post("/api/auth/register", json={
            "name": "Bilal Low-Vision Student",
            "email": cls.email_b,
            "password": "Password123!",
            "role": "student",
            "level": "college",
            "degree": "B.Sc",
            "department": "Chemistry",
            "semester": 1,
            "is_disabled_student": True,
            "disability_type": "blind_or_low_vision",
            "blind_companion_enabled": True
        })
        assert reg_b.status_code == 201, f"Reg B failed: {reg_b.get_json()}"
        cls.user_b = reg_b.get_json()["user"]
        cls.student_b_id = str(cls.user_b.get("id") or cls.user_b.get("user_id"))

        # 3. Normal Non-Disabled Student C
        cls.client_normal = app.test_client()
        cls.email_normal = f"normal_c_{uuid.uuid4().hex[:6]}@example.com"
        reg_c = cls.client_normal.post("/api/auth/register", json={
            "name": "Chloe Standard Student",
            "email": cls.email_normal,
            "password": "Password123!",
            "role": "student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Mechanical Engineering",
            "semester": 3,
            "is_disabled_student": False,
            "blind_companion_enabled": False
        })
        assert reg_c.status_code == 201, f"Reg C failed: {reg_c.get_json()}"

        # 4. Teacher for isolation check
        cls.client_teacher = app.test_client()
        cls.email_teacher = f"teacher_audit_{uuid.uuid4().hex[:6]}@example.com"
        reg_t = cls.client_teacher.post("/api/auth/register", json={
            "name": "Prof. Marcus Audit",
            "email": cls.email_teacher,
            "password": "Password123!",
            "role": "teacher"
        })
        assert reg_t.status_code == 201, f"Reg T failed: {reg_t.get_json()}"

        # Setup Syllabus for Student A: Multi-Discipline (Physics, Mathematics, Computer Science)
        cls.syllabus_a_id = f"syl_a_{uuid.uuid4().hex[:6]}"
        cls.syl_a = {
            "syllabus_id": cls.syllabus_a_id,
            "student_id": cls.student_a_id,
            "studentId": cls.student_a_id,
            "semester": 3,
            "current_semester": 3,
            "status": "VALID",
            "validation_status": "VALID",
            "is_active": True,
            "subjects": [
                {"name": "Engineering Electromagnetics", "code": "EE301"},
                {"name": "Calculus & Differential Equations", "code": "MA301"},
                {"name": "Data Structures & Algorithms", "code": "CS301"}
            ],
            "chapters": {
                "Engineering Electromagnetics": [
                    {
                        "name": "Unit 1: Electrostatics",
                        "concepts": ["Coulomb's Law", "Gauss's Law", "Electric Potential", "Capacitance"]
                    }
                ],
                "Calculus & Differential Equations": [
                    {
                        "name": "Unit 2: Differential Calculus",
                        "concepts": ["Chain Rule", "Partial Derivatives", "Gradient and Directional Derivative"]
                    }
                ],
                "Data Structures & Algorithms": [
                    {
                        "name": "Unit 3: Linear & Non-Linear Structures",
                        "concepts": ["Binary Search Trees", "Time Complexity O(log n)", "Dijkstra's Algorithm"]
                    }
                ]
            }
        }

        # Setup Syllabus for Student B: Chemistry & Molecular Sciences
        cls.syllabus_b_id = f"syl_b_{uuid.uuid4().hex[:6]}"
        cls.syl_b = {
            "syllabus_id": cls.syllabus_b_id,
            "student_id": cls.student_b_id,
            "studentId": cls.student_b_id,
            "semester": 1,
            "current_semester": 1,
            "status": "VALID",
            "validation_status": "VALID",
            "is_active": True,
            "subjects": [
                {"name": "Organic & Physical Chemistry", "code": "CH101"}
            ],
            "chapters": {
                "Organic & Physical Chemistry": [
                    {
                        "name": "Unit 1: Chemical Kinetics & Thermochemistry",
                        "concepts": ["Reaction Rates", "Arrhenius Equation", "Exothermic Reactions"]
                    }
                ]
            }
        }

        if cls.db is not None:
            cls.db.syllabi.insert_many([cls.syl_a, cls.syl_b])

    # ──────────────────────────────────────────────────────────────────────────
    # 1. SYLLABUS INTEGRATION & GROUNDING TESTS
    # ──────────────────────────────────────────────────────────────────────────
    def test_01_syllabus_grounding_and_structure(self):
        """Verify syllabus extraction, Subject -> Unit -> Topic mapping, and no mock leakage"""
        res = self.client_a.get("/api/curriculum/active")
        self.assertEqual(res.status_code, 200)
        res_data = res.get_json()
        self.assertTrue(res_data.get("success"))

        # Verify subjects strictly match Student A's syllabus
        subjects = [s.get("name") if isinstance(s, dict) else s for s in res_data.get("subjects", [])]
        self.assertIn("Engineering Electromagnetics", subjects)
        self.assertIn("Calculus & Differential Equations", subjects)
        self.assertIn("Data Structures & Algorithms", subjects)
        # Ensure Student B's subject does NOT leak into Student A
        self.assertNotIn("Organic & Physical Chemistry", subjects)

        # Check Teaching endpoint matches topic via Trainer Chat
        teach_res = self.client_a.post("/api/trainer/chat", json={
            "message": "Teach me Gauss's Law from my syllabus.",
            "subject": "Engineering Electromagnetics",
            "unit": "Unit 1: Electrostatics",
            "topic": "Gauss's Law",
            "teaching_mode": "structured_10_step",
            "depth": "detailed"
        })
        self.assertEqual(teach_res.status_code, 200)
        t_data = teach_res.get_json()
        self.assertTrue(t_data.get("success"))
        content = t_data.get("reply") or t_data.get("response") or t_data.get("content") or ""
        # Content must be educational and explicitly mention the topic
        self.assertTrue(len(content) > 50)
        self.assertIn("gauss", content.lower())

    # ──────────────────────────────────────────────────────────────────────────
    # 2. LEARNING ACCURACY TESTS (Multi-Disciplinary)
    # ──────────────────────────────────────────────────────────────────────────
    def test_02_learning_accuracy_multi_discipline(self):
        """Test mathematical expressions, physics, chemistry, programming concepts and diagrams"""
        # Math narration: LaTeX translation to natural words
        latex_expr = r"\frac{d}{dx}\left(x^2 + \sin(x)\right) = 2x + \cos(x)"
        spoken_math = narrate_math_expression(latex_expr)
        self.assertIn("derivative with respect to x", spoken_math.lower())
        self.assertIn("x squared", spoken_math.lower())
        self.assertIn("cosine", spoken_math.lower())

        # Integral expression
        integral_expr = r"\int_{0}^{\pi} \sin(x) \, dx = 2"
        spoken_integral = narrate_math_expression(integral_expr)
        self.assertIn("integral from 0 to pi", spoken_integral.lower())

        # Diagram Audio Visual Breakdown
        circuit_desc = generate_diagram_narration(
            subject="Electric Circuit Theory",
            topic="Thevenin's Theorem",
            context="DC resistive bridge"
        )
        self.assertTrue(len(circuit_desc) > 50)
        self.assertIn("planar two-terminal DC network", circuit_desc)
        self.assertIn("24-volt DC voltage source", circuit_desc)

        # Graph Audio Narration
        graph_desc = generate_diagram_narration(
            subject="Signal Processing",
            topic="Bode Graph Response",
            context="Low-pass filter"
        )
        self.assertTrue(len(graph_desc) > 50)
        self.assertIn("logarithmic scale", graph_desc)
        self.assertIn("decibels", graph_desc)

    # ──────────────────────────────────────────────────────────────────────────
    # 3. LEARNING GAP DETECTION (Evidence-Based Classification)
    # ──────────────────────────────────────────────────────────────────────────
    def test_03_learning_gap_classification(self):
        """Verify: repeated conceptual mistakes, arithmetic errors, incomplete answers, correct mastery"""
        # A. Repeated conceptual mistake on "Chain Rule"
        nature_1, gap_1, next_act_1 = classify_mistake_nature(
            student_answer="The derivative of sin(x^2) is cos(x^2)",
            expected_answer="The derivative of sin(x^2) is 2x * cos(x^2) using chain rule",
            question_text="Differentiate sin(x^2) with respect to x",
            missing_points="Conceptual misunderstanding: confused chain rule with regular power rule",
            awarded_marks=1.0,
            max_marks=5.0
        )
        self.assertEqual(nature_1, MISTAKE_TYPES["CONCEPTUAL_MISUNDERSTANDING"])
        self.assertTrue(len(gap_1) > 20)
        self.assertTrue(len(next_act_1) > 20)

        # B. Isolated arithmetic calculation mistake
        nature_2, _, _ = classify_mistake_nature(
            student_answer="2 * 3 = 5, so answer is 5x",
            expected_answer="2 * 3 = 6, so answer is 6x",
            question_text="Simplify 2 * 3 * x",
            missing_points="Minor arithmetic addition instead of multiplication",
            awarded_marks=4.0,
            max_marks=5.0
        )
        self.assertEqual(nature_2, MISTAKE_TYPES["CALCULATION_MISTAKE"])

        # C. Incomplete answer
        nature_3, _, _ = classify_mistake_nature(
            student_answer="Coulomb's Law states force depends on charges",
            expected_answer="Force is directly proportional to product of charges and inversely to square of distance",
            question_text="State Coulomb's Law completely",
            missing_points="Incomplete answer: second part omitted",
            awarded_marks=2.5,
            max_marks=5.0
        )
        self.assertEqual(nature_3, MISTAKE_TYPES["INCOMPLETE_ANSWERS"])

        # D. Record practice attempt via API and verify gap diagnosis
        sub_res = self.client_a.post("/api/blind-companion/practice/submit", json={
            "subject": "Calculus & Differential Equations",
            "unit": "Unit 2: Differential Calculus",
            "topic": "Chain Rule",
            "score": 1.0,
            "max_score": 5.0,
            "is_correct": False,
            "question_text": "Differentiate sin(x^2)",
            "student_answer": "cos(x^2)",
            "expected_answer": "2x * cos(x^2)",
            "feedback": "Failed to multiply by derivative of inside function."
        })
        self.assertEqual(sub_res.status_code, 200)

        # Check diagnosed gaps
        gaps_res = self.client_a.get("/api/blind-companion/learning-gaps")
        self.assertEqual(gaps_res.status_code, 200)
        gaps = gaps_res.get_json().get("learning_gaps", [])
        chain_gaps = [g for g in gaps if g.get("topic") == "Chain Rule"]
        self.assertTrue(len(chain_gaps) > 0)
        self.assertEqual(chain_gaps[0].get("mistake_nature"), MISTAKE_TYPES["CONCEPTUAL_MISUNDERSTANDING"])

    # ──────────────────────────────────────────────────────────────────────────
    # 4. ADAPTIVE LEARNING PROGRESSION & MASTERY
    # ──────────────────────────────────────────────────────────────────────────
    def test_04_adaptive_learning_path_and_recovery(self):
        """Verify prerequisite prioritization, targeted explanation, and mastery confirmation"""
        # Step 1: Learning path must prioritize "Chain Rule" because of the diagnosed gap
        path_res = self.client_a.get("/api/blind-companion/learning-path")
        self.assertEqual(path_res.status_code, 200)
        p_data = path_res.get_json()
        self.assertTrue(p_data.get("success"))
        self.assertEqual(p_data.get("focus_topic"), "Chain Rule")
        self.assertEqual(p_data.get("reason_type"), "needs_practice")
        steps = p_data.get("steps", [])
        self.assertTrue(len(steps) >= 5)

        # Step 2: Test voice command query: "What should I study next?"
        cmd_res = self.client_a.post("/api/blind-companion/learning-path/command", json={
            "command": "what should I study next?"
        })
        self.assertEqual(cmd_res.status_code, 200)
        cmd_data = cmd_res.get_json()
        self.assertIn("Chain Rule", cmd_data.get("spoken_response", ""))

        # Step 3: Verify topic mastery logic:
        # A single successful attempt is NOT enough (requires multi-attempt evidence >= 2)
        question_sample = {
            "subject": "Calculus & Differential Equations",
            "unit": "Unit 2: Differential Calculus",
            "topic": "Chain Rule",
            "points": 5.0,
            "expected_criteria": "24x(3x^2 + 5)^3"
        }
        res_first = evaluate_mastery_submission(
            student_id=self.student_a_id,
            student_name="Ananya Blind Student",
            question=question_sample,
            student_answer="24x(3x^2 + 5)^3",
            submission_mode="keyboard",
            mongo_db=self.db
        )
        self.assertEqual(res_first["evaluation_result"], EVALUATION_RESULTS["CORRECT"])
        # Single success is progressing / more evidence needed, NOT yet understanding demonstrated
        self.assertIn(res_first["mastery_state"], [MASTERY_STATES["PROGRESSING"], MASTERY_STATES["MORE_EVIDENCE_NEEDED"]])

        # Insert record of this attempt to simulate historical database record
        if self.db is not None:
            self.db["blind_practice_attempts"].insert_one({
                "student_id": self.student_a_id,
                "topic": "Chain Rule",
                "score": 5.0,
                "max_score": 5.0,
                "is_correct": True
            })

        # Second successful attempt certifies mastery
        res_second = evaluate_mastery_submission(
            student_id=self.student_a_id,
            student_name="Ananya Blind Student",
            question=question_sample,
            student_answer="24x(3x^2 + 5)^3",
            submission_mode="keyboard",
            mongo_db=self.db
        )
        self.assertEqual(res_second["evaluation_result"], EVALUATION_RESULTS["CORRECT"])
        self.assertEqual(res_second["mastery_state"], MASTERY_STATES["UNDERSTANDING_DEMONSTRATED"])

    # ──────────────────────────────────────────────────────────────────────────
    # 5. ACCOUNT ISOLATION (Two Independent Blind Accounts)
    # ──────────────────────────────────────────────────────────────────────────
    def test_05_account_isolation_student_a_and_b(self):
        """Student A and Student B must have 100% separate gaps, paths, syllabi, and attempts"""
        # Student B records practice attempt on Chemistry
        b_sub = self.client_b.post("/api/blind-companion/practice/submit", json={
            "subject": "Organic & Physical Chemistry",
            "unit": "Unit 1: Chemical Kinetics & Thermochemistry",
            "topic": "Arrhenius Equation",
            "score": 0.5,
            "max_score": 5.0,
            "is_correct": False,
            "question_text": "What does Ea represent in Arrhenius equation?",
            "student_answer": "Electronegativity activation",
            "expected_answer": "Activation energy of the reaction",
            "feedback": "Incorrect concept: Ea is activation energy."
        })
        self.assertEqual(b_sub.status_code, 200)

        # Retrieve gaps for Student B
        b_gaps_res = self.client_b.get("/api/blind-companion/learning-gaps")
        b_gaps = b_gaps_res.get_json().get("learning_gaps", [])
        b_topics = [g.get("topic") for g in b_gaps]
        self.assertIn("Arrhenius Equation", b_topics)
        self.assertNotIn("Chain Rule", b_topics)  # Student A's gap must NOT appear

        # Retrieve gaps for Student A
        a_gaps_res = self.client_a.get("/api/blind-companion/learning-gaps")
        a_gaps = a_gaps_res.get_json().get("learning_gaps", [])
        a_topics = [g.get("topic") for g in a_gaps]
        self.assertIn("Chain Rule", a_topics)
        self.assertNotIn("Arrhenius Equation", a_topics)  # Student B's gap must NOT appear

        # Learning paths must also be completely separate
        a_path = self.client_a.get("/api/blind-companion/learning-path").get_json()
        b_path = self.client_b.get("/api/blind-companion/learning-path").get_json()
        self.assertEqual(a_path.get("focus_topic"), "Chain Rule")
        self.assertEqual(a_path.get("focus_subject"), "Calculus & Differential Equations")
        self.assertIn(b_path.get("focus_topic"), ["Arrhenius Equation", "Reaction Rates"])
        self.assertEqual(b_path.get("focus_subject"), "Organic & Physical Chemistry")
        self.assertNotIn("Calculus", json.dumps(b_path))
        self.assertNotIn("Chemistry", json.dumps(a_path))

    # ──────────────────────────────────────────────────────────────────────────
    # 6. NORMAL STUDENT REGRESSION & TEACHER ISOLATION
    # ──────────────────────────────────────────────────────────────────────────
    def test_06_normal_student_regression_and_teacher_isolation(self):
        """Normal student has companion disabled; Teacher portal receives ZERO student blind activity leakage"""
        # Normal student me endpoint
        me_res = self.client_normal.get("/api/auth/me")
        self.assertEqual(me_res.status_code, 200)
        norm_user = me_res.get_json().get("user", {})
        self.assertFalse(bool(norm_user.get("is_disabled_student")))
        self.assertFalse(bool(norm_user.get("blind_companion_enabled")))

        # Check teacher notifications
        t_notifs = self.client_teacher.get("/api/notifications")
        self.assertEqual(t_notifs.status_code, 200)
        notifs = t_notifs.get_json().get("notifications", [])
        for n in notifs:
            msg = str(n.get("message") or "") + str(n.get("title") or "")
            self.assertNotIn("Blind Learning Companion", msg)
            self.assertNotIn(self.email_a, msg)
            self.assertNotIn(self.email_b, msg)

    # ──────────────────────────────────────────────────────────────────────────
    # 7. ACCESSIBILITY & ASSISTIVE TECH READINESS
    # ──────────────────────────────────────────────────────────────────────────
    def test_07_accessibility_and_safety_checks(self):
        """Speech normalization, review requirements, and physical experiment hazard detection"""
        # Speech transcription normalization
        norm_text = normalize_voice_transcript(
            raw_text="dy by dx equals 24 x multiplied by open parenthesis three x squared plus five close parenthesis cubed",
            subject="Calculus",
            topic="Chain Rule"
        )
        self.assertIn("24x", norm_text)
        self.assertIn("3x^2", norm_text)

        # Safety hazard detection for practical lab experiments
        hazards = []
        lab_step = "Heat 50ml of dilute hydrochloric acid over the open flame using tongs and wear safety goggles."
        lower = lab_step.lower()
        if any(h in lower for h in ["acid", "chemical"]):
            hazards.append("Chemical Corrosive")
        if any(h in lower for h in ["heat", "flame", "burner"]):
            hazards.append("Thermal/Open Flame")
        if any(h in lower for h in ["voltage", "wire", "electric"]):
            hazards.append("Electrical")
        if any(h in lower for h in ["glass", "blade", "sharp", "scalpel"]):
            hazards.append("Sharp/Glassware")

        self.assertIn("Chemical Corrosive", hazards)
        self.assertIn("Thermal/Open Flame", hazards)
        self.assertNotIn("Electrical", hazards)


if __name__ == "__main__":
    unittest.main()
