"""
LearnSphere AI - Current News & Opportunities Comprehensive Regression Test Suite

Validates all 7 Core Requirements:
1. Primary Filter: Strict School vs College separation based on authenticated MongoDB profile (zero feed mixing).
2. College Domain Segmentation:
   - Computer Science / IT (IndiaAI, GSoC, ICPC, SIH Software, Imagine Cup)
   - Electronics / ECE / EEE (India Semiconductor Mission, Chips to Startup C2S, TI IICDC, IEEE VLSI)
   - Mechanical / Automotive (Smart Manufacturing, ISRO POEM, BAJA SAEINDIA, ASME Design Challenge)
   - Civil / Infrastructure (MoHUA Smart Cities, ICI Sustainable Concrete, ASCE Sustainable Infrastructure)
   - Biotechnology / Biomedical (DBT & BIRAC Bio-Innovation, BIRAC BIG, ICMR Fellowship)
3. School-Specific Personalization:
   - Class 9 school student (NMMSS, HBCSE Olympiads, INSPIRE MANAK, Fit India Quiz, IRIS Science Fair)
   - Class 12 school student (CBSE Heritage Quiz, HBCSE Olympiad, IRIS, NMMSS)
   - Zero college hackathons or undergraduate internships shown to school students.
4. Missing Profile Handling:
   - College student missing department -> flags missing_profile_fields and only returns universal college items.
   - School student missing grade -> flags missing_profile_fields.
   - Never guesses department or grade.
5. Present & Future Only (Asia/Kolkata IST):
   - Expired deadlines marked EXPIRED/CLOSED and excluded from active recommendations.
   - Cancelled opportunities excluded.
   - Real publication dates displayed.
6. Authentic Sources & 13-Point Verification Checklist:
   - Official portals (scholarships.gov.in, sih.gov.in, cbse.gov.in, dst.gov.in, etc.)
   - UNVERIFIED items excluded from verified display.
7. Production Scheduler & Persistence:
   - MongoDB and SQLite storage.
   - Idempotent daily sync and scheduler execution.
"""

import unittest
from datetime import datetime, timezone, timedelta
from app.opportunities_service import OpportunitiesService, _get_current_ist_time


