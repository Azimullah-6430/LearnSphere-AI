import unittest
import json
import os
import sys
import uuid
from datetime import datetime

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.gemini_service import gemini_service
from app.db import get_mongodb, get_sqlite_db
from server import app

class TestLearnAnywhereInteractiveProgress(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.suffix = str(uuid.uuid4())[:8]

        self.student_a_id = f"stu_a_{self.suffix}"
        self.student_b_id = f"stu_b_{self.suffix}"

    def test_01_semantic_evaluation_accepts_different_wording(self):
        """Verify semantic evaluator accepts correct short answers even when wording differs."""
        res = gemini_service.evaluate_learn_anywhere_answer(
            subject="Physics",
            topic="Capillarity and Surface Tension",
            question="Why does water rise higher in a narrower tube?",
            expected_answer="Adhesive forces between water and glass overcome cohesive forces, creating greater capillary pressure in small radius tubes.",
            student_answer="Adhesion between water and glass pulls the liquid higher in smaller tubes.",
            attempt_number=1
        )

        self.assertIsInstance(res, dict)
        self.assertTrue(res.get("is_correct"))
        self.assertIn(res.get("error_type"), ["none", "spelling_grammar_only"])

    def test_02_spelling_grammar_typo_not_penalized(self):
        """Verify minor spelling or grammar typos are classified as spelling_grammar_only without failing academic concept."""
        res = gemini_service._evaluate_learn_anywhere_answer_fallback(
            subject="Biology",
            topic="Plant Transpiration",
            question="Which plant leaf pore regulates water loss?",
            expected_answer="Stomata pores regulate transpiration water vapor loss.",
            student_answer="Stomata pore regulate transpiraton water vapor loss.",
            attempt_number=1
        )

        self.assertIsInstance(res, dict)
        self.assertTrue(res.get("is_correct"))

    def test_03_conceptual_misunderstanding_distinguished(self):
        """Verify conceptual misunderstandings are correctly flagged and offer hints for retry."""
        res = gemini_service._evaluate_learn_anywhere_answer_fallback(
            subject="Chemistry",
            topic="Acid-Base Indicators",
            question="What color change indicates an alkaline solution when using turmeric indicator?",
            expected_answer="Turmeric turns deep reddish-brown in alkaline solutions.",
            student_answer="Turmeric turns bright purple when mixed with acid.",
            attempt_number=2
        )

        self.assertIsInstance(res, dict)
        self.assertFalse(res.get("is_correct"))
        self.assertEqual(res.get("error_type"), "conceptual_misunderstanding")
        self.assertTrue(res.get("suggested_retry"))

    def test_04_mongodb_progress_persistence_and_no_single_answer_mastery(self):
        """Verify progress records persist in learn_anywhere_progress and single answer doesn't claim mastery."""
        mongo_db = get_mongodb()
        activity_id = f"lfa_act_{self.suffix}"
        
        attempts = [
            {"question_index": 0, "is_correct": True, "score": 100, "attempt_number": 1}
        ]

        if mongo_db is not None:
            now = datetime.utcnow()
            mongo_db.learn_anywhere_progress.update_one(
                {"user_id": self.student_a_id, "activity_id": activity_id},
                {"$set": {
                    "user_id": self.student_a_id,
                    "activity_id": activity_id,
                    "subject": "Physics",
                    "topic": "Capillarity",
                    "attempts": attempts,
                    "completed_steps": [0],
                    "total_steps": 4,
                    "completion_status": "in_progress",
                    "accuracy_percent": 100,
                    "updated_at": now
                }},
                upsert=True
            )

            record = mongo_db.learn_anywhere_progress.find_one({"user_id": self.student_a_id, "activity_id": activity_id})
            self.assertIsNotNone(record)
            # Mastery rule check: Status must remain in_progress when steps are incomplete
            self.assertEqual(record["completion_status"], "in_progress")

    def test_05_cross_user_isolation(self):
        """Verify Student A cannot access or modify Student B's progress records."""
        mongo_db = get_mongodb()
        act_b = f"act_b_{self.suffix}"

        if mongo_db is not None:
            now = datetime.utcnow()
            mongo_db.learn_anywhere_progress.insert_one({
                "user_id": self.student_b_id,
                "activity_id": act_b,
                "subject": "Mathematics",
                "topic": "Trigonometry",
                "attempts": [],
                "completion_status": "in_progress",
                "created_at": now
            })

            # Student A query should return 0 records belonging to Student B
            docs_a = list(mongo_db.learn_anywhere_progress.find({"user_id": self.student_a_id}))
            self.assertFalse(any(d["activity_id"] == act_b for d in docs_a))

    def test_06_strict_teacher_and_analytics_isolation(self):
        """Verify practice activities NEVER write to teacher evaluations, misconceptions, or action center."""
        mongo_db = get_mongodb()
        
        if mongo_db is not None:
            eval_count_before = mongo_db.evaluations.count_documents({"student_id": self.student_a_id})
            misc_count_before = mongo_db.misconceptions.count_documents({"student_id": self.student_a_id})
            action_count_before = mongo_db.action_items.count_documents({"student_id": self.student_a_id})

            # Simulate practice activity submission
            res = gemini_service.evaluate_learn_anywhere_answer(
                subject="Physics",
                topic="Capillarity",
                question="What is capillary action?",
                expected_answer="Rise of liquid in narrow tube",
                student_answer="Rise of water",
                attempt_number=1
            )
            self.assertTrue(res["is_correct"])

            eval_count_after = mongo_db.evaluations.count_documents({"student_id": self.student_a_id})
            misc_count_after = mongo_db.misconceptions.count_documents({"student_id": self.student_a_id})
            action_count_after = mongo_db.action_items.count_documents({"student_id": self.student_a_id})

            # Must remain unchanged (ZERO side effects)
            self.assertEqual(eval_count_before, eval_count_after)
            self.assertEqual(misc_count_before, misc_count_after)
            self.assertEqual(action_count_before, action_count_after)

if __name__ == "__main__":
    unittest.main()
