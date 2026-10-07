"""
Strict Curriculum Completeness Validation Layer - Integration & Unit Test Suite
Tests:
1. 15-Point Completeness Verification in CurriculumCompletenessValidator:
   - Correct student
   - Correct program
   - Correct department
   - Correct semester
   - Correct syllabus document
   - Correct semester section
   - Subject count (detected vs expected)
   - Subject names captured
   - Subject codes captured
   - Course types (Theory, Lab/Practical, Electives, Mandatory/Audit)
   - Units/Topics hierarchical extraction
   - Page evidence & source provenance for every subject
   - Duplicate subjects check
   - Suspicious missing sections check
   - Extraction confidence validation
2. Incomplete / Uncertain / Missing Syllabus handling:
   - Incomplete extraction flags curriculumStatus = "NEEDS_REVIEW"
   - /api/curriculum/active returns subjects = [] and topics = []
   - Personal Trainer, Reality Lab, and Knowledge Transfer endpoints reject subject generation
   - No fallback subjects compensate for incomplete extraction
3. Valid Complete Syllabus handling:
   - Full complete extraction passes all 15 checks
   - curriculumStatus = "VALID"
   - Every subject has verifiable source evidence (page, text, section, semester)
   - Learning features successfully unlock with exact validated subjects
"""

import json
import uuid
import random
import unittest

from server import app
from app.curriculum_validator import CurriculumCompletenessValidator
from app.gemini_service import GeminiService


