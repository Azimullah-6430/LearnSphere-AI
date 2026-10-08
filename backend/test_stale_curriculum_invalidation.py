import unittest
import json
import uuid
from datetime import datetime, timezone
from server import app, _get_authoritative_curriculum
from app.db import get_mongodb, get_sqlite_db

class TestStaleCurriculumInvalidation(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.uid1 = uuid.uuid4().hex[:10]
        self.uid2 = uuid.uuid4().hex[:10]

        # Register Student 1
        self.student1_email = f"student_one_{self.uid1}@learnsphere.edu"
        self.password = "SecurePassword123!"
        reg1 = self.app.post("/api/auth/register", json={
            "name": "Student One",
            "email": self.student1_email,
            "password": self.password,
            "role": "student",
            "level": "college",
            "degree": "B.Tech Computer Science and Engineering",
            "department": "Computer Science",
            "semester": 5,
            "current_semester": 5
        })
        self.assertEqual(reg1.status_code, 201)
        self.student1_id = reg1.get_json()["user"]["id"]

        # Register Student 2
        self.student2_email = f"student_two_{self.uid2}@learnsphere.edu"
        reg2 = self.app.post("/api/auth/register", json={
            "name": "Student Two",
            "email": self.student2_email,
            "password": self.password,
            "role": "student",
            "level": "college",
            "degree": "B.Tech Mechanical Engineering",
            "department": "Mechanical Engineering",
            "semester": 5,
            "current_semester": 5
        })
        self.assertEqual(reg2.status_code, 201)
        self.student2_id = reg2.get_json()["user"]["id"]

    def tearDown(self):
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["syllabi"].delete_many({"student_id": {"$in": [self.student1_id, self.student2_id]}})
            mongo_db["users"].delete_many({"_id": {"$in": [self.student1_id, self.student2_id]}})

    def test_syllabus_replacement_invalidates_old_subjects(self):
        """
        Scenario:
        1. Student uploads Syllabus A (Subjects: DBMS, Operating Systems).
        2. Verify subjects from A appear in:
           - Personal Trainer / Active Curriculum
           - Knowledge Challenge
           - Reality Lab
        3. Student uploads Syllabus B (Subjects: Machine Learning, Computer Networks).
        4. After B becomes VALID:
           - Subjects from A MUST disappear.
           - Only subjects from B may remain.
        """
        mongo_db = get_mongodb()
        self.assertIsNotNone(mongo_db)

        # 1. Upload & Activate Syllabus A
        syl_a_id = f"syl_A_{self.uid1}"
        syl_a_doc = {
            "syllabus_id": syl_a_id,
            "syllabusId": syl_a_id,
            "student_id": self.student1_id,
            "studentId": self.student1_id,
            "semester": 5,
            "degree": "B.Tech Computer Science and Engineering",
            "department": "Computer Science",
            "curriculumStatus": "VALID",
            "validation_status": "VALID",
            "status": "VALID",
            "is_active": True,
            "subjects": [
                {
                    "id": "CS501",
                    "subject_id": "CS501",
                    "code": "CS501",
                    "name": "Database Management Systems",
                    "topics": ["ER Models", "Relational Algebra", "Normalization"],
                    "units": ["Unit 1", "Unit 2"],
                    "type": "Core Theory"
                },
                {
                    "id": "CS502",
                    "subject_id": "CS502",
                    "code": "CS502",
                    "name": "Operating Systems",
                    "topics": ["Process Scheduling", "Virtual Memory", "Deadlocks"],
                    "units": ["Unit 1", "Unit 2"],
                    "type": "Core Theory"
                }
            ],
            "chapters": {
                "Database Management Systems": [{"name": "Data Models", "concepts": ["ER Models"]}],
                "Operating Systems": [{"name": "Process Management", "concepts": ["Process Scheduling"]}]
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        mongo_db["syllabi"].insert_one(dict(syl_a_doc))

        # Authenticate as Student 1
        self.app.post("/api/auth/login", json={"email": self.student1_email, "password": self.password})

        # Check Active Curriculum API
        res_a = self.app.get("/api/curriculum/active")
        self.assertEqual(res_a.status_code, 200)
        data_a = res_a.get_json()
        self.assertTrue(data_a["is_valid"])
        self.assertEqual(data_a["curriculum_id"], syl_a_id)
        sub_names_a = [s["name"] for s in data_a["subjects"]]
        self.assertEqual(sorted(sub_names_a), ["Database Management Systems", "Operating Systems"])

        # Check consumption via authoritative curriculum service
        cur_a = _get_authoritative_curriculum(self.student1_id)
        self.assertIsNotNone(cur_a)
        self.assertEqual(cur_a["curriculum_id"], syl_a_id)
        self.assertIn("Database Management Systems", [s["name"] for s in cur_a["subjects"]])

        # 2. Student uploads Syllabus B -> Simulate upload & activation
        syl_b_id = f"syl_B_{self.uid1}"
        syl_b_doc = {
            "syllabus_id": syl_b_id,
            "syllabusId": syl_b_id,
            "student_id": self.student1_id,
            "studentId": self.student1_id,
            "semester": 5,
            "degree": "B.Tech Computer Science and Engineering",
            "department": "Computer Science",
            "curriculumStatus": "VALID",
            "validation_status": "VALID",
            "status": "VALID",
            "is_active": True,
            "subjects": [
                {
                    "id": "CS503",
                    "subject_id": "CS503",
                    "code": "CS503",
                    "name": "Machine Learning",
                    "topics": ["Linear Regression", "Neural Networks", "SVM"],
                    "units": ["Unit 1", "Unit 2"],
                    "type": "Core Theory"
                },
                {
                    "id": "CS504",
                    "subject_id": "CS504",
                    "code": "CS504",
                    "name": "Computer Networks",
                    "topics": ["TCP/IP", "Routing Protocols", "DNS"],
                    "units": ["Unit 1", "Unit 2"],
                    "type": "Core Theory"
                }
            ],
            "chapters": {
                "Machine Learning": [{"name": "Supervised Learning", "concepts": ["Linear Regression"]}],
                "Computer Networks": [{"name": "Transport Layer", "concepts": ["TCP/IP"]}]
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        # Atomically deactivate older syllabus A as server does
        mongo_db["syllabi"].update_many(
            {"student_id": self.student1_id, "is_active": True},
            {"$set": {"is_active": False, "isActive": False, "status": "ARCHIVED", "curriculumStatus": "ARCHIVED"}}
        )
        mongo_db["syllabi"].insert_one(dict(syl_b_doc))

        # 3. Retrieve curriculum again
        res_b = self.app.get("/api/curriculum/active")
        self.assertEqual(res_b.status_code, 200)
        data_b = res_b.get_json()
        self.assertTrue(data_b["is_valid"])
        self.assertEqual(data_b["curriculum_id"], syl_b_id)

        sub_names_b = [s["name"] for s in data_b["subjects"]]
        # Verify: Subjects from A MUST disappear!
        self.assertNotIn("Database Management Systems", sub_names_b)
        self.assertNotIn("Operating Systems", sub_names_b)
        # Verify: Only subjects from B may remain!
        self.assertEqual(sorted(sub_names_b), ["Computer Networks", "Machine Learning"])

        # Check authoritative curriculum consumed by learning agents
        cur_b = _get_authoritative_curriculum(self.student1_id)
        self.assertEqual(cur_b["curriculum_id"], syl_b_id)
        cur_b_sub_names = [s["name"] for s in cur_b["subjects"]]
        self.assertNotIn("Database Management Systems", cur_b_sub_names)
        self.assertIn("Machine Learning", cur_b_sub_names)
        self.assertIn("Computer Networks", cur_b_sub_names)

    def test_account_switch_and_refresh_state_isolation(self):
        """
        Scenario:
        1. Student 1 logs in and has Syllabus B (Machine Learning, Computer Networks).
        2. Student 1 logs out.
        3. Student 2 logs in (Student 2 has NO syllabus uploaded).
        4. Student 2 MUST NOT see Student 1's subjects.
        5. Page refresh simulation: calling /api/auth/me + /api/curriculum/active restores correct state from MongoDB.
        """
        mongo_db = get_mongodb()
        
        # Student 1 has valid curriculum
        syl_1_id = f"syl_1_{self.uid1}"
        mongo_db["syllabi"].insert_one({
            "syllabus_id": syl_1_id,
            "student_id": self.student1_id,
            "semester": 5,
            "curriculumStatus": "VALID",
            "validation_status": "VALID",
            "status": "VALID",
            "is_active": True,
            "subjects": [{"id": "CS1", "subject_id": "CS1", "code": "CS1", "name": "Deep Learning", "topics": ["CNNs"]}],
            "chapters": {"Deep Learning": [{"name": "CNNs", "concepts": ["CNNs"]}]},
            "updated_at": datetime.now(timezone.utc)
        })

        # 1. Student 1 logs in
        self.app.post("/api/auth/login", json={"email": self.student1_email, "password": self.password})
        res1 = self.app.get("/api/curriculum/active")
        data1 = res1.get_json()
        self.assertTrue(data1["is_valid"])
        self.assertEqual(len(data1["subjects"]), 1)
        self.assertEqual(data1["subjects"][0]["name"], "Deep Learning")

        # 2. Student 1 logs out
        logout_res = self.app.post("/api/auth/logout")
        self.assertEqual(logout_res.status_code, 200)

        # 3. Student 2 logs in
        login2_res = self.app.post("/api/auth/login", json={"email": self.student2_email, "password": self.password})
        self.assertEqual(login2_res.status_code, 200)

        # 4. Student 2 checks curriculum -> MUST NOT see Student 1's subjects
        res2 = self.app.get("/api/curriculum/active")
        data2 = res2.get_json()
        self.assertFalse(data2["is_valid"])
        self.assertEqual(data2["subjects"], [])
        self.assertEqual(data2["curriculumStatus"], "NOT_UPLOADED")

        # 5. Simulate page refresh: verify session via /api/auth/me and reload /api/curriculum/active
        me_res = self.app.get("/api/auth/me")
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.get_json()["user"]["id"], self.student2_id)

        refresh_cur_res = self.app.get("/api/curriculum/active")
        refresh_cur_data = refresh_cur_res.get_json()
        self.assertFalse(refresh_cur_data["is_valid"])
        self.assertEqual(refresh_cur_data["subjects"], [])
        self.assertNotEqual(refresh_cur_data.get("curriculum_id"), syl_1_id)

if __name__ == "__main__":
    unittest.main()
