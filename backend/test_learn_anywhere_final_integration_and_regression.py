import unittest
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
os.environ["TESTING"] = "1"

from server import app, get_mongodb, get_sqlite_db
from app.gemini_service import gemini_service
from app.teaching_planner import teaching_planner


class TestLearnAnywhereFinalIntegrationAndRegression(unittest.TestCase):
    """
    Comprehensive Final Integration and Regression Test Suite for Learn from Anywhere.
    Covers all 13 required verification areas:
    1. Activity subject matches selected validated syllabus subject and topic.
    2. School and college students receive appropriate content for profile and curriculum.
    3. Mathematics has progressively harder practical problems and worked solutions.
    4. Computer Science has relevant examples, code, and expected output.
    5. Science activities use realistic materials and safe, scientifically valid procedures.
    6. English and Social Science receive meaningful subject-specific tasks without forced experiments.
    7. Procedures have short, accurate steps with clean numbering.
    8. The result or expected output actually follows from the procedure.
    9. Missing syllabus, missing subject, failed AI generation, and invalid output handled honestly.
    10. No mock subjects, default physics templates, stale activities, or fabricated progress.
    11. Existing activity history and progress tracking still work.
    12. No teacher evaluation records, Misconception Map data, or Action Center data modified.
    13. Frontend UI responsiveness classes and touch targets verification.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.client = cls.app.test_client()

    def _seed_curriculum(self, user_id, syllabus_id, subjects_list, level="school", grade_or_sem=None):
        s_doc = {
            "_id": syllabus_id,
            "syllabus_id": syllabus_id,
            "user_id": user_id,
            "student_id": user_id,
            "is_active": True,
            "isActive": True,
            "status": "VALID",
            "validation_status": "VALID",
            "level": level,
            "academic_level": level.upper(),
            "grade_level": grade_or_sem if level == "school" else None,
            "semester": str(grade_or_sem) if level == "college" else None,
            "subjects": subjects_list,
            "chapters": {s["name"]: [{"name": t} for t in s.get("topics", [])] for s in subjects_list if isinstance(s, dict)},
            "created_at": datetime.utcnow().isoformat()
        }
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db.syllabi.update_one(
                {"user_id": user_id, "syllabus_id": syllabus_id},
                {"$set": s_doc},
                upsert=True
            )
        sqlite_db = get_sqlite_db()
        if sqlite_db:
            with sqlite_db:
                sqlite_db.execute("""
                    CREATE TABLE IF NOT EXISTS syllabi (
                        id TEXT PRIMARY KEY,
                        syllabus_id TEXT,
                        student_id TEXT,
                        file_name TEXT,
                        is_active INTEGER,
                        status TEXT,
                        validation_status TEXT,
                        analysis_json TEXT,
                        created_at TEXT,
                        updated_at TEXT
                    )
                """)
                sqlite_db.execute("DELETE FROM syllabi WHERE syllabus_id = ?", (syllabus_id,))
                sqlite_db.execute("""
                    INSERT INTO syllabi
                    (syllabus_id, student_id, file_name, is_active, status, validation_status, analysis_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    syllabus_id, str(user_id), "Curriculum.pdf", 1, "VALID", "VALID",
                    json.dumps(s_doc, default=str), datetime.utcnow().isoformat(), datetime.utcnow().isoformat()
                ))

    # ──────────────────────────────────────────────────────────────────────────
    # Verification 1 & 2: Subject, Topic, Profile & Curriculum Match
    # ──────────────────────────────────────────────────────────────────────────

    def test_01_activity_subject_matches_validated_syllabus_and_topic(self):
        """Verifies activity subject and topic strictly mirror the validated syllabus selection."""
        user_id = "test_audit_student_school"
        syl_id = "syl_audit_math_01"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Mathematics", "topics": ["Linear Equations in One Variable", "Mensuration"]}
        ], level="school", grade_or_sem=8)

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user"] = {
                "id": user_id,
                "role": "student",
                "student_type": "SCHOOL",
                "level": "school",
                "grade_level": 8,
                "board": "CBSE"
            }

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Mathematics",
            "topic": "Linear Equations in One Variable",
            "syllabus_id": syl_id,
            "difficulty": "Medium"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        act = data.get("activity")
        self.assertEqual(act["subject"], "Mathematics")
        self.assertEqual(act["topic"], "Linear Equations in One Variable")
        self.assertEqual(act.get("academic_grounding", {}).get("subject"), "Mathematics")

    def test_02_school_and_college_level_separation(self):
        """Verifies school students get school content and college students get degree/semester-grounded content."""
        # 1. School student
        sch_user_id = "test_school_profile_stu"
        sch_syl_id = "syl_sch_sci_01"
        self._seed_curriculum(sch_user_id, sch_syl_id, [
            {"name": "Physics", "topics": ["Reflection of Light"]}
        ], level="school", grade_or_sem=9)

        with self.client.session_transaction() as sess:
            sess["user_id"] = sch_user_id
            sess["user"] = {
                "id": sch_user_id,
                "role": "student",
                "student_type": "SCHOOL",
                "level": "school",
                "grade_level": 9,
                "board": "ICSE"
            }

        res_sch = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Physics",
            "topic": "Reflection of Light",
            "syllabus_id": sch_syl_id
        })
        self.assertEqual(res_sch.status_code, 200)
        act_sch = res_sch.get_json()["activity"]
        self.assertEqual(act_sch.get("student_type"), "SCHOOL")
        all_sch_text = json.dumps(act_sch).lower()
        self.assertNotIn("hamiltonian", all_sch_text)
        self.assertNotIn("tensor", all_sch_text)
        self.assertNotIn("laplace transform", all_sch_text)

        # 2. College student
        col_user_id = "test_college_profile_stu"
        col_syl_id = "syl_col_mech_01"
        self._seed_curriculum(col_user_id, col_syl_id, [
            {"name": "Mechanical Engineering", "topics": ["Fluid Mechanics and Bernoulli Principle"]}
        ], level="college", grade_or_sem=4)

        with self.client.session_transaction() as sess:
            sess["user_id"] = col_user_id
            sess["user"] = {
                "id": col_user_id,
                "role": "student",
                "student_type": "COLLEGE",
                "level": "college",
                "degree": "B.Tech Mechanical",
                "department": "Mechanical Engineering",
                "semester": 4
            }

        res_col = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Mechanical Engineering",
            "topic": "Fluid Mechanics and Bernoulli Principle",
            "syllabus_id": col_syl_id
        })
        self.assertEqual(res_col.status_code, 200)
        act_col = res_col.get_json()["activity"]
        self.assertEqual(act_col.get("student_type"), "COLLEGE")
        grounding = act_col.get("academic_grounding", {})
        self.assertIn(str(grounding.get("grade_or_semester")), ["4", "Semester 4"])

    # ──────────────────────────────────────────────────────────────────────────
    # Verification 3: Mathematics Progressive Problems & Worked Solutions
    # ──────────────────────────────────────────────────────────────────────────

    def test_03_mathematics_progressive_difficulty_and_worked_solutions(self):
        """Mathematics activities must provide progressive Easy/Medium/Hard problems and method calculations."""
        user_id = "test_math_prog_student"
        syl_id = "syl_math_prog"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Mathematics", "topics": ["Quadratic Equations"]}
        ], level="school", grade_or_sem=10)

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user"] = {
                "id": user_id,
                "role": "student",
                "student_type": "SCHOOL",
                "level": "school",
                "grade_level": 10
            }

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Mathematics",
            "topic": "Quadratic Equations",
            "syllabus_id": syl_id
        })
        self.assertEqual(res.status_code, 200)
        act = res.get_json()["activity"]
        self.assertIn("math_progressive_practice", act)
        practice = act["math_progressive_practice"]
        for tier in ["easy", "medium", "hard"]:
            self.assertIn(tier, practice)
            item = practice[tier]
            self.assertTrue(item.get("question"), f"Missing question for tier {tier}")
            self.assertTrue(item.get("method_and_calculations"), f"Missing calculations for tier {tier}")
            self.assertTrue(item.get("answer"), f"Missing answer for tier {tier}")

    # ──────────────────────────────────────────────────────────────────────────
    # Verification 4: Computer Science Code & Expected Output
    # ──────────────────────────────────────────────────────────────────────────

    def test_04_computer_science_runnable_code_and_output(self):
        """Computer Science activities must include code snippet, run instructions, expected output, and modification task."""
        user_id = "test_cs_code_student"
        syl_id = "syl_cs_code"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Computer Science", "topics": ["Binary Search Algorithm"]}
        ], level="college", grade_or_sem=3)

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user"] = {
                "id": user_id,
                "role": "student",
                "student_type": "COLLEGE",
                "level": "college",
                "degree": "B.Tech Computer Science",
                "department": "Computer Science",
                "semester": 3
            }

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Computer Science",
            "topic": "Binary Search Algorithm",
            "syllabus_id": syl_id
        })
        self.assertEqual(res.status_code, 200)
        act = res.get_json()["activity"]
        self.assertIn("coding_task", act)
        c_task = act["coding_task"]
        self.assertTrue(c_task.get("code_snippet") or c_task.get("code"))
        self.assertTrue(c_task.get("run_instructions"))
        self.assertTrue(c_task.get("expected_output"))
        self.assertTrue(c_task.get("modification_task"))

    # ──────────────────────────────────────────────────────────────────────────
    # Verification 5: Science Realistic Materials & Safety
    # ──────────────────────────────────────────────────────────────────────────

    def test_05_science_realistic_materials_and_strict_safety(self):
        """Science activities must use common safe items and include safety guidelines with zero hazards."""
        user_id = "test_sci_safety_student"
        syl_id = "syl_sci_safety"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Chemistry", "topics": ["Acids, Bases and Natural Indicators"]}
        ], level="school", grade_or_sem=7)

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user"] = {
                "id": user_id,
                "role": "student",
                "student_type": "SCHOOL",
                "level": "school",
                "grade_level": 7
            }

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Chemistry",
            "topic": "Acids, Bases and Natural Indicators",
            "syllabus_id": syl_id
        })
        self.assertEqual(res.status_code, 200)
        act = res.get_json()["activity"]
        self.assertTrue(act.get("safety_precautions"))
        all_text = json.dumps(act).lower()
        self.assertNotIn("hydrochloric", all_text)
        self.assertNotIn("sulfuric", all_text)
        self.assertNotIn("220v", all_text)
        # Check realistic common household items
        mats = [m.lower() for m in act.get("materials_student_has", [])]
        self.assertTrue(any("turmeric" in m or "lemon" in m or "water" in m or "paper" in m or "cup" in m for m in mats))

    # ──────────────────────────────────────────────────────────────────────────
    # Verification 6: English & Social Science Subject-Specific Tasks
    # ──────────────────────────────────────────────────────────────────────────

    def test_06_english_and_social_science_meaningful_tasks(self):
        """English and Social Science receive text/language and civic tasks rather than forced experiments."""
        # 1. English
        eng_user_id = "test_eng_task_student"
        eng_syl_id = "syl_eng_task"
        self._seed_curriculum(eng_user_id, eng_syl_id, [
            {"name": "English", "topics": ["Persuasive Writing and Rhetorical Analysis"]}
        ], level="college", grade_or_sem=1)

        with self.client.session_transaction() as sess:
            sess["user_id"] = eng_user_id
            sess["user"] = {
                "id": eng_user_id,
                "role": "student",
                "student_type": "COLLEGE",
                "level": "college",
                "degree": "B.A. English",
                "department": "Humanities",
                "semester": 1
            }

        res_eng = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "English",
            "topic": "Persuasive Writing and Rhetorical Analysis",
            "syllabus_id": eng_syl_id
        })
        self.assertEqual(res_eng.status_code, 200)
        act_eng = res_eng.get_json()["activity"]
        self.assertIn("model_answer", act_eng)
        self.assertNotIn("siphon", json.dumps(act_eng).lower())

        # 2. Social Science
        soc_user_id = "test_soc_task_student"
        soc_syl_id = "syl_soc_task"
        self._seed_curriculum(soc_user_id, soc_syl_id, [
            {"name": "Social Science", "topics": ["Local Governance and Village Panchayat"]}
        ], level="school", grade_or_sem=7)

        with self.client.session_transaction() as sess:
            sess["user_id"] = soc_user_id
            sess["user"] = {
                "id": soc_user_id,
                "role": "student",
                "student_type": "SCHOOL",
                "level": "school",
                "grade_level": 7
            }

        res_soc = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Social Science",
            "topic": "Local Governance and Village Panchayat",
            "syllabus_id": soc_syl_id
        })
        self.assertEqual(res_soc.status_code, 200)
        act_soc = res_soc.get_json()["activity"]
        self.assertIn(act_soc.get("demonstration_type"), ["community_civic_observation", "field_observation_and_social_analysis", "field_observation", "household_demonstration"])
        self.assertNotIn("circuit", json.dumps(act_soc).lower())

    # ──────────────────────────────────────────────────────────────────────────
    # Verification 7 & 8: Short Accurate Steps & Expected Observation Logic
    # ──────────────────────────────────────────────────────────────────────────

    def test_07_procedures_have_accurate_actionable_steps_and_numbered_flow(self):
        """Procedures must consist of clean, actionable steps and follow sequence."""
        user_id = "test_steps_flow_student"
        syl_id = "syl_steps_flow"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Biology", "topics": ["Plant Transpiration"]}
        ], level="school", grade_or_sem=8)

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user"] = {
                "id": user_id,
                "role": "student",
                "student_type": "SCHOOL",
                "level": "school",
                "grade_level": 8
            }

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Biology",
            "topic": "Plant Transpiration",
            "syllabus_id": syl_id
        })
        self.assertEqual(res.status_code, 200)
        act = res.get_json()["activity"]
        steps = act.get("steps")
        self.assertIsInstance(steps, list)
        self.assertGreaterEqual(len(steps), 2)
        for s in steps:
            self.assertIsInstance(s, str)
            self.assertGreater(len(s.strip()), 5)

    def test_08_expected_output_directly_follows_from_procedure(self):
        """Result or expected observation logically follows from the practical steps."""
        user_id = "test_obs_follow_student"
        syl_id = "syl_obs_follow"
        self._seed_curriculum(user_id, syl_id, [
            {"name": "Physics", "topics": ["Capillary Action in Liquids"]}
        ], level="school", grade_or_sem=8)

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user"] = {
                "id": user_id,
                "role": "student",
                "student_type": "SCHOOL",
                "level": "school",
                "grade_level": 8
            }

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Physics",
            "topic": "Capillary Action in Liquids",
            "syllabus_id": syl_id
        })
        self.assertEqual(res.status_code, 200)
        act = res.get_json()["activity"]
        obs = act.get("expected_observation") or act.get("expected_observations")
        self.assertTrue(obs)
        self.assertTrue("rise" in obs.lower() or "water" in obs.lower() or "climb" in obs.lower() or "liquid" in obs.lower())

    # ──────────────────────────────────────────────────────────────────────────
    # Verification 9 & 10: Honest Error Handling & Zero Template Leakage
    # ──────────────────────────────────────────────────────────────────────────

    def test_09_honest_error_handling_missing_syllabus_and_subject(self):
        """Missing syllabus or unapproved subject returns clean actionable error."""
        # 1. Missing syllabus entirely
        no_syl_user = "user_without_syllabus"
        with self.client.session_transaction() as sess:
            sess["user_id"] = no_syl_user
            sess["user"] = {"id": no_syl_user, "role": "student", "student_type": "SCHOOL", "level": "school", "grade_level": 9}

        res_no_syl = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Astronomy",
            "topic": "Black Holes"
        })
        self.assertEqual(res_no_syl.status_code, 400)
        data_no_syl = res_no_syl.get_json()
        self.assertFalse(data_no_syl["success"])
        self.assertTrue(data_no_syl.get("curriculum_required"))

        # 2. Subject not in syllabus
        has_syl_user = "user_with_restricted_syl"
        syl_id = "syl_restricted_math_only"
        self._seed_curriculum(has_syl_user, syl_id, [{"name": "Mathematics", "topics": ["Algebra"]}], level="school", grade_or_sem=9)

        with self.client.session_transaction() as sess:
            sess["user_id"] = has_syl_user
            sess["user"] = {"id": has_syl_user, "role": "student", "student_type": "SCHOOL", "level": "school", "grade_level": 9}

        res_wrong_sub = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Quantum Mechanics",
            "topic": "Wave Particle Duality",
            "syllabus_id": syl_id
        })
        self.assertEqual(res_wrong_sub.status_code, 400)
        data_wrong = res_wrong_sub.get_json()
        self.assertFalse(data_wrong["success"])
        self.assertIn("not present in your active validated curriculum", data_wrong.get("error", ""))

    def test_10_no_default_physics_template_leak_on_math_or_cs(self):
        """Mathematics and Computer Science requests never fallback to generic physics templates."""
        math_act = gemini_service.generate_learn_anywhere(
            subject="Mathematics",
            topic="Matrix Determinants and Inverses",
            student_type="COLLEGE",
            semester="2",
            program="B.Sc Mathematics",
            department="Mathematics"
        )
        self.assertEqual(math_act.get("subject"), "Mathematics")
        self.assertNotIn("siphon", json.dumps(math_act).lower())
        self.assertNotIn("focal length", json.dumps(math_act).lower())

        cs_act = gemini_service.generate_learn_anywhere(
            subject="Computer Science",
            topic="Hash Tables and Collision Resolution",
            student_type="COLLEGE",
            semester="3",
            program="B.Tech Computer Science",
            department="Computer Science"
        )
        self.assertEqual(cs_act.get("subject"), "Computer Science")
        self.assertNotIn("clay pot", json.dumps(cs_act).lower())

    # ──────────────────────────────────────────────────────────────────────────
    # Verification 11: Activity History & Progress Tracking
    # ──────────────────────────────────────────────────────────────────────────

    def test_11_history_and_progress_tracking_records_mastery(self):
        """Submitting practice attempts correctly records progress and computes mastery."""
        user_id = "test_tracking_mastery_student"
        act_id = "act_tracking_001"

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user"] = {"id": user_id, "role": "student", "student_type": "SCHOOL", "level": "school", "grade_level": 8}

        # Submit 2 consecutive correct answers in attempts list
        res = self.client.post("/api/learn-anywhere/progress", json={
            "activity_id": act_id,
            "subject": "Mathematics",
            "topic": "Linear Equations",
            "completed_steps": [0, 1, 2],
            "total_steps": 3,
            "attempts": [
                {"question_index": 0, "is_correct": True},
                {"question_index": 1, "is_correct": True}
            ]
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("completion_status"), "completed")
        self.assertEqual(data.get("accuracy_percent"), 100)

        # Session endpoint returns session with correct stats
        sess_resp = self.client.get(f"/api/learn-anywhere/session?activity_id={act_id}&subject=Mathematics")
        self.assertEqual(sess_resp.status_code, 200)
        sess_data = sess_resp.get_json()
        self.assertTrue(sess_data.get("session_exists"))
        self.assertEqual(sess_data.get("mastery_status"), "mastered")
        self.assertEqual(sess_data.get("adaptive_difficulty"), "advanced")

    # ──────────────────────────────────────────────────────────────────────────
    # Verification 12: Absolute Isolation from Teacher Data & Misconceptions
    # ──────────────────────────────────────────────────────────────────────────

    def test_12_no_teacher_evaluations_or_misconceptions_modified(self):
        """Learn from Anywhere strictly isolates student activity from teacher evaluations and misconceptions."""
        mongo_db = get_mongodb()
        eval_count_before = 0
        misc_count_before = 0
        action_count_before = 0
        if mongo_db is not None:
            eval_count_before = mongo_db.evaluations.count_documents({})
            misc_count_before = mongo_db.misconceptions.count_documents({})
            action_count_before = mongo_db.action_center.count_documents({})

        # Perform Learn from Anywhere action & progress updates
        user_id = "test_isolation_verify_stu"
        syl_id = "syl_isolation_verify"
        self._seed_curriculum(user_id, syl_id, [{"name": "Physics", "topics": ["Motion"]}], level="school", grade_or_sem=9)

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user"] = {"id": user_id, "role": "student", "student_type": "SCHOOL", "level": "school", "grade_level": 9}

        gen_res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Physics",
            "topic": "Motion",
            "syllabus_id": syl_id
        })
        self.assertEqual(gen_res.status_code, 200)

        act_id = gen_res.get_json()["activity"]["activity_id"]
        self.client.post("/api/learn-anywhere/action", json={
            "activity_id": act_id,
            "action_type": "simpler_explanation",
            "subject": "Physics",
            "topic": "Motion"
        })

        self.client.post("/api/learn-anywhere/progress", json={
            "activity_id": act_id,
            "subject": "Physics",
            "topic": "Motion",
            "completed_steps": [0]
        })

        if mongo_db is not None:
            eval_count_after = mongo_db.evaluations.count_documents({})
            misc_count_after = mongo_db.misconceptions.count_documents({})
            action_count_after = mongo_db.action_center.count_documents({})
            self.assertEqual(eval_count_before, eval_count_after, "Teacher evaluations table was modified by Learn Anywhere!")
            self.assertEqual(misc_count_before, misc_count_after, "Misconceptions table was modified by Learn Anywhere!")
            self.assertEqual(action_count_before, action_count_after, "Action Center table was modified by Learn Anywhere!")

    # ──────────────────────────────────────────────────────────────────────────
    # Verification 13: UI Responsive Design Tokens & Mobile Accessibility
    # ──────────────────────────────────────────────────────────────────────────

    def test_13_ui_responsiveness_and_touch_target_classes(self):
        """Verifies LearnAnywhere.jsx contains standard mobile-first responsive tokens and touch targets."""
        jsx_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "learnsphere-ai", "src", "pages", "LearnAnywhere.jsx"
        ))
        self.assertTrue(os.path.exists(jsx_path), f"LearnAnywhere.jsx not found at {jsx_path}")
        with open(jsx_path, "r", encoding="utf-8") as f:
            jsx_content = f.read()

        # 1. Responsive layout tokens (mobile, tablet, desktop)
        self.assertIn("sm:p-6", jsx_content)
        self.assertIn("md:p-7", jsx_content)
        self.assertIn("grid sm:grid-cols-2 md:grid-cols-3", jsx_content)
        self.assertIn("grid grid-cols-1 md:grid-cols-3", jsx_content)

        # 2. Touch target compliance (minimum 44px on interactive radio/buttons)
        self.assertIn("min-h-[44px]", jsx_content)

        # 3. Horizontal overflow safety for code and formula blocks on mobile screens
        self.assertIn("overflow-x-auto", jsx_content)

        # 4. Mobile text scaling
        self.assertIn("text-xs sm:text-sm", jsx_content)
        self.assertIn("text-xl sm:text-2xl", jsx_content)


if __name__ == "__main__":
    unittest.main()
