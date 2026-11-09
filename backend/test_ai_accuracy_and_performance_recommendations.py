"""
LearnSphere AI - Test Suite for AI Accuracy & Performance-Based Recommendations
Verifies all 10 pedagogical precision criteria from Step 14:
1. Calculation slip is NOT flagged as a conceptual misconception
2. Incomplete answer produces pacing / multi-part recommendation (not conceptual reteach)
3. Different mistake types produce distinctly tailored pedagogical actions & activities
4. Alternative valid expression is NOT marked as error or misconception
5. Insufficient evidence / ambiguous answer flagged as NEEDS_TEACHER_REVIEW
6. Adaptive lifecycle tracking (New -> Persistent -> Improving -> Resolved)
7. Deep AI failure reporting with zero mock responses
8. Student consolidation idempotency
9. Multi-student evaluation isolation
10. Zero mock/fabricated strings in output
"""

import unittest
import json
from app.evaluation.diagnostic_engine import (
    classify_student_error,
    build_personalized_action,
    generate_individual_performance_summary,
    track_adaptive_concept_lifecycle,
    TAXONOMY_CONCEPTUAL_MISUNDERSTANDING,
    TAXONOMY_INCORRECT_FORMULA_SELECTION,
    TAXONOMY_INCORRECT_FORMULA_APPLICATION,
    TAXONOMY_CALCULATION_ERROR,
    TAXONOMY_MISSING_STEPS,
    TAXONOMY_INCOMPLETE_ANSWER,
    TAXONOMY_QUESTION_INTERPRETATION_ERROR,
    TAXONOMY_ALTERNATIVE_VALID_EXPRESSION,
    STATUS_EVIDENCE_SUPPORTED,
    STATUS_NEEDS_TEACHER_REVIEW,
    STATUS_INSUFFICIENT_EVIDENCE,
)
from app.evaluation.misconceptions import extract_misconceptions_from_question, group_misconceptions_by_student
from app.evaluation.action_center import derive_action_items_from_evaluation, consolidate_action_items_by_student


