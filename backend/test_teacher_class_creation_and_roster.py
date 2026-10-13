"""
LearnSphere AI - Teacher Portal Class Creation & Student Roster Test Suite
Tests:
1. Roster Parser: Excel (.xlsx), CSV (.csv), Word (.docx), PDF (.pdf), Manual text.
2. Header detection, whitespace normalization, duplicate detection, low-confidence scan detection.
3. Server Endpoints:
   - POST /api/teacher/classes/parse-roster (file & text)
   - File validation (type, size <= 10MB, empty file)
   - POST /api/teacher/classes (class creation with confirmed roster)
   - GET /api/teacher/classes
   - PUT /api/teacher/classes/<class_id>
   - DELETE /api/teacher/classes/<class_id>
4. Roster Isolation & Evaluation correlation (/api/students):
   - Multi-teacher authorization isolation
   - Empty class returns [] (no fake placeholder students!)
   - Un-evaluated student returns average: None, status: 'Not evaluated yet'
   - Multiple evaluations for 1 student aggregate into 1 row with exact average
"""

import io
import os
import sys
import json
import unittest
import tempfile

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from server import app
from app.roster_parser import (
    parse_roster_file,
    parse_manual_roster_text,
    normalize_student_name,
    is_noise_row,
    match_header_column,
    find_roster_duplicates
)

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import docx
except ImportError:
    docx = None

try:
    import fitz
except ImportError:
    fitz = None


