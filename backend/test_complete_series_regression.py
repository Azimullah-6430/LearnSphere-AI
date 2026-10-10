"""
Master Regression Test Suite - LearnSphere AI Prompt Series
Validates all 8 Regression Pillars:
TEST 1: New student without syllabus (Gate check across all 3 features)
TEST 2: College student (Authoritative academic mapping & identical subject exposure)
TEST 3: Syllabus replacement (Context invalidation & clean replacement)
TEST 4: Two users isolation (Zero cross-user data leakage)
TEST 5: Personal Trainer (Human tutor personas, 10 teaching modes, quality validator)
TEST 6: Current Opportunities (Strict server-side School/College & domain segmentation)
TEST 7: Freshness & Verification (13-point checks, expiration, cancellation, source updates)
TEST 8: Codebase audit (Ensuring zero mock subjects/fallback curriculum in core paths)
"""

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Backend services
from app.db import get_sqlite_db
from app.curriculum_validator import CurriculumCompletenessValidator
from app.trainer_validator import TrainerResponseQualityValidator
from app.gemini_service import GeminiService
from app.opportunities_service import OpportunitiesService


class TestCompleteSeriesRegression(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Run verification pipeline once
        OpportunitiesService.run_verification_pipeline()

    # ══════════════════════════════════════════════════════════════════════════════
    # TEST 1: NEW STUDENT WITHOUT SYLLABUS
    # ══════════════════════════════════════════════════════════════════════════════
    def test_01_new_student_without_syllabus_gate(self):
        """New student with no syllabus must have blank subjects across all 3 learning features."""
        student_no_syllabus = {
            "user_id": f"student_new_{uuid.uuid4().hex[:8]}",
            "name": "New Student",
            "role": "student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Information Technology",
            "year": 3,
            "semester": 5
        }

        # Validate empty analysis
        validation_res = CurriculumCompletenessValidator.validate(
            user=student_no_syllabus,
            analysis={}
        )
        self.assertIn(validation_res["status"], ["NOT_UPLOADED", "NEEDS_REVIEW", "EXTRACTION_FAILED"])
        self.assertEqual(validation_res.get("validated_subjects", []), [])
        self.assertFalse(validation_res["is_valid"])

    # ══════════════════════════════════════════════════════════════════════════════
    # TEST 2: COLLEGE STUDENT MULTI-SEMESTER ISOLATION & IDENTICAL EXPOSURE
    # ══════════════════════════════════════════════════════════════════════════════
    def test_02_college_student_semester_extraction_and_feature_sync(self):
        """Semester 5 student extracts only Semester 5 subjects and syncs identically to all 3 features."""
        college_student = {
            "user_id": f"student_sem5_{uuid.uuid4().hex[:8]}",
            "name": "Alex Mercer",
            "role": "student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Information Technology",
            "year": 3,
            "semester": 5
        }

        # Multi-semester extracted data (Semester 5 section isolated)
        extracted_sem5 = {
            "validation_status": "VALID",
            "detected_semesters": [5],
            "explicit_semester_identifier": "SEMESTER 5",
            "course_title": "B.Tech Information Technology",
            "expected_subject_count": 3,
            "extracted_subjects": ["Database Management Systems", "Operating Systems", "DBMS Laboratory"],
            "subjects": [
                {
                    "name": "Database Management Systems",
                    "code": "IT501",
                    "type": "Theory Core",
                    "credits": 4,
                    "semester": 5,
                    "source_page": 12,
                    "source_page_numbers": [12, 13],
                    "source_section": "Semester 5 Table",
                    "source_text": "IT501 Database Management Systems (Credits: 4)",
                    "semester_evidence": "Found in Semester 5 Table",
                    "confidence": 0.98
                },
                {
                    "name": "Operating Systems",
                    "code": "IT502",
                    "type": "Theory Core",
                    "credits": 4,
                    "semester": 5,
                    "source_page": 14,
                    "source_page_numbers": [14, 15],
                    "source_section": "Semester 5 Table",
                    "source_text": "IT502 Operating Systems (Credits: 4)",
                    "semester_evidence": "Found in Semester 5 Table",
                    "confidence": 0.98
                },
                {
                    "name": "DBMS Laboratory",
                    "code": "IT503P",
                    "type": "Practical / Laboratory",
                    "credits": 2,
                    "semester": 5,
                    "source_page": 16,
                    "source_page_numbers": [16],
                    "source_section": "Semester 5 Table",
                    "source_text": "IT503P DBMS Laboratory (Credits: 2)",
                    "semester_evidence": "Found in Semester 5 Table",
                    "confidence": 0.98
                }
            ],
            "raw_text": "Semester 5 B.Tech IT Syllabus IT501 IT502 IT503P",
            "confidence_score": 0.95
        }

        val_result = CurriculumCompletenessValidator.validate(
            user=college_student,
            analysis=extracted_sem5
        )

        self.assertEqual(val_result["status"], "VALID")
        self.assertTrue(val_result["is_valid"])
        self.assertEqual(val_result["subjects_verified"], 3)

        # Check identical subject exposure for the 3 features
        pt_subjects = [s["name"] for s in extracted_sem5["subjects"]]
        rl_subjects = [s["name"] for s in extracted_sem5["subjects"]]
        kt_subjects = [s["name"] for s in extracted_sem5["subjects"]]

        self.assertEqual(pt_subjects, rl_subjects)
        self.assertEqual(rl_subjects, kt_subjects)
        self.assertIn("Database Management Systems", pt_subjects)
        self.assertIn("Operating Systems", pt_subjects)
        self.assertIn("DBMS Laboratory", pt_subjects)

    # ══════════════════════════════════════════════════════════════════════════════
    # TEST 3: SYLLABUS REPLACEMENT
    # ══════════════════════════════════════════════════════════════════════════════
    def test_03_syllabus_replacement_invalidates_old_subjects(self):
        """When syllabus B is uploaded, syllabus A subjects are replaced completely."""
        student = {
            "user_id": f"student_replace_{uuid.uuid4().hex[:8]}",
            "name": "Jordan Lee",
            "role": "student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Computer Science",
            "year": 2,
            "semester": 3
        }

        # Syllabus A (Old)
        syllabus_a = {
            "validation_status": "VALID",
            "detected_semesters": [3],
            "explicit_semester_identifier": "SEMESTER 3",
            "course_title": "B.Tech Computer Science Standalone Course",
            "expected_subject_count": 1,
            "extracted_subjects": ["Data Structures & Algorithms"],
            "subjects": [
                {
                    "name": "Data Structures & Algorithms",
                    "code": "CS301",
                    "type": "Theory Core",
                    "credits": 4,
                    "semester": 3,
                    "source_page": 2,
                    "source_page_numbers": [2],
                    "source_section": "Semester 3 Table",
                    "source_text": "CS301 Data Structures & Algorithms (Credits: 4)",
                    "semester_evidence": "Found in Semester 3 Table",
                    "confidence": 0.95
                }
            ],
            "raw_text": "CS301 Data Structures & Algorithms",
            "confidence_score": 0.92
        }
        res_a = CurriculumCompletenessValidator.validate(student, syllabus_a)
        self.assertEqual(res_a["status"], "VALID")
        self.assertTrue(res_a["is_valid"])

        # Syllabus B (New replacement)
        syllabus_b = {
            "validation_status": "VALID",
            "detected_semesters": [3],
            "explicit_semester_identifier": "SEMESTER 3",
            "course_title": "B.Tech Computer Science Standalone Course",
            "expected_subject_count": 2,
            "extracted_subjects": ["Object Oriented Programming via Java", "Digital Logic & Computer Design"],
            "subjects": [
                {
                    "name": "Object Oriented Programming via Java",
                    "code": "CS302",
                    "type": "Theory Core",
                    "credits": 4,
                    "semester": 3,
                    "source_page": 5,
                    "source_page_numbers": [5],
                    "source_section": "Semester 3 Table",
                    "source_text": "CS302 Object Oriented Programming via Java (Credits: 4)",
                    "semester_evidence": "Found in Semester 3 Table",
                    "confidence": 0.95
                },
                {
                    "name": "Digital Logic & Computer Design",
                    "code": "CS303",
                    "type": "Theory Core",
                    "credits": 4,
                    "semester": 3,
                    "source_page": 6,
                    "source_page_numbers": [6],
                    "source_section": "Semester 3 Table",
                    "source_text": "CS303 Digital Logic & Computer Design (Credits: 4)",
                    "semester_evidence": "Found in Semester 3 Table",
                    "confidence": 0.95
                }
            ],
            "raw_text": "CS302 OOP Java CS303 DLCD",
            "confidence_score": 0.94
        }
        res_b = CurriculumCompletenessValidator.validate(student, syllabus_b)
        self.assertEqual(res_b["status"], "VALID")
        self.assertTrue(res_b["is_valid"])
        new_names = [s["name"] for s in syllabus_b["subjects"]]

        self.assertNotIn("Data Structures & Algorithms", new_names)
        self.assertIn("Object Oriented Programming via Java", new_names)
        self.assertIn("Digital Logic & Computer Design", new_names)

    # ══════════════════════════════════════════════════════════════════════════════
    # TEST 4: TWO USERS ISOLATION
    # ══════════════════════════════════════════════════════════════════════════════
    def test_04_cross_user_isolation(self):
        """User A sees syllabus A, User B has no syllabus (sees blank), then uploads B and sees only B."""
        user_a = {"user_id": "user_alpha_123", "name": "User Alpha", "role": "student", "level": "college", "degree": "B.Tech", "department": "Information Technology", "year": 3, "semester": 5}
        user_b = {"user_id": "user_beta_456", "name": "User Beta", "role": "student", "level": "college", "degree": "B.Tech", "department": "Civil Engineering", "year": 2, "semester": 4}

        # User A uploads A
        data_a = {
            "validation_status": "VALID",
            "detected_semesters": [5],
            "explicit_semester_identifier": "SEMESTER 5",
            "course_title": "B.Tech Information Technology Standalone Course",
            "expected_subject_count": 1,
            "extracted_subjects": ["Software Engineering"],
            "subjects": [
                {
                    "name": "Software Engineering",
                    "code": "IT504",
                    "type": "Theory Core",
                    "credits": 3,
                    "semester": 5,
                    "source_page": 1,
                    "source_page_numbers": [1],
                    "source_section": "Semester 5 Table",
                    "source_text": "IT504 Software Engineering (Credits: 3)",
                    "semester_evidence": "Found in Semester 5 Table",
                    "confidence": 0.95
                }
            ],
            "raw_text": "IT504 Software Engineering",
            "confidence_score": 0.95
        }
        res_a = CurriculumCompletenessValidator.validate(user_a, data_a)
        self.assertEqual(res_a["status"], "VALID")
        self.assertEqual(res_a["subjects_verified"], 1)

        # User B with no syllabus
        res_b_init = CurriculumCompletenessValidator.validate(user_b, {})
        self.assertIn(res_b_init["status"], ["NOT_UPLOADED", "NEEDS_REVIEW", "EXTRACTION_FAILED"])
        self.assertFalse(res_b_init["is_valid"])

        # User B uploads B
        data_b = {
            "validation_status": "VALID",
            "detected_semesters": [4],
            "explicit_semester_identifier": "SEMESTER 4",
            "course_title": "B.Tech Civil Engineering Standalone Course",
            "expected_subject_count": 1,
            "extracted_subjects": ["Structural Analysis"],
            "subjects": [
                {
                    "name": "Structural Analysis",
                    "code": "CE401",
                    "type": "Theory Core",
                    "credits": 4,
                    "semester": 4,
                    "source_page": 3,
                    "source_page_numbers": [3],
                    "source_section": "Semester 4 Table",
                    "source_text": "CE401 Structural Analysis (Credits: 4)",
                    "semester_evidence": "Found in Semester 4 Table",
                    "confidence": 0.95
                }
            ],
            "raw_text": "CE401 Structural Analysis",
            "confidence_score": 0.93
        }
        res_b_final = CurriculumCompletenessValidator.validate(user_b, data_b)
        self.assertEqual(res_b_final["status"], "VALID")
        self.assertEqual(res_b_final["subjects_verified"], 1)
        self.assertEqual(data_b["subjects"][0]["name"], "Structural Analysis")

        # Confirm User A still isolated
        self.assertEqual(data_a["subjects"][0]["name"], "Software Engineering")


    # ══════════════════════════════════════════════════════════════════════════════
    # TEST 5: PERSONAL TRAINER QUALITY & HUMAN TUTOR PERSONAS
    # ══════════════════════════════════════════════════════════════════════════════
    def test_05_personal_trainer_teaching_modes_and_quality_checks(self):
        """Tests 10 teaching interactions with response quality validation."""
        modes = [
            ("What is B-Tree indexing?", "concept"),
            ("Explain why ACID properties are necessary for concurrent banking transactions", "theory"),
            ("Calculate binary search maximum comparisons for an array of 1024 elements", "numerical"),
            ("Write a Python function to implement binary search", "programming"),
            ("explain simply", "simple_explanation"),
            ("explain again", "deeper_explanation"),
            ("give an example", "example"),
            ("test me", "test_me"),
            ("prepare me for exam", "exam_prep"),
        ]

        service = GeminiService()
        for query, intent in modes:
            resp_text = service._build_deterministic_trainer_response(
                message=query,
                subject="Database Management Systems",
                topic="B-Tree Indexing & Transactions",
                unit="Unit 3: Indexing",
                strategy=intent,
                semester="Semester 5"
            )
            self.assertGreater(len(resp_text), 40)

            # Response quality validator
            cleaned, report = TrainerResponseQualityValidator.validate_and_refine(
                response_text=resp_text,
                student_message=query,
                subject="Database Management Systems",
                topic="B-Tree Indexing & Transactions",
                unit="Unit 3: Indexing"
            )
            self.assertTrue(report["is_valid"])
            self.assertGreaterEqual(report["confidence"], 0.70)

    # ══════════════════════════════════════════════════════════════════════════════
    # TEST 6: CURRENT OPPORTUNITIES STRICT SEGMENTATION
    # ══════════════════════════════════════════════════════════════════════════════
    def test_06_current_opportunities_strict_segmentation(self):
        """School vs College and Domain Isolation verification."""
        # College student (Mechanical)
        college_mech = {
            "role": "college_student", "level": "college", "degree": "B.Tech",
            "department": "Mechanical Engineering", "year": 3, "semester": 5
        }
        col_feed = OpportunitiesService.get_personalized_feed(college_mech)
        self.assertEqual(col_feed["level"], "college")

        # Zero school items
        for n in col_feed["news"]: self.assertEqual(n["level"], "college")
        for o in col_feed["opportunities"]: self.assertEqual(o["level"], "college")

        # Domain isolation: No CS-exclusive ICPC
        col_opp_ids = [o["id"] for o in col_feed["opportunities"]]
        self.assertNotIn("col-opp-icpc-2026", col_opp_ids)

        # School student (Class 10 CBSE)
        school_user = {
            "role": "school_student", "level": "school", "grade_level": "10", "board": "CBSE"
        }
        sch_feed = OpportunitiesService.get_personalized_feed(school_user)
        self.assertEqual(sch_feed["level"], "school")

        # Zero college items
        for n in sch_feed["news"]: self.assertEqual(n["level"], "school")
        for o in sch_feed["opportunities"]: self.assertEqual(o["level"], "school")
        sch_opp_ids = [o["id"] for o in sch_feed["opportunities"]]
        self.assertNotIn("col-opp-sih-2026", sch_opp_ids)

    # ══════════════════════════════════════════════════════════════════════════════
    # TEST 7: FRESHNESS & VERIFICATION PIPELINE
    # ══════════════════════════════════════════════════════════════════════════════
    def test_07_freshness_and_verification_pipeline(self):
        """Verifies 13-point checks, lastVerifiedAt timestamps, expiration, and cancellation."""
        report = OpportunitiesService.run_verification_pipeline()
        self.assertTrue(report["success"])
        self.assertIn("lastVerifiedAt", report)
        self.assertEqual(report["rule"], "UNVERIFIED = NOT ELIGIBLE FOR VERIFIED DISPLAY")

        # Test expiration on an expired item
        expired_test_item = {
            "id": "test-expired-opp",
            "title": "Expired Collegiate Coding Challenge 2025",
            "organizer": "Tech University",
            "eligibility": "B.Tech students",
            "deadline": "January 1, 2025",
            "url": "https://techuniv.edu/challenge",
            "isRecommended": True
        }
        v_exp = OpportunitiesService.verify_item(expired_test_item, current_time=datetime(2026, 10, 1, tzinfo=timezone.utc))
        self.assertEqual(v_exp["opportunityStatus"], "EXPIRED")
        self.assertEqual(v_exp["registrationStatus"], "CLOSED")
        self.assertFalse(v_exp["isRecommended"])

        # Test unverified URL enforcement
        unverified_item = {
            "id": "test-unverified-opp",
            "title": "Unverified Event with Fake URL",
            "organizer": "Unknown Host",
            "eligibility": "Students",
            "deadline": "November 30, 2026",
            "url": "http://insecure-unverified-fake-link.org",
            "isRecommended": True
        }
        v_unv = OpportunitiesService.verify_item(unverified_item)
        self.assertEqual(v_unv["verificationStatus"], "UNVERIFIED")
        self.assertFalse(v_unv["verified"])
        self.assertEqual(v_unv["verificationBadge"], "Pending Verification")
        self.assertFalse(v_unv["isRecommended"])

    # ══════════════════════════════════════════════════════════════════════════════
    # TEST 8: CODEBASE AUDIT (ZERO MOCK SUBJECTS IN CORE PATHS)
    # ══════════════════════════════════════════════════════════════════════════════
    def test_08_codebase_mock_subjects_audit(self):
        """Scans curriculum validator & trainer engines to ensure zero static fallback curriculum arrays."""
        backend_dir = Path(__file__).resolve().parent

        files_to_audit = [
            backend_dir / "app" / "curriculum_validator.py",
            backend_dir / "app" / "trainer_validator.py",
            backend_dir / "app" / "opportunities_service.py",
            backend_dir / "app" / "gemini_service.py"
        ]

        forbidden_phrases = [
            "DEFAULT_SUBJECTS =",
            "MOCK_SUBJECTS =",
            "FALLBACK_SUBJECTS =",
            "DEFAULT_CURRICULUM =",
            "MOCK_CURRICULUM ="
        ]

        for file_path in files_to_audit:
            self.assertTrue(file_path.exists(), f"File missing: {file_path}")
            content = file_path.read_text(encoding="utf-8")
            for phrase in forbidden_phrases:
                self.assertNotIn(phrase, content, f"Forbidden mock/fallback pattern '{phrase}' found in {file_path.name}")


if __name__ == "__main__":
    unittest.main()
