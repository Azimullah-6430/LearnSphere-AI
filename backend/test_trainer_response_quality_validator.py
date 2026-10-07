"""
LearnSphere AI - Personal Trainer Response-Quality Validation Test Suite

Verifies:
1. Relevance to student query
2. Consistency with subject/topic
3. Syllabus consistency
4. Formula accuracy
5. Numerical calculations (Independent arithmetic check)
6. Units correctness
7. Code syntax and logical soundness (AST parser)
8. Academic definition correctness
9. Example relevance
10. Addressing student confusion
11. Hallucination / banned AI metadata filtering
12. Cross-subject isolation (zero accidental topic drift)
13. Calibrated difficulty level
14. Non-leakage of internal validation metadata to student
15. Communication of academic uncertainty when confidence is low
"""

import os
import sys
import unittest

# Set up path to backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.trainer_validator import TrainerResponseQualityValidator


class TestTrainerResponseQualityValidator(unittest.TestCase):

    def test_01_valid_theory_response_passes(self):
        """Verify high-quality valid theory response passes validation with high confidence."""
        text = (
            "📚 **BCNF Normalization in Database Management Systems**\n\n"
            "Boyce-Codd Normal Form (BCNF) is an advanced normal form used in database design.\n\n"
            "### 1. Definition\n"
            "A relation R is in BCNF if for every non-trivial functional dependency X -> Y, X is a superkey.\n\n"
            "### 2. Example\n"
            "Consider a table `Student_Advisor(student_id, advisor, department)`. If each student can have multiple advisors but each advisor belongs to only one department, BCNF decomposition separates them into distinct tables.\n\n"
            "### 3. Exam Tip\n"
            "Always state that BCNF is strictly stronger than 3NF."
        )
        cleaned, report = TrainerResponseQualityValidator.validate_and_refine(
            response_text=text,
            student_message="Explain BCNF normalization in DBMS",
            subject="Database Management Systems",
            topic="BCNF Normalization",
            unit="Unit II: Relational Model"
        )
        self.assertTrue(report["is_valid"])
        self.assertGreaterEqual(report["confidence"], 0.75)
        self.assertIn("Boyce-Codd Normal Form", cleaned)

    def test_02_numerical_calculation_independent_check(self):
        """Verify independent arithmetic evaluation catches faulty calculations."""
        # Incorrect calculation: 10 * 5 = 60
        faulty_math_text = (
            "Let's calculate the throughput:\n"
            "Given bandwidth = 10 Mbps and time = 5 seconds:\n"
            "Total Data Transferred = 10 * 5 = 60 Mb\n"
        )
        cleaned, report = TrainerResponseQualityValidator.validate_and_refine(
            response_text=faulty_math_text,
            student_message="Calculate total data transferred",
            subject="Computer Networks",
            topic="Throughput Calculation"
        )
        # Check that the arithmetic check identified the mismatch
        num_check = report["checks"]["numerical_calculations"]
        self.assertFalse(num_check["passed"])
        self.assertIn("Arithmetic mismatch", num_check["details"])

    def test_03_code_syntax_ast_verification(self):
        """Verify AST code parser flags broken syntax in code examples."""
        broken_code_text = (
            "Here is the Python implementation of Binary Search:\n\n"
            "```python\n"
            "def binary_search(arr, target\n"  # Missing closing parenthesis and colon
            "    left = 0\n"
            "    right = len(arr) - 1\n"
            "```\n"
        )
        cleaned, report = TrainerResponseQualityValidator.validate_and_refine(
            response_text=broken_code_text,
            student_message="Show me python binary search",
            subject="Data Structures and Algorithms",
            topic="Binary Search"
        )
        code_check = report["checks"]["code_syntax_and_logic"]
        self.assertFalse(code_check["passed"])
        self.assertIn("syntax error", code_check["details"].lower())

    def test_04_cross_subject_drift_detection(self):
        """Verify validator flags and blocks cross-subject topic contamination."""
        # Explaining mechanical thermodynamics when subject is Database Management Systems
        contaminated_text = (
            "In Database Management Systems, we must study the Carnot cycle, rankine efficiency, "
            "entropy generation, and internal combustion otto cycle heat transfer in order to optimize systems."
        )
        cleaned, report = TrainerResponseQualityValidator.validate_and_refine(
            response_text=contaminated_text,
            student_message="Explain DBMS optimization",
            subject="Database Management Systems",
            topic="Query Optimization"
        )
        iso_check = report["checks"]["cross_subject_isolation"]
        self.assertFalse(iso_check["passed"])
        self.assertIn("Cross-subject drift detected", iso_check["details"])
        # Should sanitize/replace with safe academic clarification
        self.assertNotIn("Carnot cycle", cleaned)
        self.assertIn("Academic Clarification", cleaned)

    def test_05_internal_debug_non_leakage(self):
        """Verify internal validation tags and LLM self-referential markers are never shown to students."""
        leaked_metadata_text = (
            "[DEBUG: model=gemini-3.6-flash latency=120ms]\n"
            "[VALIDATION: confidence=0.98 checked=True]\n"
            "As an AI language model, SQL Normalization is the process of organizing data in a database."
        )
        cleaned, report = TrainerResponseQualityValidator.validate_and_refine(
            response_text=leaked_metadata_text,
            student_message="What is SQL normalization?",
            subject="Database Management Systems",
            topic="Normalization"
        )
        self.assertNotIn("[DEBUG:", cleaned)
        self.assertNotIn("[VALIDATION:", cleaned)
        self.assertNotIn("As an AI language model", cleaned)
        self.assertIn("SQL Normalization", cleaned)

    def test_06_low_confidence_uncertainty_communication(self):
        """Verify insufficient confidence results in polite academic uncertainty instead of hallucinated facts."""
        gibberish_text = "abc xyz"
        cleaned, report = TrainerResponseQualityValidator.validate_and_refine(
            response_text=gibberish_text,
            student_message="Explain hyper-quantum database serialization",
            subject="Database Management Systems",
            topic="Serialization"
        )
        self.assertFalse(report["is_valid"])
        self.assertIn("Academic Clarification", cleaned)
        self.assertIn("Database Management Systems", cleaned)


if __name__ == "__main__":
    unittest.main()