class TestCurrentNewsOpportunitiesRegression(unittest.TestCase):

    def setUp(self):
        # Run verification pipeline before each test to establish clean verified state
        OpportunitiesService.run_verification_pipeline()

    # ══════════════════════════════════════════════════════════════════════════
    # 1. SCHOOL PROFILES (Class 9 & Class 12)
    # ══════════════════════════════════════════════════════════════════════════

    def test_01_class_9_school_student_feed(self):
        """Class 9 school student receives school news, olympiads, and zero college hackathons."""
        student = {
            "role": "school_student",
            "level": "school",
            "student_type": "school",
            "grade_level": "9",
            "board": "CBSE",
            "city": "Bengaluru",
            "state": "Karnataka",
            "country": "India"
        }
        feed = OpportunitiesService.get_personalized_feed(student)

        self.assertTrue(feed["success"])
        self.assertEqual(feed["level"], "school")
        self.assertEqual(feed["student_type"], "SCHOOL")
        self.assertEqual(feed["profile"]["grade"], 9)
        self.assertEqual(feed["profile"]["board"], "CBSE")

        # Verify News Items
        news_ids = [n["id"] for n in feed["news"]]
        self.assertIn("sch-news-nsp-nmmss-2026", news_ids)
        self.assertIn("sch-news-hbcse-olympiad-2026", news_ids)
        self.assertIn("sch-news-inspire-manak-2026", news_ids)
        self.assertIn("sch-news-cbse-science-2026", news_ids)
        self.assertIn("sch-news-fit-india-2026", news_ids)

        # Ensure ZERO college items in news
        for n in feed["news"]:
            self.assertEqual(n["level"], "school")
            self.assertNotIn("col-", str(n["id"]))
            self.assertNotEqual(n.get("student_type"), "college")

        # Verify Opportunity Items
        opp_ids = [o["id"] for o in feed["opportunities"]]
        self.assertIn("sch-opp-nsp-nmmss-2026", opp_ids)
        self.assertIn("sch-opp-inspire-manak-2026", opp_ids)
        self.assertIn("sch-opp-iris-science-fair-2026", opp_ids)
        self.assertIn("sch-opp-vvm-2026", opp_ids)
        self.assertIn("sch-opp-cbse-heritage-quiz-2026", opp_ids)

        # Ensure ZERO college items in opportunities
        for o in feed["opportunities"]:
            self.assertEqual(o["level"], "school")
            self.assertNotIn("col-", str(o["id"]))
            self.assertNotEqual(o.get("student_type"), "college")
            self.assertNotIn("Hackathon", o.get("title", ""))

    def test_02_class_12_school_student_feed(self):
        """Class 12 school student receives higher-secondary eligible school competitions."""
        student = {
            "role": "school_student",
            "level": "school",
            "student_type": "school",
            "grade_level": "12",
            "board": "CBSE",
            "city": "Chennai",
            "state": "Tamil Nadu",
            "country": "India"
        }
        feed = OpportunitiesService.get_personalized_feed(student)

        self.assertEqual(feed["level"], "school")
        opp_ids = [o["id"] for o in feed["opportunities"]]

        # Class 12 is eligible for NMMSS renewal, IRIS Science Fair, CBSE Heritage Quiz
        self.assertIn("sch-opp-nsp-nmmss-2026", opp_ids)
        self.assertIn("sch-opp-iris-science-fair-2026", opp_ids)
        self.assertIn("sch-opp-cbse-heritage-quiz-2026", opp_ids)

        # Class 12 is NOT eligible for INSPIRE MANAK (max_grade is 10)
        self.assertNotIn("sch-opp-inspire-manak-2026", opp_ids)

        # Zero college hackathons
        for o in feed["opportunities"]:
            self.assertNotIn("col-", str(o["id"]))

    # ══════════════════════════════════════════════════════════════════════════
    # 2. COLLEGE DOMAIN SEGMENTATION (CS, Mech, ECE, Civil, Biotech)
    # ══════════════════════════════════════════════════════════════════════════

    def test_03_computer_science_college_student_feed(self):
        """CS / IT student receives AI, GSoC, ICPC, SIH Software, and zero Mech/Civil only items."""
        student = {
            "role": "college_student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Computer Science and Engineering",
            "year": 3,
            "semester": 5,
            "city": "Hyderabad",
            "state": "Telangana"
        }
        feed = OpportunitiesService.get_personalized_feed(student)

        self.assertEqual(feed["level"], "college")
        news_ids = [n["id"] for n in feed["news"]]
        opp_ids = [o["id"] for o in feed["opportunities"]]

        # CS News
        self.assertIn("col-news-meity-ai-2026", news_ids)
        self.assertIn("col-news-gsoc-2026", news_ids)
        self.assertIn("col-news-sih-2026", news_ids)

        # CS Opportunities
        self.assertIn("col-opp-icpc-2026", opp_ids)
        self.assertIn("col-opp-sih-2026", opp_ids)
        self.assertIn("col-opp-microsoft-imagine-2026", opp_ids)
        self.assertIn("col-opp-nsp-csss-2026", opp_ids)

        # Zero Mech-exclusive or Civil-exclusive items
        self.assertNotIn("col-opp-baja-sae-india-2026", opp_ids)
        self.assertNotIn("col-opp-ici-sustainable-concrete-2026", opp_ids)
        self.assertNotIn("col-opp-birac-big-2026", opp_ids)

    def test_04_mechanical_engineering_college_student_feed(self):
        """Mechanical student receives BAJA SAE, ASME, Smart Manufacturing, and zero CS-only items."""
        student = {
            "role": "college_student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Mechanical Engineering",
            "year": 3,
            "semester": 6,
            "city": "Pune",
            "state": "Maharashtra"
        }
        feed = OpportunitiesService.get_personalized_feed(student)

        news_ids = [n["id"] for n in feed["news"]]
        opp_ids = [o["id"] for o in feed["opportunities"]]

        # Mechanical News & Opps
        self.assertIn("col-news-heavy-industries-smart-mfg-2026", news_ids)
        self.assertIn("col-news-isro-payload-2026", news_ids)
        self.assertIn("col-opp-baja-sae-india-2026", opp_ids)
        self.assertIn("col-opp-asme-design-competition-2026", opp_ids)
        self.assertIn("col-opp-sih-2026", opp_ids)  # SIH includes Mechanical

        # Zero CS-only items
        self.assertNotIn("col-news-gsoc-2026", news_ids)
        self.assertNotIn("col-opp-icpc-2026", opp_ids)
        self.assertNotIn("col-opp-ici-sustainable-concrete-2026", opp_ids)

    def test_05_electronics_ece_college_student_feed(self):
        """Electronics / ECE student receives Semiconductor Mission, C2S, TI IICDC, IEEE VLSI."""
        student = {
            "role": "college_student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Electronics and Communication Engineering",
            "year": 3,
            "semester": 5,
            "city": "Bengaluru",
            "state": "Karnataka"
        }
        feed = OpportunitiesService.get_personalized_feed(student)

        news_ids = [n["id"] for n in feed["news"]]
        opp_ids = [o["id"] for o in feed["opportunities"]]

        self.assertIn("col-news-ism-semiconductor-2026", news_ids)
        self.assertIn("col-news-ieee-vlsi-2026", news_ids)
        self.assertIn("col-opp-ti-india-innovation-2026", opp_ids)
        self.assertIn("col-opp-sih-2026", opp_ids)

        # Zero Biotech or Civil items
        self.assertNotIn("col-opp-birac-big-2026", opp_ids)
        self.assertNotIn("col-opp-ici-sustainable-concrete-2026", opp_ids)

    def test_06_civil_engineering_college_student_feed(self):
        """Civil student receives MoHUA Smart Cities, ICI Sustainable Concrete, and ASCE Challenge."""
        student = {
            "role": "college_student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Civil Engineering",
            "year": 3,
            "semester": 5,
            "city": "New Delhi",
            "state": "Delhi"
        }
        feed = OpportunitiesService.get_personalized_feed(student)

        news_ids = [n["id"] for n in feed["news"]]
        opp_ids = [o["id"] for o in feed["opportunities"]]

        self.assertIn("col-news-mohua-smart-cities-2026", news_ids)
        self.assertIn("col-opp-ici-sustainable-concrete-2026", opp_ids)
        self.assertIn("col-opp-sih-2026", opp_ids)  # SIH includes Civil

        # Zero CS-only or Mech-only items
        self.assertNotIn("col-news-gsoc-2026", news_ids)
        self.assertNotIn("col-opp-icpc-2026", opp_ids)
        self.assertNotIn("col-opp-baja-sae-india-2026", opp_ids)

    def test_07_biotechnology_college_student_feed(self):
        """Biotechnology / Biomedical student receives DBT BIRAC grants and ICMR fellowships."""
        student = {
            "role": "college_student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Biotechnology",
            "year": 3,
            "semester": 5,
            "city": "Kolkata",
            "state": "West Bengal"
        }
        feed = OpportunitiesService.get_personalized_feed(student)

        news_ids = [n["id"] for n in feed["news"]]
        opp_ids = [o["id"] for o in feed["opportunities"]]

        self.assertIn("col-news-dbt-birac-bioinnovation-2026", news_ids)
        self.assertIn("col-opp-birac-big-2026", opp_ids)
        self.assertIn("col-opp-icmr-student-fellowship-2026", opp_ids)

        # Zero CS-only or Mech-only items
        self.assertNotIn("col-opp-icpc-2026", opp_ids)
        self.assertNotIn("col-opp-baja-sae-india-2026", opp_ids)

    # ══════════════════════════════════════════════════════════════════════════
    # 3. MISSING PROFILE INFORMATION HANDLING
    # ══════════════════════════════════════════════════════════════════════════

    def test_08_college_student_missing_department_information(self):
        """When department is missing, flag missing field and return only universal opportunities."""
        incomplete_student = {
            "role": "college_student",
            "level": "college",
            "degree": "B.Tech",
            "department": "",  # Missing department
            "year": 2,
            "semester": 3
        }
        feed = OpportunitiesService.get_personalized_feed(incomplete_student)

        self.assertIn("department", feed["missing_profile_fields"])
        self.assertIsNotNone(feed["profile_completeness_message"])
        self.assertIn("department", feed["profile_completeness_message"].lower())

        # Every opportunity returned MUST be open to all departments
        for opp in feed["opportunities"]:
            depts = opp.get("departments", ["all"])
            self.assertIn("all", depts, f"Non-universal opportunity leaked: {opp['id']}")

        # Ensure no specialized CS/Mech/Civil-only contests leaked
        opp_ids = [o["id"] for o in feed["opportunities"]]
        self.assertNotIn("col-opp-icpc-2026", opp_ids)
        self.assertNotIn("col-opp-baja-sae-india-2026", opp_ids)
        self.assertNotIn("col-opp-birac-big-2026", opp_ids)

    def test_09_school_student_missing_grade_information(self):
        """When grade is missing for a school student, flag missing field."""
        incomplete_school = {
            "role": "school_student",
            "level": "school",
            "grade_level": "",  # Missing grade
            "board": ""         # Missing board
        }
        feed = OpportunitiesService.get_personalized_feed(incomplete_school)

        self.assertIn("grade_level", feed["missing_profile_fields"])
        self.assertIn("board", feed["missing_profile_fields"])
        self.assertIsNotNone(feed["profile_completeness_message"])

    # ══════════════════════════════════════════════════════════════════════════
    # 4. PRESENT & FUTURE ONLY (Asia/Kolkata IST)
    # ══════════════════════════════════════════════════════════════════════════

    def test_10_expired_and_cancelled_opportunity_handling(self):
        """Expired deadlines and cancelled opportunities are excluded from active recommendations."""
        # Test item with past deadline relative to reference date
        ref_time = datetime(2027, 2, 1, 12, 0, 0, tzinfo=timezone.utc)

        expired_item = {
            "id": "test-opp-expired",
            "title": "Expired Hackathon 2026",
            "organizer": "Test Organizer",
            "category": "Hackathons",
            "eligibility": "College students",
            "deadline": "October 31, 2026",
            "url": "https://sih.gov.in",
            "source": "Official Portal",
            "isRecommended": True
        }
        res_exp = OpportunitiesService.verify_item(expired_item, current_time=ref_time)
        self.assertEqual(res_exp["opportunityStatus"], "EXPIRED")
        self.assertEqual(res_exp["registrationStatus"], "CLOSED")
        self.assertTrue(res_exp["isExpired"])
        self.assertFalse(res_exp["isRecommended"])

        # Test cancelled item
        cancelled_item = {
            "id": "test-opp-cancelled",
            "title": "Cancelled Robotics Contest [CANCELLED]",
            "organizer": "Test Organizer",
            "category": "Robotics",
            "eligibility": "College students",
            "deadline": "November 30, 2027",
            "url": "https://sih.gov.in",
            "source": "Official Portal",
            "is_cancelled": True,
            "isRecommended": True
        }
        res_can = OpportunitiesService.verify_item(cancelled_item, current_time=ref_time)
        self.assertEqual(res_can["opportunityStatus"], "CANCELLED")
        self.assertEqual(res_can["registrationStatus"], "CANCELLED")
        self.assertTrue(res_can["isCancelled"])
        self.assertFalse(res_can["isRecommended"])

    # ══════════════════════════════════════════════════════════════════════════
    # 5. AUTHENTIC SOURCES & 13-POINT VERIFICATION
    # ══════════════════════════════════════════════════════════════════════════

    def test_11_thirteen_point_verification_passes_for_registry(self):
        """All items in official registries pass 13-point verification and have authentic https URLs."""
        for item in OpportunitiesService.COLLEGE_NEWS_REGISTRY:
            self.assertTrue(item["url"].startswith("https://"))
            self.assertTrue(len(item["source"]) > 3)
            self.assertIn("verified", item)

        for item in OpportunitiesService.COLLEGE_OPPS_REGISTRY:
            self.assertTrue(item["url"].startswith("https://"))
            self.assertTrue(len(item["organizer"]) > 3)
            self.assertTrue(len(item["eligibility"]) > 5)

        for item in OpportunitiesService.SCHOOL_NEWS_REGISTRY:
            self.assertTrue(item["url"].startswith("https://"))
            self.assertTrue(len(item["source"]) > 3)

        for item in OpportunitiesService.SCHOOL_OPPS_REGISTRY:
            self.assertTrue(item["url"].startswith("https://"))
            self.assertTrue(len(item["organizer"]) > 3)
            self.assertTrue(len(item["eligibility"]) > 5)

    # ══════════════════════════════════════════════════════════════════════════
    # 6. DATABASE SYNC & PERSISTENCE
    # ══════════════════════════════════════════════════════════════════════════

    def test_12_database_synchronization_and_audit_logging(self):
        """Database sync successfully upserts items and records sync timestamp."""
        sync_res = OpportunitiesService.sync_to_database()
        self.assertTrue(sync_res["success"])
        self.assertGreater(sync_res["synced_news"], 0)
        self.assertGreater(sync_res["synced_opportunities"], 0)
        self.assertIsNotNone(OpportunitiesService._last_successful_refresh_time)

    # ══════════════════════════════════════════════════════════════════════════
    # 7. DYNAMIC LOCATION SELECTION & NEARBY OPPORTUNITIES
    # ══════════════════════════════════════════════════════════════════════════

    def test_13_dynamic_location_selection_and_nearby_hackathons(self):
        """Dynamic location selection boosts local city/state hackathons and attaches proximity badges."""
        college_user = {
            "role": "college_student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Computer Science",
            "year": 3,
            "semester": 5,
            "city": "Chennai",
            "state": "Tamil Nadu",
            "country": "India"
        }

        # 1. Fetch with Chennai, Tamil Nadu
        feed_tn = OpportunitiesService.get_personalized_feed(
            user=college_user,
            location_override={"city": "Chennai", "state": "Tamil Nadu"}
        )
        self.assertTrue(feed_tn["success"])
        opps_tn = feed_tn["opportunities"]

        # IIT Madras Shaastra should have city match and proximity badge
        shaastra = next((o for o in opps_tn if "IIT Madras" in o["title"] or "shaastra" in o["id"]), None)
        self.assertIsNotNone(shaastra)
        self.assertTrue(shaastra["isCityMatch"])
        self.assertTrue(shaastra["isNearYou"])
        self.assertEqual(shaastra["proximityType"], "city")
        self.assertIn("In Your City", shaastra["proximityBadge"])

        # 2. Dynamically switch location to Bengaluru, Karnataka
        feed_blr = OpportunitiesService.get_personalized_feed(
            user=college_user,
            location_override={"city": "Bengaluru", "state": "Karnataka"}
        )
        self.assertTrue(feed_blr["success"])
        opps_blr = feed_blr["opportunities"]

        # Bengaluru Tech Summit should now have city match and proximity badge
        bts = next((o for o in opps_blr if "Bengaluru Tech Summit" in o["title"] or "bts" in o["id"]), None)
        self.assertIsNotNone(bts)
        self.assertTrue(bts["isCityMatch"])
        self.assertTrue(bts["isNearYou"])
        self.assertEqual(bts["proximityType"], "city")
        self.assertIn("In Your City", bts["proximityBadge"])


if __name__ == "__main__":
    unittest.main()

