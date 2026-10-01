"""
LearnSphere AI - Production Exam Evaluator
Dynamic, evidence-first evaluation engine powered by Gemini 3.6 Flash.
"""

import os
import json
import re
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..gemini_service import GeminiService

logger = logging.getLogger(__name__)


class EvaluationAgent:
    """Dynamic, evidence-first examination evaluator using Gemini 3.6 Flash.

    Principles:
    1. Question Paper is sole source of truth for questions and maximum marks.
    2. Optional choices / choice groups (Q1 OR Q2, Answer any 1) are respected.
    3. Handwritten Answer Script is evaluated across all pages against actual question text.
    4. Honest marking: awarded_marks <= max_marks, lost = max - awarded.
    5. Independent second verification pass.
    6. If processing fails or is unreadable -> status = NEEDS_TEACHER_REVIEW or FAILED. Never invent fake fallbacks!
    """

    def __init__(self):
        self.gemini_service = GeminiService()

    def evaluate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        request = self._normalize_request(request)
        self._validate_request(request)

        subject = str(request.get("subject") or "").strip()
        if subject.lower() in {"general", "science", "unknown", "n/a"}:
            subject = ""

        level = str(request.get("level") or "school").strip()
        board = str(request.get("board") or "").strip()
        stream = str(request.get("stream") or "").strip()
        semester = str(request.get("semester") or "").strip()

        # Step 1: Question Paper Structure Extraction
        logger.info("[1/4] Extracting complete question-paper structure with Gemini 3.6 Flash...")
        try:
            qp_raw = self.gemini_service.evaluate_question_paper(
                request["question_paper"], subject, level, board, stream, semester
            )
            qp = self._strict_normalize_qp(qp_raw)
        except Exception as exc:
            logger.error(f"Question paper extraction error: {exc}")
            return self._build_review_required_result(request, f"Question paper extraction failed: {str(exc)}", status="FAILED")

        detected_subject = str(qp.get("subject") or "").strip()
        if detected_subject and detected_subject.lower() not in {"unknown", "general", "n/a"}:
            subject = detected_subject
        elif not subject:
            subject = "Uploaded Examination Paper"

        logger.info(f"QP Subject: {subject} | Total Marks: {qp['total_marks']} | Slots: {len(qp['questions'])}")

        # Step 2: Answer Script Evaluation
        logger.info("[2/4] Evaluating complete handwritten answer script...")
        try:
            ai_eval = self.gemini_service.evaluate_answer_script(
                request["question_paper"],
                request["answer_script"],
                qp,
                subject,
                request.get("rubrics"),
                request.get("syllabus"),
                level
            )
        except Exception as exc:
            logger.error(f"Answer script evaluation error: {exc}")
            return self._build_review_required_result(request, f"Handwritten answer script evaluation failed: {str(exc)}", status="NEEDS_TEACHER_REVIEW")

        if ai_eval.get("is_unreadable"):
            return self._build_review_required_result(
                request,
                ai_eval.get("unreadable_reason") or "Handwritten script was flagged as unreadable.",
                status="NEEDS_TEACHER_REVIEW"
            )

        # Step 3: Calculation & Optional Choice Handling
        logger.info("[3/4] Calculating marks and applying optional choice rules...")
        result = self.calculate_final_result(qp, ai_eval)

        # Step 4: Independent Verification Pass
        logger.info("[4/4] Executing independent second verification pass...")
        try:
            verifier = self.gemini_service.verify_evaluation(qp, result)
            if verifier.get("disagreement_detected"):
                logger.warning(f"Verifier flagged disagreement: {verifier.get('reason')}")
                result["evaluation_status"] = "NEEDS_TEACHER_REVIEW"
                result["teacher_review_required"] = True
                result["verification_status"] = "DISAGREEMENT_FLAGGED"
            else:
                result["evaluation_status"] = "COMPLETED"
                result["teacher_review_required"] = False
                result["verification_status"] = "VERIFIED"
        except Exception as v_err:
            logger.warning(f"Verification pass error: {v_err}")
            result["verification_status"] = "VERIFICATION_SKIPPED"

        result["student"] = {
            "name": request.get("student_name", "Student"),
            "roll_number": request.get("roll_number", "N/A"),
            "subject": subject,
            "level": level,
            "board": board,
            "stream": stream,
            "semester": semester,
        }
        result["question_paper"] = qp
        return result

    def calculate_final_result(self, qp: Dict[str, Any], ai_eval: Dict[str, Any]) -> Dict[str, Any]:
        eval_items = ai_eval.get("evaluations", [])
        if not isinstance(eval_items, list):
            eval_items = []

        by_qno: Dict[str, Dict[str, Any]] = {}
        for item in eval_items:
            qno = str(item.get("question_number") or item.get("question_id") or "").strip()
            if qno:
                by_qno[self._norm_qno(qno)] = item

        choice_groups: Dict[str, List[Dict[str, Any]]] = {}
        processed_questions: List[Dict[str, Any]] = []

        total_max_marks = float(qp.get("total_marks") or 0.0)

        for q in qp["questions"]:
            qno = str(q.get("question_number") or "").strip()
            norm_qno = self._norm_qno(qno)
            item = by_qno.get(norm_qno)

            max_m = float(q.get("maximum_marks") or 0.0)
            if max_m <= 0:
                max_m = 5.0

            if item:
                awarded = float(item.get("awarded_marks") or 0.0)
                awarded = max(0.0, min(awarded, max_m))
                attempted = bool(item.get("attempted", True))
                student_ans = str(item.get("student_answer") or item.get("answer_summary") or "")
                feedback_str = str(item.get("question_feedback") or "")
                done_correctly = item.get("what_was_done_correctly") or []
                what_missing = item.get("what_is_missing") or []
                should_write = str(item.get("what_student_should_write") or "")
                expected_ans = str(item.get("correct_answer_or_expected_points") or "")
                concepts = item.get("concepts_tested") or []
                misconception = str(item.get("misconception") or "")
                misconception_det = bool(item.get("misconception_detected", False))
                conf = float(item.get("confidence") or 0.9)
            else:
                awarded = 0.0
                attempted = False
                student_ans = "Question not attempted in student script."
                feedback_str = "This question was not attempted in the uploaded script."
                done_correctly = []
                what_missing = ["Question was skipped / not attempted."]
                should_write = "Attempt the question for credit."
                expected_ans = ""
                concepts = []
                misconception = ""
                misconception_det = False
                conf = 1.0

            marks_lost = round(max_m - awarded, 2)

            q_record = {
                "question_id": q.get("question_id") or norm_qno,
                "question_number": qno,
                "question_text": q.get("question_text", ""),
                "maximum_marks": max_m,
                "awarded_marks": round(awarded, 2),
                "marks_lost": marks_lost,
                "attempted": attempted,
                "student_answer": student_ans,
                "correct_answer_or_expected_points": expected_ans,
                "question_feedback": feedback_str,
                "what_was_done_correctly": done_correctly if isinstance(done_correctly, list) else [done_correctly],
                "what_is_missing": what_missing if isinstance(what_missing, list) else [what_missing],
                "what_student_should_write": should_write,
                "concepts_tested": concepts if isinstance(concepts, list) else [concepts],
                "misconception_detected": misconception_det,
                "misconception": misconception,
                "confidence": conf,
                "choice_group": q.get("choice_group"),
                "required_choice_count": q.get("required_choice_count"),
                "feedback": {
                    "what_was_done_well": done_correctly if isinstance(done_correctly, list) else [done_correctly],
                    "missing_points": what_missing if isinstance(what_missing, list) else [what_missing],
                    "expected_answer": expected_ans,
                    "improvement": should_write
                }
            }

            c_group = q.get("choice_group")
            if c_group:
                if c_group not in choice_groups:
                    choice_groups[c_group] = []
                choice_groups[c_group].append(q_record)
            else:
                processed_questions.append(q_record)

        # Handle optional choice groups (select top required_choice_count attempts per group)
        counted_obtained = sum(q["awarded_marks"] for q in processed_questions)
        all_final_questions = list(processed_questions)

        for c_group, q_list in choice_groups.items():
            # Sort by awarded marks descending
            q_list_sorted = sorted(q_list, key=lambda x: x["awarded_marks"], reverse=True)
            req_count = q_list_sorted[0].get("required_choice_count") or 1
            try: req_count = int(req_count)
            except: req_count = 1

            for idx, q_rec in enumerate(q_list_sorted):
                if idx < req_count:
                    q_rec["counted_in_total"] = True
                    counted_obtained += q_rec["awarded_marks"]
                else:
                    q_rec["counted_in_total"] = False
                    q_rec["question_feedback"] += " (Extra optional attempt - not counted towards final total)"
                all_final_questions.append(q_rec)

        if total_max_marks <= 0:
            total_max_marks = sum(q["maximum_marks"] for q in all_final_questions if q.get("counted_in_total", True))

        total_obtained = round(min(total_max_marks, max(0.0, counted_obtained)), 2)
        percentage = round((total_obtained / total_max_marks) * 100, 2) if total_max_marks > 0 else 0.0

        return {
            "obtained_marks": total_obtained,
            "total_marks": total_max_marks,
            "percentage": percentage,
            "grade": self._grade(percentage),
            "ai_confidence": round(sum(q.get("confidence", 0.9) for q in all_final_questions) / max(1, len(all_final_questions)), 2),
            "evaluation_status": "COMPLETED",
            "teacher_review_required": False,
            "questions": all_final_questions,
            "evaluations": all_final_questions,
            "overall_feedback": ai_eval.get("overall_feedback") or f"Evaluation completed successfully. Score: {total_obtained}/{total_max_marks} ({percentage}%).",
            "summary": {
                "total_questions": len(all_final_questions),
                "total_marks": total_max_marks,
                "awarded_marks": total_obtained,
                "percentage": percentage,
                "grade": self._grade(percentage)
            }
        }

    def _build_review_required_result(self, request: Dict[str, Any], reason: str, status: str = "NEEDS_TEACHER_REVIEW") -> Dict[str, Any]:
        """Build explicit review required or failure result without inventing fake marks."""
        subject = str(request.get("subject") or "Uploaded Paper").strip()
        return {
            "obtained_marks": 0.0,
            "total_marks": 0.0,
            "percentage": 0.0,
            "grade": "NEEDS_REVIEW",
            "evaluation_status": status,
            "teacher_review_required": True,
            "unreadable_reason": reason,
            "overall_feedback": f"Evaluation could not be automatically finalized: {reason}. Manual teacher review is required.",
            "questions": [],
            "evaluations": [],
            "student": {
                "name": request.get("student_name", "Student"),
                "roll_number": request.get("roll_number", "N/A"),
                "subject": subject
            }
        }

    def _normalize_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(request, dict):
            raise ValueError("Evaluation request must be an object.")
        out = dict(request)
        for field in ("question_paper", "answer_script", "rubrics", "syllabus"):
            val = out.get(field)
            if isinstance(val, str) and val.strip():
                out[field] = {"path": val.strip()}
            elif isinstance(val, dict):
                v = dict(val)
                if not v.get("path"):
                    for k in ("filepath", "file_path", "saved_path"):
                        if v.get(k):
                            v["path"] = v[k]
                            break
                out[field] = v
        return out

    def _validate_request(self, request: Dict[str, Any]) -> None:
        for field in ("question_paper", "answer_script"):
            if not request.get(field):
                raise ValueError(f"Missing required file: {field}")
            path = Path(str(request[field].get("path", "")))
            if not path.is_file():
                raise FileNotFoundError(f"{field} file not found: {path}")
            if path.stat().st_size == 0:
                raise ValueError(f"{field} file is empty: {path.name}")

    def _strict_normalize_qp(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            data = {}
        raw_q = data.get("questions") if isinstance(data.get("questions"), list) else []
        total = float(data.get("total_marks") or 0.0)

        questions = []
        for idx, q in enumerate(raw_q):
            if not isinstance(q, dict): continue
            qno = str(q.get("question_number") or q.get("question_id") or f"Q{idx+1}").strip()
            max_m = float(q.get("maximum_marks") or 5.0)
            questions.append({
                "question_id": f"q_{idx+1}",
                "question_number": qno,
                "question_text": str(q.get("question_text") or "").strip(),
                "maximum_marks": max_m,
                "section": str(q.get("section") or ""),
                "question_type": str(q.get("question_type") or "descriptive"),
                "choice_group": q.get("choice_group"),
                "required_choice_count": q.get("required_choice_count")
            })

        if total <= 0:
            total = sum(q["maximum_marks"] for q in questions)

        return {
            "subject": str(data.get("subject") or "").strip(),
            "exam_title": str(data.get("exam_title") or "").strip(),
            "total_marks": total,
            "sections": data.get("sections") if isinstance(data.get("sections"), list) else [],
            "questions": questions
        }

    @staticmethod
    def _norm_qno(value: Any) -> str:
        s = str(value or "").lower().strip()
        s = re.sub(r"^question\s*", "", s)
        s = re.sub(r"^q\s*", "", s)
        s = re.sub(r"\s+", "", s)
        return s.replace(".", "").replace("-", "")

    @staticmethod
    def _grade(percentage: float) -> str:
        if percentage >= 90: return "A+"
        if percentage >= 80: return "A"
        if percentage >= 70: return "B+"
        if percentage >= 60: return "B"
        if percentage >= 50: return "C"
        if percentage >= 40: return "D"
        return "F"
