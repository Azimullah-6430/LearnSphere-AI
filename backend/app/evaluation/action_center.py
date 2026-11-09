"""
LearnSphere AI - Action Center Derivation & Management Engine

Derives actionable pedagogical interventions from real class and evaluation evidence.
Requirements:
1. Build items exclusively from authorized, completed TEACHER_EVALUATION records.
2. Include all students who meet support criteria across the teacher's authorized classes.
3. Group data by student: Exactly ONE consolidated record per student per evaluation.
   All question-wise details, misconceptions, weaknesses, and recommendations are nested under that student.
4. Use explicit, explainable rules for prioritization (repeated difficulty, verified significant loss of marks).
   Calculates thresholds from actual awarded and maximum marks (no equal-maximum assumption).
5. Never label students as weak based on a single mistake or incomplete assessment.
6. Never fabricate action items, scores, priorities, or student identities.
7. Strictly exclude student self-evaluation records and unrelated activity data.
8. Avoid duplicate active action items for the same student.
9. Support review, dismissal, and completion workflows with audit tracking.
10. Refresh affected items when an evaluation is corrected / overridden.
11. Meaningful empty state support when no interventions are justified.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.db import get_mongodb, get_sqlite_db
from app.evaluation.diagnostic_engine import (
    classify_student_error,
    build_personalized_action,
    generate_individual_performance_summary,
    TAXONOMY_CONCEPTUAL_MISUNDERSTANDING,
    TAXONOMY_INCORRECT_FORMULA_SELECTION,
    TAXONOMY_INCORRECT_FORMULA_APPLICATION,
    TAXONOMY_CALCULATION_ERROR,
    TAXONOMY_MISSING_STEPS,
    TAXONOMY_INCOMPLETE_ANSWER,
    TAXONOMY_QUESTION_INTERPRETATION_ERROR,
    TAXONOMY_INCORRECT_TERMINOLOGY,
    TAXONOMY_LOGICAL_REASONING_ERROR,
    TAXONOMY_SYNTAX_PROGRAMMING_ERROR,
    TAXONOMY_CARELESS_MISTAKE,
    TAXONOMY_ALTERNATIVE_VALID_EXPRESSION,
    TAXONOMY_LABELS,
    STATUS_EVIDENCE_SUPPORTED,
    STATUS_NEEDS_TEACHER_REVIEW,
    STATUS_INSUFFICIENT_EVIDENCE,
)

logger = logging.getLogger(__name__)


def _num(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_str(val: Any, default: str = "") -> str:
    if val is None:
        return default
    s = str(val).strip()
    return s if s else default


def _count_previous_concept_difficulties(
    student_id: str,
    concept_name: str,
    current_eval_id: str,
    mongo_db: Any = None,
    sqlite_conn: Any = None,
) -> int:
    """Count previous verified occurrences of difficulty with concept_name for student."""
    if not student_id or not concept_name:
        return 0

    count = 0
    if mongo_db is not None:
        try:
            count = mongo_db["misconceptions"].count_documents({
                "student_id": str(student_id),
                "evaluation_id": {"$ne": str(current_eval_id)},
                "evaluation_source": "TEACHER_EVALUATION",
                "$or": [
                    {"identified_concept": concept_name},
                    {"concept": concept_name},
                    {"topic": {"$regex": concept_name, "$options": "i"}},
                ],
            })
        except Exception as exc:
            logger.debug("[ActionCenter] Mongo concept count error: %s", exc)
    elif sqlite_conn is not None:
        try:
            cur = sqlite_conn.cursor()
            cur.execute(
                """SELECT COUNT(*) FROM misconceptions 
                   WHERE student_id = ? AND evaluation_id != ? AND evaluation_source = 'TEACHER_EVALUATION'
                     AND (identified_concept = ? OR concept = ? OR topic LIKE ?)""",
                (str(student_id), str(current_eval_id), concept_name, concept_name, f"%{concept_name}%")
            )
            row = cur.fetchone()
            if row:
                count = int(row[0])
        except Exception as exc:
            logger.debug("[ActionCenter] SQLite concept count error: %s", exc)

    return count


def derive_action_items_from_evaluation(
    eval_doc: Dict[str, Any],
    class_name_lookup: Optional[Dict[str, str]] = None,
    mongo_db: Any = None,
    sqlite_conn: Any = None,
) -> List[Dict[str, Any]]:
    """
    Derive justified action items from a single completed teacher evaluation record.
    Returns exactly ONE consolidated student record per evaluation when intervention is justified.
    Contains all question-wise details, evidence, and recommendations grouped under that student.
    """
    # 1. Provenance & Authorization Guard: Exclude non-teacher evaluation records
    eval_source = eval_doc.get("evaluation_source") or eval_doc.get("evaluationSource")
    if eval_source != "TEACHER_EVALUATION":
        return []

    # Exclude records requiring identity review or unverified legacy
    identity_status = str(eval_doc.get("identity_status") or "").upper()
    if identity_status in ("NEEDS_REVIEW", "UNLINKED"):
        return []

    eval_id = str(eval_doc.get("id") or eval_doc.get("_id") or eval_doc.get("evaluation_id") or "")
    if not eval_id:
        return []

    student_name = _safe_str(eval_doc.get("student_name") or eval_doc.get("student_name_snapshot"), "Student")
    student_id = str(eval_doc.get("student_id") or eval_doc.get("studentId") or "")
    roll_number = _safe_str(eval_doc.get("roll_number") or eval_doc.get("roll_number_snapshot"), "N/A")
    teacher_id = str(eval_doc.get("teacher_id") or eval_doc.get("created_by_user_id") or "")
    created_by_user_id = str(eval_doc.get("created_by_user_id") or teacher_id)
    created_by_role = _safe_str(eval_doc.get("created_by_role"), "teacher")
    class_id = str(eval_doc.get("class_id") or "")
    class_name = ""
    if class_name_lookup and class_id in class_name_lookup:
        class_name = class_name_lookup[class_id]
    elif class_id:
        class_name = class_id

    subject = _safe_str(eval_doc.get("subject"), "General")
    assessment_title = _safe_str(eval_doc.get("assessment_title") or eval_doc.get("topic"), f"{subject} Assessment")

    total_marks = _num(eval_doc.get("total_marks"), 0.0)
    obtained_marks = _num(eval_doc.get("obtained_marks"), 0.0)
    calc_marks_lost = round(max(0.0, total_marks - obtained_marks), 2)
    overall_loss_ratio = (calc_marks_lost / total_marks) if total_marks > 0 else 0.0
    overall_feedback = _safe_str(eval_doc.get("overall_feedback"))

    is_unreadable = bool(eval_doc.get("is_unreadable", False))
    assigned_to_teacher = bool(eval_doc.get("assigned_to_teacher", False))
    unreadable_reason = _safe_str(eval_doc.get("unreadable_reason"))

    questions = eval_doc.get("questions") or eval_doc.get("evaluations") or []
    if isinstance(questions, str):
        try:
            questions = json.loads(questions)
        except Exception:
            questions = []
    if not isinstance(questions, list):
        questions = []

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    clean_id_suffix = (student_id or roll_number.replace(" ", "_") or "unknown").strip()
    item_id = f"act_student_{eval_id}_{clean_id_suffix}"

    # ══════════════════════════════════════════════════════════════════════════
    # CASE 1: Teacher Review Required (Low confidence / unreadable script)
    # ══════════════════════════════════════════════════════════════════════════
    if is_unreadable or assigned_to_teacher:
        return [{
            "id": f"act_teacher_review_{eval_id}",
            "evaluation_source": "TEACHER_EVALUATION",
            "evaluationSource": "TEACHER_EVALUATION",
            "created_by_user_id": created_by_user_id,
            "created_by_role": created_by_role,
            "teacher_id": teacher_id,
            "student_id": student_id,
            "class_id": class_id,
            "class_name": class_name,
            "evaluation_id": eval_id,
            "student_name": student_name,
            "roll_number": roll_number,
            "subject": subject,
            "assessment_title": assessment_title,
            "academic_status": "Manual Teacher Review Required",
            "topic": f"{subject} — Evaluation Script Review",
            "skill_or_topic": subject,
            "question_num": "Evaluation Scope",
            "question_number": "Evaluation Scope",
            "total_marks": obtained_marks,
            "maximum_marks": total_marks,
            "marks_lost": calc_marks_lost,
            "question_awarded_marks": obtained_marks,
            "question_max_marks": total_marks,
            "marks_awarded_vs_max": f"{obtained_marks} / {total_marks} marks",
            "affected_questions": ["All"],
            "marks_lost_per_question": {"All": calc_marks_lost},
            "question_details": [],
            "recommended_actions": [{
                "concept": subject,
                "action": "Review student answer script manually and confirm score.",
                "related_questions": ["All"]
            }],
            "exact_question": "Full assessment script manual review required.",
            "student_answer": "Script flagged by AI evaluator for manual teacher grading.",
            "misconception": "Evaluation script unreadable or ambiguous.",
            "learning_gap": "Evaluation script unreadable or ambiguous.",
            "evidence": unreadable_reason or "Low confidence / unreadable student script content.",
            "correct_understanding": "Curriculum standard solution key.",
            "issue": unreadable_reason or "The evaluator flagged this assessment for manual teacher review.",
            "priority": "High",
            "severity": "High",
            "priority_reason": "Low confidence or unreadable response requires manual teacher grading before final score.",
            "category": "teacher_review",
            "action": "Review student answer script manually and confirm score.",
            "recommended_action": "Review student answer script manually and confirm score.",
            "source_link": f"/app/history?eval_id={eval_id}",
            "evaluation_link": f"/app/history?eval_id={eval_id}",
            "status": "New",
            "is_unreadable": True,
            "created_at": now_str,
            "updated_at": now_str,
            "audit_trail": [{"action": "Derived from evaluation flagging", "timestamp": now_str}],
        }]

    # ══════════════════════════════════════════════════════════════════════════
    # ANALYZE QUESTIONS & COLLECT DETAILED EVIDENCE
    # ══════════════════════════════════════════════════════════════════════════
    question_details: List[Dict[str, Any]] = []
    affected_q_nums: List[str] = []
    marks_lost_per_q: Dict[str, float] = {}
    actions_by_concept: Dict[str, Dict[str, Any]] = {}
    classified_all_questions: List[Dict[str, Any]] = []
    historical_concept_occurrences: Dict[str, int] = {}
    has_critical = False
    has_high = False
    has_repeated = False
    primary_category = "severe_misconception"
    primary_concept = subject
    primary_misc = ""
    primary_action = ""
    primary_q_awarded = obtained_marks
    primary_q_max = total_marks
    primary_q_text = ""
    primary_std_ans = ""
    primary_evidence = ""
    primary_correct = ""

    for idx, q in enumerate(questions):
        if not isinstance(q, dict):
            continue

        q_num = str(q.get("question_number") or idx + 1)
        q_max = _num(q.get("maximum_marks") or q.get("max_marks"), 0.0)
        q_awarded = _num(q.get("awarded_marks"), 0.0)
        q_lost = round(max(0.0, q_max - q_awarded), 2)
        q_loss_ratio = (q_lost / q_max) if q_max > 0 else 0.0

        q_text = _safe_str(q.get("question_text"), f"Question {q_num}")
        std_ans = _safe_str(q.get("student_answer") or q.get("answer_summary"), "Answer recorded on script.")
        feedback = q.get("feedback") if isinstance(q.get("feedback"), dict) else {}
        missing = feedback.get("missing_points") or q.get("missing_points") or []
        if not isinstance(missing, list):
            missing = [str(missing)]

        concepts_list = q.get("concepts_tested") or []
        concept_name = str(
            q.get("concept")
            or q.get("identified_concept")
            or (concepts_list[0] if isinstance(concepts_list, list) and concepts_list else "")
            or q.get("topic")
            or f"Concept in Question {q_num}"
        ).strip()

        # Classify with 12-error taxonomy
        diag = classify_student_error(q, subject=subject)
        error_type = diag.get("error_type", TAXONOMY_CONCEPTUAL_MISUNDERSTANDING)
        error_label = diag.get("error_label", TAXONOMY_LABELS.get(error_type, error_type))
        is_conceptual = diag.get("is_conceptual_misconception", False)
        evidence_status = diag.get("evidence_status", STATUS_EVIDENCE_SUPPORTED)
        reason_for_classification = diag.get("reason_for_classification") or diag.get("diagnostic_summary") or ""
        diag_conf = diag.get("confidence", 0.90)

        # Check repeated difficulty across previous evaluations for this student
        prev_count = _count_previous_concept_difficulties(student_id, concept_name, eval_id, mongo_db, sqlite_conn)
        is_repeated_q = prev_count > 0
        if is_repeated_q:
            historical_concept_occurrences[concept_name.lower()] = prev_count

        classified_all_questions.append({
            "question_number": q_num,
            "concept": concept_name,
            "error_type": error_type,
            "error_label": error_label,
            "marks_lost": q_lost,
            "awarded_marks": q_awarded,
            "maximum_marks": q_max,
            "loss_ratio": round(q_loss_ratio * 100, 1),
            "evidence_status": evidence_status,
        })

        # Skip full marks / valid alternative expressions from intervention items
        if q_lost <= 0 or error_type == TAXONOMY_ALTERNATIVE_VALID_EXPRESSION:
            continue

        # Evidence construction
        evidence_text = _safe_str(
            q.get("evidence_reference")
            or f"Student wrote: '{std_ans[:90]}'. Awarded {q_awarded}/{q_max} marks. Diagnosed {error_label}."
        )
        correct_model = _safe_str(
            q.get("what_student_should_have_written")
            or q.get("correct_answer_or_expected_points")
            or feedback.get("expected_answer"),
            f"Curriculum rubric standard solution for {concept_name}."
        )

        # Build personalized pedagogical action
        pers_action = build_personalized_action(
            error_type=error_type,
            concept=concept_name,
            subject=subject,
            related_questions=[q_num],
            evidence_text=evidence_text,
            marks_lost=q_lost,
            total_marks=total_marks,
            is_repeated=is_repeated_q,
        )

        # Justification check: exclude isolated trivial slip (loss < 20% without misconception or repetition)
        is_justified = False
        if is_repeated_q:
            is_justified = True
            q_severity = "Critical"
            has_repeated = True
            has_critical = True
        elif is_conceptual and (q_loss_ratio >= 0.35 or q_lost >= 4.0 or (q_max <= 5 and q_loss_ratio >= 0.50)):
            is_justified = True
            q_severity = "Critical" if q_loss_ratio >= 0.70 else "High"
            if q_severity == "Critical":
                has_critical = True
            else:
                has_high = True
        elif is_conceptual and q_loss_ratio >= 0.20:
            is_justified = True
            q_severity = "Medium"
        elif q_loss_ratio >= 0.40 or q_lost >= 3.0:
            is_justified = True
            q_severity = "High" if q_lost >= 5.0 else "Medium"
            if q_severity == "High":
                has_high = True
        elif q_lost > 0 and len(questions) <= 4:
            is_justified = True
            q_severity = "Medium"

        if not is_justified:
            continue

        affected_q_nums.append(q_num)
        marks_lost_per_q[q_num] = q_lost

        actual_misc = str(
            q.get("misconception")
            or q.get("conceptual_mistake")
            or (missing[0] if missing else "")
            or error_label
        ).strip()

        q_detail = {
            "question_number": q_num,
            "question_text": q_text,
            "awarded_marks": q_awarded,
            "maximum_marks": q_max,
            "max_marks": q_max,
            "marks_lost": q_lost,
            "loss_ratio": round(q_loss_ratio * 100, 1),
            "student_answer": std_ans,
            "concept": concept_name,
            "misconception": actual_misc,
            "evidence": evidence_text,
            "correct_understanding": correct_model,
            "how_to_improve": pers_action["action"],
            "action": pers_action["action"],
            "activity": pers_action["activity"],
            "reason": pers_action["reason"],
            "expected_outcome": pers_action["expected_outcome"],
            "error_type": error_type,
            "error_label": error_label,
            "is_conceptual_misconception": is_conceptual,
            "evidence_status": evidence_status,
            "reason_for_classification": reason_for_classification,
            "confidence": diag_conf,
            "severity": q_severity,
        }
        question_details.append(q_detail)

        # Group recommendations by concept
        c_key = concept_name.lower().strip()
        if c_key not in actions_by_concept:
            actions_by_concept[c_key] = {
                "concept": concept_name,
                "error_type": error_type,
                "error_label": error_label,
                "action": pers_action["action"],
                "recommended_action": pers_action["action"],
                "activity": pers_action["activity"],
                "reason": pers_action["reason"],
                "expected_outcome": pers_action["expected_outcome"],
                "priority": pers_action["priority"],
                "related_questions": [q_num],
            }
        else:
            if q_num not in actions_by_concept[c_key]["related_questions"]:
                actions_by_concept[c_key]["related_questions"].append(q_num)

        # Track primary question for backward-compatible top-level properties
        if not primary_misc or q_lost > (primary_q_max - primary_q_awarded):
            primary_concept = concept_name
            primary_misc = actual_misc
            primary_action = pers_action["action"]
            primary_q_awarded = q_awarded
            primary_q_max = q_max
            primary_q_text = q_text
            primary_std_ans = std_ans
            primary_evidence = evidence_text
            primary_correct = correct_model

    # ══════════════════════════════════════════════════════════════════════════
    # CHECK ASSESSMENT-LEVEL LOSS AND INCOMPLETENESS
    # ══════════════════════════════════════════════════════════════════════════
    is_significant_loss = (calc_marks_lost > 20.0) or (total_marks > 0 and overall_loss_ratio >= 0.35 and calc_marks_lost >= 10.0)
    incomplete_qs = [
        q for q in questions
        if isinstance(q, dict) and (
            str(q.get("answer_classification") or "").lower() in {"incomplete_answer", "unanswered_question"}
            or not q.get("attempted", True)
        )
    ]
    has_multiple_incomplete = len(incomplete_qs) >= 2

    # If no questions met criteria and no assessment-level issue, return empty (Requirement 5 & 11)
    if not question_details and not is_significant_loss and not has_multiple_incomplete:
        return []

    # If question_details is empty but significant loss occurred, populate from questions
    if not question_details and is_significant_loss:
        for idx, q in enumerate(questions):
            if not isinstance(q, dict):
                continue
            q_num = str(q.get("question_number") or idx + 1)
            q_max = _num(q.get("maximum_marks") or q.get("max_marks"), 0.0)
            q_awarded = _num(q.get("awarded_marks"), 0.0)
            q_lost = round(max(0.0, q_max - q_awarded), 2)
            if q_lost > 0:
                affected_q_nums.append(q_num)
                marks_lost_per_q[q_num] = q_lost
                c_name = str(q.get("concept") or q.get("topic") or subject).strip()
                remedy = f"Assign targeted remedial worksheet on {c_name}."
                question_details.append({
                    "question_number": q_num,
                    "question_text": _safe_str(q.get("question_text"), f"Question {q_num}"),
                    "awarded_marks": q_awarded,
                    "maximum_marks": q_max,
                    "max_marks": q_max,
                    "marks_lost": q_lost,
                    "loss_ratio": round((q_lost / q_max * 100), 1) if q_max > 0 else 0,
                    "student_answer": _safe_str(q.get("student_answer"), "Script response."),
                    "concept": c_name,
                    "misconception": "Mark deficit on question.",
                    "evidence": _safe_str(q.get("evidence_reference") or f"Lost {q_lost} marks."),
                    "correct_understanding": _safe_str(q.get("what_student_should_have_written"), "Curriculum standard solution."),
                    "how_to_improve": remedy,
                    "action": remedy,
                    "severity": "High" if q_lost >= 5.0 else "Medium",
                })
                c_key = c_name.lower().strip()
                if c_key not in actions_by_concept:
                    actions_by_concept[c_key] = {
                        "concept": c_name,
                        "action": remedy,
                        "recommended_action": remedy,
                        "related_questions": [q_num],
                    }

    # Determine Priority and Severity
    if calc_marks_lost >= 35.0 or overall_loss_ratio >= 0.50 or has_repeated or has_critical:
        priority_str = "Critical"
    elif has_high or is_significant_loss or calc_marks_lost >= 15.0:
        priority_str = "High"
    else:
        priority_str = "Medium"

    # Determine Primary Category
    if has_repeated:
        primary_category = "repeated_concept_loss"
    elif is_significant_loss and len(affected_q_nums) > 2:
        primary_category = "excessive_marks_lost"
    elif has_multiple_incomplete:
        primary_category = "incomplete_answers"
    else:
        primary_category = "severe_misconception"

    # Compose Explanation
    if has_repeated:
        priority_explanation = f"Repeated difficulty: student struggled across multiple assessments with '{primary_concept}'."
    elif is_significant_loss:
        priority_explanation = (
            f"Significant mark loss: student lost {calc_marks_lost}/{total_marks} marks "
            f"({round(overall_loss_ratio * 100, 1)}% deficit) across {len(affected_q_nums)} questions."
        )
    elif len(question_details) > 1:
        priority_explanation = (
            f"Multiple learning gaps: {len(question_details)} questions with verified errors "
            f"resulting in {calc_marks_lost} marks lost."
        )
    else:
        priority_explanation = f"Verified conceptual mistake on Question {affected_q_nums[0] if affected_q_nums else '1'}: awarded {primary_q_awarded}/{primary_q_max} marks."

    recommended_actions_list = list(actions_by_concept.values())
    if not recommended_actions_list:
        default_remedy = f"Assign targeted remedial worksheet on {subject} and review core concepts."
        recommended_actions_list.append({
            "concept": subject,
            "action": default_remedy,
            "recommended_action": default_remedy,
            "related_questions": affected_q_nums or ["All"],
        })
        primary_action = default_remedy

    if not primary_action:
        primary_action = recommended_actions_list[0]["action"]
    if not primary_misc:
        primary_misc = _safe_str(
            eval_doc.get("major_conceptual_errors", ["Pedagogical deficit"])[0]
            if eval_doc.get("major_conceptual_errors")
            else "Multi-question deficit"
        )

    academic_status_str = f"Support Needed (Lost {calc_marks_lost} marks)" if calc_marks_lost > 0 else f"Concept Support ({primary_concept})"

    # Synthesize Individual Performance Summary
    perf_summary = generate_individual_performance_summary(
        eval_doc=eval_doc,
        classified_questions=classified_all_questions,
        historical_concept_occurrences=historical_concept_occurrences,
    )

    consolidated_item = {
        "id": item_id,
        "evaluation_source": "TEACHER_EVALUATION",
        "evaluationSource": "TEACHER_EVALUATION",
        "created_by_user_id": created_by_user_id,
        "created_by_role": created_by_role,
        "teacher_id": teacher_id,
        "student_id": student_id,
        "class_id": class_id,
        "class_name": class_name,
        "evaluation_id": eval_id,
        "student_name": student_name,
        "roll_number": roll_number,
        "subject": subject,
        "assessment_title": assessment_title,
        "academic_status": academic_status_str,
        "topic": f"{subject} — {primary_concept}",
        "skill_or_topic": primary_concept,
        "question_num": ", ".join(affected_q_nums[:4]) + ("..." if len(affected_q_nums) > 4 else ""),
        "question_number": ", ".join(affected_q_nums[:4]),
        "total_marks": obtained_marks,
        "maximum_marks": total_marks,
        "marks_lost": calc_marks_lost,
        "loss_ratio": round(overall_loss_ratio * 100, 1),
        "question_awarded_marks": primary_q_awarded,
        "question_max_marks": primary_q_max,
        "marks_awarded_vs_max": f"{primary_q_awarded} / {primary_q_max} marks",
        "affected_questions": affected_q_nums,
        "marks_lost_per_question": marks_lost_per_q,
        "question_details": question_details,
        "recommended_actions": recommended_actions_list,
        "performance_summary": perf_summary,
        "strengths": perf_summary.get("strengths", []),
        "concepts_needing_improvement": perf_summary.get("concepts_needing_improvement", []),
        "observed_error_breakdown": perf_summary.get("observed_error_breakdown", {}),
        "observed_errors_summary": perf_summary.get("observed_errors_summary", ""),
        "recommended_next_practice": perf_summary.get("recommended_next_practice", ""),
        "exact_question": primary_q_text or _safe_str(questions[0].get("question_text") if questions else "", "Assessment questions"),
        "student_answer": primary_std_ans or "Answer recorded on script.",
        "misconception": primary_misc,
        "learning_gap": primary_misc,
        "evidence": primary_evidence or f"Student lost {calc_marks_lost} marks across {len(affected_q_nums)} questions.",
        "correct_understanding": primary_correct or "Standard curriculum rubric models.",
        "issue": overall_feedback or priority_explanation,
        "priority": priority_str,
        "severity": priority_str,
        "priority_reason": priority_explanation,
        "category": primary_category,
        "action": primary_action,
        "recommended_action": primary_action,
        "source_link": f"/app/history?eval_id={eval_id}",
        "evaluation_link": f"/app/history?eval_id={eval_id}",
        "misconception_link": f"/app/misconceptions?class_id={class_id}&concept={primary_concept}" if class_id else "/app/misconceptions",
        "status": "New",
        "is_unreadable": is_unreadable,
        "created_at": now_str,
        "updated_at": now_str,
        "audit_trail": [{"action": "Derived student-consolidated learning gap item", "timestamp": now_str}],
    }

    return [consolidated_item]


def consolidate_action_items_by_student(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Consolidates any collection of Action Center items (including legacy question-level items)
    into exactly ONE consolidated record per student per evaluation.
    Preserves all question details, evidence, and actions while eliminating duplicate cards.
    """
    if not items:
        return []

    grouped: Dict[Tuple[str, str, str, str], List[Dict[str, Any]]] = {}

    for it in items:
        # Group key: (student_key, eval_id, class_id, subject)
        sid = _safe_str(it.get("student_id"))
        roll = _safe_str(it.get("roll_number"))
        sname = _safe_str(it.get("student_name"))
        # Use student_id if available; if missing, combine roll + name to distinguish identically named students
        student_key = sid if sid else f"{roll}_{sname}".lower()

        eval_id = _safe_str(it.get("evaluation_id") or it.get("eval_id"))
        class_id = _safe_str(it.get("class_id"))
        subject = _safe_str(it.get("subject"))

        key = (student_key, eval_id, class_id, subject)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(it)

    consolidated_list: List[Dict[str, Any]] = []

    priority_weight = {"Critical": 3, "High": 2, "Medium": 1, "Low": 0}

    for (student_key, eval_id, class_id, subject), group in grouped.items():
        if len(group) == 1 and group[0].get("question_details") and len(group[0].get("question_details")) > 0:
            # Already consolidated format
            consolidated_list.append(group[0])
            continue

        # Sort group by priority descending
        group.sort(key=lambda x: priority_weight.get(str(x.get("priority") or x.get("severity")), 1), reverse=True)
        primary = dict(group[0])

        all_q_details: List[Dict[str, Any]] = []
        seen_q_nums = set()
        all_actions_by_concept: Dict[str, Dict[str, Any]] = {}
        all_affected_qs: List[str] = []
        all_marks_lost_per_q: Dict[str, float] = {}
        max_marks_lost = 0.0

        for it in group:
            # Carry over any existing question_details
            if it.get("question_details") and isinstance(it["question_details"], list):
                for qd in it["question_details"]:
                    q_num = str(qd.get("question_number") or qd.get("question_num") or "").replace("Question ", "")
                    if q_num and q_num not in seen_q_nums:
                        seen_q_nums.add(q_num)
                        all_q_details.append(qd)
                        all_affected_qs.append(q_num)
                        all_marks_lost_per_q[q_num] = _num(qd.get("marks_lost"), 0.0)

            # Check item's direct question
            q_num_str = str(it.get("question_num") or it.get("question_number") or "").replace("Question ", "").strip()
            if q_num_str and q_num_str not in ("Evaluation Scope", "Overall Examination", "All", "") and "," not in q_num_str:
                if q_num_str not in seen_q_nums:
                    seen_q_nums.add(q_num_str)
                    q_lost = _num(it.get("marks_lost"), 0.0)
                    all_marks_lost_per_q[q_num_str] = q_lost
                    all_affected_qs.append(q_num_str)
                    all_q_details.append({
                        "question_number": q_num_str,
                        "question_text": _safe_str(it.get("exact_question"), f"Question {q_num_str}"),
                        "awarded_marks": _num(it.get("question_awarded_marks"), 0.0),
                        "maximum_marks": _num(it.get("question_max_marks"), 0.0),
                        "max_marks": _num(it.get("question_max_marks"), 0.0),
                        "marks_lost": q_lost,
                        "loss_ratio": _num(it.get("loss_ratio"), 0.0),
                        "student_answer": _safe_str(it.get("student_answer")),
                        "concept": _safe_str(it.get("skill_or_topic") or it.get("topic") or subject),
                        "misconception": _safe_str(it.get("misconception") or it.get("learning_gap")),
                        "evidence": _safe_str(it.get("evidence")),
                        "correct_understanding": _safe_str(it.get("correct_understanding")),
                        "how_to_improve": _safe_str(it.get("action") or it.get("recommended_action")),
                        "action": _safe_str(it.get("action") or it.get("recommended_action")),
                        "severity": str(it.get("priority") or it.get("severity") or "Medium"),
                    })

            # Check affected_questions list
            aff = it.get("affected_questions") or []
            if isinstance(aff, list):
                for a in aff:
                    a_str = str(a).strip()
                    if a_str and a_str not in all_affected_qs and a_str != "All":
                        all_affected_qs.append(a_str)

            # Accumulate marks lost per question
            mlpq = it.get("marks_lost_per_question") or {}
            if isinstance(mlpq, dict):
                for k, v in mlpq.items():
                    if str(k) not in all_marks_lost_per_q:
                        all_marks_lost_per_q[str(k)] = _num(v, 0.0)

            # Collect recommended actions
            c_name = _safe_str(it.get("skill_or_topic") or it.get("concept") or it.get("topic") or subject)
            act_text = _safe_str(it.get("action") or it.get("recommended_action"))
            if act_text:
                c_key = c_name.lower()
                if c_key not in all_actions_by_concept:
                    all_actions_by_concept[c_key] = {
                        "concept": c_name,
                        "action": act_text,
                        "recommended_action": act_text,
                        "related_questions": [q_num_str] if q_num_str else all_affected_qs,
                    }

            if _num(it.get("marks_lost")) > max_marks_lost:
                max_marks_lost = _num(it.get("marks_lost"))

        # Consolidate top-level fields
        primary["id"] = f"act_student_{eval_id}_{student_key.replace(' ', '_')}"
        primary["question_details"] = all_q_details
        primary["recommended_actions"] = list(all_actions_by_concept.values())
        if all_affected_qs:
            primary["affected_questions"] = all_affected_qs
            primary["question_num"] = ", ".join(all_affected_qs[:4]) + ("..." if len(all_affected_qs) > 4 else "")
            primary["question_number"] = ", ".join(all_affected_qs[:4])
        if all_marks_lost_per_q:
            primary["marks_lost_per_question"] = all_marks_lost_per_q

        if max_marks_lost > 0:
            primary["marks_lost"] = max_marks_lost

        if not primary.get("performance_summary") and all_q_details:
            perf_summary = generate_individual_performance_summary(
                eval_doc=primary,
                classified_questions=all_q_details,
                historical_concept_occurrences={},
            )
            primary["performance_summary"] = perf_summary
            primary["strengths"] = perf_summary.get("strengths", [])
            primary["concepts_needing_improvement"] = perf_summary.get("concepts_needing_improvement", [])
            primary["observed_error_breakdown"] = perf_summary.get("observed_error_breakdown", {})
            primary["observed_errors_summary"] = perf_summary.get("observed_errors_summary", "")
            primary["recommended_next_practice"] = perf_summary.get("recommended_next_practice", "")

        consolidated_list.append(primary)

    return consolidated_list
