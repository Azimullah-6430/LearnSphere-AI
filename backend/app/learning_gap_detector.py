"""
Learning Gap Detector for Blind Learning Companion
=================================================
Grounded strictly in authentic student learning evidence:
- Knowledge Challenge records
- Student Self-Evaluations
- Topic Practice & Checkpoints
- Historical and repeated attempts

Strict Constraints:
- No mock learning gaps or random suggestions.
- Distinct classification: calculation vs formula vs diagram vs conceptual.
- Syllabus-mapped: Student -> Subject -> Unit -> Topic -> Subtopic -> Attempt.
- Topic Learning Status: Not started, Learning in progress, Needs more practice,
  Understanding demonstrated, Insufficient evidence.
- No Teacher Portal data modification or reliance.
- Supportive, audio-accessible diagnostic feedback.
"""

import json
import logging
import uuid
import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


# Standardized Nature of Mistake Classifications (Prompt 3 Requirement 3)
MISTAKE_TYPES = {
    "CALCULATION_MISTAKE": "Calculation mistakes",
    "INCORRECT_FORMULA_SELECTION": "Incorrect formula selection",
    "INCORRECT_FORMULA_APPLICATION": "Incorrect formula application",
    "MISSING_REASONING_STEPS": "Missing reasoning steps",
    "INCOMPLETE_ANSWERS": "Incomplete answers",
    "TERMINOLOGY_MISUNDERSTANDING": "Misunderstanding of terminology",
    "DIAGRAM_INTERPRETATION_DIFFICULTY": "Difficulty interpreting diagrams",
    "GRAPH_UNDERSTANDING_DIFFICULTY": "Difficulty understanding graphs",
    "CARELESS_ERROR": "Correct understanding with an isolated careless error",
    "CONCEPTUAL_MISUNDERSTANDING": "Conceptual misunderstanding"
}

# Standardized Topic Learning Status (Prompt 3 Requirement 2)
TOPIC_STATUS = {
    "NOT_STARTED": "Not started",
    "IN_PROGRESS": "Learning in progress",
    "NEEDS_PRACTICE": "Needs more practice",
    "UNDERSTANDING_DEMONSTRATED": "Understanding demonstrated",
    "INSUFFICIENT_EVIDENCE": "Insufficient evidence"
}

# Standardized Evidence Strength (Prompt 3 Requirement 4)
EVIDENCE_STRENGTH = {
    "CONFIRMED_REPEATED": "Confirmed repeated difficulty",
    "POSSIBLE_DIFFICULTY": "Possible difficulty requiring more practice",
    "INSUFFICIENT": "Insufficient evidence"
}


