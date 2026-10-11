"""
LearnSphere AI - Adaptive Teaching Strategies Unit & Integration Test Suite

Verifies:
  1. SCHOOL MODE vs COLLEGE MODE differentiation within the Universal Teaching Engine (teaching_planner.py).
  2. Authentic student profile source of truth: Student type and academic level are determined strictly from
     the authenticated student's saved DB profile and validated curriculum, ignoring client payload overrides.
  3. Meaningful pedagogical differentiation in depth, terminology, methods, guidelines, and understanding checks
     across identical concepts (e.g. Programming Loops, Mathematics Derivatives, Financial Ledgers, History).
"""

import unittest
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.teaching_planner import DynamicTeachingPlanner, teaching_planner
from server import app, get_mongodb


class TestAdaptiveTeachingStrategies(unittest.TestCase):

    def setUp(self):
        self.planner = DynamicTeachingPlanner()
        self.app = app
        self.client = app.test_client()

        self.school_student_id = "stu_school_adaptive_101"
        self.college_student_id = "stu_college_adaptive_202"

        # Setup sessions & DB records for both students
        mongo_db = get_mongodb()
        if mongo_db is not None:
            try:
                mongo_db.users.delete_many({"_id": {"$in": [self.school_student_id, self.college_student_id]}})
                mongo_db.syllabi.delete_many({"user_id": {"$in": [self.school_student_id, self.college_student_id]}})
            except Exception:
                pass

            # 1. School Student DB record
            mongo_db.users.insert_one({
                "_id": self.school_student_id,
                "id": self.school_student_id,
                "user_id": self.school_student_id,
                "email": "school_student@learn.edu",
                "role": "student",
                "level": "school",
                "grade": "Grade 8",
                "class_level": "8",
                "full_name": "School Student"
            })

            mongo_db.syllabi.insert_one({
                "user_id": self.school_student_id,
                "student_id": self.school_student_id,
                "syllabus_id": "syl_school_888",
                "is_active": True,
                "status": "VALID",
                "validation_status": "VALID",
                "subjects": [
                    {"name": "Computer Science", "topics": ["Loop Constructs", "Variables"]},
                    {"name": "Mathematics", "topics": ["Rate of Change", "Fractions"]},
                    {"name": "Commerce & Bookkeeping", "topics": ["Cash Ledger", "Income & Expense"]},
                    {"name": "World History", "topics": ["Industrial Revolution", "Timelines"]}
                ],
                "chapters": {
                    "Computer Science": ["Loop Constructs", "Variables"],
                    "Mathematics": ["Rate of Change", "Fractions"],
                    "Commerce & Bookkeeping": ["Cash Ledger", "Income & Expense"],
                    "World History": ["Industrial Revolution", "Timelines"]
                }
            })

            # 2. College Student DB record
            mongo_db.users.insert_one({
                "_id": self.college_student_id,
                "id": self.college_student_id,
                "user_id": self.college_student_id,
                "email": "college_student@learn.edu",
                "role": "student",
                "level": "college",
                "degree": "B.Tech Computer Science",
                "program": "B.Tech",
                "department": "Computer Science & Engineering",
                "year": "3rd Year",
                "semester": 5,
                "full_name": "College Student"
            })

            mongo_db.syllabi.insert_one({
                "user_id": self.college_student_id,
                "student_id": self.college_student_id,
                "syllabus_id": "syl_college_999",
                "is_active": True,
                "status": "VALID",
                "validation_status": "VALID",
                "target_semester": 5,
                "subjects": [
                    {"name": "Computer Science", "topics": ["Loop Constructs", "Variables"]},
                    {"name": "Mathematics", "topics": ["Rate of Change", "Fractions"]},
                    {"name": "Commerce & Bookkeeping", "topics": ["Cash Ledger", "Income & Expense"]},
                    {"name": "World History", "topics": ["Industrial Revolution", "Timelines"]}
                ],
                "chapters": {
                    "Computer Science": ["Loop Constructs", "Variables"],
                    "Mathematics": ["Rate of Change", "Fractions"],
                    "Commerce & Bookkeeping": ["Cash Ledger", "Income & Expense"],
                    "World History": ["Industrial Revolution", "Timelines"]
                }
            })

    def test_01_programming_loop_school_vs_college(self):
        """
        Programming loop concept tested at SCHOOL vs COLLEGE levels:
        - School: simple visual flowchart, paper trace table, clear language, no Big-O assumption.
        - College: Big-O asymptotic analysis, memory allocation, loop invariants, edge cases.
        """
        school_prof = {"level": "SCHOOL", "grade": "Grade 8"}
        college_prof = {"level": "COLLEGE", "program": "B.Tech", "department": "Computer Science", "semester": 5}

        plan_school = self.planner.create_teaching_plan("Computer Science", "Loop Constructs", school_prof)
        plan_college = self.planner.create_teaching_plan("Computer Science", "Loop Constructs", college_prof)

        self.assertEqual(plan_school["student_type"], "SCHOOL")
        self.assertEqual(plan_college["student_type"], "COLLEGE")

        # Verify teaching methods differ meaningfully
        self.assertIn("Age-Appropriate", plan_school["teaching_approach"])
        self.assertIn("Complexity Analysis", plan_college["teaching_approach"])

        # Verify terminology and depth differ
        self.assertIn("age-appropriate logic", plan_school["explanation_strategy"].lower())
        self.assertIn("big-o", plan_college["explanation_strategy"].lower())
        self.assertIn("introductory", plan_school["learning_depth"].lower())
        self.assertIn("advanced", plan_college["learning_depth"].lower())

        # Verify understanding checks differ
        self.assertIn("input", plan_school["understanding_checks"][0].lower())
        self.assertIn("big-o", plan_college["understanding_checks"][0].lower())

    def test_02_mathematics_rate_of_change_school_vs_college(self):
        """
        Mathematics topic 'Rate of Change' tested at SCHOOL vs COLLEGE levels:
        - School: step-by-step visual calculations, everyday speed/hill examples, simple terms.
        - College: first-principles limit derivations, vector space analysis, formal proofs.
        """
        school_prof = {"level": "SCHOOL", "grade": "Grade 9"}
        college_prof = {"level": "COLLEGE", "department": "Mathematics", "semester": 3}

        plan_school = self.planner.create_teaching_plan("Mathematics", "Rate of Change", school_prof)
        plan_college = self.planner.create_teaching_plan("Mathematics", "Rate of Change", college_prof)

        self.assertEqual(plan_school["student_type"], "SCHOOL")
        self.assertEqual(plan_college["student_type"], "COLLEGE")

        self.assertIn("Visual Reasoning", plan_school["teaching_approach"])
        self.assertIn("First-Principles", plan_college["teaching_approach"])

        self.assertIn("real-world situations", plan_school["explanation_strategy"].lower())
        self.assertIn("prerequisites", plan_college["explanation_strategy"].lower())

    def test_03_accounting_cash_ledger_school_vs_college(self):
        """
        Accounting topic 'Cash Ledger' tested at SCHOOL vs COLLEGE levels:
        - School: shopkeeper story, 2-column cash ledger, simple debit/credit definition.
        - College: IFRS/GAAP standards, double-entry T-accounts, adjusting entries, balance sheet ratios.
        """
        school_prof = {"level": "SCHOOL", "grade": "Grade 10"}
        college_prof = {"level": "COLLEGE", "program": "B.Com", "department": "Finance", "semester": 4}

        plan_school = self.planner.create_teaching_plan("Commerce & Bookkeeping", "Cash Ledger", school_prof)
        plan_college = self.planner.create_teaching_plan("Commerce & Bookkeeping", "Cash Ledger", college_prof)

        self.assertEqual(plan_school["student_type"], "SCHOOL")
        self.assertEqual(plan_college["student_type"], "COLLEGE")

        self.assertIn("Shopkeeper Story", plan_school["teaching_approach"])
        self.assertIn("Double-Entry", plan_college["teaching_approach"])

        self.assertIn("shopkeeper", plan_school["explanation_strategy"].lower())
        self.assertIn("ifrs/gaap", plan_college["explanation_strategy"].lower())

    def test_04_history_industrial_revolution_school_vs_college(self):
        """
        History topic 'Industrial Revolution' tested at SCHOOL vs COLLEGE levels:
        - School: story timeline, key figures, simple cause-and-effect.
        - College: historiographical debates, primary source criticism, socio-economic structural models.
        """
        school_prof = {"level": "SCHOOL", "grade": "Grade 8"}
        college_prof = {"level": "COLLEGE", "department": "History", "semester": 2}

        plan_school = self.planner.create_teaching_plan("World History", "Industrial Revolution", school_prof)
        plan_college = self.planner.create_teaching_plan("World History", "Industrial Revolution", college_prof)

        self.assertEqual(plan_school["student_type"], "SCHOOL")
        self.assertEqual(plan_college["student_type"], "COLLEGE")

        self.assertIn("Story Timeline", plan_school["teaching_approach"])
        self.assertIn("Historiographical", plan_college["teaching_approach"])

    def test_05_authenticated_db_profile_is_sole_source_of_truth(self):
        """
        Verify that backend endpoints (/api/learn-anywhere/plan) lookup the authenticated
        student's DB profile as the sole source of truth and ignore client request body overrides.
        """
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.school_student_id
            sess["user"] = {
                "id": self.school_student_id,
                "user_id": self.school_student_id,
                "role": "student",
                "level": "school",
                "grade": "Grade 8"
            }

        # Client attempts to send fake 'COLLEGE' profile override in JSON body
        payload = {
            "subject": "Computer Science",
            "topic": "Loop Constructs",
            "level": "COLLEGE",
            "program": "Fake Master Degree",
            "semester": 8
        }

        response = self.client.post("/api/learn-anywhere/plan", json=payload)
        self.assertEqual(response.status_code, 200)
        res_data = response.get_json()
        self.assertTrue(res_data.get("success"))

        plan = res_data.get("teaching_plan") or {}
        # Must resolve to SCHOOL student type based on DB profile, ignoring client override
        self.assertEqual(plan.get("student_type"), "SCHOOL")
        self.assertEqual(plan.get("academic_profile", {}).get("grade"), "Grade 8")

    def test_06_math_school_topic_relevant_context(self):
        """
        Math School Mode:
        - Abstract topic ('Polynomial Factorization') uses visual/step-by-step reasoning without forcing shopping/farming.
        - Applied topic ('Perimeter and Area') uses measurement/everyday quantities.
        """
        school_prof = {"level": "SCHOOL", "grade": "Grade 9"}
        plan_abstract = self.planner.create_teaching_plan("Mathematics", "Polynomial Factorization", school_prof)
        plan_applied = self.planner.create_teaching_plan("Mathematics", "Perimeter and Area", school_prof)

        self.assertEqual(plan_abstract["student_type"], "SCHOOL")
        self.assertIn("Visual Reasoning", plan_abstract["teaching_approach"])
        self.assertIn("step-by-step", plan_abstract["explanation_strategy"].lower())

        self.assertIn("Visual Reasoning", plan_applied["teaching_approach"])

    def test_07_math_college_prerequisites_notation_proofs(self):
        """
        Math College Mode:
        - Includes prerequisites, formal mathematical notation, worked step-by-step derivations,
          first-principles proofs, and domain applications in engineering/CS/physics.
        """
        college_prof = {"level": "COLLEGE", "department": "Mathematics", "semester": 4}
        plan = self.planner.create_teaching_plan("Mathematics", "Matrix Diagonalization", college_prof)

        self.assertEqual(plan["student_type"], "COLLEGE")
        self.assertIn("First-Principles", plan["teaching_approach"])
        self.assertTrue(len(plan["prerequisites"]) > 0)
        self.assertIn("prerequisites", plan["explanation_strategy"].lower())
        self.assertIn("rigorous", plan["learning_depth"].lower())

    def test_08_cs_school_inputs_processing_outputs(self):
        """
        CS School Mode:
        - Uses age-appropriate logic, algorithms, flowcharts, pseudocode, and explicitly defines inputs, processing, outputs.
        """
        school_prof = {"level": "SCHOOL", "grade": "Grade 8"}
        plan = self.planner.create_teaching_plan("Computer Science", "Sorting Algorithms", school_prof)

        self.assertEqual(plan["student_type"], "SCHOOL")
        self.assertIn("Age-Appropriate", plan["teaching_approach"])
        self.assertIn("inputs", plan["explanation_strategy"].lower())
        self.assertIn("pseudocode", plan["practice_method"].lower())

    def test_09_cs_college_language_selection_and_performance(self):
        """
        CS College Mode:
        - Specifies topic-appropriate language (C/C++ for OS/Pointers, SQL for Databases, Python/Java for DS),
          execution, debugging, testing, and Big-O performance considerations.
        """
        college_prof = {"level": "COLLEGE", "department": "Computer Science", "semester": 5}
        plan_os = self.planner.create_teaching_plan("Computer Science", "Pointer Arithmetic & Memory Management", college_prof)
        plan_db = self.planner.create_teaching_plan("Computer Science", "Relational Database SQL Joins", college_prof)

        self.assertEqual(plan_os["student_type"], "COLLEGE")
        self.assertIn("Topic-Appropriate Language", plan_os["teaching_approach"])
        self.assertIn("big-o", plan_os["explanation_strategy"].lower())

        self.assertIn("Topic-Appropriate Language", plan_db["teaching_approach"])

    def test_10_cs_non_coding_theory_guardrail(self):
        """
        CS Non-Coding Guardrail:
        - Pure theoretical CS topics (e.g. 'Automata Theory & DFA') avoid forcing coding and focus on state transition diagrams/proofs.
        """
        college_prof = {"level": "COLLEGE", "department": "Computer Science", "semester": 6}
        plan = self.planner.create_teaching_plan("Computer Science", "Automata Theory & Turing Machines", college_prof)

        self.assertEqual(plan["student_type"], "COLLEGE")
        self.assertIn("Socratic Conceptual", plan["teaching_approach"])
        self.assertIn("theoretical", plan["explanation_strategy"].lower())


if __name__ == "__main__":
    unittest.main()

