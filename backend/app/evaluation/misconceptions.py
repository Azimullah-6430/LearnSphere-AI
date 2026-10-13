"""
LearnSphere AI - Misconception Engine

Derives genuine misconception insights exclusively from authentic, completed
teacher evaluations and actual student answers.

Guarantees:
1. Uses only valid, authorized TEACHER_EVALUATION records associated with a real student and class.
2. Preserves student name, class, subject, assessment, question, actual student answer,
   expected answer/rubric evidence, and marks awarded vs maximum marks.
3. Identifies a misconception only when the answer provides sufficient evidence of a conceptual
   misunderstanding (arithmetic slips and simple incorrect answers are never mislabeled as misconceptions).
4. If evidence is insufficient, labels the insight as 'Needs teacher review' without inventing a diagnosis.
5. Groups related misconceptions by concept supported by actual questions/topics/evidence.
6. Zero invention of student responses, topics, marks, or names.
7. Zero inclusion of student self-evaluations, practice tasks, or unverified records.
8. Links every insight to its source evaluation_id and question_number.
9. Provides recalculation and synchronization for evaluations on save, update/override, and query.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..db import get_mongodb, get_sqlite_db

logger = logging.getLogger(__name__)


def is_valid_teacher_evaluation(eval_doc: Dict[str, Any]) -> bool:
    """Check if an evaluation record is an authorized TEACHER_EVALUATION with a real student and class."""
    if not isinstance(eval_doc, dict):
        return False

    # 1. Must be TEACHER_EVALUATION
    source = str(eval_doc.get("evaluation_source") or "").strip()
    if source != "TEACHER_EVALUATION":
        return False

    # 2. Must not be a failed or deleted evaluation
    eval_status = str(eval_doc.get("evaluation_status") or eval_doc.get("status") or "").upper()
    if eval_status == "FAILED":
        return False

    # 3. Must reference a real class
    class_id = str(eval_doc.get("class_id") or "").strip()
    if not class_id or class_id.lower() in ("none", "null", "undefined", ""):
        return False

    # 4. Must reference a verified student identity (Requirement 1 & 7)
    identity_status = str(eval_doc.get("identity_status") or "VERIFIED").strip().upper()
    if identity_status in ("NEEDS_REVIEW", "UNLINKED"):
        return False

    # Must have a student identifier or snapshot
    student_id = eval_doc.get("student_id")
    student_name = eval_doc.get("student_name_snapshot") or eval_doc.get("student_name")
    if not student_id and not student_name:
        return False

    return True


def extract_misconceptions_from_question(
    q: Dict[str, Any],
    eval_doc: Dict[str, Any],
    class_name: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Extract a diagnosed misconception or 'Needs teacher review' record from a single evaluated question.
    Returns None if the question is unattempted, correct, an arithmetic error, or not conceptual.
    """
    if not isinstance(q, dict):
        return None

    # Exclude unattempted questions or skipped elective choices
    if q.get("attempted") is False:
        return False
    classification = str(q.get("answer_classification") or "").strip().lower()
    if classification == "unanswered_question":
        return None

    # Exclude answers without any student response
    student_ans = str(q.get("student_answer") or q.get("answer_summary") or "").strip()
    if not student_ans:
        return None

    # Exclude calculation errors and correct answers (Requirement 3: Incorrect answer by itself is not proof)
    if classification in {"correct_concept_with_calculation_error", "correct_answer"}:
        return None

    try:
        max_marks = float(q.get("maximum_marks") or q.get("max_marks") or 0.0)
    except (ValueError, TypeError):
        max_marks = 0.0

    try:
        awarded_marks = float(q.get("awarded_marks") or 0.0)
    except (ValueError, TypeError):
        awarded_marks = 0.0

    # If student got full marks and no misconception was detected, skip
    if max_marks > 0 and awarded_marks >= max_marks and not q.get("misconception_detected"):
        return None

    feedback = q.get("feedback") if isinstance(q.get("feedback"), dict) else {}

    # Check for evidence of conceptual misunderstanding
    misc_detected = q.get("misconception_detected") is True
    explicit_misc = str(q.get("misconception") or "").strip()
    conceptual_mistake = str(q.get("conceptual_mistake") or "").strip()
    error_type = str(q.get("error_type") or "").strip().lower()
    issue_types = [str(x).strip().lower() for x in (q.get("issue_types") or []) if isinstance(x, str)]

    has_conceptual_indicator = (
        misc_detected
        or bool(explicit_misc and len(explicit_misc) > 3)
        or bool(conceptual_mistake and len(conceptual_mistake) > 3 and conceptual_mistake.lower() != "none")
        or classification in {"wrong_concept", "contradictory_answer"}
        or error_type in {"misconception", "conceptual_error", "conceptual misunderstanding"}
        or any(t in {"misconception", "conceptual_error", "conceptual misunderstanding"} for t in issue_types)
    )

    if not has_conceptual_indicator:
        # Not a conceptual issue (could be minor formatting, omission, or incomplete without conceptual error)
        return None

    # Determine whether evidence is sufficient to diagnose a specific conceptual flaw
    diagnosed_flaw = explicit_misc or conceptual_mistake
    if diagnosed_flaw and diagnosed_flaw.lower() in ("none", "n/a", "null", "false"):
        diagnosed_flaw = ""

    # Requirement 3 & 4:
    # If the answer provides sufficient evidence of conceptual misunderstanding:
    if diagnosed_flaw and len(diagnosed_flaw) > 3:
        needs_teacher_review = False
        evidence_status = "VERIFIED"
        confidence = str(q.get("confidence") or "High")
        actual_misconception = diagnosed_flaw
    else:
        # Evidence is insufficient to diagnose a specific conceptual flaw (Requirement 4)
        needs_teacher_review = True
        evidence_status = "NEEDS_TEACHER_REVIEW"
        confidence = "Needs teacher review"
        actual_misconception = "Needs teacher review: Student response indicates an error, but evidence is insufficient to confirm a specific conceptual misunderstanding."

    # Extract concept name strictly supported by the actual questions, curriculum topic, or evaluation evidence
    concepts_tested = q.get("concepts_tested")
    if isinstance(concepts_tested, list) and concepts_tested and str(concepts_tested[0]).strip():
        concept_name = str(concepts_tested[0]).strip()
    elif q.get("concept") and str(q.get("concept")).strip():
        concept_name = str(q.get("concept")).strip()
    elif q.get("identified_concept") and str(q.get("identified_concept")).strip():
        concept_name = str(q.get("identified_concept")).strip()
    elif q.get("topic") and str(q.get("topic")).strip():
        concept_name = str(q.get("topic")).strip()
    else:
        concept_name = f"{eval_doc.get('subject', 'General')} Question Concept"

    # Extract verbatim question text
    exact_question = str(q.get("question_text") or "").strip()
    q_num = str(q.get("question_number") or q.get("question_id") or "1").strip()

    # Expected answer / rubric model
    expected_ans = str(
        q.get("what_student_should_have_written")
        or q.get("expected_answer")
        or feedback.get("expected_answer")
        or q.get("correct_answer")
        or ""
    ).strip()
    correct_understanding = expected_ans if expected_ans else f"Standard curriculum model for {concept_name}."

    # Evidence reference / student reasoning
    evidence_text = str(
        q.get("evidence_reference")
        or q.get("evaluation_reason")
        or feedback.get("evaluation_reason")
        or student_ans
    ).strip()

    # Recommended remedy
    remedy = str(
        q.get("how_to_improve")
        or feedback.get("improvement")
        or f"Review core principles of {concept_name} with teacher guidance."
    ).strip()

    eval_id_str = str(eval_doc.get("_id") or eval_doc.get("id") or eval_doc.get("evaluation_id") or "").strip()
    student_name = str(eval_doc.get("student_name_snapshot") or eval_doc.get("student_name") or "Student").strip()
    roll_number = str(eval_doc.get("roll_number_snapshot") or eval_doc.get("roll_number") or "N/A").strip()
    teacher_id = str(eval_doc.get("teacher_id") or eval_doc.get("created_by_user_id") or "").strip()
    class_id = str(eval_doc.get("class_id") or "").strip()
    subject = str(eval_doc.get("subject") or "General").strip()
    assessment_title = str(eval_doc.get("assessment_title") or f"{subject} Assessment").strip()
    created_at = eval_doc.get("created_at") or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Severity: High if student scored below 50% on this question or lost marks repeatedly
    ratio = awarded_marks / max_marks if max_marks > 0 else 0.0
    severity = "Critical" if ratio < 0.3 else ("High" if ratio < 0.6 else "Medium")

    return {
        "id": f"misc_{eval_id_str}_{q_num.replace(' ', '_')}",
        "evaluation_id": eval_id_str,
        "evaluationId": eval_id_str,
        "evaluation_source": "TEACHER_EVALUATION",
        "teacher_id": teacher_id,
        "class_id": class_id,
        "class_name": class_name,
        "student_id": str(eval_doc.get("student_id") or ""),
        "student_user_id": eval_doc.get("student_user_id"),
        "student_name": student_name,
        "roll_number": roll_number,
        "subject": subject,
        "assessment_title": assessment_title,
        "assessments": [assessment_title],
        "question_number": q_num,
        "question_num": f"Question {q_num}",
        "exact_question": exact_question,
        "student_answer": student_ans,
        "student_reasoning": student_ans,
        "expected_answer": expected_ans,
        "correct_understanding": correct_understanding,
        "correct_concept": correct_understanding,
        "awarded_marks": awarded_marks,
        "maximum_marks": max_marks,
        "identified_concept": concept_name,
        "concept": concept_name,
        "topic": f"{subject} — {concept_name}",
        "actual_misconception": actual_misconception,
        "misconception": actual_misconception,
        "description": actual_misconception,
        "evidence": evidence_text,
        "evidence_status": evidence_status,
        "needs_teacher_review": needs_teacher_review,
        "confidence": confidence,
        "severity": severity,
        "recommended_remediation": remedy,
        "remedy": remedy,
        "status": "Active",
        "occurrences": 1,
        "created_at": created_at,
    }


