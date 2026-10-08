import unittest
from app.gemini_service import gemini_service
from server import app

class TestComprehensiveSubjectExtraction(unittest.TestCase):
    """
    Test suite for complete, rock-solid subject extraction algorithm:
    1. Multi-page tables with page breaks & repeated table headers
    2. Multi-line wrapped subject names and separated codes
    3. Complete course type extraction:
       - Theory Core
       - Laboratory / Practical
       - Project / Seminar / Capstone
       - Professional Electives
       - Open Electives
       - Mandatory / Audit Non-Credit Courses
       - Humanities / Management
    4. Exact credit information (integers, floating point 1.5, zero credits 0.0, L-T-P-C)
    5. Subjects appearing under category and elective headings
    6. Presence of all 11 canonical fields for EVERY subject:
       subjectId, subjectCode, subjectName, courseType, credits, semester, program, department, sourcePages, sourceText, extractionConfidence
    7. Anti-hallucination and no artificial count limits (extracts 100% of curriculum section).
    """

    def setUp(self):
        self.client = app.test_client()

    def test_01_multipage_table_with_repeated_headers_and_wrapped_names(self):
        """Verify extraction across page breaks with repeated headers and multi-line wrapped cells."""
        multipage_doc = """
--- Page 1 ---
ANNA UNIVERSITY :: CHENNAI
AFFILIATED INSTITUTIONS
B.TECH. INFORMATION TECHNOLOGY
REGULATIONS - 2021
CHOICE BASED CREDIT SYSTEM
SEMESTER V

| S.No | Course Code | Course Title | Category | L | T | P | C |
|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| 1 | IT3501 | Database Management Systems | Theory Core | 3 | 0 | 0 | 3.0 |
| 2 | CS3591 | Computer Networks | Theory Core | 3 | 0 | 0 | 3.0 |
| 3 | IT3511 | Web Technologies | Theory Core | 3 | 0 | 2 | 4.0 |
| 4 | CS3551 | Distributed Systems and | Theory Core | 3 | 0 | 0 | 3.0 |
|   |        | Cloud Computing         |             |   |   |   |     |

--- Page 2 ---
ANNA UNIVERSITY :: CHENNAI
B.TECH. INFORMATION TECHNOLOGY
SEMESTER V (Continued)

| S.No | Course Code | Course Title | Category | L | T | P | C |
|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| 5 | PE3501 | Professional Elective I: Advanced | Professional Elective | 3 | 0 | 0 | 3.0 |
|   |        | Database Technologies             |                       |   |   |   |     |
| 6 | OE3501 | Open Elective I: Industrial IoT | Open Elective | 3 | 0 | 0 | 3.0 |
| 7 | MC3501 | Constitution of India | Mandatory Audit | 2 | 0 | 0 | 0.0 |
| 8 | IT3521 | Database Management Systems Laboratory | Laboratory | 0 | 0 | 4 | 2.0 |
| 9 | IT3531 | Web Technologies Laboratory | Laboratory | 0 | 0 | 3 | 1.5 |
| 10 | IT3541 | Mini Project and Technical Seminar | Project/Seminar | 0 | 0 | 2 | 1.0 |
| 11 | HS3501 | Professional Communication | Humanities | 1 | 0 | 2 | 2.0 |
"""
        res = gemini_service._deterministic_syllabus_parser(
            multipage_doc,
            target_semester=5,
            level="college",
            dept_str="Information Technology",
            prog_str="B.Tech"
        )

        self.assertEqual(res.get("validation_status"), "VALID")
        subjects = res.get("subjects", [])
        self.assertEqual(len(subjects), 11, f"Expected 11 subjects, got {len(subjects)}: {[s['name'] for s in subjects]}")

        # Check every subject has all 11 required fields
        required_fields = [
            "subjectId", "subjectCode", "subjectName", "courseType",
            "credits", "semester", "program", "department",
            "sourcePages", "sourceText", "extractionConfidence"
        ]
        for sub in subjects:
            for field in required_fields:
                self.assertIn(field, sub, f"Missing required field '{field}' in subject: {sub}")

        sub_map = {s["subjectCode"]: s for s in subjects if s.get("subjectCode")}

        # Test multi-line wrapped name on page 1
        self.assertIn("CS3551", sub_map)
        self.assertIn("Distributed Systems and Cloud Computing", sub_map["CS3551"]["subjectName"])
        self.assertEqual(sub_map["CS3551"]["credits"], 3.0)

        # Test multi-line wrapped elective on page 2
        self.assertIn("PE3501", sub_map)
        self.assertIn("Advanced Database Technologies", sub_map["PE3501"]["subjectName"])
        self.assertEqual(sub_map["PE3501"]["courseType"], "Professional Elective")

        # Test floating-point credit lab
        self.assertIn("IT3531", sub_map)
        self.assertEqual(sub_map["IT3531"]["credits"], 1.5)
        self.assertEqual(sub_map["IT3531"]["courseType"], "Laboratory")

        # Test mandatory audit zero credits
        self.assertIn("MC3501", sub_map)
        self.assertEqual(sub_map["MC3501"]["credits"], 0.0)
        self.assertEqual(sub_map["MC3501"]["courseType"], "Mandatory Audit")

        # Test project / seminar
        self.assertIn("IT3541", sub_map)
        self.assertEqual(sub_map["IT3541"]["courseType"], "Project/Seminar")

    def test_02_space_delimited_scheme_with_separated_lines_and_elective_headings(self):
        """Verify line-delimited scheme parser where codes, wrapped names, and headings are on separate lines."""
        scheme_doc = """
JAWAHARLAL NEHRU TECHNOLOGICAL UNIVERSITY
B.TECH IN COMPUTER SCIENCE AND ENGINEERING
III YEAR - SEMESTER V CURRICULUM

THEORY COURSES
1. CS501
Formal Languages and Automata
Theory
3 0 0 3.0

2. CS502 Design and Analysis of
Algorithms
Credits: 4.0

3. CS503 Operating Systems Concepts
L:3 T:0 P:0 C:3

PROFESSIONAL ELECTIVES - I
4. PE501 Artificial Intelligence &
Machine Learning
3 0 0 3.0

5. PE502 Cyber Security and Privacy
Credits: 3

OPEN ELECTIVES - I
6. OE501 Renewable Energy Engineering
Credits: 3.0

MANDATORY COURSES (NON-CREDIT)
7. MC501 Environmental Science
Credits: 0.0

LABORATORY & PRACTICAL COURSES
8. CS504 Algorithms Simulation and
Analysis Laboratory
0 0 4 2.0

9. CS505 Operating Systems Laboratory
0 0 3 1.5

EMPLOYABILITY ENHANCEMENT COURSES (EEC)
10. CS506 Mini Project & Capstone Phase I
0 0 2 1.0
"""
        res = gemini_service._deterministic_syllabus_parser(
            scheme_doc,
            target_semester=5,
            level="college",
            dept_str="Computer Science and Engineering",
            prog_str="B.Tech"
        )

        self.assertEqual(res.get("validation_status"), "VALID")
        subjects = res.get("subjects", [])
        self.assertEqual(len(subjects), 10, f"Expected 10 subjects, got {len(subjects)}: {[s['name'] for s in subjects]}")

        sub_map = {s["subjectCode"]: s for s in subjects if s.get("subjectCode")}

        # Check line 1 code separated from wrapped title
        self.assertIn("CS501", sub_map)
        self.assertIn("Formal Languages and Automata Theory", sub_map["CS501"]["subjectName"])
        self.assertEqual(sub_map["CS501"]["credits"], 3.0)

        # Check wrapped title with credits on next line
        self.assertIn("CS502", sub_map)
        self.assertIn("Design and Analysis of Algorithms", sub_map["CS502"]["subjectName"])
        self.assertEqual(sub_map["CS502"]["credits"], 4.0)

        # Check elective heading inheritance
        self.assertIn("PE501", sub_map)
        self.assertEqual(sub_map["PE501"]["courseType"], "Professional Elective")

        self.assertIn("OE501", sub_map)
        self.assertEqual(sub_map["OE501"]["courseType"], "Open Elective")

        # Check mandatory course zero credits
        self.assertIn("MC501", sub_map)
        self.assertEqual(sub_map["MC501"]["courseType"], "Mandatory Audit")
        self.assertEqual(sub_map["MC501"]["credits"], 0.0)

        # Check lab with decimal credits
        self.assertIn("CS505", sub_map)
        self.assertEqual(sub_map["CS505"]["courseType"], "Laboratory")
        self.assertEqual(sub_map["CS505"]["credits"], 1.5)

        # Check project / EEC
        self.assertIn("CS506", sub_map)
        self.assertEqual(sub_map["CS506"]["courseType"], "Project/Seminar")

if __name__ == "__main__":
    unittest.main()
