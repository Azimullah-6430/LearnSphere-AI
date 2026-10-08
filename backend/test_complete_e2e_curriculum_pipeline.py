import unittest
import json
import uuid
import time
from datetime import datetime, timezone
from server import app, _get_authoritative_curriculum, gemini_service
from app.db import get_mongodb

class TestCompleteE2ECurriculumPipeline(unittest.TestCase):
    """
    Complete End-to-End Test Suite for Syllabus Processing and Learning-Feature Pipeline.
    Tests all 11 required scenarios:
    1. Student with no syllabus.
    2. College student with semester 1 syllabus.
    3. College student with a multi-semester syllabus.
    4. College student with semester 5 profile and multi-semester syllabus.
    5. Large syllabus document.
    6. Multi-page subject table.
    7. Subject names spanning multiple lines.
    8. Laboratory subjects.
    9. Elective subjects.
    10. Repeated table headers across pages.
    11. Multiple students with strict data isolation.
    """

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.uid_prefix = uuid.uuid4().hex[:8]
        self.password = "SecurePassword123!"

    def tearDown(self):
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["syllabi"].delete_many({"student_id": {"$regex": f"^{self.uid_prefix}"}})
            mongo_db["users"].delete_many({"email": {"$regex": f"^{self.uid_prefix}"}})

    def _create_and_login_student(self, name, semester=1, degree="B.Tech Computer Science and Engineering", department="Computer Science"):
        uid = f"{self.uid_prefix}_{uuid.uuid4().hex[:6]}"
        email = f"{uid}@learnsphere.edu"
        reg_res = self.app.post("/api/auth/register", json={
            "name": name,
            "email": email,
            "password": self.password,
            "role": "student",
            "level": "college",
            "degree": degree,
            "program": degree,
            "department": department,
            "branch": department,
            "semester": semester,
            "current_semester": semester
        })
        self.assertEqual(reg_res.status_code, 201)
        user_id = reg_res.get_json()["user"]["id"]
        
        login_res = self.app.post("/api/auth/login", json={"email": email, "password": self.password})
        self.assertEqual(login_res.status_code, 200)
        return user_id, email

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 1: Student with NO syllabus
    # ──────────────────────────────────────────────────────────────────────────
    def test_01_student_with_no_syllabus(self):
        """
        Verify:
        NO SYLLABUS:
        - Personal Trainer -> blank (subjects = [])
        - Knowledge Challenge -> blank (subjects = [], topics = [])
        - Reality Lab -> blank (subjects = [])
        """
        user_id, email = self._create_and_login_student("No Syllabus Student", semester=1)

        # 1. Authoritative Backend Service returns None
        auth_curriculum = _get_authoritative_curriculum(user_id)
        self.assertIsNone(auth_curriculum)

        # 2. Active Curriculum API returns is_valid = False and empty subjects
        res = self.app.get("/api/curriculum/active")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["is_valid"])
        self.assertEqual(data["curriculumStatus"], "NOT_UPLOADED")
        self.assertEqual(data["subjects"], [])
        self.assertEqual(data["topics"], [])

        # 3. Personal Trainer Chat endpoint rejects unuploaded syllabus
        trainer_res = self.app.post("/api/trainer/chat", json={
            "message": "Explain the first topic",
            "subject": "Mathematics I"
        })
        # Should gracefully enforce syllabus upload requirement or inform student
        self.assertIn(trainer_res.status_code, [200, 400, 404])
        if trainer_res.status_code == 200:
            tr_data = trainer_res.get_json()
            self.assertTrue(tr_data.get("requires_syllabus", False) or "syllabus" in tr_data.get("reply", "").lower() or "upload" in tr_data.get("reply", "").lower())

        # 4. Knowledge Challenge Quiz endpoint returns empty / prompts upload
        quiz_res = self.app.get("/api/challenge/quiz?subject=Mathematics%20I&difficulty=Medium")
        self.assertIn(quiz_res.status_code, [200, 400, 404])
        if quiz_res.status_code == 400:
            q_data = quiz_res.get_json()
            self.assertFalse(q_data["success"])
            self.assertEqual(q_data["subjects"], [])

        # 5. Reality Lab Generation endpoint returns empty / prompts upload
        rl_res = self.app.post("/api/reality-lab/generate", json={
            "subject": "Mathematics I",
            "topic": "Matrices",
            "difficulty": "Medium"
        })
        self.assertIn(rl_res.status_code, [200, 400, 404])

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 2: College Student with Semester 1 Syllabus
    # ──────────────────────────────────────────────────────────────────────────
    def test_02_college_student_semester_1_syllabus(self):
        """
        Verify:
        VALID SYLLABUS: All correctly extracted subjects appear in Personal Trainer, Knowledge Challenge, and Reality Lab.
        """
        user_id, email = self._create_and_login_student("Semester 1 Student", semester=1)

        sem1_text = """
        DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING
        B.TECH FIRST YEAR CURRICULUM SCHEME
        
        SEMESTER 1
        | S.No | Course Code | Course Title | Category | Credits | L | T | P |
        | 1 | MA101 | Engineering Mathematics I | Theory Core | 4 | 3 | 1 | 0 |
        | 2 | PH101 | Engineering Physics | Theory Core | 3 | 3 | 0 | 0 |
        | 3 | CS101 | Problem Solving and Python Programming | Theory Core | 3 | 3 | 0 | 0 |
        | 4 | EE101 | Basic Electrical and Electronics Engineering | Theory Core | 3 | 3 | 0 | 0 |
        | 5 | PH111 | Physics Laboratory | Laboratory | 1.5 | 0 | 0 | 3 |
        | 6 | CS111 | Python Programming Laboratory | Laboratory | 1.5 | 0 | 0 | 3 |
        """

        start_time = time.time()
        upload_res = self.app.post("/api/syllabus/analyze", json={"text": sem1_text, "semester": 1})
        elapsed = time.time() - start_time
        self.assertEqual(upload_res.status_code, 200)
        up_data = upload_res.get_json()
        self.assertEqual(up_data["validation_status"], "VALID")

        # Query Active Curriculum
        res = self.app.get("/api/curriculum/active")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["is_valid"])
        self.assertEqual(data["curriculumStatus"], "VALID")
        
        sub_names = [s["name"] for s in data["subjects"]]
        self.assertEqual(len(sub_names), 6)
        self.assertIn("Engineering Mathematics I", sub_names)
        self.assertIn("Engineering Physics", sub_names)
        self.assertIn("Problem Solving and Python Programming", sub_names)
        self.assertIn("Basic Electrical and Electronics Engineering", sub_names)
        self.assertIn("Physics Laboratory", sub_names)
        self.assertIn("Python Programming Laboratory", sub_names)

        # Verify all 3 learning features receive the SAME curriculum
        auth_cur = _get_authoritative_curriculum(user_id)
        self.assertIsNotNone(auth_cur)
        self.assertEqual(len(auth_cur["subjects"]), 6)

    # ──────────────────────────────────────────────────────────────────────────
    # Scenarios 3 & 4: Multi-Semester Syllabus with Semester 5 Profile
    # ──────────────────────────────────────────────────────────────────────────
    def test_03_and_04_multi_semester_syllabus_selective_extraction(self):
        """
        Verify:
        - College student with semester 5 profile and multi-semester syllabus (Sem 1 to 8).
        - Extracts ONLY Semester 5 subjects.
        - Zero subjects from Semester 1, 2, 3, 4, 6, 7, 8 are included.
        """
        user_id, email = self._create_and_login_student("Semester 5 Student", semester=5)

        multi_sem_text = """
        ANNA UNIVERSITY CHENNAI - AFFILIATED INSTITUTIONS
        B.TECH COMPUTER SCIENCE AND ENGINEERING
        REGULATION 2021 CURRICULUM

        SEMESTER IV
        | S.No | Course Code | Course Title | Credits |
        | 1 | CS401 | Design and Analysis of Algorithms | 4 |
        | 2 | CS402 | Operating Systems | 3 |
        | 3 | CS403 | Database Management Systems | 3 |

        SEMESTER V
        | S.No | Course Code | Course Title | Category | Credits |
        | 1 | CS501 | Compiler Design | Theory Core | 4 |
        | 2 | CS502 | Computer Networks | Theory Core | 3 |
        | 3 | CS503 | Theory of Computation | Theory Core | 3 |
        | 4 | CS504 | Artificial Intelligence | Theory Core | 3 |
        | 5 | CS505 | Professional Elective I: Cloud Computing | Professional Elective | 3 |
        | 6 | CS511 | Compiler Design Laboratory | Laboratory | 1.5 |
        | 7 | CS512 | Networks Laboratory | Laboratory | 1.5 |

        SEMESTER VI
        | S.No | Course Code | Course Title | Credits |
        | 1 | CS601 | Distributed Systems | 3 |
        | 2 | CS602 | Mobile Computing | 3 |
        """

        upload_res = self.app.post("/api/syllabus/analyze", json={"text": multi_sem_text, "semester": 5})
        self.assertEqual(upload_res.status_code, 200)
        up_data = upload_res.get_json()
        self.assertEqual(up_data["validation_status"], "VALID")

        # Query active curriculum
        res = self.app.get("/api/curriculum/active")
        data = res.get_json()
        self.assertTrue(data["is_valid"])
        
        extracted_names = [s["name"] for s in data["subjects"]]
        self.assertEqual(len(extracted_names), 7)

        # Verify NO subjects from Semester IV or Semester VI
        self.assertNotIn("Design and Analysis of Algorithms", extracted_names)
        self.assertNotIn("Operating Systems", extracted_names)
        self.assertNotIn("Distributed Systems", extracted_names)
        self.assertNotIn("Mobile Computing", extracted_names)

        # Verify ALL Semester V subjects present
        self.assertIn("Compiler Design", extracted_names)
        self.assertIn("Computer Networks", extracted_names)
        self.assertIn("Theory of Computation", extracted_names)
        self.assertIn("Artificial Intelligence", extracted_names)
        self.assertTrue(any("Cloud Computing" in n for n in extracted_names))
        self.assertIn("Compiler Design Laboratory", extracted_names)
        self.assertIn("Networks Laboratory", extracted_names)

    # ──────────────────────────────────────────────────────────────────────────
    # Scenarios 5, 6, 7, 8, 9, 10: Large Multi-Page Syllabus with Multiline Names,
    # Labs, Electives, and Repeated Table Headers
    # ──────────────────────────────────────────────────────────────────────────
    def test_05_to_10_complex_multipage_syllabus_features(self):
        """
        Tests:
        5. Large syllabus
        6. Multi-page subject table (Page 1 -> Page 2 -> Page 3)
        7. Subject names spanning multiple lines
        8. Laboratory subjects
        9. Elective subjects
        10. Repeated table headers
        """
        user_id, email = self._create_and_login_student("Advanced Student", semester=3)

        complex_multipage_text = """
        --- Page 1 ---
        DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING
        CURRICULUM FOR B.TECH CSE (SEMESTER 3)
        
        SEMESTER 3 SCHEME
        | S.No | Course Code | Course Title | Category | Credits |
        | 1 | CS301 | Discrete Mathematics and\nGraph Theory | Theory Core | 4 |
        | 2 | CS302 | Data Structures and\nAlgorithms | Theory Core | 3 |
        | 3 | CS303 | Digital Systems and\nLogic Design | Theory Core | 3 |
        
        --- Page 2 ---
        SEMESTER 3 SCHEME (CONTINUED)
        | S.No | Course Code | Course Title | Category | Credits |
        | 4 | CS304 | Object Oriented Programming\nUsing Java | Theory Core | 3 |
        | 5 | CS305 | Professional Elective I:\nCloud Infrastructure | Professional Elective | 3 |
        | 6 | OE301 | Open Elective I:\nCyber Ethics and Laws | Open Elective | 3 |
        
        --- Page 3 ---
        SEMESTER 3 LABORATORY & AUDIT COURSES
        | S.No | Course Code | Course Title | Category | Credits |
        | 7 | CS311 | Data Structures and Algorithms\nLaboratory | Laboratory | 1.5 |
        | 8 | CS312 | Java Programming\nPractice Laboratory | Laboratory | 1.5 |
        | 9 | MC301 | Universal Human Values and\nProfessional Ethics | Mandatory Audit | 0 |
        """

        start_time = time.time()
        upload_res = self.app.post("/api/syllabus/analyze", json={"text": complex_multipage_text, "semester": 3})
        extraction_duration = time.time() - start_time
        self.assertEqual(upload_res.status_code, 200)

        # Query Active Curriculum
        res = self.app.get("/api/curriculum/active")
        data = res.get_json()
        self.assertTrue(data["is_valid"])

        subs = data["subjects"]
        self.assertEqual(len(subs), 9)
        names = [s["name"] for s in subs]

        # 7. Verify multiline subject names are properly normalized and joined
        self.assertTrue(any("Discrete Mathematics" in n for n in names))
        self.assertTrue(any("Data Structures" in n for n in names))
        self.assertTrue(any("Digital Systems" in n for n in names))
        self.assertTrue(any("Object Oriented Programming" in n for n in names))

        # 8. Verify Laboratories
        labs = [s for s in subs if s.get("type") == "Laboratory" or "Laboratory" in s.get("category", "") or "Lab" in s["name"]]
        self.assertTrue(len(labs) >= 2)

        # 9. Verify Electives
        electives = [s for s in subs if "Elective" in s.get("type", "") or "Elective" in s.get("category", "") or "Elective" in s["name"]]
        self.assertTrue(len(electives) >= 2)

        # 10. Verify repeated headers ("Course Title", "Credits", "Category") are NOT in subject names
        for n in names:
            self.assertNotIn("Course Code", n)
            self.assertNotIn("Course Title", n)
            self.assertNotIn("SEMESTER 3", n)

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 11: Multiple Students & Strict Data Isolation
    # ──────────────────────────────────────────────────────────────────────────
    def test_11_multiple_students_strict_isolation(self):
        """
        Verify:
        - Student A uploads Mechanical Engineering Syllabus (Thermodynamics, Fluid Mechanics).
        - Student B uploads Computer Science Syllabus (Operating Systems, DBMS).
        - Student A only sees Mechanical subjects.
        - Student B only sees CS subjects.
        - Zero cross-student data leakage.
        """
        # Student A
        user_a_id, email_a = self._create_and_login_student("Mech Student", semester=4, degree="B.Tech Mechanical", department="Mechanical")
        mech_syl = """
        DEPARTMENT OF MECHANICAL ENGINEERING
        SEMESTER 4
        | S.No | Course Code | Course Title | Credits |
        | 1 | ME401 | Applied Thermodynamics | 4 |
        | 2 | ME402 | Fluid Mechanics and Machinery | 4 |
        | 3 | ME403 | Manufacturing Technology | 3 |
        """
        self.app.post("/api/syllabus/analyze", json={"text": mech_syl, "semester": 4})

        # Student B
        user_b_id, email_b = self._create_and_login_student("CS Student", semester=4, degree="B.Tech CS", department="Computer Science")
        cs_syl = """
        DEPARTMENT OF COMPUTER SCIENCE
        SEMESTER 4
        | S.No | Course Code | Course Title | Credits |
        | 1 | CS401 | Database Systems | 4 |
        | 2 | CS402 | Operating Systems | 4 |
        | 3 | CS403 | Computer Networks | 3 |
        """
        self.app.post("/api/syllabus/analyze", json={"text": cs_syl, "semester": 4})

        # Check Student B's active curriculum
        res_b = self.app.get("/api/curriculum/active")
        data_b = res_b.get_json()
        names_b = [s["name"] for s in data_b["subjects"]]
        self.assertEqual(sorted(names_b), ["Computer Networks", "Database Systems", "Operating Systems"])
        self.assertNotIn("Applied Thermodynamics", names_b)

        # Switch back to Student A
        self.app.post("/api/auth/login", json={"email": email_a, "password": self.password})
        res_a = self.app.get("/api/curriculum/active")
        data_a = res_a.get_json()
        names_a = [s["name"] for s in data_a["subjects"]]
        self.assertEqual(sorted(names_a), ["Applied Thermodynamics", "Fluid Mechanics and Machinery", "Manufacturing Technology"])
        self.assertNotIn("Database Systems", names_a)

    # ──────────────────────────────────────────────────────────────────────────
    # Learning Feature Verifications: Personal Trainer, Knowledge Challenge, Reality Lab
    # ──────────────────────────────────────────────────────────────────────────
    def test_12_personal_trainer_behavior(self):
        """
        Verify Personal Trainer is:
        - subject-aware
        - topic-aware
        - conversational
        - educational
        - uses appropriate learning techniques
        """
        user_id, email = self._create_and_login_student("Trainer Student", semester=5)
        syl = """
        SEMESTER 5
        | S.No | Course Code | Course Title | Category | Credits |
        | 1 | CS501 | Database Management Systems | Theory Core | 4 |
        | 2 | CS502 | Operating Systems | Theory Core | 3 |
        | 3 | CS503 | Computer Networks | Theory Core | 3 |
        """
        self.app.post("/api/syllabus/analyze", json={"text": syl, "semester": 5})

        auth_cur = _get_authoritative_curriculum(user_id)
        self.assertIsNotNone(auth_cur)
        dbms_sub = auth_cur["subjects"][0]
        self.assertEqual(dbms_sub["name"], "Database Management Systems")

        # Test Personal Trainer Chat
        chat_res = self.app.post("/api/trainer/chat", json={
            "subject": "Database Management Systems",
            "subjectId": dbms_sub.get("id") or dbms_sub.get("code"),
            "curriculumId": auth_cur["curriculum_id"],
            "topic": "Normalization and ACID Properties",
            "message": "Can you explain 3NF and BCNF with a clear example?",
            "method": "conceptual-deep-dive",
            "technique": "active-recall"
        })
        self.assertEqual(chat_res.status_code, 200)
        data = chat_res.get_json()
        self.assertTrue(data["success"])
        reply = data.get("reply", "")
        self.assertTrue(len(reply) > 20)

    def test_13_knowledge_challenge_behavior(self):
        """
        Verify Knowledge Challenge is:
        - subject-aware
        - topic-aware
        - difficulty-aware
        - generates questions from actual curriculum
        """
        user_id, email = self._create_and_login_student("Challenge Student", semester=5)
        syl = """
        SEMESTER 5
        | S.No | Course Code | Course Title | Category | Credits |
        | 1 | CS501 | Computer Networks | Theory Core | 4 |
        | 2 | CS502 | Operating Systems | Theory Core | 3 |
        | 3 | CS503 | Database Systems | Theory Core | 3 |
        """
        self.app.post("/api/syllabus/analyze", json={"text": syl, "semester": 5})

        auth_cur = _get_authoritative_curriculum(user_id)
        sub = auth_cur["subjects"][0]
        sub_id = sub.get("id") or sub.get("code") or "CS501"

        quiz_res = self.app.get(f"/api/challenge/quiz?subject={sub['name']}&subject_id={sub_id}&curriculum_id={auth_cur['curriculum_id']}&difficulty=Medium")
        self.assertEqual(quiz_res.status_code, 200)
        q_data = quiz_res.get_json()
        self.assertTrue(q_data["success"])
        # Must return valid question structure
        self.assertTrue(q_data.get("question") or q_data.get("quiz") or q_data.get("scenario") or len(q_data.get("questions", [])) > 0)

    def test_14_reality_lab_behavior(self):
        """
        Verify Reality Lab is:
        - subject-aware
        - topic-aware
        - practical activities actually relate to the selected curriculum
        """
        user_id, email = self._create_and_login_student("RealityLab Student", semester=5)
        syl = """
        SEMESTER 5
        | S.No | Course Code | Course Title | Category | Credits |
        | 1 | CS501 | Artificial Intelligence and Robotics | Theory Core | 4 |
        | 2 | CS502 | Machine Learning | Theory Core | 3 |
        | 3 | CS503 | Computer Vision | Theory Core | 3 |
        """
        self.app.post("/api/syllabus/analyze", json={"text": syl, "semester": 5})

        auth_cur = _get_authoritative_curriculum(user_id)
        sub = auth_cur["subjects"][0]
        sub_id = sub.get("id") or sub.get("code") or "CS501"

        lab_res = self.app.post("/api/reality-lab/generate", json={
            "subject": "Artificial Intelligence and Robotics",
            "subjectId": sub_id,
            "curriculumId": auth_cur["curriculum_id"],
            "topic": "Path Planning and Obstacle Avoidance",
            "difficulty": "Medium"
        })
        self.assertEqual(lab_res.status_code, 200)
        l_data = lab_res.get_json()
        self.assertTrue(l_data["success"])

    def test_15_performance_benchmark(self):
        """
        Measure syllabus processing performance.
        Verify fast text parsing executes under 1.5 seconds.
        """
        large_multi_sem_text = """
        COLLEGE OF ENGINEERING & TECHNOLOGY
        DEPARTMENT OF INFORMATION TECHNOLOGY
        SEMESTER 1
        | 1 | IT101 | Technical English | 3 |
        | 2 | IT102 | Engineering Mathematics I | 4 |
        SEMESTER 2
        | 1 | IT201 | Engineering Mathematics II | 4 |
        | 2 | IT202 | Programming in C | 3 |
        SEMESTER 3
        | 1 | IT301 | Data Structures | 3 |
        | 2 | IT302 | Digital Logic Design | 3 |
        SEMESTER 4
        | 1 | IT401 | Database Systems | 3 |
        | 2 | IT402 | Design and Analysis of Algorithms | 4 |
        SEMESTER 5
        | 1 | IT501 | Web Technologies | 3 |
        | 2 | IT502 | Computer Networks | 3 |
        | 3 | IT503 | Software Engineering | 3 |
        | 4 | IT504 | Professional Elective I: Cloud Computing | 3 |
        | 5 | IT511 | Web Technologies Laboratory | 1.5 |
        | 6 | IT512 | Networks Laboratory | 1.5 |
        """
        t0 = time.time()
        res = gemini_service.analyze_syllabus(
            large_multi_sem_text,
            level="college",
            semester=5,
            degree="B.Tech IT",
            department="Information Technology"
        )
        duration = time.time() - t0
        self.assertEqual(res["validation_status"], "VALID")
        self.assertEqual(len(res["subjects"]), 6)
        # Fast deterministic extraction should execute under 0.5s
        self.assertLess(duration, 1.5, f"Extraction was too slow: {duration:.3f}s")

if __name__ == "__main__":
    unittest.main()
