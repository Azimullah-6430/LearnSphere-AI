import unittest
import json
import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from server import app
from app.gemini_service import gemini_service

class TestLearnAnywhereReliabilityAudit(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        os.environ["TESTING"] = "1"

        # Mock authenticated student user session
        self.student_headers = {"Content-Type": "application/json"}
        with self.client.session_transaction() as sess:
            sess["user_id"] = "audit_student_123"
            sess["user_role"] = "student"

    def test_unauthorized_teacher_access_blocked(self):
        """Teacher portal accounts must be blocked with 403."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = "audit_teacher_456"
            sess["user_role"] = "teacher"

        res = self.client.post("/api/learn-anywhere/generate", json={"subject": "Physics"})
        self.assertEqual(res.status_code, 403)
        data = json.loads(res.data)
        self.assertFalse(data["success"])
        self.assertIn("Access denied", data["error"])

    def test_unauthenticated_access_blocked(self):
        """Unauthenticated requests must be blocked with 401."""
        unauth_client = app.test_client()
        res = unauth_client.post("/api/learn-anywhere/generate", json={"subject": "Physics"})
        self.assertEqual(res.status_code, 401)

    def test_missing_syllabus_returns_curriculum_required(self):
        """Students without an active validated syllabus must receive curriculum_required: True."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = "no_syllabus_student_789"
            sess["user_role"] = "student"

        res = self.client.post("/api/learn-anywhere/generate", json={"subject": "Quantum Physics"})
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertFalse(data["success"])
        self.assertTrue(data.get("curriculum_required"))
        self.assertIn("syllabus", data["error"].lower())

    def _seed_test_syllabus(self, user_id, syllabus_id, subjects_list):
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

    def test_invalid_subject_not_in_syllabus_rejected(self):
        """Requesting a subject outside the validated curriculum must return 400 error."""
        self._seed_test_syllabus("audit_student_123", "syl_audit_1", [
            {"name": "Physics", "topics": ["Laws of Motion", "Optics"]}
        ])

        res = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Astronomy", # Not in syllabus
            "topic": "Black Holes",
            "syllabus_id": "syl_audit_1"
        })
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertFalse(data["success"])
        self.assertIn("Astronomy", data["error"])

    def test_subject_switch_clears_incompatible_cache(self):
        """Changing requested subject must NOT return cached response from another subject."""
        self._seed_test_syllabus("audit_student_123", "syl_audit_2", [
            {"name": "Physics", "topics": ["Kinematics"]},
            {"name": "Computer Science", "topics": ["Data Structures"]}
        ])

        # 1. Physics request
        res1 = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Physics",
            "topic": "Kinematics",
            "syllabus_id": "syl_audit_2",
            "idempotency_key": "req_key_101"
        })
        self.assertEqual(res1.status_code, 200)
        data1 = json.loads(res1.data)
        self.assertEqual(data1["activity"]["subject"], "Physics")

        # 2. Computer Science request with different subject
        res2 = self.client.post("/api/learn-anywhere/generate", json={
            "subject": "Computer Science",
            "topic": "Data Structures",
            "syllabus_id": "syl_audit_2",
            "idempotency_key": "req_key_102"
        })
        self.assertEqual(res2.status_code, 200)
        data2 = json.loads(res2.data)
        self.assertEqual(data2["activity"]["subject"], "Computer Science")
        self.assertNotEqual(data2["activity"]["title"], data1["activity"]["title"])

    def test_school_vs_college_teaching_plan_adaptation(self):
        """School vs College profile attributes adapt teaching strategies appropriately."""
        school_plan = gemini_service._normalize_learn_anywhere_response(
            res={"activity_title": "Soil Moisture Test"},
            subject="Biology",
            topic="Plant Respiration",
            unit="Unit 1",
            curriculum_ref="NCERT Grade 8",
            resource_env="Farmland & Soil",
            difficulty="Easy",
            semester="Class 8",
            program="School Education",
            department="Class 8 Science",
            constraint_mode="strict_only"
        )
        self.assertEqual(school_plan["academic_grounding"]["grade_or_semester"], "Class 8")
        self.assertEqual(school_plan["subject"], "Biology")

        college_plan = gemini_service._normalize_learn_anywhere_response(
            res={"activity_title": "Binary Tree Traversal Analysis"},
            subject="Computer Science",
            topic="Binary Search Trees",
            unit="Unit 3",
            curriculum_ref="AICTE B.Tech CSE",
            resource_env="All Local Resources",
            difficulty="Hard",
            semester="Semester 4",
            program="B.Tech Computer Science",
            department="Computer Science & Engineering",
            constraint_mode="strict_only"
        )
        self.assertEqual(college_plan["academic_grounding"]["grade_or_semester"], "Semester 4")
        self.assertEqual(college_plan["academic_grounding"]["program"], "B.Tech Computer Science")

    def test_hazardous_instruction_neutralization(self):
        """Hazardous safety precautions (e.g. mains electricity, open fire) must be neutralized."""
        raw_res = {
            "title": "Electrical Conductivity Test",
            "safety_precautions": "Plug copper wires directly into 220V mains electricity outlet and ignite open flame."
        }
        normalized = gemini_service._normalize_learn_anywhere_response(
            res=raw_res,
            subject="Physics",
            topic="Electric Circuits",
            unit="Electricity",
            curriculum_ref="Syllabus",
            resource_env="All Local Resources",
            difficulty="Medium",
            semester="Semester 2",
            program="B.Sc",
            department="Physics",
            constraint_mode="strict_only"
        )
        # Verify hazardous instructions were removed
        self.assertNotIn("220V", normalized["safety_precautions"])
        self.assertNotIn("open flame", normalized["safety_precautions"].lower())
        self.assertIn("flat ground", normalized["safety_precautions"])

    def test_python_code_syntax_validation(self):
        """Python code snippets in coding tasks must undergo syntax validation."""
        valid_res = {
            "title": "Stack Implementation",
            "coding_task": {
                "is_coding_topic": True,
                "target_language": "Python",
                "code_snippet": "def push(item, stack):\n    stack.append(item)\n    return stack"
            }
        }
        norm_valid = gemini_service._normalize_learn_anywhere_response(
            res=valid_res,
            subject="Computer Science",
            topic="Stacks",
            unit="Data Structures",
            curriculum_ref="Syllabus",
            resource_env="All Local Resources",
            difficulty="Medium",
            semester="Semester 3",
            program="B.Tech",
            department="CSE",
            constraint_mode="strict_only"
        )
        self.assertNotIn("Syntax note", norm_valid["coding_task"]["debugging_guidance"])

        invalid_res = {
            "title": "Broken Code",
            "coding_task": {
                "is_coding_topic": True,
                "target_language": "Python",
                "code_snippet": "def broken_func(\n    return 42" # Invalid syntax
            }
        }
        norm_invalid = gemini_service._normalize_learn_anywhere_response(
            res=invalid_res,
            subject="Computer Science",
            topic="Syntax",
            unit="Data Structures",
            curriculum_ref="Syllabus",
            resource_env="All Local Resources",
            difficulty="Medium",
            semester="Semester 3",
            program="B.Tech",
            department="CSE",
            constraint_mode="strict_only"
        )
        self.assertIn("Syntax note", norm_invalid["coding_task"]["debugging_guidance"])

if __name__ == "__main__":
    unittest.main()
