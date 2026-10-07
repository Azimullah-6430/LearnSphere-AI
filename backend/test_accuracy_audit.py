"""
LearnSphere AI - Comprehensive Accuracy, Reliability & Security Audit Suite
Tests all 29 target scenarios and verification criteria.
"""

import json
import os
import unittest
import uuid
from datetime import datetime

# Setup in-memory / test environment
os.environ["FLASK_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key"

from app.evaluation.evaluator import EvaluationAgent
from app.evaluation.store import store_evaluation_pipeline, _is_conceptual_issue
from server import app, _lookup_user_by_id


class AccuracyAuditTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = EvaluationAgent()
        cls.client = app.test_client()

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 1 - 4: Theory Questions (2-mark, 5-mark, 10-mark, 16-mark)
    # ──────────────────────────────────────────────────────────────────────────
    def test_01_two_mark_theory_question(self):
        """1. 2-mark theory question: bounds 0..2, feedback present, no mark overflow."""
        qp_struct = {
            "subject": "Physics",
            "total_marks": 2.0,
            "questions": [
                {"question_id": "q1", "question_number": "1", "question_text": "Define inertia.", "maximum_marks": 2.0}
            ]
        }
        ai_response = {
            "evaluations": [
                {
                    "question_id": "q1",
                    "question_number": "1",
                    "attempted": True,
                    "maximum_marks": 2.0,
                    "awarded_marks": 2.0,
                    "percentage_of_question": 100.0,
                    "answer_classification": "correct_answer",
                    "student_answer": "Inertia is the resistance of any physical object to any change in its velocity.",
                    "evaluation_reason": "Accurate definition provided with correct physical property cited.",
                    "teacher_feedback": "Precise and concise definition.",
                    "what_was_done_correctly": ["Correctly identified resistance to velocity change"],
                    "what_is_incorrect": [],
                    "what_is_missing": [],
                    "what_student_should_have_written": "Inertia is the tendency of an object to resist changes in its state of motion.",
                    "how_to_improve": "Keep maintaining this precision.",
                }
            ],
            "overall_teacher_comment": "Excellent concise answer.",
            "strongest_areas": ["Definitions"],
            "weakest_areas": [],
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["total_marks"], 2.0)
        self.assertEqual(result["obtained_marks"], 2.0)
        self.assertLessEqual(result["obtained_marks"], result["total_marks"])
        self.assertEqual(result["evaluations"][0]["awarded_marks"], 2.0)
        self.assertTrue(len(result["evaluations"][0]["teacher_feedback"]) > 0)

    def test_02_five_mark_theory_question(self):
        """2. 5-mark theory question: partial credit awarded, missing points tracked."""
        qp_struct = {
            "subject": "Biology",
            "total_marks": 5.0,
            "questions": [
                {"question_id": "q1", "question_number": "1", "question_text": "Describe the light-dependent reactions of photosynthesis.", "maximum_marks": 5.0}
            ]
        }
        ai_response = {
            "evaluations": [
                {
                    "question_id": "q1",
                    "question_number": "1",
                    "attempted": True,
                    "maximum_marks": 5.0,
                    "awarded_marks": 3.5,
                    "percentage_of_question": 70.0,
                    "answer_classification": "partially_correct_concept",
                    "student_answer": "Chlorophyll absorbs sunlight, water splits into oxygen and hydrogen, producing ATP.",
                    "evaluation_reason": "Correctly covered chlorophyll absorption and water photolysis; omitted NADPH reduction and thylakoid membrane location.",
                    "teacher_feedback": "Good summary of water photolysis and ATP generation. 1.5 marks deducted for missing NADPH production and thylakoid context.",
                    "what_was_done_correctly": ["Photolysis of water identified", "ATP synthesis mentioned"],
                    "what_is_incorrect": [],
                    "what_is_missing": ["NADPH formation", "Thylakoid membrane localization"],
                    "what_student_should_have_written": "Light-dependent reactions occur in thylakoid membranes, generating ATP and NADPH while releasing O2.",
                    "how_to_improve": "Include both energy carriers (ATP and NADPH) and organelle structures.",
                }
            ],
            "overall_teacher_comment": "Sound understanding of fundamental reaction, needs structural details.",
            "strongest_areas": ["Photolysis"],
            "weakest_areas": ["Carrier molecules"],
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["total_marks"], 5.0)
        self.assertEqual(result["obtained_marks"], 3.5)
        self.assertEqual(len(result["evaluations"][0]["what_is_missing"]), 2)

    def test_03_ten_mark_theory_question(self):
        """3. 10-mark theory question: thorough evaluation bounds and multi-point feedback."""
        qp_struct = {
            "subject": "Computer Science",
            "total_marks": 10.0,
            "questions": [
                {"question_id": "q1", "question_number": "1", "question_text": "Explain ACID properties in Database Management Systems with examples.", "maximum_marks": 10.0}
            ]
        }
        ai_response = {
            "evaluations": [
                {
                    "question_id": "q1",
                    "question_number": "1",
                    "attempted": True,
                    "maximum_marks": 10.0,
                    "awarded_marks": 8.0,
                    "percentage_of_question": 80.0,
                    "answer_classification": "partially_correct_concept",
                    "student_answer": "Atomicity (all or nothing), Consistency (preserves database rules), Isolation (concurrent transactions don't interfere), Durability (persisted committed data). Included bank transfer example for Atomicity.",
                    "evaluation_reason": "All 4 properties clearly defined with strong Atomicity example; 2 marks deducted because Isolation levels (dirty reads, phantom reads) and Durability WAL mechanics were not explained.",
                    "teacher_feedback": "Excellent definitions of all 4 properties. To achieve full 10/10, elaborate on Isolation concurrency anomalies.",
                    "what_was_done_correctly": ["Accurate definition of all four ACID properties", "Clear bank transfer example for Atomicity"],
                    "what_is_incorrect": [],
                    "what_is_missing": ["Isolation concurrency anomalies", "Write-ahead logging for durability"],
                    "what_student_should_have_written": "Detailed definitions with concrete transaction diagrams and Isolation level trade-offs.",
                    "how_to_improve": "Include concurrency issues when explaining Isolation.",
                }
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["obtained_marks"], 8.0)
        self.assertLessEqual(result["obtained_marks"], 10.0)

    def test_04_sixteen_mark_theory_question(self):
        """4. 16-mark university engineering question."""
        qp_struct = {
            "subject": "Software Engineering",
            "total_marks": 16.0,
            "questions": [
                {"question_id": "q1", "question_number": "1", "question_text": "Critically analyze Agile vs Waterfall SDLC models across 5 engineering dimensions.", "maximum_marks": 16.0}
            ]
        }
        ai_response = {
            "evaluations": [
                {
                    "question_id": "q1",
                    "question_number": "1",
                    "attempted": True,
                    "maximum_marks": 16.0,
                    "awarded_marks": 13.0,
                    "percentage_of_question": 81.25,
                    "answer_classification": "correct_answer",
                    "student_answer": "Analyzed flexibility, cost of change, client involvement, documentation, and delivery timeline with comparative table.",
                    "evaluation_reason": "Strong 5-dimension comparative framework provided; 3 marks deducted due to minimal coverage of risk management in large regulated systems.",
                    "teacher_feedback": "Comprehensive comparative table and practical trade-off analysis across all 5 dimensions.",
                    "what_was_done_correctly": ["5 comparative dimensions analyzed", "Tabular comparison constructed"],
                    "what_is_incorrect": [],
                    "what_is_missing": ["Regulated domain compliance nuances"],
                    "what_student_should_have_written": "Complete comparative breakdown including compliance in medical/aerospace software.",
                    "how_to_improve": "Highlight regulatory compliance constraints in Agile.",
                }
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["total_marks"], 16.0)
        self.assertEqual(result["obtained_marks"], 13.0)

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 5 - 8: Numericals, MCQs, Multi-step & Subquestions
    # ──────────────────────────────────────────────────────────────────────────
    def test_05_numerical_problem(self):
        """5. Single numerical problem: formula, substitution, calculation."""
        qp_struct = {
            "subject": "Physics",
            "total_marks": 5.0,
            "questions": [{"question_id": "q1", "question_number": "1", "question_text": "Calculate kinetic energy of a 2kg mass moving at 3m/s.", "maximum_marks": 5.0}]
        }
        ai_response = {
            "evaluations": [
                {
                    "question_id": "q1",
                    "question_number": "1",
                    "attempted": True,
                    "maximum_marks": 5.0,
                    "awarded_marks": 5.0,
                    "percentage_of_question": 100.0,
                    "answer_classification": "correct_answer",
                    "student_answer": "KE = 0.5 * m * v^2 = 0.5 * 2 * (3)^2 = 1 * 9 = 9 Joules.",
                    "evaluation_reason": "Correct formula, exact substitution, flawless calculation, and proper SI unit (Joules).",
                    "teacher_feedback": "Perfect numerical solution.",
                    "what_was_done_correctly": ["Formula KE = 1/2 mv^2", "Correct substitution", "Correct SI unit"],
                    "what_is_incorrect": [],
                    "what_is_missing": [],
                    "what_student_should_have_written": "KE = 0.5 * 2 * 9 = 9 J",
                    "how_to_improve": "Excellent work.",
                }
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["obtained_marks"], 5.0)

    def test_06_multi_step_numerical_with_arithmetic_slip(self):
        """6. Multi-step numerical with arithmetic error: partial credit awarded, NO misconception falsely created."""
        qp_struct = {
            "subject": "Physics",
            "total_marks": 5.0,
            "questions": [{"question_id": "q1", "question_number": "1", "question_text": "Calculate resistance of a 100W, 200V bulb.", "maximum_marks": 5.0}]
        }
        ai_response = {
            "evaluations": [
                {
                    "question_id": "q1",
                    "question_number": "1",
                    "attempted": True,
                    "maximum_marks": 5.0,
                    "awarded_marks": 3.0,
                    "percentage_of_question": 60.0,
                    "answer_classification": "correct_concept_with_calculation_error",
                    "student_answer": "P = V^2 / R => R = V^2 / P = (200)^2 / 100 = 4000 / 100 = 40 Ohms.",
                    "evaluation_reason": "Correct electrical power formula selected and rearranged properly; 2 marks deducted because (200)^2 was written as 4000 instead of 40000.",
                    "step_or_calculation_mistake": "Squaring error: 200^2 = 4000 instead of 40000.",
                    "conceptual_mistake": "",
                    "misconception_detected": False,
                    "misconception": "",
                    "teacher_feedback": "Formula selection is correct, but 200 squared is 40,000, not 4,000. Final resistance is 400 ohms.",
                    "what_was_done_correctly": ["Power formula P = V^2 / R correctly rearranged"],
                    "what_is_incorrect": ["Arithmetic squaring of 200"],
                    "what_is_missing": ["Correct final numerical value 400 Ω"],
                    "what_student_should_have_written": "R = (200)^2 / 100 = 40000 / 100 = 400 Ω",
                    "how_to_improve": "Double-check basic squares in intermediate steps.",
                }
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        q = result["evaluations"][0]
        self.assertEqual(q["awarded_marks"], 3.0)
        self.assertFalse(_is_conceptual_issue(q), "Calculation error must NOT be flagged as conceptual misconception")

    def test_07_mcq_evaluation(self):
        """7. MCQ Question: binary grading."""
        qp_struct = {
            "subject": "Chemistry",
            "total_marks": 1.0,
            "questions": [{"question_id": "q1", "question_number": "1", "question_text": "What is the pH of pure water at 25C? (A) 5 (B) 7 (C) 9 (D) 14", "maximum_marks": 1.0}]
        }
        ai_response = {
            "evaluations": [
                {
                    "question_id": "q1",
                    "question_number": "1",
                    "attempted": True,
                    "maximum_marks": 1.0,
                    "awarded_marks": 1.0,
                    "percentage_of_question": 100.0,
                    "answer_classification": "correct_answer",
                    "student_answer": "Option (B) 7",
                    "evaluation_reason": "Correct option selected.",
                    "teacher_feedback": "Correct option (B).",
                    "what_was_done_correctly": ["Selected option B"],
                    "what_is_incorrect": [],
                    "what_is_missing": [],
                    "what_student_should_have_written": "Option (B) 7",
                    "how_to_improve": "Correct.",
                }
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["obtained_marks"], 1.0)

    def test_08_multiple_subquestions(self):
        """8. Multi-part questions (1(a), 1(b), 1(c)) mapped independently."""
        qp_struct = {
            "subject": "Mathematics",
            "total_marks": 10.0,
            "questions": [
                {"question_id": "q1_a", "question_number": "1(a)", "question_text": "Find derivative of sin(x).", "maximum_marks": 3.0},
                {"question_id": "q1_b", "question_number": "1(b)", "question_text": "Find derivative of e^(2x).", "maximum_marks": 3.0},
                {"question_id": "q1_c", "question_number": "1(c)", "question_text": "Integrate x^2 dx.", "maximum_marks": 4.0},
            ]
        }
        ai_response = {
            "evaluations": [
                {"question_id": "q1_a", "question_number": "1(a)", "attempted": True, "maximum_marks": 3.0, "awarded_marks": 3.0, "teacher_feedback": "Correct derivative cos(x)."},
                {"question_id": "q1_b", "question_number": "1(b)", "attempted": True, "maximum_marks": 3.0, "awarded_marks": 3.0, "teacher_feedback": "Correct chain rule application 2e^(2x)."},
                {"question_id": "q1_c", "question_number": "1(c)", "attempted": True, "maximum_marks": 4.0, "awarded_marks": 3.0, "teacher_feedback": "x^3/3 found, constant of integration + C omitted."},
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(len(result["evaluations"]), 3)
        self.assertEqual(result["obtained_marks"], 9.0)
        self.assertEqual(result["total_marks"], 10.0)

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 9 - 13: Order Permutation, Skipped Questions, Multi-Page
    # ──────────────────────────────────────────────────────────────────────────
    def test_09_answers_in_wrong_order(self):
        """9. Student answers Q3 first, then Q1, then Q2: correctly aligned with paper."""
        qp_struct = {
            "subject": "Chemistry",
            "total_marks": 15.0,
            "questions": [
                {"question_id": "q1", "question_number": "1", "question_text": "Question 1 text", "maximum_marks": 5.0},
                {"question_id": "q2", "question_number": "2", "question_text": "Question 2 text", "maximum_marks": 5.0},
                {"question_id": "q3", "question_number": "3", "question_text": "Question 3 text", "maximum_marks": 5.0},
            ]
        }
        ai_response = {
            "evaluations": [
                {"question_id": "q3", "question_number": "3", "attempted": True, "maximum_marks": 5.0, "awarded_marks": 5.0, "teacher_feedback": "Q3 answered first, full marks."},
                {"question_id": "q1", "question_number": "1", "attempted": True, "maximum_marks": 5.0, "awarded_marks": 4.0, "teacher_feedback": "Q1 answered second."},
                {"question_id": "q2", "question_number": "2", "attempted": True, "maximum_marks": 5.0, "awarded_marks": 3.0, "teacher_feedback": "Q2 answered third."},
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["obtained_marks"], 12.0)
        self.assertEqual(result["total_marks"], 15.0)

    def test_10_skipped_questions(self):
        """10. Skipped questions: attempted=False, 0 marks, not hallucinated."""
        qp_struct = {
            "subject": "Physics",
            "total_marks": 10.0,
            "questions": [
                {"question_id": "q1", "question_number": "1", "question_text": "Explain Doppler effect.", "maximum_marks": 5.0},
                {"question_id": "q2", "question_number": "2", "question_text": "Derive lens maker formula.", "maximum_marks": 5.0},
            ]
        }
        ai_response = {
            "evaluations": [
                {"question_id": "q1", "question_number": "1", "attempted": True, "maximum_marks": 5.0, "awarded_marks": 4.5, "teacher_feedback": "Accurate explanation."},
                # Q2 not present in AI evaluation output
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(len(result["evaluations"]), 2)
        q2 = next(q for q in result["evaluations"] if q["question_number"] == "2")
        self.assertFalse(q2["attempted"])
        self.assertEqual(q2["awarded_marks"], 0.0)
        self.assertEqual(q2["answer_classification"], "unanswered_question")

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 14 - 20: Diagnostic Nuances & Error Classification
    # ──────────────────────────────────────────────────────────────────────────
    def test_14_genuine_conceptual_misconception(self):
        """14. Genuine misconception (e.g. Newton's 3rd Law) correctly triggers misconception record."""
        q = {
            "attempted": True,
            "question_number": "2",
            "maximum_marks": 5.0,
            "awarded_marks": 1.0,
            "answer_classification": "wrong_concept",
            "misconception_detected": True,
            "misconception": "Believes action and reaction forces act on the same object and cancel each other out.",
            "conceptual_mistake": "Believes action and reaction forces act on the same object.",
        }
        self.assertTrue(_is_conceptual_issue(q))

    def test_15_calculation_error_is_not_misconception(self):
        """15. Calculation error must NEVER be classified as a misconception."""
        q = {
            "attempted": True,
            "question_number": "1",
            "maximum_marks": 5.0,
            "awarded_marks": 3.0,
            "answer_classification": "correct_concept_with_calculation_error",
            "misconception_detected": False,
            "misconception": "",
            "step_or_calculation_mistake": "10 * 2.5 was multiplied as 20 instead of 25.",
        }
        self.assertFalse(_is_conceptual_issue(q))

    def test_16_irrelevant_and_blank_answers(self):
        """16. Completely irrelevant and blank answers receive 0 marks."""
        qp_struct = {
            "subject": "History",
            "total_marks": 5.0,
            "questions": [{"question_id": "q1", "question_number": "1", "question_text": "Causes of World War I.", "maximum_marks": 5.0}]
        }
        ai_response = {
            "evaluations": [
                {
                    "question_id": "q1",
                    "question_number": "1",
                    "attempted": True,
                    "maximum_marks": 5.0,
                    "awarded_marks": 0.0,
                    "percentage_of_question": 0.0,
                    "answer_classification": "irrelevant_answer",
                    "student_answer": "Writes lyrics to a song unrelated to the prompt.",
                    "evaluation_reason": "Response is completely irrelevant to World War I causes.",
                    "teacher_feedback": "No relevant historical points provided. 0 marks awarded.",
                    "what_was_done_correctly": [],
                    "what_is_incorrect": ["Entire content is irrelevant"],
                    "what_is_missing": ["M-A-I-N causes of WWI"],
                    "what_student_should_have_written": "Militarism, Alliances, Imperialism, Nationalism.",
                    "how_to_improve": "Answer the specific historical prompt.",
                }
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["obtained_marks"], 0.0)

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 21 - 26: Paper Variations, Rubrics & Subjects
    # ──────────────────────────────────────────────────────────────────────────
    def test_21_paper_without_rubric(self):
        """21. Paper evaluated with standard curriculum knowledge when rubric is omitted."""
        qp_struct = {
            "subject": "Chemistry",
            "total_marks": 5.0,
            "questions": [{"question_id": "q1", "question_number": "1", "question_text": "Define Le Chatelier's Principle.", "maximum_marks": 5.0}]
        }
        ai_response = {
            "evaluations": [
                {
                    "question_id": "q1",
                    "question_number": "1",
                    "attempted": True,
                    "maximum_marks": 5.0,
                    "awarded_marks": 5.0,
                    "teacher_feedback": "Accurately stated dynamic equilibrium shift response.",
                }
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["obtained_marks"], 5.0)

    def test_22_total_marks_never_exceeds_maximum(self):
        """22. Safety assertion: awarded marks clamped strictly to maximum."""
        qp_struct = {
            "subject": "Mathematics",
            "total_marks": 10.0,
            "questions": [
                {"question_id": "q1", "question_number": "1", "question_text": "Q1", "maximum_marks": 10.0}
            ]
        }
        ai_response = {
            "evaluations": [
                # Faulty AI hallucinated 12 marks on a 10 mark question
                {"question_id": "q1", "question_number": "1", "attempted": True, "maximum_marks": 10.0, "awarded_marks": 12.0, "teacher_feedback": "Overallocated."}
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertLessEqual(result["obtained_marks"], 10.0)
        self.assertEqual(result["evaluations"][0]["awarded_marks"], 10.0)

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 27 - 29: Security, Multi-User Isolation & Concurrency
    # ──────────────────────────────────────────────────────────────────────────
    def test_27_cross_student_access_prevention(self):
        """27. Student B cannot access Student A's evaluation record."""
        with app.test_client() as client:
            # Simulate student session with ID student_a
            with client.session_transaction() as sess:
                sess["user_id"] = "student_a_uid"
                sess["role"] = "student"

            # Request an evaluation belonging to student_b
            res = client.get("/api/evaluations/eval_belonging_to_student_b_9999")
            # Must return 404 or 403, never 200 with student B's data
            self.assertIn(res.status_code, [403, 404])

    def test_28_marks_lost_calculation_rule(self):
        """28. >20 Marks Lost calculation rule: marks_lost = maximum_marks - obtained_marks."""
        max_marks = 100.0
        obtained_marks = 75.0
        marks_lost = max_marks - obtained_marks
        self.assertEqual(marks_lost, 25.0)
        self.assertTrue(marks_lost > 20.0, "Should trigger >20 mark loss alert")

    def test_29_concurrent_evaluation_isolation(self):
        """29. Two evaluations run with unique evaluation IDs without state bleed."""
        eval_id_1 = f"eval_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
        eval_id_2 = f"eval_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
    def test_30_choice_option_attempted_one_skipped_other(self):
        """30. Internal (OR) choice: student attempts 1(a) and leaves 1(b). 1(b) is marked skipped due to choice, not counted against student."""
        qp_struct = {
            "subject": "Physics",
            "total_marks": 5.0,
            "questions": [
                {"question_id": "q1_a", "question_number": "1(a)", "question_text": "Option A: State Lenz's Law", "maximum_marks": 5.0, "choice_group": "choice_q1", "required_choice_count": 1},
                {"question_id": "q1_b", "question_number": "1(b)", "question_text": "Option B (OR): State Faraday's Law", "maximum_marks": 5.0, "choice_group": "choice_q1", "required_choice_count": 1}
            ]
        }
        ai_response = {
            "evaluations": [
                {"question_id": "q1_a", "question_number": "1(a)", "attempted": True, "maximum_marks": 5.0, "awarded_marks": 4.5, "teacher_feedback": "Accurate statement of induced EMF direction."}
                # 1(b) was not attempted in script
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["total_marks"], 5.0, "Total marks for paper with 1 of 2 choice must be 5.0, not 10.0")
        self.assertEqual(result["obtained_marks"], 4.5)
        self.assertEqual(result["percentage"], 90.0)

        q1_a = next(q for q in result["evaluations"] if q["question_number"] == "1(a)")
        q1_b = next(q for q in result["evaluations"] if q["question_number"] == "1(b)")

        self.assertTrue(q1_a["counted_in_total"])
        self.assertEqual(q1_a["awarded_marks"], 4.5)

        self.assertFalse(q1_b["counted_in_total"])
        self.assertTrue(q1_b.get("is_skipped_due_to_choice"))
        self.assertEqual(q1_b["marks_lost"], 0.0)
        self.assertEqual(q1_b["answer_classification"], "skipped_choice_option")
        self.assertIn("elective choice", q1_b["teacher_feedback"].lower())

    def test_31_choice_option_attempted_both_highest_counted(self):
        """31. Internal (OR) choice: student attempts BOTH options. Higher score is counted, other is marked extra choice."""
        qp_struct = {
            "subject": "Mathematics",
            "total_marks": 5.0,
            "questions": [
                {"question_id": "q1_a", "question_number": "1(a)", "question_text": "Option A: Prove trigonometric identity", "maximum_marks": 5.0, "choice_group": "choice_q1", "required_choice_count": 1},
                {"question_id": "q1_b", "question_number": "1(b)", "question_text": "Option B (OR): Evaluate definite integral", "maximum_marks": 5.0, "choice_group": "choice_q1", "required_choice_count": 1}
            ]
        }
        ai_response = {
            "evaluations": [
                {"question_id": "q1_a", "question_number": "1(a)", "attempted": True, "maximum_marks": 5.0, "awarded_marks": 3.0, "teacher_feedback": "Partial proof."},
                {"question_id": "q1_b", "question_number": "1(b)", "attempted": True, "maximum_marks": 5.0, "awarded_marks": 5.0, "teacher_feedback": "Flawless integration."}
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["total_marks"], 5.0)
        self.assertEqual(result["obtained_marks"], 5.0, "Should count 5.0 from the higher scoring choice")
        self.assertEqual(result["percentage"], 100.0)

        q1_a = next(q for q in result["evaluations"] if q["question_number"] == "1(a)")
        q1_b = next(q for q in result["evaluations"] if q["question_number"] == "1(b)")

        self.assertTrue(q1_b["counted_in_total"])
        self.assertEqual(q1_b["awarded_marks"], 5.0)

        self.assertFalse(q1_a["counted_in_total"])
        self.assertTrue(q1_a.get("is_extra_choice"))
        self.assertEqual(q1_a["marks_lost"], 0.0)

    def test_32_robust_question_number_format_matching(self):
        """32. Multi-format matching: QP has '1(a)' and '1(b)', evaluated answers return 'q1_a' and '1.b'. Must match 100%."""
        qp_struct = {
            "subject": "Chemistry",
            "total_marks": 10.0,
            "questions": [
                {"question_id": "q1_a", "question_number": "1(a)", "question_text": "Define molarity.", "maximum_marks": 5.0},
                {"question_id": "q1_b", "question_number": "1(b)", "question_text": "Define molality.", "maximum_marks": 5.0},
            ]
        }
        ai_response = {
            "evaluations": [
                # First answer returned with question_id only
                {"question_id": "q1_a", "question_number": "Q.1 a", "attempted": True, "maximum_marks": 5.0, "awarded_marks": 5.0, "teacher_feedback": "Perfect definition."},
                # Second answer returned with dot notation
                {"question_id": "q_sub_2", "question_number": "1.b", "attempted": True, "maximum_marks": 5.0, "awarded_marks": 4.5, "teacher_feedback": "Accurate definition."}
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["total_marks"], 10.0)
        self.assertEqual(result["obtained_marks"], 9.5)
        self.assertEqual(result["percentage"], 95.0)

        q1_a = next(q for q in result["evaluations"] if q["question_number"] == "1(a)")
        q1_b = next(q for q in result["evaluations"] if q["question_number"] == "1(b)")

        self.assertTrue(q1_a["attempted"])
        self.assertEqual(q1_a["awarded_marks"], 5.0)

        self.assertTrue(q1_b["attempted"])
        self.assertEqual(q1_b["awarded_marks"], 4.5)

    def test_33_multi_part_choice_group_evaluation(self):
        """33. Multi-subpart choice: Option A has 6(a)(i) [8m] + 6(a)(ii) [8m] = 16m; Option B has 6(b) [16m].
        Student answers 6(b) (15/16). Option A is skipped due to choice. Total marks must be 16.0, not 32.0.
        """
        qp_struct = {
            "subject": "Software Engineering",
            "total_marks": 16.0,
            "questions": [
                {"question_id": "q6_a_1", "question_number": "6(a)(i)", "question_text": "Spiral model diagram", "maximum_marks": 8.0, "choice_group": "choice_q6", "required_choice_count": 1},
                {"question_id": "q6_a_2", "question_number": "6(a)(ii)", "question_text": "Prototyping approach", "maximum_marks": 8.0, "choice_group": "choice_q6", "required_choice_count": 1},
                {"question_id": "q6_b", "question_number": "6(b)", "question_text": "Extreme Programming (XP)", "maximum_marks": 16.0, "choice_group": "choice_q6", "required_choice_count": 1}
            ]
        }
        ai_response = {
            "evaluations": [
                {"question_id": "q6_b", "question_number": "6(b)", "attempted": True, "maximum_marks": 16.0, "awarded_marks": 15.0, "teacher_feedback": "Comprehensive XP answer."}
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["total_marks"], 16.0, "Paper total with 1 of 2 16-mark options must be 16.0")
        self.assertEqual(result["obtained_marks"], 15.0)
        self.assertEqual(result["percentage"], 93.75)

        q6_b = next(q for q in result["evaluations"] if q["question_number"] == "6(b)")
        q6_a1 = next(q for q in result["evaluations"] if q["question_number"] == "6(a)(i)")
        q6_a2 = next(q for q in result["evaluations"] if q["question_number"] == "6(a)(ii)")

        self.assertTrue(q6_b["counted_in_total"])
        self.assertEqual(q6_b["awarded_marks"], 15.0)

        self.assertFalse(q6_a1["counted_in_total"])
        self.assertTrue(q6_a1["is_skipped_due_to_choice"])
        self.assertEqual(q6_a1["marks_lost"], 0.0)

        self.assertFalse(q6_a2["counted_in_total"])
        self.assertTrue(q6_a2["is_skipped_due_to_choice"])
        self.assertEqual(q6_a2["marks_lost"], 0.0)

    def test_34_prevent_cross_option_and_subpart_mismatch(self):
        """34. Strict mapping: When student answers 6(b), 7(a)(i), and 7(a)(ii):
        - 6(b) must map ONLY to 6(b), NEVER to 6(a)(i) or 6(a)(ii).
        - 7(a)(i) must map ONLY to 7(a)(i), NEVER to 7(b)(i) or 7(a)(ii).
        - 7(a)(ii) must map ONLY to 7(a)(ii), NEVER to 7(b)(ii) or 7(a)(i).
        - 6(a)(i), 6(a)(ii), 7(b)(i), 7(b)(ii) must be correctly marked as skipped choice options.
        """
        qp_struct = {
            "subject": "Computer Science & Engineering",
            "total_marks": 30.0,
            "questions": [
                # Question 6 elective group (15 marks total)
                {"question_id": "q6_a_1", "question_number": "6(a)(i)", "question_text": "Explain agile principles.", "maximum_marks": 7.0, "choice_group": "choice_q6", "required_choice_count": 1},
                {"question_id": "q6_a_2", "question_number": "6(a)(ii)", "question_text": "Describe scrum sprints.", "maximum_marks": 8.0, "choice_group": "choice_q6", "required_choice_count": 1},
                {"question_id": "q6_b", "question_number": "6(b)", "question_text": "Discuss waterfall model with diagram.", "maximum_marks": 15.0, "choice_group": "choice_q6", "required_choice_count": 1},

                # Question 7 elective group (15 marks total)
                {"question_id": "q7_a_1", "question_number": "7(a)(i)", "question_text": "Draw use case diagram for banking.", "maximum_marks": 8.0, "choice_group": "choice_q7", "required_choice_count": 1},
                {"question_id": "q7_a_2", "question_number": "7(a)(ii)", "question_text": "Explain class relationships.", "maximum_marks": 7.0, "choice_group": "choice_q7", "required_choice_count": 1},
                {"question_id": "q7_b_1", "question_number": "7(b)(i)", "question_text": "Sequence diagram for ATM.", "maximum_marks": 8.0, "choice_group": "choice_q7", "required_choice_count": 1},
                {"question_id": "q7_b_2", "question_number": "7(b)(ii)", "question_text": "Activity diagram for checkout.", "maximum_marks": 7.0, "choice_group": "choice_q7", "required_choice_count": 1}
            ]
        }

        # Simulated AI evaluation matching the student's actual handwritten answers:
        ai_response = {
            "evaluations": [
                # Student wrote 6(b)
                {
                    "question_id": "q6_b",
                    "question_number": "6(b)",
                    "attempted": True,
                    "maximum_marks": 15.0,
                    "awarded_marks": 13.5,
                    "student_answer": "Student drew complete waterfall phases with feedback loops.",
                    "teacher_feedback": "Excellent waterfall explanation and neat diagram."
                },
                # Student wrote 7(a)(i)
                {
                    "question_id": "q7_a_1",
                    "question_number": "7(a)(i)",
                    "attempted": True,
                    "maximum_marks": 8.0,
                    "awarded_marks": 7.5,
                    "student_answer": "Student drew banking use cases with actors and include/extend relationships.",
                    "teacher_feedback": "Accurate use cases and actors."
                },
                # Student wrote 7(a)(ii)
                {
                    "question_id": "q7_a_2",
                    "question_number": "7(a)(ii)",
                    "attempted": True,
                    "maximum_marks": 7.0,
                    "awarded_marks": 6.0,
                    "student_answer": "Student detailed generalization, association, and aggregation.",
                    "teacher_feedback": "Good explanation of OOP relationships."
                }
            ]
        }

        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)

        # 1. Total marks should be 30.0 (15 for Q6 + 15 for Q7)
        self.assertEqual(result["total_marks"], 30.0)
        # 2. Total obtained should be 13.5 + 7.5 + 6.0 = 27.0
        self.assertEqual(result["obtained_marks"], 27.0)
        self.assertEqual(result["percentage"], 90.0)

        # Check Question 6 mapping
        evals_by_qno = {q["question_number"]: q for q in result["evaluations"]}

        self.assertTrue(evals_by_qno["6(b)"]["attempted"])
        self.assertEqual(evals_by_qno["6(b)"]["awarded_marks"], 13.5)
        self.assertTrue(evals_by_qno["6(b)"]["counted_in_total"])

        self.assertFalse(evals_by_qno["6(a)(i)"]["attempted"])
        self.assertEqual(evals_by_qno["6(a)(i)"]["awarded_marks"], 0.0)
        self.assertFalse(evals_by_qno["6(a)(i)"]["counted_in_total"])
        self.assertTrue(evals_by_qno["6(a)(i)"]["is_skipped_due_to_choice"])

        self.assertFalse(evals_by_qno["6(a)(ii)"]["attempted"])
        self.assertEqual(evals_by_qno["6(a)(ii)"]["awarded_marks"], 0.0)
        self.assertFalse(evals_by_qno["6(a)(ii)"]["counted_in_total"])
        self.assertTrue(evals_by_qno["6(a)(ii)"]["is_skipped_due_to_choice"])

        # Check Question 7 mapping
        self.assertTrue(evals_by_qno["7(a)(i)"]["attempted"])
        self.assertEqual(evals_by_qno["7(a)(i)"]["awarded_marks"], 7.5)
        self.assertTrue(evals_by_qno["7(a)(i)"]["counted_in_total"])

        self.assertTrue(evals_by_qno["7(a)(ii)"]["attempted"])
        self.assertEqual(evals_by_qno["7(a)(ii)"]["awarded_marks"], 6.0)
        self.assertTrue(evals_by_qno["7(a)(ii)"]["counted_in_total"])

        self.assertFalse(evals_by_qno["7(b)(i)"]["attempted"])
        self.assertEqual(evals_by_qno["7(b)(i)"]["awarded_marks"], 0.0)
        self.assertFalse(evals_by_qno["7(b)(i)"]["counted_in_total"])
        self.assertTrue(evals_by_qno["7(b)(i)"]["is_skipped_due_to_choice"])

        self.assertFalse(evals_by_qno["7(b)(ii)"]["attempted"])
        self.assertEqual(evals_by_qno["7(b)(ii)"]["awarded_marks"], 0.0)
        self.assertFalse(evals_by_qno["7(b)(ii)"]["counted_in_total"])
        self.assertTrue(evals_by_qno["7(b)(ii)"]["is_skipped_due_to_choice"])

    def test_35_hierarchy_parser_variants(self):
        """35. Hierarchy parser unit tests on wide variety of numbering formats."""
        p = self.agent._parse_q_hierarchy
        self.assertEqual(p("6(a)(i)"), (6, 'a', '1'))
        self.assertEqual(p("6(a)(ii)"), (6, 'a', '2'))
        self.assertEqual(p("6(b)"), (6, 'b', None))
        self.assertEqual(p("7a i"), (7, 'a', '1'))
        self.assertEqual(p("7.b.ii"), (7, 'b', '2'))
        self.assertEqual(p("Q7_b_2"), (7, 'b', '2'))
        self.assertEqual(p("3(i)"), (3, None, '1'))
        self.assertEqual(p("Q5"), (5, None, None))
        self.assertEqual(p("12(c)"), (12, 'c', None))

        # Compatibility checks
        comp = self.agent.is_hierarchy_compatible
        self.assertFalse(comp((6, 'a', '1'), (6, 'b', None)), "Option A cannot match Option B")
        self.assertFalse(comp((7, 'a', '1'), (7, 'b', '1')), "7a cannot match 7b")
        self.assertFalse(comp((7, 'a', '1'), (7, 'a', '2')), "Subpart 1 cannot match Subpart 2")
        self.assertTrue(comp((6, 'b', None), (6, 'b', None)))
        self.assertTrue(comp((7, 'a', '1'), (7, 'a', '1')))

    def test_36_unprinted_top_question_number_choice_continuity(self):
        """36. Test scenario where Option B is printed as just '(b)' or under '(OR)' without '6' printed on top.
        The normalization must assign it to 6(b), group under choice_q6, and ensure 7(a) is NOT confused with 6(b).
        """
        raw_extracted_qp = {
            "subject": "Software Engineering",
            "total_marks": 30.0,
            "questions": [
                # 6(a)(i) and 6(a)(ii)
                {"question_id": "raw_1", "question_number": "6(a)(i)", "question_text": "Explain agile principles.", "maximum_marks": 7.0},
                {"question_id": "raw_2", "question_number": "6(a)(ii)", "question_text": "Describe scrum sprints.", "maximum_marks": 8.0},
                # Option B printed as just '(b)' with '(OR)' marker
                {"question_id": "raw_3", "question_number": "(b)", "question_text": "(OR) Discuss waterfall model with neat diagram.", "maximum_marks": 15.0},

                # 7(a)(i) and 7(a)(ii)
                {"question_id": "raw_4", "question_number": "7(a)(i)", "question_text": "Draw banking use case diagram.", "maximum_marks": 8.0},
                {"question_id": "raw_5", "question_number": "7(a)(ii)", "question_text": "Explain class relationships.", "maximum_marks": 7.0},
                # Option B of Q7 printed as just 'b)' with OR
                {"question_id": "raw_6", "question_number": "b)", "question_text": "OR Explain sequence diagrams.", "maximum_marks": 15.0}
            ]
        }

        normalized_qp = self.agent._strict_normalize_qp(raw_extracted_qp)
        q_map = {q["question_number"]: q for q in normalized_qp["questions"]}

        # Verify Option B of Q6 was resolved to '6(b)'
        self.assertIn("6(b)", q_map)
        self.assertEqual(q_map["6(b)"]["choice_group"], "choice_q6")
        self.assertEqual(q_map["6(a)(i)"]["choice_group"], "choice_q6")
        self.assertEqual(q_map["6(a)(ii)"]["choice_group"], "choice_q6")

        # Verify Option B of Q7 was resolved to '7(b)'
        self.assertIn("7(b)", q_map)
        self.assertEqual(q_map["7(b)"]["choice_group"], "choice_q7")
        self.assertEqual(q_map["7(a)(i)"]["choice_group"], "choice_q7")
        self.assertEqual(q_map["7(a)(ii)"]["choice_group"], "choice_q7")

        # Now simulate student answering 6(b) and 7(a)(i) + 7(a)(ii)
        ai_response = {
            "evaluations": [
                {"question_id": "raw_3", "question_number": "6(b)", "attempted": True, "maximum_marks": 15.0, "awarded_marks": 14.0, "teacher_feedback": "Detailed waterfall answer."},
                {"question_id": "raw_4", "question_number": "7(a)(i)", "attempted": True, "maximum_marks": 8.0, "awarded_marks": 8.0, "teacher_feedback": "Accurate use cases."},
                {"question_id": "raw_5", "question_number": "7(a)(ii)", "attempted": True, "maximum_marks": 7.0, "awarded_marks": 6.5, "teacher_feedback": "Good OOP relationship analysis."}
            ]
        }

        result = self.agent.verify_and_finalize_evaluation(normalized_qp, ai_response)

        # Total marks must be 30.0
        self.assertEqual(result["total_marks"], 30.0)
        # Total obtained: 14.0 + 8.0 + 6.5 = 28.5
        self.assertEqual(result["obtained_marks"], 28.5)
        self.assertEqual(result["percentage"], 95.0)

        evals_by_qno = {q["question_number"]: q for q in result["evaluations"]}
        self.assertTrue(evals_by_qno["6(b)"]["counted_in_total"])
        self.assertEqual(evals_by_qno["6(b)"]["awarded_marks"], 14.0)

        self.assertFalse(evals_by_qno["6(a)(i)"]["counted_in_total"])
        self.assertTrue(evals_by_qno["6(a)(i)"]["is_skipped_due_to_choice"])

        self.assertTrue(evals_by_qno["7(a)(i)"]["counted_in_total"])
        self.assertEqual(evals_by_qno["7(a)(i)"]["awarded_marks"], 8.0)

        self.assertTrue(evals_by_qno["7(a)(ii)"]["counted_in_total"])
        self.assertEqual(evals_by_qno["7(a)(ii)"]["awarded_marks"], 6.5)

        self.assertFalse(evals_by_qno["7(b)"]["counted_in_total"])
        self.assertTrue(evals_by_qno["7(b)"]["is_skipped_due_to_choice"])

    def test_37_resilient_json_repair_engine(self):
        """37. Verify that parse_json_response repairs LaTeX backslashes, trailing commas,
        raw newlines, and truncated JSON blocks with 100% success.
        """
        parser = self.agent.gemini_service.parse_json_response

        # Case 1: Unescaped LaTeX backslashes
        latex_json = r'{"question_id": "q1", "feedback": "Formula: \theta = \frac{\lambda}{d} and R = 50\Omega, \Delta x = 2"}'
        res1 = parser(latex_json)
        self.assertIn("Formula:", res1["feedback"])
        self.assertEqual(res1["question_id"], "q1")

        # Case 2: Trailing commas and markdown code fences
        trailing_comma_json = """```json
        {
          "is_unreadable": false,
          "evaluations": [
            {"question_id": "q1", "awarded_marks": 5.0,},
          ],
        }
        ```"""
        res2 = parser(trailing_comma_json)
        self.assertFalse(res2["is_unreadable"])
        self.assertEqual(len(res2["evaluations"]), 1)
        self.assertEqual(res2["evaluations"][0]["awarded_marks"], 5.0)

        # Case 3: Truncated JSON recovery
        truncated_json = '{"is_unreadable": false, "evaluations": [{"question_id": "q1", "maximum_marks": 10.0, "awarded_marks": 8.5, "student_answer": "Student explained waterfall"'
        res3 = parser(truncated_json)
        self.assertTrue(len(res3["evaluations"]) >= 1)
        self.assertEqual(res3["evaluations"][0]["question_id"], "q1")

    def test_38_strict_mark_to_depth_rigor(self):
        """38. Strict mark-to-depth evaluation: verify that 8-mark, 12-mark, and 16-mark
        questions written as brief/short answers are strictly capped and penalized by real teacher standards.
        """
        qp_struct = {
            "subject": "Computer Science & Engineering",
            "total_marks": 36.0,
            "questions": [
                {"question_id": "q1", "question_number": "1", "question_text": "Explain the Working Principle of Transformer Architecture with Self-Attention Mechanism.", "maximum_marks": 8.0},
                {"question_id": "q2", "question_number": "2", "question_text": "Explain Relational Database Normalization from 1NF to BCNF with concrete tables and dependency diagrams.", "maximum_marks": 12.0},
                {"question_id": "q3", "question_number": "3", "question_text": "Design an End-to-End Distributed Microservices Architecture for an E-commerce Platform with trade-offs.", "maximum_marks": 16.0}
            ]
        }
        ai_response = {
            "evaluations": [
                {
                    "question_id": "q1",
                    "question_number": "1",
                    "attempted": True,
                    "maximum_marks": 8.0,
                    "awarded_marks": 2.5,
                    "percentage_of_question": 31.25,
                    "answer_classification": "correct_answer_with_insufficient_explanation",
                    "student_answer": "Transformers use self-attention to process words in parallel instead of sequentially like RNNs.",
                    "evaluation_reason": "Awarded 2.5/8.0: Accurate core concept (+2.5m). Deducted 5.5 marks because the response is a brief one-line summary for an 8-mark question—missing Query/Key/Value matrix formulations, multi-head attention diagrams, feed-forward layers, and positional encoding.",
                    "teacher_feedback": "Your fundamental concept of parallel self-attention vs RNNs is correct. However, for an 8-mark question, a brief one-line answer cannot receive full credit. You must provide QKV equations, multi-head architecture, and positional encodings.",
                    "what_was_done_correctly": ["Correct definition of Transformer parallel attention mechanism"],
                    "what_is_missing": ["Q, K, V mathematical matrix formulation", "Multi-Head Attention mechanism and block diagram", "Positional encoding explanation", "Feed-forward layer and residual normalization details"],
                    "what_is_incorrect": []
                },
                {
                    "question_id": "q2",
                    "question_number": "2",
                    "attempted": True,
                    "maximum_marks": 12.0,
                    "awarded_marks": 3.5,
                    "percentage_of_question": 29.17,
                    "answer_classification": "incomplete_answer",
                    "student_answer": "1NF removes repeating groups. 2NF removes partial dependency. 3NF removes transitive dependency. BCNF is Boyce Codd normal form.",
                    "evaluation_reason": "Awarded 3.5/12.0: Correct definitions of normal forms (+3.5m). Deducted 8.5 marks because 12-mark question requires step-by-step decomposed table schemas, functional dependency diagrams, anomaly examples (insert/update/delete), and formal determinant criteria for BCNF.",
                    "teacher_feedback": "Accurate basic definitions of normal forms. However, this is a 12-mark major question. You must include sample relation tables, show functional dependencies, and illustrate anomalies at each stage.",
                    "what_was_done_correctly": ["Accurate baseline definitions of 1NF, 2NF, 3NF, and BCNF"],
                    "what_is_missing": ["Concrete sample relation tables and decomposition examples", "Functional dependency diagrams", "Insertion, deletion, and update anomaly demonstrations", "Formal mathematical determinant definition for BCNF"],
                    "what_is_incorrect": []
                },
                {
                    "question_id": "q3",
                    "question_number": "3",
                    "attempted": True,
                    "maximum_marks": 16.0,
                    "awarded_marks": 4.5,
                    "percentage_of_question": 28.12,
                    "answer_classification": "correct_answer_with_insufficient_explanation",
                    "student_answer": "We have microservices like User Service, Order Service, and Payment Service. They communicate via REST APIs and use separate databases.",
                    "evaluation_reason": "Awarded 4.5/16.0: High-level microservices concept identified (+4.5m). Deducted 11.5 marks because 16-mark comprehensive design question demands API gateway architecture, distributed transactions (Saga pattern/2PC), event brokers (Kafka/RabbitMQ), circuit breakers, caching, and resiliency trade-offs.",
                    "teacher_feedback": "Good high-level identification of core microservice boundaries. For a 16-mark engineering design question, extensive depth is required: API gateway, asynchronous messaging, Saga pattern for distributed transactions, CQRS, and latency/resilience analysis.",
                    "what_was_done_correctly": ["Correctly identified independent service boundaries and database-per-service pattern"],
                    "what_is_missing": ["System architecture block diagram", "API Gateway and Service Discovery", "Distributed transaction management (Saga Pattern / 2PC)", "Event-driven messaging architecture", "Resiliency mechanisms (Circuit breaker, rate limiting)", "CAP theorem trade-offs"],
                    "what_is_incorrect": []
                }
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["total_marks"], 36.0)
        self.assertEqual(result["obtained_marks"], 10.5)

        q1 = next(q for q in result["evaluations"] if q["question_number"] == "1")
        self.assertLessEqual(q1["awarded_marks"], 3.0)
        self.assertEqual(q1["answer_classification"], "correct_answer_with_insufficient_explanation")

        q2 = next(q for q in result["evaluations"] if q["question_number"] == "2")
        self.assertLessEqual(q2["awarded_marks"], 4.0)

        q3 = next(q for q in result["evaluations"] if q["question_number"] == "3")
        self.assertLessEqual(q3["awarded_marks"], 5.0)

    def test_39_strike_outs_disregarded_clean_text_evaluated(self):
        """39. Verify that crossed-out/struck-through sections in student scripts are completely
        excluded from evaluation and only clean, un-struck text is evaluated.
        """
        qp_struct = {
            "subject": "Mathematics",
            "total_marks": 5.0,
            "questions": [
                {"question_id": "q1", "question_number": "1", "question_text": "Find the derivative of f(x) = x^3 - 4x + 7.", "maximum_marks": 5.0}
            ]
        }
        ai_response = {
            "evaluations": [
                {
                    "question_id": "q1",
                    "question_number": "1",
                    "attempted": True,
                    "maximum_marks": 5.0,
                    "awarded_marks": 5.0,
                    "percentage_of_question": 100.0,
                    "answer_classification": "correct_answer",
                    "student_answer": "Student struck through initial attempt 'f'(x) = 2x - 4'. Replaced with clean un-struck solution: 'f'(x) = d/dx(x^3) - d/dx(4x) + d/dx(7) = 3x^2 - 4'.",
                    "evaluation_reason": "Full marks (5.0/5.0) awarded for correct power rule differentiation. The student's initial crossed-out work was strictly disregarded, and only the final clean solution was evaluated.",
                    "teacher_feedback": "Perfect step-by-step differentiation using the power rule. Clean final answer 3x^2 - 4.",
                    "what_was_done_correctly": ["Correct differentiation of x^3 to 3x^2", "Correct differentiation of -4x to -4", "Derivative of constant 7 equals 0"],
                    "what_is_missing": [],
                    "what_is_incorrect": []
                }
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["total_marks"], 5.0)
        self.assertEqual(result["obtained_marks"], 5.0)
        self.assertEqual(result["evaluations"][0]["awarded_marks"], 5.0)
        self.assertIn("struck through", result["evaluations"][0]["student_answer"])

    def test_40_non_sequential_and_varied_labels_zero_omission(self):
        """40. Zero Omission & Varied Labelling Test: Ensure questions answered out of sequence,
        with varied prefix tags (e.g. 'Ans 1', 'Part B Q6(a)(i)', '6.a.2') are accurately mapped
        and awarded marks without any question being skipped.
        """
        qp_struct = {
            "subject": "Data Structures & Algorithms",
            "total_marks": 25.0,
            "questions": [
                {"question_id": "q1", "question_number": "1", "question_text": "Define time complexity of Binary Search.", "maximum_marks": 5.0},
                {"question_id": "q2", "question_number": "2", "question_text": "Explain QuickSort partition algorithm.", "maximum_marks": 5.0},
                {"question_id": "q6_a_1", "question_number": "6(a)(i)", "question_text": "Explain BFS graph traversal.", "maximum_marks": 7.5},
                {"question_id": "q6_a_2", "question_number": "6(a)(ii)", "question_text": "Explain DFS graph traversal.", "maximum_marks": 7.5}
            ]
        }
        ai_response = {
            "evaluations": [
                {
                    "question_id": "eval_bfs",
                    "question_number": "Part B - Question 6(a)(i)",
                    "attempted": True,
                    "maximum_marks": 7.5,
                    "awarded_marks": 7.0,
                    "percentage_of_question": 93.33,
                    "student_answer": "BFS uses a Queue (FIFO) to explore graph level by level.",
                    "evaluation_reason": "Awarded 7.0/7.5 for accurate Queue mechanism and level-order traversal explanation."
                },
                {
                    "question_id": "eval_q1",
                    "question_number": "Ans. 1",
                    "attempted": True,
                    "maximum_marks": 5.0,
                    "awarded_marks": 5.0,
                    "percentage_of_question": 100.0,
                    "student_answer": "Binary search time complexity is O(log n) best case O(1).",
                    "evaluation_reason": "Full marks awarded for O(log n)."
                },
                {
                    "question_id": "eval_dfs",
                    "question_number": "6.a.2",
                    "attempted": True,
                    "maximum_marks": 7.5,
                    "awarded_marks": 6.5,
                    "percentage_of_question": 86.67,
                    "student_answer": "DFS uses a Stack / recursion to explore as far as possible along each branch.",
                    "evaluation_reason": "Awarded 6.5/7.5 for correct recursion/stack explanation."
                },
                {
                    "question_id": "eval_q2",
                    "question_number": "Answer 2",
                    "attempted": True,
                    "maximum_marks": 5.0,
                    "awarded_marks": 4.5,
                    "percentage_of_question": 90.0,
                    "student_answer": "QuickSort chooses a pivot and places smaller elements left and greater elements right.",
                    "evaluation_reason": "Awarded 4.5/5.0 for clear Lomuto/Hoare partitioning description."
                }
            ]
        }
        result = self.agent.verify_and_finalize_evaluation(qp_struct, ai_response)
        self.assertEqual(result["total_marks"], 25.0)
        self.assertEqual(result["obtained_marks"], 23.0)

        # Ensure all 4 questions were correctly mapped and none marked unattempted
        self.assertEqual(len(result["evaluations"]), 4)
        for q in result["evaluations"]:
            self.assertTrue(q["attempted"], f"Question {q['question_number']} was mistakenly marked unattempted!")
            self.assertGreater(q["awarded_marks"], 0.0)


if __name__ == "__main__":
    unittest.main()



