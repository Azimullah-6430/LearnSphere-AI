import unittest
import json
import os
import sys

# Ensure backend root is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.gemini_service import gemini_service

class TestLearnAnywhereAIEngine(unittest.TestCase):
    def test_01_schema_completeness_16_points(self):
        """Verify the AI engine output contains all 16 required structured sections."""
        res = gemini_service.generate_learn_anywhere(
            subject="Physics",
            subject_id="sub_phy_101",
            topic="Capillarity and Surface Tension",
            unit="Fluid Dynamics",
            curriculum_reference="VTU Syllabus ME401",
            resource_environment="Farmland & Soil",
            difficulty="Medium",
            semester="4",
            program="B.Tech Mechanical",
            department="Mechanical Engineering",
            custom_materials="Clay pot, well water, cotton strip"
        )

        self.assertIsInstance(res, dict)
        
        # 1. Activity Title
        self.assertTrue(bool(res.get("activity_title") or res.get("title")))

        # 2. Academic Grounding
        grounding = res.get("academic_grounding")
        self.assertIsInstance(grounding, dict)
        self.assertEqual(grounding.get("subject"), "Physics")
        self.assertIn("Capillarity", grounding.get("topic"))
        self.assertTrue(bool(grounding.get("grade_or_semester")))

        # 3. Learning Objectives
        self.assertIsInstance(res.get("learning_objectives"), list)
        self.assertTrue(len(res["learning_objectives"]) >= 1)

        # 4. Real-world Concept
        self.assertTrue(bool(res.get("real_world_concept")))

        # 5. Materials Student Has
        self.assertIsInstance(res.get("materials_student_has"), list)
        self.assertTrue(len(res["materials_student_has"]) >= 1)

        # 6. Safe Substitutions & No Purchase Alternative
        self.assertIsInstance(res.get("safe_substitutions"), list)
        self.assertTrue(bool(res.get("no_purchase_alternative")))

        # 7. Step-by-Step Instructions
        self.assertIsInstance(res.get("steps"), list)
        self.assertTrue(len(res["steps"]) >= 3)

        # 8. Simple Explanation
        self.assertTrue(bool(res.get("simple_explanation")))

        # 9. Academic Theory & Equations
        self.assertTrue(bool(res.get("academic_theory")))

        # 10. Everyday Applications
        self.assertTrue(bool(res.get("everyday_applications")))

        # 11. Expected Observations
        self.assertTrue(bool(res.get("expected_observations")))

        # 12. Limitations & Misconceptions
        self.assertTrue(bool(res.get("limitations_and_misconceptions")))

        # 13. Safety Precautions
        self.assertTrue(bool(res.get("safety_precautions")))

        # 14. Understanding Questions (3-5 items with question, answer, explanation)
        questions = res.get("understanding_questions")
        self.assertIsInstance(questions, list)
        self.assertTrue(3 <= len(questions) <= 5)
        for q in questions:
            self.assertIn("question", q)
            self.assertIn("answer", q)
            self.assertIn("explanation", q)

        # 15. Reflection Task
        self.assertTrue(bool(res.get("reflection_task")))

        # 16. Follow-up Practice
        self.assertTrue(bool(res.get("follow_up_practice")))

    def test_02_safety_sanitization_no_hazardous_recommendations(self):
        """Ensure no hazardous chemicals, high voltages, or open flames are recommended."""
        res = gemini_service.generate_learn_anywhere(
            subject="Chemistry",
            topic="Acids and Bases",
            custom_materials="Turmeric, lemon juice, wood ash"
        )

        all_text = json.dumps(res).lower()
        forbidden_hazards = ["hydrochloric acid", "hcl", "nitric acid", "mains 220v", "high voltage", "ignite gasoline", "kerosene fire"]
        for hazard in forbidden_hazards:
            self.assertNotIn(hazard, all_text)

        self.assertTrue(bool(res.get("safety_precautions")))

    def test_03_multimodal_image_payload_handling(self):
        """Ensure image_data (data URL / base64) is correctly processed without crashing."""
        dummy_b64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
        res = gemini_service.generate_learn_anywhere(
            subject="Biology",
            topic="Photosynthesis and Stomata",
            custom_materials="Hibiscus leaves, sunlight, glass bowl",
            image_data=dummy_b64
        )

        self.assertIsInstance(res, dict)
        self.assertTrue(bool(res.get("title")))
        self.assertTrue(len(res.get("steps", [])) > 0)

    def test_04_constraint_mode_enforcement(self):
        """Strict constraint mode enforces only student materials."""
        res = gemini_service.generate_learn_anywhere(
            subject="Physics",
            topic="Lever Mechanics",
            custom_materials="Wooden stick, 2 stones, rope",
            constraint_mode="strict_only"
        )

        self.assertEqual(res.get("constraint_mode"), "strict_only")
        self.assertTrue(len(res.get("materials_student_has", [])) > 0)

    def test_05_mathematics_and_pebble_geometry(self):
        """Test mathematics learning approach using everyday objects, shadow geometry, and pebble series."""
        res = gemini_service._build_deterministic_learn_anywhere(
            subject="Mathematics",
            subject_id="MATH101",
            topic="Trigonometric Heights & Triangular Series",
            resource_env="Sunlight & Shadows",
            difficulty="Medium",
            semester="2",
            program="B.Sc Mathematics",
            department="Mathematics"
        )
        self.assertIn("Shadow Trigonometry", res["title"])
        self.assertTrue("triangles" in res["academic_theory"].lower() or "thales" in res["academic_theory"].lower())
        self.assertIn("pebbles", json.dumps(res["materials_student_has"]).lower())
        self.assertTrue(len(res["understanding_questions"]) >= 3)

    def test_06_biology_and_plant_transpiration(self):
        """Test biology learning approach using non-invasive plant and leaf observations."""
        res = gemini_service._build_deterministic_learn_anywhere(
            subject="Biology",
            subject_id="BIO102",
            topic="Plant Transpiration and Stomatal Regulation",
            resource_env="Plants & Bio Resources",
            difficulty="Easy",
            semester="1",
            program="B.Sc Botany",
            department="Life Sciences"
        )
        self.assertEqual(res["demonstration_type"], "outdoor_observation")
        self.assertIn("Transpiration", res["title"])
        self.assertIn("stomata", res["simple_explanation"].lower())
        self.assertIn("Fick", res["academic_theory"])

    def test_07_environmental_science_and_terracotta_cooling(self):
        """Test environmental science approach covering soil runoff and zero-electricity terracotta cooling."""
        res = gemini_service._build_deterministic_learn_anywhere(
            subject="Environmental Science",
            subject_id="ENV201",
            topic="Watershed Conservation & Evaporative Cooling",
            resource_env="Farmland & Soil",
            difficulty="Medium",
            semester="3",
            program="Civil Engineering",
            department="Environmental Studies"
        )
        self.assertIn("Soil Runoff", res["title"])
        self.assertIn("RUSLE", res["academic_theory"])
        self.assertIn("latent heat", res["academic_theory"].lower())

    def test_08_engineering_and_siphon_mechanisms(self):
        """Test engineering approach using bicycle gear ratios and siphon fluidics."""
        res = gemini_service._build_deterministic_learn_anywhere(
            subject="Mechanical Engineering",
            subject_id="ME301",
            topic="Bicycle Gear Ratios & Siphon Flow",
            resource_env="Bicycle & Simple Tools",
            difficulty="Hard",
            semester="5",
            program="B.Tech Mechanical",
            department="Mechanical Engineering"
        )
        self.assertIn("Mechanical Advantage", res["title"])
        self.assertIn("Bernoulli", res["academic_theory"])
        self.assertIn("Gear ratio", res["academic_theory"])

    def test_09_abstract_theoretical_thought_experiment_boundaries(self):
        """Verify abstract/non-demonstrable concepts (quantum/nuclear/relativity) use thought experiments with clear feasibility boundaries."""
        res = gemini_service._build_deterministic_learn_anywhere(
            subject="Modern Physics",
            subject_id="PHY401",
            topic="Quantum Wave-Particle Duality and Superposition",
            resource_env="Sunlight & Shadows",
            difficulty="Hard",
            semester="6",
            program="B.Sc Physics",
            department="Physics"
        )
        self.assertEqual(res["demonstration_type"], "thought_experiment_and_analog")
        self.assertIn("Thought Experiment", res["title"])
        self.assertIn("FEASIBILITY LIMITATION", res["limitations_and_misconceptions"])
        self.assertIn("de Broglie", res["academic_theory"])

    def test_10_multilingual_and_difficulty_options(self):
        """Ensure preferred language and difficulty choices are passed without mutating curriculum."""
        res = gemini_service.generate_learn_anywhere(
            subject="Chemistry",
            topic="Natural Indicators",
            difficulty="Easy",
            preferred_language="Hindi",
            custom_materials="Haldi, Nimbu, Paani"
        )
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("academic_grounding", {}).get("subject"), "Chemistry")
        self.assertTrue(bool(res.get("title")))


if __name__ == "__main__":
    unittest.main()
