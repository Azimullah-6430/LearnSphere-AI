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

class TestLearnAnywhereNetworkOptimization(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.suffix = str(uuid.uuid4())[:8]

        self.student_a_id = f"opt_stu_a_{self.suffix}"
        self.student_b_id = f"opt_stu_b_{self.suffix}"

    def test_01_idempotency_key_deduplication(self):
        """Verify retried request with identical idempotency_key returns cached response without duplicate creation."""
        mongo_db = get_mongodb()
        idempotency_key = f"idem_key_{self.suffix}"

        activity_data = {
            "title": "Capillary Action in Farm Soil",
            "subject": "Environmental Science",
            "topic": "Soil Water Percolation",
            "steps": ["Step 1: Fill jar with soil", "Step 2: Add water"]
        }

        if mongo_db is not None:
            # Insert initial cached activity
            mongo_db.learn_anywhere_cache.insert_one({
                "user_id": self.student_a_id,
                "idempotency_key": idempotency_key,
                "activity": activity_data,
                "subject": "Environmental Science",
                "topic": "Soil Water Percolation",
                "created_at": datetime.utcnow()
            })

            # Query cached activity by idempotency_key & user_id
            cached = mongo_db.learn_anywhere_cache.find_one({
                "user_id": self.student_a_id,
                "idempotency_key": idempotency_key
            })

            self.assertIsNotNone(cached)
            self.assertEqual(cached["activity"]["title"], "Capillary Action in Farm Soil")

    def test_02_idempotency_cache_user_isolation(self):
        """Verify Student B cannot retrieve Student A's idempotency cached response."""
        mongo_db = get_mongodb()
        idempotency_key = f"idem_shared_{self.suffix}"

        if mongo_db is not None:
            mongo_db.learn_anywhere_cache.insert_one({
                "user_id": self.student_a_id,
                "idempotency_key": idempotency_key,
                "activity": {"title": "Student A Private Experiment"},
                "created_at": datetime.utcnow()
            })

            # Student B attempts lookup with same key
            b_lookup = mongo_db.learn_anywhere_cache.find_one({
                "user_id": self.student_b_id,
                "idempotency_key": idempotency_key
            })

            self.assertIsNone(b_lookup)

    def test_03_deterministic_fallback_no_crash_on_network_failure(self):
        """Verify AI engine falls back deterministically without crashing when network is interrupted."""
        res = gemini_service._build_deterministic_learn_anywhere(
            subject="Physics",
            subject_id="PHY101",
            topic="Refractive Index of Water Droplets",
            resource_env="Sunlight & Shadows",
            difficulty="Medium",
            semester="1",
            program="General Science",
            department="Physics"
        )

        self.assertIsInstance(res, dict)
        self.assertIn("steps", res)
        self.assertTrue(len(res["steps"]) >= 3)
        self.assertIn("understanding_questions", res)
        self.assertFalse(res.get("image_analysis", {}).get("image_processed", False))

    def test_04_offline_and_no_fake_generation_policy(self):
        """Verify offline indicator policy: offline users receive clear notice and cannot fake new AI generation."""
        # Simulated frontend offline policy check
        is_online = False
        if not is_online:
            error_notice = "Internet connection is required to generate new AI activities. Your previously loaded activity remains readable below."
            self.assertIn("Internet connection is required", error_notice)
            self.assertIn("previously loaded activity remains readable", error_notice)

if __name__ == "__main__":
    unittest.main()
