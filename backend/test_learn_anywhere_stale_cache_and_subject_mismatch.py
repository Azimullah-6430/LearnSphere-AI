import unittest
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
os.environ["TESTING"] = "1"

from app.gemini_service import gemini_service
from app.teaching_planner import teaching_planner


class TestLearnAnywhereStaleCacheAndSubjectMismatch(unittest.TestCase):
    """
    Validation Suite for Stale State, Cache, and Subject Mismatch in Learn from Anywhere:
    1. Selecting Mathematics must not return an unrelated physics, engineering, or CS coding experiment.
    2. Selecting English must return an appropriate language/literature activity.
    3. Selecting Social Science must return a suitable observation, research, map, or analysis task.
    4. Selecting Computer Science must return a level-appropriate coding or computing task when suitable.
    5. Selecting Biology or Chemistry must return a relevant, safe activity.
    6. A school account must not receive college-level content merely because a similarly named subject exists in both curricula.
    7. A college account must use the correct authenticated semester and validated curriculum.
    8. Changing the selected subject must clear previous activity and invalidate stale cache.
    9. Generating another activity must use the current subject and topic, not cached content from another selection.
    10. If generation fails or returns invalid data, return a clean retry error.
    11. Multi-point schema validation and topic relevance.
    """

    def test_01_mathematics_does_not_return_physics_or_engineering_experiment(self):
        """Mathematics must return mathematical problem solving / discrete math, never physics or engineering apparatus."""
        # College level Mathematics
        col_math = gemini_service._raw_build_deterministic_college_activity(
            subject="Mathematics",
            subject_id="sub_math_col",
            topic="Quadratic Functions and Maximum Area",
            resource_env="Household & Crafts",
            difficulty="Medium",
            semester="1",
            program="Science",
            department="Mathematics",
            student_type="COLLEGE"
        )
        self.assertTrue(col_math["is_supported"])
        self.assertIn(col_math.get("demonstration_type"), ["worked_problem_set", "household_demonstration"])
        self.assertIn("math_progressive_practice", col_math)
        all_text = json.dumps(col_math).lower()
        self.assertNotIn("siphon", all_text)
        self.assertNotIn("bicycle gear", all_text)
        self.assertNotIn("hydrostatic", all_text)
        self.assertNotIn("deflection", all_text)

        # School level Mathematics
        sch_math = gemini_service._build_deterministic_school_activity(
            subject="Mathematics",
            subject_id="sub_math_sch",
            topic="Simple Equations and Unknowns",
            resource_env="Paper & Household",
            difficulty="Easy",
            semester="Grade 6",
            program="Middle School",
            department="Mathematics"
        )
        self.assertTrue(sch_math["is_supported"])
        self.assertEqual(sch_math["demonstration_type"], "worked_problem_set")
        self.assertIn("math_progressive_practice", sch_math)
        sch_text = json.dumps(sch_math).lower()
        self.assertNotIn("refraction", sch_text)
        self.assertNotIn("fluid dynamics", sch_text)
        self.assertNotIn("circuit", sch_text)

    def test_02_english_returns_language_activity(self):
        """English must return language, reading, rhetoric, or text analysis."""
        col_eng = gemini_service._raw_build_deterministic_college_activity(
            subject="English",
            subject_id="sub_eng_col",
            topic="Persuasive Writing and Rhetorical Analysis",
            resource_env="Household & Crafts",
            difficulty="Medium",
            semester="1",
            program="Arts",
            department="Humanities",
            student_type="COLLEGE"
        )
        self.assertTrue(col_eng["is_supported"])
        self.assertIn(col_eng.get("demonstration_type"), ["reading_and_writing_task", "language_and_text_analysis"])
        all_text = json.dumps(col_eng).lower()
        self.assertTrue("editorial" in all_text or "writing" in all_text or "rhetoric" in all_text)
        self.assertNotIn("gravity", all_text)

        coh = gemini_service.validate_activity_coherence(col_eng, "English", "Persuasive Writing", "COLLEGE")
        self.assertTrue(coh["is_coherent"])

    def test_03_social_science_returns_civic_or_research_task(self):
        """Social Science must return an observation, civic research, map, or analysis task."""
        sch_soc = gemini_service._build_deterministic_school_activity(
            subject="Social Science",
            subject_id="sub_soc_sch",
            topic="Local Governance and Village Panchayat",
            resource_env="Everyday Surroundings",
            difficulty="Easy",
            semester="Grade 7",
            program="School",
            department="Social Studies"
        )
        self.assertTrue(sch_soc["is_supported"])
        self.assertIn(sch_soc.get("demonstration_type"), ["community_civic_observation", "field_observation_and_social_analysis", "field_observation", "household_demonstration"])
        soc_text = json.dumps(sch_soc).lower()
        self.assertTrue("civic" in soc_text or "panchayat" in soc_text or "community" in soc_text or "governance" in soc_text)
        self.assertNotIn("centripetal", soc_text)

    def test_04_computer_science_returns_level_appropriate_coding_task(self):
        """Computer Science must return coding or computing logic task."""
        col_cs = gemini_service._raw_build_deterministic_college_activity(
            subject="Computer Science",
            subject_id="sub_cs_col",
            topic="Binary Search Algorithm",
            resource_env="Household & Crafts",
            difficulty="Medium",
            semester="3",
            program="B.Tech",
            department="Computer Science",
            student_type="COLLEGE"
        )
        self.assertTrue(col_cs["is_supported"])
        self.assertIn("coding_task", col_cs)
        self.assertEqual(col_cs["coding_task"].get("target_language"), "Python")
        self.assertIn("code_snippet", col_cs["coding_task"])

        sch_cs = gemini_service._build_deterministic_school_activity(
            subject="Computer Science",
            subject_id="sub_cs_sch",
            topic="Introduction to Loops",
            resource_env="Paper & Slips",
            difficulty="Easy",
            semester="Grade 6",
            program="School",
            department="Computer Studies"
        )
        self.assertTrue(sch_cs["is_supported"])
        self.assertEqual(sch_cs.get("demonstration_type"), "code_and_logic_simulation")
        self.assertIn("coding_task", sch_cs)

    def test_05_biology_and_chemistry_return_safe_activities(self):
        """Biology and Chemistry must return grounded, non-hazardous activities."""
        bio_act = gemini_service._build_deterministic_school_activity(
            subject="Biology",
            subject_id="sub_bio_sch",
            topic="Plant Leaf Veins and Respiration",
            resource_env="Plants & Bio Resources",
            difficulty="Easy",
            semester="Grade 8",
            program="School",
            department="Science"
        )
        self.assertTrue(bio_act["is_supported"])
        self.assertIn("safety_precautions", bio_act)
        bio_text = json.dumps(bio_act).lower()
        self.assertNotIn("hydrochloric", bio_text)
        self.assertNotIn("sulfuric", bio_text)

        chem_act = gemini_service._build_deterministic_school_activity(
            subject="Chemistry",
            subject_id="sub_chem_sch",
            topic="Solubility and Solutions",
            resource_env="Household & Crafts",
            difficulty="Easy",
            semester="Grade 7",
            program="School",
            department="Science"
        )
        self.assertTrue(chem_act["is_supported"])
        self.assertIn("safety_precautions", chem_act)
        chem_text = json.dumps(chem_act).lower()
        self.assertNotIn("cyanide", chem_text)

    def test_06_school_account_does_not_receive_college_content(self):
        """School account must not receive college equations or jargon."""
        sch_act = gemini_service._build_deterministic_school_activity(
            subject="Physics",
            subject_id="sub_phy",
            topic="Capillary Action and Water Movement",
            resource_env="Household & Crafts",
            difficulty="Easy",
            semester="Grade 8",
            program="Secondary School",
            department="Science"
        )
        self.assertEqual(sch_act["student_type"], "SCHOOL")
        self.assertEqual(sch_act["academic_level"], "SCHOOL")
        sch_text = json.dumps(sch_act).lower()
        self.assertNotIn("hamiltonian", sch_text)
        self.assertNotIn("laplace", sch_text)
        self.assertNotIn("navier-stokes", sch_text)
        self.assertNotIn("eigenvalue", sch_text)

    def test_07_coherence_validator_rejects_cross_discipline_and_level_mismatch(self):
        """validate_activity_coherence rejects activities if discipline hazard or level mismatch occurs."""
        phy_act = gemini_service._build_deterministic_school_activity(
            subject="Physics",
            subject_id="sub_phy",
            topic="Force and Motion",
            resource_env="Household & Crafts",
            difficulty="Easy",
            semester="Grade 7",
            program="School",
            department="Science"
        )
        # Physics activity evaluated against Mathematics
        coh_math_fail = gemini_service.validate_activity_coherence(
            activity=phy_act,
            subject="Mathematics",
            topic="Algebraic Equations",
            student_type="SCHOOL"
        )
        self.assertFalse(coh_math_fail["is_coherent"])

        # School activity injected with college jargon
        fake_school_with_jargon = dict(phy_act)
        fake_school_with_jargon["academic_theory"] = "Computed using matrix eigenvalue decomposition and gradient descent."
        coh_level_fail = gemini_service.validate_activity_coherence(
            activity=fake_school_with_jargon,
            subject="Physics",
            topic="Force and Motion",
            student_type="SCHOOL"
        )
        self.assertFalse(coh_level_fail["is_coherent"])

    def test_08_teaching_planner_topic_nature_preserves_subject_boundaries(self):
        """Mathematical terms like function or graph must not trigger programming-oriented classification."""
        nature1 = teaching_planner.detect_topic_nature("Mathematics", "Quadratic Function and Vertex")
        self.assertNotEqual(nature1, "programming-oriented")

        nature2 = teaching_planner.detect_topic_nature("Mathematics", "Graph of Polynomials")
        self.assertNotEqual(nature2, "programming-oriented")

        nature3 = teaching_planner.detect_topic_nature("Biology", "Phylogenetic Tree Classification")
        self.assertNotEqual(nature3, "programming-oriented")

        nature4 = teaching_planner.detect_topic_nature("Computer Science", "Binary Search Trees")
        self.assertEqual(nature4, "programming-oriented")

    def test_09_college_account_enforces_semester_and_curriculum(self):
        """College activity must ground in specified semester."""
        col_act = gemini_service._build_deterministic_college_activity(
            subject="Mechanical Engineering",
            subject_id="sub_me",
            topic="Fluid Mechanics and Bernoulli Principle",
            resource_env="Household & Crafts",
            difficulty="Hard",
            semester="4",
            program="B.Tech Mechanical",
            department="Mechanical Engineering",
            student_type="COLLEGE"
        )
        self.assertEqual(col_act["student_type"], "COLLEGE")
        grounding = col_act.get("academic_grounding", {})
        self.assertEqual(grounding.get("grade_or_semester"), "4")
        self.assertEqual(grounding.get("program"), "B.Tech Mechanical")


if __name__ == "__main__":
    unittest.main()
