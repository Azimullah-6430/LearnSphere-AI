"""
LearnSphere AI - Universal Teaching Engine & Dynamic Planner Unit Test Suite

Verifies:
  1. Universal topic-driven pedagogical strategy selection across all subject domains:
     - Science (safe experiments, observations, scientific principles)
     - Mathematics (visual reasoning, worked examples, calculations, proofs)
     - Computer Science (algorithms, logic, flowcharts, code execution, testing, debugging)
     - Engineering (diagrams, derivations, calculations, simulations, design exercises)
     - Commerce & Accounting (transactions, ledger entries, financial statements, case studies)
     - Economics (graphs, numerical elasticity, models, policy applications)
     - History (timelines, causes and consequences, primary source evaluation)
     - Geography (maps, spatial reasoning, environmental data, soil/climate observations)
     - Languages (grammar rules, vocabulary, writing, communication drills)
     - Literature (themes, interpretation, close reading, evidence-based analysis)
     - Unfamiliar / New Subjects (Law, Philosophy, Agriculture) without code changes per subject.
  2. Prevention of forced inappropriate activities (no forced physical experiments or coding on literature, accounting, history, or math).
  3. Honest limitations reporting in teaching plans.
  4. Accuracy of teaching plan schema and backend integration.
"""

import unittest
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.teaching_planner import DynamicTeachingPlanner, teaching_planner
from server import app, get_mongodb


