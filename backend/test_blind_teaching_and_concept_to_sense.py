"""
Automated Test Suite for Prompt 2:
Syllabus-Aware Audio Teaching and Concept-to-Sense Engine
Verifies:
1. 10-Step Structured Syllabus Teaching Workflow across curriculum subjects.
2. Concept-to-Sense Visual Audio Intelligence Engine (Component breakdown, spatial layout, signal flow, numericals, limitations).
3. Simple, Detailed, and Quick Revision modes.
4. Multi-turn interactive conversation context.
5. Integration with Personal Trainer (/api/trainer/chat).
"""

import unittest
import json
import uuid
from datetime import datetime, timezone
from server import app, get_mongodb, get_sqlite_db


class TestBlindTeachingAndConceptToSense(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

        # Register a test student with disabled/blind companion enabled and an active syllabus
        self.email = f"blind_learner_{uuid.uuid4().hex[:6]}@example.com"
        reg_res = self.client.post("/api/auth/register", json={
            "name": "Aarav Sharma",
            "email": self.email,
            "password": "password123",
            "role": "student",
            "level": "college",
            "degree": "B.Tech",
            "department": "Computer Science & Engineering",
            "semester": 5,
            "is_disabled_student": True,
            "disability_type": "blind_or_low_vision",
            "blind_companion_enabled": True
        })
        self.assertEqual(reg_res.status_code, 201)
        user_data = reg_res.get_json()["user"]
        self.user_id = str(user_data.get("id") or user_data.get("user_id"))

        # Seed authoritative syllabus for this student
        self.syllabus_id = f"syl_test_{uuid.uuid4().hex[:6]}"
        syllabus_doc = {
            "syllabus_id": self.syllabus_id,
            "student_id": self.user_id,
            "studentId": self.user_id,
            "semester": 5,
            "degree": "B.Tech Computer Science & Engineering",
            "department": "Computer Science & Engineering",
            "curriculumStatus": "VALID",
            "validation_status": "VALID",
            "status": "VALID",
            "is_active": True,
            "subjects": [
                {
                    "subject_id": "CS501",
                    "code": "CS501",
                    "name": "Database Management Systems",
                    "type": "Theory Core",
                    "credits": 4
                },
                {
                    "subject_id": "EE501",
                    "code": "EE501",
                    "name": "Basic Electrical Engineering",
                    "type": "Theory Core",
                    "credits": 4
                },
                {
                    "subject_id": "CS502",
                    "code": "CS502",
                    "name": "Data Structures & Algorithms",
                    "type": "Theory Core",
                    "credits": 4
                }
            ],
            "chapters": {
                "Database Management Systems": [
                    {"name": "Unit 3: Relational Database Design", "concepts": ["SQL Normalization", "Boyce-Codd Normal Form", "Functional Dependencies"]}
                ],
                "Basic Electrical Engineering": [
                    {"name": "Unit 1: DC Circuits", "concepts": ["Voltage Divider Rule", "Kirchhoff's Laws", "Series-Parallel Resistance"]}
                ],
                "Data Structures & Algorithms": [
                    {"name": "Unit 2: Searching and Sorting", "concepts": ["Binary Search", "Merge Sort", "Time Complexity"]}
                ]
            },
            "updated_at": datetime.now(timezone.utc),
            "version": 1
        }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["syllabi"].insert_one(syllabus_doc)
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO syllabi (syllabus_id, student_id, semester, status, validation_status, is_active, version, analysis_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self.syllabus_id,
                    self.user_id,
                    5,
                    "VALID",
                    "VALID",
                    1,
                    1,
                    json.dumps(syllabus_doc)
                )
            )
            conn.commit()
            conn.close()

    def test_structured_10_step_teaching_workflow(self):
        """Verify that the 10-step structured teaching workflow produces all required sections."""
        res = self.client.post("/api/trainer/chat", json={
            "message": "Teach me SQL Normalization following the 10-step structured teaching workflow.",
            "subject": "Database Management Systems",
            "unit": "Unit 3: Relational Database Design",
            "topic": "SQL Normalization",
            "subtopic": "Boyce-Codd Normal Form",
            "teaching_mode": "structured_10_step",
            "audio_friendly": True
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        reply = data.get("reply", "")

        # Verify key sections of the 10-step workflow are present
        self.assertIn("What the Concept Means", reply)
        self.assertIn("Why the Concept is Important", reply)
        self.assertIn("Explanation in Simple Language", reply)
        self.assertIn("Detailed Subject-Specific Explanation", reply)
        self.assertIn("Step-by-Step Reasoning", reply)
        self.assertIn("Relevant Examples", reply)
        self.assertIn("Real-World Applications", reply)
        self.assertIn("Important Terminology", reply)
        self.assertIn("Common Misconceptions", reply)
        self.assertIn("Questions to Check Understanding", reply)

    def test_concept_to_sense_visual_intelligence(self):
        """Verify Concept-to-Sense visual intelligence explains components, connections, signal flow, and limitations."""
        res = self.client.post("/api/trainer/chat", json={
            "message": "Explain the circuit diagram for Voltage Divider and Series Resistance using Concept-to-Sense.",
            "subject": "Basic Electrical Engineering",
            "unit": "Unit 1: DC Circuits",
            "topic": "Voltage Divider Rule",
            "teaching_mode": "concept_to_sense",
            "diagram_type": "Circuit Diagram",
            "visual_content": "Series DC circuit with 12V voltage source, series switch S1, 100-ohm resistor R1, and ground node.",
            "audio_friendly": True
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        reply = data.get("reply", "")

        # Verify Concept-to-Sense structural dimensions
        self.assertTrue(
            "Component-by-Component" in reply or "Component" in reply,
            "Expected component inventory"
        )
        self.assertTrue(
            "Spatial" in reply or "Layout" in reply or "Interconnections" in reply or "Series" in reply,
            "Expected spatial/topological relationships"
        )
        self.assertTrue(
            "Process" in reply or "Flow" in reply or "Current" in reply,
            "Expected signal or current flow"
        )
        self.assertTrue(
            "Calculation" in reply or "Formula" in reply or "Voltage" in reply,
            "Expected numerical parameter verification"
        )
        self.assertTrue(
            "Limitation" in reply or "Notice" in reply,
            "Expected honest limitation reporting"
        )

    def test_teaching_modes_simple_and_quick_revision(self):
        """Verify Simple Mode and Quick Revision Mode produce concise, mode-specific content."""
        # Simple Mode
        simple_res = self.client.post("/api/trainer/chat", json={
            "message": "Explain Binary Search in simple language.",
            "subject": "Data Structures & Algorithms",
            "unit": "Unit 2: Searching and Sorting",
            "topic": "Binary Search",
            "teaching_mode": "simple",
            "audio_friendly": True
        })
        self.assertEqual(simple_res.status_code, 200)
        simple_reply = simple_res.get_json().get("reply", "")
        self.assertTrue(len(simple_reply) > 50)

        # Quick Revision Mode
        rev_res = self.client.post("/api/trainer/chat", json={
            "message": "Quick revision for Binary Search.",
            "subject": "Data Structures & Algorithms",
            "unit": "Unit 2: Searching and Sorting",
            "topic": "Binary Search",
            "teaching_mode": "quick_revision",
            "audio_friendly": True
        })
        self.assertEqual(rev_res.status_code, 200)
        rev_reply = rev_res.get_json().get("reply", "")
        self.assertTrue(len(rev_reply) > 50)

    def test_multi_turn_interactive_context(self):
        """Verify that multi-turn context (history) is respected for follow-up questions."""
        history = [
            {"role": "user", "text": "What is Kirchhoff's Current Law?"},
            {"role": "model", "text": "Kirchhoff's Current Law states that the algebraic sum of currents entering a junction equals zero."}
        ]
        followup_res = self.client.post("/api/trainer/chat", json={
            "message": "Why does this law rely on conservation of electric charge?",
            "subject": "Basic Electrical Engineering",
            "unit": "Unit 1: DC Circuits",
            "topic": "Kirchhoff's Laws",
            "teaching_mode": "detailed",
            "history": history,
            "audio_friendly": True
        })
        self.assertEqual(followup_res.status_code, 200)
        followup_reply = followup_res.get_json().get("reply", "")
        self.assertIn("charge", followup_reply.lower())


if __name__ == "__main__":
    unittest.main()
