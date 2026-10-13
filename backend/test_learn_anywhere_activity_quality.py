import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
os.environ["TESTING"] = "1"

from app.gemini_service import gemini_service


class TestLearnAnywhereActivityQuality(unittest.TestCase):
    """
    Quality verification for Learn from Anywhere activities:
    - Teach one identifiable concept
    - Completeable task
    - Explains why the task matters (why_it_matters)
    - Maths: method and calculations, progressive difficulty Easy/Medium/Hard
    - Computer Science: runnable code matching language and level, run instructions, expected output, small modification task
    - Science: distinguishes expected results from guaranteed results
    - English and social science: model answer and assessment checklist
    - Plain, encouraging language without fake percentage claims or unsupported claims
    """

    def test_01_maths_progressive_difficulty_and_calculations(self):
        """Maths activities must provide progressive difficulty (Easy, Medium, Hard) and show method & calculations."""
        res = gemini_service.generate_learn_anywhere(
            subject="Mathematics",
            topic="Linear Equations and Problem Solving",
            student_type="COLLEGE",
            semester="2",
            program="B.Sc Mathematics",
            department="Mathematics"
        )
        self.assertIsInstance(res, dict)
        self.assertTrue(bool(res.get("why_it_matters")), "Must explain why the task matters")
        self.assertNotIn("boost your marks by", str(res.get("why_it_matters")).lower())
        self.assertNotIn("guaranteed", str(res.get("why_it_matters")).lower())

        prog = res.get("math_progressive_practice")
        self.assertIsInstance(prog, dict, "Maths must provide math_progressive_practice")
        for level in ["easy", "medium", "hard"]:
            self.assertIn(level, prog, f"Must include {level} tier")
            tier = prog[level]
            self.assertTrue(bool(tier.get("question")), f"{level} must have a question")
            self.assertTrue(bool(tier.get("method_and_calculations")), f"{level} must have method and calculations")
            self.assertTrue(bool(tier.get("answer")), f"{level} must have an answer")
            # Verify method shows step-by-step calculation
            self.assertTrue(
                "step" in tier["method_and_calculations"].lower() or "=" in tier["method_and_calculations"],
                f"{level} must show calculation steps, not only final answer"
            )

    def test_02_computer_science_run_output_modification_task(self):
        """Computer Science activities must include code, how to run, expected output, and a modification task."""
        res = gemini_service.generate_learn_anywhere(
            subject="Computer Science",
            topic="Binary Search Algorithm",
            student_type="COLLEGE",
            semester="3",
            program="B.Tech Computer Science",
            department="Computer Science"
        )
        self.assertIsInstance(res, dict)
        self.assertTrue(bool(res.get("why_it_matters")), "Must explain why the task matters")

        ct = res.get("coding_task")
        self.assertIsInstance(ct, dict, "Must provide coding_task")
        self.assertTrue(ct.get("is_coding_topic"))
        self.assertTrue(bool(ct.get("code_snippet") and ct.get("code_snippet") != "N/A"))
        self.assertTrue(bool(ct.get("run_instructions") and ct.get("run_instructions") != "N/A"))
        self.assertTrue(bool(ct.get("expected_output") and ct.get("expected_output") != "N/A"))
        self.assertTrue(bool(ct.get("modification_task") and ct.get("modification_task") != "N/A"))
        self.assertEqual(ct.get("code_verified"), True, "Valid Python code must be verified with ast.parse")

    def test_03_science_distinguishes_expected_from_guaranteed(self):
        """Science activities must distinguish expected results from guaranteed results."""
        res = gemini_service.generate_learn_anywhere(
            subject="Physics",
            topic="Capillarity and Surface Tension",
            student_type="COLLEGE",
            semester="4",
            program="B.Tech Mechanical",
            department="Mechanical Engineering"
        )
        self.assertIsInstance(res, dict)
        self.assertTrue(bool(res.get("why_it_matters")), "Must explain why the task matters")

        obs = str(res.get("expected_observations") or res.get("expected_observation") or "").lower()
        self.assertTrue(
            any(w in obs for w in ["vary", "variance", "conditional", "real-world", "ambient", "factors", "temperature"]),
            "Science expected results must note conditional variance / real-world factors"
        )
        self.assertTrue(bool(res.get("safety_precautions")), "Must include relevant safety precautions")
        self.assertTrue(bool(res.get("safe_substitutions")), "Must include realistic material substitutions")

    def test_04_english_and_social_science_model_answer_checklist(self):
        """English and social science activities must provide model answers or assessment checklists."""
        res_eng = gemini_service.generate_learn_anywhere(
            subject="English",
            topic="Active and Passive Voice Transformation",
            student_type="COLLEGE",
            semester="1",
            program="B.A. English",
            department="Humanities"
        )
        self.assertIsInstance(res_eng, dict)
        self.assertTrue(bool(res_eng.get("why_it_matters")), "Must explain why the task matters")
        self.assertTrue(bool(res_eng.get("model_answer")), "English must include a model answer")
        self.assertIsInstance(res_eng.get("assessment_checklist"), list, "English must include assessment checklist")
        self.assertGreaterEqual(len(res_eng.get("assessment_checklist")), 2)

        res_soc = gemini_service.generate_learn_anywhere(
            subject="Social Science",
            topic="Local Civic Governance and Panchayati Raj",
            student_type="COLLEGE",
            semester="2",
            program="B.A. Political Science",
            department="Social Sciences"
        )
        self.assertIsInstance(res_soc, dict)
        self.assertTrue(bool(res_soc.get("why_it_matters")), "Must explain why the task matters")
        self.assertTrue(bool(res_soc.get("model_answer")), "Social Science must include a model answer")
        self.assertIsInstance(res_soc.get("assessment_checklist"), list, "Social Science must include checklist")

    def test_05_school_level_math_and_cs_progressive_and_modification(self):
        """School activities adapt quality features with age-appropriate examples."""
        res_math = gemini_service.generate_learn_anywhere(
            subject="Mathematics",
            topic="Simple Addition and Subtraction Equations",
            student_type="SCHOOL",
            semester="Class 6",
            program="School Board",
            department="Mathematics"
        )
        self.assertEqual(res_math.get("student_type"), "SCHOOL")
        self.assertTrue(bool(res_math.get("why_it_matters")))
        prog = res_math.get("math_progressive_practice")
        self.assertIsInstance(prog, dict)
        self.assertIn("easy", prog)
        self.assertIn("medium", prog)
        self.assertIn("hard", prog)
        self.assertTrue(bool(prog["easy"]["method_and_calculations"]))
        self.assertTrue(any(w in prog["easy"]["method_and_calculations"].lower() for w in ["step", "subtract", "add", "multiply", "divide", "=", "-", "+"]))

        res_cs = gemini_service.generate_learn_anywhere(
            subject="Computer Science",
            topic="Introductory Loops",
            student_type="SCHOOL",
            semester="Class 7",
            program="School Board",
            department="Computer Studies"
        )
        self.assertEqual(res_cs.get("student_type"), "SCHOOL")
        self.assertTrue(bool(res_cs["coding_task"].get("modification_task")))
        self.assertTrue(bool(res_cs["coding_task"].get("run_instructions")))

    def test_06_accessibility_no_purchase_and_offline_alternative(self):
        """Activities must provide zero-cost substitutes, no-purchase guide, and offline alternative without assuming bicycles or farmland."""
        res_mech = gemini_service.generate_learn_anywhere(
            subject="Mechanical Engineering",
            topic="Levers and Moment Equilibrium",
            student_type="COLLEGE",
            semester="3",
            program="B.Tech Mechanical",
            department="Mechanical Engineering"
        )
        self.assertIsInstance(res_mech, dict)
        # Offline alternative must be present
        self.assertTrue(bool(res_mech.get("offline_alternative")), "Must provide an offline alternative")
        self.assertTrue(
            any(w in str(res_mech.get("offline_alternative")).lower() for w in ["paper", "notebook", "pencil", "diagram", "offline", "calculate"]),
            "Offline alternative must offer paper/worked or observation alternative"
        )

        # No purchase alternative must be present and free
        no_pur = str(res_mech.get("no_purchase_alternative") or "").lower()
        self.assertTrue(bool(no_pur), "Must provide no-purchase alternative")
        self.assertNotIn("must buy", no_pur)
        self.assertNotIn("purchase from store", no_pur)

        # Zero assumption of bicycles or farmland when not provided by student
        safe_subs_str = " ".join(str(s) for s in res_mech.get("safe_substitutions", [])).lower()
        self.assertNotIn("bicycle pedal", safe_subs_str, "Must not assume student has a bicycle")
        self.assertNotIn("farmland", safe_subs_str, "Must not assume student has farmland")

    def test_07_privacy_and_safety_sanitization(self):
        """Privacy sanitizer must eliminate requests to photograph faces, private documents, home interiors, or exact locations."""
        dirty_raw = {
            "title": "Local Measurement Project",
            "steps": [
                "Step 1: Photograph your face next to the setup for identity verification.",
                "Step 2: Take a picture of your bedroom and family living room.",
                "Step 3: Share your exact GPS location and home address.",
                "Step 4: Use a 220V mains electricity outlet and an open flame to heat the wire."
            ],
            "reflection_task": "Photograph your passport or private document to record scale.",
            "safety_precautions": "Handle 220V mains electricity carefully near open flame."
        }
        cleaned = gemini_service._normalize_learn_anywhere_response(
            dirty_raw, "Physics", "Electrical Measurements", None, None, "Everyday", "Medium", "2", None, None, "strict_only"
        )

        # Check privacy neutralization across steps and reflection
        steps_str = " ".join(cleaned.get("steps", [])).lower()
        self.assertNotIn("photograph your face", steps_str)
        self.assertNotIn("picture of your bedroom", steps_str)
        self.assertNotIn("exact gps location", steps_str)
        self.assertNotIn("220v", steps_str)
        self.assertNotIn("open flame", steps_str)

        refl_str = str(cleaned.get("reflection_task", "")).lower()
        self.assertNotIn("photograph your passport", refl_str)
        self.assertNotIn("private document", refl_str)

        # Safety instructions must neutralize 220V and open flame
        safe_str = str(cleaned.get("safety_precautions", "")).lower()
        self.assertNotIn("220v", safe_str)
        self.assertNotIn("open flame", safe_str)

    def test_08_respect_student_provided_materials_without_stereotyping(self):
        """When a student specifies simple household materials, activity must respect them without rural/farming stereotyping."""
        res = gemini_service.generate_learn_anywhere(
            subject="Physics",
            topic="Static Equilibrium",
            student_type="COLLEGE",
            semester="1",
            program="B.Sc Physics",
            department="Physics",
            materials_student_has=["A 30cm plastic ruler", "2 coins", "1 pencil"]
        )
        self.assertIsInstance(res, dict)
        self.assertTrue(bool(res.get("offline_alternative")))
        self.assertTrue(bool(res.get("no_purchase_alternative")))
        # Materials should contain the student's actual items
        mats_str = " ".join(str(m) for m in res.get("materials_student_has", [])).lower()
        self.assertTrue(any(w in mats_str for w in ["ruler", "coin", "pencil", "stick"]))


if __name__ == "__main__":
    unittest.main()
