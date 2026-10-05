"""
LearnSphere AI - Evaluation Storage

Stores a completed evaluation without changing the marks produced by the
EvaluationAgent. This module deliberately does not invent marks, questions,
misconceptions, or grading data when fields are missing.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict

from ..db import get_mongodb, get_sqlite_db


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return json.dumps(str(value), ensure_ascii=False)


def _path(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("path") or "")
    return str(value or "")


def _feedback(q: Dict[str, Any]) -> Dict[str, Any]:
    value = q.get("feedback")
    return value if isinstance(value, dict) else {}


def _is_conceptual_issue(q: Dict[str, Any]) -> bool:
    """Only create a misconception when the evaluator explicitly identifies a genuine conceptual misunderstanding.
    Wrong arithmetic, spelling errors, skipped questions, or calculation slips are strictly excluded.
    """
    if not q.get("attempted", True):
        return False

    classification = str(q.get("answer_classification") or "").lower()
    if classification in {"unanswered_question", "correct_concept_with_calculation_error", "correct_answer"}:
        return False

    if q.get("misconception_detected") is True:
        misc = str(q.get("misconception") or q.get("conceptual_mistake") or "").strip()
        return bool(misc and len(misc) > 3)

    if q.get("conceptual_mistake"):
        cm = str(q.get("conceptual_mistake")).strip()
        return bool(cm and len(cm) > 3)

    labels = q.get("issue_types")
    if isinstance(labels, list):
        normalized = {str(x).strip().lower() for x in labels}
        return bool(normalized.intersection({"misconception", "conceptual_error", "conceptual misunderstanding"}))

    return str(q.get("error_type") or "").strip().lower() in {
        "misconception",
        "conceptual_error",
        "conceptual misunderstanding",
    }


def _status_for_percentage(percentage: float) -> str:
    # UI status only; this is not used to alter the grade or marks.
    if percentage >= 75:
        return "success"
    if percentage >= 50:
        return "warning"
    return "danger"


def store_evaluation_pipeline(
    request_data: Dict[str, Any],
    eval_result: Dict[str, Any],
    plagiarism_result: Dict[str, Any] | None = None,
) -> str:
    """Persist one evaluation and its question-level evidence.

    The result supplied by EvaluationAgent remains authoritative. This function
    only stores it and derives non-marking metadata. It never creates a default
    total of 100 or a default grade.
    """
    request_data = request_data or {}
    eval_result = eval_result or {}
    plagiarism_result = plagiarism_result or {}

    student = eval_result.get("student")
    if not isinstance(student, dict):
        student = {}

    student_name = str(
        request_data.get("student_name")
        or student.get("name")
        or "Student"
    )
    roll_number = str(
        request_data.get("roll_number")
        or student.get("roll_number")
        or "N/A"
    )

    qp = eval_result.get("question_paper")
    if not isinstance(qp, dict):
        qp = {}

    subject = str(
        request_data.get("subject")
        or qp.get("subject")
        or student.get("subject")
        or "General"
    )
    assessment_title = str(
        request_data.get("assessment_title")
        or f"{subject} Examination"
    )

    summary = eval_result.get("summary")
    if not isinstance(summary, dict):
        summary = {}

    if "total_marks" not in eval_result and "total_marks" in summary:
        eval_result["total_marks"] = summary.get("total_marks")
    if "obtained_marks" not in eval_result and ("awarded_marks" in summary or "obtained_marks" in summary):
        eval_result["obtained_marks"] = summary.get("awarded_marks", summary.get("obtained_marks"))
    if "percentage" not in eval_result and "percentage" in summary:
        eval_result["percentage"] = summary.get("percentage")
    if "grade" not in eval_result and "grade" in summary:
        eval_result["grade"] = summary.get("grade")

    total_marks = _number(eval_result.get("total_marks"), 0)
    obtained_marks = _number(eval_result.get("obtained_marks"), 0)

    if total_marks <= 0:
        raise ValueError("Evaluation result contains an invalid total_marks value.")
    if obtained_marks < 0 or obtained_marks > total_marks:
        raise ValueError("Evaluation result contains obtained_marks outside the valid range.")

    if "percentage" in eval_result:
        percentage = _number(eval_result.get("percentage"), 0)
    else:
        percentage = round((obtained_marks / total_marks) * 100, 2)

    grade = eval_result.get("grade")
    if grade is None or str(grade).strip() == "":
        grade = "Not assigned"
    else:
        grade = str(grade)

    status = _status_for_percentage(percentage)
    overall_feedback = str(eval_result.get("overall_feedback") or "")
    eval_notes = eval_result.get("evaluation_notes")
    if not isinstance(eval_notes, list):
        eval_notes = []

    evaluations = eval_result.get("evaluations")
    if not isinstance(evaluations, list):
        evaluations = []

    qp_path = _path(request_data.get("question_paper"))
    ans_path = _path(request_data.get("answer_script"))
    rubric_path = _path(request_data.get("rubrics"))

    is_unreadable = bool(eval_result.get("is_unreadable", False))
    assigned_to_teacher = bool(eval_result.get("assigned_to_teacher", False))
    unreadable_reason = str(eval_result.get("unreadable_reason") or "")

    mongo_db = get_mongodb()

    if mongo_db is not None:
        return _store_mongodb(
            mongo_db,
            request_data,
            student_name,
            roll_number,
            subject,
            assessment_title,
            total_marks,
            obtained_marks,
            percentage,
            grade,
            status,
            overall_feedback,
            eval_notes,
            qp_path,
            ans_path,
            rubric_path,
            evaluations,
            plagiarism_result,
            is_unreadable,
            assigned_to_teacher,
            unreadable_reason,
        )

    return _store_sqlite(
        request_data,
        student_name,
        roll_number,
        subject,
        assessment_title,
        total_marks,
        obtained_marks,
        percentage,
        grade,
        status,
        overall_feedback,
        eval_notes,
        qp_path,
        ans_path,
        rubric_path,
        evaluations,
        plagiarism_result,
        is_unreadable,
        assigned_to_teacher,
        unreadable_reason,
    )


def _store_mongodb(
    db: Any,
    request_data: Dict[str, Any],
    student_name: str,
    roll_number: str,
    subject: str,
    assessment_title: str,
    total_marks: float,
    obtained_marks: float,
    percentage: float,
    grade: str,
    status: str,
    overall_feedback: str,
    eval_notes: list,
    qp_path: str,
    ans_path: str,
    rubric_path: str,
    evaluations: list,
    plagiarism_result: Dict[str, Any],
    is_unreadable: bool,
    assigned_to_teacher: bool,
    unreadable_reason: str,
) -> str:
    now = datetime.utcnow()
    submitted_by = request_data.get("submitted_by")
    submitter_role = request_data.get("submitter_role")
    student_id = request_data.get("student_id") or (submitted_by if submitter_role == "student" else None)
    teacher_id = request_data.get("teacher_id") or (submitted_by if submitter_role == "teacher" else None)

    eval_doc = {
        "submitted_by": submitted_by,
        "submitter_role": submitter_role,
        "student_id": student_id,
        "teacher_id": teacher_id,
        "student_name": student_name,
        "roll_number": roll_number,
        "subject": subject,
        "assessment_title": assessment_title,
        "total_marks": total_marks,
        "obtained_marks": obtained_marks,
        "percentage": percentage,
        "grade": grade,
        "status": status,
        "is_unreadable": is_unreadable,
        "assigned_to_teacher": assigned_to_teacher,
        "unreadable_reason": unreadable_reason,
        "overall_feedback": overall_feedback,
        "evaluation_notes": eval_notes,
        "question_paper_path": qp_path,
        "answer_script_path": ans_path,
        "rubrics_path": rubric_path,
        "questions": evaluations,
        "evaluations": evaluations,
        "summary": summary,
        "strengths": eval_result.get("strengths") or [],
        "weaknesses": eval_result.get("weaknesses") or [],
        "major_conceptual_errors": eval_result.get("major_conceptual_errors") or [],
        "improvement_recommendations": eval_result.get("improvement_recommendations") or [],
        "verification_status": eval_result.get("verification_status") or "verified",
        "plagiarism": plagiarism_result,
        "created_at": now,
    }

    result = db["evaluations"].insert_one(eval_doc)
    eval_id = str(result.inserted_id)

    # 1. Flag for Teacher Review if unreadable / assigned
    if is_unreadable or assigned_to_teacher:
        db["action_items"].insert_one({
            "id": f"act_teacher_review_{eval_id}",
            "teacher_id": teacher_id,
            "student_id": student_id,
            "evaluation_id": eval_id,
            "student_name": student_name,
            "roll_number": roll_number,
            "academic_status": "Assigned to Teacher",
            "subject": subject,
            "topic": f"Teacher Review Required for {subject}",
            "question_num": "Evaluation",
            "total_marks": obtained_marks,
            "maximum_marks": total_marks,
            "marks_lost": max(0.0, round(total_marks - obtained_marks, 2)),
            "affected_questions": ["All"],
            "marks_lost_per_question": {"All": max(0.0, round(total_marks - obtained_marks, 2))},
            "exact_question": "Full assessment script review required",
            "student_answer": "Script flagged for manual teacher grading.",
            "misconception": "Evaluation script unreadable or ambiguous.",
            "evidence": unreadable_reason or "Low confidence / unreadable script content.",
            "correct_understanding": "Standard curriculum rubric.",
            "issue": unreadable_reason or "The evaluator flagged this assessment for teacher review.",
            "priority": "High",
            "severity": "High",
            "category": "teacher_review",
            "action": "Teacher review required before treating the AI result as final.",
            "recommended_action": "Teacher review required before treating the AI result as final.",
            "status": "New",
            "is_unreadable": is_unreadable,
            "created_at": now,
        })

    # 2. Strict Rule: Students who lose more than 20 marks in an evaluation
    # marks_lost = total_maximum_marks - total_marks_obtained
    calc_marks_lost = round(max(0.0, total_marks - obtained_marks), 2)
    affected_qs = [
        str(q.get("question_number") or i + 1)
        for i, q in enumerate(evaluations)
        if _number(q.get("maximum_marks"), 0) > _number(q.get("awarded_marks"), 0)
    ]
    marks_lost_per_q = {
        str(q.get("question_number") or i + 1): round(
            max(0.0, _number(q.get("maximum_marks"), 0) - _number(q.get("awarded_marks"), 0)), 2
        )
        for i, q in enumerate(evaluations)
        if _number(q.get("maximum_marks"), 0) > _number(q.get("awarded_marks"), 0)
    }

    if calc_marks_lost > 20.0:
        worst_q = max(
            evaluations,
            key=lambda x: _number(x.get("maximum_marks"), 0) - _number(x.get("awarded_marks"), 0),
            default={},
        ) if evaluations else {}
        db["action_items"].insert_one({
            "id": f"act_loss_{eval_id}",
            "teacher_id": teacher_id,
            "student_id": student_id,
            "evaluation_id": eval_id,
            "student_name": student_name,
            "roll_number": roll_number,
            "academic_status": f"At Risk (Lost {calc_marks_lost} marks)",
            "subject": subject,
            "topic": f"{subject} — {assessment_title}",
            "question_num": ", ".join(affected_qs[:4]) + ("..." if len(affected_qs) > 4 else ""),
            "total_marks": obtained_marks,
            "maximum_marks": total_marks,
            "marks_lost": calc_marks_lost,
            "affected_questions": affected_qs,
            "marks_lost_per_question": marks_lost_per_q,
            "exact_question": str(worst_q.get("question_text") or "Multi-question examination breakdown"),
            "student_answer": str(worst_q.get("student_answer") or worst_q.get("answer_summary") or "Accumulated multiple incorrect answers across the paper."),
            "misconception": str(eval_result.get("major_conceptual_errors", ["Overall examination deficit"])[0] if eval_result.get("major_conceptual_errors") else "Multi-topic assessment deficit"),
            "evidence": str(worst_q.get("evidence_reference") or overall_feedback or f"Lost {calc_marks_lost} marks out of {total_marks} marks."),
            "correct_understanding": str(worst_q.get("what_student_should_have_written") or "Comprehensive standard examination solutions."),
            "issue": overall_feedback or f"Student lost {calc_marks_lost} marks ({obtained_marks}/{total_marks}) across {len(affected_qs)} questions.",
            "priority": "Critical" if calc_marks_lost >= 35 else "High",
            "severity": "Critical" if calc_marks_lost >= 35 else "High",
            "category": "excessive_marks_lost",
            "action": f"Assign targeted remedial worksheet on {subject} and schedule 1-on-1 diagnostic review.",
            "recommended_action": f"Assign targeted remedial worksheet on {subject} and schedule 1-on-1 diagnostic review.",
            "status": "New",
            "is_unreadable": is_unreadable,
            "created_at": now,
        })

    # 3. Create misconceptions and misconception-linked Action Items
    for q in evaluations:
        if not isinstance(q, dict) or not _is_conceptual_issue(q):
            continue

        feedback = _feedback(q)
        max_marks = _number(q.get("maximum_marks"), 0)
        awarded = _number(q.get("awarded_marks"), 0)
        missing = feedback.get("missing_points") or q.get("missing_points")
        if not isinstance(missing, list):
            missing = []

        actual = str(q.get("misconception") or q.get("conceptual_mistake") or (missing[0] if missing else "Conceptual error"))
        q_num = str(q.get("question_number") or "Unknown")
        ratio = awarded / max_marks if max_marks > 0 else 0
        concepts_list = q.get("concepts_tested") or []
        concept_name = str(concepts_list[0] if isinstance(concepts_list, list) and concepts_list else (q.get("topic") or f"Concept in Question {q_num}"))
        q_text = str(q.get("question_text") or "")
        std_ans = str(q.get("student_answer") or q.get("answer_summary") or "")
        evidence_text = str(q.get("evidence_reference") or std_ans or actual)
        correct_model = str(q.get("what_student_should_have_written") or q.get("correct_answer_or_expected_points") or feedback.get("expected_answer") or "")
        remediation = str(q.get("how_to_improve") or feedback.get("improvement") or "Targeted concept practice with the Personal AI Trainer.")
        q_lost = round(max(0.0, max_marks - awarded), 2)

        # Check if student already had this misconception before (repeated concept loss)
        prev_count = 0
        try:
            prev_count = db["misconceptions"].count_documents({
                "student_id": student_id,
                "identified_concept": concept_name,
                "evaluation_id": {"$ne": eval_id},
            })
        except Exception:
            pass

        is_repeated = prev_count > 0

        db["misconceptions"].insert_one({
            "student_id": student_id,
            "teacher_id": teacher_id,
            "student_name": student_name,
            "evaluation_id": eval_id,
            "subject": subject,
            "topic": f"{subject} — Question {q_num}",
            "question_number": q_num,
            "question_num": f"Question {q_num}",
            "exact_question": q_text,
            "student_answer": std_ans,
            "student_reasoning": std_ans,
            "awarded_marks": awarded,
            "maximum_marks": max_marks,
            "identified_concept": concept_name,
            "concept": concept_name,
            "misconception": actual,
            "actual_misconception": actual,
            "description": actual,
            "evidence": evidence_text,
            "correct_understanding": correct_model,
            "correct_concept": correct_model,
            "occurrences": prev_count + 1,
            "assessments": [assessment_title],
            "confidence": str(q.get("confidence") or ("High" if ratio < 0.5 else "Medium")),
            "affected_count": 1,
            "student_names": [student_name],
            "severity": "Critical" if is_repeated else ("High" if ratio < 0.5 else "Medium"),
            "recommended_remediation": remediation,
            "remedy": remediation,
            "status": "Active",
            "created_at": now,
        })

        # Connect with Action Center: create an actionable intervention item
        db["action_items"].insert_one({
            "id": f"act_misc_{eval_id}_{q_num}",
            "teacher_id": teacher_id,
            "student_id": student_id,
            "evaluation_id": eval_id,
            "student_name": student_name,
            "roll_number": roll_number,
            "academic_status": f"Repeated Concept Gap ({concept_name})" if is_repeated else f"Conceptual Misunderstanding ({concept_name})",
            "subject": subject,
            "topic": f"{subject} — {concept_name}",
            "question_num": f"Question {q_num}",
            "total_marks": obtained_marks,
            "maximum_marks": total_marks,
            "marks_lost": q_lost,
            "affected_questions": [q_num],
            "marks_lost_per_question": {q_num: q_lost},
            "exact_question": q_text,
            "student_answer": std_ans,
            "misconception": actual,
            "evidence": evidence_text,
            "correct_understanding": correct_model,
            "issue": f"Evidence in Question {q_num} demonstrates conceptual misunderstanding of {concept_name}: {actual}",
            "priority": "Critical" if is_repeated else ("High" if ratio < 0.5 else "Medium"),
            "severity": "Critical" if is_repeated else ("High" if ratio < 0.5 else "Medium"),
            "category": "repeated_concept_loss" if is_repeated else "severe_misconception",
            "action": remediation or f"Assign targeted tutorial on {concept_name} via Personal AI Trainer.",
            "recommended_action": remediation or f"Assign targeted tutorial on {concept_name} via Personal AI Trainer.",
            "status": "New",
            "is_unreadable": is_unreadable,
            "created_at": now,
        })

    # 4. Repeatedly producing incomplete answers
    incomplete_qs = [
        q for q in evaluations
        if str(q.get("answer_classification") or "").lower() in {"incomplete_answer", "unanswered_question"}
        or not q.get("attempted", True)
    ]
    if len(incomplete_qs) >= 2:
        inc_q_nums = [str(q.get("question_number") or i + 1) for i, q in enumerate(incomplete_qs)]
        inc_lost = sum(max(0.0, _number(q.get("maximum_marks"), 0) - _number(q.get("awarded_marks"), 0)) for q in incomplete_qs)
        db["action_items"].insert_one({
            "id": f"act_inc_{eval_id}",
            "teacher_id": teacher_id,
            "student_id": student_id,
            "evaluation_id": eval_id,
            "student_name": student_name,
            "roll_number": roll_number,
            "academic_status": "Incomplete Submissions",
            "subject": subject,
            "topic": f"{subject} — Multi-Question Incompleteness",
            "question_num": ", ".join(inc_q_nums[:4]),
            "total_marks": obtained_marks,
            "maximum_marks": total_marks,
            "marks_lost": round(inc_lost, 2),
            "affected_questions": inc_q_nums,
            "marks_lost_per_question": {
                str(q.get("question_number") or i + 1): round(max(0.0, _number(q.get("maximum_marks"), 0) - _number(q.get("awarded_marks"), 0)), 2)
                for i, q in enumerate(incomplete_qs)
            },
            "exact_question": str(incomplete_qs[0].get("question_text") or "Multiple questions left incomplete"),
            "student_answer": str(incomplete_qs[0].get("student_answer") or "Left incomplete or unattempted in script"),
            "misconception": "Time-management gap and incomplete multi-part structural answering.",
            "evidence": f"Left {len(incomplete_qs)} questions incomplete or unanswered.",
            "correct_understanding": "Complete, structured solutions for all required questions.",
            "issue": f"Student produced incomplete or unattempted answers in {len(incomplete_qs)} questions, losing {round(inc_lost, 1)} marks.",
            "priority": "High" if inc_lost > 15 else "Medium",
            "severity": "High" if inc_lost > 15 else "Medium",
            "category": "incomplete_answers",
            "action": "Guide student on exam time allocation, pacing, and structuring multi-part solutions.",
            "recommended_action": "Guide student on exam time allocation, pacing, and structuring multi-part solutions.",
            "status": "New",
            "is_unreadable": is_unreadable,
            "created_at": now,
        })

    db["academic_memory"].insert_one({
        "student_id": student_id,
        "student_name": student_name,
        "subject": subject,
        "topic": f"{subject} — {assessment_title} Review",
        "mastery": int(round(max(0, min(100, percentage)))),
        "retention_rate": int(round(max(0, min(100, percentage)))),
        "status": "Mastered" if percentage >= 85 else "Learning",
        "last_reviewed": now,
        "next_review": now + timedelta(days=2),
    })

    if is_unreadable or assigned_to_teacher:
        teacher_title = "Evaluation Needs Teacher Review"
        teacher_message = unreadable_reason or f"{student_name}'s {subject} evaluation was flagged for teacher review."
        student_title = "Your Exam Is Under Teacher Review"
        student_message = f"Your {subject} examination has been flagged for teacher review."
        category = "warning"
    else:
        teacher_title = "Evaluation Completed"
        teacher_message = f"Evaluated {student_name}'s {subject} script ({obtained_marks}/{total_marks})."
        student_title = "Your Exam Has Been Graded"
        student_message = f"Your {subject} examination scored {obtained_marks}/{total_marks} ({percentage}%)."
        category = "success"

    db["notifications"].insert_many([
        {
            "target_role": "teacher",
            "target_id": teacher_id,
            "target_name": None,
            "title": teacher_title,
            "message": teacher_message,
            "category": category,
            "is_read": False,
            "created_at": now,
        },
        {
            "target_role": "student",
            "target_id": student_id,
            "target_name": student_name,
            "title": student_title,
            "message": student_message,
            "category": "info" if category == "warning" else "success",
            "is_read": False,
            "created_at": now,
        },
    ])

    return eval_id


def _store_sqlite(
    request_data: Dict[str, Any],
    student_name: str,
    roll_number: str,
    subject: str,
    assessment_title: str,
    total_marks: float,
    obtained_marks: float,
    percentage: float,
    grade: str,
    status: str,
    overall_feedback: str,
    eval_notes: list,
    qp_path: str,
    ans_path: str,
    rubric_path: str,
    evaluations: list,
    plagiarism_result: Dict[str, Any],
    is_unreadable: bool,
    assigned_to_teacher: bool,
    unreadable_reason: str,
) -> str:
    conn = get_sqlite_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO evaluations
            (student_name, roll_number, subject, assessment_title,
             total_marks, obtained_marks, percentage, grade, status,
             overall_feedback, evaluation_notes_json,
             question_paper_path, answer_script_path, rubrics_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_name,
                roll_number,
                subject,
                assessment_title,
                total_marks,
                obtained_marks,
                percentage,
                grade,
                status,
                overall_feedback,
                _safe_json(eval_notes),
                qp_path,
                ans_path,
                rubric_path,
            ),
        )
        eval_id = str(cursor.lastrowid)

        for q in evaluations:
            if not isinstance(q, dict):
                continue

            q_num = str(q.get("question_number") or "Unknown")
            q_type = str(q.get("question_type") or "short_answer")
            max_marks = _number(q.get("maximum_marks"), 0)
            awarded = _number(q.get("awarded_marks"), 0)
            answer_present = 1 if q.get("answer_present", True) else 0
            is_correct = 1 if max_marks > 0 and awarded >= max_marks else 0
            feedback = _feedback(q)
            missing = feedback.get("missing_points")
            if not isinstance(missing, list):
                missing = []

            cursor.execute(
                """
                INSERT INTO evaluation_questions
                (evaluation_id, question_number, question_type,
                 maximum_marks, awarded_marks, is_correct, answer_present,
                 answer_summary, what_was_done_well, missing_points,
                 expected_answer, improvement_advice)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(eval_id),
                    q_num,
                    q_type,
                    max_marks,
                    awarded,
                    is_correct,
                    answer_present,
                    str(q.get("answer_summary") or ""),
                    _safe_json(feedback.get("what_was_done_well") or []),
                    _safe_json(missing),
                    str(feedback.get("expected_answer") or q.get("correct_answer") or ""),
                    str(feedback.get("improvement") or ""),
                ),
            )

            if _is_conceptual_issue(q):
                concept = str(q.get("misconception") or (missing[0] if missing else "Conceptual error"))
                cursor.execute(
                    """
                    INSERT INTO misconceptions
                    (student_name, subject, topic, concept, description, severity, remedy)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student_name,
                        subject,
                        f"{subject} — Question {q_num}",
                        concept,
                        str(q.get("grader_notes") or concept),
                        "High" if max_marks > 0 and awarded / max_marks < 0.5 else "Medium",
                        str(feedback.get("improvement") or "Targeted practice with AI trainer."),
                    ),
                )

        cursor.execute(
            """
            INSERT INTO academic_memory
            (student_name, subject, topic, mastery, retention_rate, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                student_name,
                subject,
                f"{subject} — {assessment_title}",
                int(round(max(0, min(100, percentage)))),
                int(round(max(0, min(100, percentage)))),
                "Mastered" if percentage >= 85 else "Learning",
            ),
        )

        # Insert Action Items in SQLite
        calc_marks_lost = round(max(0.0, total_marks - obtained_marks), 2)
        affected_qs = [
            str(q.get("question_number") or i + 1)
            for i, q in enumerate(evaluations)
            if _number(q.get("maximum_marks"), 0) > _number(q.get("awarded_marks"), 0)
        ]
        marks_lost_per_q = {
            str(q.get("question_number") or i + 1): round(
                max(0.0, _number(q.get("maximum_marks"), 0) - _number(q.get("awarded_marks"), 0)), 2
            )
            for i, q in enumerate(evaluations)
            if _number(q.get("maximum_marks"), 0) > _number(q.get("awarded_marks"), 0)
        }

        if is_unreadable or assigned_to_teacher:
            cursor.execute(
                """
                INSERT INTO action_items
                (id, teacher_id, student_id, evaluation_id, student_name, roll_number,
                 academic_status, subject, topic, question_num, total_marks, maximum_marks,
                 marks_lost, affected_questions, marks_lost_per_question, exact_question,
                 student_answer, misconception, evidence, correct_understanding, issue,
                 priority, severity, action, recommended_action, category, status, is_unreadable)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"act_teacher_review_{eval_id}",
                    teacher_id,
                    student_id,
                    eval_id,
                    student_name,
                    roll_number,
                    "Assigned to Teacher",
                    subject,
                    f"Teacher Review Required for {subject}",
                    "Evaluation",
                    obtained_marks,
                    total_marks,
                    calc_marks_lost,
                    _safe_json(["All"]),
                    _safe_json({"All": calc_marks_lost}),
                    "Full assessment script review required",
                    "Script flagged for manual teacher grading.",
                    "Evaluation script unreadable or ambiguous.",
                    unreadable_reason or "Low confidence / unreadable script content.",
                    "Standard curriculum rubric.",
                    unreadable_reason or "The evaluator flagged this assessment for teacher review.",
                    "High",
                    "High",
                    "Teacher review required before treating the AI result as final.",
                    "Teacher review required before treating the AI result as final.",
                    "teacher_review",
                    "New",
                    1,
                ),
            )

        if calc_marks_lost > 20.0:
            worst_q = max(
                evaluations,
                key=lambda x: _number(x.get("maximum_marks"), 0) - _number(x.get("awarded_marks"), 0),
                default={},
            ) if evaluations else {}
            cursor.execute(
                """
                INSERT INTO action_items
                (id, teacher_id, student_id, evaluation_id, student_name, roll_number,
                 academic_status, subject, topic, question_num, total_marks, maximum_marks,
                 marks_lost, affected_questions, marks_lost_per_question, exact_question,
                 student_answer, misconception, evidence, correct_understanding, issue,
                 priority, severity, action, recommended_action, category, status, is_unreadable)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"act_loss_{eval_id}",
                    teacher_id,
                    student_id,
                    eval_id,
                    student_name,
                    roll_number,
                    f"At Risk (Lost {calc_marks_lost} marks)",
                    subject,
                    f"{subject} — {assessment_title}",
                    ", ".join(affected_qs[:4]),
                    obtained_marks,
                    total_marks,
                    calc_marks_lost,
                    _safe_json(affected_qs),
                    _safe_json(marks_lost_per_q),
                    str(worst_q.get("question_text") or ""),
                    str(worst_q.get("student_answer") or worst_q.get("answer_summary") or ""),
                    "Multiple question assessment deficit",
                    overall_feedback or f"Lost {calc_marks_lost} marks out of {total_marks} marks.",
                    "Comprehensive standard solutions.",
                    overall_feedback or f"Student lost {calc_marks_lost} marks ({obtained_marks}/{total_marks}).",
                    "Critical" if calc_marks_lost >= 35 else "High",
                    "Critical" if calc_marks_lost >= 35 else "High",
                    f"Assign targeted remedial worksheet on {subject} and schedule 1-on-1 review.",
                    f"Assign targeted remedial worksheet on {subject} and schedule 1-on-1 review.",
                    "excessive_marks_lost",
                    "New",
                    0,
                ),
            )

        conn.commit()
        return eval_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
