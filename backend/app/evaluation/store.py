"""
LearnSphere AI - Evaluation Storage Pipeline
Persists graded evaluations to MongoDB Atlas (with SQLite fallback), extracts misconceptions,
schedules spaced-repetition reviews, and delivers notifications.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any
from ..db import get_mongodb, get_sqlite_db

def store_evaluation_pipeline(
    request_data: Dict[str, Any],
    eval_result: Dict[str, Any],
    plagiarism_result: Dict[str, Any]
) -> str:
    """
    Sequentially stores evaluation details into MongoDB or SQLite.
    Returns the string ID of the new evaluation.
    """
    student_name = request_data.get("student_name") or eval_result.get("student", {}).get("name") or "Student"
    roll_number = request_data.get("roll_number") or eval_result.get("student", {}).get("roll_number") or "N/A"
    subject = request_data.get("subject") or eval_result.get("student", {}).get("subject") or "General"
    assessment_title = request_data.get("assessment_title") or f"{subject} Examination"
    
    total_marks = float(eval_result.get("total_marks", 100))
    obtained_marks = float(eval_result.get("obtained_marks", 0))
    percentage = float(eval_result.get("percentage", round((obtained_marks / total_marks) * 100, 2) if total_marks else 0))
    grade = eval_result.get("grade", "B")
    status = "success" if percentage >= 75 else "warning" if percentage >= 50 else "danger"
    overall_feedback = eval_result.get("overall_feedback", "Completed evaluation.")
    eval_notes = eval_result.get("evaluation_notes", [])

    qp_path = request_data.get("question_paper", {}).get("path") if isinstance(request_data.get("question_paper"), dict) else str(request_data.get("question_paper") or "")
    ans_path = request_data.get("answer_script", {}).get("path") if isinstance(request_data.get("answer_script"), dict) else str(request_data.get("answer_script") or "")
    rubric_path = request_data.get("rubrics", {}).get("path") if isinstance(request_data.get("rubrics"), dict) else str(request_data.get("rubrics") or "")

    is_unreadable = bool(eval_result.get("is_unreadable", False))
    assigned_to_teacher = bool(eval_result.get("assigned_to_teacher", False))
    unreadable_reason = str(eval_result.get("unreadable_reason", ""))

    mongo_db = get_mongodb()

    if mongo_db is not None:
        # --- 1. MONGODB ATLAS STORAGE ---
        eval_doc = {
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
            "questions": eval_result.get("evaluations", []),
            "plagiarism": plagiarism_result,
            "created_at": datetime.utcnow()
        }

        res = mongo_db["evaluations"].insert_one(eval_doc)
        eval_id = str(res.inserted_id)

        # 2. Unreadable Script -> Assign to Teacher Action Item
        if is_unreadable or assigned_to_teacher:
            mongo_db["action_items"].insert_one({
                "id": f"act_unreadable_{eval_id}",
                "student_name": student_name,
                "roll_number": roll_number,
                "academic_status": "Assigned to Teacher (Unreadable Script)",
                "subject": subject,
                "topic": f"Manual Grading Required for {subject}",
                "question_num": "All Questions",
                "marks_lost": int(total_marks - obtained_marks),
                "issue": unreadable_reason or "Handwriting was too illegible for AI evaluation agent (>90% safety guard). Assigned to teacher for manual mark allotment.",
                "misconception": "Illegible / Bad Handwriting",
                "priority": "High",
                "action": "Teacher manual mark allotment & review required.",
                "status": "New",
                "is_unreadable": True,
                "eval_id": eval_id,
                "created_at": datetime.utcnow().strftime("%Y-%m-%d")
            })

        # 3. Misconceptions extraction (Strict Rule: Mistake != Misconception)
        # Ignores arithmetic, calculation, spelling, or simple slips.
        for q in eval_result.get("evaluations", []):
            max_m = float(q.get("maximum_marks", 0))
            awd_m = float(q.get("awarded_marks", 0))
            feedback = q.get("feedback", {})
            missing = feedback.get("missing_points", [])
            grader_notes = str(feedback.get("improvement", "") or "") + " " + str(q.get("grader_notes", "") or "")
            
            # Check if this error represents a conceptual misconception vs simple slip
            notes_lower = grader_notes.lower()
            is_arithmetic_slip = any(kw in notes_lower for kw in ["arithmetic", "calculation", "calculation mistake", "addition error", "subtraction error", "spelling", "grammar", "misread question"])
            
            if awd_m < max_m and len(missing) > 0 and not is_arithmetic_slip:
                actual_misc = missing[0]
                student_answer_snippet = str(q.get("student_answer", "Incorrect step in response."))
                correct_concept_text = str(q.get("correct_answer", "Standard physical/mathematical law."))
                q_num = f"Question {q.get('question_number', '')}"
                
                # Formulate explicit evidence sentence
                evidence_text = f"{student_name}'s reasoning in {q_num} indicates a conceptual misunderstanding: {actual_misc}"
                
                mongo_db["misconceptions"].insert_one({
                    "student_name": student_name,
                    "subject": subject,
                    "topic": f"{subject} — {q_num}",
                    "concept": q.get("topic") or f"Concept in {q_num}",
                    "actual_misconception": actual_misc,
                    "description": actual_misc,
                    "question_num": q_num,
                    "student_reasoning": student_answer_snippet,
                    "correct_concept": correct_concept_text,
                    "evidence": evidence_text,
                    "occurrences": 1,
                    "assessments": [assessment_title],
                    "confidence": "High" if (awd_m / max_m if max_m else 0) < 0.5 else "Medium",
                    "affected_count": 1,
                    "student_names": [student_name],
                    "severity": "High" if (awd_m / max_m if max_m else 0) < 0.5 else "Medium",
                    "remedy": feedback.get("improvement", "Targeted concept practice with Personal AI Trainer."),
                    "status": "Active",
                    "created_at": datetime.utcnow()
                })

        # 4. Spaced Repetition Memory
        mongo_db["academic_memory"].insert_one({
            "student_name": student_name,
            "subject": subject,
            "topic": f"{subject} — {assessment_title} Review",
            "mastery": int(percentage),
            "retention_rate": int(min(100, percentage + 10)),
            "status": "Mastered" if percentage >= 85 else "Learning",
            "last_reviewed": datetime.utcnow(),
            "next_review": datetime.utcnow() + timedelta(days=2)
        })

        # 5. Notifications
        notif_msg = f"Handwriting unreadable for {student_name}'s {subject} paper. Assigned to you for manual grading." if (is_unreadable or assigned_to_teacher) else f"Evaluated {student_name}'s {subject} script ({obtained_marks}/{total_marks} marks, Grade {grade})."
        mongo_db["notifications"].insert_many([
            {
                "target_role": "teacher",
                "target_name": None,
                "title": "Unreadable Script Assigned" if (is_unreadable or assigned_to_teacher) else "Evaluation Completed",
                "message": notif_msg,
                "category": "warning" if (is_unreadable or assigned_to_teacher) else "success",
                "is_read": False,
                "created_at": datetime.utcnow()
            },
            {
                "target_role": "student",
                "target_name": student_name,
                "title": "Script Under Teacher Review" if (is_unreadable or assigned_to_teacher) else "Your Exam Has Been Graded",
                "message": f"Your {subject} examination is undergoing manual review by teacher." if (is_unreadable or assigned_to_teacher) else f"Your {subject} examination scored {obtained_marks}/{total_marks} ({percentage}%).",
                "category": "info" if (is_unreadable or assigned_to_teacher) else "success",
                "is_read": False,
                "created_at": datetime.utcnow()
            }
        ])

        return eval_id

    else:
        # --- 2. SQLITE FALLBACK STORAGE ---
        conn = get_sqlite_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO evaluations 
            (student_name, roll_number, subject, assessment_title, total_marks, obtained_marks, percentage, grade, status, overall_feedback, evaluation_notes_json, question_paper_path, answer_script_path, rubrics_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            student_name, roll_number, subject, assessment_title,
            total_marks, obtained_marks, percentage, grade, status,
            overall_feedback, json.dumps(eval_notes), qp_path, ans_path, rubric_path
        ))
        eval_id = str(cursor.lastrowid)

        for q in eval_result.get("evaluations", []):
            q_num = str(q.get("question_number", ""))
            q_type = str(q.get("question_type", "short_answer"))
            max_m = float(q.get("maximum_marks", 0))
            awd_m = float(q.get("awarded_marks", 0))
            is_corr = 1 if (awd_m >= max_m and max_m > 0) else 0
            ans_pres = 1 if q.get("answer_present", True) else 0
            summary = str(q.get("answer_summary", ""))
            fb = q.get("feedback", {})

            cursor.execute("""
                INSERT INTO evaluation_questions
                (evaluation_id, question_number, question_type, maximum_marks, awarded_marks, is_correct, answer_present, answer_summary, what_was_done_well, missing_points, expected_answer, improvement_advice)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(eval_id), q_num, q_type, max_m, awd_m, is_corr, ans_pres,
                summary, json.dumps(fb.get("what_was_done_well", [])), json.dumps(fb.get("missing_points", [])),
                str(fb.get("expected_answer", "")), str(fb.get("improvement", ""))
            ))

        conn.commit()
        conn.close()
        return eval_id
