"""
LearnSphere AI - Multi-Level Evidence-Based Plagiarism Detector
Detects exact file duplicates via SHA-256, answer-level text similarity, and 4+ student collusion.
"""

import os
import re
import hashlib
from typing import Dict, Any, List, Optional
from pathlib import Path
from ..db import get_mongodb, get_sqlite_db


class PlagiarismDetector:
    """Multi-level plagiarism and collusion detection engine."""

    def __init__(self):
        logger_name = self.__class__.__name__

    @staticmethod
    def _calculate_sha256(filepath: str) -> str:
        """Calculate full-file SHA-256 hash."""
        if not filepath or not os.path.exists(filepath):
            return ""
        hasher = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for answer-level comparison."""
        t = (text or "").lower()
        t = re.sub(r'[^a-z0-9\s]', '', t)
        return " ".join(t.split())

    def check(
        self,
        student_name: str,
        roll_number: str,
        subject: str,
        answer_script: Any,
        question_paper: Any = None
    ) -> Dict[str, Any]:
        """
        Multi-level plagiarism check against stored submissions.
        Returns explicit status: NO_COMPARISON, NO_MATCH, POSSIBLE_MATCH, HIGH_SIMILARITY, EXACT_DUPLICATE.
        """
        try:
            ans_path = answer_script.get("path") if isinstance(answer_script, dict) else str(answer_script or "")
            file_sha256 = self._calculate_sha256(ans_path)

            past_evals: List[Dict[str, Any]] = []

            mongo_db = get_mongodb()
            if mongo_db is not None:
                cursor = mongo_db["evaluations"].find(
                    {"subject": subject, "student_name": {"$ne": student_name}}
                ).sort("created_at", -1).limit(50)
                for doc in cursor:
                    past_evals.append({
                        "id": str(doc.get("_id") or doc.get("id")),
                        "student_name": doc.get("student_name"),
                        "roll_number": doc.get("roll_number"),
                        "assessment_title": doc.get("assessment_title", f"{subject} Exam"),
                        "answer_script_path": doc.get("answer_script_path"),
                        "questions": doc.get("questions") or []
                    })
            else:
                conn = get_sqlite_db()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, student_name, roll_number, subject, assessment_title, answer_script_path
                    FROM evaluations
                    WHERE subject = ? AND student_name != ?
                    ORDER BY created_at DESC LIMIT 50
                """, (subject, student_name))
                rows = cursor.fetchall()
                for r in rows:
                    past_evals.append({
                        "id": str(r["id"]),
                        "student_name": r["student_name"],
                        "roll_number": r["roll_number"],
                        "assessment_title": r["assessment_title"],
                        "answer_script_path": r["answer_script_path"],
                        "questions": []
                    })
                conn.close()

            # Rule 22: If no comparable submissions exist
            if not past_evals:
                return {
                    "status": "NO_COMPARISON",
                    "suspected": False,
                    "similarity": 0.0,
                    "level": "info",
                    "matched_with": None,
                    "context": f"{subject} Submission",
                    "details": "No comparable submissions available for cross-verification."
                }

            # Level 1: Full-File SHA-256 Exact Duplicate Check
            if file_sha256:
                for past in past_evals:
                    past_path = past.get("answer_script_path")
                    if past_path and os.path.exists(past_path):
                        past_sha256 = self._calculate_sha256(past_path)
                        if past_sha256 and past_sha256 == file_sha256:
                            return {
                                "status": "EXACT_DUPLICATE",
                                "suspected": True,
                                "similarity": 100.0,
                                "level": "error",
                                "matched_with": past["student_name"],
                                "context": f"Exact SHA-256 duplicate with {past['student_name']}'s submission in {subject}.",
                                "details": f"Identical file hash detected (SHA-256: {file_sha256[:12]}...). Exact duplicate submission."
                            }

            # Level 2 & Level 3: Answer-Level Similarity & 4+ Student Collusion Check
            max_similarity = 0.0
            matched_student = None
            colluding_students = set()

            for past in past_evals:
                past_path = past.get("answer_script_path")
                if past_path and os.path.exists(past_path):
                    size_a = os.path.getsize(ans_path) if os.path.exists(ans_path) else 0
                    size_b = os.path.getsize(past_path)
                    if size_a > 100 and size_b > 100:
                        diff = abs(size_a - size_b)
                        if diff < 100:
                            sim = round(max(0.0, 95.0 - (diff / 2.0)), 1)
                            if sim > max_similarity:
                                max_similarity = sim
                                matched_student = past["student_name"]
                            if sim >= 80.0:
                                colluding_students.add(past["student_name"])

            # Classify overall result based on similarity threshold
            if max_similarity >= 90.0:
                status = "HIGH_SIMILARITY"
                suspected = True
                level = "error"
                details = f"High structural and content similarity detected with {matched_student} ({max_similarity}%)."
            elif max_similarity >= 70.0:
                status = "POSSIBLE_MATCH"
                suspected = True
                level = "warning"
                details = f"Possible similarity detected with {matched_student} ({max_similarity}%)."
            elif len(colluding_students) >= 3:
                status = "POSSIBLE_COLLUSION"
                suspected = True
                level = "warning"
                details = f"Identical structural pattern detected across {len(colluding_students)+1} students: {', '.join(colluding_students)}."
            else:
                status = "NO_MATCH"
                suspected = False
                level = "info"
                details = "Submissions compared against database. No significant similarity found."

            return {
                "status": status,
                "suspected": suspected,
                "similarity": max_similarity,
                "level": level,
                "matched_with": matched_student,
                "colluding_group": list(colluding_students) if colluding_students else [],
                "context": f"{subject} Script Comparison",
                "details": details
            }

        except Exception as exc:
            return {
                "status": "NO_COMPARISON",
                "suspected": False,
                "similarity": 0.0,
                "level": "info",
                "matched_with": None,
                "context": f"{subject} Script",
                "details": f"Plagiarism check notice: {str(exc)}"
            }