def classify_mistake_nature(
    student_answer: str,
    expected_answer: str,
    question_text: str = "",
    missing_points: str = "",
    awarded_marks: float = 0.0,
    max_marks: float = 5.0,
    prior_attempts: List[Dict[str, Any]] = None
) -> Tuple[str, str, str]:
    """
    Classify the exact nature of mistake, explanation of why it indicates a gap,
    and recommended next action based strictly on evidence.
    """
    s_lower = (student_answer or "").lower().strip()
    e_lower = (expected_answer or "").lower().strip()
    q_lower = (question_text or "").lower().strip()
    m_lower = (missing_points or "").lower().strip()

    # Score ratio
    ratio = awarded_marks / max_marks if max_marks > 0 else 0.0

    # 1. Calculation Mistake: Check if formula and reasoning are correct, but final arithmetic/number is wrong
    arithmetic_signals = [
        "arithmetic", "calculation error", "arithmetic mistake", "calculation mistake",
        "math error", "sign error", "multiplication error", "addition error", "division error",
        "arithmetic slip"
    ]
    has_arithmetic_feedback = any(w in m_lower or w in s_lower for w in arithmetic_signals)
    has_math_in_q = any(sym in q_lower for sym in ["calculate", "numerical", "solve", "find the value", "=", "+", "-", "*", "/"])

    if has_arithmetic_feedback or (has_math_in_q and ratio >= 0.6 and any(w in m_lower for w in ["value", "final answer", "number"])):
        return (
            MISTAKE_TYPES["CALCULATION_MISTAKE"],
            "Your underlying conceptual setup and formula substitution were correct, but an arithmetic slip occurred in intermediate computation.",
            "Double-check step-by-step arithmetic operations and verify SI units before writing the final numeric answer."
        )

    # 2. Diagram Interpretation Difficulty
    diagram_signals = ["diagram", "circuit", "schematic", "polarity", "connection", "component", "loop", "node", "branch"]
    if any(w in q_lower for w in diagram_signals) and any(w in m_lower for w in ["diagram", "circuit", "polarity", "node", "connection", "component", "symbol"]):
        return (
            MISTAKE_TYPES["DIAGRAM_INTERPRETATION_DIFFICULTY"],
            "Evidence indicates difficulty mapping component interconnections, polarity conventions, or branch paths in the visual schematic.",
            "Use Concept-to-Sense Audio to trace component-by-component current or signal flow from the source through each junction."
        )

    # 3. Graph Understanding Difficulty
    graph_signals = ["graph", "plot", "curve", "slope", "axis", "axes", "intercept", "inflection", "asymptote"]
    if any(w in q_lower for w in graph_signals) and any(w in m_lower for w in ["slope", "axis", "curve", "intercept", "inflection", "coordinates"]):
        return (
            MISTAKE_TYPES["GRAPH_UNDERSTANDING_DIFFICULTY"],
            "Evidence indicates confusion reading coordinate axes, calculating tangent slope, or identifying curve inflection points.",
            "Review the physical meaning of the graph's horizontal and vertical axes and practice extracting slope units."
        )

    # 4. Incorrect Formula Selection
    if any(w in m_lower for w in ["wrong formula", "incorrect formula", "formula used is not applicable", "used the wrong equation"]):
        return (
            MISTAKE_TYPES["INCORRECT_FORMULA_SELECTION"],
            "The formula chosen does not apply to the specific boundary conditions given in the problem statement.",
            "Review the boundary constraints governing when this formula applies versus alternative equations."
        )

    # 5. Incorrect Formula Application
    if any(w in m_lower for w in ["substitution", "substituted incorrectly", "plugged in wrong variable", "variable mismatch"]):
        return (
            MISTAKE_TYPES["INCORRECT_FORMULA_APPLICATION"],
            "The correct governing formula was identified, but variables or given quantities were substituted into the wrong positions.",
            "Write down each variable explicitly with its given numerical value and unit before performing algebraic substitution."
        )

    # 6. Misunderstanding of Terminology
    if any(w in m_lower for w in ["terminology", "confused term", "definition", "keyword", "symbol definition"]):
        return (
            MISTAKE_TYPES["TERMINOLOGY_MISUNDERSTANDING"],
            "Evidence shows technical confusion between interrelated syllabus terms or standard definitions.",
            "Listen to the Important Terminology audio recap for this unit to master precise academic definitions."
        )

    # 7. Missing Reasoning Steps
    if any(w in m_lower for w in ["missing steps", "derivation steps", "no working shown", "intermediate steps", "skipped reasoning"]):
        return (
            MISTAKE_TYPES["MISSING_REASONING_STEPS"],
            "The final conclusion was stated without showing the necessary intermediate logical derivation steps.",
            "Practice writing out each intermediate derivation step clearly; university rubrics allocate partial marks per step."
        )

    # 8. Incomplete Answers
    if any(w in m_lower for w in ["incomplete", "omitted", "missing part", "partially answered", "second part omitted", "addressed only part"]):
        return (
            MISTAKE_TYPES["INCOMPLETE_ANSWERS"],
            "Only a portion of the multi-part question was addressed, leaving key required components unanswered.",
            "Break down multi-part exam prompts into an explicit sub-question checklist before formulating your answer."
        )

    # 9. Correct Understanding with Isolated Careless Error
    if ratio >= 0.8 and prior_attempts and len(prior_attempts) >= 1:
        avg_score = sum(a.get("score", 0) for a in prior_attempts) / len(prior_attempts)
        if avg_score >= 0.75:
            return (
                MISTAKE_TYPES["CARELESS_ERROR"],
                "Your track record shows solid conceptual grasp of this topic; this incorrect answer represents an isolated careless error.",
                "Review the question carefully to eliminate isolated typographical or minor oversight errors."
            )

    # 10. Default: Conceptual Misunderstanding
    return (
        MISTAKE_TYPES["CONCEPTUAL_MISUNDERSTANDING"],
        "Evidence indicates a gap in understanding the core theoretical or physical principles governing this syllabus concept.",
        "Listen to the 10-Step Master Lesson in Simple Mode to rebuild foundational intuition before attempting practice questions."
    )


