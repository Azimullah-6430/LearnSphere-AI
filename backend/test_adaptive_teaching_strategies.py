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
        self.assertIn("Visual Loop", plan_school["teaching_approach"])
        self.assertIn("Big-O Complexity", plan_college["teaching_approach"])

        # Verify terminology and depth differ
        self.assertIn("simple language", plan_school["explanation_strategy"].lower())
        self.assertIn("big-o", plan_college["explanation_strategy"].lower())
        self.assertIn("introductory", plan_school["learning_depth"].lower())
        self.assertIn("advanced", plan_college["learning_depth"].lower())

        # Verify understanding checks differ
        self.assertIn("starting value", plan_school["understanding_checks"][0].lower())
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

        self.assertIn("Step-by-Step Visual", plan_school["teaching_approach"])
        self.assertIn("First-Principles", plan_college["teaching_approach"])

        self.assertIn("everyday examples", plan_school["explanation_strategy"].lower())
        self.assertIn("axioms", plan_college["explanation_strategy"].lower())

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


if __name__ == "__main__":
    unittest.main()