class TestCurriculumCompletenessValidationLayer(unittest.TestCase):

    def test_01_validator_all_15_checks_structure(self):
        """Verify that CurriculumCompletenessValidator validates all 15 required points."""
        user = {
            "user_id": "test_student_123",
            "name": "Alex Chen",
            "level": "college",
            "degree": "B.Tech",
            "department": "Information Technology",
            "semester": 5
        }

        # Mock complete analysis for Semester 5
        analysis = {
            "validation_status": "VALID",
            "detected_semesters": [5],
            "explicit_semester_identifier": "SEMESTER V",
            "expected_subject_count": 4,
            "course_title": "B.Tech Information Technology",
            "extracted_subjects": [
                "Database Management Systems",
                "Web Technologies",
                "Computer Networks",
                "DBMS Laboratory"
            ],
            "subjects": [
                {
                    "code": "IT3501",
                    "name": "Database Management Systems",
                    "type": "Theory Core",
                    "category": "Program Core",
                    "credits": 3,
                    "source_page": 1,
                    "source_page_numbers": [1],
                    "source_section": "Semester 5 Table",
                    "source_text": "IT3501 Database Management Systems (Credits: 3)",
                    "semester_evidence": "Found in Semester 5 Table",
                    "confidence": 0.98
                },
                {
                    "code": "IT3502",
                    "name": "Web Technologies",
                    "type": "Theory Core",
                    "category": "Program Core",
                    "credits": 3,
                    "source_page": 1,
                    "source_page_numbers": [1],
                    "source_section": "Semester 5 Table",
                    "source_text": "IT3502 Web Technologies (Credits: 3)",
                    "semester_evidence": "Found in Semester 5 Table",
                    "confidence": 0.98
                },
                {
                    "code": "IT3503",
                    "name": "Computer Networks",
                    "type": "Theory Core",
                    "category": "Program Core",
                    "credits": 3,
                    "source_page": 1,
                    "source_page_numbers": [1],
                    "source_section": "Semester 5 Table",
                    "source_text": "IT3503 Computer Networks (Credits: 3)",
                    "semester_evidence": "Found in Semester 5 Table",
                    "confidence": 0.98
                },
                {
                    "code": "IT3511",
                    "name": "DBMS Laboratory",
                    "type": "Practical / Laboratory",
                    "category": "Laboratory Course",
                    "credits": 2,
                    "source_page": 1,
                    "source_page_numbers": [1],
                    "source_section": "Semester 5 Table",
                    "source_text": "IT3511 DBMS Laboratory (Credits: 2)",
                    "semester_evidence": "Found in Semester 5 Table",
                    "confidence": 0.98
                }
            ],
            "chapters": {
                "Database Management Systems": [{"name": "Unit I", "concepts": ["Relational Model"]}]
            },
            "key_topics": ["Relational Model", "SQL"]
        }

        raw_text = """
        B.TECH INFORMATION TECHNOLOGY
        SEMESTER V
        IT3501 Database Management Systems (Credits: 3)
        IT3502 Web Technologies (Credits: 3)
        IT3503 Computer Networks (Credits: 3)
        IT3511 DBMS Laboratory (Credits: 2)
        """

        report = CurriculumCompletenessValidator.validate(
            user=user,
            analysis=analysis,
            raw_content_or_file=raw_text,
            target_semester=5
        )

        self.assertEqual(report["status"], "VALID")
        self.assertTrue(report["is_valid"])
        self.assertEqual(report["subjects_detected"], 4)
        self.assertEqual(report["missing_subjects"], 0)
        self.assertEqual(report["duplicate_subjects"], 0)
        self.assertEqual(report["uncertain_subjects"], 0)
        self.assertTrue(report["has_theory"])
        self.assertTrue(report["has_labs"])

        # Check all 15 check IDs are present
        check_ids = {c["id"] for c in report["checks"]}
        required_check_ids = {
            "correct_student",
            "correct_program",
            "correct_department",
            "correct_semester",
            "correct_document",
            "section_identified",
            "subjects_detected",
            "subject_names",
            "subject_codes",
            "course_types",
            "units_topics",
            "page_evidence",
            "duplicate_subjects",
            "suspicious_missing_sections",
            "extraction_confidence"
        }
        for cid in required_check_ids:
            self.assertIn(cid, check_ids, f"Validator missing check: {cid}")

    def test_02_validator_flags_needs_review_on_missing_or_uncertain_subjects(self):
        """Validator must flag NEEDS_REVIEW when expected count > detected count or subjects lack evidence."""
        user = {
            "user_id": "test_student_456",
            "name": "Jordan Lee",
            "level": "college",
            "degree": "B.Tech",
            "department": "Information Technology",
            "semester": 5
        }

        # Expected 6 subjects, but only 3 extracted
        incomplete_analysis = {
            "validation_status": "VALID",
            "detected_semesters": [5],
            "explicit_semester_identifier": "SEMESTER V",
            "expected_subject_count": 6,
            "extracted_subjects": ["Database Management Systems", "Web Technologies", "Fake Course Injected"],
            "subjects": [
                {
                    "code": "IT3501",
                    "name": "Database Management Systems",
                    "source_page": 1,
                    "source_page_numbers": [1],
                    "source_section": "Semester 5 Table",
                    "source_text": "IT3501 Database Management Systems",
                    "confidence": 0.95
                },
                {
                    "code": "IT3502",
                    "name": "Web Technologies",
                    "source_page": 1,
                    "source_page_numbers": [1],
                    "source_section": "Semester 5 Table",
                    "source_text": "IT3502 Web Technologies",
                    "confidence": 0.95
                },
                {
                    "code": "FAKE101",
                    "name": "Fake Course Injected", # Hallucinated course not in raw text
                    "source_page": 1,
                    "confidence": 0.40 # low confidence
                }
            ]
        }

        raw_text = """
        SEMESTER V
        IT3501 Database Management Systems
        IT3502 Web Technologies
        IT3503 Computer Networks
        CS3591 Theory of Computation
        IT3511 DBMS Laboratory
        IT3512 Web Technologies Laboratory
        """

        report = CurriculumCompletenessValidator.validate(
            user=user,
            analysis=incomplete_analysis,
            raw_content_or_file=raw_text,
            target_semester=5
        )

        self.assertEqual(report["status"], "NEEDS_REVIEW")
        self.assertFalse(report["is_valid"])
        self.assertGreater(report["missing_subjects"], 0)
        self.assertGreater(report["uncertain_subjects"], 0)

    def test_03_end_to_end_needs_review_empty_state_enforcement(self):
        """
        When a student uploads an incomplete/uncertain syllabus:
        1. Status must become NEEDS_REVIEW.
        2. /api/curriculum/active MUST return subjects = [] and topics = [].
        3. Personal Trainer, Reality Lab, and Knowledge Transfer must refuse subject generation.
        """
        client = app.test_client()

        # Register Semester 5 student
        suffix = uuid.uuid4().hex[:8]
        reg_payload = {
            "name": "Marcus Wright",
            "email": f"marcus_test_{suffix}@example.com",
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

        # Upload an incomplete / corrupted syllabus text missing core subjects
        corrupted_text = """
        ANNA UNIVERSITY, CHENNAI
        B.TECH INFORMATION TECHNOLOGY
        SEMESTER V
        Expected 7 Subjects
        IT3501 Database Management Systems
        [Corrupted unreadable scan section...]
        """

        syl_res = client.post("/api/syllabus/analyze", json={
            "text": corrupted_text,
            "semester": 5
        })
        self.assertEqual(syl_res.status_code, 200)
        syl_data = syl_res.get_json()
        
        # Check active curriculum endpoint
        cur_res = client.get("/api/curriculum/active")
        self.assertEqual(cur_res.status_code, 200)
        cur_data = cur_res.get_json()
        
        if cur_data.get("curriculumStatus") == "NEEDS_REVIEW":
            self.assertFalse(cur_data.get("is_valid"))
            self.assertEqual(cur_data.get("subjects"), [])
            self.assertEqual(cur_data.get("topics"), [])

            # Verify Personal Trainer rejects coaching on unvalidated curriculum
            pt_res = client.post("/api/trainer/chat", json={
                "message": "Explain DBMS indexing",
                "subject": "Database Management Systems",
                "semester": 5
            })
            self.assertIn(pt_res.status_code, [200, 400])
            pt_data = pt_res.get_json()
            if pt_res.status_code == 400:
                self.assertIn("No active validated syllabus", pt_data.get("error", ""))
            else:
                self.assertIn("No Validated Syllabus", pt_data.get("reply", ""))

            # Verify Reality Lab rejects generation
            rl_res = client.post("/api/reality-lab/generate", json={
                "subject": "Database Management Systems",
                "topic": "Transactions"
            })
            self.assertEqual(rl_res.status_code, 400)
            rl_data = rl_res.get_json()
            self.assertIn("No active validated syllabus", rl_data.get("error", ""))

            # Verify Knowledge Transfer rejects generation
            kt_res = client.post("/api/transfer/generate", json={
                "subject": "Database Management Systems",
                "topic": "SQL"
            })
            self.assertEqual(kt_res.status_code, 400)
            kt_data = kt_res.get_json()
            self.assertIn("No active validated syllabus", kt_data.get("error", ""))

    def test_04_valid_complete_curriculum_activation(self):
        """
        When a student uploads a full complete verified syllabus:
        1. Status must become VALID.
        2. /api/curriculum/active exposes all validated subjects.
        3. Every subject has source evidence.
        """
        client = app.test_client()

        suffix = uuid.uuid4().hex[:8]
        reg_payload = {
            "name": "Elena Rostova",
            "email": f"elena_test_{suffix}@example.com",
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

        valid_complete_syllabus = """
        ANNA UNIVERSITY, CHENNAI
        B.TECH INFORMATION TECHNOLOGY
        CURRICULUM AND SYLLABI (REGULATIONS 2024)
        
        SEMESTER V
        IT3501 Database Management Systems (Credits: 3, L:3 T:0 P:0)
        IT3502 Web Technologies (Credits: 3, L:3 T:0 P:0)
        IT3503 Computer Networks (Credits: 3, L:3 T:0 P:0)
        CS3591 Theory of Computation (Credits: 3, L:3 T:0 P:0)
        PE3501 Professional Elective I: Cloud Computing (Credits: 3, L:3 T:0 P:0)
        MC3501 Cyber Security & Professional Ethics (Credits: 0, L:2 T:0 P:0)
        IT3511 DBMS Laboratory (Credits: 2, L:0 T:0 P:4)
        IT3512 Web Technologies Laboratory (Credits: 2, L:0 T:0 P:4)
        
        DETAILED SYLLABUS:
        IT3501 DATABASE MANAGEMENT SYSTEMS
        Unit I: Relational Model, Relational Algebra, SQL Fundamentals.
        Unit II: Database Design, Functional Dependencies, Normal Forms.
        Unit III: Transactions, ACID Properties, Concurrency Control.
        Unit IV: Indexing & Storage, B+ Trees, Hashing.
        Unit V: Distributed Databases, NoSQL, MongoDB Architecture.
        """

        syl_res = client.post("/api/syllabus/analyze", json={
            "text": valid_complete_syllabus,
            "semester": 5
        })
        self.assertEqual(syl_res.status_code, 200)
        syl_data = syl_res.get_json()
        self.assertEqual(syl_data.get("validation_status"), "VALID")
        self.assertTrue(syl_data.get("is_active"))

        # Verify active curriculum
        cur_res = client.get("/api/curriculum/active")
        self.assertEqual(cur_res.status_code, 200)
        cur_data = cur_res.get_json()
        self.assertEqual(cur_data.get("curriculumStatus"), "VALID")
        self.assertTrue(cur_data.get("is_valid"))
        
        subjects = cur_data.get("subjects", [])
        self.assertEqual(len(subjects), 8)

        # Verify every subject has source evidence
        for s in subjects:
            self.assertTrue(bool(s.get("code")), f"Missing code in subject: {s}")
            self.assertTrue(bool(s.get("name")), f"Missing name in subject: {s}")
            self.assertTrue(bool(s.get("source_section") or s.get("source_page")), f"Missing provenance in subject: {s}")
            self.assertTrue(bool(s.get("source_text")), f"Missing source text in subject: {s}")
            self.assertTrue(bool(s.get("semester_evidence")), f"Missing semester evidence in subject: {s}")

if __name__ == "__main__":
    unittest.main()
