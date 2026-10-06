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

        # Exhaustive multi-strategy question matcher with strict hierarchy enforcement
        used_item_indices = set()

        def find_matching_eval_item(q_spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            target_id = str(q_spec.get("question_id") or "").strip()
            target_no = str(q_spec.get("question_number") or "").strip()
            target_norm_id = self._norm_qno(target_id)
            target_norm_no = self._norm_qno(target_no)
            target_text = str(q_spec.get("question_text") or "").strip().lower()

            target_hier = self._parse_q_hierarchy(target_no)
            if target_hier == (None, None, None):
                target_hier = self._parse_q_hierarchy(target_id)

            def get_item_hiers(item: Dict[str, Any]) -> tuple[tuple[Optional[int], Optional[str], Optional[str]], tuple[Optional[int], Optional[str], Optional[str]]]:
                h_no = self._parse_q_hierarchy(item.get("question_number"))
                h_id = self._parse_q_hierarchy(item.get("question_id"))
                return h_no, h_id

            def is_item_compatible(item: Dict[str, Any]) -> bool:
                h_no, h_id = get_item_hiers(item)
                # If item has explicit question number hierarchy, check compatibility
                if h_no != (None, None, None):
                    if not self.is_hierarchy_compatible(target_hier, h_no):
                        return False
                if h_id != (None, None, None):
                    if not self.is_hierarchy_compatible(target_hier, h_id):
                        return False
                return True

            # Pass 1: Exact question_id match
            for idx, item in enumerate(eval_items):
                if idx in used_item_indices: continue
                item_id = str(item.get("question_id") or "").strip()
                if item_id and target_id and item_id.lower() == target_id.lower():
                    if is_item_compatible(item):
                        used_item_indices.add(idx)
                        return item

            # Pass 2: Exact question_number match
            for idx, item in enumerate(eval_items):
                if idx in used_item_indices: continue
                item_no = str(item.get("question_number") or "").strip()
                if item_no and target_no and item_no.lower() == target_no.lower():
                    if is_item_compatible(item):
                        used_item_indices.add(idx)
                        return item

            # Pass 3: Strict Hierarchy Exact Match (e.g. 6(a)(i) <-> 6.a.1 or 7b(ii) <-> 7(b)(ii))
            if target_hier[0] is not None:
                for idx, item in enumerate(eval_items):
                    if idx in used_item_indices: continue
                    h_no, h_id = get_item_hiers(item)
                    if self.is_hierarchy_exact_match(target_hier, h_no) or self.is_hierarchy_exact_match(target_hier, h_id):
                        used_item_indices.add(idx)
                        return item

            # Pass 4: Normalized question_id / question_number match
            for idx, item in enumerate(eval_items):
                if idx in used_item_indices: continue
                item_id = str(item.get("question_id") or "").strip()
                item_no = str(item.get("question_number") or "").strip()
                if target_norm_id and (self._norm_qno(item_id) == target_norm_id or self._norm_qno(item_no) == target_norm_id):
                    if is_item_compatible(item):
                        used_item_indices.add(idx)
                        return item
                if target_norm_no and (self._norm_qno(item_no) == target_norm_no or self._norm_qno(item_id) == target_norm_no):
                    if is_item_compatible(item):
                        used_item_indices.add(idx)
                        return item

            # Pass 5: Alphanumeric core match (e.g. "q1_a" <-> "1a", "q2_b" <-> "2(b)")
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
                    if target_clean in item_cleans and is_item_compatible(item):
                        used_item_indices.add(idx)
                        return item

            # Pass 6: Substring keyword alignment ONLY when hierarchy is strictly compatible
            if target_text and len(target_text) > 15:
                stop_words = {
                    "what", "explain", "describe", "define", "calculate", "prove", "following",
                    "software", "engineering", "system", "model", "diagram", "design", "process",
                    "method", "phase", "level", "type", "types", "state", "case", "write", "short",
                    "notes", "note", "with", "neat", "help", "example", "examples", "discuss",
                    "detail", "briefly", "advantages", "disadvantages", "difference", "between"
                }
                target_words = {w for w in re.findall(r"\b[a-z]{4,}\b", target_text) if w not in stop_words}
                if len(target_words) >= 2:
                    for idx, item in enumerate(eval_items):
                        if idx in used_item_indices: continue
                        if not is_item_compatible(item): continue
                        item_text = str(item.get("question_text") or item.get("student_answer") or item.get("teacher_feedback") or "").lower()
                        item_words = set(re.findall(r"\b[a-z]{4,}\b", item_text))
                        matched_words = target_words.intersection(item_words)
                        if len(matched_words) >= min(3, len(target_words)):
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

            understanding_lvl = str((item or {}).get("demonstrated_understanding_level") or (
                "thorough" if pct_of_q >= 90 else
                "substantial" if pct_of_q >= 65 else
                "partial" if pct_of_q >= 30 else
                "minimal" if pct_of_q > 0 else "none"
            ))

            q_record = {
                "evaluation_id": eval_id,
                "question_id": q.get("question_id") or norm_qno,
                "question_number": qno,
                "question_text": q.get("question_text", ""),
                "maximum_marks": max_m,
                "awarded_marks": round(awarded, 2),
                "marks_lost": marks_lost,
                "percentage_of_question": pct_of_q,
                "demonstrated_understanding_level": understanding_lvl,
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

            # Detect option-level grouping (e.g. 6(a)(i) + 6(a)(ii) belong to Option A, 6(b) belongs to Option B)
            options_map: Dict[str, List[Dict[str, Any]]] = {}

            for q in q_list:
                qno = q.get("question_number", "")
                hier = self._parse_q_hierarchy(qno)
                if hier[1]:
                    opt_key = hier[1]
                else:
                    opt_match = re.search(r"\b(?:q?\d+[\.\s]*)?\(?([a-zA-Z])\)?(?:\s*\(?[ivxlcdm0-9]+\)?)?", qno, re.I)
                    if opt_match:
                        opt_key = opt_match.group(1).lower()
                    else:
                        opt_key = q.get("question_id") or qno

                if opt_key not in options_map:
                    options_map[opt_key] = []
                options_map[opt_key].append(q)

            if len(options_map) > 1:
                # Option-level evaluation
                option_stats = []
                for opt_key, opt_qs in options_map.items():
                    opt_awarded = sum(q["awarded_marks"] for q in opt_qs if q.get("attempted"))
                    opt_max = sum(q["maximum_marks"] for q in opt_qs)
                    any_attempted = any(q.get("attempted") for q in opt_qs)
                    option_stats.append({
                        "opt_key": opt_key,
                        "questions": opt_qs,
                        "awarded": opt_awarded,
                        "max": opt_max,
                        "attempted": any_attempted
                    })

                option_stats_sorted = sorted(option_stats, key=lambda x: (1 if x["attempted"] else 0, x["awarded"]), reverse=True)

                counted_opts = 0
                for opt_stat in option_stats_sorted:
                    if counted_opts < req_count and opt_stat["attempted"]:
                        for q_rec in opt_stat["questions"]:
                            if q_rec.get("attempted"):
                                q_rec["counted_in_total"] = True
                                q_rec["is_extra_choice"] = False
                                q_rec["is_skipped_due_to_choice"] = False
                                counted_obtained += q_rec["awarded_marks"]
                            else:
                                q_rec["counted_in_total"] = True
                                q_rec["is_skipped_due_to_choice"] = False
                                q_rec["is_extra_choice"] = False
                                q_rec["marks_lost"] = q_rec["maximum_marks"]
                                q_rec["answer_classification"] = "unanswered_question"
                                q_rec["evaluation_reason"] = "Sub-question in chosen elective option was omitted. 0 marks awarded."
                            all_final_questions.append(q_rec)
                        counted_opts += 1
                    elif counted_opts < req_count and not opt_stat["attempted"]:
                        for q_rec in opt_stat["questions"]:
                            q_rec["counted_in_total"] = True
                            q_rec["is_skipped_due_to_choice"] = False
                            q_rec["is_extra_choice"] = False
                            q_rec["marks_lost"] = q_rec["maximum_marks"]
                            q_rec["answer_classification"] = "unanswered_question"
                            all_final_questions.append(q_rec)
                        counted_opts += 1
                    else:
                        is_extra = opt_stat["attempted"]
                        for q_rec in opt_stat["questions"]:
                            q_rec["counted_in_total"] = False
                            q_rec["is_skipped_due_to_choice"] = not is_extra
                            q_rec["is_extra_choice"] = is_extra
                            q_rec["marks_lost"] = 0.0
                            if not is_extra:
                                q_rec["awarded_marks"] = 0.0
                                q_rec["percentage_of_question"] = 0.0
                                q_rec["answer_classification"] = "skipped_choice_option"
                                q_rec["student_answer"] = "Skipped in accordance with elective choice (Alternative Option attempted)."
                                q_rec["evidence_reference"] = "Omitted per choice rule"
                                q_rec["evaluation_reason"] = "This question was omitted in accordance with the internal elective choice / (OR) option on the paper."
                                q_rec["teacher_feedback"] = "Skipped in accordance with elective choice (Alternative Option attempted)."
                                q_rec["what_is_missing"] = []
                                q_rec["missing_points"] = []
                                q_rec["what_is_incorrect"] = []
                                q_rec["errors"] = []
                                q_rec["what_was_done_correctly"] = []
                                q_rec["strengths"] = []
                                q_rec["how_to_improve"] = "Alternative choice option was attempted."
                                q_rec["conceptual_mistake"] = ""
                                q_rec["step_or_calculation_mistake"] = ""
                                q_rec["misconception_detected"] = False
                                q_rec["misconception"] = ""
                            else:
                                q_rec["evaluation_reason"] += f" (Extra elective option evaluated: Awarded {q_rec['awarded_marks']}/{q_rec['maximum_marks']}. Top scoring choice option counted towards total)"
                                q_rec["teacher_feedback"] = "Extra elective choice evaluated for feedback (Highest scoring option counted towards total)."
                            all_final_questions.append(q_rec)
            else:
                # Single item-level partition
                attempted_list = [q for q in q_list if q.get("attempted")]
                unattempted_list = [q for q in q_list if not q.get("attempted")]
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
        last_main_num = None
        last_opt_letter = None
        last_choice_grp = None

        for idx, q in enumerate(raw_q):
            if not isinstance(q, dict): continue
            qno = str(q.get("question_number") or q.get("question_id") or f"Q{idx+1}").strip()
            max_m = float(q.get("maximum_marks") or 0.0)
            c_grp = q.get("choice_group")
            req_c = q.get("required_choice_count")
            q_text = str(q.get("question_text") or "").strip()

            # Parse hierarchy of current item
            main_n, opt_l, sub_p = self._parse_q_hierarchy(qno)

            # Check for (OR) indicators in question number or text
            is_or_choice = bool(
                "(or)" in qno.lower() or "[or]" in qno.lower() or
                "(or)" in q_text[:35].lower() or "[or]" in q_text[:35].lower() or
                q_text.strip().upper().startswith("OR ") or q_text.strip().upper().startswith("OR\n")
            )

            # Clean '(OR)' markers from question number
            clean_qno = re.sub(r"[\(\[\{]\s*or\s*[\)\]\}]", "", qno, flags=re.I).strip()
            if clean_qno:
                qno = clean_qno

            # If main question number changes, reset last_choice_grp
            if main_n is not None and last_main_num is not None and main_n != last_main_num:
                last_choice_grp = None
                last_opt_letter = None

            # Case A: Standalone option without main number (e.g. "b", "(b)", "(b)(i)", "b)")
            if main_n is None and opt_l is not None and last_main_num is not None:
                main_n = last_main_num
                qno = f"{main_n}({opt_l})" + (f"({sub_p})" if sub_p else "")
                if not c_grp:
                    c_grp = f"choice_q{main_n}"
                    req_c = 1

            # Case B: OR marker present after a question (e.g. after 6(a), text says "(OR) Discuss waterfall...")
            if is_or_choice and last_main_num is not None:
                if main_n is None or (opt_l == "b" and main_n > last_main_num):
                    # Model mistakenly incremented main_num across an OR barrier (e.g. called 6b as 7 or 7a)
                    main_n = last_main_num
                    if not opt_l:
                        opt_l = "b"
                    qno = f"{main_n}({opt_l})" + (f"({sub_p})" if sub_p else "")
                if not c_grp:
                    c_grp = f"choice_q{main_n}"
                    req_c = 1

            # Case C: Question has same main number and different option letter (e.g. 6(a) and 6(b))
            if main_n is not None and main_n == last_main_num and opt_l is not None and last_opt_letter is not None and opt_l != last_opt_letter:
                if not c_grp:
                    c_grp = f"choice_q{main_n}"
                    req_c = 1

            # Default required choice count to 1 if choice group exists
            if c_grp and not req_c:
                req_c = 1

            if main_n is not None:
                last_main_num = main_n
            if opt_l is not None:
                last_opt_letter = opt_l
            if c_grp:
                last_choice_grp = c_grp

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

        # Backfill choice groups to earlier siblings of the same main question
        for q_item in questions:
            cg = q_item.get("choice_group")
            if cg:
                m_num = self._parse_q_hierarchy(q_item.get("question_number"))[0]
                if m_num is not None:
                    for prev_q in questions:
                        prev_m_num = self._parse_q_hierarchy(prev_q.get("question_number"))[0]
                        if prev_m_num == m_num and not prev_q.get("choice_group"):
                            prev_q["choice_group"] = cg
                            prev_q["required_choice_count"] = q_item.get("required_choice_count") or 1

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
    def _parse_q_hierarchy(val: Any) -> tuple[Optional[int], Optional[str], Optional[str]]:
        """Parse any question number or ID into (main_number, option_letter, subpart_number).
        Examples:
          '6(a)(i)' -> (6, 'a', '1')
          '6(a)(ii)' -> (6, 'a', '2')
          '6(b)' -> (6, 'b', None)
          '7a i' -> (7, 'a', '1')
          '7b (ii)' -> (7, 'b', '2')
          'q7_b_2' -> (7, 'b', '2')
          '3(i)' -> (3, None, '1')
          'Q5' -> (5, None, None)
        """
        if not val:
            return (None, None, None)
        s = str(val).strip().lower()
        s = re.sub(r"^(?:question[\s\._-]*|q[\s\._-]*(?=\d))", "", s)

        roman_to_int = {
            "i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5",
            "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10",
            "xi": "11", "xii": "12", "xiii": "13", "xiv": "14", "xv": "15"
        }

        # Compound pattern: 6(a)(i), 6.a.i, 6_a_1, 6 a i, 6(a)(1), 7_b_2
        m = re.search(r"(?:^|[^a-z0-9])(\d+)\s*[\.\_\-\s/]*\(?([a-z])\)?\s*[\.\_\-\s/]*\(?([ivxlcdm0-9]+)\)?", s)
        if m:
            main_n = int(m.group(1))
            opt_l = m.group(2).lower()
            raw_sub = m.group(3).lower()
            sub_p = roman_to_int.get(raw_sub, raw_sub)
            return (main_n, opt_l, sub_p)

        # Main + roman subpart: 3(i), 3(ii), 3(iii), 3(iv), 3(v), 3(vi), 3(vii), 3(viii), 3(ix), 3(x)
        m = re.search(r"(?:^|[^a-z0-9])(\d+)\s*[\.\_\-\s/]*\(?([ivxlcdm]+)\)?(?![a-z0-9])", s)
        if m and m.group(2).lower() in roman_to_int:
            main_n = int(m.group(1))
            raw_sub = m.group(2).lower()
            sub_p = roman_to_int[raw_sub]
            return (main_n, None, sub_p)

        # Main + option letter: 6(b), 6b, 6.b, 6_b, 6 b (excluding roman subparts)
        m = re.search(r"(?:^|[^a-z0-9])(\d+)\s*[\.\_\-\s/]*\(?([a-z])\)?(?![a-z0-9])", s)
        if m:
            main_n = int(m.group(1))
            raw_letter = m.group(2).lower()
            if raw_letter in roman_to_int and raw_letter not in {"a", "b", "c", "d", "e", "f", "g", "h"}:
                return (main_n, None, roman_to_int[raw_letter])
            return (main_n, raw_letter, None)

        # Main + numeric subpart: 3.1, 3(1), 3_1
        m = re.search(r"(?:^|[^a-z0-9])(\d+)\s*[\.\_\-\s/]+\(?(\d+)\)?(?![a-z0-9])", s)
        if m:
            main_n = int(m.group(1))
            sub_p = m.group(2)
            return (main_n, None, sub_p)

        # Standalone option + subpart: (a)(i), a.i, a_1
        m = re.search(r"(?:^|[^a-z0-9])\(?([a-z])\)?\s*[\.\_\-\s/]*\(?([ivxlcdm0-9]+)\)?", s)
        if m:
            opt_l = m.group(1).lower()
            raw_sub = m.group(2).lower()
            sub_p = roman_to_int.get(raw_sub, raw_sub)
            return (None, opt_l, sub_p)

        # Main question only: 1, 5, 12, 1.
        m = re.search(r"(?:^|[^a-z0-9])(\d+)", s)
        if m:
            return (int(m.group(1)), None, None)

        # Standalone option letter: (a) or (b)
        m = re.search(r"\(?([a-z])\)?", s)
        if m:
            return (None, m.group(1).lower(), None)

        return (None, None, None)

    @staticmethod
    def is_hierarchy_compatible(
        target_hier: tuple[Optional[int], Optional[str], Optional[str]],
        item_hier: tuple[Optional[int], Optional[str], Optional[str]]
    ) -> bool:
        """Strictly prevent cross-option (e.g. 6a vs 6b) or cross-subpart mismatching."""
        t_main, t_opt, t_sub = target_hier
        i_main, i_opt, i_sub = item_hier

        # Main question numbers must match if both present
        if t_main is not None and i_main is not None and t_main != i_main:
            return False

        # Option letters must match if both present (Option A != Option B)
        if t_opt is not None and i_opt is not None and t_opt != i_opt:
            return False

        # Subparts must match if both present (Subpart 1 != Subpart 2)
        if t_sub is not None and i_sub is not None and t_sub != i_sub:
            return False

        return True

    @staticmethod
    def is_hierarchy_exact_match(
        target_hier: tuple[Optional[int], Optional[str], Optional[str]],
        item_hier: tuple[Optional[int], Optional[str], Optional[str]]
    ) -> bool:
        t_main, t_opt, t_sub = target_hier
        i_main, i_opt, i_sub = item_hier
        if t_main is not None and i_main is not None and t_main == i_main:
            if t_opt == i_opt and t_sub == i_sub:
                return True
        return False

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
