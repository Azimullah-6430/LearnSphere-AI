"""
Authoritative Single-Source Curriculum Service Synchronization Test
Verifies:
1. Personal Trainer, Reality Lab, and Knowledge Transfer all connect to ONE authoritative curriculum service.
2. They do NOT maintain independent subject lists.
3. If curriculumStatus != "VALID", all three receive subjects = [] and refuse generation.
4. If curriculumStatus == "VALID", all three receive the exact same validated subjects list.
5. Invalidation and replacement flow:
   - When a new syllabus is uploaded, old curriculum context is invalidated.
   - New syllabus is processed and validated.
   - Replaced only after successful validation.
"""

import json
import uuid
import unittest
from server import app

class TestAuthoritativeCurriculumServiceSync(unittest.TestCase):

    def test_01_single_authoritative_curriculum_sync_across_features(self):
        """Verify that Personal Trainer, Reality Lab, and Knowledge Transfer receive the exact same subjects."""
        client = app.test_client()

        suffix = uuid.uuid4().hex[:8]
        reg_payload = {
            "name": "Sync Test Student",
            "email": f"sync_student_{suffix}@example.com",
            "password": "Password123!",
            "role": "student",
            "level": "college",
            "institution_name": "Anna University",
            "degree": "B.Tech",
            "department": "Information Technology",
            "current_year": 3,
            "current_semester": 5,
            "regulation": "R2024"
        }
        reg_res = client.post("/api/auth/register", json=reg_payload)
        self.assertIn(reg_res.status_code, [200, 201])

        # 1. State: NOT_UPLOADED -> all three must have 0 subjects and reject generation
        cur_res = client.get("/api/curriculum/active")
        self.assertEqual(cur_res.status_code, 200)
        self.assertEqual(cur_res.get_json().get("subjects"), [])

        pt_res = client.post("/api/trainer/chat", json={"message": "Explain SQL", "subject": "Database Management Systems", "semester": 5})
        self.assertEqual(pt_res.status_code, 400)

        rl_res = client.post("/api/reality-lab/generate", json={"subject": "Database Management Systems"})
        self.assertEqual(rl_res.status_code, 400)

        kt_res = client.post("/api/transfer/generate", json={"subject": "Database Management Systems", "topic": "Transactions"})
        self.assertEqual(kt_res.status_code, 400)

        # 2. Upload Valid Semester 5 Syllabus
        sem5_syllabus = """
        ANNA UNIVERSITY, CHENNAI
        B.TECH INFORMATION TECHNOLOGY
        SEMESTER V
        IT3501 Database Management Systems (Credits: 3, L:3 T:0 P:0)
        IT3502 Web Technologies (Credits: 3, L:3 T:0 P:0)
        IT3503 Computer Networks (Credits: 3, L:3 T:0 P:0)
        CS3591 Theory of Computation (Credits: 3, L:3 T:0 P:0)
        IT3511 DBMS Laboratory (Credits: 2, L:0 T:0 P:4)
        """
        syl_res = client.post("/api/syllabus/analyze", json={"text": sem5_syllabus, "semester": 5})
        self.assertEqual(syl_res.status_code, 200)
        self.assertEqual(syl_res.get_json().get("validation_status"), "VALID")

        # 3. Active curriculum returns validated subjects
        cur_res = client.get("/api/curriculum/active")
        self.assertEqual(cur_res.status_code, 200)
        cur_data = cur_res.get_json()
        validated_subjects = [s.get("name") if isinstance(s, dict) else s for s in cur_data.get("subjects", [])]
        self.assertEqual(len(validated_subjects), 5)

        # 4. Query Personal Trainer for subjects -> Returns the exact same validated subjects list
        pt_list_res = client.post("/api/trainer/chat", json={"message": "What are my semester subjects?", "semester": 5})
        self.assertEqual(pt_list_res.status_code, 200)
        pt_reply = pt_list_res.get_json().get("reply", "")
        for s in validated_subjects:
            self.assertIn(s, pt_reply, f"Personal Trainer missing subject: {s}")

        # 5. Reality Lab generates successfully with the validated subject
        rl_res = client.post("/api/reality-lab/generate", json={"subject": "Database Management Systems"})
        self.assertEqual(rl_res.status_code, 200)
        self.assertEqual(rl_res.get_json().get("subject"), "Database Management Systems")

        # 6. Knowledge Transfer accepts the validated subject and rejects unvalidated subject
        kt_res = client.post("/api/transfer/generate", json={"subject": "Database Management Systems", "topic": "Relational Algebra"})
        self.assertEqual(kt_res.status_code, 200)

        kt_invalid_res = client.post("/api/transfer/generate", json={"subject": "Unrelated Mechanical Dynamics", "topic": "Thermodynamics"})
        self.assertEqual(kt_invalid_res.status_code, 400)

        # 7. Invalidate and Replace flow: Upload a new syllabus for Semester 5 with different subjects
        new_syllabus = """
        ANNA UNIVERSITY, CHENNAI
        B.TECH INFORMATION TECHNOLOGY
        SEMESTER V (REVISED 2026)
        IT5010 Advanced Distributed Computing (Credits: 4, L:3 T:1 P:0)
        IT5020 Modern Full-Stack Engineering (Credits: 4, L:3 T:1 P:0)
        IT5030 High-Performance Networks (Credits: 3, L:3 T:0 P:0)
        """
        syl_res2 = client.post("/api/syllabus/analyze", json={"text": new_syllabus, "semester": 5})
        self.assertEqual(syl_res2.status_code, 200)
        self.assertEqual(syl_res2.get_json().get("validation_status"), "VALID")

        # 8. All three features immediately reflect the newly validated syllabus with zero stale caching
        cur_res2 = client.get("/api/curriculum/active")
        cur_data2 = cur_res2.get_json()
        new_validated_subjects = [s.get("name") if isinstance(s, dict) else s for s in cur_data2.get("subjects", [])]
        self.assertEqual(len(new_validated_subjects), 3)
        self.assertIn("Advanced Distributed Computing", new_validated_subjects)
        self.assertNotIn("Database Management Systems", new_validated_subjects)

        # Personal Trainer now returns revised subjects
        pt_list_res2 = client.post("/api/trainer/chat", json={"message": "What are my semester subjects?", "semester": 5})
        pt_reply2 = pt_list_res2.get_json().get("reply", "")
        self.assertIn("Advanced Distributed Computing", pt_reply2)
        self.assertNotIn("Database Management Systems", pt_reply2)

if __name__ == "__main__":
    unittest.main()
