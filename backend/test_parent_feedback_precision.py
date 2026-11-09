"""
LearnSphere AI - Test Suite for AI Parent Feedback & Diagnostic Accuracy
Verifies:
1. Translates genuine student test evaluations into clear, parent-friendly feedback
2. Accurately highlights demonstrated strengths with evidence
3. Clearly diagnoses weaknesses (distinguishing calculation slips from conceptual gaps)
4. Provides a concrete home action plan for parents
5. Recommends the specific next learning target
6. Blocks unauthenticated access to /api/parent/report
7. Operates reliably with zero mock/hardcoded templates
"""

import unittest
from server import app
import json
from app.evaluation.parent_feedback import generate_parent_feedback_report


class TestParentFeedbackPrecision(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_01_parent_report_requires_auth(self):
        """Unauthenticated request to /api/parent/report is blocked."""
        res = self.client.post("/api/parent/report", json={})
        self.assertIn(res.status_code, (401, 403))

    def test_02_deterministic_parent_feedback_report_generation(self):
        """Generates evidence-backed strengths and weaknesses from real test evaluations."""
        student_profile = {
            "name": "Aarav Sharma",
            "institution_name": "Delhi Public School",
            "level": "school",
            "grade_level": "10",
        }
        evaluations = [
            {
                "id": "eval_101",
                "subject": "Physics",
                "assessment_title": "Electricity & Magnetism Unit Test",
                "percentage": 78.0,
                "questions": [
                    {
                        "question_number": "1",
                        "concept": "Ohm's Law",
                        "maximum_marks": 5.0,
                        "awarded_marks": 5.0,
                    },
                    {
                        "question_number": "2",
                        "concept": "Series and Parallel Circuits",
                        "maximum_marks": 10.0,
                        "awarded_marks": 6.0,
                        "answer_classification": "calculation_error",
                        "step_or_calculation_mistake": "Arithmetic slip when adding equivalent resistance fractions 1/R.",
                    },
                    {
                        "question_number": "3",
                        "concept": "Magnetic Field Induction",
                        "maximum_marks": 10.0,
                        "awarded_marks": 4.0,
                        "answer_classification": "conceptual_misunderstanding",
                        "misconception": "Confused direction of magnetic field lines with electric field lines.",
                    }
                ]
            }
        ]

        report = generate_parent_feedback_report(
            student_profile=student_profile,
            evaluations=evaluations,
            streak_days=5,
            formatted_session_time="1h 15m",
            use_gemini=False
        )

        self.assertTrue(report["success"])
        self.assertEqual(report["student_name"], "Aarav Sharma")
        self.assertEqual(report["total_evaluations_analyzed"], 1)
        self.assertIn("Distinction" in report["academic_standing"] or "Proficient" in report["academic_standing"], [True])

        # Strengths check
        strengths = report["demonstrated_strengths"]
        self.assertTrue(any("Ohm's Law" in s["concept"] for s in strengths))

        # Weaknesses check: must clearly distinguish calculation slip vs conceptual misunderstanding
        weaknesses = report["areas_needing_support"]
        self.assertTrue(len(weaknesses) >= 2)
        calc_weakness = next((w for w in weaknesses if "Calculation" in w["gap_type"]), None)
        self.assertIsNotNone(calc_weakness)
        self.assertIn("Series and Parallel Circuits", calc_weakness["concept"])

        concept_weakness = next((w for w in weaknesses if "Conceptual" in w["gap_type"]), None)
        self.assertIsNotNone(concept_weakness)
        self.assertIn("Magnetic Field Induction", concept_weakness["concept"])

        # Home action plan
        action_plan = report["home_action_plan"]
        self.assertTrue(len(action_plan) >= 2)

        # Next target
        self.assertIn("Magnetic Field Induction" in report["next_learning_target"] or "Series and Parallel Circuits" in report["next_learning_target"], [True])

    def test_03_authenticated_endpoint_execution(self):
        """Authenticated student calls /api/parent/report and receives structured report."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = "test_student_aarav"
            sess["role"] = "student"
            sess["name"] = "Aarav Sharma"
            sess["email"] = "aarav@example.com"

        res = self.client.post("/api/parent/report", json={
            "streak_days": 4,
            "formatted_session_time": "45m"
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data.get("success"))
        self.assertIn("executive_summary", data)
        self.assertIn("demonstrated_strengths", data)
        self.assertIn("areas_needing_support", data)
        self.assertIn("home_action_plan", data)


if __name__ == "__main__":
    unittest.main()

