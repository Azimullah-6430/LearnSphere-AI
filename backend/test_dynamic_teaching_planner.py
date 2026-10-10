"""
LearnSphere AI - Dynamic Teaching Planner Unit Test Suite

Verifies:
  1. Dynamic plan creation across any subject/topic without fixed lists or hardcoded templates.
  2. Classification of topic natures (theoretical, numerical, practical, procedural, creative, interpretive, language-based, programming-oriented).
  3. Student profile differentiation (SCHOOL vs COLLEGE) and verified academic details.
  4. Inferred prerequisites, explanation strategies, practice methods, and understanding checks.
  5. Clarification handling for empty or ambiguous topic requests.
  6. Backend endpoint integration (/api/learn-anywhere/plan).
"""

import unittest
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.teaching_planner import DynamicTeachingPlanner, teaching_planner
from server import app, get_mongodb


class TestDynamicTeachingPlanner(unittest.TestCase):

    def setUp(self):
        self.planner = DynamicTeachingPlanner()
        self.app = app
        self.client = app.test_client()
        self.student_id = "stu_planner_test_001"

        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_id
            sess["user"] = {
                "id": self.student_id,
                "user_id": self.student_id,
                "role": "student",
                "name": "Alex Student",
                "degree": "B.Tech",
                "department": "Computer Science & Humanities",
                "semester": 3
            }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            try:
                mongo_db.users.delete_many({"_id": self.student_id})
                mongo_db.syllabi.delete_many({"user_id": self.student_id})
            except Exception:
                pass

            mongo_db.users.insert_one({
                "_id": self.student_id,
                "id": self.student_id,
                "user_id": self.student_id,
                "email": "planner@learn.edu",
                "role": "student",
                "full_name": "Alex Student"
            })

            mongo_db.syllabi.insert_one({
                "user_id": self.student_id,
                "student_id": self.student_id,
                "syllabus_id": "syl_plan_101",
                "is_active": True,
                "status": "VALID",
                "validation_status": "VALID",
                "target_semester": 3,
                "subjects": [
                    {"name": "Data Structures & Algorithms", "topics": ["B-Trees", "Graph Search"]},
                    {"name": "Classical Literature", "topics": ["Shakespearean Tragedy", "Victorian Novels"]},
                    {"name": "Cost Accounting", "topics": ["Variance Analysis", "Ledger Reconciliation"]},
                    {"name": "Organic Chemistry", "topics": ["Electrophilic Addition"]}
                ],
                "chapters": {
                    "Data Structures & Algorithms": ["B-Trees", "Graph Search"],
                    "Classical Literature": ["Shakespearean Tragedy", "Victorian Novels"],
                    "Cost Accounting": ["Variance Analysis", "Ledger Reconciliation"],
                    "Organic Chemistry": ["Electrophilic Addition"]
                }
            })

    def test_01_topic_nature_classification(self):
        """Verify dynamic topic nature detection across diverse academic fields."""
        # Programming
        nature_cs = self.planner.detect_topic_nature("Data Structures", "B-Tree Insertion")
        self.assertEqual(nature_cs, "programming-oriented")

        # Numerical
        nature_math = self.planner.detect_topic_nature("Calculus", "Differential Equations")
        self.assertEqual(nature_math, "numerical")

        # Practical
        nature_chem = self.planner.detect_topic_nature("Chemistry", "Acid-Base Titration")
        self.assertEqual(nature_chem, "practical")

        # Interpretive / Humanities
        nature_lit = self.planner.detect_topic_nature("Literature", "Shakespearean Tragedy")
        self.assertEqual(nature_lit, "interpretive")

        # Language
        nature_lang = self.planner.detect_topic_nature("Spanish", "Verb Conjugation Syntax")
        self.assertEqual(nature_lang, "language-based")

        # Creative
        nature_art = self.planner.detect_topic_nature("Digital Arts", "UI/UX Layout Composition")
        self.assertEqual(nature_art, "creative")

        # Procedural
        nature_med = self.planner.detect_topic_nature("Clinical Nursing", "Standard Operating Diagnosis Protocol")
        self.assertEqual(nature_med, "procedural")

    def test_02_school_vs_college_profile(self):
        """Verify teaching planner adapts structure to SCHOOL vs COLLEGE profile."""
        school_prof = {"level": "SCHOOL", "grade": "Class 10", "stream": "Science"}
        plan_school = self.planner.create_teaching_plan("Physics", "Ohm's Law", school_prof)
        self.assertEqual(plan_school["student_type"], "SCHOOL")
        self.assertEqual(plan_school["academic_profile"]["grade"], "Class 10")

        college_prof = {"level": "COLLEGE", "degree": "B.Tech", "department": "ECE", "semester": "4"}
        plan_college = self.planner.create_teaching_plan("Physics", "Semiconductor Diodes", college_prof)
        self.assertEqual(plan_college["student_type"], "COLLEGE")
        self.assertEqual(plan_college["academic_profile"]["department"], "ECE")

    def test_03_prerequisites_and_explanation_strategy(self):
        """Verify prerequisites and strategies are dynamically generated for any topic."""
        plan = self.planner.create_teaching_plan(
            subject="Data Structures & Algorithms",
            topic="B-Trees",
            student_profile={"level": "COLLEGE", "degree": "B.Tech", "department": "CS", "semester": 3}
        )
        self.assertTrue(plan["is_valid"])
        self.assertFalse(plan["needs_clarification"])
        self.assertIn("Pointers", str(plan["prerequisites"]))
        self.assertIn("Algorithmic", plan["teaching_approach"])
        self.assertTrue(len(plan["understanding_checks"]) >= 3)

    def test_04_clarification_handling_for_ambiguous_topics(self):
        """Verify planner asks a focused clarification question for empty/ambiguous topics."""
        plan_empty = self.planner.create_teaching_plan("Chemistry", "", {"level": "COLLEGE"})
        self.assertTrue(plan_empty["needs_clarification"])
        self.assertIn("select a valid subject and specific topic", plan_empty["clarification_question"])

        plan_vague = self.planner.create_teaching_plan("Chemistry", "x", {"level": "COLLEGE"})
        self.assertTrue(plan_vague["needs_clarification"])
        self.assertIn("ambiguous", plan_vague["clarification_question"])

    def test_05_plan_api_endpoint(self):
        """Verify /api/learn-anywhere/plan HTTP endpoint."""
        payload = {
            "subject": "Data Structures & Algorithms",
            "topic": "B-Trees"
        }
        res = self.client.post("/api/learn-anywhere/plan", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        plan = data.get("teaching_plan")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.get("selected_subject"), "Data Structures & Algorithms")
        self.assertEqual(plan.get("selected_topic"), "B-Trees")
        self.assertEqual(plan.get("topic_nature"), "programming-oriented")

    def test_06_unmatched_subject_api_rejection(self):
        """Verify /api/learn-anywhere/plan rejects subjects not in curriculum."""
        payload = {
            "subject": "Quantum Astrodynamics",
            "topic": "Wormhole Metrics"
        }
        res = self.client.post("/api/learn-anywhere/plan", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("not present in your active validated curriculum", data.get("error"))


if __name__ == "__main__":
    unittest.main()
