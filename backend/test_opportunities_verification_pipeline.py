"""
Test Suite: Current Opportunities Verification Pipeline
Validates:
1. 13-point verification checks:
   - title
   - organizer
   - eligibility
   - student type
   - class/year
   - domain
   - location
   - registration status
   - deadline
   - event date
   - official source
   - registration URL
   - latest available information
2. Storage of:
   - lastVerifiedAt
   - sourceUrl
   - verificationStatus
   - opportunityStatus
3. Enforcement of: UNVERIFIED = NOT ELIGIBLE FOR VERIFIED DISPLAY.
4. Expiration handling: marks EXPIRED/CLOSED, removes from active recommendations.
5. Cancellation handling: marks CANCELLED, removes from active recommendations.
6. Official source changes update existing records.
7. Background scheduler and pipeline runner operation.
"""

import unittest
from datetime import datetime, timedelta
from app.opportunities_service import OpportunitiesService


class TestOpportunitiesVerificationPipeline(unittest.TestCase):

    def setUp(self):
        # Base valid opportunity item for testing
        self.valid_college_item = {
            "id": "test-opp-valid-1",
            "title": "National Level Innovation & Hackathon 2026",
            "organizer": "Ministry of Education Innovation Cell",
            "category": "Hackathons & Innovation",
            "eligibility": "B.Tech and M.Tech engineering students enrolled in accredited universities",
            "prize": "₹5,00,000 Cash Prize & Incubation Support",
            "deadline": "November 30, 2026",
            "isOnline": True,
            "locationScope": "India",
            "source": "Ministry of Education Innovation Cell",
            "url": "https://sih.gov.in",
            "degrees": ["B.Tech", "M.Tech"],
            "departments": ["Computer Science", "Information Technology"],
            "min_year": 1,
            "max_year": 4,
            "isRecommended": True
        }

    def test_13_point_verification_passes_for_valid_item(self):
        """Verify all 13 fields are checked and item is verified."""
        ref_time = datetime(2026, 10, 1, 10, 0, 0)
        verified = OpportunitiesService.verify_item(self.valid_college_item, current_time=ref_time)

        # Check stored required properties
        self.assertIn("lastVerifiedAt", verified)
        self.assertEqual(verified["lastVerifiedAt"], "2026-10-01T10:00:00Z")
        self.assertEqual(verified["sourceUrl"], "https://sih.gov.in")
        self.assertEqual(verified["registrationUrl"], "https://sih.gov.in")
        self.assertEqual(verified["verificationStatus"], "VERIFIED")
        self.assertEqual(verified["opportunityStatus"], "ACTIVE")
        self.assertEqual(verified["registrationStatus"], "OPEN")
        self.assertTrue(verified["verified"])
        self.assertEqual(verified["verificationBadge"], "Verified Official Source")
        self.assertTrue(verified["isRecommended"])

        # Check 13 checks metadata
        checks = verified["verificationChecks"]
        self.assertTrue(checks["title"])
        self.assertTrue(checks["organizer"])
        self.assertTrue(checks["eligibility"])
        self.assertTrue(checks["student_type"])
        self.assertTrue(checks["class_year"])
        self.assertTrue(checks["domain"])
        self.assertTrue(checks["location"])
        self.assertTrue(checks["registration_status"])
        self.assertTrue(checks["deadline"])
        self.assertTrue(checks["event_date"])
        self.assertTrue(checks["official_source"])
        self.assertTrue(checks["registration_url"])
        self.assertTrue(checks["latest_available_information"])

    def test_unverified_rule_enforcement(self):
        """Rule: UNVERIFIED = NOT ELIGIBLE FOR VERIFIED DISPLAY."""
        # Case A: Missing or invalid registration URL
        invalid_url_item = dict(self.valid_college_item, url="http://insecure-site-fake.com")
        res_a = OpportunitiesService.verify_item(invalid_url_item)
        self.assertEqual(res_a["verificationStatus"], "UNVERIFIED")
        self.assertFalse(res_a["verified"])
        self.assertEqual(res_a["verificationBadge"], "Pending Verification")
        # Must be removed from active recommendations
        self.assertFalse(res_a["isRecommended"])

        # Case B: Demo / Fake organizer
        fake_organizer_item = dict(self.valid_college_item, organizer="Fake Org 123", source="Fake Org 123")
        res_b = OpportunitiesService.verify_item(fake_organizer_item)
        self.assertEqual(res_b["verificationStatus"], "UNVERIFIED")
        self.assertFalse(res_b["verified"])
        self.assertFalse(res_b["isRecommended"])

        # Case C: Missing title
        no_title_item = dict(self.valid_college_item, title="")
        res_c = OpportunitiesService.verify_item(no_title_item)
        self.assertEqual(res_c["verificationStatus"], "UNVERIFIED")
        self.assertFalse(res_c["verified"])

    def test_expired_deadline_handling(self):
        """If an event expires, mark EXPIRED/CLOSED and remove from active recommendations."""
        ref_time = datetime(2026, 11, 1, 0, 0, 0)
        # Event deadline was October 15, 2026
        expired_item = dict(self.valid_college_item, deadline="October 15, 2026", isRecommended=True)
        res = OpportunitiesService.verify_item(expired_item, current_time=ref_time)

        self.assertEqual(res["opportunityStatus"], "EXPIRED")
        self.assertEqual(res["registrationStatus"], "CLOSED")
        self.assertTrue(res["isExpired"])
        self.assertFalse(res["isClosingSoon"])
        self.assertLess(res["daysRemaining"], 0)
        # MUST remove from active recommendations
        self.assertFalse(res["isRecommended"])

    def test_closing_soon_handling(self):
        """If an event deadline is within 7 days, mark CLOSING_SOON."""
        ref_time = datetime(2026, 10, 26, 0, 0, 0)
        # Deadline is October 31, 2026 (5 days away)
        closing_item = dict(self.valid_college_item, deadline="October 31, 2026")
        res = OpportunitiesService.verify_item(closing_item, current_time=ref_time)

        self.assertEqual(res["opportunityStatus"], "CLOSING_SOON")
        self.assertEqual(res["registrationStatus"], "CLOSING_SOON")
        self.assertTrue(res["isClosingSoon"])
        self.assertFalse(res["isExpired"])
        self.assertEqual(res["daysRemaining"], 5)

    def test_cancelled_event_handling(self):
        """If an event is cancelled, mark CANCELLED and remove from active recommendations."""
        cancelled_item = dict(self.valid_college_item, is_cancelled=True, isRecommended=True)
        res = OpportunitiesService.verify_item(cancelled_item)

        self.assertEqual(res["opportunityStatus"], "CANCELLED")
        self.assertEqual(res["registrationStatus"], "CANCELLED")
        self.assertTrue(res["isCancelled"])
        self.assertFalse(res["isRecommended"])

    def test_update_official_source(self):
        """If an official source changes, update existing record and re-verify."""
        # Use an existing registry item id
        item_id = "col-news-nsp-2026"
        new_source = "Ministry of Education NSP Verification Desk"
        new_url = "https://scholarships.gov.in/schemes"

        success = OpportunitiesService.update_official_source(item_id, new_source, new_url)
        self.assertTrue(success)

        # Confirm update in registry
        found = False
        for it in OpportunitiesService.COLLEGE_NEWS_REGISTRY:
            if it["id"] == item_id:
                found = True
                self.assertEqual(it["source"], new_source)
                self.assertEqual(it["sourceUrl"], new_url)
                self.assertEqual(it["verificationStatus"], "VERIFIED")
                break
        self.assertTrue(found)

    def test_mark_cancelled_method(self):
        """mark_cancelled marks the registry item as cancelled."""
        item_id = "col-news-meity-ai-2026"
        success = OpportunitiesService.mark_cancelled(item_id)
        self.assertTrue(success)

        found = False
        for it in OpportunitiesService.COLLEGE_NEWS_REGISTRY:
            if it["id"] == item_id:
                found = True
                self.assertEqual(it["opportunityStatus"], "CANCELLED")
                self.assertTrue(it["isCancelled"])
                self.assertFalse(it["isRecommended"])
                break
        self.assertTrue(found)

    def test_full_pipeline_run_and_reporting(self):
        """run_verification_pipeline refreshes all registries and outputs a summary report."""
        report = OpportunitiesService.run_verification_pipeline()
        self.assertTrue(report["success"])
        self.assertIn("lastVerifiedAt", report)
        self.assertGreater(report["total_items_processed"], 0)
        self.assertGreater(report["total_verified"], 0)
        self.assertEqual(report["rule"], "UNVERIFIED = NOT ELIGIBLE FOR VERIFIED DISPLAY")

    def test_background_scheduler_idempotency(self):
        """Background scheduler starts cleanly without duplicate daemon threads."""
        OpportunitiesService.start_background_scheduler(interval_hours=12)
        self.assertTrue(OpportunitiesService._scheduler_started)
        # Calling again should not raise or restart
        OpportunitiesService.start_background_scheduler(interval_hours=12)
        self.assertTrue(OpportunitiesService._scheduler_started)


if __name__ == "__main__":
    unittest.main()