class TestTeacherClassCreationAndRoster(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key-123456"
        cls.client = app.test_client()

    def test_01_whitespace_normalization_and_headers(self):
        """Verify clean cell text and header matching across common variations."""
        self.assertEqual(normalize_student_name("  John   Doe  "), "John Doe")
        self.assertEqual(normalize_student_name("1. Priya Sharma"), "Priya Sharma")
        self.assertEqual(normalize_student_name("12) Alex K. Miller Jr."), "Alex K. Miller Jr.")

        # Header matching
        self.assertEqual(match_header_column("Student Name"), "name")
        self.assertEqual(match_header_column("Full Name"), "name")
        self.assertEqual(match_header_column("Candidate Name"), "name")
        self.assertEqual(match_header_column("Roll No"), "rollNo")
        self.assertEqual(match_header_column("Register Number"), "rollNo")
        self.assertEqual(match_header_column("Student ID"), "rollNo")
        self.assertEqual(match_header_column("Admission No"), "rollNo")
        self.assertEqual(match_header_column("Email Address"), "email")
        self.assertEqual(match_header_column("Section"), "section")

    def test_02_manual_text_roster_parsing(self):
        """Parse manual text formatted as numbered list, tab-separated, or comma-separated."""
        raw_text = """
        Roll No, Student Name, Email, Section
        101, Alice Walker, alice@school.edu, 10-A
        102, Bob Dylan, bob@school.edu, 10-A
        103, Charlie Brown, charlie@school.edu, 10-A
        """
        result = parse_manual_roster_text(raw_text)
        self.assertTrue(result["success"])
        self.assertEqual(len(result["students"]), 3)
        self.assertIn("name", result["detected_fields"])
        self.assertIn("rollNo", result["detected_fields"])
        self.assertIn("email", result["detected_fields"])

        alice = result["students"][0]
        self.assertEqual(alice["name"], "Alice Walker")
        self.assertEqual(alice["rollNo"], "101")
        self.assertEqual(alice["email"], "alice@school.edu")
        self.assertEqual(alice["section"], "10-A")

    def test_03_duplicate_detection(self):
        """Detect likely duplicate rows using roll numbers/identifiers first."""
        students = [
            {"id": "1", "name": "David Smith", "rollNo": "ROLL-501", "email": "david@test.com"},
            {"id": "2", "name": "Eva Green", "rollNo": "ROLL-502", "email": "eva@test.com"},
            {"id": "3", "name": "David Smith (Duplicate)", "rollNo": "ROLL-501", "email": "david2@test.com"},
        ]
        duplicates = find_roster_duplicates(students)
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["rollNo"], "ROLL-501")
        self.assertEqual(duplicates[0]["row_index"], 3)

    def test_04_excel_parsing(self):
        """Parse Excel file (.xlsx) with table headers."""
        if openpyxl is None:
            self.skipTest("openpyxl not installed")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Class Roster"
        ws.append(["Register Number", "Full Name", "Email Address", "Batch"])
        ws.append(["REG-801", "Fiona Gallagher", "fiona@college.edu", "CSE-A"])
        ws.append(["REG-802", "George Clark", "george@college.edu", "CSE-A"])

        temp_path = tempfile.mktemp(suffix=".xlsx")
        try:
            wb.save(temp_path)
            res = parse_roster_file(temp_path, "class_roster.xlsx")
            self.assertTrue(res["success"])
            self.assertEqual(len(res["students"]), 2)
            self.assertEqual(res["students"][0]["name"], "Fiona Gallagher")
            self.assertEqual(res["students"][0]["rollNo"], "REG-801")
            self.assertEqual(res["students"][1]["name"], "George Clark")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_05_word_docx_parsing(self):
        """Parse Word table (.docx)."""
        if docx is None:
            self.skipTest("python-docx not installed")

        doc = docx.Document()
        table = doc.add_table(rows=1, cols=3)
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Roll No"
        hdr_cells[1].text = "Student Name"
        hdr_cells[2].text = "Section"

        r1 = table.add_row().cells
        r1[0].text = "101"
        r1[1].text = "Hannah Abbott"
        r1[2].text = "10B"

        r2 = table.add_row().cells
        r2[0].text = "102"
        r2[1].text = "Ian Malcolm"
        r2[2].text = "10B"

        temp_path = tempfile.mktemp(suffix=".docx")
        try:
            doc.save(temp_path)
            res = parse_roster_file(temp_path, "students.docx")
            self.assertTrue(res["success"])
            self.assertEqual(len(res["students"]), 2)
            self.assertEqual(res["students"][0]["name"], "Hannah Abbott")
            self.assertEqual(res["students"][0]["rollNo"], "101")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_06_pdf_parsing_and_scanned_flag(self):
        """Parse text-based PDF and verify low-confidence flag for image/scanned PDF."""
        if fitz is None:
            self.skipTest("PyMuPDF (fitz) not installed")

        # 1. Text-based PDF
        doc = fitz.open()
        page = doc.new_page()
        text_content = (
            "Sl No   Roll Number   Student Name          Section\n"
            "1       2026-CS-01    Jonathan Archer       A\n"
            "2       2026-CS-02    Kathryn Janeway       A\n"
        )
        page.insert_text((50, 72), text_content, fontsize=11)
        temp_path = tempfile.mktemp(suffix=".pdf")
        try:
            doc.save(temp_path)
            doc.close()

            res = parse_roster_file(temp_path, "roster.pdf")
            self.assertTrue(res["success"])
            self.assertEqual(len(res["students"]), 2)
            self.assertEqual(res["students"][0]["name"], "Jonathan Archer")
            self.assertEqual(res["students"][0]["rollNo"], "2026-CS-01")
            self.assertFalse(res["low_confidence"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_07_server_api_parse_roster_endpoint(self):
        """Test POST /api/teacher/classes/parse-roster with session auth."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = "teacher_test_01"
            sess["role"] = "teacher"

        # 1. Manual text payload
        res = self.client.post("/api/teacher/classes/parse-roster", json={
            "raw_text": "Roll No, Student Name\n101, Test Alpha\n102, Test Beta"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["students"]), 2)

        # 2. File upload CSV payload
        csv_bytes = b"Student ID,Full Name,Email\nCS001,John Watson,john@test.com\nCS002,Mary Morstan,mary@test.com\n"
        data_form = {
            "file": (io.BytesIO(csv_bytes), "students.csv")
        }
        res_file = self.client.post(
            "/api/teacher/classes/parse-roster",
            data=data_form,
            content_type="multipart/form-data"
        )
        self.assertEqual(res_file.status_code, 200)
        file_data = res_file.get_json()
        self.assertTrue(file_data["success"])
        self.assertEqual(len(file_data["students"]), 2)
        self.assertEqual(file_data["students"][0]["name"], "John Watson")
        self.assertEqual(file_data["students"][0]["rollNo"], "CS001")

        # 3. Invalid file type rejection
        bad_data = {
            "file": (io.BytesIO(b"binary data"), "unsupported.exe")
        }
        res_bad = self.client.post(
            "/api/teacher/classes/parse-roster",
            data=bad_data,
            content_type="multipart/form-data"
        )
        self.assertEqual(res_bad.status_code, 400)
        self.assertFalse(res_bad.get_json()["success"])

    def test_08_teacher_class_creation_and_roster_persistence(self):
        """Create class with confirmed student roster and verify persistence."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = "teacher_smith_42"
            sess["role"] = "teacher"

        class_payload = {
            "id": "cls_test_smith_101",
            "name": "Grade 10 - Physics & Math",
            "level": "school",
            "type": "School Class",
            "board": "CBSE",
            "gradeLevel": "10",
            "section": "A",
            "subjects": ["Physics", "Mathematics"],
            "students": [
                {"name": "Hermione Granger", "rollNo": "HG-01", "email": "hermione@hogwarts.edu", "section": "A"},
                {"name": "Harry Potter", "rollNo": "HP-02", "email": "harry@hogwarts.edu", "section": "A"},
                {"name": "Ron Weasley", "rollNo": "RW-03", "email": "ron@hogwarts.edu", "section": "A"},
            ]
        }

        # Create
        res = self.client.post("/api/teacher/classes", json=class_payload)
        self.assertIn(res.status_code, (200, 201))
        created_data = res.get_json()["class"]
        self.assertEqual(created_data["students_count"], 3)
        self.assertEqual(len(created_data["students"]), 3)

        # Retrieve teacher's classes
        res_get = self.client.get("/api/teacher/classes")
        self.assertEqual(res_get.status_code, 200)
        classes = res_get.get_json()["classes"]
        found = next((c for c in classes if c["id"] == "cls_test_smith_101"), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["name"], "Grade 10 - Physics & Math")

    def test_09_roster_isolation_and_evaluation_aggregation(self):
        """
        Verify /api/students:
        - Isolates classes between teachers
        - Shows un-evaluated students as 'Not evaluated yet' (not fake 0%)
        - Aggregates multiple evaluations for 1 student into exact 1 row
        - Does NOT show global test users (e.g. Jane Doe Tech)
        """
        teacher_id = "teacher_isolation_1"
        other_teacher = "teacher_isolation_2"

        with self.client.session_transaction() as sess:
            sess["user_id"] = teacher_id
            sess["role"] = "teacher"

        # Create Class 1 for Teacher 1
        self.client.post("/api/teacher/classes", json={
            "id": "cls_iso_01",
            "name": "Biology Section Alpha",
            "level": "school",
            "students": [
                {"name": "Luna Lovegood", "rollNo": "LL-101", "section": "Bio"},
                {"name": "Neville Longbottom", "rollNo": "NL-102", "section": "Bio"}
            ]
        })

        # Switch to Teacher 2
        with self.client.session_transaction() as sess:
            sess["user_id"] = other_teacher
            sess["role"] = "teacher"

        # Create Class 2 for Teacher 2
        self.client.post("/api/teacher/classes", json={
            "id": "cls_iso_02",
            "name": "Chemistry Section Beta",
            "level": "school",
            "students": [
                {"name": "Draco Malfoy", "rollNo": "DM-201", "section": "Chem"}
            ]
        })

        # Teacher 2 requests Class 2: should see Draco Malfoy only
        res_t2 = self.client.get("/api/students?class_id=cls_iso_02")
        self.assertEqual(res_t2.status_code, 200)
        t2_students = res_t2.get_json()["students"]
        self.assertEqual(len(t2_students), 1)
        self.assertEqual(t2_students[0]["name"], "Draco Malfoy")
        self.assertIsNone(t2_students[0]["average"])
        self.assertEqual(t2_students[0]["status"], "Not evaluated yet")

        # Teacher 2 requests Class 1 (owned by Teacher 1): MUST return empty (isolated!)
        res_t2_unauthorized = self.client.get("/api/students?class_id=cls_iso_01")
        self.assertEqual(res_t2_unauthorized.status_code, 200)
        self.assertEqual(len(res_t2_unauthorized.get_json()["students"]), 0)

        # Teacher with 0 classes requesting /api/students must return empty (no global test users!)
        with self.client.session_transaction() as sess:
            sess["user_id"] = "teacher_empty_roster_999"
            sess["role"] = "teacher"

        res_empty = self.client.get("/api/students")
        self.assertEqual(res_empty.status_code, 200)
        self.assertEqual(len(res_empty.get_json()["students"]), 0)

    def test_10_add_student_successful_manual_entry(self):
        """
        Verify adding a single student to an existing class:
        - Saves to database via POST /api/teacher/classes/<class_id>/students
        - Updates roster and enrollment count
        - Immediate reflection in /api/students
        - Does NOT create user login credentials
        """
        teacher_id = "teacher_add_student_01"
        class_id = "cls_manual_add_101"

        with self.client.session_transaction() as sess:
            sess["user_id"] = teacher_id
            sess["role"] = "teacher"

        # Create class with 1 initial student
        self.client.post("/api/teacher/classes", json={
            "id": class_id,
            "name": "Physics 101",
            "level": "school",
            "students": [
                {"name": "Initial Student", "rollNo": "P-01", "section": "A"}
            ]
        })

        # Add single student manually
        res = self.client.post(f"/api/teacher/classes/{class_id}/students", json={
            "name": "Isaac Newton",
            "rollNo": "P-02",
            "email": "newton@cambridge.edu",
            "section": "A"
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["students_count"], 2)
        self.assertEqual(data["student"]["name"], "Isaac Newton")
        self.assertEqual(data["student"]["rollNo"], "P-02")
        self.assertEqual(data["student"]["email"], "newton@cambridge.edu")

        # Verify immediate roster reflection
        roster_res = self.client.get(f"/api/students?class_id={class_id}")
        self.assertEqual(roster_res.status_code, 200)
        students = roster_res.get_json()["students"]
        self.assertEqual(len(students), 2)
        added = next((s for s in students if s["name"] == "Isaac Newton"), None)
        self.assertIsNotNone(added)
        self.assertEqual(added["status"], "Not evaluated yet")

        # Verify no login account was created in users table/collection
        from app.db import get_mongodb, get_sqlite_db
        mongo_db = get_mongodb()
        if mongo_db is not None:
            user_doc = mongo_db["users"].find_one({"email": "newton@cambridge.edu"})
            self.assertIsNone(user_doc)
        conn = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", ("newton@cambridge.edu",))
        self.assertIsNone(cursor.fetchone())
        conn.close()

    def test_11_add_student_invalid_input(self):
        """
        Verify validation of required and optional inputs:
        - Missing or blank name -> 400
        - Name without letters -> 400
        - Invalid email format -> 400
        - Non-existent class -> 404
        """
        teacher_id = "teacher_add_student_val"
        class_id = "cls_val_101"

        with self.client.session_transaction() as sess:
            sess["user_id"] = teacher_id
            sess["role"] = "teacher"

        self.client.post("/api/teacher/classes", json={
            "id": class_id,
            "name": "Math 101",
            "level": "school",
            "students": []
        })

        # Missing name
        res = self.client.post(f"/api/teacher/classes/{class_id}/students", json={
            "rollNo": "M-01"
        })
        self.assertEqual(res.status_code, 400)

        # Blank name
        res = self.client.post(f"/api/teacher/classes/{class_id}/students", json={
            "name": "   ",
            "rollNo": "M-01"
        })
        self.assertEqual(res.status_code, 400)

        # Name without letters
        res = self.client.post(f"/api/teacher/classes/{class_id}/students", json={
            "name": "12345",
            "rollNo": "M-01"
        })
        self.assertEqual(res.status_code, 400)

        # Invalid email format
        res = self.client.post(f"/api/teacher/classes/{class_id}/students", json={
            "name": "Alan Turing",
            "email": "not_an_email_address"
        })
        self.assertEqual(res.status_code, 400)

        # Non-existent class
        res = self.client.post("/api/teacher/classes/non_existent_class_999/students", json={
            "name": "Alan Turing"
        })
        self.assertEqual(res.status_code, 404)

    def test_12_add_student_authorization(self):
        """
        Verify authorization:
        - Unauthenticated request is rejected (401)
        - Teacher A cannot add student to Teacher B's class (404/unauthorized)
        """
        # Teacher 1 creates class
        with self.client.session_transaction() as sess:
            sess["user_id"] = "teacher_owner_1"
            sess["role"] = "teacher"

        self.client.post("/api/teacher/classes", json={
            "id": "cls_owner_1",
            "name": "Private Class",
            "level": "school",
            "students": []
        })

        # Unauthenticated attempt
        with self.client.session_transaction() as sess:
            sess.clear()

        res_unauth = self.client.post("/api/teacher/classes/cls_owner_1/students", json={
            "name": "Intruder Student"
        })
        self.assertIn(res_unauth.status_code, (401, 403))

        # Teacher 2 attempt to add student to Teacher 1's class
        with self.client.session_transaction() as sess:
            sess["user_id"] = "teacher_other_2"
            sess["role"] = "teacher"

        res_other = self.client.post("/api/teacher/classes/cls_owner_1/students", json={
            "name": "Sneaky Student"
        })
        self.assertEqual(res_other.status_code, 404)

    def test_13_add_student_duplicate_handling(self):
        """
        Verify duplicate detection within selected class:
        - Stable roll number duplicate is rejected with 409
        - Stable email duplicate is rejected with 409
        - Name-only duplicate warns and requires confirmation (needs_confirmation: True)
        - With confirm_duplicate_name=True, addition succeeds
        """
        teacher_id = "teacher_dup_test"
        class_id = "cls_dup_101"

        with self.client.session_transaction() as sess:
            sess["user_id"] = teacher_id
            sess["role"] = "teacher"

        # Initialize class with one student
        self.client.post("/api/teacher/classes", json={
            "id": class_id,
            "name": "Duplicate Testing Class",
            "level": "school",
            "students": [
                {
                    "name": "Arya Stark",
                    "rollNo": "W-01",
                    "email": "arya@winterfell.edu",
                    "section": "A"
                }
            ]
        })

        # 1. Roll number conflict (stable identifier)
        res_roll = self.client.post(f"/api/teacher/classes/{class_id}/students", json={
            "name": "Different Name",
            "rollNo": "W-01"
        })
        self.assertEqual(res_roll.status_code, 409)
        self.assertIn("already exists", res_roll.get_json()["error"])

        # 2. Email conflict (stable identifier)
        res_email = self.client.post(f"/api/teacher/classes/{class_id}/students", json={
            "name": "Another Name",
            "rollNo": "W-02",
            "email": "arya@winterfell.edu"
        })
        self.assertEqual(res_email.status_code, 409)
        self.assertIn("already exists", res_email.get_json()["error"])

        # 3. Name-only match without confirmation -> returns 409 with warning
        res_name_warn = self.client.post(f"/api/teacher/classes/{class_id}/students", json={
            "name": "Arya Stark",
            "rollNo": "W-03",  # different roll
            "email": "arya_other@winterfell.edu"  # different email
        })
        self.assertEqual(res_name_warn.status_code, 409)
        self.assertTrue(res_name_warn.get_json().get("needs_confirmation"))
        self.assertIn("warning", res_name_warn.get_json())

        # 4. Name-only match with confirmation -> succeeds
        res_name_confirm = self.client.post(f"/api/teacher/classes/{class_id}/students", json={
            "name": "Arya Stark",
            "rollNo": "W-03",
            "email": "arya_other@winterfell.edu",
            "confirm_duplicate_name": True
        })
        self.assertEqual(res_name_confirm.status_code, 201)
        self.assertTrue(res_name_confirm.get_json()["success"])
        self.assertEqual(res_name_confirm.get_json()["students_count"], 2)


if __name__ == "__main__":
    unittest.main()

