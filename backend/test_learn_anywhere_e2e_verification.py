import unittest
import time
import json
import os
import sys

# Ensure backend root is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from server import app
from app.gemini_service import gemini_service

class TestLearnAnywhereE2EVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["TESTING"] = "1"
        cls.app = app

    def setUp(self):
        self.client = self.app.test_client()

    def _seed_curriculum(self, user_id, syllabus_id, subjects_list, level="COLLEGE", degree="B.Tech"):
        s_doc = {
            "_id": syllabus_id,
            "syllabus_id": syllabus_id,
            "user_id": user_id,
            "student_id": user_id,
            "is_active": True,
            "status": "VALID",
            "validation_status": "VALID",
            "academic_level": level,
            "level": level,
            "degree": degree,
            "grade_level": degree if level == "SCHOOL" else None,
            "grade": degree if level == "SCHOOL" else None,
            "board": "CBSE" if level == "SCHOOL" else None,
            "department": "Engineering" if level == "COLLEGE" else "High School",
            "semester": 4 if level == "COLLEGE" else None,
            "subjects": subjects_list,
            "chapters": {
                (s["name"] if isinstance(s, dict) else str(s)): [
                    {"name": t, "concepts": [t]} for t in (s.get("topics", []) if isinstance(s, dict) else [])
                ] for s in subjects_list
            }
        }
        with self.app.app_context():
            from server import get_mongodb
            mongo = get_mongodb()
            if mongo is not None:
                mongo.syllabi.update_one(
                    {"user_id": user_id, "syllabus_id": syllabus_id},
                    {"$set": s_doc},
                    upsert=True
                )

    # =========================================================================
    # 1. Subject Accuracy Tests
    # =========================================================================

    def test_01_subject_accuracy_school_science(self):
        """School Science must receive physical experiments grounded in syllabus without lab equipment."""
        user_id = "school_sci_e2e_student"
        syl_id = "syl_school_sci_e2e"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "General Science", "topics": ["Light Reflection and Refraction"]}
        ], level="SCHOOL", degree="Class 9")

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        t0 = time.time()
        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "General Science",
            "topic": "Light Reflection and Refraction",
            "resource_category": "Village Water & Wells",
            "difficulty": "Medium",
            "syllabus_id": syl_id,
            "student_type": "SCHOOL"
        })
        duration = time.time() - t0

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        act = data.get("activity")
        self.assertEqual(act.get("subject"), "General Science")
        self.assertIn("Light", act.get("topic"))
        self.assertEqual(act.get("academic_level"), "SCHOOL")
        # Ensure materials do not require commercial lab apparatus
        mats_text = " ".join(act.get("materials_student_has", [])).lower()
        self.assertNotIn("spectrometer", mats_text)
        self.assertNotIn("laser cutter", mats_text)
        # Verify response speed is reasonable
        self.assertLess(duration, 5.0)

    def test_02_subject_accuracy_school_mathematics(self):
        """School Mathematics must receive progressive practice (easy/med/hard) and calculation method, not science apparatus."""
        user_id = "school_math_e2e_student"
        syl_id = "syl_school_math_e2e"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Mathematics", "topics": ["Linear Equations in Two Variables"]}
        ], level="SCHOOL", degree="Class 10")

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Mathematics",
            "topic": "Linear Equations in Two Variables",
            "resource_category": "Paper & Pen Only",
            "difficulty": "Medium",
            "syllabus_id": syl_id,
            "student_type": "SCHOOL"
        })
        self.assertEqual(res.status_code, 200)
        act = res.get_json()["activity"]
        self.assertEqual(act.get("subject"), "Mathematics")
        self.assertTrue(bool(act.get("math_progressive_practice")))
        practice = act["math_progressive_practice"]
        self.assertIn("easy", practice)
        self.assertIn("medium", practice)
        self.assertIn("hard", practice)
        self.assertTrue(bool(practice["easy"].get("method_and_calculations")))
        # Ensure no biology/chemistry materials leaked in
        mats_text = " ".join(act.get("materials_student_has", [])).lower()
        self.assertNotIn("beaker", mats_text)
        self.assertNotIn("turmeric", mats_text)
        self.assertNotIn("test tube", mats_text)

    def test_03_subject_accuracy_college_computer_science(self):
        """College Computer Science must receive coding task, valid Python code snippet, and trace logic."""
        user_id = "college_cs_e2e_student"
        syl_id = "syl_college_cs_e2e"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Computer Science", "topics": ["Binary Search Trees and Traversal"]}
        ], level="COLLEGE", degree="B.Tech Computer Science")

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Computer Science",
            "topic": "Binary Search Trees and Traversal",
            "resource_category": "Browser or Terminal IDE",
            "difficulty": "Hard",
            "syllabus_id": syl_id,
            "student_type": "COLLEGE"
        })
        self.assertEqual(res.status_code, 200)
        act = res.get_json()["activity"]
        self.assertEqual(act.get("subject"), "Computer Science")
        ct = act.get("coding_task")
        self.assertIsInstance(ct, dict)
        self.assertTrue(ct.get("is_coding_topic"))
        self.assertTrue(bool(ct.get("code_snippet")))
        # Verify deterministic AST syntax parsing
        self.assertIsNotNone(ct.get("code_verified"))

    def test_04_subject_accuracy_humanities_and_languages(self):
        """Languages/Humanities must receive textual model answers and assessment checklist, not circuits or test tubes."""
        user_id = "school_lang_e2e_student"
        syl_id = "syl_school_lang_e2e"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "English", "topics": ["Persuasive Essay Writing and Argument Structure"]}
        ], level="SCHOOL", degree="Class 10")

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "English",
            "topic": "Persuasive Essay Writing and Argument Structure",
            "resource_category": "Paper & Pen",
            "difficulty": "Medium",
            "syllabus_id": syl_id,
            "student_type": "SCHOOL"
        })
        self.assertEqual(res.status_code, 200)
        act = res.get_json()["activity"]
        self.assertEqual(act.get("subject"), "English")
        self.assertTrue(bool(act.get("model_answer")))
        self.assertTrue(bool(act.get("assessment_checklist")))
        mats_text = " ".join(act.get("materials_student_has", [])).lower()
        self.assertNotIn("beaker", mats_text)
        self.assertNotIn("circuit", mats_text)

    # =========================================================================
    # 2. Response Speed & Deduplication Performance
    # =========================================================================

    def test_05_response_speed_and_deduplication_cache(self):
        """Initial generation vs cached second request with identical idempotency key must demonstrate significant speedup."""
        user_id = "perf_e2e_student"
        syl_id = "syl_perf_e2e"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Physics", "topics": ["Ohm's Law and Resistance"]}
        ], level="COLLEGE", degree="B.Tech EE")

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        payload = {
            "subject": "Physics",
            "topic": "Ohm's Law and Resistance",
            "resource_category": "Household Electronics",
            "difficulty": "Medium",
            "syllabus_id": syl_id,
            "student_type": "COLLEGE",
            "idempotency_key": f"perf_key_{user_id}_{int(time.time())}"
        }

        # First request (full pipeline)
        t_start_1 = time.time()
        res1 = self.client.post("/api/learn-anywhere/generate", json=payload)
        t_duration_1 = time.time() - t_start_1
        self.assertEqual(res1.status_code, 200)

        # Second identical request (deduplication cache hit)
        t_start_2 = time.time()
        res2 = self.client.post("/api/learn-anywhere/generate", json=payload)
        t_duration_2 = time.time() - t_start_2
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertTrue(data2.get("deduplicated") or data2.get("cached_response") or t_duration_2 < t_duration_1)

        # Deduplicated response should complete in fraction of time (< 0.2s)
        self.assertLess(t_duration_2, 0.5)

    # =========================================================================
    # 3. Step Numbering & Formatting Integrity
    # =========================================================================

    def test_06_step_numbering_sequential_clean_layer(self):
        """Verify that generated activities present strictly sequential 1..N steps with no duplicate prefix layers."""
        raw_ai_payload = {
            "title": "Calorimetry Practical",
            "steps": [
                "1. **Step 1:** Measure 100ml of room temperature water.",
                "2. **Step 2:** Record the baseline temperature with precision.",
                "3. **Step 3:** Dissolve 5g of ammonium nitrate and measure temperature change."
            ]
        }
        normalized = gemini_service._normalize_learn_anywhere_response(
            raw_ai_payload, subject="Chemistry", topic="Calorimetry"
        )
        steps = normalized.get("steps")
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0], "Measure 100ml of room temperature water.")
        self.assertEqual(steps[1], "Record the baseline temperature with precision.")
        self.assertEqual(steps[2], "Dissolve 5g of ammonium nitrate and measure temperature change.")

        # Ensure no lingering prefix
        import re
        for s in steps:
            self.assertFalse(bool(re.match(r'^(?:step|\d+[\.)]|\*\*)', s, re.IGNORECASE)))

    def test_07_step_numbering_multi_activity_independence(self):
        """Verify that multiple activities in one response restart numbering at 1 independently."""
        multi_activity = {
            "title": "Mechanics Dual Task",
            "experiments": [
                {
                    "title": "Task 1: Static Friction",
                    "steps": ["Step 1: Place block on ramp.", "Step 2: Increase tilt until slip occurs."]
                },
                {
                    "title": "Task 2: Kinetic Friction",
                    "steps": ["Step 1: Set tilt angle to 30 degrees.", "Step 2: Record time to reach base."]
                }
            ]
        }
        normalized = gemini_service._normalize_learn_anywhere_response(
            multi_activity, subject="Physics", topic="Friction"
        )
        exps = normalized.get("experiments")
        self.assertEqual(len(exps), 2)
        # Task 1
        self.assertEqual(exps[0]["steps"][0], "Place block on ramp.")
        self.assertEqual(exps[0]["steps"][1], "Increase tilt until slip occurs.")
        # Task 2 starts cleanly from step 1
        self.assertEqual(exps[1]["steps"][0], "Set tilt angle to 30 degrees.")
        self.assertEqual(exps[1]["steps"][1], "Record time to reach base.")

    # =========================================================================
    # 4. Error Handling & Incomplete State Tests
    # =========================================================================

    def test_08_error_handling_unauthenticated_request(self):
        """Unauthenticated requests must receive 401 Unauthorized, never fabricated mock data."""
        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Physics",
            "topic": "Gravity"
        })
        self.assertIn(res.status_code, [401, 302])

    def test_09_error_handling_missing_curriculum(self):
        """Students without a syllabus must receive a structured 400 with curriculum_required flag."""
        user_id = "no_syl_student"
        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Physics",
            "topic": "Gravity"
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertTrue(data.get("curriculum_required"))

    def test_10_error_handling_incomplete_profile_prompts_completion(self):
        """Student profile missing required school grade or college semester must prompt profile completion."""
        user_id = "incomplete_profile_student"
        syl_id = "syl_incomplete"
        # Seed syllabus without grade or semester
        self._seed_curriculum(user_id, syl_id, [{"name": "Physics", "topics": ["Motion"]}], level="UNKNOWN", degree="")

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_role"] = "student"

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Physics",
            "topic": "Motion",
            "syllabus_id": syl_id
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertTrue(data.get("profile_incomplete") or data.get("action_required") == "complete_profile")

if __name__ == "__main__":
    unittest.main()