class TestUniversalTeachingEngine(unittest.TestCase):

    def setUp(self):
        self.planner = DynamicTeachingPlanner()
        self.app = app
        self.client = app.test_client()
        self.student_id = "stu_univ_engine_101"

        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_id
            sess["user"] = {
                "id": self.student_id,
                "user_id": self.student_id,
                "role": "student",
                "name": "Universal Learner",
                "degree": "B.Tech & B.Com",
                "department": "Interdisciplinary Studies",
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
                "email": "universal@learn.edu",
                "role": "student",
                "full_name": "Universal Learner"
            })

            mongo_db.syllabi.insert_one({
                "user_id": self.student_id,
                "student_id": self.student_id,
                "syllabus_id": "syl_univ_202",
                "is_active": True,
                "status": "VALID",
                "validation_status": "VALID",
                "target_semester": 3,
                "subjects": [
                    {"name": "Computer Science & Engineering", "topics": ["Merge Sort Algorithm", "Graph Traversal"]},
                    {"name": "Financial Accounting", "topics": ["Ledger Reconciliation", "Balance Sheet Analysis"]},
                    {"name": "World History", "topics": ["French Revolution", "Industrialization"]},
                    {"name": "English Literature", "topics": ["Shakespearean Tragedy", "Victorian Poetic Imagery"]},
                    {"name": "Microeconomics", "topics": ["Price Elasticity of Demand", "Supply Equilibrium"]},
                    {"name": "French Grammar", "topics": ["Subjunctive Mood Syntax", "Past Tense Conjugation"]},
                    {"name": "Physical Geography", "topics": ["Contour Map Topography", "Soil Erosion Runoff"]},
                    {"name": "Pure Mathematics", "topics": ["Calculus Derivatives", "Matrix Inversion"]},
                    {"name": "Electrical Engineering", "topics": ["Kirchhoff Circuit Analysis", "Transformer Derivation"]},
                    {"name": "Organic Chemistry", "topics": ["Acid-Base Titration", "Electrophilic Addition"]},
                    {"name": "Environmental Law", "topics": ["Jurisdictional Precedents", "Statutory Interpretation"]}
                ],
                "chapters": {
                    "Computer Science & Engineering": ["Merge Sort Algorithm", "Graph Traversal"],
                    "Financial Accounting": ["Ledger Reconciliation", "Balance Sheet Analysis"],
                    "World History": ["French Revolution", "Industrialization"],
                    "English Literature": ["Shakespearean Tragedy", "Victorian Poetic Imagery"],
                    "Microeconomics": ["Price Elasticity of Demand", "Supply Equilibrium"],
                    "French Grammar": ["Subjunctive Mood Syntax", "Past Tense Conjugation"],
                    "Physical Geography": ["Contour Map Topography", "Soil Erosion Runoff"],
                    "Pure Mathematics": ["Calculus Derivatives", "Matrix Inversion"],
                    "Electrical Engineering": ["Kirchhoff Circuit Analysis", "Transformer Derivation"],
                    "Organic Chemistry": ["Acid-Base Titration", "Electrophilic Addition"],
                    "Environmental Law": ["Jurisdictional Precedents", "Statutory Interpretation"]
                }
            })

    def test_01_computer_science_approach(self):
        """CS topics must use algorithms, flowcharts, code trace, and debugging."""
        plan = self.planner.create_teaching_plan("Computer Science", "Merge Sort Algorithm", {"level": "COLLEGE"})
        self.assertEqual(plan["topic_nature"], "programming-oriented")
        self.assertEqual(plan["demonstration_type"], "code_and_logic_simulation")
        self.assertIn("Algorithmic", plan["teaching_approach"])
        self.assertIn("tracing", plan["practice_method"].lower())

    def test_02_accounting_approach(self):
        """Commerce/Accounting topics must use ledger transactions and financial statement case studies."""
        plan = self.planner.create_teaching_plan("Financial Accounting", "Ledger Reconciliation", {"level": "COLLEGE"})
        self.assertEqual(plan["topic_nature"], "accounting-financial")
        self.assertEqual(plan["demonstration_type"], "financial_case_study")
        self.assertIn("Double-Entry", plan["teaching_approach"])
        self.assertIn("do not apply", plan["honest_limitation"].lower())

    def test_03_history_approach(self):
        """History topics must use timelines, causality mapping, and primary source document analysis."""
        plan = self.planner.create_teaching_plan("World History", "French Revolution", {"level": "COLLEGE"})
        self.assertEqual(plan["topic_nature"], "historical-source")
        self.assertEqual(plan["demonstration_type"], "source_analysis_and_criticism")
        self.assertIn("Chronological Timeline", plan["teaching_approach"])
        self.assertIn("do not apply", plan["honest_limitation"].lower())

    def test_04_literature_approach(self):
        """Literature topics must use close text reading, thematic interpretation, and evidence analysis."""
        plan = self.planner.create_teaching_plan("English Literature", "Shakespearean Tragedy", {"level": "COLLEGE"})
        self.assertEqual(plan["topic_nature"], "literary-thematic")
        self.assertEqual(plan["demonstration_type"], "textual_analysis_and_criticism")
        self.assertIn("Close Textual Reading", plan["teaching_approach"])
        self.assertIn("do not apply", plan["honest_limitation"].lower())

    def test_05_economics_approach(self):
        """Economics topics must use supply/demand equilibrium graphs, elasticity calculations, and policy models."""
        plan = self.planner.create_teaching_plan("Microeconomics", "Price Elasticity of Demand", {"level": "COLLEGE"})
        self.assertEqual(plan["topic_nature"], "economics-analytical")
        self.assertEqual(plan["demonstration_type"], "worked_example_and_derivation")
        self.assertIn("Economic Graph", plan["teaching_approach"])

    def test_06_languages_approach(self):
        """Language topics must use syntax breakdowns, grammar rules, and contextual communication drills."""
        plan = self.planner.create_teaching_plan("French Grammar", "Subjunctive Mood Syntax", {"level": "COLLEGE"})
        self.assertEqual(plan["topic_nature"], "language-grammar")
        self.assertEqual(plan["demonstration_type"], "textual_analysis_and_criticism")
        self.assertIn("Syntax", plan["teaching_approach"])

    def test_07_mathematics_approach(self):
        """Mathematics topics must use derivations, worked calculations, proofs, and real-life problems."""
        plan = self.planner.create_teaching_plan("Pure Mathematics", "Calculus Derivatives", {"level": "COLLEGE"})
        self.assertEqual(plan["topic_nature"], "numerical")
        self.assertEqual(plan["demonstration_type"], "worked_example_and_derivation")
        self.assertIn("First-Principles Derivation", plan["teaching_approach"])

    def test_08_engineering_approach(self):
        """Engineering topics must use block schematics, derivations, component constraints, and simulations."""
        plan = self.planner.create_teaching_plan("Electrical Engineering", "Kirchhoff Circuit Analysis", {"level": "COLLEGE"})
        self.assertEqual(plan["topic_nature"], "engineering-design")
        self.assertEqual(plan["demonstration_type"], "system_diagram_and_simulation")
        self.assertIn("System Block Diagram", plan["teaching_approach"])

    def test_09_science_practical_approach(self):
        """Science topics must use safe experiments, observations, and physical principles."""
        plan = self.planner.create_teaching_plan("Organic Chemistry", "Acid-Base Titration", {"level": "COLLEGE"})
        self.assertEqual(plan["topic_nature"], "practical")
        self.assertEqual(plan["demonstration_type"], "physical_demonstration")

    def test_10_unfamiliar_new_subject_support(self):
        """Unfamiliar subjects (e.g. Environmental Law) work automatically based on topic characteristics."""
        plan = self.planner.create_teaching_plan("Environmental Law", "Jurisdictional Precedents", {"level": "COLLEGE"})
        self.assertTrue(plan["is_valid"])
        self.assertEqual(plan["topic_nature"], "interpretive")
        self.assertEqual(plan["demonstration_type"], "thought_experiment_and_analog")

    def test_11_no_forced_inappropriate_activities(self):
        """Verify non-science topics never force physical experiments or coding."""
        non_science_topics = [
            ("English Literature", "Victorian Poetic Imagery"),
            ("Financial Accounting", "Balance Sheet Analysis"),
            ("World History", "Industrialization"),
            ("French Grammar", "Past Tense Conjugation")
        ]
        for sub, top in non_science_topics:
            plan = self.planner.create_teaching_plan(sub, top, {"level": "COLLEGE"})
            self.assertNotEqual(plan["demonstration_type"], "physical_demonstration")
            self.assertTrue(len(plan["honest_limitation"]) > 10)


if __name__ == "__main__":
    unittest.main()
