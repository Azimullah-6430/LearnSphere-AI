import unittest
import re
from app.gemini_service import gemini_service
from app.curriculum_validator import CurriculumCompletenessValidator

class TestSyllabusExtractionPipeline(unittest.TestCase):
    """
    Comprehensive verification suite for the syllabus extraction pipeline:
    - Tables (Pipe & Column-based)
    - Multi-page subject lists and continuation across pages
    - Subject codes (Standard, AICTE, Autonomous, University, Lab formats)
    - All subject types (Theory, Lab, Professional Elective, Open Elective, Mandatory/Audit, Project/Seminar, Humanities)
    - Accurate credit and LTP parsing (including decimal and zero credits)
    - Units/topics extraction strictly from document evidence (no generic fabrication)
    - Complete source page evidence preservation
    - Anti-hallucination & uncertainty review gating
    """

    def setUp(self):
        self.college_user_sem5 = {
            "user_id": "student_pipe_001",
            "name": "Jane Doe",
            "level": "college",
            "degree": "B.Tech",
            "department": "Information Technology",
            "semester": 5,
            "current_semester": 5
        }

    def test_01_pipe_table_extraction_with_all_categories_and_credits(self):
        """Test extraction from markdown pipe tables with theory, lab, electives, mandatory, project, and floating credits."""
        pipe_table_syllabus = """
--- Page 1 ---
ANNA UNIVERSITY :: CHENNAI
B.TECH INFORMATION TECHNOLOGY - REGULATION 2021
CHOICE BASED CREDIT SYSTEM

SEMESTER V

| S.No | Course Code | Course Title | Category | L | T | P | C |
|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| 1 | IT3501 | Database Management Systems | Theory Core | 3 | 0 | 0 | 3.0 |
| 2 | CS3591 | Computer Networks | Theory Core | 3 | 0 | 0 | 3.0 |
| 3 | IT3511 | Web Technologies | Theory Core | 3 | 0 | 2 | 4.0 |
| 4 | PE3501 | Professional Elective I: Cloud Computing | Professional Elective | 3 | 0 | 0 | 3.0 |
| 5 | OE3501 | Open Elective I: Robotics & Automation | Open Elective | 3 | 0 | 0 | 3.0 |
| 6 | MC3501 | Constitution of India | Mandatory Audit | 2 | 0 | 0 | 0.0 |
| 7 | IT3521 | Database Management Systems Laboratory | Laboratory | 0 | 0 | 4 | 2.0 |
| 8 | IT3531 | Web Technologies Laboratory | Laboratory | 0 | 0 | 3 | 1.5 |
| 9 | IT3541 | Mini Project and Technical Seminar | Project/Seminar | 0 | 0 | 2 | 1.0 |
| 10 | HS3501 | Professional Communication | Humanities | 1 | 0 | 2 | 2.0 |
"""
        res = gemini_service._deterministic_syllabus_parser(
            pipe_table_syllabus,
            target_semester=5,
            level="college",
            dept_str="Information Technology",
            prog_str="B.Tech"
        )

        self.assertEqual(res.get("validation_status"), "VALID")
        subjects = res.get("subjects", [])
        self.assertEqual(len(subjects), 10)

        # Map by code
        sub_map = {s["code"]: s for s in subjects if s.get("code")}

        # 1. Database Management Systems
        self.assertIn("IT3501", sub_map)
        self.assertEqual(sub_map["IT3501"]["name"], "Database Management Systems")
        self.assertEqual(sub_map["IT3501"]["credits"], 3.0)
        self.assertEqual(sub_map["IT3501"]["type"], "Theory Core")

        # 2. Web Technologies with Practical (4 credits)
        self.assertIn("IT3511", sub_map)
        self.assertEqual(sub_map["IT3511"]["credits"], 4.0)

        # 3. Professional Elective
        self.assertIn("PE3501", sub_map)
        self.assertEqual(sub_map["PE3501"]["type"], "Professional Elective")

        # 4. Open Elective
        self.assertIn("OE3501", sub_map)
        self.assertEqual(sub_map["OE3501"]["type"], "Open Elective")

        # 5. Mandatory Audit (0.0 credits)
        self.assertIn("MC3501", sub_map)
        self.assertEqual(sub_map["MC3501"]["credits"], 0.0)
        self.assertEqual(sub_map["MC3501"]["type"], "Mandatory Audit")

        # 6. Floating-point credits Lab (1.5 credits)
        self.assertIn("IT3531", sub_map)
        self.assertEqual(sub_map["IT3531"]["credits"], 1.5)
        self.assertEqual(sub_map["IT3531"]["type"], "Laboratory")

        # 7. Project/Seminar
        self.assertIn("IT3541", sub_map)
        self.assertEqual(sub_map["IT3541"]["type"], "Project/Seminar")

        # 8. Humanities
        self.assertIn("HS3501", sub_map)
        self.assertEqual(sub_map["HS3501"]["type"], "Humanities / Management")

    def test_02_multi_page_continuation_and_source_evidence(self):
        """Test multi-page syllabus continuation across pages 1, 2, and 3 with accurate page provenance."""
        multi_page_syllabus = """
--- Page 1 ---
NATIONAL INSTITUTE OF TECHNOLOGY
DEPARTMENT OF INFORMATION TECHNOLOGY
CURRICULUM SCHEME

SEMESTER 5 (THEORY COURSES)
1. PCC-IT501 Formal Languages and Automata Theory Credits: 4 L:3 T:1 P:0
2. PCC-IT502 Design and Analysis of Algorithms Credits: 3 L:3 T:0 P:0
3. PCC-IT503 Software Engineering Credits: 3 L:3 T:0 P:0

--- Page 2 ---
DEPARTMENT OF INFORMATION TECHNOLOGY
SEMESTER 5 (ELECTIVES AND HUMANITIES CONTINUATION)
4. PEC-IT501 Professional Elective - I (Distributed Systems) Credits: 3 L:3 T:0 P:0
5. OEC-IT501 Open Elective - I (Artificial Intelligence) Credits: 3 L:3 T:0 P:0
6. HSMC-501 Principles of Management Credits: 2 L:2 T:0 P:0

--- Page 3 ---
DEPARTMENT OF INFORMATION TECHNOLOGY
SEMESTER 5 (PRACTICAL COURSES AND PROJECT)
7. PCC-IT504 Algorithms Laboratory Credits: 1.5 L:0 T:0 P:3
8. PCC-IT505 Software Engineering Laboratory Credits: 1.5 L:0 T:0 P:3
9. PROJ-IT501 Mini Project Phase I Credits: 2.0 L:0 T:0 P:4
10. MC-501 Environmental Science and Engineering Credits: 0.0 L:2 T:0 P:0
"""
        res = gemini_service._deterministic_syllabus_parser(
            multi_page_syllabus,
            target_semester=5,
            level="college",
            dept_str="Information Technology",
            prog_str="B.Tech"
        )

        self.assertEqual(res.get("validation_status"), "VALID")
        subjects = res.get("subjects", [])
        self.assertEqual(len(subjects), 10)

        # Verify page evidence mapping
        code_map = {s["code"]: s for s in subjects}

        # Page 1 subjects
        self.assertEqual(code_map["PCC-IT501"]["source_page"], 1)
        self.assertEqual(code_map["PCC-IT502"]["source_page"], 1)

        # Page 2 subjects
        self.assertEqual(code_map["PEC-IT501"]["source_page"], 2)
        self.assertEqual(code_map["OEC-IT501"]["source_page"], 2)
        self.assertEqual(code_map["HSMC-501"]["source_page"], 2)

        # Page 3 subjects
        self.assertEqual(code_map["PCC-IT504"]["source_page"], 3)
        self.assertEqual(code_map["PROJ-IT501"]["source_page"], 3)
        self.assertEqual(code_map["MC-501"]["source_page"], 3)

        # Ensure all subjects have source provenance
        for s in subjects:
            self.assertTrue(s.get("evidence_verified"))
            self.assertTrue(len(s.get("source_text", "")) > 5)
            self.assertTrue(s.get("source_page") in [1, 2, 3])

    def test_03_units_and_topics_extracted_from_document_evidence(self):
        """Test that detailed units/topics in document are extracted without inventing missing ones."""
        detailed_units_syllabus = """
--- Page 1 ---
SEMESTER 5
IT501 Database Management Systems Credits: 4
IT502 Computer Networks Credits: 3

DETAILED SYLLABUS:

IT501 DATABASE MANAGEMENT SYSTEMS
Unit I: Relational Model and Algebra, Codd's Rules, Tuple Relational Calculus
Unit II: SQL Queries, Nested Queries, Aggregate Functions, Joins, Triggers
Unit III: Normalization Theory, 1NF, 2NF, 3NF, BCNF, Multivalued Dependencies
Unit IV: Transaction Management, ACID Properties, Concurrency Control, Two Phase Locking
Unit V: Indexing and Hashing, B-Trees, B+ Trees, Query Optimization Techniques

IT502 COMPUTER NETWORKS
Unit 1: Physical Layer, Transmission Media, Switching, Topologies
Unit 2: Data Link Layer, Error Detection, Framing, Flow Control, Sliding Window
Unit 3: Network Layer, IPv4, IPv6, Routing Algorithms, OSPF, BGP
"""
        res = gemini_service._deterministic_syllabus_parser(
            detailed_units_syllabus,
            target_semester=5,
            level="college",
            dept_str="Information Technology"
        )

        self.assertEqual(res.get("validation_status"), "VALID")
        chapters = res.get("chapters", {})
        
        # Verify IT501 has all 5 exact units
        self.assertIn("Database Management Systems", chapters)
        dbms_units = chapters["Database Management Systems"]
        self.assertEqual(len(dbms_units), 5)
        self.assertIn("Relational Model", dbms_units[0]["name"])
        self.assertTrue(any("Codd" in c for c in dbms_units[0]["concepts"]))

        # Verify IT502 has exact 3 units
        self.assertIn("Computer Networks", chapters)
        cn_units = chapters["Computer Networks"]
        self.assertEqual(len(cn_units), 3)

    def test_04_completeness_validator_approves_full_extraction(self):
        """Test CurriculumCompletenessValidator validates 16-point check on full extraction."""
        syllabus_text = """
SEMESTER 5
1. IT501 Database Systems Credits: 4
2. IT502 Web Engineering Credits: 3
3. IT503 Operating Systems Credits: 3
4. IT504 Professional Elective I Credits: 3
5. IT505 Database Laboratory Credits: 2
6. IT506 Web Laboratory Credits: 2
7. MC501 Constitution of India Credits: 0
"""
        analysis = gemini_service._deterministic_syllabus_parser(
            syllabus_text,
            target_semester=5,
            level="college",
            dept_str="Information Technology"
        )

        report = CurriculumCompletenessValidator.validate(
            user=self.college_user_sem5,
            analysis=analysis,
            raw_content_or_file=syllabus_text,
            target_semester=5
        )

        self.assertEqual(report["status"], "VALID")
        self.assertTrue(report["is_valid"])
        self.assertEqual(report["cross_semester_subjects"], 0)
        self.assertEqual(report["duplicate_subjects"], 0)
        self.assertEqual(report["missing_subjects"], 0)
        self.assertEqual(report["uncertain_subjects"], 0)
        self.assertEqual(report["subjects_detected"], 7)
        self.assertEqual(report["subjects_verified"], 7)

if __name__ == "__main__":
    unittest.main()
