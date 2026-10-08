"""
Unit Test Suite for Curriculum Completeness Validator

Verifies:
1. Correct student
2. Correct program
3. Correct department
4. Correct semester
5. Correct curriculum section
6. All detected subject tables processed
7. All pages belonging to the section processed
8. No duplicate subjects
9. No suspicious missing subject-code sequence
10. No suspicious incomplete table
11. Every subject has source evidence
12. Subject names are non-empty & valid
13. Subject identity is sufficiently confident

Verifies detection of common extraction problems:
- table ended unexpectedly
- subject code without subject name
- subject name without subject code when code should exist
- suspiciously low subject count
- duplicate subject
- repeated header treated as subject
- footer treated as subject
- page number treated as subject
- unrelated semester subjects included

Enforces:
- curriculumStatus = VALID when all checks pass
- curriculumStatus = NEEDS_REVIEW when completeness cannot be established
- subjects must NOT be partially exposed to learning features
- Zero mock subjects
"""
import unittest
import uuid
from app.curriculum_validator import CurriculumCompletenessValidator
from server import app


class TestCurriculumCompletenessValidator(unittest.TestCase):

    def setUp(self):
        self.user = {
            "user_id": "test_student_001",
            "name": "Jane Doe",
            "level": "college",
            "degree": "B.Tech",
            "department": "Computer Science and Engineering",
            "semester": 5
        }

        self.valid_subjects = [
            {
                "code": "CS501",
                "name": "Database Management Systems",
                "type": "Theory Core",
                "category": "Program Core",
                "credits": 3,
                "source_page": 1,
                "source_page_numbers": [1],
                "source_section": "Semester 5 Curriculum Table",
                "source_text": "CS501 Database Management Systems (3-0-0-3)",
                "semester_evidence": "Found in Semester 5 Table",
                "confidence": 0.98
            },
            {
                "code": "CS502",
                "name": "Theory of Computation",
                "type": "Theory Core",
                "category": "Program Core",
                "credits": 3,
                "source_page": 1,
                "source_page_numbers": [1],
                "source_section": "Semester 5 Curriculum Table",
                "source_text": "CS502 Theory of Computation (3-0-0-3)",
                "semester_evidence": "Found in Semester 5 Table",
                "confidence": 0.98
            },
            {
                "code": "CS503",
                "name": "Computer Networks",
                "type": "Theory Core",
                "category": "Program Core",
                "credits": 3,
                "source_page": 1,
                "source_page_numbers": [1],
                "source_section": "Semester 5 Curriculum Table",
                "source_text": "CS503 Computer Networks (3-0-0-3)",
                "semester_evidence": "Found in Semester 5 Table",
                "confidence": 0.98
            },
            {
                "code": "CS504",
                "name": "Operating Systems",
                "type": "Theory Core",
                "category": "Program Core",
                "credits": 3,
                "source_page": 2,
                "source_page_numbers": [2],
                "source_section": "Semester 5 Curriculum Table",
                "source_text": "CS504 Operating Systems (3-0-0-3)",
                "semester_evidence": "Found in Semester 5 Table",
                "confidence": 0.98
            },
            {
                "code": "CS511",
                "name": "Database Management Systems Laboratory",
                "type": "Practical / Laboratory",
                "category": "Laboratory Course",
                "credits": 2,
                "source_page": 2,
                "source_page_numbers": [2],
                "source_section": "Semester 5 Curriculum Table",
                "source_text": "CS511 Database Management Systems Laboratory (0-0-4-2)",
                "semester_evidence": "Found in Semester 5 Table",
                "confidence": 0.98
            }
        ]

        self.valid_raw_text = """
        DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING
        B.TECH COMPUTER SCIENCE AND ENGINEERING
        SEMESTER V
        CS501 Database Management Systems (3-0-0-3)
        CS502 Theory of Computation (3-0-0-3)
        CS503 Computer Networks (3-0-0-3)
        CS504 Operating Systems (3-0-0-3)
        CS511 Database Management Systems Laboratory (0-0-4-2)
        """

    def test_01_valid_curriculum_passes_all_checks(self):
        """A complete curriculum with all 13 checks passing must return curriculumStatus = VALID."""
        analysis = {
            "validation_status": "VALID",
            "detected_semesters": [5],
            "explicit_semester_identifier": "SEMESTER V",
            "expected_subject_count": 5,
            "course_title": "B.Tech Computer Science and Engineering",
            "extracted_subjects": [s["name"] for s in self.valid_subjects],
            "subjects": self.valid_subjects,
            "chapters": {s["name"]: [{"name": "Unit I", "concepts": ["Foundations"]}] for s in self.valid_subjects},
            "key_topics": ["Relational Model", "Automata", "TCP/IP", "Deadlocks", "SQL Queries"]
        }

        report = CurriculumCompletenessValidator.validate(
            user=self.user,
            analysis=analysis,
            raw_content_or_file=self.valid_raw_text,
            target_semester=5
        )

        self.assertEqual(report["status"], "VALID")
        self.assertEqual(report["curriculumStatus"], "VALID")
        self.assertTrue(report["is_valid"])
        self.assertEqual(report["subjects_detected"], 5)
        self.assertEqual(report["missing_subjects"], 0)
        self.assertEqual(report["duplicate_subjects"], 0)
        self.assertEqual(report["uncertain_subjects"], 0)
        self.assertEqual(len(report["issues"]), 0)

    def test_02_detect_table_ended_unexpectedly(self):
        """Detect when table ended unexpectedly (expected count > detected count, or missing practicals)."""
        bad_analysis = {
            "validation_status": "VALID",
            "detected_semesters": [5],
            "explicit_semester_identifier": "SEMESTER V",
            "expected_subject_count": 8,  # Expected 8, only got 3
            "course_title": "B.Tech Computer Science and Engineering",
            "extracted_subjects": [self.valid_subjects[0]["name"], self.valid_subjects[1]["name"]],
            "subjects": [self.valid_subjects[0], self.valid_subjects[1]]
        }

        report = CurriculumCompletenessValidator.validate(
            user=self.user,
            analysis=bad_analysis,
            raw_content_or_file=self.valid_raw_text + "\n... table continues on next page",
            target_semester=5
        )

        self.assertEqual(report["curriculumStatus"], "NEEDS_REVIEW")
        self.assertFalse(report["is_valid"])
        self.assertGreater(report["missing_subjects"], 0)
        self.assertIn("table ended unexpectedly", report["extraction_problems"])

    def test_03_detect_subject_code_without_subject_name(self):
        """Detect subject code without subject name or with empty/symbol name."""
        corrupted_subjects = list(self.valid_subjects[:4])
        corrupted_subjects.append({
            "code": "CS512",
            "name": "---", # Empty/symbol name
            "type": "Practical",
            "source_page": 2,
            "source_section": "Semester 5 Table",
            "source_text": "CS512 ---",
            "confidence": 0.95
        })

        analysis = {
            "validation_status": "VALID",
            "detected_semesters": [5],
            "expected_subject_count": 5,
            "extracted_subjects": [s["name"] for s in corrupted_subjects],
            "subjects": corrupted_subjects
        }

        report = CurriculumCompletenessValidator.validate(
            user=self.user,
            analysis=analysis,
            raw_content_or_file=self.valid_raw_text,
            target_semester=5
        )

        self.assertEqual(report["curriculumStatus"], "NEEDS_REVIEW")
        self.assertFalse(report["is_valid"])
        self.assertIn("subject code without subject name", report["extraction_problems"])

    def test_04_detect_subject_name_without_subject_code_when_code_should_exist(self):
        """Detect subject name without subject code when surrounding subjects have standard codes."""
        missing_code_subjects = list(self.valid_subjects[:3])
        missing_code_subjects.append({
            "code": "", # Missing code when CS501, CS502, CS503 exist
            "name": "Cloud Computing",
            "type": "Theory",
            "source_page": 2,
            "source_section": "Semester 5 Table",
            "source_text": "Cloud Computing (3-0-0-3)",
            "confidence": 0.95
        })

        analysis = {
            "validation_status": "VALID",
            "detected_semesters": [5],
            "expected_subject_count": 4,
            "extracted_subjects": [s["name"] for s in missing_code_subjects],
            "subjects": missing_code_subjects
        }

        raw = self.valid_raw_text + "\nCloud Computing (3-0-0-3)"
        report = CurriculumCompletenessValidator.validate(
            user=self.user,
            analysis=analysis,
            raw_content_or_file=raw,
            target_semester=5
        )

        self.assertEqual(report["curriculumStatus"], "NEEDS_REVIEW")
        self.assertFalse(report["is_valid"])
        self.assertIn("subject name without subject code when code should exist", report["extraction_problems"])

    def test_05_detect_suspiciously_low_subject_count(self):
        """Detect suspiciously low subject count (< 3 subjects for full semester)."""
        low_subjects = [self.valid_subjects[0]]

        analysis = {
            "validation_status": "VALID",
            "detected_semesters": [5],
            "expected_subject_count": 1,
            "extracted_subjects": [low_subjects[0]["name"]],
            "subjects": low_subjects
        }

        report = CurriculumCompletenessValidator.validate(
            user=self.user,
            analysis=analysis,
            raw_content_or_file=self.valid_raw_text,
            target_semester=5
        )

        self.assertEqual(report["curriculumStatus"], "NEEDS_REVIEW")
        self.assertFalse(report["is_valid"])
        self.assertIn("suspiciously low subject count", report["extraction_problems"])

    def test_06_detect_duplicate_subjects(self):
        """Detect duplicate subjects in extraction."""
        dup_subjects = list(self.valid_subjects[:4])
        # Add duplicate of CS501
        dup_subjects.append(dict(self.valid_subjects[0]))

        analysis = {
            "validation_status": "VALID",
            "detected_semesters": [5],
            "expected_subject_count": 5,
            "extracted_subjects": [s["name"] for s in dup_subjects],
            "subjects": dup_subjects
        }

        report = CurriculumCompletenessValidator.validate(
            user=self.user,
            analysis=analysis,
            raw_content_or_file=self.valid_raw_text,
            target_semester=5
        )

        self.assertEqual(report["curriculumStatus"], "NEEDS_REVIEW")
        self.assertFalse(report["is_valid"])
        self.assertGreater(report["duplicate_subjects"], 0)
        self.assertIn("duplicate subject", report["extraction_problems"])

    def test_07_detect_repeated_header_treated_as_subject(self):
        """Detect repeated table header erroneously captured as a subject."""
        header_noise_subjects = list(self.valid_subjects[:4])
        header_noise_subjects.append({
            "code": "HDR",
            "name": "Course Title", # Header mistaken for subject
            "type": "Theory",
            "source_page": 1,
            "source_section": "Semester 5 Table",
            "source_text": "Course Title",
            "confidence": 0.90
        })

        analysis = {
            "validation_status": "VALID",
            "detected_semesters": [5],
            "expected_subject_count": 5,
            "extracted_subjects": [s["name"] for s in header_noise_subjects],
            "subjects": header_noise_subjects
        }

        report = CurriculumCompletenessValidator.validate(
            user=self.user,
            analysis=analysis,
            raw_content_or_file=self.valid_raw_text,
            target_semester=5
        )

        self.assertEqual(report["curriculumStatus"], "NEEDS_REVIEW")
        self.assertFalse(report["is_valid"])
        self.assertEqual(report["header_as_subject_count"], 1)
        self.assertIn("repeated header treated as subject", report["extraction_problems"])

    def test_08_detect_footer_treated_as_subject(self):
        """Detect document footer erroneously captured as a subject."""
        footer_noise_subjects = list(self.valid_subjects[:4])
        footer_noise_subjects.append({
            "code": "COE",
            "name": "Controller of Examinations", # Footer mistaken for subject
            "type": "Theory",
            "source_page": 1,
            "source_section": "Semester 5 Table",
            "source_text": "Controller of Examinations",
            "confidence": 0.90
        })

        analysis = {
            "validation_status": "VALID",
            "detected_semesters": [5],
            "expected_subject_count": 5,
            "extracted_subjects": [s["name"] for s in footer_noise_subjects],
            "subjects": footer_noise_subjects
        }

        report = CurriculumCompletenessValidator.validate(
            user=self.user,
            analysis=analysis,
            raw_content_or_file=self.valid_raw_text,
            target_semester=5
        )

        self.assertEqual(report["curriculumStatus"], "NEEDS_REVIEW")
        self.assertFalse(report["is_valid"])
        self.assertEqual(report["footer_as_subject_count"], 1)
        self.assertIn("footer treated as subject", report["extraction_problems"])

    def test_09_detect_page_number_treated_as_subject(self):
        """Detect page number or solitary digits treated as a subject."""
        page_num_subjects = list(self.valid_subjects[:4])
        page_num_subjects.append({
            "code": "P2",
            "name": "Page 2", # Page number mistaken for subject
            "type": "Theory",
            "source_page": 2,
            "source_section": "Semester 5 Table",
            "source_text": "Page 2",
            "confidence": 0.90
        })

        analysis = {
            "validation_status": "VALID",
            "detected_semesters": [5],
            "expected_subject_count": 5,
            "extracted_subjects": [s["name"] for s in page_num_subjects],
            "subjects": page_num_subjects
        }

        report = CurriculumCompletenessValidator.validate(
            user=self.user,
            analysis=analysis,
            raw_content_or_file=self.valid_raw_text,
            target_semester=5
        )

        self.assertEqual(report["curriculumStatus"], "NEEDS_REVIEW")
        self.assertFalse(report["is_valid"])
        self.assertEqual(report["page_num_as_subject_count"], 1)
        self.assertIn("page number treated as subject", report["extraction_problems"])

    def test_10_detect_unrelated_semester_subjects(self):
        """Detect unrelated semester subjects included in current semester extraction."""
        cross_sem_subjects = list(self.valid_subjects[:4])
        cross_sem_subjects.append({
            "code": "CS301",
            "name": "Semester 3 Data Structures", # Unrelated semester 3 course
            "type": "Theory",
            "source_page": 1,
            "source_section": "Semester 3 Table",
            "source_text": "Semester 3 Data Structures",
            "confidence": 0.95
        })

        analysis = {
            "validation_status": "VALID",
            "detected_semesters": [5],
            "expected_subject_count": 5,
            "extracted_subjects": [s["name"] for s in cross_sem_subjects],
            "subjects": cross_sem_subjects
        }

        report = CurriculumCompletenessValidator.validate(
            user=self.user,
            analysis=analysis,
            raw_content_or_file=self.valid_raw_text + "\nSemester 3 Data Structures",
            target_semester=5
        )

        self.assertEqual(report["curriculumStatus"], "NEEDS_REVIEW")
        self.assertFalse(report["is_valid"])
        self.assertGreater(report["cross_semester_subjects"], 0)
        self.assertIn("unrelated semester subjects included", report["extraction_problems"])

    def test_11_detect_suspicious_missing_subject_code_sequence(self):
        """Detect suspicious gap in subject code sequence (e.g. CS501, CS502, CS504 skipping CS503)."""
        gap_subjects = [
            self.valid_subjects[0], # CS501
            self.valid_subjects[1], # CS502
            self.valid_subjects[3]  # CS504 (CS503 skipped)
        ]

        analysis = {
            "validation_status": "VALID",
            "detected_semesters": [5],
            "expected_subject_count": 3,
            "extracted_subjects": [s["name"] for s in gap_subjects],
            "subjects": gap_subjects
        }

        report = CurriculumCompletenessValidator.validate(
            user=self.user,
            analysis=analysis,
            raw_content_or_file=self.valid_raw_text,
            target_semester=5
        )

        self.assertEqual(report["curriculumStatus"], "NEEDS_REVIEW")
        self.assertFalse(report["is_valid"])
        self.assertIn("suspicious missing subject-code sequence", report["extraction_problems"])

    def test_12_no_partial_exposure_when_needs_review(self):
        """
        When curriculum validation fails and status is NEEDS_REVIEW,
        /api/curriculum/active MUST return subjects = [] and NO subjects are partially exposed.
        """
        client = app.test_client()

        suffix = uuid.uuid4().hex[:8]
        reg_payload = {
            "name": "Audit Student",
            "email": f"audit_student_{suffix}@example.com",
            "password": "Password123!",
            "role": "student",
            "level": "college",
            "institution_name": "Anna University",
            "degree": "B.Tech",
            "department": "Computer Science and Engineering",
            "current_year": 3,
            "current_semester": 5
        }
        reg_res = client.post("/api/auth/register", json=reg_payload)
        self.assertIn(reg_res.status_code, [200, 201])

        # Upload a corrupted syllabus where extraction produces missing / header noise
        corrupted_text = """
        B.TECH COMPUTER SCIENCE AND ENGINEERING
        SEMESTER V
        CS501 Database Management Systems
        Course Title
        Page 1
        """
        syl_res = client.post("/api/syllabus/analyze", json={
            "text": corrupted_text,
            "semester": 5
        })
        self.assertEqual(syl_res.status_code, 200)

        # Check /api/curriculum/active
        cur_res = client.get("/api/curriculum/active")
        self.assertEqual(cur_res.status_code, 200)
        cur_data = cur_res.get_json()

        self.assertEqual(cur_data.get("curriculumStatus"), "NEEDS_REVIEW")
        self.assertFalse(cur_data.get("is_valid"))
        self.assertEqual(cur_data.get("subjects"), [])
        self.assertEqual(cur_data.get("extracted_subjects"), [])


if __name__ == "__main__":
    unittest.main()
