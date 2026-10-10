import unittest
import json
import uuid
import datetime
import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from server import app, get_mongodb, get_sqlite_db

class TestLearnAnywhereCurriculumIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()
        cls.mongo = get_mongodb()

    def _create_test_student(self, email_prefix="student_lfa"):
        client = app.test_client()
        unique_id = str(uuid.uuid4())[:8]
        email = f"{email_prefix}_{unique_id}@test.com"
        password = "Password123!"

        # Register student
        res = client.post("/api/auth/register", json={
            "name": f"Student {unique_id}",
            "email": email,
            "password": password,
            "role": "student",
            "student_type": "COLLEGE",
            "degree": "B.Tech Mechanical Engineering",
            "department": "Mechanical Engineering",
            "semester": 4,
            "current_semester": 4
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        token = data.get("token")
        user_id = data.get("user", {}).get("id") or data.get("user", {}).get("user_id")

        return {
            "client": client,
            "token": token,
            "user_id": str(user_id),
            "email": email,
            "headers": {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        }

    def _insert_valid_syllabus(self, student_id, subjects_data, syllabus_id=None, is_active=True, status="VALID"):
        s_id = syllabus_id or f"syl_{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.utcnow()

        units = {}
        for sub in subjects_data:
            s_name = sub.get("name") if isinstance(sub, dict) else str(sub)
            units[s_name] = [
                {"name": f"Unit 1: Fundamentals of {s_name}", "concepts": [f"{s_name} Law 1", f"{s_name} Application"]},
                {"name": f"Unit 2: Applied {s_name}", "concepts": [f"{s_name} Equilibrium", f"{s_name} Dynamics"]}
            ]

        doc = {
            "syllabus_id": s_id,
            "student_id": str(student_id),
            "studentId": str(student_id),
            "file_name": "Official_Mechanical_Curriculum.pdf",
            "document_name": "Official_Mechanical_Curriculum.pdf",
            "degree": "B.Tech Mechanical Engineering",
            "department": "Mechanical Engineering",
            "semester": 4,
            "current_semester": 4,
            "is_active": is_active,
            "isActive": is_active,
            "status": status,
            "curriculumStatus": status,
            "validation_status": status,
            "validationStatus": status,
            "subjects": subjects_data,
            "extracted_subjects": subjects_data,
            "units": units,
            "chapters": units,
            "created_at": now,
            "updated_at": now
        }

        if self.mongo is not None:
            self.mongo["syllabi"].insert_one(doc)
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO syllabi (syllabus_id, student_id, file_name, is_active, status, validation_status, analysis_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (s_id, str(student_id), "Official_Mechanical_Curriculum.pdf", 1 if is_active else 0, status, status, json.dumps(doc), now.isoformat(), now.isoformat())
            )
            conn.commit()
            conn.close()

        return s_id

    def test_1_missing_curriculum_gating(self):
        """When no valid syllabus has been uploaded, generation must be blocked (400)."""
        student = self._create_test_student("lfa_missing_curric")

        # Attempt generating without syllabus
        res = student["client"].post("/api/learn-anywhere/generate", headers=student["headers"], json={
            "subject": "Thermodynamics",
            "topic": "Heat Transfer",
            "resource_category": "Farmland & Soil"
        })

        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertTrue(data.get("curriculum_required"))
        self.assertIn("No active validated syllabus found", data.get("error"))

    def test_2_valid_curriculum_grounded_generation(self):
        """When student has a valid curriculum, subjects and topics are strictly validated and traceable."""
        student = self._create_test_student("lfa_valid_curric")

        subjects_data = [
            {"name": "Fluid Mechanics", "code": "ME401", "subject_id": "sub_fm_401"},
            {"name": "Applied Thermodynamics", "code": "ME402", "subject_id": "sub_th_402"}
        ]
        s_id = self._insert_valid_syllabus(student["user_id"], subjects_data)

        # Generate activity with valid subject
        res = student["client"].post("/api/learn-anywhere/generate", headers=student["headers"], json={
            "subject": "Fluid Mechanics",
            "subject_id": "sub_fm_401",
            "topic": "Capillarity and Surface Tension",
            "resource_category": "Village Water & Wells",
            "custom_materials": "Clay pot, well water, cotton thread",
            "constraint_mode": "strict_only",
            "syllabus_id": s_id
        })

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("subject"), "Fluid Mechanics")
        self.assertEqual(data.get("syllabus_id"), s_id)
        self.assertIn("activity", data)

        activity = data["activity"]
        self.assertEqual(activity.get("syllabus_id"), s_id)
        self.assertEqual(activity.get("subject"), "Fluid Mechanics")
        self.assertTrue(len(activity.get("steps", [])) > 0)
        self.assertTrue(len(activity.get("local_materials", [])) > 0)
        self.assertTrue(bool(activity.get("scientific_principle")))

    def test_3_invalid_curriculum_states_blocked(self):
        """When syllabus is in EXTRACTION_FAILED or NEEDS_REVIEW status, generation must be blocked."""
        student = self._create_test_student("lfa_invalid_status")

        # Insert failed syllabus
        self._insert_valid_syllabus(
            student["user_id"],
            [{"name": "General Science"}],
            status="EXTRACTION_FAILED",
            is_active=False
        )

        res = student["client"].post("/api/learn-anywhere/generate", headers=student["headers"], json={
            "subject": "General Science"
        })

        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertTrue(data.get("curriculum_required"))

    def test_4_cross_user_isolation_and_idor_protection(self):
        """Student A cannot use Student B's syllabus_id to generate activities or read Student B's curriculum."""
        student_a = self._create_test_student("lfa_student_a")
        student_b = self._create_test_student("lfa_student_b")

        # Student B uploads valid syllabus
        b_subjects = [{"name": "Biochemistry", "code": "BIO101", "subject_id": "sub_bio_101"}]
        s_id_b = self._insert_valid_syllabus(student_b["user_id"], b_subjects)

        # Student A (no syllabus of their own) attempts to pass Student B's syllabus_id
        res = student_a["client"].post("/api/learn-anywhere/generate", headers=student_a["headers"], json={
            "subject": "Biochemistry",
            "syllabus_id": s_id_b
        })

        # Must reject because syllabus belongs to student B
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertTrue(data.get("curriculum_required"))

    def test_5_syllabus_replacement_and_stale_invalidation(self):
        """When student replaces their syllabus, old syllabus is archived and new curriculum becomes authoritative."""
        student = self._create_test_student("lfa_replace_curric")

        # 1. Upload Syllabus V1 (Physics)
        v1_subs = [{"name": "Classical Physics", "code": "PHY101"}]
        s_id_v1 = self._insert_valid_syllabus(student["user_id"], v1_subs, is_active=True)

        # Generate with V1
        res1 = student["client"].post("/api/learn-anywhere/generate", headers=student["headers"], json={
            "subject": "Classical Physics"
        })
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.get_json().get("syllabus_id"), s_id_v1)

        # 2. Student replaces syllabus (deletes / archives V1, uploads V2 Chemistry)
        del_res = student["client"].delete("/api/syllabus", headers=student["headers"])
        self.assertEqual(del_res.status_code, 200)

        v2_subs = [{"name": "Organic Chemistry", "code": "CHEM201"}]
        s_id_v2 = self._insert_valid_syllabus(student["user_id"], v2_subs, is_active=True)

        # 3. Old subject from V1 is no longer part of validated curriculum
        res_old = student["client"].post("/api/learn-anywhere/generate", headers=student["headers"], json={
            "subject": "Classical Physics"
        })
        self.assertEqual(res_old.status_code, 400)
        self.assertIn("not present in your validated curriculum", res_old.get_json().get("error"))

        # 4. New subject from V2 succeeds with new syllabus ID
        res_new = student["client"].post("/api/learn-anywhere/generate", headers=student["headers"], json={
            "subject": "Organic Chemistry"
        })
        self.assertEqual(res_new.status_code, 200)
        data_new = res_new.get_json()
        self.assertEqual(data_new.get("subject"), "Organic Chemistry")
        self.assertEqual(data_new.get("syllabus_id"), s_id_v2)


if __name__ == "__main__":
    unittest.main()
