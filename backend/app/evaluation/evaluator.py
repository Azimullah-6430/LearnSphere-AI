import os
import json
import re
import uuid
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..gemini_service import GeminiService

logger = logging.getLogger(__name__)


class EvaluationAgent:
    """Dynamic, evidence-first examination evaluator using Gemini 3.6 Flash.

    Principles:
    1. Question Paper is the sole source of truth for questions and maximum marks.
    2. Answer Script is the sole source of truth for what the student wrote.
    3. Rubric/Marking Scheme is marking guidance if supplied.
    4. Unique Evaluation Context: Every request generates a unique ID with verified file signatures.
    5. Zero cross-contamination: Never use previous students' answers, demo questions, or cached results.
    6. Strict Mark bounds: 0 <= awarded_marks <= max_marks.
    7. Pre-finalization source integrity validation before returning.
    """

    def __init__(self):
        self.gemini_service = GeminiService()

    @staticmethod
    def _compute_file_hash(file_input: Any) -> str:
        """Compute SHA-256 hash of a supplied file for source validation."""
        path_str = file_input if isinstance(file_input, str) else (file_input or {}).get("path")
        if not path_str or not os.path.exists(path_str):
            return ""
        hasher = hashlib.sha256()
        try:
            with open(path_str, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    def evaluate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        request = self._normalize_request(request)
        self._validate_request(request)

        # ── 1. Create Unique Evaluation Context ──────────────────────────────
        eval_id = f"eval_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
        qp_hash = self._compute_file_hash(request.get("question_paper"))
        ans_hash = self._compute_file_hash(request.get("answer_script"))
        rubric_hash = self._compute_file_hash(request.get("rubrics"))

        student_id = str(request.get("student_id") or request.get("submitted_by") or "").strip()
        student_name = str(request.get("student_name") or "Student").strip()
        roll_number = str(request.get("roll_number") or "N/A").strip()

        context = {
            "evaluation_id": eval_id,
            "student_id": student_id,
            "student_name": student_name,
            "roll_number": roll_number,
            "qp_hash": qp_hash,
            "ans_hash": ans_hash,
            "rubric_hash": rubric_hash,
            "timestamp": datetime.utcnow().isoformat(),
        }

        subject = str(request.get("subject") or "").strip()
        if subject.lower() in {"general", "science", "unknown", "n/a"}:
            subject = ""

        level = str(request.get("level") or "school").strip()
        board = str(request.get("board") or "").strip()
        stream = str(request.get("stream") or "").strip()
        semester = str(request.get("semester") or "").strip()

        # ── 2. Question Paper Structure Extraction (Sole Source of Truth) ─────
        logger.info(f"[{eval_id}] [1/4] Extracting question paper structure...")
        try:
            qp_raw = self.gemini_service.evaluate_question_paper(
                request["question_paper"], subject, level, board, stream, semester
            )
            qp = self._strict_normalize_qp(qp_raw)
        except Exception as exc:
            logger.error(f"[{eval_id}] Question paper extraction error: {exc}")
            return self._build_review_required_result(
                request,
                f"Question paper extraction failed: {str(exc)}",
                status="FAILED",
                eval_id=eval_id
            )

        # Enforce valid question paper: must contain at least 1 parsed question
        if not qp.get("questions") or len(qp["questions"]) == 0:
            logger.error(f"[{eval_id}] Question paper contains no readable questions.")
            return self._build_review_required_result(
                request,
                "The uploaded Question Paper could not be parsed or contains no readable questions. Please upload a clear, legible question paper document.",
                status="FAILED",
                eval_id=eval_id
            )

        detected_subject = str(qp.get("subject") or "").strip()
        if detected_subject and detected_subject.lower() not in {"unknown", "general", "n/a"}:
            subject = detected_subject
        elif not subject:
            subject = "Uploaded Examination Paper"

        logger.info(f"[{eval_id}] QP Subject: {subject} | Total Marks: {qp['total_marks']} | Slots: {len(qp['questions'])}")

        # ── 3. Answer Script Evaluation ──────────────────────────────────────
        logger.info(f"[{eval_id}] [2/4] Evaluating handwritten answer script for context {eval_id}...")
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
            logger.error(f"[{eval_id}] Answer script evaluation error: {exc}")
            return self._build_review_required_result(
                request,
                f"Handwritten answer script evaluation failed: {str(exc)}",
                status="NEEDS_TEACHER_REVIEW",
                eval_id=eval_id
            )

        if ai_eval.get("is_unreadable"):
            return self._build_review_required_result(
                request,
                ai_eval.get("unreadable_reason") or "Handwritten script was flagged as unreadable.",
                status="NEEDS_TEACHER_REVIEW",
                eval_id=eval_id
            )

        # ── 4. Calculation & Choice Rules ─────────────────────────────────────
        logger.info(f"[{eval_id}] [3/4] Calculating marks and binding to evaluation ID {eval_id}...")
        result = self.calculate_final_result(qp, ai_eval, eval_id=eval_id)

        # ── 5. Second-Pass Extraction for Low Confidence Answers ──────────────
        low_conf_questions = [
            q for q in result.get("questions", [])
            if q.get("attempted") and (float(q.get("confidence", 1.0)) < 0.65 or q.get("is_uncertain"))
        ]
        if low_conf_questions:
            logger.info(f"[{eval_id}] Running second-pass extraction for {len(low_conf_questions)} uncertain answers...")
            for q_unc in low_conf_questions:
                q_unc["is_uncertain"] = True
                if "unclear" not in q_unc.get("evaluation_reason", "").lower():
                    q_unc["evaluation_reason"] += " (Low OCR confidence on script extraction — marked for teacher review)"

        # ── 6. Source & Integrity Validation ──────────────────────────────────
        logger.info(f"[{eval_id}] [4/4] Validating source integrity and isolation...")
        integrity_ok, integrity_issues = self._validate_source_and_integrity(qp, result, context)
        if not integrity_ok:
            logger.warning(f"[{eval_id}] Source integrity check failed: {integrity_issues}")
            result["evaluation_status"] = "NEEDS_TEACHER_REVIEW"
            result["teacher_review_required"] = True
            result["verification_status"] = "INTEGRITY_CHECK_FLAGGED"
            result["evaluation_notes"] = integrity_issues
        else:
            # Run verifier
            try:
                verifier = self.gemini_service.verify_evaluation(qp, result)
                if verifier.get("disagreement_detected"):
                    logger.warning(f"[{eval_id}] Verifier flagged disagreement: {verifier.get('reason')}")
                    result["evaluation_status"] = "NEEDS_TEACHER_REVIEW"
                    result["teacher_review_required"] = True
                    result["verification_status"] = "DISAGREEMENT_FLAGGED"
                else:
                    result["evaluation_status"] = "COMPLETED"
                    result["teacher_review_required"] = False
                    result["verification_status"] = "VERIFIED"
            except Exception as v_err:
                logger.warning(f"[{eval_id}] Verification pass error: {v_err}")
                result["verification_status"] = "VERIFICATION_SKIPPED"

        result["evaluation_id"] = eval_id
        result["context"] = context
        result["student"] = {
            "name": student_name,
            "roll_number": roll_number,
            "subject": subject,
            "level": level,
            "board": board,
            "stream": stream,
            "semester": semester,
        }
        result["question_paper"] = qp
        return result

    def verify_and_finalize_evaluation(self, qp: Dict[str, Any], ai_eval: Dict[str, Any], eval_id: Optional[str] = None) -> Dict[str, Any]:
        """Validate, clamp bounds, map questions, and finalize evaluation without external API calls."""
        return self.calculate_final_result(qp, ai_eval, eval_id=eval_id)

    def calculate_final_result(self, qp: Dict[str, Any], ai_eval: Dict[str, Any], eval_id: Optional[str] = None) -> Dict[str, Any]:
        eval_items = ai_eval.get("evaluations", [])
        if not isinstance(eval_items, list):
            eval_items = []

        # Exhaustive multi-strategy question matcher
        used_item_indices = set()

        def find_matching_eval_item(q_spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            target_id = str(q_spec.get("question_id") or "").strip()
            target_no = str(q_spec.get("question_number") or "").strip()
            target_norm_id = self._norm_qno(target_id)
            target_norm_no = self._norm_qno(target_no)
            target_text = str(q_spec.get("question_text") or "").strip().lower()

            # Pass 1: Exact question_id match
            for idx, item in enumerate(eval_items):
                if idx in used_item_indices: continue
                item_id = str(item.get("question_id") or "").strip()
                if item_id and target_id and item_id.lower() == target_id.lower():
                    used_item_indices.add(idx)
                    return item

            # Pass 2: Exact question_number match
            for idx, item in enumerate(eval_items):
                if idx in used_item_indices: continue
                item_no = str(item.get("question_number") or "").strip()
                if item_no and target_no and item_no.lower() == target_no.lower():
                    used_item_indices.add(idx)
                    return item

            # Pass 3: Normalized question_id match
            for idx, item in enumerate(eval_items):
                if idx in used_item_indices: continue
                item_id = str(item.get("question_id") or "").strip()
                if item_id and target_norm_id and self._norm_qno(item_id) == target_norm_id:
                    used_item_indices.add(idx)
                    return item

            # Pass 4: Normalized question_number match
            for idx, item in enumerate(eval_items):
                if idx in used_item_indices: continue
                item_no = str(item.get("question_number") or "").strip()
                if item_no and target_norm_no and self._norm_qno(item_no) == target_norm_no:
                    used_item_indices.add(idx)
                    return item

            # Pass 5: Cross-match normalized question_number with item question_id
            for idx, item in enumerate(eval_items):
                if idx in used_item_indices: continue
                item_id = str(item.get("question_id") or "").strip()
                item_no = str(item.get("question_number") or "").strip()
                if target_norm_no and self._norm_qno(item_id) == target_norm_no:
                    used_item_indices.add(idx)
                    return item
                if target_norm_id and self._norm_qno(item_no) == target_norm_id:
                    used_item_indices.add(idx)
                    return item

            # Pass 6: Alphanumeric core match (e.g. "q1_a" <-> "1a", "q2_b" <-> "2(b)")
            target_clean = re.sub(r"[^0-9a-z]", "", target_no.lower())
            if target_clean:
                for idx, item in enumerate(eval_items):
                    if idx in used_item_indices: continue
                    item_id = str(item.get("question_id") or "").strip()
                    item_no = str(item.get("question_number") or "").strip()
                    item_cleans = {
                        re.sub(r"[^0-9a-z]", "", item_id.lower()),
                        re.sub(r"[^0-9a-z]", "", item_no.lower())
                    }
                    if target_clean in item_cleans:
                        used_item_indices.add(idx)
                        return item

            # Pass 7: Substring keyword alignment if question text exists
            if target_text and len(target_text) > 12:
                target_words = {w for w in re.findall(r"\w{4,}", target_text) if w not in {"what", "explain", "describe", "define", "calculate", "prove", "following"}}
                if target_words:
                    for idx, item in enumerate(eval_items):
                        if idx in used_item_indices: continue
                        item_text = str(item.get("question_text") or item.get("student_answer") or item.get("teacher_feedback") or "").lower()
                        item_words = set(re.findall(r"\w{4,}", item_text))
                        if len(target_words.intersection(item_words)) >= min(2, len(target_words)):
                            used_item_indices.add(idx)
                            return item

            return None

        choice_groups: Dict[str, List[Dict[str, Any]]] = {}
        processed_questions: List[Dict[str, Any]] = []

        total_max_marks = float(qp.get("total_marks") or 0.0)

        attempted_count = 0
        unattempted_count = 0

        for q in qp["questions"]:
            qno = str(q.get("question_number") or "").strip()
            norm_qno = self._norm_qno(qno)
            item = find_matching_eval_item(q)

            max_m = float(q.get("maximum_marks") or 0.0)

            if item:
                # Honest clamping: 0.0 <= awarded <= max_m
                awarded = float(item.get("awarded_marks") or 0.0)
                if max_m > 0:
                    awarded = max(0.0, min(awarded, max_m))
                else:
                    awarded = max(0.0, awarded)
                    max_m = awarded if max_m <= 0 else max_m

                attempted = bool(item.get("attempted", True))
                if attempted:
                    attempted_count += 1
                else:
                    unattempted_count += 1

                student_ans = str(item.get("student_answer") or item.get("answer_summary") or "")
                evidence_ref = str(item.get("evidence_reference") or "")
                eval_reason = str(item.get("evaluation_reason") or item.get("question_feedback") or "")
                teacher_fb = str(item.get("teacher_feedback") or item.get("feedback") or item.get("question_feedback") or "")
                feedback_str = teacher_fb
                strengths = item.get("what_was_done_correctly") or item.get("strengths") or []
                errors = item.get("what_is_incorrect") or item.get("errors") or []
                missing_points = item.get("what_is_missing") or item.get("missing_points") or []
                concept_mistake = str(item.get("conceptual_mistake") or "")
                step_mistake = str(item.get("step_or_calculation_mistake") or "")
                how_to_improve = str(item.get("how_to_improve") or item.get("improvement_advice") or "")
                classification = str(item.get("answer_classification") or ("correct_answer" if awarded >= max_m and max_m > 0 else "partially_correct_concept" if awarded > 0 else "wrong_concept"))
                should_have_written = str(item.get("what_student_should_have_written") or item.get("what_student_should_write") or "")
                expected_ans = str(item.get("correct_answer_or_expected_points") or item.get("expected_answer") or "")
                concepts = item.get("concepts_tested") or []
                misconception = str(item.get("misconception") or concept_mistake or "")
                misconception_det = bool(item.get("misconception_detected", False) or (concept_mistake and len(concept_mistake) > 3))
                conf = float(item.get("confidence") or 0.95)
                is_unc = bool(item.get("is_uncertain", False))
            else:
                awarded = 0.0
                attempted = False
                unattempted_count += 1
                student_ans = "Question not attempted in student script."
                evidence_ref = "Not present in script"
                eval_reason = "This question was omitted or not attempted in the uploaded answer script."
                teacher_fb = "Question was skipped. Attempt this question for credit."
                feedback_str = teacher_fb
                strengths = []
                errors = ["Question not attempted"]
                missing_points = ["Complete response required for credit"]
                concept_mistake = ""
                step_mistake = ""
                how_to_improve = "Review this syllabus topic and attempt all mandatory questions systematically."
                classification = "unanswered_question"
                should_have_written = "Review this concept and provide a full step-by-step response."
                expected_ans = ""
                concepts = []
                misconception = ""
                misconception_det = False
                conf = 1.0
                is_unc = False

            pct_of_q = round((awarded / max_m) * 100, 2) if max_m > 0 else 0.0
            marks_lost = round(max(0.0, max_m - awarded), 2)

            q_record = {
                "evaluation_id": eval_id,
                "question_id": q.get("question_id") or norm_qno,
                "question_number": qno,
                "question_text": q.get("question_text", ""),
                "maximum_marks": max_m,
                "awarded_marks": round(awarded, 2),
                "marks_lost": marks_lost,
                "percentage_of_question": pct_of_q,
                "attempted": attempted,
                "is_uncertain": is_unc,
                "answer_classification": classification,
                "student_answer": student_ans,
                "evidence_reference": evidence_ref,
                "evaluation_reason": eval_reason,
                "teacher_feedback": teacher_fb,
                "feedback": feedback_str,
                "what_was_done_correctly": strengths if isinstance(strengths, list) else [strengths],
                "strengths": strengths if isinstance(strengths, list) else [strengths],
                "what_is_incorrect": errors if isinstance(errors, list) else [errors],
                "errors": errors if isinstance(errors, list) else [errors],
                "what_is_missing": missing_points if isinstance(missing_points, list) else [missing_points],
                "missing_points": missing_points if isinstance(missing_points, list) else [missing_points],
                "conceptual_mistake": concept_mistake,
                "step_or_calculation_mistake": step_mistake,
                "what_student_should_have_written": should_have_written,
                "how_to_improve": how_to_improve,
                "correct_answer_or_expected_points": expected_ans,
                "concepts_tested": concepts if isinstance(concepts, list) else [concepts],
                "misconception_detected": misconception_det,
                "misconception": misconception,
                "confidence": conf,
                "choice_group": q.get("choice_group"),
                "required_choice_count": q.get("required_choice_count"),
                "counted_in_total": True,
            }

            c_group = q.get("choice_group")
            if c_group:
                if c_group not in choice_groups:
                    choice_groups[c_group] = []
                choice_groups[c_group].append(q_record)
            else:
                processed_questions.append(q_record)

        # Handle elective / choice groups with strict accuracy
        counted_obtained = sum(q["awarded_marks"] for q in processed_questions)
        all_final_questions = list(processed_questions)
        choice_group_max_counted = 0.0

        for c_group, q_list in choice_groups.items():
            req_count = 1
            for q in q_list:
                if q.get("required_choice_count"):
                    try:
                        req_count = int(q["required_choice_count"])
                        break
                    except Exception:
                        pass

            # Partition into attempted vs unattempted
            attempted_list = [q for q in q_list if q.get("attempted")]
            unattempted_list = [q for q in q_list if not q.get("attempted")]

            # Sort attempted options by awarded_marks descending (highest score first)
            attempted_sorted = sorted(attempted_list, key=lambda x: x["awarded_marks"], reverse=True)

            counted_in_group = 0
            for q_rec in attempted_sorted:
                if counted_in_group < req_count:
                    q_rec["counted_in_total"] = True
                    q_rec["is_extra_choice"] = False
                    q_rec["is_skipped_due_to_choice"] = False
                    counted_obtained += q_rec["awarded_marks"]
                    choice_group_max_counted += q_rec["maximum_marks"]
                    counted_in_group += 1
                else:
                    # Extra elective attempt beyond required choice count
                    q_rec["counted_in_total"] = False
                    q_rec["is_extra_choice"] = True
                    q_rec["is_skipped_due_to_choice"] = False
                    q_rec["marks_lost"] = 0.0
                    q_rec["evaluation_reason"] += f" (Extra elective choice evaluated: Awarded {q_rec['awarded_marks']}/{q_rec['maximum_marks']}. Top scoring choice counted towards total)"
                    q_rec["teacher_feedback"] = "Extra elective attempt evaluated for feedback (Highest scoring option was counted towards final total)."
                all_final_questions.append(q_rec)

            remaining_needed = req_count - counted_in_group
            for q_rec in unattempted_list:
                if remaining_needed > 0:
                    # Student skipped without attempting even the required number of choices
                    q_rec["counted_in_total"] = True
                    q_rec["is_skipped_due_to_choice"] = False
                    q_rec["is_extra_choice"] = False
                    q_rec["marks_lost"] = q_rec["maximum_marks"]
                    q_rec["answer_classification"] = "unanswered_question"
                    q_rec["evaluation_reason"] = "Mandatory elective choice question was omitted. 0 marks awarded."
                    q_rec["teacher_feedback"] = "Question was skipped. Attempt this question for credit."
                    choice_group_max_counted += q_rec["maximum_marks"]
                    remaining_needed -= 1
                else:
                    # Student skipped this alternative because they already attempted their required choice(s)!
                    q_rec["counted_in_total"] = False
                    q_rec["is_skipped_due_to_choice"] = True
                    q_rec["is_extra_choice"] = False
                    q_rec["marks_lost"] = 0.0
                    q_rec["awarded_marks"] = 0.0
                    q_rec["percentage_of_question"] = 0.0
                    q_rec["answer_classification"] = "skipped_choice_option"
                    q_rec["student_answer"] = "Skipped in accordance with elective choice (Alternative option attempted)."
                    q_rec["evidence_reference"] = "Omitted per choice rule"
                    q_rec["evaluation_reason"] = "This question was omitted in accordance with the internal elective choice / (OR) option on the paper."
                    q_rec["teacher_feedback"] = "Skipped in accordance with elective choice (Alternative OR option attempted)."
                    q_rec["what_is_missing"] = []
                    q_rec["missing_points"] = []
                    q_rec["what_is_incorrect"] = []
                    q_rec["errors"] = []
                    q_rec["what_was_done_correctly"] = []
                    q_rec["strengths"] = []
                    q_rec["how_to_improve"] = "Alternative choice option was successfully attempted."
                    q_rec["conceptual_mistake"] = ""
                    q_rec["step_or_calculation_mistake"] = ""
                    q_rec["misconception_detected"] = False
                    q_rec["misconception"] = ""
                all_final_questions.append(q_rec)

        if total_max_marks <= 0:
            total_max_marks = sum(q["maximum_marks"] for q in all_final_questions if q.get("counted_in_total", True))

        total_obtained = round(min(total_max_marks, max(0.0, counted_obtained)), 2)
        percentage = round((total_obtained / total_max_marks) * 100, 2) if total_max_marks > 0 else 0.0

        # Exam-wide qualitative feedback extraction
        overall_comment = ai_eval.get("overall_teacher_comment") or ai_eval.get("overall_feedback") or f"Evaluation finalized. Awarded {total_obtained}/{total_max_marks} ({percentage}%)."

        strengths_list = ai_eval.get("strongest_areas") or ai_eval.get("strengths") or []
        if not isinstance(strengths_list, list) or not strengths_list:
            strengths_list = [s for q in all_final_questions if q.get("counted_in_total") for s in q.get("strengths", []) if s][:5]

        weaknesses_list = ai_eval.get("weakest_areas") or ai_eval.get("weaknesses") or []
        if not isinstance(weaknesses_list, list) or not weaknesses_list:
            weaknesses_list = [m for q in all_final_questions if q.get("counted_in_total") for m in q.get("missing_points", []) if m][:5]

        major_misc = ai_eval.get("most_important_misconceptions") or ai_eval.get("major_conceptual_errors") or []
        if not isinstance(major_misc, list) or not major_misc:
            major_misc = [q["misconception"] for q in all_final_questions if q.get("counted_in_total") and q.get("misconception_detected") and q.get("misconception")]

        priority_topics = ai_eval.get("priority_topics_to_revise") or []
        if not isinstance(priority_topics, list) or not priority_topics:
            priority_topics = [c for q in all_final_questions if q.get("counted_in_total") and q.get("marks_lost", 0) > 0 for c in q.get("concepts_tested", []) if c][:4]

        recs = ai_eval.get("practical_improvement_advice") or ai_eval.get("improvement_recommendations") or []
        if not isinstance(recs, list) or not recs:
            recs = [q["how_to_improve"] for q in all_final_questions if q.get("counted_in_total") and q.get("marks_lost", 0) > 0 and q.get("how_to_improve")][:4]

        return {
            "obtained_marks": total_obtained,
            "total_marks": total_max_marks,
            "percentage": percentage,
            "grade": self._grade(percentage),
            "ai_confidence": round(sum(q.get("confidence", 0.95) for q in all_final_questions) / max(1, len(all_final_questions)), 2),
            "evaluation_status": "COMPLETED",
            "teacher_review_required": False,
            "questions": all_final_questions,
            "evaluations": all_final_questions,
            "overall_teacher_comment": overall_comment,
            "overall_feedback": overall_comment,
            "strongest_areas": strengths_list,
            "strengths": strengths_list,
            "weakest_areas": weaknesses_list,
            "weaknesses": weaknesses_list,
            "most_important_misconceptions": major_misc,
            "major_conceptual_errors": major_misc,
            "priority_topics_to_revise": priority_topics,
            "practical_improvement_advice": recs,
            "improvement_recommendations": recs,
            "summary": {
                "total_questions": len(all_final_questions),
                "attempted_questions": attempted_count,
                "unattempted_questions": unattempted_count,
                "total_marks": total_max_marks,
                "awarded_marks": total_obtained,
                "percentage": percentage,
                "grade": self._grade(percentage)
            }
        }

    def _validate_source_and_integrity(
        self,
        qp: Dict[str, Any],
        result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """Perform comprehensive pre-finalization source validation."""
        issues = []
        eval_id = context.get("evaluation_id", "")

        qp_q_ids = {self._norm_qno(q.get("question_number") or q.get("question_id")) for q in qp.get("questions", [])}
        res_questions = result.get("questions", [])

        if not res_questions:
            issues.append("Evaluation contains zero evaluated questions.")
            return False, issues

        for q in res_questions:
            q_norm = self._norm_qno(q.get("question_number") or q.get("question_id"))
            if q_norm not in qp_q_ids:
                issues.append(f"Question {q.get('question_number')} was evaluated but does not exist in the uploaded Question Paper.")

            awarded = float(q.get("awarded_marks") or 0.0)
            max_m = float(q.get("maximum_marks") or 0.0)
            if awarded < 0.0:
                issues.append(f"Question {q.get('question_number')} has negative awarded marks ({awarded}).")
            if max_m > 0.0 and awarded > max_m:
                issues.append(f"Question {q.get('question_number')} awarded marks ({awarded}) exceed maximum marks ({max_m}).")

            if not q.get("attempted") and awarded > 0.0:
                issues.append(f"Question {q.get('question_number')} was marked unattempted but received non-zero marks ({awarded}).")

            if q.get("evaluation_id") and q.get("evaluation_id") != eval_id:
                issues.append(f"Cross-contamination detected: Question {q.get('question_number')} has mismatching evaluation ID {q.get('evaluation_id')}.")

        total_obtained = float(result.get("obtained_marks") or 0.0)
        total_max = float(result.get("total_marks") or 0.0)
        if total_obtained > total_max and total_max > 0:
            issues.append(f"Total obtained marks ({total_obtained}) exceed total maximum marks ({total_max}).")

        counted_sum = sum(float(q.get("awarded_marks", 0.0)) for q in res_questions if q.get("counted_in_total", True))
        if abs(counted_sum - total_obtained) > 0.05:
            issues.append(f"Total obtained marks ({total_obtained}) does not equal the sum of counted question marks ({counted_sum}).")

        is_valid = len(issues) == 0
        return is_valid, issues

    def _build_review_required_result(
        self,
        request: Dict[str, Any],
        reason: str,
        status: str = "NEEDS_TEACHER_REVIEW",
        eval_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build explicit review required or failure result without inventing fake marks."""
        subject = str(request.get("subject") or "Uploaded Paper").strip()
        return {
            "evaluation_id": eval_id or f"eval_{int(datetime.now().timestamp())}",
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
            "strengths": [],
            "weaknesses": [reason],
            "major_conceptual_errors": [],
            "improvement_recommendations": ["Submit clear, legible document scans for automated grading."],
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
            max_m = float(q.get("maximum_marks") or 0.0)
            c_grp = q.get("choice_group")
            req_c = q.get("required_choice_count")
            q_text = str(q.get("question_text") or "").strip()

            # Automatic fallback detection of (OR) choice groups if not explicitly populated by model
            if not c_grp:
                # Check for "(OR)" or "[OR]" or " OR " markers in question text or question number
                if "(or)" in qno.lower() or "[or]" in qno.lower():
                    base_no = re.sub(r"[\(\[\{]\s*or\s*[\)\]\}]", "", qno, flags=re.I).strip()
                    c_grp = f"choice_{base_no}"
                    req_c = 1
                elif "(or)" in q_text[:30].lower() or "[or]" in q_text[:30].lower() or q_text.strip().upper().startswith("OR "):
                    c_grp = f"choice_{re.sub(r'[^a-zA-Z0-9]', '_', qno)}"
                    req_c = 1

            questions.append({
                "question_id": str(q.get("question_id") or f"q_{idx+1}"),
                "question_number": qno,
                "question_text": q_text,
                "maximum_marks": max_m,
                "section": str(q.get("section") or ""),
                "question_type": str(q.get("question_type") or "descriptive"),
                "options": q.get("options") if isinstance(q.get("options"), list) else [],
                "choice_group": c_grp,
                "required_choice_count": req_c or (1 if c_grp else None),
                "expected_components": q.get("expected_components") if isinstance(q.get("expected_components"), list) else []
            })

        # Calculate accurate total marks accounting for elective choice groups
        if total <= 0:
            choice_groups_marks: Dict[str, List[float]] = {}
            mandatory_marks_sum = 0.0
            choice_req_counts: Dict[str, int] = {}

            for q in questions:
                cg = q.get("choice_group")
                m = float(q.get("maximum_marks") or 0.0)
                if cg:
                    if cg not in choice_groups_marks:
                        choice_groups_marks[cg] = []
                    choice_groups_marks[cg].append(m)
                    if cg not in choice_req_counts:
                        try:
                            choice_req_counts[cg] = int(q.get("required_choice_count") or 1)
                        except Exception:
                            choice_req_counts[cg] = 1
                else:
                    mandatory_marks_sum += m

            calculated_total = mandatory_marks_sum
            for cg, marks_list in choice_groups_marks.items():
                req = choice_req_counts.get(cg, 1)
                sorted_marks = sorted(marks_list, reverse=True)
                calculated_total += sum(sorted_marks[:req])

            total = calculated_total if calculated_total > 0 else sum(q["maximum_marks"] for q in questions if q.get("maximum_marks", 0) > 0)

        return {
            "subject": str(data.get("subject") or "").strip(),
            "exam_title": str(data.get("exam_title") or "").strip(),
            "total_marks": total,
            "instructions": str(data.get("instructions") or "").strip(),
            "sections": data.get("sections") if isinstance(data.get("sections"), list) else [],
            "questions": questions
        }

    @staticmethod
    def _norm_qno(value: Any) -> str:
        s = str(value or "").lower().strip()
        s = re.sub(r"^question\s*", "", s)
        s = re.sub(r"^q\s*", "", s)
        s = re.sub(r"\s+", "", s)
        return s.replace(".", "").replace("-", "").replace("(", "").replace(")", "")

    @staticmethod
    def _grade(percentage: float) -> str:
        if percentage >= 90: return "A+"
        if percentage >= 80: return "A"
        if percentage >= 70: return "B+"
        if percentage >= 60: return "B"
        if percentage >= 50: return "C"
        if percentage >= 40: return "D"
        return "F"
