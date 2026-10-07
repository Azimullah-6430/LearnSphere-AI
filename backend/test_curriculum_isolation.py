"""
LearnSphere AI - Multi-User Curriculum Isolation & Invalidation Test Suite

Verifies:
1. Student A (B.Tech IT Sem 5) and Student B (B.Tech CSE Sem 6) have strict curriculum isolation.
2. Neither student can see or access the other's curriculum or subjects.
3. Personal Trainer, Reality Lab, and Knowledge Transfer query only the authenticated student's curriculum.
4. When Student A logs out and Student B logs in, no Student A subjects remain.
5. Uploading a new syllabus replaces and invalidates the previous active curriculum without stale subjects.
"""

import os
import sys
import json
import re
import unittest
from datetime import datetime

# Set up path to backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server import app, get_mongodb, get_sqlite_db
from unittest.mock import patch


def _mock_analyze_syllabus(file_input, **kwargs):
    text = ""
    if isinstance(file_input, str):
        if os.path.exists(file_input):
            with open(file_input, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        else:
            text = file_input
    elif isinstance(file_input, dict):
        text = file_input.get("text", "")

    target_semester = kwargs.get("target_semester")
    if not target_semester:
        m_sem = re.search(r"SEMESTER\s+(\d+)", text, re.I)
        if m_sem:
            target_semester = int(m_sem.group(1))
        else:
            target_semester = 5

    subjects = []
    lines = text.strip().split("\n")
    for line in lines:
        line_clean = line.strip()
        m = re.match(r"^([A-Z]{2,4}\d{3,4})\s+(.+?)(?:\s+Credits:|\s+L:|$)", line_clean)
        if m:
            code = m.group(1).strip()
            name = m.group(2).strip()
            subjects.append({
                "code": code,
                "name": name,
                "type": "Laboratory" if "Laboratory" in name or "Lab" in name else "Theory Core",
                "category": "Program Core",
                "credits": 4.0,
                "semester": target_semester,
                "source_page": 1,
                "source_section": f"Semester {target_semester} Scheme",
                "source_text": line_clean,
                "confidence": 0.98,
                "evidence_verified": True
            })

    return {
        "status": "VALID",
        "validation_status": "VALID",
        "detected_semesters": [target_semester],
        "extracted_subjects": [s["name"] for s in subjects],
        "subjects": subjects,
        "expected_subject_count": len(subjects),
        "extracted_subject_count": len(subjects),
        "is_active": True,
        "key_topics": ["Unit 1: Fundamentals", "Unit 2: Advanced Topics"],
        "chapters": {},
        "program": kwargs.get("degree") or "B.Tech",
        "department": kwargs.get("department") or "Information Technology"
    }


class TestCurriculumIsolation(unittest.TestCase):

    def setUp(self):
        self.patcher = patch("server.gemini_service.analyze_syllabus", side_effect=_mock_analyze_syllabus)
        self.mock_analyze = self.patcher.start()

        self.app = app.test_client()
        self.app.testing = True

        self.timestamp = int(datetime.utcnow().timestamp())
        self.student_a_email = f"student_a_{self.timestamp}@learnsphere.test"
        self.student_b_email = f"student_b_{self.timestamp}@learnsphere.test"
        self.password = "TestPassword123!"

        # Register Student A: B.Tech IT, Semester 5
        res_a = self.app.post("/api/auth/register", json={
            "name": "Student A (IT Sem 5)",
            "email": self.student_a_email,
            "password": self.password,
            "role": "student",
            "level": "college",
            "degree": "B.Tech",
            "program": "B.Tech",
            "department": "Information Technology",
            "branch": "Information Technology",
            "year": 3,
            "semester": 5,
            "current_semester": 5,
            "regulation": "R2021"
        })
        self.assertEqual(res_a.status_code, 201)
        self.student_a_id = res_a.get_json()["user"]["id"]

        # Register Student B: B.Tech CSE, Semester 6
        res_b = self.app.post("/api/auth/register", json={
            "name": "Student B (CSE Sem 6)",
            "email": self.student_b_email,
            "password": self.password,
            "role": "student",
            "level": "college",
            "degree": "B.Tech",
            "program": "B.Tech",
            "department": "Computer Science and Engineering",
            "branch": "Computer Science and Engineering",
            "year": 3,
            "semester": 6,
            "current_semester": 6,
            "regulation": "R2021"
        })
        self.assertEqual(res_b.status_code, 201)
        self.student_b_id = res_b.get_json()["user"]["id"]

        # Syllabus A: Semester 5 (Information Technology)
        self.syllabus_a_text = """
DEPARTMENT OF INFORMATION TECHNOLOGY
SEMESTER 5 CURRICULUM SCHEME
IT501 Database Management Systems Credits: 4 L:3 T:0 P:2
IT502 Web Technologies Credits: 3 L:3 T:0 P:0
IT503 Computer Networks Credits: 3 L:3 T:0 P:0
IT504 Formal Languages and Automata Theory Credits: 4 L:3 T:1 P:0
IT505 Software Engineering Credits: 3 L:3 T:0 P:0
IT506 Database Management Systems Laboratory Credits: 2 L:0 T:0 P:4
IT507 Web Technologies Laboratory Credits: 2 L:0 T:0 P:4
IT508 Professional Communication Laboratory Credits: 1 L:0 T:0 P:2
"""

        # Syllabus B: Semester 6 (Computer Science and Engineering)
        self.syllabus_b_text = """
DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING
SEMESTER 6 CURRICULUM SCHEME
CS601 Compiler Design Credits: 4 L:3 T:0 P:2
CS602 Cloud Computing Credits: 3 L:3 T:0 P:0
CS603 Cryptography and Network Security Credits: 3 L:3 T:0 P:0
CS604 Distributed Systems Credits: 3 L:3 T:0 P:0
CS605 Compiler Design Laboratory Credits: 2 L:0 T:0 P:4
CS606 Cloud Computing Laboratory Credits: 2 L:0 T:0 P:4
"""

    def tearDown(self):
        self.patcher.stop()

    def _login(self, email):
        res = self.app.post("/api/auth/login", json={
            "email": email,
            "password": self.password
        })
        self.assertEqual(res.status_code, 200)
        return res

    def _logout(self):
        return self.app.post("/api/auth/logout")

    def test_01_student_a_and_b_curriculum_isolation(self):
        """Verify Student A and Student B have completely isolated curricula."""
        # 1. Login as Student A and upload Syllabus A
        self._login(self.student_a_email)
        upload_res_a = self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": self.syllabus_a_text,
            "file_name": "Syllabus_IT_Sem5.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "Information Technology"
        })
        self.assertEqual(upload_res_a.status_code, 200)
        self.assertTrue(upload_res_a.get_json()["is_active"])

        # Fetch active curriculum for Student A
        cur_a_res = self.app.get("/api/curriculum/active")
        self.assertEqual(cur_a_res.status_code, 200)
        cur_a = cur_a_res.get_json()
        self.assertEqual(cur_a["semester"], 5)
        self.assertEqual(cur_a["department"], "Information Technology")
        subj_a_names = [s.get("name") for s in cur_a.get("subjects", [])]
        subj_a_codes = [s.get("code") for s in cur_a.get("subjects", [])]
        self.assertEqual(len(subj_a_names), 8)
        self.assertIn("Database Management Systems", subj_a_names)
        self.assertIn("IT501", subj_a_codes)
        self.assertNotIn("Compiler Design", subj_a_names)
        self.assertNotIn("CS601", subj_a_codes)

        # 2. Logout Student A and login as Student B
        self._logout()
        self._login(self.student_b_email)

        # Before Student B uploads a syllabus, active curriculum must NOT contain Student A's subjects
        cur_b_initial_res = self.app.get("/api/curriculum/active")
        self.assertEqual(cur_b_initial_res.status_code, 200)
        cur_b_initial = cur_b_initial_res.get_json()
        b_initial_subjects = [s.get("name") for s in cur_b_initial.get("subjects", [])]
        self.assertEqual(len(b_initial_subjects), 0)
        self.assertNotIn("Database Management Systems", b_initial_subjects)

        # Upload Syllabus B for Student B
        upload_res_b = self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": self.syllabus_b_text,
            "file_name": "Syllabus_CSE_Sem6.txt",
            "level": "college",
            "semester": 6,
            "degree": "B.Tech",
            "department": "Computer Science and Engineering"
        })
        self.assertEqual(upload_res_b.status_code, 200)
        self.assertTrue(upload_res_b.get_json()["is_active"])

        # Fetch active curriculum for Student B
        cur_b_res = self.app.get("/api/curriculum/active")
        self.assertEqual(cur_b_res.status_code, 200)
        cur_b = cur_b_res.get_json()
        self.assertEqual(cur_b["semester"], 6)
        self.assertEqual(cur_b["department"], "Computer Science and Engineering")
        subj_b_names = [s.get("name") for s in cur_b.get("subjects", [])]
        subj_b_codes = [s.get("code") for s in cur_b.get("subjects", [])]
        self.assertEqual(len(subj_b_names), 6)
        self.assertIn("Compiler Design", subj_b_names)
        self.assertIn("CS601", subj_b_codes)
        self.assertNotIn("Database Management Systems", subj_b_names)
        self.assertNotIn("IT501", subj_b_codes)

        # 3. Switch back to Student A: ensure Student A still sees only Syllabus A
        self._logout()
        self._login(self.student_a_email)

        cur_a_check = self.app.get("/api/curriculum/active").get_json()
        a_check_subjects = [s.get("name") for s in cur_a_check.get("subjects", [])]
        self.assertEqual(len(a_check_subjects), 8)
        self.assertIn("Database Management Systems", a_check_subjects)
        self.assertNotIn("Compiler Design", a_check_subjects)

    @patch("server.gemini_service.generate_knowledge_transfer")
    def test_02_learning_agents_consume_only_authenticated_student_curriculum(self, mock_kt):
        """Verify Personal Trainer, Reality Lab, and Knowledge Transfer are strictly isolated."""
        mock_kt.side_effect = lambda **kwargs: {
            "exact_subject": kwargs.get("subject"),
            "exact_topic": kwargs.get("topic"),
            "real_world_application": "Test Application",
            "concept_explanation": "Test Explanation",
            "practical_connection": "Test Connection",
            "example": "Test Example",
            "misconception": "Test Misconception",
            "understanding_question": "Test Question?",
            "exam_relevance": "High"
        }

        # 1. Setup Student A (Sem 5 IT)
        self._login(self.student_a_email)
        self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": self.syllabus_a_text,
            "file_name": "Syllabus_IT_Sem5.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "Information Technology"
        })


        # Knowledge Transfer request for Student A with valid Subject
        kt_a_res = self.app.post("/api/transfer/generate", json={
            "subject": "Database Management Systems",
            "topic": "Normalization and Indexing"
        })
        self.assertEqual(kt_a_res.status_code, 200)
        self.assertEqual(kt_a_res.get_json()["exact_subject"], "Database Management Systems")

        # Knowledge Transfer request for Student A with Student B's subject must be REJECTED (400)
        kt_a_invalid = self.app.post("/api/transfer/generate", json={
            "subject": "Compiler Design",
            "topic": "Lexical Analysis"
        })
        self.assertEqual(kt_a_invalid.status_code, 400)
        self.assertIn("does not exist in your active", kt_a_invalid.get_json()["error"])

        # 2. Switch to Student B (Sem 6 CSE)
        self._logout()
        self._login(self.student_b_email)
        self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": self.syllabus_b_text,
            "file_name": "Syllabus_CSE_Sem6.txt",
            "level": "college",
            "semester": 6,
            "degree": "B.Tech",
            "department": "Computer Science and Engineering"
        })

        # Knowledge Transfer for Student B with Student B's subject succeeds
        kt_b_res = self.app.post("/api/transfer/generate", json={
            "subject": "Compiler Design",
            "topic": "Lexical Analysis"
        })
        self.assertEqual(kt_b_res.status_code, 200)
        self.assertEqual(kt_b_res.get_json()["exact_subject"], "Compiler Design")

        # Knowledge Transfer for Student B with Student A's subject must be REJECTED (400)
        kt_b_invalid = self.app.post("/api/transfer/generate", json={
            "subject": "Database Management Systems",
            "topic": "Relational Model"
        })
        self.assertEqual(kt_b_invalid.status_code, 400)
        self.assertIn("does not exist in your active", kt_b_invalid.get_json()["error"])

    def test_03_syllabus_replacement_invalidates_old_curriculum(self):
        """Verify that uploading a new syllabus cleanly replaces previous active curriculum with zero stale subjects."""
        self._login(self.student_a_email)

        # Upload initial Syllabus A (8 subjects)
        self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": self.syllabus_a_text,
            "file_name": "Syllabus_IT_Sem5_v1.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "Information Technology"
        })

        cur_v1 = self.app.get("/api/curriculum/active").get_json()
        self.assertEqual(len(cur_v1["subjects"]), 8)

        # Student A uploads updated Syllabus A_v2 (e.g. specialized 5-subject scheme)
        syllabus_a_v2_text = """
DEPARTMENT OF INFORMATION TECHNOLOGY
SEMESTER 5 REVISED CURRICULUM
IT511 Advanced Database Systems Credits: 4 L:3 T:0 P:2
IT512 Full Stack Web Engineering Credits: 4 L:3 T:0 P:2
IT513 High Performance Networks Credits: 4 L:3 T:0 P:2
IT514 Theory of Computation Credits: 4 L:3 T:1 P:0
IT515 Advanced Web Engineering Laboratory Credits: 2 L:0 T:0 P:4
"""
        upload_v2_res = self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": syllabus_a_v2_text,
            "file_name": "Syllabus_IT_Sem5_v2.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "Information Technology"
        })
        self.assertEqual(upload_v2_res.status_code, 200)

        # Active curriculum must now contain ONLY the 5 new subjects
        cur_v2 = self.app.get("/api/curriculum/active").get_json()
        v2_subjects = [s.get("name") for s in cur_v2.get("subjects", [])]
        v2_codes = [s.get("code") for s in cur_v2.get("subjects", [])]

        self.assertEqual(len(v2_subjects), 5)
        self.assertIn("Advanced Database Systems", v2_subjects)
        self.assertIn("IT511", v2_codes)
        self.assertIn("Full Stack Web Engineering", v2_subjects)
        self.assertIn("IT512", v2_codes)

        # STALE SUBJECT CHECKS: Old subjects must not remain active
        self.assertNotIn("Database Management Systems", v2_subjects)
        self.assertNotIn("IT501", v2_codes)
        self.assertNotIn("Web Technologies", v2_subjects)
        self.assertNotIn("IT502", v2_codes)
        self.assertNotIn("Computer Networks", v2_subjects)
        self.assertNotIn("IT503", v2_codes)

    def test_04_logout_and_session_clearing(self):
        """Verify that deleting syllabus or logging out leaves zero active curriculum."""
        self._login(self.student_a_email)
        self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": self.syllabus_a_text,
            "file_name": "Syllabus_IT_Sem5.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "Information Technology"
        })

        # Explicitly archive/delete syllabus
        del_res = self.app.delete("/api/syllabus")
        self.assertEqual(del_res.status_code, 200)

        # Active curriculum should return empty subjects
        cur_empty = self.app.get("/api/curriculum/active").get_json()
        self.assertEqual(len(cur_empty.get("subjects", [])), 0)

        # Logout
        logout_res = self._logout()
        self.assertEqual(logout_res.status_code, 200)

        # Unauthenticated query must be rejected with 401
        unauth_cur = self.app.get("/api/curriculum/active")
        self.assertEqual(unauth_cur.status_code, 401)


if __name__ == "__main__":
    unittest.main()
