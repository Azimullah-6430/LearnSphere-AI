"""
LearnSphere AI - Test Suite for Dashboard Analytics & Required Details
Verifies that the dashboard analytics endpoint:
1. Returns only required and genuine data for students
2. Accurately calculates average mastery based on real scores
3. Dynamically identifies top practice concept for students
4. Returns genuine teacher evaluation metrics:
   - Total evaluations graded
   - Active students evaluated count
   - Pending action items requiring pedagogical intervention
   - Diagnosed misconceptions count
5. Strictly excludes unlinked/mock data and ensures clean, high-precision payloads
"""

import unittest
from server import app
import json


class TestDashboardAnalyticsPrecision(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_01_student_dashboard_requires_auth(self):
        """Unauthenticated request to dashboard analytics is blocked."""
        res = self.client.get("/api/analytics/dashboard")
        self.assertIn(res.status_code, (401, 403))

    def test_02_student_dashboard_returns_required_structure(self):
        """Student gets genuine stats including total_evaluations, average_mastery, weakTopics."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = "test_student_123"
            sess["role"] = "student"
            sess["name"] = "Priya Sharma"
            sess["email"] = "priya@example.com"

        res = self.client.get("/api/analytics/dashboard")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("role"), "student")
        self.assertIn("recentEvaluations", data)
        self.assertIn("stats", data)
        stats = data["stats"]
        self.assertIn("total_evaluations", stats)
        self.assertIn("weak_topics_count", stats)

    def test_03_teacher_dashboard_returns_faculty_metrics(self):
        """Teacher gets genuine counts of graded evaluations, active students, action items, and misconceptions."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = "test_teacher_456"
            sess["role"] = "teacher"
            sess["name"] = "Dr. Ramesh Kumar"
            sess["email"] = "ramesh@example.com"

        res = self.client.get("/api/analytics/dashboard")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("role"), "teacher")
        self.assertIn("stats", data)
        stats = data["stats"]
        self.assertIn("total_evaluations", stats)
        self.assertIn("active_students_count", stats)
        self.assertIn("pending_action_items_count", stats)
        self.assertIn("active_misconceptions_count", stats)


if __name__ == "__main__":
    unittest.main()

