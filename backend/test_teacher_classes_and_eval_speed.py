import unittest
import json
import uuid
from server import app
from app.db import get_mongodb

class TestTeacherClassesAndEval(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.uid_prefix = uuid.uuid4().hex[:8]
        self.password = "TeacherPass123!"

    def tearDown(self):
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["users"].delete_many({"email": {"$regex": f"^{self.uid_prefix}"}})
            mongo_db["teacher_classes"].delete_many({"name": {"$regex": f"^{self.uid_prefix}"}})

    def _create_and_login_teacher(self, name="Test Teacher"):
        uid = f"{self.uid_prefix}_{uuid.uuid4().hex[:6]}"
        email = f"{uid}@learnsphere.edu"
        reg_res = self.app.post("/api/auth/register", json={
            "name": name,
            "email": email,
            "password": self.password,
            "role": "teacher",
            "teacherLevel": "school",
            "institutionName": "Greenwood High"
        })
        self.assertEqual(reg_res.status_code, 201)
        user_id = reg_res.get_json()["user"]["id"]
        
        login_res = self.app.post("/api/auth/login", json={"email": email, "password": self.password, "role": "teacher"})
        self.assertEqual(login_res.status_code, 200)
        return user_id, email

    def test_teacher_class_persistence_lifecycle(self):
        """Verify teacher class is created, stored permanently in MongoDB, retrieved on login, updated, and deleted."""
        teacher_id, email = self._create_and_login_teacher("Dr. Alan Turing")

        # 1. Create Class
        cls_name = f"{self.uid_prefix} Grade 10-A Science"
        create_res = self.app.post("/api/teacher/classes", json={
            "id": f"cls_{self.uid_prefix}_1",
            "name": cls_name,
            "level": "school",
            "type": "School Class",
            "board": "CBSE",
            "gradeLevel": "Grade 10",
            "section": "A",
            "subjects": ["Physics", "Chemistry", "Biology"],
            "students": [
                {"id": "std_1", "rollNo": "ROLL-101", "name": "Alice Johnson", "order": 1, "marksHistory": []},
                {"id": "std_2", "rollNo": "ROLL-102", "name": "Bob Smith", "order": 2, "marksHistory": []}
            ],
            "students_count": 2
        })
        self.assertEqual(create_res.status_code, 201)
        created_data = create_res.get_json()
        self.assertTrue(created_data["success"])
        self.assertEqual(created_data["class"]["name"], cls_name)

        # 2. Query Classes from MongoDB
        get_res = self.app.get("/api/teacher/classes")
        self.assertEqual(get_res.status_code, 200)
        classes_data = get_res.get_json()
        self.assertTrue(classes_data["success"])
        self.assertEqual(len(classes_data["classes"]), 1)
        self.assertEqual(classes_data["classes"][0]["name"], cls_name)
        self.assertEqual(len(classes_data["classes"][0]["students"]), 2)

        # 3. Simulate Logout and Login Again -> Classes must still exist in MongoDB
        self.app.post("/api/auth/logout")
        login_res = self.app.post("/api/auth/login", json={"email": email, "password": self.password, "role": "teacher"})
        self.assertEqual(login_res.status_code, 200)

        get_res_after_login = self.app.get("/api/teacher/classes")
        self.assertEqual(get_res_after_login.status_code, 200)
        reloaded_classes = get_res_after_login.get_json()
        self.assertEqual(len(reloaded_classes["classes"]), 1)
        self.assertEqual(reloaded_classes["classes"][0]["name"], cls_name)

        # 4. Update Class (Roster update)
        update_res = self.app.put(f"/api/teacher/classes/cls_{self.uid_prefix}_1", json={
            "students": [
                {"id": "std_1", "rollNo": "ROLL-101", "name": "Alice Johnson", "order": 1, "marksHistory": [{"subject": "Physics", "assessment": "Midterm", "score": 48, "maxMarks": 50}]},
                {"id": "std_2", "rollNo": "ROLL-102", "name": "Bob Smith", "order": 2, "marksHistory": []},
                {"id": "std_3", "rollNo": "ROLL-103", "name": "Charlie Brown", "order": 3, "marksHistory": []}
            ]
        })
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.get_json()["class"]["students_count"], 3)

        # 5. Delete Class
        del_res = self.app.delete(f"/api/teacher/classes/cls_{self.uid_prefix}_1")
        self.assertEqual(del_res.status_code, 200)

        get_after_del = self.app.get("/api/teacher/classes")
        self.assertEqual(len(get_after_del.get_json()["classes"]), 0)

if __name__ == "__main__":
    unittest.main()
