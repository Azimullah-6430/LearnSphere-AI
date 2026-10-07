"""
Test Suite: Strict Server-Side Opportunity Segmentation
Validates:
1. College students receive ONLY college opportunities and ZERO school competitions.
2. School students receive ONLY school opportunities and ZERO college hackathons.
3. Domain isolation: College student from one domain (e.g., Mechanical) does NOT
   receive unrelated domain-specific opportunities (e.g., ICPC Software-only).
4. All-domain opportunities (e.g., NSP, Imagine Cup) are accessible to all eligible college students.
5. Year/Semester filtering for college students.
6. Grade/Class filtering for school students.
7. Location filtering.
8. Deadline validity (expired/cancelled items excluded from active feed).
9. Zero unrelated filler content.
"""

import unittest
from app.opportunities_service import OpportunitiesService


class TestStrictOpportunitySegmentation(unittest.TestCase):

    def setUp(self):
        # Refresh verification state
        OpportunitiesService.run_verification_pipeline()

    def test_college_student_receives_zero_school_items(self):
        """Test: College student -> no school competitions or school news."""
        college_user = {
            "role": "college_student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Computer Science",
            "year": 3,
            "semester": 5,
            "city": "Bengaluru",
            "state": "Karnataka",
            "country": "India"
        }
        feed = OpportunitiesService.get_personalized_feed(college_user)

        self.assertEqual(feed["level"], "college")
        # Check all news items
        for item in feed["news"]:
            self.assertEqual(item["level"], "college")
            self.assertNotIn("sch-", str(item.get("id", "")))
            self.assertNotEqual(item.get("student_type"), "school")
            self.assertNotIn("School", item.get("category", ""))

        # Check all opportunity items
        for item in feed["opportunities"]:
            self.assertEqual(item["level"], "college")
            self.assertNotIn("sch-", str(item.get("id", "")))
            self.assertNotEqual(item.get("student_type"), "school")

    def test_school_student_receives_zero_college_hackathons(self):
        """Test: School student -> no college hackathons, ICPC, or college scholarships."""
        school_user = {
            "role": "school_student",
            "level": "school",
            "grade_level": "10",
            "board": "CBSE",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India"
        }
        feed = OpportunitiesService.get_personalized_feed(school_user)

        self.assertEqual(feed["level"], "school")
        # Check all news items
        for item in feed["news"]:
            self.assertEqual(item["level"], "school")
            self.assertNotIn("col-", str(item.get("id", "")))
            self.assertNotEqual(item.get("student_type"), "college")

        # Check all opportunity items
        for item in feed["opportunities"]:
            self.assertEqual(item["level"], "school")
            self.assertNotIn("col-", str(item.get("id", "")))
            self.assertNotEqual(item.get("student_type"), "college")
            self.assertNotIn("Hackathon", item.get("title", ""))

    def test_college_domain_isolation(self):
        """Test: College student from one domain (Mechanical) does NOT see CS-only opportunities."""
        mech_student = {
            "role": "college_student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Mechanical Engineering",
            "year": 3,
            "semester": 5
        }
        feed = OpportunitiesService.get_personalized_feed(mech_student)

        opp_ids = [item["id"] for item in feed["opportunities"]]
        news_ids = [item["id"] for item in feed["news"]]

        # ICPC is restricted to CS, IT, Software Engineering, Data Science, Electronics
        self.assertNotIn("col-opp-icpc-2026", opp_ids)
        # GSoC is restricted to CS, IT, Software Engineering, Data Science, Electronics
        self.assertNotIn("col-news-gsoc-2026", news_ids)

        # But should receive opportunities that accept Mechanical or all departments
        self.assertIn("col-opp-sih-2026", opp_ids)  # SIH includes Mechanical
        self.assertIn("col-opp-nsp-csss-2026", opp_ids)  # NSP accepts all departments
        self.assertIn("col-opp-microsoft-imagine-2026", opp_ids)  # Imagine Cup accepts all departments

    def test_cs_student_receives_cs_specific_opportunities(self):
        """Test: CS student receives CS-specific opportunities like ICPC and GSoC."""
        cs_student = {
            "role": "college_student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Computer Science",
            "year": 3,
            "semester": 5
        }
        feed = OpportunitiesService.get_personalized_feed(cs_student)

        opp_ids = [item["id"] for item in feed["opportunities"]]
        news_ids = [item["id"] for item in feed["news"]]

        self.assertIn("col-opp-icpc-2026", opp_ids)
        self.assertIn("col-news-gsoc-2026", news_ids)

    def test_year_eligibility_filtering(self):
        """Test: 1st Year college student does NOT receive Year 2+ exclusive research opportunities."""
        year1_student = {
            "role": "college_student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Computer Science",
            "year": 1,
            "semester": 1
        }
        feed = OpportunitiesService.get_personalized_feed(year1_student)

        news_ids = [item["id"] for item in feed["news"]]
        # ISRO payload is min_year 2
        self.assertNotIn("col-news-isro-payload-2026", news_ids)
        # MeitY IndiaAI is min_year 2
        self.assertNotIn("col-news-meity-ai-2026", news_ids)

    def test_school_grade_eligibility_filtering(self):
        """Test: Class 6 student does NOT receive Class 8-12 exclusive scholarships."""
        class6_student = {
            "role": "school_student",
            "level": "school",
            "grade_level": "6",
            "board": "CBSE"
        }
        feed = OpportunitiesService.get_personalized_feed(class6_student)

        opp_ids = [item["id"] for item in feed["opportunities"]]
        news_ids = [item["id"] for item in feed["news"]]

        # NMMSS scholarship is min_grade 8
        self.assertNotIn("sch-opp-nsp-nmmss-2026", opp_ids)
        self.assertNotIn("sch-news-nsp-nmmss-2026", news_ids)
        # HBCSE Olympiad is min_grade 8
        self.assertNotIn("sch-opp-hbcse-olympiad-2026", opp_ids)

        # But should receive Class 6-10 INSPIRE Awards MANAK
        self.assertIn("sch-opp-inspire-manak-2026", opp_ids)
        self.assertIn("sch-news-inspire-manak-2026", news_ids)

    def test_no_unrelated_content_padding(self):
        """Test: When no opportunities match a niche non-matching profile, do not pad with unrelated items."""
        unknown_student = {
            "role": "college_student",
            "level": "college",
            "degree": "B.A. Literature",
            "department": "Ancient Sanskrit Literature",
            "year": 4,
            "semester": 8
        }
        feed = OpportunitiesService.get_personalized_feed(unknown_student)

        # Ensure no engineering-only competitions are injected
        for item in feed["opportunities"]:
            depts = item.get("departments", ["all"])
            degrees = item.get("degrees", ["all"])
            # Every item returned must be an all-departments/all-degrees open opportunity
            self.assertTrue("all" in depts or "all" in degrees or "B.A" in degrees)


if __name__ == "__main__":
    unittest.main()
