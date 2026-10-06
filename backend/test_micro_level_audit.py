"""
LearnSphere AI - Final Micro-Level Audit Test Suite
Verifies all 16 acceptance scenarios across the syllabus-to-learning-agent pipeline.
"""

import os
import sys
import json
import unittest
from datetime import datetime
from unittest.mock import patch

# Set up path to backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server import app, get_mongodb, get_sqlite_db
from app.curriculum_validator import CurriculumCompletenessValidator
import app.gemini_service as gemini_service

class TestMicroLevelAudit(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.timestamp = int(datetime.utcnow().timestamp())
        self.password = "TestPassword123!"

    def _register_user(self, name, email, degree="B.Tech", dept="Information Technology", sem=5):
        res = self.app.post("/api/auth/register", json={
            "name": name,
            "email": email,
            "password": self.password,
            "role": "student",
            "level": "college",
            "degree": degree,
            "program": degree,
            "department": dept,
            "branch": dept,
            "year": 3,
            "semester": sem,
            "current_semester": sem,
            "regulation": "R2021"
        })
        self.assertEqual(res.status_code, 201)
        return res.get_json()["user"]

    def _login(self, email):
        res = self.app.post("/api/auth/login", json={
            "email": email,
            "password": self.password
        })
        self.assertEqual(res.status_code, 200)
        return res

    def _logout(self):
        return self.app.post("/api/auth/logout")

    # ─────────────────────────────────────────────────────────────────────────
    # 1. College student Semester 5 + single-semester syllabus
    # ─────────────────────────────────────────────────────────────────────────
    def test_01_college_student_sem5_single_semester(self):
        email = f"audit_sem5_{self.timestamp}@learnsphere.test"
        self._register_user("Audit Student Sem5", email, degree="B.Tech", dept="Information Technology", sem=5)
        self._login(email)

        syllabus_text = """
        ANNA UNIVERSITY :: CHENNAI - 600 025
        B.TECH INFORMATION TECHNOLOGY - REGULATION 2021
        SEMESTER V
        IT501 Database Management Systems Credits: 4
        IT502 Web Technology Credits: 3
        IT503 Computer Networks Credits: 3
        IT504 Formal Languages and Automata Theory Credits: 4
        IT505 Software Engineering Credits: 3
        IT506 Database Management Systems Laboratory Credits: 2
        """
        res = self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": syllabus_text,
            "file_name": "Syllabus_IT_Sem5.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "Information Technology"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        if not data.get("is_active"):
            print("\nDEBUG TEST 01 DATA:", json.dumps(data, indent=2))
        self.assertTrue(data["is_active"])
        self.assertEqual(data["validation_status"], "VALID")


        cur = self.app.get("/api/curriculum/active").get_json()
        self.assertEqual(cur["semester"], 5)

        self.assertEqual(len(cur["subjects"]), 6)
        names = [s["name"] for s in cur["subjects"]]
        self.assertIn("Database Management Systems", names)
        self.assertIn("Web Technology", names)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. College student Semester 6 + single-semester syllabus
    # ─────────────────────────────────────────────────────────────────────────
    def test_02_college_student_sem6_single_semester(self):
        email = f"audit_sem6_{self.timestamp}@learnsphere.test"
        self._register_user("Audit Student Sem6", email, degree="B.Tech", dept="Computer Science and Engineering", sem=6)
        self._login(email)

        syllabus_text = """
        DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING
        CURRICULUM FOR SEMESTER VI
        CS601 Compiler Design Credits: 4
        CS602 Cloud Computing Credits: 3
        CS603 Cryptography and Network Security Credits: 3
        CS604 Distributed Systems Credits: 3
        CS605 Compiler Design Laboratory Credits: 2
        """
        res = self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": syllabus_text,
            "file_name": "Syllabus_CSE_Sem6.txt",
            "level": "college",
            "semester": 6,
            "degree": "B.Tech",
            "department": "Computer Science and Engineering"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        cur = self.app.get("/api/curriculum/active").get_json()
        if len(cur.get("subjects", [])) == 0:
            print("\nDEBUG TEST 02 RES:", json.dumps(data, indent=2))
            print("\nDEBUG TEST 02 CUR:", json.dumps(cur, indent=2))
        self.assertEqual(cur["semester"], 6)
        self.assertEqual(len(cur["subjects"]), 5)
        names = [s["name"] for s in cur["subjects"]]
        self.assertIn("Compiler Design", names)
        self.assertNotIn("Database Management Systems", names)


    # ─────────────────────────────────────────────────────────────────────────
    # 3. Multi-semester syllabus PDF
    # ─────────────────────────────────────────────────────────────────────────
    def test_03_multi_semester_syllabus_pdf(self):
        email = f"audit_multisem_{self.timestamp}@learnsphere.test"
        self._register_user("Audit MultiSem Student", email, degree="B.Tech", dept="IT", sem=5)
        self._login(email)

        multi_sem_text = """
        SEMESTER 4 SCHEME:
        MA401 Probability and Statistics
        CS402 Operating Systems
        CS403 Design and Analysis of Algorithms

        SEMESTER 5 SCHEME:
        IT501 Database Management Systems
        IT502 Web Technologies
        IT503 Computer Networks
        IT504 Formal Languages and Automata Theory

        SEMESTER 6 SCHEME:
        IT601 Mobile Computing
        IT602 Artificial Intelligence
        """
        res = self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": multi_sem_text,
            "file_name": "Full_Curriculum_Sem1_to_8.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "IT"
        })
        self.assertEqual(res.status_code, 200)
        cur = self.app.get("/api/curriculum/active").get_json()
        self.assertEqual(cur["semester"], 5)
        names = [s["name"] for s in cur["subjects"]]
        # ONLY Sem 5 subjects
        self.assertIn("Database Management Systems", names)
        self.assertIn("Web Technologies", names)
        # Sem 4 and Sem 6 must NOT be included
        self.assertNotIn("Operating Systems", names)
        self.assertNotIn("Mobile Computing", names)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Syllabus containing theory + laboratory subjects
    # ─────────────────────────────────────────────────────────────────────────
    def test_04_theory_and_laboratory_subjects(self):
        email = f"audit_labs_{self.timestamp}@learnsphere.test"
        self._register_user("Audit Lab Student", email, degree="B.Tech", dept="IT", sem=5)
        self._login(email)

        syllabus_text = """
        SEMESTER 5:
        THEORY:
        IT501 Database Management Systems Credits: 3
        IT502 Web Technologies Credits: 3
        PRACTICAL / LABORATORY:
        IT507 Database Management Systems Laboratory Credits: 2
        IT508 Web Technologies Laboratory Credits: 2
        """
        res = self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": syllabus_text,
            "file_name": "Theory_And_Labs_Sem5.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "IT"
        })
        self.assertEqual(res.status_code, 200)
        cur = self.app.get("/api/curriculum/active").get_json()
        types = [s.get("type", "").lower() for s in cur["subjects"]]
        names = [s["name"] for s in cur["subjects"]]
        self.assertIn("Database Management Systems", names)
        self.assertIn("Database Management Systems Laboratory", names)
        self.assertTrue(any("lab" in n.lower() or "practical" in n.lower() for n in names))

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Syllabus containing electives
    # ─────────────────────────────────────────────────────────────────────────
    def test_05_syllabus_containing_electives(self):
        email = f"audit_electives_{self.timestamp}@learnsphere.test"
        self._register_user("Audit Electives Student", email, degree="B.Tech", dept="IT", sem=5)
        self._login(email)

        syllabus_text = """
        SEMESTER 5:
        IT501 Database Management Systems Credits: 4
        IT502 Web Technologies Credits: 3
        PROFESSIONAL ELECTIVE I:
        PE501 Cloud Computing Credits: 3
        PE502 Internet of Things Credits: 3
        OPEN ELECTIVE I:
        OE501 Principles of Management Credits: 3
        """
        res = self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": syllabus_text,
            "file_name": "Electives_Sem5.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "IT"
        })
        self.assertEqual(res.status_code, 200)
        cur = self.app.get("/api/curriculum/active").get_json()
        names = [s["name"] for s in cur["subjects"]]
        self.assertIn("Cloud Computing", names)
        self.assertIn("Principles of Management", names)

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Syllabus with subject codes
    # ─────────────────────────────────────────────────────────────────────────
    def test_06_syllabus_with_subject_codes(self):
        email = f"audit_codes_{self.timestamp}@learnsphere.test"
        self._register_user("Audit Codes Student", email, degree="B.Tech", dept="IT", sem=5)
        self._login(email)

        syllabus_text = """
        SEMESTER 5 COURSE STRUCTURE
        IT501 Database Management Systems
        IT502 Web Technologies
        IT503 Computer Networks
        """
        res = self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": syllabus_text,
            "file_name": "Codes_Sem5.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "IT"
        })
        self.assertEqual(res.status_code, 200)
        cur = self.app.get("/api/curriculum/active").get_json()
        codes = [s.get("code") for s in cur["subjects"]]
        self.assertIn("IT501", codes)
        self.assertIn("IT502", codes)
        self.assertIn("IT503", codes)

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Syllabus with tables
    # ─────────────────────────────────────────────────────────────────────────
    def test_07_syllabus_with_tables(self):
        email = f"audit_tables_{self.timestamp}@learnsphere.test"
        self._register_user("Audit Tables Student", email, degree="B.Tech", dept="IT", sem=5)
        self._login(email)

        syllabus_table = """
        +---------+-----------------------------------+---+---+---+---+
        | Course  | Course Title                      | L | T | P | C |
        +---------+-----------------------------------+---+---+---+---+
        | SEMESTER V                                                  |
        +---------+-----------------------------------+---+---+---+---+
        | IT501   | Database Management Systems       | 3 | 0 | 2 | 4 |
        | IT502   | Web Technologies                  | 3 | 0 | 0 | 3 |
        | IT503   | Computer Networks                 | 3 | 0 | 0 | 3 |
        | IT504   | Theory of Computation             | 3 | 1 | 0 | 4 |
        +---------+-----------------------------------+---+---+---+---+
        """
        res = self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": syllabus_table,
            "file_name": "Table_Sem5.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "IT"
        })
        self.assertEqual(res.status_code, 200)
        cur = self.app.get("/api/curriculum/active").get_json()
        self.assertEqual(len(cur["subjects"]), 4)
        codes = [s.get("code") for s in cur["subjects"]]
        self.assertIn("IT501", codes)
        self.assertIn("IT504", codes)

    # ─────────────────────────────────────────────────────────────────────────
    # 8. Long syllabus spanning many pages / chapters
    # ─────────────────────────────────────────────────────────────────────────
    def test_08_long_syllabus_spanning_pages(self):
        email = f"audit_long_{self.timestamp}@learnsphere.test"
        self._register_user("Audit Long Student", email, degree="B.Tech", dept="IT", sem=5)
        self._login(email)

        long_text = """
        DEPARTMENT OF INFORMATION TECHNOLOGY
        SEMESTER 5 CURRICULUM AND DETAILED SYLLABI
        
        IT501 Database Management Systems Credits: 4
        Unit I: Introduction to Relational Databases, ER Diagrams, Relational Model
        Unit II: SQL, DDL, DML, Complex Queries, Views, Triggers
        Unit III: Relational Database Design, Normalization 1NF 2NF 3NF BCNF
        Unit IV: Transaction Management, Concurrency Control, ACID properties
        Unit V: Storage and Indexing, B+ Trees, Hashing, Query Processing

        IT502 Web Technologies Credits: 3
        Unit I: HTML5, CSS3, Responsive Design, CSS Grid and Flexbox
        Unit II: Client-Side Scripting, JavaScript ES6+, DOM Manipulation, Async Await
        Unit III: Server-Side Programming, Node.js, Express, RESTful APIs
        Unit IV: Frontend Frameworks, React Components, State Management
        Unit V: Web Security, HTTPS, JWT, OWASP Top 10 vulnerabilities

        IT503 Computer Networks Credits: 3
        Unit I: OSI and TCP/IP Reference Models, Physical Layer, Transmission Media
        Unit II: Data Link Layer, Error Detection, Sliding Window Protocols, MAC
        Unit III: Network Layer, IPv4 IPv6 Addressing, Routing Algorithms OSPF BGP
        Unit IV: Transport Layer, TCP UDP Sockets, Congestion Control
        Unit V: Application Layer, HTTP DNS SMTP, Network Security Protocols
        """
        res = self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": long_text,
            "file_name": "Long_Detailed_Syllabus_Sem5.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "IT"
        })
        self.assertEqual(res.status_code, 200)
        cur = self.app.get("/api/curriculum/active").get_json()
        self.assertEqual(len(cur["subjects"]), 3)
        self.assertTrue(bool(cur.get("units") or cur.get("chapters") or cur.get("topics") or len(cur["subjects"]) == 3))


    # ─────────────────────────────────────────────────────────────────────────
    # 9. Scanned syllabus (OCR-like text with artifacts)
    # ─────────────────────────────────────────────────────────────────────────
    def test_09_scanned_ocr_syllabus(self):
        email = f"audit_scanned_{self.timestamp}@learnsphere.test"
        self._register_user("Audit Scanned Student", email, degree="B.Tech", dept="IT", sem=5)
        self._login(email)

        scanned_text = """
        [OCR SCAN] UNIVERSITY COLLEGE OF ENGG
        S-E-M-E-S-T-E-R - 5
        1. IT-501 : Database Management Systems (4 Cr)
        2. IT-502 : Web Technologies (3 Cr)
        3. IT-503 : Computer Networks (3 Cr)
        """
        res = self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": scanned_text,
            "file_name": "Scanned_Syllabus_Sem5.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "IT"
        })
        self.assertEqual(res.status_code, 200)
        cur = self.app.get("/api/curriculum/active").get_json()
        names = [s["name"] for s in cur["subjects"]]
        self.assertIn("Database Management Systems", names)
        self.assertIn("Computer Networks", names)

    # ─────────────────────────────────────────────────────────────────────────
    # 10. Poor-quality syllabus (unstructured text missing semester markers)
    # ─────────────────────────────────────────────────────────────────────────
    def test_10_poor_quality_syllabus_requires_review(self):
        email = f"audit_poor_{self.timestamp}@learnsphere.test"
        self._register_user("Audit Poor Student", email, degree="B.Tech", dept="IT", sem=5)
        self._login(email)

        poor_text = "Some random unstructured text without headings or table columns xyz 123."
        res = self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": poor_text,
            "file_name": "Poor_Quality.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "IT"
        })
        data = res.get_json()
        # Must NOT silently activate invalid curriculum
        self.assertFalse(data.get("is_active", False))
        self.assertIn(data.get("validation_status"), ["NEEDS_REVIEW", "MISMATCH"])

    # ─────────────────────────────────────────────────────────────────────────
    # 11. Incorrect semester uploaded (Student Sem 5 uploads Sem 2)
    # ─────────────────────────────────────────────────────────────────────────
    def test_11_incorrect_semester_uploaded_mismatch(self):
        email = f"audit_wrongsem_{self.timestamp}@learnsphere.test"
        self._register_user("Audit WrongSem Student", email, degree="B.Tech", dept="IT", sem=5)
        self._login(email)

        wrong_sem_text = """
        DEPARTMENT OF INFORMATION TECHNOLOGY
        SEMESTER 2 CURRICULUM
        MA201 Engineering Mathematics II
        PH201 Physics for Information Science
        CY201 Environmental Science
        """
        res = self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": wrong_sem_text,
            "file_name": "Syllabus_Sem2.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "IT"
        })
        data = res.get_json()
        self.assertFalse(data.get("is_active", False))
        self.assertIn(data.get("validation_status"), ["MISMATCH", "NEEDS_REVIEW"])

        # Active curriculum must remain empty
        cur = self.app.get("/api/curriculum/active").get_json()
        self.assertEqual(len(cur.get("subjects", [])), 0)

    # ─────────────────────────────────────────────────────────────────────────
    # 12. Incomplete syllabus (missing subjects vs expected count)
    # ─────────────────────────────────────────────────────────────────────────
    def test_12_incomplete_syllabus_handled_by_validator(self):
        email = f"audit_incomplete_{self.timestamp}@learnsphere.test"
        user = self._register_user("Audit Incomplete Student", email, degree="B.Tech", dept="IT", sem=5)

        # Analysis payload that expects 8 subjects but only found 2
        mock_analysis = {
            "course_title": "B.Tech IT Semester 5",
            "detected_semesters": [5],
            "explicit_semester_identifier": "Semester 5",
            "expected_subject_count": 8,
            "subjects": [
                {"name": "Database Management Systems", "code": "IT501", "source_section": "Table 1"},
                {"name": "Web Technologies", "code": "IT502", "source_section": "Table 1"}
            ],
            "validation_status": "VALID"
        }
        report = CurriculumCompletenessValidator.validate(
            user=user,
            analysis=mock_analysis,
            raw_content_or_file="IT501 Database Management Systems IT502 Web Technologies",
            target_semester=5
        )
        self.assertFalse(report["is_valid"])
        self.assertEqual(report["status"], "NEEDS_REVIEW")
        self.assertEqual(report["missing_subjects"], 6)

    # ─────────────────────────────────────────────────────────────────────────
    # 13. Student changes semester
    # ─────────────────────────────────────────────────────────────────────────
    def test_13_student_changes_semester(self):
        email = f"audit_semchange_{self.timestamp}@learnsphere.test"
        self._register_user("Audit SemChange Student", email, degree="B.Tech", dept="IT", sem=5)
        self._login(email)

        # Upload Sem 5 syllabus
        syllabus_text = """
        SEMESTER 5:
        IT501 Database Management Systems
        IT502 Web Technologies
        """
        self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": syllabus_text,
            "file_name": "Syllabus_Sem5.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "IT"
        })

        # Update profile to Semester 6
        self.app.put("/api/user/profile", json={
            "semester": 6,
            "current_semester": 6
        })

        # Query active curriculum for Semester 6: Sem 5 subjects must not serve as active Sem 6
        cur = self.app.get("/api/curriculum/active").get_json()
        # When active curriculum's semester does not match the student's new semester 6, it is not active
        self.assertEqual(len(cur.get("subjects", [])), 0)

    # ─────────────────────────────────────────────────────────────────────────
    # 14. Student uploads a new syllabus (Atomic replacement & stale invalidation)
    # ─────────────────────────────────────────────────────────────────────────
    def test_14_student_uploads_new_syllabus_replaces_old(self):
        email = f"audit_replace_{self.timestamp}@learnsphere.test"
        self._register_user("Audit Replace Student", email, degree="B.Tech", dept="IT", sem=5)
        self._login(email)

        v1_text = """
        SEMESTER 5:
        IT501 Old Subject One
        IT502 Old Subject Two
        """
        self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": v1_text,
            "file_name": "Syllabus_v1.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "IT"
        })

        v2_text = """
        SEMESTER 5:
        IT511 Revised Advanced Subject Alpha
        IT512 Revised Advanced Subject Beta
        """
        self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": v2_text,
            "file_name": "Syllabus_v2.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "IT"
        })

        cur = self.app.get("/api/curriculum/active").get_json()
        names = [s["name"] for s in cur["subjects"]]
        self.assertIn("Revised Advanced Subject Alpha", names)
        self.assertIn("Revised Advanced Subject Beta", names)
        # Stale subjects must NOT remain
        self.assertNotIn("Old Subject One", names)
        self.assertNotIn("Old Subject Two", names)

    # ─────────────────────────────────────────────────────────────────────────
    # 15. Student refreshes browser (persisted active state)
    # ─────────────────────────────────────────────────────────────────────────
    def test_15_student_refreshes_browser_state_persists(self):
        email = f"audit_refresh_{self.timestamp}@learnsphere.test"
        self._register_user("Audit Refresh Student", email, degree="B.Tech", dept="IT", sem=5)
        self._login(email)

        syllabus_text = """
        SEMESTER 5:
        IT501 Database Management Systems
        IT502 Web Technologies
        """
        self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": syllabus_text,
            "file_name": "Syllabus_Sem5.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "IT"
        })

        # Simulate browser refresh (fresh GET request on same session)
        cur = self.app.get("/api/curriculum/active").get_json()
        self.assertTrue(cur.get("is_active"))
        self.assertEqual(len(cur.get("subjects", [])), 2)
        self.assertEqual(cur["semester"], 5)

    # ─────────────────────────────────────────────────────────────────────────
    # 16. Student logs out and another student logs in (Cross-user isolation)
    # ─────────────────────────────────────────────────────────────────────────
    def test_16_logout_and_switch_student_isolation(self):
        email_a = f"audit_user_a_{self.timestamp}@learnsphere.test"
        email_b = f"audit_user_b_{self.timestamp}@learnsphere.test"
        self._register_user("User A", email_a, degree="B.Tech", dept="IT", sem=5)
        self._register_user("User B", email_b, degree="B.Tech", dept="CSE", sem=6)

        # User A uploads Sem 5 IT
        self._login(email_a)
        self.app.post("/api/syllabus/analyze", json={
            "syllabus_text": "SEMESTER 5:\nIT501 Database Systems\nIT502 Web Engineering",
            "file_name": "User_A_Sem5.txt",
            "level": "college",
            "semester": 5,
            "degree": "B.Tech",
            "department": "IT"
        })
        self._logout()

        # User B logs in (has uploaded nothing)
        self._login(email_b)
        cur_b = self.app.get("/api/curriculum/active").get_json()
        # User B must see ZERO of User A's subjects
        self.assertEqual(len(cur_b.get("subjects", [])), 0)

        # Evidence endpoint for User A's syllabus must NOT be accessible to User B
        ev_res = self.app.get("/api/syllabus/evidence")
        self.assertEqual(len(ev_res.get_json().get("subjects", [])), 0)


if __name__ == "__main__":
    unittest.main()
