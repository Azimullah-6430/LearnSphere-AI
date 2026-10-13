"""
LearnSphere AI - Multi-Level Evidence-Based Plagiarism Detector
Detects exact file duplicates, content-level fingerprints (renamed duplicate files),
answer-level text similarity, repeated submissions, and student collusion.
Provides teacher review signals with concrete matched evidence passages.
"""

import os
import re
import hashlib
import zipfile
import xml.etree.ElementTree as ET
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from ..db import get_mongodb, get_sqlite_db

logger = logging.getLogger(__name__)


class PlagiarismDetector:
    """Multi-level plagiarism and collusion detection engine."""

    def __init__(self):
        pass

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
        t = re.sub(r'[^a-z0-9\s]', ' ', t)
        return " ".join(t.split())

    @classmethod
    def _extract_text_from_file(cls, filepath: str) -> str:
        """Extract plain text from PDF, DOCX, or text-based documents."""
        if not filepath or not os.path.exists(filepath):
            return ""

        ext = Path(filepath).suffix.lower()

        # 1. PDF extraction using PyMuPDF (fitz)
        if ext == ".pdf":
            try:
                try:
                    import pymupdf as fitz
                except ImportError:
                    import fitz
                doc = fitz.open(filepath)
                pages_text = []
                for page in doc:
                    txt = page.get_text("text") or ""
                    if txt.strip():
                        pages_text.append(txt.strip())
                doc.close()
                return "\n".join(pages_text)
            except Exception as e:
                logger.warning(f"[Plagiarism] PDF text extraction failed for {filepath}: {e}")
                return ""

        # 2. DOCX extraction using zipfile & XML parsing (zero external dependencies)
        elif ext == ".docx":
            try:
                with zipfile.ZipFile(filepath) as z:
                    xml_content = z.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    paragraphs = []
                    for node in tree.iter():
                        if node.tag.endswith("}p"):
                            p_text = "".join(t.text for t in node.iter() if t.text)
                            if p_text.strip():
                                paragraphs.append(p_text.strip())
                    return "\n".join(paragraphs)
            except Exception as e:
                logger.warning(f"[Plagiarism] DOCX text extraction failed for {filepath}: {e}")
                return ""

        # 3. Plain text formats (.txt, .md, .csv, .json)
        elif ext in (".txt", ".md", ".csv", ".json", ".tsv"):
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"[Plagiarism] Text file read failed for {filepath}: {e}")
                return ""

        return ""

    @classmethod
    def extract_text_and_fingerprints(cls, source: Any) -> Dict[str, Any]:
        """
        Extract text, compute raw file hash, and compute content-based fingerprint.
        Supports file paths, dicts with text/path, or direct text strings.
        """
        raw_text = ""
        file_sha256 = ""
        filepath = ""

        if isinstance(source, dict):
            if source.get("text"):
                raw_text = str(source["text"]).strip()
            if source.get("path"):
                filepath = str(source["path"])
        elif isinstance(source, str):
            if os.path.exists(source) and os.path.isfile(source):
                filepath = source
            else:
                raw_text = source.strip()

        if filepath and os.path.exists(filepath):
            file_sha256 = cls._calculate_sha256(filepath)
            if not raw_text:
                raw_text = cls._extract_text_from_file(filepath).strip()

        normalized = cls._normalize_text(raw_text)
        tokens = normalized.split() if normalized else []

        # Content fingerprint: SHA-256 of normalized text tokens (detects renamed duplicate files)
        content_fingerprint = ""
        if len(tokens) >= 5:
            content_fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

        return {
            "raw_text": raw_text,
            "normalized_text": normalized,
            "tokens": tokens,
            "token_count": len(tokens),
            "file_sha256": file_sha256,
            "content_fingerprint": content_fingerprint,
            "filepath": filepath,
            "has_content": bool(raw_text or file_sha256),
        }

    @staticmethod
    def _find_overlapping_passage(tokens1: List[str], tokens2: List[str], min_length: int = 5) -> str:
        """Find the longest consecutive matching word sequence between two token lists."""
        if not tokens1 or not tokens2 or len(tokens1) < min_length or len(tokens2) < min_length:
            return ""

        phrase_map = {}
        for i in range(len(tokens2) - min_length + 1):
            phrase = " ".join(tokens2[i:i + min_length])
            if phrase not in phrase_map:
                phrase_map[phrase] = i

        longest_match = []
        i = 0
        while i < len(tokens1) - min_length + 1:
            phrase = " ".join(tokens1[i:i + min_length])
            if phrase in phrase_map:
                j = phrase_map[phrase]
                k = 0
                while i + k < len(tokens1) and j + k < len(tokens2) and tokens1[i + k] == tokens2[j + k]:
                    k += 1
                if k > len(longest_match):
                    longest_match = tokens1[i:i + k]
                i += max(1, k)
            else:
                i += 1

        return " ".join(longest_match)

    @staticmethod
    def _is_test_record(doc: Dict[str, Any]) -> bool:
        """Reliably identify mock or unit test evaluations to exclude them from production analysis."""
        if doc.get("is_mock") is True or doc.get("is_test") is True or doc.get("is_sample") is True:
            return True
        source = str(doc.get("evaluation_source") or "").upper()
        if source in ("MOCK_TEST", "TEST_SUITE", "SAMPLE_DATA"):
            return True
        tags = doc.get("tags") or []
        if isinstance(tags, list) and any(str(t).lower() in ("test_data", "mock_record", "sample") for t in tags):
            return True
        return False

    def check(
        self,
        student_name: str = "",
        roll_number: str = "",
        subject: str = "",
        answer_script: Any = None,
        question_paper: Any = None,
        teacher_id: Optional[str] = None,
        class_id: Optional[str] = None,
        student_id: Optional[str] = None,
        evaluation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Multi-level plagiarism and integrity check against stored submissions.
        Scoped to teacher and class to prevent cross-teacher data leakage.
        Returns explicit review signals with concrete matched passages and evidence.
        """
        try:
            curr_data = self.extract_text_and_fingerprints(answer_script)
            tokens1 = curr_data["tokens"]
            file_sha256 = curr_data["file_sha256"]
            fingerprint1 = curr_data["content_fingerprint"]

            # Rule: Distinguish analysis failed / missing text from "no matches found"
            if not curr_data["has_content"]:
                return {
                    "status": "ANALYSIS_FAILED",
                    "suspected": False,
                    "similarity": 0.0,
                    "level": "error",
                    "matched_with": None,
                    "matched_student_name": None,
                    "matched_student_id": None,
                    "matched_evaluation_id": None,
                    "matched_roll_number": None,
                    "matched_passage": "",
                    "evidence": "Unable to extract readable text or verify answer script file for similarity analysis.",
                    "context": f"{subject or 'General'} Submission",
                    "details": "Plagiarism check notice: answer script file is missing, unreadable, or corrupted.",
                }

            if curr_data["token_count"] < 5 and not file_sha256:
                return {
                    "status": "INSUFFICIENT_DATA",
                    "suspected": False,
                    "similarity": 0.0,
                    "level": "info",
                    "matched_with": None,
                    "matched_student_name": None,
                    "matched_student_id": None,
                    "matched_evaluation_id": None,
                    "matched_roll_number": None,
                    "matched_passage": "",
                    "evidence": "Answer script text is insufficient (< 5 words) for meaningful similarity comparison.",
                    "context": f"{subject or 'General'} Submission",
                    "details": "Submission contains too few extractable words for cross-verification.",
                }

            # Retrieve eligible peer submissions within authorized scope
            past_evals: List[Dict[str, Any]] = []

            mongo_db = get_mongodb()
            if mongo_db is not None:
                query: Dict[str, Any] = {}
                if subject and subject.lower() not in ("general", "unknown", "n/a", ""):
                    query["subject"] = subject

                if teacher_id:
                    query["$or"] = [{"teacher_id": str(teacher_id)}, {"created_by_user_id": str(teacher_id)}]
                if class_id and str(class_id).lower() != "all":
                    query["class_id"] = str(class_id)

                # Exclude the current evaluation itself if an ID was provided
                if evaluation_id:
                    query["_id"] = {"$ne": evaluation_id}
                    query["id"] = {"$ne": str(evaluation_id)}

                cursor = mongo_db["evaluations"].find(query).sort("created_at", -1).limit(60)
                for doc in cursor:
                    if self._is_test_record(doc):
                        continue
                    if doc.get("is_unreadable"):
                        continue
                    past_evals.append({
                        "id": str(doc.get("_id") or doc.get("id")),
                        "student_id": str(doc.get("student_id") or ""),
                        "student_name": str(doc.get("student_name_snapshot") or doc.get("student_name") or "Student"),
                        "roll_number": str(doc.get("roll_number_snapshot") or doc.get("roll_number") or ""),
                        "assessment_title": doc.get("assessment_title", f"{subject} Exam"),
                        "answer_script_path": doc.get("answer_script_path"),
                        "questions": doc.get("questions") or doc.get("evaluations") or [],
                        "created_at": doc.get("created_at"),
                    })
            else:
                conn = get_sqlite_db()
                cursor = conn.cursor()
                sql = "SELECT id, student_id, student_name, student_name_snapshot, roll_number, roll_number_snapshot, subject, assessment_title, answer_script_path, is_unreadable, evaluation_source FROM evaluations WHERE 1=1"
                params: List[Any] = []

                if subject and subject.lower() not in ("general", "unknown", "n/a", ""):
                    sql += " AND subject = ?"
                    params.append(subject)

                if teacher_id:
                    sql += " AND (teacher_id = ? OR created_by_user_id = ?)"
                    params.extend([str(teacher_id), str(teacher_id)])

                if class_id and str(class_id).lower() != "all":
                    sql += " AND class_id = ?"
                    params.append(str(class_id))

                if evaluation_id:
                    sql += " AND id != ?"
                    params.append(str(evaluation_id))

                sql += " ORDER BY created_at DESC LIMIT 60"
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
                for r in rows:
                    r_dict = dict(r)
                    if self._is_test_record(r_dict) or r_dict.get("is_unreadable"):
                        continue
                    ev_id = r_dict["id"]
                    try:
                        cursor.execute("SELECT student_answer, answer_summary FROM evaluation_questions WHERE evaluation_id = ?", (ev_id,))
                        q_rows = cursor.fetchall()
                    except Exception:
                        cursor.execute("SELECT answer_summary FROM evaluation_questions WHERE evaluation_id = ?", (ev_id,))
                        q_rows = cursor.fetchall()
                    past_evals.append({
                        "id": str(ev_id),
                        "student_id": str(r_dict.get("student_id") or ""),
                        "student_name": str(r_dict.get("student_name_snapshot") or r_dict.get("student_name") or "Student"),
                        "roll_number": str(r_dict.get("roll_number_snapshot") or r_dict.get("roll_number") or ""),
                        "assessment_title": r_dict.get("assessment_title", f"{subject} Exam"),
                        "answer_script_path": r_dict.get("answer_script_path"),
                        "questions": [dict(qr) for qr in q_rows],
                    })
                conn.close()

            # Rule: Distinguish "not enough data" from "no matches found"
            if not past_evals:
                return {
                    "status": "INSUFFICIENT_DATA",
                    "suspected": False,
                    "similarity": 0.0,
                    "level": "info",
                    "matched_with": None,
                    "matched_student_name": None,
                    "matched_student_id": None,
                    "matched_evaluation_id": None,
                    "matched_roll_number": None,
                    "matched_passage": "",
                    "evidence": "No eligible peer submissions currently available in the database for comparison.",
                    "context": f"{subject or 'General'} Submission",
                    "details": "Not enough peer submissions available in this cohort for cross-verification.",
                }

            best_match: Optional[Dict[str, Any]] = None
            max_similarity = 0.0
            matched_passage = ""
            is_same_student_match = False
            match_evidence_type = ""
            colluding_group = set()

            clean_curr_roll = str(roll_number or "").strip().lower()
            clean_curr_sid = str(student_id or "").strip().lower()

            for past in past_evals:
                past_sid = str(past.get("student_id") or "").strip().lower()
                past_roll = str(past.get("roll_number") or "").strip().lower()

                # Check if this comparison is with the same student (repeated submission)
                same_student = False
                if clean_curr_sid and past_sid and clean_curr_sid == past_sid:
                    same_student = True
                elif clean_curr_roll and past_roll and clean_curr_roll not in ("n/a", "none", "") and clean_curr_roll == past_roll:
                    same_student = True

                # Extract past text & fingerprints
                past_path = past.get("answer_script_path")
                past_file_sha = ""
                past_text = ""

                if past_path and os.path.exists(past_path):
                    past_file_sha = self._calculate_sha256(past_path)
                    past_text = self._extract_text_from_file(past_path).strip()

                if not past_text:
                    past_questions = past.get("questions") or []
                    past_text = " ".join([
                        str(q.get("student_answer") or q.get("answer_summary") or "")
                        for q in past_questions if isinstance(q, dict)
                    ]).strip()

                past_normalized = self._normalize_text(past_text)
                tokens2 = past_normalized.split() if past_normalized else []
                past_fingerprint = hashlib.sha256(past_normalized.encode("utf-8")).hexdigest() if len(tokens2) >= 5 else ""

                sim = 0.0
                curr_passage = ""
                curr_evidence_type = ""

                # Level 1: Full-File SHA-256 Exact Duplicate Check
                if file_sha256 and past_file_sha and file_sha256 == past_file_sha:
                    sim = 100.0
                    curr_evidence_type = "EXACT_FILE_HASH"
                    curr_passage = " ".join(tokens1[:30]) if tokens1 else "Identical binary file hash."

                # Level 2: Content-based fingerprint match (Renamed duplicate files with identical text)
                elif fingerprint1 and past_fingerprint and fingerprint1 == past_fingerprint:
                    sim = 100.0
                    curr_evidence_type = "EXACT_CONTENT_FINGERPRINT"
                    curr_passage = " ".join(tokens1[:30]) if tokens1 else "Identical textual fingerprint."

                # Level 3: Token-level overlap and matched passage detection
                elif tokens1 and tokens2:
                    overlap_passage = self._find_overlapping_passage(tokens1, tokens2, min_length=6)
                    curr_passage = overlap_passage

                    s1 = set(tokens1)
                    s2 = set(tokens2)
                    inter = s1.intersection(s2)
                    union = s1.union(s2)

                    jaccard = (len(inter) / len(union) * 100.0) if union else 0.0
                    # Containment handles cases where one student copies a section of another's work
                    containment = (len(inter) / min(len(s1), len(s2)) * 100.0) if min(len(s1), len(s2)) > 0 else 0.0

                    # Weighted composite similarity: balance global structure and dense local overlap
                    composite_sim = round(max(jaccard, containment * 0.9), 1)

                    # Require meaningful passage match for high scores
                    if overlap_passage and len(overlap_passage.split()) >= 10:
                        composite_sim = max(composite_sim, 80.0)

                    sim = composite_sim
                    curr_evidence_type = "TEXT_OVERLAP"

                if sim >= 80.0 and not same_student:
                    colluding_group.add(past["student_name"])

                if sim > max_similarity:
                    max_similarity = sim
                    best_match = past
                    matched_passage = curr_passage
                    is_same_student_match = same_student
                    match_evidence_type = curr_evidence_type

            # Rule: Distinguish exact/near-duplicate, repeated submissions, ordinary similarity, and no match
            if max_similarity >= 95.0 or match_evidence_type in ("EXACT_FILE_HASH", "EXACT_CONTENT_FINGERPRINT"):
                if is_same_student_match:
                    status = "REPEATED_SUBMISSION"
                    suspected = True
                    level = "warning"
                    details = (
                        f"Repeated submission: identical answer script previously submitted by the same student for "
                        f"'{best_match['assessment_title']}'."
                    )
                else:
                    status = "EXACT_DUPLICATE"
                    suspected = True
                    level = "error"
                    details = (
                        f"Exact duplicate content detected with {best_match['student_name']}'s submission "
                        f"({100.0 if match_evidence_type in ('EXACT_FILE_HASH', 'EXACT_CONTENT_FINGERPRINT') else max_similarity}% match). "
                        f"Submissions share identical textual content."
                    )
            elif max_similarity >= 85.0:
                if is_same_student_match:
                    status = "REPEATED_SUBMISSION"
                    suspected = True
                    level = "warning"
                    details = (
                        f"Repeated submission: high structural similarity ({max_similarity}%) with student's previous work."
                    )
                else:
                    status = "HIGH_SIMILARITY"
                    suspected = True
                    level = "error"
                    details = (
                        f"High structural and content similarity ({max_similarity}%) detected with {best_match['student_name']}. "
                        f"Significant matching passage identified."
                    )
            elif max_similarity >= 70.0:
                status = "POSSIBLE_MATCH"
                suspected = True
                level = "warning"
                details = (
                    f"Possible similarity detected with {best_match['student_name']} ({max_similarity}%). "
                    f"Overlapping phrasing flagged for teacher review."
                )
            elif len(colluding_group) >= 3:
                status = "POSSIBLE_COLLUSION"
                suspected = True
                level = "warning"
                details = (
                    f"Identical structural pattern detected across {len(colluding_group) + 1} students: "
                    f"{', '.join(list(colluding_group)[:4])}."
                )
            elif max_similarity >= 30.0:
                status = "ORDINARY_SIMILARITY"
                suspected = False
                level = "info"
                details = (
                    f"Ordinary subject terminology and prompt overlap ({max_similarity}%). "
                    f"Within expected variation for shared assessment questions; not flagged as plagiarism."
                )
            else:
                status = "NO_MATCH"
                suspected = False
                level = "info"
                details = "Submissions compared against eligible cohort papers. All evaluated answers appear distinct."

            evidence_text = ""
            if matched_passage:
                evidence_text = f"Matched Passage: \"{matched_passage[:280]}\""
            elif match_evidence_type == "EXACT_FILE_HASH":
                evidence_text = f"Exact SHA-256 byte-for-byte file match ({file_sha256[:16]}...)."
            elif match_evidence_type == "EXACT_CONTENT_FINGERPRINT":
                evidence_text = f"Exact normalized content fingerprint match ({fingerprint1[:16]}...)."
            elif best_match:
                evidence_text = f"Highest observed token overlap ({max_similarity}%) with {best_match['student_name']}."
            else:
                evidence_text = "No matching passages found across stored cohort submissions."

            return {
                "status": status,
                "suspected": suspected,
                "similarity": round(max_similarity, 1),
                "level": level,
                "matched_with": best_match["student_name"] if best_match else None,
                "matched_student_name": best_match["student_name"] if best_match else None,
                "matched_student_id": best_match.get("student_id") if best_match else None,
                "matched_roll_number": best_match.get("roll_number") if best_match else None,
                "matched_evaluation_id": best_match.get("id") if best_match else None,
                "matched_passage": matched_passage,
                "evidence": evidence_text,
                "evidence_type": match_evidence_type,
                "is_repeated_submission": is_same_student_match,
                "colluding_group": list(colluding_group) if colluding_group else [],
                "context": f"{subject or 'General'} Submission Comparison",
                "details": details,
            }

        except Exception as exc:
            logger.error("[Plagiarism] Check exception: %s", exc, exc_info=True)
            return {
                "status": "ANALYSIS_FAILED",
                "suspected": False,
                "similarity": 0.0,
                "level": "error",
                "matched_with": None,
                "matched_student_name": None,
                "matched_student_id": None,
                "matched_evaluation_id": None,
                "matched_roll_number": None,
                "matched_passage": "",
                "evidence": f"Analysis interrupted due to internal error: {str(exc)}",
                "context": f"{subject or 'General'} Script",
                "details": f"Plagiarism analysis failed: {str(exc)}",
            }
