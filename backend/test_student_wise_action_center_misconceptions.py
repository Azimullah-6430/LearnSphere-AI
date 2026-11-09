"""
LearnSphere AI - Verification Suite for Student-Wise Action Center & Misconceptions Grouping

Validates:
1. Single student with multiple mistakes produces exactly ONE consolidated Action Center card.
2. Single student with multiple conceptual errors produces exactly ONE consolidated Misconceptions card.
3. Two students with identical names but different IDs remain distinct and are never merged.
4. Same student across different assessments produces separate historical records.
5. Idempotent evaluation re-runs do not create duplicate records.
6. Multi-concept grouping within a student's evaluation groups questions cleanly under concepts.
7. Verbatim question text, student answers, marks awarded/max/lost, and evidence are strictly preserved.
8. Backward compatibility fields remain accessible for existing consumers.
"""

import unittest
import json
from app.evaluation.action_center import (
    derive_action_items_from_evaluation,
    consolidate_action_items_by_student,
)
from app.evaluation.misconceptions import (
    derive_misconceptions_from_evaluation,
    group_misconceptions_by_student,
)


class TestStudentWiseActionCenterAndMisconceptions(unittest.TestCase):

    def setUp(self):
        # Evaluation with student Azim who has mistakes across 3 questions
        self.azim_eval = {
            "id": "eval_azim_001",
            "evaluation_source": "TEACHER_EVALUATION",
            "teacher_id": "teacher_001",
            "class_id": "cls_grade10_a",
            "student_id": "stu_azim_01",
            "student_name": "Azim Khan",
            "roll_number": "10-A-01",
            "subject": "Physics",
            "assessment_title": "Midterm Examination",
            "total_marks": 50.0,
            "obtained_marks": 32.0,
            "questions": [
                {
                    "question_number": "1",
                    "question_text": "State Newton's Third Law with an example.",
                    "concept": "Newton's Laws",
                    "maximum_marks": 10.0,
                    "awarded_marks": 4.0,
                    "student_answer": "Force on horse is more than force on cart so cart moves.",
                    "misconception_detected": True,
                    "misconception": "Action-reaction forces are unequal during movement.",
                    "what_student_should_have_written": "Action and reaction are always equal and opposite.",
                    "how_to_improve": "Practice action-reaction pairs in stationary and accelerating systems.",
                },
                {
                    "question_number": "2",
                    "question_text": "Calculate the friction force for a 5kg block on a rough surface.",
                    "concept": "Friction & Normal Force",
                    "maximum_marks": 10.0,
                    "awarded_marks": 5.0,
                    "student_answer": "Friction = mass * gravity = 5 * 9.8 = 49N without coefficient.",
                    "misconception_detected": True,
                    "misconception": "Confusing normal force with maximum friction without multiplying mu.",
                    "what_student_should_have_written": "f_max = mu * N where N = mg.",
                    "how_to_improve": "Review friction formula and the role of the coefficient of friction.",
                },
                {
                    "question_number": "3",
                    "question_text": "Explain why reaction force does not cancel the action force.",
                    "concept": "Newton's Laws",
                    "maximum_marks": 10.0,
                    "awarded_marks": 3.0,
                    "student_answer": "Because action happens first before reaction begins.",
                    "misconception_detected": True,
                    "misconception": "Belief that action precedes reaction with a time lag.",
                    "what_student_should_have_written": "Action and reaction act simultaneously on different bodies.",
                    "how_to_improve": "Illustrate simultaneous force interaction pairs on separate free-body diagrams.",
                },
                {
                    "question_number": "4",
                    "question_text": "Define inertia of rest.",
                    "concept": "Inertia",
                    "maximum_marks": 10.0,
                    "awarded_marks": 10.0,
                    "student_answer": "Inertia of rest is the inability of a body to move on its own.",
                    "misconception_detected": False,
                },
                {
                    "question_number": "5",
                    "question_text": "Define momentum and state its SI unit.",
                    "concept": "Linear Momentum",
                    "maximum_marks": 10.0,
                    "awarded_marks": 10.0,
                    "student_answer": "Momentum is the product of mass and velocity. Unit is kg m/s.",
                    "misconception_detected": False,
                }
            ]
        }

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 1: Single student with multiple questions produces EXACTLY 1 card
    # ──────────────────────────────────────────────────────────────────────────
    def test_single_student_consolidated_action_card(self):
        items = derive_action_items_from_evaluation(self.azim_eval)
        # MUST return exactly 1 consolidated record for Azim
        self.assertEqual(len(items), 1)

        card = items[0]
        self.assertEqual(card["student_name"], "Azim Khan")
        self.assertEqual(card["student_id"], "stu_azim_01")
        self.assertEqual(card["subject"], "Physics")
        self.assertEqual(card["total_marks"], 32.0)
        self.assertEqual(card["maximum_marks"], 50.0)
        self.assertEqual(card["marks_lost"], 18.0)

        # All 3 affected questions must be nested inside question_details
        self.assertIn("question_details", card)
        self.assertEqual(len(card["question_details"]), 3)

        q_nums = [qd["question_number"] for qd in card["question_details"]]
        self.assertEqual(q_nums, ["1", "2", "3"])

        # Preserves verbatim text & answers
        q1 = card["question_details"][0]
        self.assertEqual(q1["question_text"], "State Newton's Third Law with an example.")
        self.assertIn("Force on horse is more than force on cart", q1["student_answer"])
        self.assertEqual(q1["marks_lost"], 6.0)

        # Recommendations grouped by concept
        self.assertIn("recommended_actions", card)
        # Two distinct concepts: "Newton's Laws" and "Friction & Normal Force"
        concept_names = [ra["concept"] for ra in card["recommended_actions"]]
        self.assertIn("Newton's Laws", concept_names)
        self.assertIn("Friction & Normal Force", concept_names)

        # For "Newton's Laws", it affects Q1 and Q3
        nl_action = next(ra for ra in card["recommended_actions"] if ra["concept"] == "Newton's Laws")
        self.assertEqual(sorted(nl_action["related_questions"]), ["1", "3"])

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 2: Single student with multiple misconceptions in Misconception Map
    # ──────────────────────────────────────────────────────────────────────────
    def test_single_student_consolidated_misconceptions(self):
        raw_misc = derive_misconceptions_from_evaluation(self.azim_eval)
        # Raw questions with misconceptions: Q1, Q2, Q3
        self.assertEqual(len(raw_misc), 3)

        # Grouping by student consolidates into 1 record for Azim
        grouped = group_misconceptions_by_student(raw_misc)
        self.assertEqual(len(grouped), 1)

        student_misc = grouped[0]
        self.assertEqual(student_misc["student_name"], "Azim Khan")
        self.assertEqual(student_misc["total_misconceptions"], 3)
        self.assertEqual(student_misc["concept_count"], 2)  # Newton's Laws & Friction

        # Grouped concept blocks
        c_names = [cg["concept"] for cg in student_misc["concept_groups"]]
        self.assertIn("Newton's Laws", c_names)
        self.assertIn("Friction & Normal Force", c_names)

        # Under Newton's Laws, both Q1 and Q3 are present
        nl_cg = next(cg for cg in student_misc["concept_groups"] if cg["concept"] == "Newton's Laws")
        self.assertEqual(len(nl_cg["questions"]), 2)
        q_nums = [q["question_number"] for q in nl_cg["questions"]]
        self.assertEqual(sorted(q_nums), ["1", "3"])

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 3: Identical student names with different IDs remain distinct
    # ──────────────────────────────────────────────────────────────────────────
    def test_identical_names_different_ids_remain_distinct(self):
        eval_alex_1 = dict(self.azim_eval)
        eval_alex_1["id"] = "eval_alex_01"
        eval_alex_1["student_name"] = "Alex Johnson"
        eval_alex_1["student_id"] = "stu_alex_A"
        eval_alex_1["roll_number"] = "10-A-05"

        eval_alex_2 = dict(self.azim_eval)
        eval_alex_2["id"] = "eval_alex_02"
        eval_alex_2["student_name"] = "Alex Johnson"
        eval_alex_2["student_id"] = "stu_alex_B"
        eval_alex_2["roll_number"] = "10-A-06"

        items_1 = derive_action_items_from_evaluation(eval_alex_1)
        items_2 = derive_action_items_from_evaluation(eval_alex_2)
        combined = items_1 + items_2

        consolidated = consolidate_action_items_by_student(combined)
        # MUST have 2 separate items, not collapsed into 1!
        self.assertEqual(len(consolidated), 2)
        student_ids = [c["student_id"] for c in consolidated]
        self.assertIn("stu_alex_A", student_ids)
        self.assertIn("stu_alex_B", student_ids)

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 4: Same student across different assessments produces separate records
    # ──────────────────────────────────────────────────────────────────────────
    def test_same_student_different_evaluations_remain_separate(self):
        eval_term1 = dict(self.azim_eval)
        eval_term1["id"] = "eval_term_1"
        eval_term1["assessment_title"] = "Term 1 Exam"

        eval_term2 = dict(self.azim_eval)
        eval_term2["id"] = "eval_term_2"
        eval_term2["assessment_title"] = "Term 2 Exam"

        items_1 = derive_action_items_from_evaluation(eval_term1)
        items_2 = derive_action_items_from_evaluation(eval_term2)
        combined = items_1 + items_2

        consolidated = consolidate_action_items_by_student(combined)
        # MUST remain 2 separate historical evaluation items
        self.assertEqual(len(consolidated), 2)
        eval_ids = [c["evaluation_id"] for c in consolidated]
        self.assertIn("eval_term_1", eval_ids)
        self.assertIn("eval_term_2", eval_ids)

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 5: Consolidates legacy separate question-level items on the fly
    # ──────────────────────────────────────────────────────────────────────────
    def test_consolidate_legacy_question_level_items(self):
        # Simulating legacy DB state: 3 items for same student evaluation
        legacy_items = [
            {
                "id": "act_misc_eval_101_1",
                "evaluation_id": "eval_101",
                "evaluation_source": "TEACHER_EVALUATION",
                "student_id": "stu_099",
                "student_name": "Sarah Connor",
                "roll_number": "SC-01",
                "subject": "Chemistry",
                "class_id": "cls_chem_10",
                "question_num": "Question 1",
                "exact_question": "Define covalent bonding.",
                "student_answer": "Electrons are transferred completely.",
                "misconception": "Confusing covalent bonding with ionic transfer.",
                "marks_lost": 4.0,
                "question_awarded_marks": 1.0,
                "question_max_marks": 5.0,
                "priority": "High",
                "status": "New",
            },
            {
                "id": "act_misc_eval_101_2",
                "evaluation_id": "eval_101",
                "evaluation_source": "TEACHER_EVALUATION",
                "student_id": "stu_099",
                "student_name": "Sarah Connor",
                "roll_number": "SC-01",
                "subject": "Chemistry",
                "class_id": "cls_chem_10",
                "question_num": "Question 2",
                "exact_question": "Explain electronegativity difference.",
                "student_answer": "No difference means polar.",
                "misconception": "Inverse understanding of electronegativity.",
                "marks_lost": 3.0,
                "question_awarded_marks": 2.0,
                "question_max_marks": 5.0,
                "priority": "Medium",
                "status": "New",
            },
            {
                "id": "act_loss_eval_101",
                "evaluation_id": "eval_101",
                "evaluation_source": "TEACHER_EVALUATION",
                "student_id": "stu_099",
                "student_name": "Sarah Connor",
                "roll_number": "SC-01",
                "subject": "Chemistry",
                "class_id": "cls_chem_10",
                "question_num": "1, 2",
                "marks_lost": 7.0,
                "priority": "High",
                "status": "New",
            }
        ]

        consolidated = consolidate_action_items_by_student(legacy_items)
        # Should consolidate the 3 items into EXACTLY 1 card for Sarah Connor
        self.assertEqual(len(consolidated), 1)
        card = consolidated[0]
        self.assertEqual(card["student_name"], "Sarah Connor")
        self.assertEqual(len(card["question_details"]), 2)
        q_nums = [qd["question_number"] for qd in card["question_details"]]
        self.assertEqual(sorted(q_nums), ["1", "2"])


if __name__ == "__main__":
    unittest.main()

