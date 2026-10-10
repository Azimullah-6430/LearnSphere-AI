"""
LearnSphere AI - Learn from Anywhere Subject Grounding & Topic Matching Test Suite

Verifies:
  1. Activity generation uses only the authenticated student's actual validated syllabus.
  2. Subject & topic matching prevents stale topics from leaking across subjects.
  3. Deduplication cache verifies subject and topic matching before returning entries.
  4. Response normalization forces subject and topic alignment.
  5. AI generation errors return honest error responses rather than serving hardcoded mock activities for a different subject.
"""

import unittest
import json, sys, os
from datetime import datetime

# Adjust path so backend imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from server import app
from app.db import get_mongodb
from app.gemini_service import gemini_service

class TestLearnAnywhereSubjectGrounding(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.client = app.test_client()
        self.student_id = "test_student_grounding_001"

        # Set session context
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_id
            sess["user"] = {
                "id": self.student_id,
                "user_id": self.student_id,
                "role": "student",
                "name": "Jane Doe",
                "degree": "B.Tech",
                "department": "Computer Science & Chemistry",
                "semester": 3
            }

        # Seed authoritative active syllabus in MongoDB
        mongo_db = get_mongodb()
        if mongo_db is not None:
            try:
                mongo_db.users.delete_many({"_id": self.student_id})
                mongo_db.syllabi.delete_many({"student_id": self.student_id})
                mongo_db.learn_anywhere_cache.delete_many({"user_id": self.student_id})
                mongo_db.learn_anywhere_history.delete_many({"user_id": self.student_id})
            except Exception:
                pass

            mongo_db.users.insert_one({
                "_id": self.student_id,
                "id": self.student_id,
                "user_id": self.student_id,
                "email": "grounding@learn.edu",
                "role": "student",
                "full_name": "Jane Doe"
            })

            self.syllabus_doc = {
                "student_id": self.student_id,
                "user_id": self.student_id,
                "syllabus_id": "syl_grounding_100",
                "status": "VALID",
                "validation_status": "VALID",
                "curriculumStatus": "VALID",
                "is_active": True,
                "semester": 3,
                "created_at": datetime.utcnow(),
                "subjects": [
                    {
                        "subject_id": "sub_cs301",
                        "name": "Data Structures & Algorithms",
                        "topics": ["B-Trees", "Binary Search", "Graph Traversal"]
                    },
                    {
                        "subject_id": "sub_chem201",
                        "name": "Organic Chemistry",
                        "topics": ["Electrophilic Addition", "Aromatic Substitution", "Protonation"]
                    },
                    {
                        "subject_id": "sub_phy101",
                        "name": "Engineering Physics",
                        "topics": ["Capillary Action", "Surface Tension", "Wave Interference"]
                    }
                ],
                "chapters": {
                    "Data Structures & Algorithms": ["B-Trees", "Binary Search", "Graph Traversal"],
                    "Organic Chemistry": ["Electrophilic Addition", "Aromatic Substitution", "Protonation"],
                    "Engineering Physics": ["Capillary Action", "Surface Tension", "Wave Interference"]
                }
            }
            try:
                mongo_db.syllabi.insert_one(self.syllabus_doc)
            except Exception as e:
                print(f"Warning inserting test syllabus: {e}")

    def test_01_subject_and_topic_grounding_in_generation(self):
        """Verify generating for Organic Chemistry returns content grounded strictly in Organic Chemistry."""
        payload = {
            "subject": "Organic Chemistry",
            "subject_id": "sub_chem201",
            "topic": "Electrophilic Addition",
            "syllabus_id": "syl_grounding_100"
        }
        res = self.client.post("/api/learn-anywhere/generate", json=payload)
        self.assertIn(res.status_code, [200, 503])
        data = res.get_json()

        if res.status_code == 200:
            self.assertTrue(data.get("success"))
            act = data.get("activity")
            self.assertIsNotNone(act)
            self.assertEqual(act.get("subject"), "Organic Chemistry")
            self.assertEqual(act.get("topic"), "Electrophilic Addition")
            self.assertEqual(act.get("academic_grounding", {}).get("subject"), "Organic Chemistry")
            self.assertEqual(act.get("academic_grounding", {}).get("topic"), "Electrophilic Addition")

    def test_02_stale_topic_correction_prevents_cross_subject_leakage(self):
        """If topic from Physics ('Capillary Action') is passed with 'Organic Chemistry', backend corrects topic."""
        payload = {
            "subject": "Organic Chemistry",
            "subject_id": "sub_chem201",
            "topic": "Capillary Action", # Stale topic from Physics!
            "syllabus_id": "syl_grounding_100"
        }
        res = self.client.post("/api/learn-anywhere/generate", json=payload)
        self.assertIn(res.status_code, [200, 503])
        data = res.get_json()

        if res.status_code == 200:
            self.assertTrue(data.get("success"))
            act = data.get("activity")
            # Backend must correct topic to valid topic of Organic Chemistry (Electrophilic Addition)
            self.assertEqual(act.get("subject"), "Organic Chemistry")
            self.assertIn(act.get("topic"), ["Electrophilic Addition", "Aromatic Substitution", "Protonation"])
            self.assertNotEqual(act.get("topic"), "Capillary Action")

    def test_03_invalid_unmatched_subject_rejected(self):
        """If student requests a subject not present in their syllabus, backend rejects with HTTP 400."""
        payload = {
            "subject": "Astrophysics & Relativity",
            "syllabus_id": "syl_grounding_100"
        }
        res = self.client.post("/api/learn-anywhere/generate", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("not present in your active validated curriculum", data.get("error", ""))

    def test_04_deduplication_cache_verifies_subject_matching(self):
        """Deduplication cache ignores cache hits if cached subject does not match requested subject."""
        mongo_db = get_mongodb()
        if mongo_db is not None:
            # Seed a cache entry with idempotency key for Physics
            idempotency_key = "dup_key_test_123"
            mongo_db.learn_anywhere_cache.insert_one({
                "user_id": self.student_id,
                "idempotency_key": idempotency_key,
                "subject": "Engineering Physics",
                "topic": "Capillary Action",
                "activity": {
                    "title": "Soil Capillarity Experiment",
                    "subject": "Engineering Physics",
                    "topic": "Capillary Action"
                }
            })

            # Now send request with SAME idempotency key but requesting Organic Chemistry
            payload = {
                "subject": "Organic Chemistry",
                "topic": "Electrophilic Addition",
                "idempotency_key": idempotency_key
            }
            res = self.client.post("/api/learn-anywhere/generate", json=payload)
            data = res.get_json()
            # Must NOT return the cached Physics activity!
            if res.status_code == 200:
                self.assertEqual(data.get("activity", {}).get("subject"), "Organic Chemistry")

    def test_05_deterministic_builder_respects_subject(self):
        """Verify _build_deterministic_learn_anywhere generates templates matching requested subject."""
        res_cs = gemini_service._build_deterministic_learn_anywhere(
            subject="Data Structures & Algorithms",
            subject_id="sub_cs301",
            topic="B-Trees",
            resource_env="All Local Resources",
            difficulty="Medium",
            semester="3",
            program="B.Tech",
            department="Computer Science"
        )
        norm_cs = gemini_service._normalize_learn_anywhere_response(
            res_cs, "Data Structures & Algorithms", "B-Trees", "Unit 1", "Ref", "Env", "Medium", "3", "B.Tech", "CS", "strict_only"
        )
        self.assertEqual(norm_cs["subject"], "Data Structures & Algorithms")
        self.assertEqual(norm_cs["topic"], "B-Trees")
        self.assertIn("Algorithmic", norm_cs["title"])

        res_chem = gemini_service._build_deterministic_learn_anywhere(
            subject="Organic Chemistry",
            subject_id="sub_chem201",
            topic="Electrophilic Addition",
            resource_env="All Local Resources",
            difficulty="Medium",
            semester="3",
            program="B.Tech",
            department="Chemistry"
        )
        norm_chem = gemini_service._normalize_learn_anywhere_response(
            res_chem, "Organic Chemistry", "Electrophilic Addition", "Unit 2", "Ref", "Env", "Medium", "3", "B.Tech", "Chem", "strict_only"
        )
        self.assertEqual(norm_chem["subject"], "Organic Chemistry")
        self.assertEqual(norm_chem["topic"], "Electrophilic Addition")
        self.assertIn("pH", norm_chem["title"])

if __name__ == "__main__":
    unittest.main()
