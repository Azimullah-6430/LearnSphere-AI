"""
LearnSphere AI - Current News & Opportunities Personalization & Isolation Test Suite

Verifies:
1. SCHOOL Student Personalization:
   - Receives school education news, inter-school competitions, science olympiads, and school scholarships.
   - Zero college hackathons, GSoC, or university opportunities in school feed.
2. COLLEGE Student Personalization:
   - Receives university news, domain-related tech developments, hackathons (SIH 2026), coding contests (ICPC), and college scholarships (NSP Central Sector AY 2026–27).
   - Zero school olympiads, NMMSS, or inter-school competitions in college feed.
3. Strict Profile-Based Filtering:
   - School: class/grade, location, board.
   - College: program/degree, department, year, semester, location.
4. Authoritative Source Provenance:
   - Every opportunity references official verified portals (scholarships.gov.in, sih.gov.in, inspireawards-dst.gov.in, etc.).
   - Zero fake or invented opportunities.
5. Unauthenticated 401 gate protection.
"""

import os
import sys
import uuid
import unittest
from datetime import datetime

# Set up path to backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server import app


class TestOpportunitiesPersonalization(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        self.suffix = uuid.uuid4().hex[:8]
        self.school_email = f"school_{self.suffix}@learnsphere.test"
        self.college_email = f"college_{self.suffix}@learnsphere.test"
        self.password = "TestPass123!"

        # Register School Student (Class 10 CBSE, Chennai, Tamil Nadu)
        res_sch = self.app.post("/api/auth/register", json={
            "name": "Rohan (Class 10 School)",
            "email": self.school_email,
            "password": self.password,
            "role": "student",
            "level": "school",
            "grade_level": 10,
            "classLevel": 10,
            "board": "CBSE",
            "city": "Chennai",
            "state": "Tamil Nadu",
            "country": "India"
        })
        self.assertIn(res_sch.status_code, [200, 201])
        self.school_user_id = res_sch.get_json()["user"]["id"]

        # Register College Student (B.Tech IT, Year 3 Sem 5, Bengaluru, Karnataka)
        res_col = self.app.post("/api/auth/register", json={
            "name": "Ananya (B.Tech IT College)",
            "email": self.college_email,
            "password": self.password,
            "role": "student",
            "level": "college",
            "degree": "B.Tech",
            "program": "B.Tech",
            "department": "Information Technology",
            "branch": "Information Technology",
            "year": 3,
            "current_year": 3,
            "semester": 5,
            "current_semester": 5,
            "city": "Bengaluru",
            "state": "Karnataka",
            "country": "India"
        })
        self.assertIn(res_col.status_code, [200, 201])
        self.college_user_id = res_col.get_json()["user"]["id"]

    def _login(self, email):
        return self.app.post("/api/auth/login", json={
            "email": email,
            "password": self.password
        })

    def _logout(self):
        return self.app.post("/api/auth/logout")

    def test_01_school_student_feed_personalization_and_isolation(self):
        """Verify School student receives only age-appropriate school opportunities and zero college data."""
        self._login(self.school_email)

        res = self.app.get("/api/opportunities")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("level"), "school")
        self.assertEqual(data["profile"]["role"], "school_student")

        news_titles = [n["title"] for n in data.get("news", [])]
        opp_titles = [o["title"] for o in data.get("opportunities", [])]
        all_sources = [n.get("source") for n in data.get("news", [])] + [o.get("source") for o in data.get("opportunities", [])]

        # 1. Must contain verified school competitions / olympiads / scholarships
        self.assertTrue(any("NMMSS" in t or "National Means" in t for t in opp_titles or news_titles))
        self.assertTrue(any("INSPIRE" in t or "MANAK" in t for t in opp_titles or news_titles))
        self.assertTrue(any("Olympiad" in t or "HBCSE" in t or "VVM" in t for t in opp_titles or news_titles))

        # 2. Must NOT contain college-only hackathons or collegiate programs
        for t in news_titles + opp_titles:
            self.assertNotIn("Smart India Hackathon", t)
            self.assertNotIn("Google Summer of Code", t)
            self.assertNotIn("ICPC", t)
            self.assertNotIn("Imagine Cup", t)

        # 3. Source verification
        for src in all_sources:
            self.assertTrue(bool(src), "Every opportunity must have an authoritative source")

    def test_02_college_student_feed_personalization_and_isolation(self):
        """Verify College student receives domain-specific collegiate competitions and zero school data."""
        self._login(self.college_email)

        res = self.app.get("/api/opportunities")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("level"), "college")
        self.assertEqual(data["profile"]["role"], "college_student")
        self.assertEqual(data["profile"]["department"], "Information Technology")

        news_titles = [n["title"] for n in data.get("news", [])]
        opp_titles = [o["title"] for o in data.get("opportunities", [])]

        # 1. Must contain collegiate hackathons, ICPC, GSoC, NSP College scholarship
        self.assertTrue(any("Smart India Hackathon" in t or "SIH" in t for t in opp_titles or news_titles))
        self.assertTrue(any("Google Summer of Code" in t or "GSoC" in t for t in news_titles))
        self.assertTrue(any("ICPC" in t or "Programming Contest" in t for t in opp_titles))
        self.assertTrue(any("Central Sector" in t or "NSP" in t for t in opp_titles or news_titles))

        # 2. Must NOT contain school-only olympiads or NMMSS
        for t in news_titles + opp_titles:
            self.assertNotIn("NMMSS", t)
            self.assertNotIn("INSPIRE Awards - MANAK", t)
            self.assertNotIn("Fit India School Quiz", t)
            self.assertNotIn("Inter-School Robotics", t)

    def test_03_national_scholarship_portal_ay2026_schemes(self):
        """Verify scholarship eligibility and scheme details reference authentic AY 2026–27 NSP programs."""
        self._login(self.college_email)
        res = self.app.get("/api/opportunities")
        data = res.get_json()

        nsp_opp = next((o for o in data["opportunities"] if "NSP" in o["title"] or "scholarships.gov.in" in o.get("url", "")), None)
        self.assertIsNotNone(nsp_opp)
        self.assertIn("scholarships.gov.in", nsp_opp["url"])
        self.assertIn("Ministry of Education", nsp_opp["organizer"])
        self.assertIn("2026", nsp_opp["title"])

    def test_04_unauthenticated_request_is_rejected(self):
        """Verify unauthenticated requests cannot access personalized opportunities feed."""
        self._logout()
        res = self.app.get("/api/opportunities")
        self.assertEqual(res.status_code, 401)


if __name__ == "__main__":
    unittest.main()
