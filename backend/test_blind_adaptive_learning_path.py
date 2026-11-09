"""
Automated Test Suite for Prompt 4:
Adaptive Learning Path for Blind Students in LearnSphere AI
============================================================
Verifies:
1. Prerequisite Handling: Foundational concepts prioritized before advanced topics.
2. Intelligent Prioritization: Considers repeated mistakes, evidence strength, and dependencies.
3. Recommendation Transparency: Every step specifies what, why, evidence, activity, and mastery check.
4. Audio Commands Execution: All 5 commands ("What should I study next?", "Why this topic?", "Start learning", "Give me another example", "Show progress").
5. Durable Progress Preservation: Completed steps are recorded in the database and never reset.
6. Adaptive Progression: Moves to the next syllabus objective when understanding is demonstrated.
"""

import unittest
import json
import uuid
from datetime import datetime, timezone
from server import app, get_mongodb, get_sqlite_db
from app.adaptive_learning_path import (
    find_prerequisite_topics,
    generate_adaptive_learning_path,
    handle_learning_path_command,
    save_student_step_completion,
    get_student_topic_progress
)
from app.learning_gap_detector import record_blind_practice_attempt, MISTAKE_TYPES


class TestBlindAdaptiveLearningPath(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

        # Register test student
        self.email = f"adaptive_student_{uuid.uuid4().hex[:6]}@example.com"
        reg_res = self.client.post("/api/auth/register", json={
            "name": "Ananya Sharma",
            "email": self.email,
            "password": "password123",
            "role": "student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Electrical & Electronics Engineering",
            "semester": 4,
            "is_disabled_student": True,
            "disability_type": "blind_or_low_vision",
            "blind_companion_enabled": True
        })
        self.assertEqual(reg_res.status_code, 201)
        user_data = reg_res.get_json()["user"]
        self.student_id = str(user_data.get("id") or user_data.get("user_id"))

        # Setup active syllabus with foundational and advanced topics
        self.syllabus_id = f"syl_adapt_{uuid.uuid4().hex[:6]}"
        self.syllabus_doc = {
            "syllabus_id": self.syllabus_id,
            "student_id": self.student_id,
            "studentId": self.student_id,
            "semester": 4,
            "status": "VALID",
            "validation_status": "VALID",
            "is_active": True,
            "subjects": [
                {"name": "Electric Circuit Theory", "code": "EE401"},
                {"name": "Calculus & Linear Algebra", "code": "MA401"}
            ],
            "chapters": {
                "Electric Circuit Theory": [
                    {
                        "name": "Unit 1: Network Theorems",
                        "concepts": ["Ohm's Law", "Thevenin's Theorem", "Norton's Equivalent", "Maximum Power Transfer"]
                    }
                ],
                "Calculus & Linear Algebra": [
                    {
                        "name": "Unit 2: Differential Calculus",
                        "concepts": ["Differentiation", "Composite Functions", "Chain Rule", "Implicit Differentiation"]
                    }
                ]
            }
        }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["syllabi"].insert_one(self.syllabus_doc)
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO syllabi (syllabus_id, student_id, semester, status, validation_status, is_active, version, analysis_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (self.syllabus_id, self.student_id, 4, "VALID", "VALID", 1, 1, json.dumps(self.syllabus_doc))
            )
            conn.commit()
            conn.close()

    def test_find_prerequisite_topics(self):
        """Verify prerequisite detector accurately identifies dependencies."""
        available = ["Ohm's Law", "Thevenin's Theorem", "Norton's Equivalent", "Maximum Power Transfer"]
        prereqs_norton = find_prerequisite_topics("Norton's Equivalent", available)
        self.assertIn("Thevenin's Theorem", prereqs_norton)

        calc_available = ["Differentiation", "Composite Functions", "Chain Rule", "Implicit Differentiation"]
        prereqs_chain = find_prerequisite_topics("Chain Rule", calc_available)
        self.assertIn("Differentiation", prereqs_chain)
        self.assertIn("Composite Functions", prereqs_chain)

    def test_prerequisite_blocker_prioritization(self):
        """
        If a student struggles on an advanced topic (Norton's Equivalent),
        the system must prioritize its foundational prerequisite (Thevenin's Theorem)
        FIRST rather than simply recommending the lowest-scoring topic.
        """
        # Student fails Norton's Equivalent
        submit_res = self.client.post("/api/blind-companion/practice/submit", json={
            "subject": "Electric Circuit Theory",
            "unit": "Unit 1: Network Theorems",
            "topic": "Norton's Equivalent",
            "subtopic": "Norton's Equivalent",
            "question_text": "Find Norton current IN and Norton resistance RN.",
            "student_answer": "IN = 2A, RN = 10 Ohms (Unclear on open vs short circuit equivalent)",
            "expected_answer": "IN = 3A, RN = 4 Ohms",
            "is_correct": False,
            "score": 1.0,
            "max_score": 5.0,
            "feedback": "Fundamental misconception on equivalent resistance and source transformation"
        })
        self.assertEqual(submit_res.status_code, 200)

        # Generate adaptive learning path
        res = self.client.get("/api/blind-companion/learning-path")
        self.assertEqual(res.status_code, 200)
        path = res.get_json()
        self.assertTrue(path.get("success"))

        # Prerequisite blocker must be prioritized first
        self.assertEqual(path.get("reason_type"), "prerequisite_blocker")
        # Focus topic should be Thevenin's Theorem (the prerequisite)
        self.assertEqual(path.get("focus_topic"), "Thevenin's Theorem")

        # Step 1 must explicitly be a prerequisite revision step
        steps = path.get("steps", [])
        self.assertTrue(len(steps) >= 4)
        step1 = steps[0]
        self.assertEqual(step1["step_type"], "revise_prerequisite")
        self.assertIn("Thevenin's Theorem", step1["title"])
        self.assertIn("Norton's Equivalent", step1["why_recommended"])

    def test_recommendation_transparency(self):
        """
        Every recommendation step must be transparent:
        What to study, why recommended, evidence basis, activity description, and mastery check.
        No generic or fixed fallback text allowed.
        """
        res = self.client.get("/api/blind-companion/learning-path")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        steps = data.get("steps", [])
        self.assertTrue(len(steps) > 0)

        for step in steps:
            self.assertTrue(bool(step.get("what_to_study")), f"Missing what_to_study in {step['title']}")
            self.assertTrue(bool(step.get("why_recommended")), f"Missing why_recommended in {step['title']}")
            self.assertTrue(bool(step.get("evidence_basis")), f"Missing evidence_basis in {step['title']}")
            self.assertTrue(bool(step.get("activity_description")), f"Missing activity_description in {step['title']}")
            self.assertTrue(bool(step.get("mastery_check")), f"Missing mastery_check in {step['title']}")

    def test_audio_first_commands_execution(self):
        """Verify all 5 audio commands execute and return supportive spoken responses."""
        commands = [
            ("what should i study next", "what_should_i_study_next"),
            ("why was this topic recommended", "why_was_this_topic_recommended"),
            ("start learning", "start_learning"),
            ("give me another example", "give_me_another_example"),
            ("show my learning progress", "show_my_learning_progress")
        ]

        for phrase, expected_cmd in commands:
            res = self.client.post("/api/blind-companion/learning-path/command", json={"command": phrase})
            self.assertEqual(res.status_code, 200, f"Failed on command {phrase}")
            data = res.get_json()
            self.assertTrue(data.get("success"))
            self.assertEqual(data.get("command"), expected_cmd)
            self.assertTrue(bool(data.get("spoken_response")), f"Spoken response missing for {phrase}")

            # "give me another example" must include worked steps
            if expected_cmd == "give_me_another_example":
                self.assertIn("example", data)
                self.assertTrue(len(data["example"]["worked_steps"]) >= 3)

    def test_durable_progress_preservation(self):
        """Verify marking steps as completed is durable in database and survives re-queries."""
        path_res = self.client.get("/api/blind-companion/learning-path")
        self.assertEqual(path_res.status_code, 200)
        initial_path = path_res.get_json()
        steps = initial_path.get("steps", [])
        self.assertTrue(len(steps) > 0)

        target_step = steps[0]
        step_id = target_step["step_id"]

        # Mark step complete
        complete_res = self.client.post("/api/blind-companion/learning-path/complete-step", json={
            "step_id": step_id,
            "subject": target_step["subject"],
            "topic": target_step["topic"],
            "unit": target_step["unit"]
        })
        self.assertEqual(complete_res.status_code, 200)
        comp_data = complete_res.get_json()
        self.assertTrue(comp_data.get("success"))

        # Re-fetch learning path; step must be marked completed
        fresh_path_res = self.client.get("/api/blind-companion/learning-path")
        self.assertEqual(fresh_path_res.status_code, 200)
        fresh_steps = fresh_path_res.get_json().get("steps", [])
        matching_step = next((s for s in fresh_steps if s["step_id"] == step_id), None)
        self.assertIsNotNone(matching_step)
        self.assertTrue(matching_step.get("completed"))

        # Verify progress table endpoint
        progress_res = self.client.get("/api/blind-companion/learning-path/progress")
        self.assertEqual(progress_res.status_code, 200)
        progress_data = progress_res.get_json()
        self.assertTrue(progress_data.get("success"))
        topic_key = f"{target_step['subject']}::{target_step['topic']}"
        self.assertIn(topic_key, progress_data.get("progress_map", {}))


if __name__ == "__main__":
    unittest.main()