def extract_student_learning_evidence(
    student_id: str,
    student_name: str,
    mongo_db: Any = None,
    sqlite_conn: Any = None,
    include_self_eval: bool = True
) -> List[Dict[str, Any]]:
    """
    Collect authentic learning records strictly belonging to the authenticated student:
    - Knowledge Challenge attempts
    - Student Self-Evaluations (STUDENT_SELF_EVALUATION or created_by_role == 'student', excluded for blind mode)
    - Blind Companion Practice Attempts
    """
    evidence_items = []
    clean_id = str(student_id or "").strip()
    clean_name = str(student_name or "").strip()

    # 1. Blind Practice Attempts
    if mongo_db is not None:
        try:
            records = list(mongo_db["blind_practice_attempts"].find({
                "$or": [{"student_id": clean_id}, {"studentId": clean_id}]
            }))
            for r in records:
                evidence_items.append({
                    "source": "blind_practice",
                    "subject": r.get("subject"),
                    "unit": r.get("unit"),
                    "topic": r.get("topic"),
                    "subtopic": r.get("subtopic"),
                    "question_text": r.get("question_text"),
                    "student_answer": r.get("student_answer"),
                    "expected_answer": r.get("expected_answer"),
                    "is_correct": bool(r.get("is_correct")),
                    "score": float(r.get("score") or 0.0),
                    "max_score": float(r.get("max_score") or 5.0),
                    "feedback": r.get("feedback") or "",
                    "created_at": r.get("created_at")
                })
        except Exception as exc:
            logger.debug("[LearningGapDetector] Mongo blind_practice error: %s", exc)
    elif sqlite_conn is not None:
        try:
            cursor = sqlite_conn.cursor()
            cursor.execute(
                "SELECT * FROM blind_practice_attempts WHERE student_id = ? ORDER BY created_at DESC",
                (clean_id,)
            )
            rows = cursor.fetchall()
            for row in rows:
                r = dict(row)
                evidence_items.append({
                    "source": "blind_practice",
                    "subject": r.get("subject"),
                    "unit": r.get("unit"),
                    "topic": r.get("topic"),
                    "subtopic": r.get("subtopic"),
                    "question_text": r.get("question_text"),
                    "student_answer": r.get("student_answer"),
                    "expected_answer": r.get("expected_answer"),
                    "is_correct": bool(r.get("is_correct")),
                    "score": float(r.get("score") or 0.0),
                    "max_score": float(r.get("max_score") or 5.0),
                    "feedback": r.get("feedback") or "",
                    "created_at": r.get("created_at")
                })
        except Exception as exc:
            logger.debug("[LearningGapDetector] SQLite blind_practice error: %s", exc)

    # 2. Knowledge Challenge Records
    if mongo_db is not None:
        try:
            kc_records = list(mongo_db["knowledge_challenges"].find({
                "$or": [{"student_id": clean_id}, {"studentId": clean_id}]
            }))
            for kc in kc_records:
                subj = kc.get("subject") or "General Academic"
                top = kc.get("topic") or "General"
                score = float(kc.get("score") or 0.0)
                total = float(kc.get("total_questions") or 5.0)
                c_data = kc.get("challenge_data") or []
                if isinstance(c_data, list):
                    for q_idx, q in enumerate(c_data):
                        evidence_items.append({
                            "source": "knowledge_challenge",
                            "subject": subj,
                            "unit": kc.get("unit") or "",
                            "topic": top,
                            "subtopic": top,
                            "question_text": q.get("question") or f"Knowledge Challenge Question {q_idx + 1}",
                            "student_answer": str(q.get("selected_option") or q.get("student_answer") or ""),
                            "expected_answer": str(q.get("correct_answer") or ""),
                            "is_correct": bool(q.get("is_correct", False)),
                            "score": 1.0 if q.get("is_correct") else 0.0,
                            "max_score": 1.0,
                            "feedback": q.get("explanation") or "",
                            "created_at": kc.get("created_at")
                        })
        except Exception as exc:
            logger.debug("[LearningGapDetector] Mongo KC error: %s", exc)
    elif sqlite_conn is not None:
        try:
            cursor = sqlite_conn.cursor()
            cursor.execute(
                "SELECT * FROM knowledge_challenges WHERE student_id = ? ORDER BY created_at DESC",
                (clean_id,)
            )
            kc_rows = cursor.fetchall()
            for row in kc_rows:
                kc = dict(row)
                subj = kc.get("subject") or "General Academic"
                top = kc.get("topic") or "General"
                c_raw = kc.get("challenge_data_json") or "[]"
                try:
                    c_data = json.loads(c_raw)
                except Exception:
                    c_data = []
                if isinstance(c_data, list):
                    for q_idx, q in enumerate(c_data):
                        evidence_items.append({
                            "source": "knowledge_challenge",
                            "subject": subj,
                            "unit": "",
                            "topic": top,
                            "subtopic": top,
                            "question_text": q.get("question") or f"Knowledge Challenge Question {q_idx + 1}",
                            "student_answer": str(q.get("selected_option") or q.get("student_answer") or ""),
                            "expected_answer": str(q.get("correct_answer") or ""),
                            "is_correct": bool(q.get("is_correct", False)),
                            "score": 1.0 if q.get("is_correct") else 0.0,
                            "max_score": 1.0,
                            "feedback": q.get("explanation") or "",
                            "created_at": kc.get("created_at")
                        })
        except Exception as exc:
            logger.debug("[LearningGapDetector] SQLite KC error: %s", exc)

    # 3. Student Self-Evaluations (Only for non-blind students)
    if include_self_eval:
        if mongo_db is not None:
            try:
                self_evals = list(mongo_db["evaluations"].find({
                    "$and": [
                        {"$or": [{"student_id": clean_id}, {"created_by_user_id": clean_id}]},
                        {"$or": [
                            {"evaluation_source": "STUDENT_SELF_EVALUATION"},
                            {"created_by_role": "student"},
                            {"role": "student"}
                        ]}
                    ]
                }))
                for se in self_evals:
                    subj = se.get("subject") or "General Academic"
                    eval_id = str(se.get("_id") or se.get("id"))
                    questions = se.get("questions") or []
                    if isinstance(questions, list):
                        for q in questions:
                            q_awarded = float(q.get("awarded_marks", 0))
                            q_max = float(q.get("maximum_marks", 5))
                            is_corr = q_awarded >= (q_max * 0.7)
                            evidence_items.append({
                                "source": "self_evaluation",
                                "subject": subj,
                                "unit": se.get("unit") or "",
                                "topic": q.get("topic") or subj,
                                "subtopic": q.get("subtopic") or q.get("topic") or subj,
                                "question_text": q.get("question_number") or q.get("question_type") or "Evaluation Question",
                                "student_answer": q.get("student_answer") or q.get("answer_summary") or "",
                                "expected_answer": q.get("expected_answer") or "",
                                "is_correct": is_corr,
                                "score": q_awarded,
                                "max_score": q_max,
                                "missing_points": q.get("missing_points") or "",
                                "feedback": q.get("improvement_advice") or "",
                                "created_at": se.get("created_at")
                            })
            except Exception as exc:
                logger.debug("[LearningGapDetector] Mongo Self-Evaluation error: %s", exc)
        elif sqlite_conn is not None:
            try:
                cursor = sqlite_conn.cursor()
                cursor.execute("""
                    SELECT e.id as eval_id, e.subject, eq.*
                    FROM evaluations e
                    JOIN evaluation_questions eq ON e.id = eq.evaluation_id
                    WHERE (e.student_id = ? OR e.created_by_user_id = ?)
                      AND (e.evaluation_source = 'STUDENT_SELF_EVALUATION' OR e.created_by_role = 'student')
                    ORDER BY e.created_at DESC
                """, (clean_id, clean_id))
                rows = cursor.fetchall()
                for row in rows:
                    r = dict(row)
                    q_awarded = float(r.get("awarded_marks") or 0.0)
                    q_max = float(r.get("maximum_marks") or 5.0)
                    is_corr = q_awarded >= (q_max * 0.7)
                    evidence_items.append({
                        "source": "self_evaluation",
                        "subject": r.get("subject") or "General Academic",
                        "unit": "",
                        "topic": r.get("question_type") or r.get("subject"),
                        "subtopic": r.get("question_type") or r.get("subject"),
                        "question_text": f"Question {r.get('question_number')}",
                        "student_answer": r.get("student_answer") or r.get("answer_summary") or "",
                        "expected_answer": r.get("expected_answer") or "",
                        "is_correct": is_corr,
                        "score": q_awarded,
                        "max_score": q_max,
                        "missing_points": r.get("missing_points") or "",
                        "feedback": r.get("improvement_advice") or "",
                        "created_at": r.get("created_at")
                    })
            except Exception as exc:
                logger.debug("[LearningGapDetector] SQLite Self-Evaluation error: %s", exc)

    return evidence_items


