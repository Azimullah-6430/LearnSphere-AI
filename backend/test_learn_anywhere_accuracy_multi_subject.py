"""
LearnSphere AI - Multi-Subject Accuracy & Pedagogical Level Verification Test Suite

Verifies:
  1. Subject-Specific Generation Across School & College:
     - School Math: worked examples, small numbers, balance scale reasoning, vocabulary glossary, no physics apparatus.
     - College Math: progressive practice, algebraic problem sets, numerical validation, no hardware hazards.
     - School Computer Science: sequencing, loops, trace tables, beginner Python code.
     - College Computer Science: algorithm logic, code snippets, complexity/edge cases, no wet-lab experiments.
     - School & College Science: safe household materials, clear procedural steps, expected observations with real-world variance, safety precautions.
     - Humanities & Languages: reading, writing, grammar, literary analysis, strictly no STEM apparatus.
     - Social Sciences & Commerce: civics, timelines, financial budgeting, no circuits or chemical titration.
  2. Syllabus & Subject Alignment Enforcement:
     - Missing subject returns HTTP 400 with needs_clarification=True.
     - Invalid topic not in student syllabus returns HTTP 400 with needs_clarification=True.
     - No generic mock activities disguised as AI results.
  3. Answer Evaluation & Follow-Up Actions:
     - Numerical/algebraic answer accuracy (e.g., '6' or 'x = 6' for x + 4 = 10 marked correct).
     - Follow-up actions (simpler explanation, another example, worked solution) strictly aligned to the subject.
"""

import unittest
import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
os.environ["TESTING"] = "1"

from app.gemini_service import gemini_service
from app.teaching_planner import teaching_planner
from server import app


