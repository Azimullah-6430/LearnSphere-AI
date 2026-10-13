import unittest
import json
import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Enable test environment fallback
os.environ["TESTING"] = "1"

from server import app, get_mongodb
from app.gemini_service import gemini_service


class TestLearnAnywhereStudentLevelAdaptation(unittest.TestCase):
    """
    Validates student-level adaptation inside Learn from Anywhere:
    - Profile grounding (School vs College classification)
    - Incomplete profile enforcement (no blind guessing or defaulting)
    - School pedagogical rules (simple language, 1 concept, glossary of unfamiliar words, small numbers, no college equations)
    - College pedagogical rules (semester grounding, realistic technical examples, formal calculations, assumptions & reasoning)
    - Switching accounts produces distinct, level-appropriate tasks
    - Subject name alone does NOT dictate academic level
    """

    def setUp(self):
        self.app = app
        self.client = app.test_client()

    def _seed_test_syllabus(self, user_id, syllabus_id, subjects_list, semester=None, grade_level=None):
        s_doc = {
            "_id": syllabus_id,
            "syllabus_id": syllabus_id,
            "user_id": user_id,
            "student_id": user_id,
            "is_active": True,
            "status": "VALID",
            "validation_status": "VALID",
            "curriculumStatus": "VALID",
            "subjects": subjects_list,
            "chapters": {s["name"]: [{"name": t} for t in s.get("topics", [])] for s in subjects_list if isinstance(s, dict)}
        }
        if semester is not None:
            s_doc["semester"] = semester
            s_doc["current_semester"] = semester
        if grade_level is not None:
            s_doc["grade_level"] = grade_level
            s_doc["grade"] = grade_level
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db.syllabi.update_one(
                {"user_id": user_id, "syllabus_id": syllabus_id},
                {"$set": s_doc},
                upsert=True
            )

    def test_01_incomplete_profile_rejected_with_action_required(self):
        """Students with missing school/college classification must be asked to complete profile."""
        uid = "test_incomplete_student"
        self._seed_test_syllabus(uid, "syl_incomplete_01", [
            {"name": "Mathematics", "topics": ["Linear Equations"]}
        ])
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["user"] = {
                "id": uid,
                "email": "incomplete@student.test",
                "name": "Incomplete Student",
                "role": "student"
                # Intentionally missing grade, class, school, semester, college, program
            }

        res = self.client.post(
            "/api/learn-anywhere/generate",
            json={
                "subject": "Mathematics",
                "topic": "Linear Equations",
                "resource_category": "All Local Resources",
                "difficulty": "Medium"
            }
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertTrue(data.get("profile_incomplete"))
        self.assertEqual(data.get("action_required"), "complete_profile")
        self.assertIn("profile", data.get("error", "").lower())

    def test_02_college_student_missing_semester_rejected(self):
        """College student missing semester must be requested to complete profile, not guessed."""
        uid = "test_college_no_sem"
        self._seed_test_syllabus(uid, "syl_college_nosem_01", [
            {"name": "Computer Science", "topics": ["Sorting Algorithms"]}
        ])
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["user"] = {
                "id": uid,
                "email": "college_nosem@student.test",
                "name": "College Student No Sem",
                "role": "student",
                "college": "State Engineering College",
                "degree": "B.Tech",
                "department": "Computer Science"
                # Missing semester
            }

        res = self.client.post(
            "/api/learn-anywhere/generate",
            json={
                "subject": "Computer Science",
                "topic": "Sorting Algorithms",
                "resource_category": "All Local Resources",
                "difficulty": "Medium"
            }
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertTrue(data.get("profile_incomplete"))
        self.assertIn("semester", data.get("error", "").lower())

    def test_03_school_student_missing_grade_rejected(self):
        """School student missing grade level / class must be requested to complete profile."""
        uid = "test_school_no_grade"
        self._seed_test_syllabus(uid, "syl_school_nograde_01", [
            {"name": "General Science", "topics": ["Plant Leaves"]}
        ])
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["user"] = {
                "id": uid,
                "email": "school_nograde@student.test",
                "name": "School Student No Grade",
                "role": "student",
                "school": "City High School"
                # Missing grade_level / class / standard
            }

        res = self.client.post(
            "/api/learn-anywhere/generate",
            json={
                "subject": "General Science",
                "topic": "Plant Leaves",
                "resource_category": "Plants & Bio Resources",
                "difficulty": "Easy"
            }
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertTrue(data.get("profile_incomplete"))
        self.assertIn("grade", data.get("error", "").lower())

    def test_04_authenticated_school_student_receives_school_pedagogy(self):
        """School student must receive simple language, small numbers, and glossary of unfamiliar words."""
        uid = "test_auth_school_student"
        self._seed_test_syllabus(uid, "syl_auth_school_01", [
            {"name": "Mathematics", "topics": ["Simple Equations"]}
        ])
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["user"] = {
                "id": uid,
                "email": "school_kid@test.edu",
                "name": "School Kid",
                "role": "student",
                "school": "Green Valley Public School",
                "grade_level": "Grade 6",
                "board": "CBSE"
            }

        res = self.client.post(
            "/api/learn-anywhere/generate",
            json={
                "subject": "Mathematics",
                "topic": "Simple Equations",
                "resource_category": "All Local Resources",
                "difficulty": "Easy"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        act = data.get("activity", {})

        # Grounded student level
        self.assertEqual(act.get("student_type"), "SCHOOL")
        self.assertEqual(act.get("academic_level"), "SCHOOL")

        # Unfamiliar words glossary present
        unfamiliar = act.get("unfamiliar_words", [])
        self.assertIsInstance(unfamiliar, list)
        self.assertTrue(len(unfamiliar) >= 1)
        # Verify glossary structure
        for w in unfamiliar:
            self.assertTrue(bool(w.get("word")))
            self.assertTrue(bool(w.get("simple_meaning")))

        # Simple, beginner-friendly content with small numbers
        act_str = json.dumps(act).lower()
        self.assertTrue("x + 2 = 5" in act_str or "small" in act_str or "notebook" in act_str)
        # Must not contain advanced college calculus equations
        self.assertNotIn("characteristic equation", act_str)
        self.assertNotIn("continuous differentiability", act_str)

    def test_05_authenticated_college_student_receives_college_pedagogy(self):
        """College student must receive technical examples, calculations, and assumptions & reasoning."""
        uid = "test_auth_college_student"
        self._seed_test_syllabus(uid, "syl_auth_college_01", [
            {"name": "Computer Science", "topics": ["Sorting Algorithms & Complexity"]}
        ], semester="5")
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["user"] = {
                "id": uid,
                "email": "college_senior@university.edu",
                "name": "College Senior",
                "role": "student",
                "college": "Institute of Technology",
                "degree": "B.Tech",
                "department": "Computer Science & Engineering",
                "semester": "5"
            }

        res = self.client.post(
            "/api/learn-anywhere/generate",
            json={
                "subject": "Computer Science",
                "topic": "Sorting Algorithms & Complexity",
                "resource_category": "All Local Resources",
                "difficulty": "Hard"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        act = data.get("activity", {})

        # Grounded student level
        self.assertEqual(act.get("student_type"), "COLLEGE")
        self.assertEqual(act.get("academic_level"), "COLLEGE")

        # Assumptions and reasoning present
        assumptions = act.get("assumptions_and_reasoning", [])
        self.assertIsInstance(assumptions, list)
        self.assertTrue(len(assumptions) >= 1)

        # Realistic technical content with formal concepts
        act_str = json.dumps(act)
        self.assertTrue("O(N" in act_str or "trace" in act_str.lower() or "asymptotic" in act_str.lower())
        # Not reduced to a school-level counting experiment
        self.assertNotIn("Pocket Money", act["title"])

    def test_06_switching_accounts_produces_distinct_tasks(self):
        """Switching between School and College accounts for the same topic produces distinct tasks."""
        # 1. School Student Request
        res_school = gemini_service._build_deterministic_learn_anywhere(
            subject="Economics",
            subject_id="sub_econ_01",
            topic="Budgeting & Choice",
            resource_env="All Local Resources",
            difficulty="Medium",
            semester="Grade 7",
            program="School Social Studies",
            department="Social Studies",
            student_type="SCHOOL"
        )
        self.assertEqual(res_school.get("student_type"), "SCHOOL")
        self.assertIn("unfamiliar_words", res_school)
        self.assertTrue(len(res_school["unfamiliar_words"]) >= 2)
        self.assertIn("Needs vs Wants", res_school["title"])

        # 2. College Student Request
        res_college = gemini_service._build_deterministic_learn_anywhere(
            subject="Economics",
            subject_id="sub_econ_01",
            topic="Budgeting & Choice",
            resource_env="All Local Resources",
            difficulty="Medium",
            semester="3",
            program="B.A. Economics",
            department="Economics",
            student_type="COLLEGE"
        )
        self.assertEqual(res_college.get("student_type"), "COLLEGE")
        self.assertIn("assumptions_and_reasoning", res_college)
        self.assertTrue(len(res_college["assumptions_and_reasoning"]) >= 1)
        self.assertIn("Equilibrium", res_college["title"])

        # Tasks are completely distinct
        self.assertNotEqual(res_school["title"], res_college["title"])
        self.assertNotEqual(res_school["steps"], res_college["steps"])

    def test_07_subject_name_does_not_override_student_level(self):
        """A technical subject like 'Computer Science' generates a school task when requested by a school student."""
        res_cs_school = gemini_service._build_deterministic_learn_anywhere(
            subject="Computer Science",
            subject_id="CS101",
            topic="Algorithms",
            resource_env="All Local Resources",
            difficulty="Easy",
            semester="Grade 5",
            program="School Computing",
            department="Computer Studies",
            student_type="SCHOOL"
        )
        self.assertEqual(res_cs_school["student_type"], "SCHOOL")
        self.assertIn("unfamiliar_words", res_cs_school)
        # Explains one concept with small numbers (1 to 5)
        self.assertIn("5", json.dumps(res_cs_school["steps"]))
        # Does not use Big-O jargon
        self.assertNotIn("asymptotic", res_cs_school["simple_explanation"].lower())


if __name__ == "__main__":
    unittest.main()
