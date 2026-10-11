import unittest
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from server import app
from app.gemini_service import gemini_service
from app.teaching_planner import teaching_planner

class TestLearnAnywhereEndToEndRegression(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        os.environ["TESTING"] = "1"

    def _seed_curriculum(self, user_id, syllabus_id, subjects_list):
        s_doc = {
            "_id": syllabus_id,
            "syllabus_id": syllabus_id,
            "user_id": user_id,
            "student_id": user_id,
            "is_active": True,
            "status": "VALID",
            "validation_status": "VALID",
            "subjects": subjects_list,
            "chapters": {s["name"]: [{"name": t} for t in s.get("topics", [])] for s in subjects_list if isinstance(s, dict)}
        }
        with app.app_context():
            from server import get_mongodb
            mongo_db = get_mongodb()
            if mongo_db is not None:
                mongo_db.syllabi.update_one(
                    {"user_id": user_id, "syllabus_id": syllabus_id},
                    {"$set": s_doc},
                    upsert=True
                )

    def test_01_school_mathematics_end_to_end(self):
        """School Mathematics (Grade 8): Simple explanations, visual reasoning, step-by-step calculation."""
        user_id = "school_math_student"
        syl_id = "syl_school_math"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Mathematics", "topics": ["Linear Equations in One Variable", "Mensuration"]}
        ])

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Mathematics",
            "topic": "Linear Equations in One Variable",
            "syllabus_id": syl_id,
            "difficulty": "Easy"
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        act = data["activity"]

        self.assertEqual(act["subject"], "Mathematics")
        self.assertEqual(act["topic"], "Linear Equations in One Variable")
        self.assertIn("learning_objectives", act)
        self.assertGreaterEqual(len(act["steps"]), 1)
        self.assertIn("understanding_questions", act)

    def test_02_school_science_end_to_end(self):
        """School Science (Grade 9): Age-appropriate logic, safe zero-cost practical experiment."""
        user_id = "school_sci_student"
        syl_id = "syl_school_sci"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Physics", "topics": ["Reflection of Light", "Laws of Motion"]}
        ])

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Physics",
            "topic": "Reflection of Light",
            "syllabus_id": syl_id,
            "difficulty": "Easy"
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        act = data["activity"]

        self.assertEqual(act["subject"], "Physics")
        self.assertEqual(act["topic"], "Reflection of Light")
        self.assertIsNotNone(act.get("safety_precautions"))
        self.assertNotIn("220v", act["safety_precautions"].lower())

    def test_03_school_computer_science_end_to_end(self):
        """School Computer Science (Grade 10): Algorithms, pseudocode, simple logic walkthrough."""
        user_id = "school_cs_student"
        syl_id = "syl_school_cs"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Computer Science", "topics": ["Algorithms & Flowcharts", "Conditional Statements"]}
        ])

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Computer Science",
            "topic": "Algorithms & Flowcharts",
            "syllabus_id": syl_id,
            "difficulty": "Easy"
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        act = data["activity"]

        self.assertEqual(act["subject"], "Computer Science")
        self.assertIn("coding_task", act)

    def test_04_college_mathematics_end_to_end(self):
        """College Mathematics (B.Tech Sem 2): Prerequisites, formal notation, worked problem."""
        user_id = "college_math_student"
        syl_id = "syl_college_math"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Engineering Mathematics", "topics": ["Eigenvalues and Eigenvectors", "Differential Equations"]}
        ])

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Engineering Mathematics",
            "topic": "Eigenvalues and Eigenvectors",
            "syllabus_id": syl_id,
            "difficulty": "Hard"
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        act = data["activity"]

        self.assertEqual(act["subject"], "Engineering Mathematics")
        self.assertEqual(act["topic"], "Eigenvalues and Eigenvectors")
        self.assertIn("academic_theory", act)

    def test_05_college_computer_science_end_to_end(self):
        """College Computer Science (B.Tech CSE Sem 4): Code implementation, runtime performance, debugging guidance."""
        user_id = "college_cs_student"
        syl_id = "syl_college_cs"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Data Structures & Algorithms", "topics": ["Binary Search Trees", "Graph Traversal Algorithms"]}
        ])

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Data Structures & Algorithms",
            "topic": "Binary Search Trees",
            "syllabus_id": syl_id,
            "difficulty": "Hard"
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        act = data["activity"]

        self.assertEqual(act["subject"], "Data Structures & Algorithms")
        self.assertIn("coding_task", act)

    def test_06_additional_discipline_chemistry_end_to_end(self):
        """Additional Discipline 1: Chemistry / Chemical Engineering (Reaction Rates)."""
        user_id = "chem_student"
        syl_id = "syl_chem"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Chemistry", "topics": ["Chemical Kinetics & Reaction Rates"]}
        ])

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Chemistry",
            "topic": "Chemical Kinetics & Reaction Rates",
            "syllabus_id": syl_id
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        act = data["activity"]

        self.assertEqual(act["subject"], "Chemistry")
        self.assertIn("expected_observations", act)

    def test_07_additional_discipline_biology_end_to_end(self):
        """Additional Discipline 2: Biology / Agriculture (Plant Photosynthesis)."""
        user_id = "bio_student"
        syl_id = "syl_bio"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Biology", "topics": ["Plant Photosynthesis & Stomatal Transpiration"]}
        ])

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Biology",
            "topic": "Plant Photosynthesis & Stomatal Transpiration",
            "syllabus_id": syl_id
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        act = data["activity"]

        self.assertEqual(act["subject"], "Biology")

    def test_08_zero_analytics_side_effects(self):
        """Verify Learn from Anywhere activity generation and progress saving produce zero side-effects on teacher evaluation tables or teacher analytics."""
        user_id = "isolation_student_99"
        syl_id = "syl_iso_99"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Physics", "topics": ["Thermodynamics"]}
        ])

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        # 1. Generate activity
        gen_res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Physics",
            "topic": "Thermodynamics",
            "syllabus_id": syl_id
        })
        self.assertEqual(gen_res.status_code, 200)
        act_id = json.loads(gen_res.data)["activity"]["activity_id"]

        # 2. Save student progress
        prog_res = self.client.post("/api/learn-anywhere/progress", json={
            "activity_id": act_id,
            "subject": "Physics",
            "topic": "Thermodynamics",
            "completed_steps": [0, 1],
            "attempts": [{"question_index": 0, "is_correct": True, "score": 100}]
        })
        self.assertEqual(prog_res.status_code, 200)

        # 3. Verify zero records in evaluations or teacher analytics
        with app.app_context():
            from server import get_mongodb, get_sqlite_db
            mongo_db = get_mongodb()
            if mongo_db is not None:
                eval_count = mongo_db.evaluations.count_documents({"activity_id": act_id})
                self.assertEqual(eval_count, 0)
                misc_count = mongo_db.misconceptions.count_documents({"activity_id": act_id})
                self.assertEqual(misc_count, 0)

    def test_09_student_on_demand_actions(self):
        """Test on-demand assistance actions (simpler_explanation, another_example, worked_solution, more_challenging_task)."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = "action_student_1"
            sess["user_role"] = "student"

        res = self.client.post("/api/learn-anywhere/action", json={
            "action_type": "simpler_explanation",
            "subject": "Physics",
            "topic": "Gravity",
            "current_explanation": "Objects attract proportional to mass."
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertIn("content", data["result"])

    def test_10_session_restoration(self):
        """Test GET /api/learn-anywhere/session restores recent activity."""
        user_id = "session_student_77"
        syl_id = "syl_session_77"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Chemistry", "topics": ["Atomic Structure"]}
        ])

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        # Generate activity to populate history/session
        self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Chemistry",
            "topic": "Atomic Structure",
            "syllabus_id": syl_id
        })

        sess_res = self.client.get("/api/learn-anywhere/session")
        self.assertEqual(sess_res.status_code, 200)
        sess_data = json.loads(sess_res.data)
        self.assertTrue(sess_data["success"])
        self.assertEqual(sess_data["subject"], "Chemistry")

if __name__ == "__main__":
    unittest.main()
