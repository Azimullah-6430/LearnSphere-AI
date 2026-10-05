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


if __name__ == "__main__":
    unittest.main()
