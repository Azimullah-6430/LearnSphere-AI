import unittest
import os
import sys
import re

# Ensure backend root is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.gemini_service import gemini_service

class TestLearnAnywhereStepNumbering(unittest.TestCase):
    def setUp(self):
        self.service = gemini_service

    def test_01_unnumbered_instructions(self):
        """
        Verify unnumbered instructions are parsed into clean sequential steps
        without changing their original text or meaning.
        """
        raw_response = {
            "title": "Unnumbered Activity Test",
            "steps": [
                "Prepare 200ml of water in a clear glass container.",
                "Add three drops of vegetable oil to observe interface separation.",
                "Gently stir the mixture and observe whether the emulsion is temporary or permanent."
            ]
        }
        normalized = self.service._normalize_learn_anywhere_response(
            raw_response, subject="Chemistry", topic="Emulsions and Immiscibility"
        )
        steps = normalized.get("steps")
        self.assertIsInstance(steps, list)
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0], "Prepare 200ml of water in a clear glass container.")
        self.assertEqual(steps[1], "Add three drops of vegetable oil to observe interface separation.")
        self.assertEqual(steps[2], "Gently stir the mixture and observe whether the emulsion is temporary or permanent.")

        # Also test newline-separated unnumbered string
        str_response = {
            "title": "Multiline String Unnumbered",
            "steps": "Collect clean water.\nAdd common salt and stir.\nObserve complete dissolution."
        }
        normalized_str = self.service._normalize_learn_anywhere_response(
            str_response, subject="Chemistry", topic="Solubility"
        )
        str_steps = normalized_str.get("steps")
        self.assertEqual(len(str_steps), 3)
        self.assertEqual(str_steps[0], "Collect clean water.")
        self.assertEqual(str_steps[1], "Add common salt and stir.")
        self.assertEqual(str_steps[2], "Observe complete dissolution.")

    def test_02_already_numbered_instructions_no_double_layer(self):
        """
        Verify that already numbered instructions (e.g. 'Step 1:', '1.', '1)', '[1]', '1. Step 1:')
        have redundant prefixes stripped so frontend/backend do not add duplicate numbers,
        while preserving mathematical equations like '1 + 1 = 2' and 'x + 2 = 5'.
        """
        various_numbered = {
            "title": "Prefix Stripping Test",
            "steps": [
                "Step 1: Set up the apparatus on a level table.",
                "2. Align the optical sensor along the baseline.",
                "3) Measure initial intensity and verify that 1 + 1 = 2.",
                "Step 4 - Calculate the slope using equation: y = 2x + 1.",
                "[5] Verify that at limit x -> 0, x + 2 = 2.",
                "(6) Record final equilibrium value in observation table."
            ]
        }
        normalized = self.service._normalize_learn_anywhere_response(
            various_numbered, subject="Physics", topic="Optics and Measurement"
        )
        steps = normalized.get("steps")
        self.assertEqual(len(steps), 6)
        self.assertEqual(steps[0], "Set up the apparatus on a level table.")
        self.assertEqual(steps[1], "Align the optical sensor along the baseline.")
        self.assertEqual(steps[2], "Measure initial intensity and verify that 1 + 1 = 2.")
        self.assertEqual(steps[3], "Calculate the slope using equation: y = 2x + 1.")
        self.assertEqual(steps[4], "Verify that at limit x -> 0, x + 2 = 2.")
        self.assertEqual(steps[5], "Record final equilibrium value in observation table.")

        # Test chained double numbering '1. Step 1:'
        chained_response = {
            "title": "Chained Prefix Test",
            "steps": [
                "1. Step 1: Open terminal and verify Python installation.",
                "2. Step 2: Create a virtual environment using venv.",
                "3. Step 3: Run the test suite."
            ]
        }
        norm_chained = self.service._normalize_learn_anywhere_response(
            chained_response, subject="Computer Science", topic="Python Environment Setup"
        )
        chained_steps = norm_chained.get("steps")
        self.assertEqual(chained_steps[0], "Open terminal and verify Python installation.")
        self.assertEqual(chained_steps[1], "Create a virtual environment using venv.")
        self.assertEqual(chained_steps[2], "Run the test suite.")

    def test_03_markdown_numbered_lists(self):
        """
        Verify Markdown bold numbered lists (e.g. '1. **Step 1:** ...') are properly cleaned
        and sequential without broken markdown tags or duplicate numbering.
        """
        markdown_response = {
            "title": "Markdown List Test",
            "steps": (
                "1. **Step 1:** Inspect the leaf specimen under natural sunlight.\n"
                "2. **Step 2:** Note the stomata distribution and vein structure.\n"
                "3. **Step 3:** Draw a labeled diagram of the cross-section."
            )
        }
        normalized = self.service._normalize_learn_anywhere_response(
            markdown_response, subject="Biology", topic="Plant Anatomy"
        )
        steps = normalized.get("steps")
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0], "Inspect the leaf specimen under natural sunlight.")
        self.assertEqual(steps[1], "Note the stomata distribution and vein structure.")
        self.assertEqual(steps[2], "Draw a labeled diagram of the cross-section.")

    def test_04_multiple_activities_in_one_response(self):
        """
        Verify that responses containing multiple experiments/activities:
        - Are partitioned into independent experiments
        - Step numbering restarts from 1 for each experiment
        - Neither experiment inherits or skips step numbers
        """
        # Case A: Explicit experiments list
        multi_exp_structured = {
            "title": "Water Properties Dual Activity",
            "experiments": [
                {
                    "title": "Experiment 1: Surface Tension",
                    "steps": [
                        "Fill glass to the rim with clean water.",
                        "Carefully place a dry paperclip horizontally on surface.",
                        "Confirm that the paperclip floats due to surface tension."
                    ]
                },
                {
                    "title": "Experiment 2: Surfactant Disruption",
                    "steps": [
                        "Add a single drop of liquid soap near the floating paperclip.",
                        "Observe the immediate disruption of water surface bonds."
                    ]
                }
            ]
        }
        norm_a = self.service._normalize_learn_anywhere_response(
            multi_exp_structured, subject="Physics", topic="Fluid Surface Tension"
        )
        exps_a = norm_a.get("experiments")
        self.assertIsInstance(exps_a, list)
        self.assertEqual(len(exps_a), 2)
        # Experiment 1 has 3 steps
        self.assertEqual(len(exps_a[0]["steps"]), 3)
        self.assertEqual(exps_a[0]["steps"][0], "Fill glass to the rim with clean water.")
        # Experiment 2 has 2 steps starting from 1
        self.assertEqual(len(exps_a[1]["steps"]), 2)
        self.assertEqual(exps_a[1]["steps"][0], "Add a single drop of liquid soap near the floating paperclip.")
        # Combined steps list has total 5 steps
        self.assertEqual(len(norm_a.get("steps")), 5)

        # Case B: Multi-activity demarcated by Markdown headers in steps
        multi_exp_headers = {
            "title": "Capillary Action and Density Experiments",
            "steps": [
                "### Experiment 1: Measuring Capillary Rise",
                "1. Place a paper towel strip into colored water.",
                "2. Measure rise height at 30 seconds interval.",
                "### Experiment 2: Saline Density Comparison",
                "1. Dissolve 2 tablespoons of salt in second glass.",
                "2. Compare drop descent rate between fresh and saline water."
            ]
        }
        norm_b = self.service._normalize_learn_anywhere_response(
            multi_exp_headers, subject="Physics", topic="Capillarity"
        )
        exps_b = norm_b.get("experiments")
        self.assertEqual(len(exps_b), 2)
        self.assertIn("Capillary Rise", exps_b[0]["title"])
        self.assertEqual(len(exps_b[0]["steps"]), 2)
        self.assertEqual(exps_b[0]["steps"][0], "Place a paper towel strip into colored water.")
        self.assertEqual(exps_b[0]["steps"][1], "Measure rise height at 30 seconds interval.")

        self.assertIn("Saline Density", exps_b[1]["title"])
        self.assertEqual(len(exps_b[1]["steps"]), 2)
        self.assertEqual(exps_b[1]["steps"][0], "Dissolve 2 tablespoons of salt in second glass.")
        self.assertEqual(exps_b[1]["steps"][1], "Compare drop descent rate between fresh and saline water.")

    def test_05_headings_materials_code_blocks_and_safety_notes_mixed(self):
        """
        Verify that:
        - Headings, materials, safety notes, and observation blocks are NOT numbered as steps.
        - Materials are saved to materials list.
        - Safety notes are preserved in safety metadata.
        - Code blocks within steps remain intact and are not broken into fragmented steps.
        """
        mixed_payload = {
            "title": "Algorithmic Complexity Experiment",
            "steps": [
                "### Materials Needed",
                "Computer with Python 3, stopwatch or timer",
                "### Safety Precautions",
                "Ensure workspace has proper ergonomic lighting and seating.",
                "1. Initialize a sorted array of 10,000 integers.",
                "2. Implement binary search algorithm:\n```python\ndef binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1\n```",
                "3. Measure execution time across 50 lookup trials: time = t2 - t1.",
                "Expected Observations: Binary search executes within O(log N) operations consistently."
            ]
        }
        normalized = self.service._normalize_learn_anywhere_response(
            mixed_payload, subject="Computer Science", topic="Binary Search Complexity"
        )
        steps = normalized.get("steps")
        self.assertEqual(len(steps), 3)

        # Confirm step 1 is the actual instruction, NOT materials or safety
        self.assertEqual(steps[0], "Initialize a sorted array of 10,000 integers.")

        # Confirm step 2 retains python code block intact
        self.assertIn("def binary_search(arr, target):", steps[1])
        self.assertIn("return -1", steps[1])

        # Confirm step 3
        self.assertEqual(steps[2], "Measure execution time across 50 lookup trials: time = t2 - t1.")

        # Confirm materials and safety were extracted and NOT numbered
        self.assertTrue(any("Python" in str(m) for m in normalized.get("materials_student_has", [])))
        self.assertTrue(bool(normalized.get("safety_precautions")))
        self.assertIn("ergonomic", normalized.get("safety_precautions").lower())

    def test_06_empty_or_malformed_responses(self):
        """
        Verify that empty, None, whitespace, or malformed inputs fall back cleanly
        to valid sequential steps starting from 1 without crashing.
        """
        cases = [
            {"steps": []},
            {"steps": None},
            {"steps": ""},
            {"steps": ["   ", ""]},
            {"steps": 12345},
            {"steps": {"invalid": "dict"}}
        ]
        for c in cases:
            norm = self.service._normalize_learn_anywhere_response(c, subject="Mathematics", topic="Linear Equations")
            steps = norm.get("steps")
            self.assertIsInstance(steps, list)
            self.assertTrue(len(steps) >= 3, f"Failed for case: {c}")
            for st in steps:
                self.assertTrue(len(st.strip()) > 5)
                # Confirm no lingering prefix
                self.assertFalse(bool(re.match(r'^(?:step\s*\d+|\d+[\.)])', st, re.IGNORECASE)))

if __name__ == "__main__":
    unittest.main()