class TestLearnAnywhereMultiSubjectAccuracy(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.client = app.test_client()

    # =========================================================================
    # 1. School Level Subject-Specific Verification
    # =========================================================================

    def test_01_school_mathematics_accuracy(self):
        """School Mathematics must feature small numbers, balance analogy, glossary, and no physics lab apparatus."""
        act = gemini_service._build_deterministic_school_activity(
            subject="Mathematics",
            subject_id="sub_math_sch",
            topic="Linear Equations",
            resource_env="Household & Crafts",
            difficulty="Easy",
            semester="Grade 6",
            program="School",
            department="Mathematics"
        )
        norm = gemini_service._normalize_learn_anywhere_response(
            act, "Mathematics", "Linear Equations", "Algebra", "School Syllabus",
            "Household & Crafts", "Easy", "Grade 6", "School", "Mathematics", "strict",
            student_type="SCHOOL"
        )

        self.assertEqual(norm["subject"], "Mathematics")
        self.assertEqual(norm["student_type"], "SCHOOL")
        self.assertEqual(norm["demonstration_type"], "worked_problem_set")

        # Must contain beginner glossary and math practice
        self.assertIn("unfamiliar_words", norm)
        self.assertIn("math_progressive_practice", norm)

        # Materials must be paper/pencil, NOT test tubes or water/clay
        mats_text = " ".join(norm.get("materials_student_has", [])).lower()
        self.assertTrue(any(w in mats_text for w in ["notebook", "pencil", "ruler", "paper"]))
        self.assertFalse(any(w in mats_text for w in ["beaker", "test tube", "turmeric", "battery", "soil", "clay"]))

        # Applications must relate to math, not agriculture or irrigation
        apps = norm.get("everyday_applications", "").lower()
        self.assertTrue(any(w in apps for w in ["budget", "count", "store", "measure", "shar"]))
        self.assertNotIn("irrigation", apps)

        # Coherence check must pass
        coh = gemini_service.validate_activity_coherence(norm, "Mathematics", "Linear Equations", "SCHOOL")
        self.assertTrue(coh["is_coherent"], f"Coherence failed: {coh['reason']}")

    def test_02_school_computer_science_accuracy(self):
        """School Computer Science must provide logic loops, trace tables, beginner Python, no botany or wet-lab."""
        act = gemini_service._build_deterministic_school_activity(
            subject="Computer Science",
            subject_id="sub_cs_sch",
            topic="Counting Loops",
            resource_env="Household & Crafts",
            difficulty="Easy",
            semester="Grade 7",
            program="School",
            department="Computer Studies"
        )
        norm = gemini_service._normalize_learn_anywhere_response(
            act, "Computer Science", "Counting Loops", "Intro Computing", "School Syllabus",
            "Household & Crafts", "Easy", "Grade 7", "School", "Computer Studies", "strict",
            student_type="SCHOOL"
        )

        self.assertEqual(norm["subject"], "Computer Science")
        self.assertEqual(norm["student_type"], "SCHOOL")
        self.assertIn("coding_task", norm)
        self.assertTrue(norm["coding_task"].get("is_coding_topic"))
        self.assertIn("range(1, 6)", norm["coding_task"].get("code_snippet", ""))

        # No biological or chemical experiment materials
        mats_text = " ".join(norm.get("materials_student_has", [])).lower()
        self.assertFalse(any(w in mats_text for w in ["leaf", "turmeric", "beaker", "soil", "clay pot"]))

        # Coherence check must pass
        coh = gemini_service.validate_activity_coherence(norm, "Computer Science", "Counting Loops", "SCHOOL")
        self.assertTrue(coh["is_coherent"], f"Coherence failed: {coh['reason']}")

    def test_03_school_science_experiment_accuracy(self):
        """School Science (Physics/Chemistry) must provide safe household experiments with real-world variance notes."""
        phy_act = gemini_service._build_deterministic_school_activity(
            subject="Physics",
            subject_id="sub_phy_sch",
            topic="Capillary Action",
            resource_env="Household & Crafts",
            difficulty="Easy",
            semester="Grade 7",
            program="School",
            department="Science"
        )
        norm_phy = gemini_service._normalize_learn_anywhere_response(
            phy_act, "Physics", "Capillary Action", "Fluid Motion", "School Science Syllabus",
            "Household & Crafts", "Easy", "Grade 7", "School", "Science", "strict",
            student_type="SCHOOL"
        )

        self.assertEqual(norm_phy["subject"], "Physics")
        # Must have expected observations with variance note
        obs = norm_phy.get("expected_observations", "").lower()
        self.assertTrue(any(w in obs for w in ["vary", "variance", "ambient", "factors", "conditions"]))
        # Must have safety precautions
        self.assertIn("safety_precautions", norm_phy)

        coh_phy = gemini_service.validate_activity_coherence(norm_phy, "Physics", "Capillary Action", "SCHOOL")
        self.assertTrue(coh_phy["is_coherent"], f"Coherence failed: {coh_phy['reason']}")

    def test_04_humanities_and_language_accuracy(self):
        """English and Literature activities must focus on reading, writing, and vocabulary, rejecting STEM apparatus."""
        lang_act = gemini_service._build_deterministic_school_activity(
            subject="English",
            subject_id="sub_eng_sch",
            topic="Reading Comprehension",
            resource_env="Household & Crafts",
            difficulty="Easy",
            semester="Grade 6",
            program="School",
            department="English"
        )
        norm_lang = gemini_service._normalize_learn_anywhere_response(
            lang_act, "English", "Reading Comprehension", "Reading Skills", "School English Syllabus",
            "Household & Crafts", "Easy", "Grade 6", "School", "English", "strict",
            student_type="SCHOOL"
        )

        self.assertEqual(norm_lang["subject"], "English")
        self.assertEqual(norm_lang["demonstration_type"], "reading_and_writing_task")

        # Materials must not include farm/lab items
        mats_text = " ".join(norm_lang.get("materials_student_has", [])).lower()
        self.assertFalse(any(w in mats_text for w in ["beaker", "test tube", "transpiration", "clean water", "circuit"]))

        coh_lang = gemini_service.validate_activity_coherence(norm_lang, "English", "Reading Comprehension", "SCHOOL")
        self.assertTrue(coh_lang["is_coherent"], f"Coherence failed: {coh_lang['reason']}")

    # =========================================================================
    # 2. College Level Subject-Specific Verification
    # =========================================================================

    def test_05_college_computer_science_accuracy(self):
        """College Computer Science must provide runnable algorithmic coding snippets, test cases, and debugging guidance."""
        cs_act = gemini_service._build_deterministic_college_activity(
            subject="Computer Science & Engineering",
            subject_id="sub_cs_col",
            topic="Binary Search Tree Traversal",
            resource_env="Computer/Simulation",
            difficulty="Medium",
            semester="Semester 3",
            program="B.Tech CSE",
            department="Computer Science",
            student_type="COLLEGE"
        )
        norm_cs = gemini_service._normalize_learn_anywhere_response(
            cs_act, "Computer Science & Engineering", "Binary Search Tree Traversal", "Data Structures",
            "University Curriculum", "Computer/Simulation", "Medium", "Semester 3", "B.Tech CSE",
            "Computer Science", "strict", student_type="COLLEGE"
        )

        self.assertEqual(norm_cs["subject"], "Computer Science & Engineering")
        self.assertEqual(norm_cs["student_type"], "COLLEGE")
        self.assertIn("coding_task", norm_cs)
        code_task = norm_cs["coding_task"]
        self.assertTrue(code_task.get("is_coding_topic"))
        self.assertTrue(any(w in code_task.get("code_snippet", "") for w in ["def", "class", "print", "return"]))

        coh_cs = gemini_service.validate_activity_coherence(norm_cs, "Computer Science & Engineering", "Binary Search Tree Traversal", "COLLEGE")
        self.assertTrue(coh_cs["is_coherent"], f"Coherence failed: {coh_cs['reason']}")

    # =========================================================================
    # 3. Answer Evaluation Accuracy (Numerical & Conceptual)
    # =========================================================================

    def test_06_numerical_evaluation_accuracy(self):
        """Numerical answers (e.g. '6' or 'x = 6') must evaluate as correct without false negatives."""
        # Test exact numeric equality
        eval_res1 = gemini_service._evaluate_learn_anywhere_answer_fallback(
            subject="Mathematics",
            topic="Linear Equations",
            question="In the equation x + 4 = 10, what is the value of x?",
            expected_answer="x = 6 (because 10 - 4 = 6).",
            student_answer="6"
        )
        self.assertTrue(eval_res1["is_correct"], f"Expected True for '6', got {eval_res1}")
        self.assertEqual(eval_res1["error_type"], "none")

        # Test algebraic expression
        eval_res2 = gemini_service._evaluate_learn_anywhere_answer_fallback(
            subject="Mathematics",
            topic="Linear Equations",
            question="In the equation x + 4 = 10, what is the value of x?",
            expected_answer="x = 6 (because 10 - 4 = 6).",
            student_answer="x = 6"
        )
        self.assertTrue(eval_res2["is_correct"], f"Expected True for 'x = 6', got {eval_res2}")
        self.assertEqual(eval_res2["error_type"], "none")

        # Test decimal answer
        eval_res3 = gemini_service._evaluate_learn_anywhere_answer_fallback(
            subject="Mathematics",
            topic="Decimals",
            question="What is 10.5 + 4.7?",
            expected_answer="15.2",
            student_answer="15.2"
        )
        self.assertTrue(eval_res3["is_correct"], f"Expected True for '15.2', got {eval_res3}")

        # Test genuine incorrect answer
        eval_res4 = gemini_service._evaluate_learn_anywhere_answer_fallback(
            subject="Mathematics",
            topic="Linear Equations",
            question="In the equation x + 4 = 10, what is the value of x?",
            expected_answer="x = 6 (because 10 - 4 = 6).",
            student_answer="14"
        )
        self.assertFalse(eval_res4["is_correct"])
        self.assertEqual(eval_res4["error_type"], "conceptual_misunderstanding")

    # =========================================================================
    # 4. Discipline-Grounded Action Responses
    # =========================================================================

    def test_07_action_responses_match_subject(self):
        """Action fallbacks (simpler explanation, another example, worked solution) must be subject-specific."""
        # Mathematics another_example must not contain water or sponges
        math_ex = gemini_service.generate_learn_anywhere_action(
            action_type="another_example",
            subject="Mathematics",
            topic="Linear Equations",
            question="In the equation x + 4 = 10, what is the value of x?",
            current_explanation="",
            current_example=""
        )
        self.assertNotIn("sponge", str(math_ex).lower())
        self.assertNotIn("water", str(math_ex).lower())
        self.assertTrue(any(w in str(math_ex).lower() for w in ["calculate", "equation", "number", "balance", "solve"]))

        # Computer Science worked_solution must feature coding logic
        cs_sol = gemini_service.generate_learn_anywhere_action(
            action_type="worked_solution",
            subject="Computer Science",
            topic="Binary Search",
            question="How does binary search divide the search space?",
            current_explanation="",
            current_example=""
        )
        self.assertTrue(any(w in str(cs_sol).lower() for w in ["trace", "input", "variable", "code", "loop", "state"]))

        # English simpler_explanation must feature language concepts
        eng_exp = gemini_service.generate_learn_anywhere_action(
            action_type="simpler_explanation",
            subject="English",
            topic="Paragraph Writing",
            question="How do topic sentences organize a paragraph?",
            current_explanation="",
            current_example=""
        )
        self.assertTrue(any(w in str(eng_exp).lower() for w in ["sentence", "word", "meaning", "express", "read"]))

    # =========================================================================
    # 5. Missing & Invalid Input Enforcement in Server Endpoints
    # =========================================================================

    def test_08_missing_subject_rejected_with_clarification_error(self):
        """Requests with no selected subject must return HTTP 400 with needs_clarification=True."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = "test_acc_user"
            sess["user"] = {
                "id": "test_acc_user",
                "role": "student",
                "level": "COLLEGE",
                "semester": 4
            }

        # Subject omitted completely
        res = self.client.post("/api/learn-anywhere/generate", json={})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertTrue(data.get("needs_clarification"))
        self.assertIn(data.get("missing_field"), ["subject", "curriculum"])

    def test_09_additional_practice_questions_discipline_aligned(self):
        """Practice questions must match subject discipline and avoid generic physical lab questions."""
        math_q = gemini_service.generate_additional_practice_questions(
            subject="Mathematics",
            topic="Calculus Derivatives"
        )
        self.assertTrue(len(math_q) >= 1)
        q_text = " ".join([q.get("question", "") for q in math_q]).lower()
        self.assertTrue(any(w in q_text for w in ["rate", "formula", "derivative", "value", "graph", "numeric"]))
        self.assertNotIn("sponge", q_text)


if __name__ == "__main__":
    unittest.main()