def analyze_student_learning_gaps(
    student_id: str,
    student_name: str,
    syllabus_doc: Dict[str, Any] = None,
    mongo_db: Any = None,
    sqlite_conn: Any = None,
    is_blind: bool = True
) -> Dict[str, Any]:
    """
    Main diagnostic engine for Learning Gap Detector.
    Constructs the structured relationship:
    Student -> Subject -> Unit -> Topic -> Subtopic -> Question -> Attempt -> Observed Gap.
    Computes Topic Learning Status and Evidence Strength.
    """
    clean_id = str(student_id or "").strip()
    evidence_items = extract_student_learning_evidence(clean_id, student_name, mongo_db, sqlite_conn, include_self_eval=not is_blind)

    # 1. Build syllabus catalog from authoritative syllabus
    syllabus_tree: Dict[str, Any] = {}
    if syllabus_doc and isinstance(syllabus_doc, dict):
        raw_subjects = syllabus_doc.get("subjects") or []
        chapters_dict = syllabus_doc.get("chapters") or syllabus_doc.get("units") or {}

        for s in raw_subjects:
            s_name = s.get("name") if isinstance(s, dict) else str(s)
            if not s_name:
                continue
            syllabus_tree[s_name] = {}
            # Units for this subject
            s_units = chapters_dict.get(s_name) or []
            if isinstance(s_units, list):
                for u in s_units:
                    if isinstance(u, dict):
                        u_name = u.get("name") or u.get("title") or "Unit"
                        concepts = u.get("concepts") or u.get("topics") or []
                        syllabus_tree[s_name][u_name] = [str(c) for c in concepts]
                    elif isinstance(u, str):
                        syllabus_tree[s_name][u] = [u]

    # If no evidence items exist at all, return pristine empty state
    if not evidence_items:
        # Build initial status map
        status_map = {}
        for s_name, units in syllabus_tree.items():
            for u_name, topics in units.items():
                for t in topics:
                    status_map[f"{s_name}::{t}"] = TOPIC_STATUS["NOT_STARTED"]

        return {
            "has_evidence": False,
            "total_attempts": 0,
            "learning_gaps": [],
            "topic_status_map": status_map,
            "audio_summary": (
                "No practice or checkpoint records detected yet. Start exploring your syllabus lessons and attempt checkpoints to unlock personalized learning gap insights."
                if is_blind else
                "No practice or evaluation records detected yet. Start exploring your syllabus lessons and attempt checkpoints to unlock personalized learning gap insights."
            )
        }

    # 2. Group evidence items by Subject -> Topic
    topic_attempts: Dict[str, List[Dict[str, Any]]] = {}
    for item in evidence_items:
        subj = item.get("subject") or "General Academic"
        top = item.get("topic") or "General Concept"
        # Match against syllabus topic if possible
        matched_top = None
        for s_k, u_dict in syllabus_tree.items():
            if subj.lower() in s_k.lower() or s_k.lower() in subj.lower():
                for u_k, t_list in u_dict.items():
                    for t_item in t_list:
                        if top.lower() in t_item.lower() or t_item.lower() in top.lower():
                            matched_top = t_item
                            subj = s_k
                            break
                    if matched_top:
                        break
            if matched_top:
                break

        final_top = matched_top or top
        key = f"{subj}::{final_top}"
        if key not in topic_attempts:
            topic_attempts[key] = []
        topic_attempts[key].append(item)

    # 3. Analyze each topic for gaps and calculate learning status
    learning_gaps = []
    topic_status_map = {}

    for s_name, units in syllabus_tree.items():
        for u_name, topics in units.items():
            for t_name in topics:
                key = f"{s_name}::{t_name}"
                attempts = topic_attempts.get(key, [])

                if not attempts:
                    topic_status_map[key] = TOPIC_STATUS["NOT_STARTED"]
                    continue

                # Analyze attempts
                correct_count = sum(1 for a in attempts if a.get("is_correct"))
                total_attempts = len(attempts)
                avg_score = sum(a.get("score", 0) for a in attempts) / max(sum(a.get("max_score", 5) for a in attempts), 1.0)

                # Check if there are failures / mistakes
                failed_attempts = [a for a in attempts if not a.get("is_correct")]

                if not failed_attempts:
                    if total_attempts >= 2 and avg_score >= 0.8:
                        topic_status_map[key] = TOPIC_STATUS["UNDERSTANDING_DEMONSTRATED"]
                    else:
                        topic_status_map[key] = TOPIC_STATUS["INSUFFICIENT_EVIDENCE"]
                    continue

                # Mistake exists: determine nature of mistake for each failed attempt
                mistakes_by_nature: Dict[str, List[Dict[str, Any]]] = {}
                for fa in failed_attempts:
                    feedback_str = fa.get("missing_points") or fa.get("feedback") or ""
                    mistake_nature, why_gap, next_action = classify_mistake_nature(
                        student_answer=fa.get("student_answer", ""),
                        expected_answer=fa.get("expected_answer", ""),
                        question_text=fa.get("question_text", ""),
                        missing_points=feedback_str,
                        awarded_marks=fa.get("score", 0.0),
                        max_marks=fa.get("max_score", 5.0),
                        prior_attempts=attempts
                    )
                    if mistake_nature not in mistakes_by_nature:
                        mistakes_by_nature[mistake_nature] = []
                    mistakes_by_nature[mistake_nature].append({
                        "attempt": fa,
                        "why_gap": why_gap,
                        "next_action": next_action
                    })

                # Assign Topic Status
                if len(failed_attempts) >= 2 or any(m == MISTAKE_TYPES["CONCEPTUAL_MISUNDERSTANDING"] for m in mistakes_by_nature):
                    topic_status_map[key] = TOPIC_STATUS["NEEDS_PRACTICE"]
                elif any(m == MISTAKE_TYPES["CALCULATION_MISTAKE"] or m == MISTAKE_TYPES["CARELESS_ERROR"] for m in mistakes_by_nature):
                    topic_status_map[key] = TOPIC_STATUS["IN_PROGRESS"]
                elif total_attempts == 1 and not failed_attempts:
                    topic_status_map[key] = TOPIC_STATUS["INSUFFICIENT_EVIDENCE"]
                else:
                    topic_status_map[key] = TOPIC_STATUS["IN_PROGRESS"]

                # Create evidence-grounded gap entries (consolidating duplicate error types per topic)
                for m_nature, occs in mistakes_by_nature.items():
                    rep_count = len(occs)
                    primary_occ = occs[-1]
                    att = primary_occ["attempt"]

                    # Determine evidence strength
                    if rep_count >= 2:
                        strength = EVIDENCE_STRENGTH["CONFIRMED_REPEATED"]
                    elif rep_count == 1 and total_attempts >= 2:
                        strength = EVIDENCE_STRENGTH["POSSIBLE_DIFFICULTY"]
                    else:
                        strength = EVIDENCE_STRENGTH["INSUFFICIENT"]

                    created_val = att.get("created_at")
                    if isinstance(created_val, datetime):
                        created_val = created_val.isoformat()
                    elif created_val is not None:
                        created_val = str(created_val)
                    else:
                        created_val = now.isoformat()

                    gap_entry = {
                        "gap_id": f"gap_{uuid.uuid4().hex[:8]}",
                        "student_id": clean_id,
                        "student_name": student_name,
                        "subject": s_name,
                        "unit": u_name,
                        "topic": t_name,
                        "subtopic": att.get("subtopic") or t_name,
                        "question_ref": att.get("question_text") or f"Practice on {t_name}",
                        "student_answer": att.get("student_answer") or "Not provided",
                        "expected_answer": att.get("expected_answer") or "Standard curriculum criteria",
                        "mistake_nature": m_nature,
                        "why_learning_gap": primary_occ["why_gap"],
                        "evidence_strength": strength,
                        "recommended_action": primary_occ["next_action"],
                        "attempt_count": rep_count,
                        "total_topic_attempts": total_attempts,
                        "status": topic_status_map[key],
                        "created_at": created_val
                    }
                    learning_gaps.append(gap_entry)

    # Persist authoritative gaps to database for durability & history
    if mongo_db is not None:
        try:
            mongo_db["blind_learning_gaps"].delete_many({"student_id": clean_id})
            if learning_gaps:
                mongo_db["blind_learning_gaps"].insert_many([{**g} for g in learning_gaps])
        except Exception as exc:
            logger.debug("[LearningGapDetector] Mongo gap cache save error: %s", exc)
    elif sqlite_conn is not None:
        try:
            cursor = sqlite_conn.cursor()
            cursor.execute("DELETE FROM blind_learning_gaps WHERE student_id = ?", (clean_id,))
            for g in learning_gaps:
                cursor.execute("""
                    INSERT INTO blind_learning_gaps
                    (gap_id, student_id, student_name, subject, unit, topic, subtopic,
                     question_ref, student_answer, expected_answer, mistake_nature,
                     why_learning_gap, evidence_strength, recommended_action, attempt_count,
                     status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    g["gap_id"], g["student_id"], g["student_name"], g["subject"], g["unit"],
                    g["topic"], g["subtopic"], g["question_ref"], g["student_answer"],
                    g["expected_answer"], g["mistake_nature"], g["why_learning_gap"],
                    g["evidence_strength"], g["recommended_action"], g["attempt_count"],
                    g["status"], str(g.get("created_at") or now.isoformat()), now.isoformat()
                ))
            sqlite_conn.commit()
        except Exception as exc:
            logger.debug("[LearningGapDetector] SQLite gap cache save error: %s", exc)

    # 4. Generate supportive spoken summary (Prompt 3 Requirement 5)
    if not learning_gaps:
        audio_summary = f"Great work, {student_name}! Based on your practice attempts across {len(topic_attempts)} syllabus topics, no active conceptual learning gaps were observed. Keep exploring new units."
    else:
        gap_count = len(learning_gaps)
        first_gap = learning_gaps[0]
        analysis_source = "practice attempts and concept checkpoints" if is_blind else "recent practice and self-evaluations"
        audio_summary = (
            f"Hello {student_name}. We analyzed your {analysis_source}. "
            f"You have {gap_count} specific learning point{'' if gap_count == 1 else 's'} to improve. "
            f"For {first_gap['topic']} in {first_gap['subject']}, the observed area is {first_gap['mistake_nature']}. "
            f"{first_gap['why_learning_gap']} {first_gap['recommended_action']}"
        )

    return {
        "has_evidence": True,
        "total_attempts": len(evidence_items),
        "learning_gaps": learning_gaps,
        "topic_status_map": topic_status_map,
        "audio_summary": audio_summary
    }


def record_blind_practice_attempt(
    student_id: str,
    student_name: str,
    subject: str,
    unit: str,
    topic: str,
    subtopic: str,
    question_text: str,
    student_answer: str,
    expected_answer: str,
    is_correct: bool,
    score: float,
    max_score: float = 5.0,
    feedback: str = "",
    mongo_db: Any = None,
    sqlite_conn: Any = None
) -> Dict[str, Any]:
    """
    Record an authentic practice attempt from the Blind Learning Companion,
    dynamically update the learning gap, and update the topic's learning status.
    """
    clean_id = str(student_id or "").strip()
    attempt_id = f"att_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)

    # Classify mistake nature if incorrect
    mistake_nature = None
    if not is_correct or (score / max_score if max_score > 0 else 0) < 0.7:
        mistake_nature, _, _ = classify_mistake_nature(
            student_answer=student_answer,
            expected_answer=expected_answer,
            question_text=question_text,
            missing_points=feedback,
            awarded_marks=score,
            max_marks=max_score
        )

    attempt_record = {
        "attempt_id": attempt_id,
        "student_id": clean_id,
        "student_name": student_name,
        "subject": subject,
        "unit": unit,
        "topic": topic,
        "subtopic": subtopic or topic,
        "question_text": question_text,
        "student_answer": student_answer,
        "expected_answer": expected_answer,
        "is_correct": bool(is_correct),
        "score": float(score),
        "max_score": float(max_score),
        "feedback": feedback,
        "mistake_nature": mistake_nature,
        "created_at": now
    }

    if mongo_db is not None:
        try:
            mongo_db["blind_practice_attempts"].insert_one(attempt_record)
        except Exception as exc:
            logger.error("[LearningGapDetector] Mongo record attempt error: %s", exc)
    elif sqlite_conn is not None:
        try:
            cursor = sqlite_conn.cursor()
            cursor.execute("""
                INSERT INTO blind_practice_attempts
                (attempt_id, student_id, student_name, subject, unit, topic, subtopic,
                 question_text, student_answer, expected_answer, is_correct, score, max_score, feedback, mistake_nature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attempt_id, clean_id, student_name, subject, unit, topic, subtopic or topic,
                question_text, student_answer, expected_answer, 1 if is_correct else 0,
                score, max_score, feedback, mistake_nature
            ))
            sqlite_conn.commit()
        except Exception as exc:
            logger.error("[LearningGapDetector] SQLite record attempt error: %s", exc)

    if "_id" in attempt_record:
        attempt_record["_id"] = str(attempt_record["_id"])
    if isinstance(attempt_record.get("created_at"), datetime):
        attempt_record["created_at"] = attempt_record["created_at"].isoformat()

    return attempt_record