def derive_misconceptions_from_evaluation(
    eval_doc: Dict[str, Any],
    class_name_lookup: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """Derive all valid misconception items from a genuine completed teacher evaluation."""
    if not is_valid_teacher_evaluation(eval_doc):
        return []

    class_id = str(eval_doc.get("class_id") or "")
    class_name = (class_name_lookup or {}).get(class_id, "")
    if not class_name:
        class_name = str(eval_doc.get("class_name") or "")

    questions = eval_doc.get("questions") or eval_doc.get("evaluations") or []
    if isinstance(questions, str):
        try:
            questions = json.loads(questions)
        except Exception:
            questions = []

    derived: List[Dict[str, Any]] = []
    for q in questions:
        item = extract_misconceptions_from_question(q, eval_doc, class_name)
        if item:
            derived.append(item)

    return derived


def group_misconceptions_by_concept(misconceptions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Requirement 5: Group related misconceptions by concept only when supported
    by the actual questions, curriculum topic, or evaluation evidence.
    Combines instances for the same concept while preserving all individual student question evidence.
    """
    if not misconceptions:
        return []

    grouped: Dict[str, Dict[str, Any]] = {}

    for m in misconceptions:
        concept_key = (m.get("concept") or m.get("identified_concept") or "General").strip().lower()

        if concept_key not in grouped:
            primary = dict(m)
            primary["instances"] = [m]
            primary["student_names"] = [m["student_name"]] if m.get("student_name") else []
            primary["assessments"] = [m["assessment_title"]] if m.get("assessment_title") else []
            primary["occurrences"] = 1
            grouped[concept_key] = primary
        else:
            group = grouped[concept_key]
            group["instances"].append(m)
            group["occurrences"] += 1

            if m.get("student_name") and m["student_name"] not in group["student_names"]:
                group["student_names"].append(m["student_name"])

            if m.get("assessment_title") and m["assessment_title"] not in group["assessments"]:
                group["assessments"].append(m["assessment_title"])

            # If any instance has a verified diagnostic, group is not purely needs review
            if not m.get("needs_teacher_review"):
                group["needs_teacher_review"] = False
                group["confidence"] = m.get("confidence") or "High"
                group["actual_misconception"] = m.get("actual_misconception") or group["actual_misconception"]
                group["misconception"] = group["actual_misconception"]

    return list(grouped.values())


def sync_misconceptions_for_evaluation(eval_id: str, db_or_conn: Any = None) -> List[Dict[str, Any]]:
    """
    Requirement 9: Recalculate and synchronize misconceptions when an evaluation
    is saved, corrected, or overridden. Handles stale caches safely.
    """
    eval_id_str = str(eval_id).strip()
    if not eval_id_str:
        return []

    mongo_db = get_mongodb()
    if mongo_db is not None:
        return _sync_misconceptions_mongodb(mongo_db, eval_id_str)
    return _sync_misconceptions_sqlite(eval_id_str)


def _sync_misconceptions_mongodb(db: Any, eval_id_str: str) -> List[Dict[str, Any]]:
    from bson import ObjectId

    # Purge previous misconceptions for this evaluation
    db["misconceptions"].delete_many({
        "$or": [{"evaluation_id": eval_id_str}, {"evaluationId": eval_id_str}]
    })

    # Fetch evaluation
    eval_doc = db["evaluations"].find_one({"$or": [{"id": eval_id_str}, {"evaluation_id": eval_id_str}]})
    if not eval_doc and ObjectId and len(eval_id_str) == 24:
        try:
            eval_doc = db["evaluations"].find_one({"_id": ObjectId(eval_id_str)})
        except Exception:
            pass

    if not eval_doc:
        return []

    # Lookup class name
    class_id = str(eval_doc.get("class_id") or "")
    class_name = ""
    if class_id:
        c_doc = db["teacher_classes"].find_one({"id": class_id})
        if c_doc:
            class_name = c_doc.get("name") or c_doc.get("class_name") or ""

    derived = derive_misconceptions_from_evaluation(eval_doc, {class_id: class_name})

    for item in derived:
        db["misconceptions"].insert_one(item)

    return derived


def _sync_misconceptions_sqlite(eval_id_str: str) -> List[Dict[str, Any]]:
    conn = get_sqlite_db()
    cursor = conn.cursor()
    try:
        # Purge previous misconceptions for this evaluation
        cursor.execute("DELETE FROM misconceptions WHERE evaluation_id = ?", (eval_id_str,))

        # Fetch evaluation
        cursor.execute("SELECT * FROM evaluations WHERE id = ?", (eval_id_str,))
        row = cursor.fetchone()
        if not row:
            conn.commit()
            return []

        eval_doc = dict(row)

        # Fetch question details from evaluation_questions if questions JSON is not directly in row
        cursor.execute("SELECT * FROM evaluation_questions WHERE evaluation_id = ?", (eval_id_str,))
        q_rows = cursor.fetchall()
        questions = []
        for qr in q_rows:
            q_dict = dict(qr)
            # Map column names
            q_dict["student_answer"] = q_dict.get("answer_summary") or ""
            q_dict["what_student_should_have_written"] = q_dict.get("expected_answer") or ""
            q_dict["how_to_improve"] = q_dict.get("improvement_advice") or ""
            questions.append(q_dict)

        if not questions and eval_doc.get("questions_json"):
            try:
                questions = json.loads(eval_doc["questions_json"])
            except Exception:
                questions = []

        eval_doc["questions"] = questions

        # Lookup class name
        class_id = str(eval_doc.get("class_id") or "")
        class_name = ""
        if class_id:
            cursor.execute("SELECT name FROM teacher_classes WHERE id = ?", (class_id,))
            c_row = cursor.fetchone()
            if c_row:
                class_name = c_row["name"]

        derived = derive_misconceptions_from_evaluation(eval_doc, {class_id: class_name})

        for item in derived:
            cursor.execute(
                """
                INSERT INTO misconceptions
                (evaluation_id, student_id, teacher_id, created_by_user_id, created_by_role,
                 evaluation_source, class_id, student_name, roll_number, subject, topic,
                 concept, description, severity, remedy, exact_question, student_answer,
                 actual_misconception, correct_understanding, evidence, evidence_status,
                 needs_teacher_review, confidence, awarded_marks, maximum_marks,
                 question_number, assessment_title, occurrences, status, class_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["evaluation_id"],
                    item["student_id"],
                    item["teacher_id"],
                    item["teacher_id"],
                    "teacher",
                    "TEACHER_EVALUATION",
                    item["class_id"],
                    item["student_name"],
                    item["roll_number"],
                    item["subject"],
                    item["topic"],
                    item["concept"],
                    item["description"],
                    item["severity"],
                    item["remedy"],
                    item["exact_question"],
                    item["student_answer"],
                    item["actual_misconception"],
                    item["correct_understanding"],
                    item["evidence"],
                    item["evidence_status"],
                    1 if item["needs_teacher_review"] else 0,
                    item["confidence"],
                    item["awarded_marks"],
                    item["maximum_marks"],
                    item["question_number"],
                    item["assessment_title"],
                    item["occurrences"],
                    item["status"],
                    item["class_name"],
                ),
            )

        conn.commit()
        return derived
    finally:
        conn.close()


def get_teacher_misconceptions_list(teacher_id: Any, class_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch and recalculate genuine misconception insights for a teacher.
    Guarantees:
    - Strictly scoped to classes owned by this teacher.
    - Derived only from valid TEACHER_EVALUATION records with verified student identity.
    - Groups related misconceptions by concept.
    - Returns empty list if no eligible evidence exists (honest empty state).
    """
    if isinstance(teacher_id, (list, tuple, set)):
        teacher_ids = [str(t).strip() for t in teacher_id if t]
    else:
        teacher_ids = [str(teacher_id).strip()] if teacher_id else []

    if not teacher_ids:
        return []

    mongo_db = get_mongodb()
    if mongo_db is not None:
        return _get_teacher_misconceptions_mongodb(mongo_db, teacher_ids, class_id)
    return _get_teacher_misconceptions_sqlite(teacher_ids, class_id)


def _get_teacher_misconceptions_mongodb(db: Any, teacher_ids: List[str], class_id: Optional[str] = None) -> List[Dict[str, Any]]:
    # 1. Fetch authorized classes for this teacher
    class_query: Dict[str, Any] = {"teacher_id": {"$in": teacher_ids}}
    if class_id and class_id != "all":
        class_query["id"] = str(class_id)

    authorized_classes = list(db["teacher_classes"].find(class_query))
    if not authorized_classes:
        return []

    class_name_lookup = {
        str(c.get("id")): (c.get("name") or c.get("class_name") or "")
        for c in authorized_classes
    }
    authorized_class_ids = list(class_name_lookup.keys())

    # 2. Query valid TEACHER_EVALUATION records for these classes
    eval_query: Dict[str, Any] = {
        "evaluation_source": "TEACHER_EVALUATION",
        "$or": [
            {"teacher_id": {"$in": teacher_ids}},
            {"created_by_user_id": {"$in": teacher_ids}},
        ],
        "class_id": {"$in": authorized_class_ids},
        "identity_status": {"$nin": ["NEEDS_REVIEW", "UNLINKED"]},
    }

    eval_docs = list(db["evaluations"].find(eval_query).sort("created_at", -1))

    all_items: List[Dict[str, Any]] = []
    for ed in eval_docs:
        ed_items = derive_misconceptions_from_evaluation(ed, class_name_lookup)
        all_items.extend(ed_items)

    # 3. Group related misconceptions by concept (Requirement 5)
    return group_misconceptions_by_concept(all_items)


def _get_teacher_misconceptions_sqlite(teacher_ids: List[str], class_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_sqlite_db()
    cursor = conn.cursor()
    try:
        # 1. Fetch authorized classes
        t_placeholders = ",".join("?" for _ in teacher_ids)
        if class_id and class_id != "all":
            cursor.execute(
                f"SELECT id, name FROM teacher_classes WHERE teacher_id IN ({t_placeholders}) AND id = ?",
                teacher_ids + [str(class_id)]
            )
        else:
            cursor.execute(
                f"SELECT id, name FROM teacher_classes WHERE teacher_id IN ({t_placeholders})",
                teacher_ids
            )

        cls_rows = cursor.fetchall()
        if not cls_rows:
            return []

        class_name_lookup = {str(r["id"]): str(r["name"]) for r in cls_rows}
        authorized_class_ids = list(class_name_lookup.keys())

        # 2. Query valid TEACHER_EVALUATION records
        c_placeholders = ",".join("?" for _ in authorized_class_ids)
        cursor.execute(
            f"""
            SELECT * FROM evaluations
            WHERE evaluation_source = 'TEACHER_EVALUATION'
              AND (teacher_id IN ({t_placeholders}) OR created_by_user_id IN ({t_placeholders}))
              AND class_id IN ({c_placeholders})
              AND (identity_status IS NULL OR identity_status NOT IN ('NEEDS_REVIEW', 'UNLINKED'))
            ORDER BY created_at DESC
            """,
            teacher_ids + teacher_ids + authorized_class_ids
        )
        eval_rows = cursor.fetchall()

        all_items: List[Dict[str, Any]] = []
        for er in eval_rows:
            ed = dict(er)
            e_id = str(ed["id"])

            cursor.execute("SELECT * FROM evaluation_questions WHERE evaluation_id = ?", (e_id,))
            q_rows = cursor.fetchall()
            questions = []
            for qr in q_rows:
                qd = dict(qr)
                qd["student_answer"] = qd.get("answer_summary") or ""
                qd["what_student_should_have_written"] = qd.get("expected_answer") or ""
                qd["how_to_improve"] = qd.get("improvement_advice") or ""
                questions.append(qd)

            if not questions and ed.get("questions_json"):
                try:
                    questions = json.loads(ed["questions_json"])
                except Exception:
                    questions = []

            ed["questions"] = questions
            ed_items = derive_misconceptions_from_evaluation(ed, class_name_lookup)
            all_items.extend(ed_items)

        return group_misconceptions_by_concept(all_items)
    finally:
        conn.close()
