import sys
import os
import unittest
from pathlib import Path

# Set up path to import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.gemini_service import gemini_service
from app.curriculum_validator import CurriculumCompletenessValidator

class TestMultiSemesterSyllabus(unittest.TestCase):
    """
    Test suite for Multi-Semester Syllabus Document Processing.
    Ensures:
    1. Target semester section is isolated from multi-semester PDFs/documents.
    2. Only target semester subjects and units are extracted.
    3. Other semesters are strictly ignored for active curriculum.
    4. Mismatch is flagged when target semester is absent.
    5. NEEDS_REVIEW is flagged when semester headings cannot be identified (NO GUESSING).
    6. Completeness validator verifies 0 cross-semester contamination.
    """

    def setUp(self):
        self.college_student_sem5 = {
            "id": "student_sem5_001",
            "user_id": "student_sem5_001",
            "name": "Alex Mercer",
            "level": "college",
            "degree": "B.Tech",
            "department": "Information Technology",
            "year": 3,
            "semester": 5,
            "current_semester": 5,
            "regulation": "R2021",
            "academic_year": "2024-2025"
        }

        self.college_student_sem3 = {
            "id": "student_sem3_002",
            "user_id": "student_sem3_002",
            "name": "Sarah Connor",
            "level": "college",
            "degree": "B.Tech",
            "department": "Computer Science and Engineering",
            "year": 2,
            "semester": 3,
            "current_semester": 3,
            "regulation": "R2021",
            "academic_year": "2024-2025"
        }

        # Comprehensive 8-semester curriculum document
        self.multi_sem_8_document = """
================================================================================
DEPARTMENT OF INFORMATION TECHNOLOGY - CURRICULUM SCHEME (SEMESTERS 1 TO 8)
================================================================================

SEMESTER 1
CS101 Problem Solving and Python Programming Credits: 4 L:3 T:0 P:2
MA101 Linear Algebra and Calculus Credits: 4 L:3 T:1 P:0
PH101 Engineering Physics Credits: 3 L:3 T:0 P:0
CS102 Python Programming Laboratory Credits: 2 L:0 T:0 P:4

SEMESTER 2
CS201 Data Structures in C Credits: 4 L:3 T:0 P:2
MA201 Differential Equations Credits: 4 L:3 T:1 P:0
EE201 Basic Electrical Engineering Credits: 3 L:3 T:0 P:0
CS202 Data Structures Laboratory Credits: 2 L:0 T:0 P:4

SEMESTER 3
IT301 Digital Principles and System Design Credits: 4 L:3 T:0 P:2
IT302 Object Oriented Programming in Java Credits: 3 L:3 T:0 P:0
IT303 Discrete Mathematics Credits: 4 L:3 T:1 P:0
IT304 Java Programming Laboratory Credits: 2 L:0 T:0 P:4

SEMESTER 4
IT401 Design and Analysis of Algorithms Credits: 4 L:3 T:0 P:2
IT402 Operating Systems Credits: 3 L:3 T:0 P:0
IT403 Microprocessors and Interfacing Credits: 3 L:3 T:0 P:0
IT404 Operating Systems Laboratory Credits: 2 L:0 T:0 P:4

SEMESTER 5
IT501 Database Management Systems Credits: 4 L:3 T:0 P:2
IT502 Web Technologies Credits: 3 L:3 T:0 P:0
IT503 Computer Networks Credits: 3 L:3 T:0 P:0
IT504 Formal Languages and Automata Theory Credits: 4 L:3 T:1 P:0
IT505 Software Engineering Credits: 3 L:3 T:0 P:0
IT506 Database Management Systems Laboratory Credits: 2 L:0 T:0 P:4
IT507 Web Technologies Laboratory Credits: 2 L:0 T:0 P:4
IT508 Professional Communication Laboratory Credits: 1 L:0 T:0 P:2

SEMESTER 6
IT601 Compiler Design Credits: 4 L:3 T:0 P:2
IT602 Cloud Computing Credits: 3 L:3 T:0 P:0
IT603 Cryptography and Network Security Credits: 3 L:3 T:0 P:0
IT604 Mobile Application Development Credits: 3 L:3 T:0 P:0
IT605 Mobile Application Development Laboratory Credits: 2 L:0 T:0 P:4

SEMESTER 7
IT701 Artificial Intelligence and Machine Learning Credits: 4 L:3 T:0 P:2
IT702 Internet of Things Credits: 3 L:3 T:0 P:0
IT703 Big Data Analytics Credits: 3 L:3 T:0 P:0
IT704 Project Phase I Credits: 4 L:0 T:0 P:8

SEMESTER 8
IT801 Professional Ethics and Human Values Credits: 3 L:3 T:0 P:0
IT802 Project Phase II Credits: 10 L:0 T:0 P:20

================================================================================
DETAILED SYLLABUS SECTION
================================================================================

SEMESTER 5
IT501 DATABASE MANAGEMENT SYSTEMS
Unit I: Relational Model and ER Modeling
Unit II: SQL, Relational Algebra, and Normalization
Unit III: Transaction Processing and Concurrency Control
Unit IV: Indexing, B-Trees, and Query Optimization
Unit V: NoSQL Databases and Distributed Systems

IT502 WEB TECHNOLOGIES
Unit I: HTML5, CSS3, and Responsive UI Design
Unit II: JavaScript ES6+, Async Programming, and DOM
Unit III: Server-Side Development with Node.js and Express
Unit IV: RESTful APIs and Database Integration
Unit V: Web Security, HTTPS, and Cloud Deployment

SEMESTER 6
IT601 COMPILER DESIGN
Unit I: Lexical Analysis and Regular Expressions
Unit II: Syntax Analysis and Parsing Techniques
Unit III: Intermediate Code Generation
Unit IV: Code Optimization Strategies
Unit V: Target Machine Code Generation
"""

    def test_01_semester_5_isolation_from_8_semester_document(self):
        """Verify that a Semester 5 student uploading an 8-semester document gets ONLY Semester 5 curriculum."""
        result = gemini_service.analyze_syllabus(
            content_or_file=self.multi_sem_8_document,
            level="college",
            semester=5,
            degree="B.Tech",
            department="Information Technology"
        )

        self.assertEqual(result.get("validation_status"), "VALID")
        detected_sems = result.get("detected_semesters", [])
        self.assertIn(1, detected_sems)
        self.assertIn(5, detected_sems)
        self.assertIn(8, detected_sems)

        subjects = result.get("subjects", [])
        extracted_names = [s.get("name") for s in subjects]
        extracted_codes = [s.get("code") for s in subjects]

        # Ensure all 8 Semester 5 subjects are present
        self.assertEqual(len(subjects), 8)
        self.assertIn("IT501", extracted_codes)
        self.assertIn("IT502", extracted_codes)
        self.assertIn("IT503", extracted_codes)
        self.assertIn("IT504", extracted_codes)
        self.assertIn("IT505", extracted_codes)
        self.assertIn("IT506", extracted_codes)
        self.assertIn("IT507", extracted_codes)
        self.assertIn("IT508", extracted_codes)

        # STRICT NEGATIVE CHECKS: Sem 1, 2, 3, 4, 6, 7, 8 MUST NOT BE EXTRACTED
        self.assertNotIn("CS101", extracted_codes)
        self.assertNotIn("Problem Solving and Python Programming", extracted_names)
        self.assertNotIn("CS201", extracted_codes)
        self.assertNotIn("Data Structures in C", extracted_names)
        self.assertNotIn("IT301", extracted_codes)
        self.assertNotIn("IT401", extracted_codes)
        self.assertNotIn("IT601", extracted_codes)
        self.assertNotIn("Compiler Design", extracted_names)
        self.assertNotIn("IT701", extracted_codes)
        self.assertNotIn("IT801", extracted_codes)

        # Verify unit extraction is strictly from Semester 5
        units = result.get("units", {})
        self.assertIn("Database Management Systems", units)
        self.assertIn("Web Technologies", units)
        self.assertNotIn("Compiler Design", units)
        self.assertNotIn("Problem Solving and Python Programming", units)

    def test_02_completeness_validator_on_isolated_semester_5(self):
        """Validate that the completeness validator certifies 0 cross-semester pollution."""
        analysis = gemini_service.analyze_syllabus(
            content_or_file=self.multi_sem_8_document,
            level="college",
            semester=5,
            degree="B.Tech",
            department="Information Technology"
        )

        validation_report = CurriculumCompletenessValidator.validate(
            user=self.college_student_sem5,
            analysis=analysis,
            raw_content_or_file=self.multi_sem_8_document,
            target_semester=5
        )

        self.assertEqual(validation_report["status"], "VALID")
        self.assertTrue(validation_report["is_valid"])
        self.assertEqual(validation_report["cross_semester_subjects"], 0)
        self.assertEqual(validation_report["duplicate_subjects"], 0)
        self.assertEqual(validation_report["missing_subjects"], 0)
        self.assertEqual(validation_report["uncertain_subjects"], 0)
        self.assertEqual(validation_report["subjects_detected"], 8)
        self.assertEqual(validation_report["subjects_verified"], 8)

    def test_03_semester_3_isolation_from_same_8_semester_document(self):
        """Verify that a Semester 3 student uploading the same document gets ONLY Semester 3 curriculum."""
        result = gemini_service.analyze_syllabus(
            content_or_file=self.multi_sem_8_document,
            level="college",
            semester=3,
            degree="B.Tech",
            department="Computer Science and Engineering"
        )

        self.assertEqual(result.get("validation_status"), "VALID")
        subjects = result.get("subjects", [])
        extracted_codes = [s.get("code") for s in subjects]

        self.assertEqual(len(subjects), 4)
        self.assertIn("IT301", extracted_codes)
        self.assertIn("IT302", extracted_codes)
        self.assertIn("IT303", extracted_codes)
        self.assertIn("IT304", extracted_codes)

        # Ensure no Semester 5 or Semester 6 subjects
        self.assertNotIn("IT501", extracted_codes)
        self.assertNotIn("IT601", extracted_codes)

    def test_04_mismatched_multi_semester_document(self):
        """Verify that uploading a Sem 1-4 document for a Semester 5 student triggers MISMATCH."""
        sem_1_to_4_doc = """
SEMESTER 1
CS101 Python Programming Credits: 4
MA101 Calculus Credits: 4

SEMESTER 2
CS201 Data Structures Credits: 4

SEMESTER 3
CS301 Discrete Math Credits: 4

SEMESTER 4
CS401 Operating Systems Credits: 4
"""
        result = gemini_service.analyze_syllabus(
            content_or_file=sem_1_to_4_doc,
            level="college",
            semester=5,
            degree="B.Tech",
            department="Information Technology"
        )

        self.assertEqual(result.get("validation_status"), "MISMATCH")
        self.assertFalse(result.get("completeness_verified"))
        self.assertTrue("Semester 5" in result.get("mismatch_reason", "") or "mismatch" in result.get("mismatch_reason", "").lower())

        # Completeness validator report must also be MISMATCH
        report = CurriculumCompletenessValidator.validate(
            user=self.college_student_sem5,
            analysis=result,
            raw_content_or_file=sem_1_to_4_doc,
            target_semester=5
        )
        self.assertEqual(report["status"], "MISMATCH")
        self.assertFalse(report["is_valid"])

    def test_05_unheaded_syllabus_flags_needs_review_no_guessing(self):
        """Verify that an unheaded/ambiguous document is marked NEEDS_REVIEW without guessing."""
        unheaded_doc = """
DEPARTMENT OF COMPUTER SCIENCE
List of Courses Offered:
CS101 Programming Concepts Credits: 4
CS102 Data Structures & Algorithms Credits: 4
CS103 Database Principles Credits: 4
CS104 Operating Systems Credits: 4
CS105 Artificial Intelligence Credits: 4
"""
        result = gemini_service.analyze_syllabus(
            content_or_file=unheaded_doc,
            level="college",
            semester=5,
            degree="B.Tech",
            department="Computer Science"
        )

        self.assertEqual(result.get("validation_status"), "NEEDS_REVIEW")
        self.assertFalse(result.get("completeness_verified"))
        self.assertIn("could not be reliably identified", result.get("mismatch_reason", ""))

        report = CurriculumCompletenessValidator.validate(
            user=self.college_student_sem5,
            analysis=result,
            raw_content_or_file=unheaded_doc,
            target_semester=5
        )
        self.assertEqual(report["status"], "NEEDS_REVIEW")
        self.assertFalse(report["is_valid"])

    def test_06_roman_numeral_and_word_heading_formats(self):
        """Verify robust recognition of Roman numeral (SEM V) and word ordinal (FIFTH SEMESTER) headings."""
        varied_format_doc = """
### THIRD SEMESTER
EC301 Electronic Circuits Credits: 4
EC302 Signals and Systems Credits: 4

### FOURTH SEMESTER
EC401 Analog Communication Credits: 4
EC402 Linear Integrated Circuits Credits: 4

### FIFTH SEMESTER
EC501 Digital Communication Credits: 4
EC502 Microprocessors and Microcontrollers Credits: 4
EC503 Digital Signal Processing Credits: 4
EC504 DSP Laboratory Credits: 2

### SIXTH SEMESTER
EC601 VLSI Design Credits: 4
EC602 Antenna and Wave Propagation Credits: 4
"""
        result = gemini_service.analyze_syllabus(
            content_or_file=varied_format_doc,
            level="college",
            semester=5,
            degree="B.E.",
            department="Electronics and Communication"
        )

        self.assertEqual(result.get("validation_status"), "VALID")
        subjects = result.get("subjects", [])
        extracted_codes = [s.get("code") for s in subjects]

        self.assertEqual(len(subjects), 4)
        self.assertIn("EC501", extracted_codes)
        self.assertIn("EC502", extracted_codes)
        self.assertIn("EC503", extracted_codes)
        self.assertIn("EC504", extracted_codes)

        self.assertNotIn("EC301", extracted_codes)
        self.assertNotIn("EC401", extracted_codes)
        self.assertNotIn("EC601", extracted_codes)

if __name__ == "__main__":
    unittest.main()