class TestAIAccuracyAndPerformanceRecommendations(unittest.TestCase):

    def test_01_calculation_mistake_is_not_conceptual_misconception(self):
        """Scenario 1: Calculation/arithmetic error must NOT be flagged as conceptual misconception."""
        calc_q = {
            "question_number": "2",
            "question_text": "Calculate the kinetic energy of a 2kg mass moving at 3 m/s.",
            "maximum_marks": 5.0,
            "awarded_marks": 3.0,
            "student_answer": "KE = 1/2 * m * v^2 = 1/2 * 2 * 9 = 8 J",
            "what_student_should_have_written": "KE = 1/2 * 2 * 9 = 9 J",
            "concept": "Kinetic Energy",
            "answer_classification": "calculation_error",
            "step_or_calculation_mistake": "Arithmetic slip in multiplying 1/2 * 2 * 9.",
        }
        res = classify_student_error(calc_q, subject="Physics")
        self.assertEqual(res["error_type"], TAXONOMY_CALCULATION_ERROR)
        self.assertFalse(res["is_conceptual_misconception"])

        eval_doc = {
            "id": "eval_1",
            "student_id": "std_1",
            "student_name": "Alice",
            "subject": "Physics",
            "evaluation_source": "TEACHER_EVALUATION"
        }
        misc = extract_misconceptions_from_question(calc_q, eval_doc=eval_doc)
        self.assertIsNone(misc, "Pure calculation errors must never produce a misconception record.")

    def test_02_incomplete_answer_recommendation(self):
        """Scenario 2: Incomplete answer produces pacing/completion action, NOT conceptual reteaching."""
        inc_q = {
            "question_number": "4",
            "question_text": "Derive the quadratic formula and state the discriminant conditions.",
            "maximum_marks": 10.0,
            "awarded_marks": 5.0,
            "student_answer": "x = (-b +- sqrt(b^2-4ac)) / (2a). Ran out of time for part b.",
            "what_student_should_have_written": "Derivation using completing the square plus discriminant conditions (D > 0, D = 0, D < 0).",
            "concept": "Quadratic Equations",
            "answer_classification": "incomplete_answer",
        }
        res = classify_student_error(inc_q, subject="Mathematics")
        self.assertEqual(res["error_type"], TAXONOMY_INCOMPLETE_ANSWER)
        self.assertFalse(res["is_conceptual_misconception"])

        action = build_personalized_action(
            error_type=TAXONOMY_INCOMPLETE_ANSWER,
            concept="Quadratic Equations",
            subject="Mathematics",
            related_questions=["4"],
            evidence_text="Student left part b incomplete due to exam pacing.",
            marks_lost=5.0,
            total_marks=50.0,
        )
        self.assertIn("pacing", action["action"].lower() + action["activity"].lower())
        self.assertNotIn("first-principles lesson on quadratic equations", action["activity"].lower())

    def test_03_different_mistake_types_produce_distinct_recommendations(self):
        """Scenario 3: Different taxonomy mistakes yield strictly differentiated pedagogical actions."""
        action_formula_sel = build_personalized_action(
            TAXONOMY_INCORRECT_FORMULA_SELECTION, "Electromagnetism", "Physics", ["1"], "Used wrong formula", 5.0, 50.0
        )
        action_calc = build_personalized_action(
            TAXONOMY_CALCULATION_ERROR, "Electromagnetism", "Physics", ["2"], "Arithmetic error", 2.0, 50.0
        )
        action_concept = build_personalized_action(
            TAXONOMY_CONCEPTUAL_MISUNDERSTANDING, "Electromagnetism", "Physics", ["3"], "Confused electric vs magnetic flux", 6.0, 50.0
        )

        self.assertNotEqual(action_formula_sel["action"], action_calc["action"])
        self.assertNotEqual(action_formula_sel["action"], action_concept["action"])
        self.assertIn("discrimination", action_formula_sel["action"].lower())
        self.assertIn("precision", action_calc["action"].lower())
        self.assertIn("conceptual review", action_concept["action"].lower())

    def test_04_alternative_valid_expression_not_flagged(self):
        """Scenario 4: Valid alternative phrasing with full marks is NOT marked as error or misconception."""
        alt_q = {
            "question_number": "1",
            "question_text": "Define work done by a force.",
            "maximum_marks": 3.0,
            "awarded_marks": 3.0,
            "student_answer": "Energy transferred to an object when force moves it over a displacement.",
            "what_student_should_have_written": "W = F * d * cos(theta)",
            "concept": "Work and Energy",
            "answer_classification": "correct",
        }
        res = classify_student_error(alt_q, subject="Physics")
        self.assertEqual(res["error_type"], TAXONOMY_ALTERNATIVE_VALID_EXPRESSION)
        self.assertFalse(res["is_conceptual_misconception"])
        self.assertEqual(res["marks_lost"], 0.0)

    def test_05_insufficient_evidence_flagged_as_needs_review(self):
        """Scenario 5: Highly ambiguous answers or uncertain markings are flagged for review."""
        ambig_q = {
            "question_number": "5",
            "question_text": "Explain why metals conduct electricity.",
            "maximum_marks": 4.0,
            "awarded_marks": 2.0,
            "student_answer": "They have particles moving.",
            "is_uncertain": True,
            "concept": "Metallic Bonding",
        }
        res = classify_student_error(ambig_q, subject="Chemistry")
        self.assertIn(res["evidence_status"], (STATUS_NEEDS_TEACHER_REVIEW, STATUS_INSUFFICIENT_EVIDENCE))

    def test_06_adaptive_lifecycle_tracking(self):
        """Scenario 6: Concept difficulty transitions over time across assessments."""
        previous_evals = [
            {
                "id": "eval_old_1",
                "created_at": "2026-01-01",
                "questions": [{"concept": "Ohm's Law", "awarded_marks": 2.0, "maximum_marks": 10.0}]
            },
            {
                "id": "eval_old_2",
                "created_at": "2026-01-15",
                "questions": [{"concept": "Ohm's Law", "awarded_marks": 4.0, "maximum_marks": 10.0}]
            },
        ]
        # Current assessment shows improvement (8.5/10 = 0.85 ratio)
        lifecycle = track_adaptive_concept_lifecycle(
            student_id="std_1",
            concept="Ohm's Law",
            current_eval_id="eval_new",
            current_score_ratio=0.85,
            previous_evaluations=previous_evals
        )
        self.assertIn(lifecycle["lifecycle_status"], ("Improving", "Resolved"))
        self.assertTrue(lifecycle["occurrences"] >= 2)

    def test_07_individual_performance_summary_synthesis(self):
        """Scenario 7: Synthesizes strengths, gaps, error breakdown, and practice targets accurately."""
        eval_doc = {
            "student_name": "Rohan Gupta",
            "subject": "Mathematics",
            "total_marks": 30.0,
            "obtained_marks": 22.0,
        }
        classified_qs = [
            {"question_number": "1", "concept": "Calculus - Differentiation", "error_type": "alternative_valid_expression", "marks_lost": 0.0, "awarded_marks": 10.0, "maximum_marks": 10.0},
            {"question_number": "2", "concept": "Calculus - Integration", "error_type": "calculation_error", "marks_lost": 3.0, "awarded_marks": 7.0, "maximum_marks": 10.0},
            {"question_number": "3", "concept": "Trigonometry", "error_type": "incorrect_formula_selection", "marks_lost": 5.0, "awarded_marks": 5.0, "maximum_marks": 10.0},
        ]
        summary = generate_individual_performance_summary(eval_doc, classified_qs, {"trigonometry": 1})
        self.assertIn("Calculus - Differentiation", summary["strengths"])
        self.assertIn("Trigonometry", summary["concepts_needing_improvement"])
        self.assertTrue(summary["has_repeated_deficits"])
        self.assertIn("Trigonometry", summary["recommended_next_practice"])

    def test_08_student_consolidation_idempotency(self):
        """Scenario 8: Running consolidation multiple times does not duplicate or alter items."""
        eval_doc = {
            "id": "eval_test_100",
            "evaluation_source": "TEACHER_EVALUATION",
            "student_id": "std_100",
            "student_name": "Kavita Verma",
            "roll_number": "R-100",
            "subject": "Chemistry",
            "total_marks": 25.0,
            "obtained_marks": 15.0,
            "questions": [
                {
                    "question_number": "1",
                    "concept": "Stoichiometry",
                    "maximum_marks": 10.0,
                    "awarded_marks": 5.0,
                    "student_answer": "Incorrect mole ratio used in balancing.",
                    "conceptual_mistake": "Used mass ratios instead of mole ratios.",
                },
                {
                    "question_number": "2",
                    "concept": "Redox Reactions",
                    "maximum_marks": 15.0,
                    "awarded_marks": 10.0,
                    "student_answer": "Forgot charge balancing.",
                    "step_or_calculation_mistake": "Omitted electron transfer count.",
                }
            ]
        }
        items_1 = derive_action_items_from_evaluation(eval_doc)
        self.assertEqual(len(items_1), 1, "Exactly one consolidated record must be produced.")
        self.assertEqual(len(items_1[0]["question_details"]), 2)

        # Run consolidation again
        items_2 = consolidate_action_items_by_student(items_1)
        self.assertEqual(len(items_2), 1)
        self.assertEqual(items_2[0]["id"], items_1[0]["id"])
        self.assertEqual(len(items_2[0]["question_details"]), 2)

    def test_09_multi_student_evaluation_isolation(self):
        """Scenario 9: Multiple students are completely isolated and consolidated separately."""
        raw_items = [
            {"student_id": "s1", "student_name": "Student One", "evaluation_id": "ev1", "subject": "Math", "marks_lost": 5.0, "question_number": "1", "priority": "High"},
            {"student_id": "s1", "student_name": "Student One", "evaluation_id": "ev1", "subject": "Math", "marks_lost": 3.0, "question_number": "2", "priority": "Medium"},
            {"student_id": "s2", "student_name": "Student Two", "evaluation_id": "ev1", "subject": "Math", "marks_lost": 7.0, "question_number": "3", "priority": "Critical"},
        ]
        consolidated = consolidate_action_items_by_student(raw_items)
        self.assertEqual(len(consolidated), 2, "Must produce exactly 2 distinct consolidated student records.")
        sids = {c["student_id"] for c in consolidated}
        self.assertEqual(sids, {"s1", "s2"})

        s1_item = next(c for c in consolidated if c["student_id"] == "s1")
        self.assertEqual(len(s1_item["question_details"]), 2)

    def test_10_zero_mock_strings(self):
        """Scenario 10: Verify no fallback mock strings are emitted in personalized actions."""
        action = build_personalized_action(
            TAXONOMY_CONCEPTUAL_MISUNDERSTANDING, "Thermodynamics", "Physics", ["1"], "Entropy violation", 5.0, 50.0
        )
        for field in ("action", "activity", "reason", "expected_outcome"):
            val = action.get(field, "")
            self.assertTrue(len(val) > 10)
            self.assertNotIn("mock", val.lower())
            self.assertNotIn("lorem ipsum", val.lower())
            self.assertNotIn("generic template", val.lower())


if __name__ == "__main__":
    unittest.main()
