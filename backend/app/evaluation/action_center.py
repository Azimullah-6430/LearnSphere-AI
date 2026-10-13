"""
LearnSphere AI - Action Center Derivation & Management Engine

Derives actionable pedagogical interventions from real class and evaluation evidence.
Requirements:
1. Build items exclusively from authorized, completed TEACHER_EVALUATION records.
2. Include all students who meet support criteria across the teacher's authorized classes.
3. Use explicit, explainable rules for prioritization (repeated difficulty, verified significant loss of marks).
   Calculates thresholds from actual awarded and maximum marks (no equal-maximum assumption).
4. Never label students as weak based on a single mistake or incomplete assessment.
5. Never fabricate action items, scores, priorities, or student identities.
6. Strictly exclude student self-evaluation records and unrelated activity data.
7. Avoid duplicate active action items for the same student, concept, and evidence.
8. Support review, dismissal, and completion workflows with audit tracking.
9. Refresh affected items when an evaluation is corrected / overridden.
10. Meaningful empty state support when no interventions are justified.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.db import get_mongodb, get_sqlite_db

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
    Derive all justified action items from a single completed teacher evaluation record.
    Returns a list of complete, auditable action item dictionaries.
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

    student_name = _safe_str(eval_doc.get("student_name"), "Student")
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
    if not isinstance(questions, list):
        questions = []

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    derived_items: List[Dict[str, Any]] = []

    # ══════════════════════════════════════════════════════════════════════════
    # ITEM TYPE 1: Teacher Review Required (Low confidence / unreadable script)
    # ══════════════════════════════════════════════════════════════════════════
    if is_unreadable or assigned_to_teacher:
        derived_items.append({
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
        })

    # ══════════════════════════════════════════════════════════════════════════
    # ITEM TYPE 2: Significant Loss of Marks Across Assessment
    # Requirement 3: Calculated threshold from actual marks and maximum marks.
    # Evaluates whether total marks lost > 20 OR loss_ratio >= 35% with >= 10 marks lost.
    # ══════════════════════════════════════════════════════════════════════════
    is_significant_loss = (calc_marks_lost > 20.0) or (total_marks > 0 and overall_loss_ratio >= 0.35 and calc_marks_lost >= 10.0)
    if is_significant_loss:
        affected_qs = [
            str(q.get("question_number") or i + 1)
            for i, q in enumerate(questions)
            if isinstance(q, dict) and _num(q.get("maximum_marks") or q.get("max_marks"), 0.0) > _num(q.get("awarded_marks"), 0.0)
        ]
        marks_lost_per_q = {
            str(q.get("question_number") or i + 1): round(
                max(0.0, _num(q.get("maximum_marks") or q.get("max_marks"), 0.0) - _num(q.get("awarded_marks"), 0.0)), 2
            )
            for i, q in enumerate(questions)
            if isinstance(q, dict) and _num(q.get("maximum_marks") or q.get("max_marks"), 0.0) > _num(q.get("awarded_marks"), 0.0)
        }
        worst_q = max(
            [q for q in questions if isinstance(q, dict)],
            key=lambda x: _num(x.get("maximum_marks") or x.get("max_marks"), 0.0) - _num(x.get("awarded_marks"), 0.0),
            default={},
        )
        gap_text = _safe_str(
            eval_doc.get("major_conceptual_errors", ["Overall examination deficit"])[0]
            if eval_doc.get("major_conceptual_errors")
            else "Multi-topic assessment deficit"
        )
        is_crit = calc_marks_lost >= 35.0 or overall_loss_ratio >= 0.50
        priority_str = "Critical" if is_crit else "High"
        priority_explanation = (
            f"Significant mark loss: student lost {calc_marks_lost}/{total_marks} marks "
            f"({round(overall_loss_ratio * 100, 1)}% deficit) across {len(affected_qs)} questions."
        )

        derived_items.append({
            "id": f"act_loss_{eval_id}",
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
            "academic_status": f"Support Needed (Lost {calc_marks_lost} marks)",
            "topic": f"{subject} — {assessment_title}",
            "skill_or_topic": subject,
            "question_num": ", ".join(affected_qs[:4]) + ("..." if len(affected_qs) > 4 else ""),
            "question_number": ", ".join(affected_qs[:4]),
            "total_marks": obtained_marks,
            "maximum_marks": total_marks,
            "marks_lost": calc_marks_lost,
            "loss_ratio": round(overall_loss_ratio * 100, 1),
            "question_awarded_marks": obtained_marks,
            "question_max_marks": total_marks,
            "marks_awarded_vs_max": f"{obtained_marks} / {total_marks} marks",
            "affected_questions": affected_qs,
            "marks_lost_per_question": marks_lost_per_q,
            "exact_question": _safe_str(worst_q.get("question_text"), "Multi-question examination breakdown"),
            "student_answer": _safe_str(worst_q.get("student_answer") or worst_q.get("answer_summary"), "Accumulated incorrect answers across script."),
            "misconception": gap_text,
            "learning_gap": gap_text,
            "evidence": _safe_str(worst_q.get("evidence_reference") or overall_feedback or f"Lost {calc_marks_lost} marks out of {total_marks} marks."),
            "correct_understanding": _safe_str(worst_q.get("what_student_should_have_written"), "Standard examination solutions."),
            "issue": overall_feedback or f"Student lost {calc_marks_lost} marks ({obtained_marks}/{total_marks}) across {len(affected_qs)} questions.",
            "priority": priority_str,
            "severity": priority_str,
            "priority_reason": priority_explanation,
            "category": "excessive_marks_lost",
            "action": f"Assign targeted remedial worksheet on {subject} and schedule 1-on-1 diagnostic review.",
            "recommended_action": f"Assign targeted remedial worksheet on {subject} and schedule 1-on-1 diagnostic review.",
            "source_link": f"/app/history?eval_id={eval_id}",
            "evaluation_link": f"/app/history?eval_id={eval_id}",
            "status": "New",
            "is_unreadable": is_unreadable,
            "created_at": now_str,
            "updated_at": now_str,
            "audit_trail": [{"action": "Derived from significant assessment marks deficit", "timestamp": now_str}],
        })

    # ══════════════════════════════════════════════════════════════════════════
    # ITEM TYPE 3: Question-Level Conceptual Misconceptions / Difficulties
    # Requirement 3 & 4: Uses explicit explainable rules; does not flag trivial single mistakes.
    # ══════════════════════════════════════════════════════════════════════════
    for idx, q in enumerate(questions):
        if not isinstance(q, dict):
            continue

        q_num = str(q.get("question_number") or idx + 1)
        q_max = _num(q.get("maximum_marks") or q.get("max_marks"), 0.0)
        q_awarded = _num(q.get("awarded_marks"), 0.0)
        q_lost = round(max(0.0, q_max - q_awarded), 2)
        if q_lost <= 0:
            continue

        q_loss_ratio = (q_lost / q_max) if q_max > 0 else 0.0
        feedback = q.get("feedback") if isinstance(q.get("feedback"), dict) else {}
        missing = feedback.get("missing_points") or q.get("missing_points") or []
        if not isinstance(missing, list):
            missing = [str(missing)]

        has_misc_flag = bool(q.get("misconception_detected") or q.get("misconception") or q.get("conceptual_mistake"))
        actual_misc = str(
            q.get("misconception")
            or q.get("conceptual_mistake")
            or (missing[0] if missing else "")
            or "Conceptual misunderstanding"
        ).strip()

        concepts_list = q.get("concepts_tested") or []
        concept_name = str(
            q.get("concept")
            or q.get("identified_concept")
            or (concepts_list[0] if isinstance(concepts_list, list) and concepts_list else "")
            or q.get("topic")
            or f"Concept in Question {q_num}"
        ).strip()

        # Check repeated difficulty across previous evaluations for this student
        prev_count = _count_previous_concept_difficulties(student_id, concept_name, eval_id, mongo_db, sqlite_conn)
        is_repeated = prev_count > 0

        # Requirement 4 Filter:
        # Do not label students or generate support items for a single isolated minor mistake (e.g., loss < 25% with no misconception)
        is_justified = False
        if is_repeated:
            is_justified = True
            priority_str = "Critical"
            priority_explanation = f"Repeated difficulty: student struggled with '{concept_name}' across {prev_count + 1} evaluations."
            category_str = "repeated_concept_loss"
            status_label = f"Repeated Concept Support ({concept_name})"
        elif has_misc_flag and (q_loss_ratio >= 0.40 or q_lost >= 5.0 or (q_max <= 5 and q_loss_ratio >= 0.50)):
            is_justified = True
            priority_str = "High" if q_loss_ratio < 0.70 else "Critical"
            priority_explanation = f"Verified conceptual mistake on Question {q_num}: awarded {q_awarded}/{q_max} marks ({round(q_loss_ratio * 100, 1)}% lost)."
            category_str = "severe_misconception"
            status_label = f"Concept Support Needed ({concept_name})"
        elif has_misc_flag and q_loss_ratio >= 0.25:
            is_justified = True
            priority_str = "Medium"
            priority_explanation = f"Moderate conceptual misunderstanding on Question {q_num}: awarded {q_awarded}/{q_max} marks."
            category_str = "severe_misconception"
            status_label = f"Concept Review ({concept_name})"

        if not is_justified:
            continue

        q_text = _safe_str(q.get("question_text"), f"Question {q_num}")
        std_ans = _safe_str(q.get("student_answer") or q.get("answer_summary"), "Answer recorded on script.")
        evidence_text = _safe_str(
            q.get("evidence_reference")
            or f"Student answered: '{std_ans}'. Awarded {q_awarded}/{q_max} marks. Identified gap: {actual_misc}."
        )
        correct_model = _safe_str(
            q.get("what_student_should_have_written")
            or q.get("correct_answer_or_expected_points")
            or feedback.get("expected_answer"),
            "Standard rubric model solution."
        )
        remediation = _safe_str(
            q.get("how_to_improve") or feedback.get("improvement"),
            f"Assign targeted tutorial on {concept_name} via Personal AI Trainer."
        )

        derived_items.append({
            "id": f"act_misc_{eval_id}_{q_num}",
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
            "academic_status": status_label,
            "topic": f"{subject} — {concept_name}",
            "skill_or_topic": concept_name,
            "question_num": f"Question {q_num}",
            "question_number": q_num,
            "total_marks": obtained_marks,
            "maximum_marks": total_marks,
            "marks_lost": q_lost,
            "loss_ratio": round(q_loss_ratio * 100, 1),
            "question_awarded_marks": q_awarded,
            "question_max_marks": q_max,
            "marks_awarded_vs_max": f"{q_awarded} / {q_max} marks",
            "affected_questions": [q_num],
            "marks_lost_per_question": {q_num: q_lost},
            "exact_question": q_text,
            "student_answer": std_ans,
            "misconception": actual_misc,
            "learning_gap": actual_misc,
            "evidence": evidence_text,
            "correct_understanding": correct_model,
            "issue": f"Evidence in Question {q_num} demonstrates conceptual misunderstanding of {concept_name}: {actual_misc}",
            "priority": priority_str,
            "severity": priority_str,
            "priority_reason": priority_explanation,
            "category": category_str,
            "action": remediation,
            "recommended_action": remediation,
            "source_link": f"/app/history?eval_id={eval_id}",
            "evaluation_link": f"/app/history?eval_id={eval_id}",
            "misconception_link": f"/app/misconceptions?class_id={class_id}&concept={concept_name}" if class_id else "/app/misconceptions",
            "status": "New",
            "is_unreadable": is_unreadable,
            "created_at": now_str,
            "updated_at": now_str,
            "audit_trail": [{"action": "Derived from question-level misconception evidence", "timestamp": now_str}],
        })

    # ══════════════════════════════════════════════════════════════════════════
    # ITEM TYPE 4: Incomplete / Unanswered Submissions (>= 2 questions)
    # ══════════════════════════════════════════════════════════════════════════
    incomplete_qs = [
        q for q in questions
        if isinstance(q, dict) and (
            str(q.get("answer_classification") or "").lower() in {"incomplete_answer", "unanswered_question"}
            or not q.get("attempted", True)
        )
    ]
    if len(incomplete_qs) >= 2:
        inc_q_nums = [str(q.get("question_number") or i + 1) for i, q in enumerate(incomplete_qs)]
        inc_lost = sum(max(0.0, _num(q.get("maximum_marks") or q.get("max_marks"), 0.0) - _num(q.get("awarded_marks"), 0.0)) for q in incomplete_qs)
        inc_pri = "High" if inc_lost > 15 else "Medium"
        inc_reason = f"Exam pacing and completeness: left {len(incomplete_qs)} questions incomplete, losing {round(inc_lost, 1)} marks."

        derived_items.append({
            "id": f"act_inc_{eval_id}",
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
            "academic_status": "Pacing & Completion Support",
            "topic": f"{subject} — Multi-Question Incompleteness",
            "skill_or_topic": "Exam Pacing & Time Management",
            "question_num": ", ".join(inc_q_nums[:4]),
            "question_number": ", ".join(inc_q_nums[:4]),
            "total_marks": obtained_marks,
            "maximum_marks": total_marks,
            "marks_lost": round(inc_lost, 2),
            "question_awarded_marks": obtained_marks,
            "question_max_marks": total_marks,
            "marks_awarded_vs_max": f"{obtained_marks} / {total_marks} marks",
            "affected_questions": inc_q_nums,
            "marks_lost_per_question": {
                str(q.get("question_number") or i + 1): round(max(0.0, _num(q.get("maximum_marks") or q.get("max_marks"), 0.0) - _num(q.get("awarded_marks"), 0.0)), 2)
                for i, q in enumerate(incomplete_qs)
            },
            "exact_question": str(incomplete_qs[0].get("question_text") or "Multiple questions left incomplete"),
            "student_answer": str(incomplete_qs[0].get("student_answer") or "Left incomplete or unattempted in script"),
            "misconception": "Time-management gap and incomplete multi-part structural answering.",
            "learning_gap": "Time-management gap and incomplete multi-part structural answering.",
            "evidence": f"Left {len(incomplete_qs)} questions incomplete or unanswered.",
            "correct_understanding": "Complete, structured solutions for all required questions.",
            "issue": f"Student produced incomplete or unattempted answers in {len(incomplete_qs)} questions, losing {round(inc_lost, 1)} marks.",
            "priority": inc_pri,
            "severity": inc_pri,
            "priority_reason": inc_reason,
            "category": "incomplete_answers",
            "action": "Guide student on exam time allocation, pacing, and structuring multi-part solutions.",
            "recommended_action": "Guide student on exam time allocation, pacing, and structuring multi-part solutions.",
            "source_link": f"/app/history?eval_id={eval_id}",
            "evaluation_link": f"/app/history?eval_id={eval_id}",
            "status": "New",
            "is_unreadable": is_unreadable,
            "created_at": now_str,
            "updated_at": now_str,
            "audit_trail": [{"action": "Derived from multiple incomplete submissions", "timestamp": now_str}],
        })

    return derived_items
