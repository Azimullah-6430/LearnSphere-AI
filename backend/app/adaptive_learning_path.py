"""
LearnSphere AI - Adaptive Learning Path Engine for Blind Companion
==================================================================
Prompt 4: Generates personalized, syllabus-integrated, evidence-grounded
learning paths for blind and low-vision students.

Core Principles:
1. Strict grounding in actual uploaded syllabus, unit/topic structure, and genuine evaluation history.
2. Intelligent topic prioritization: considers prerequisite concepts, topic dependencies,
   repeated mistakes, and demonstrated improvement. Weak foundational concepts are prioritized first.
3. Adaptive teaching: provides smaller breakdown steps, alternate explanations, terminology clarity,
   and fresh examples when struggling; advances to next objectives when understanding is demonstrated.
4. Recommendation transparency: every recommendation explicitly details what to study, why it is
   recommended, which learning evidence supports it, what activity will help, and how understanding
   will be checked.
5. Audio-first presentation & voice commands: "What should I study next?", "Why was this topic recommended?",
   "Start learning", "Give me another example", "Show my learning progress".
6. Durable progress preservation across sessions and settings toggles.
"""

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.learning_gap_detector import (
    EVIDENCE_STRENGTH,
    MISTAKE_TYPES,
    TOPIC_STATUS,
    analyze_student_learning_gaps,
    extract_student_learning_evidence,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# PREREQUISITE & DEPENDENCY MAPPING
# ─────────────────────────────────────────────────────────────────────────────

# Domain-specific foundational prerequisite rules (lowered key -> list of prerequisite terms)
ACADEMIC_PREREQUISITES: Dict[str, List[str]] = {
    # Mathematics / Calculus
    "chain rule": ["differentiation", "composite functions", "limits", "derivatives"],
    "composite functions": ["functions", "domain and range"],
    "product rule": ["derivatives", "limits"],
    "quotient rule": ["product rule", "derivatives"],
    "implicit differentiation": ["chain rule", "derivatives"],
    "integration by parts": ["integration", "product rule"],
    "differential equations": ["integration", "derivatives"],
    "definite integrals": ["indefinite integrals", "antiderivatives"],
    "taylor series": ["power series", "derivatives", "factorials"],

    # Circuit Theory / Electrical
    "thevenin's theorem": ["ohm's law", "kirchhoff's laws", "voltage divider", "equivalent resistance"],
    "norton's equivalent": ["thevenin's theorem", "kirchhoff's current law", "source transformation"],
    "maximum power transfer": ["thevenin's theorem", "load resistance"],
    "superposition theorem": ["linearity", "independent sources", "kirchhoff's laws"],
    "mesh analysis": ["kirchhoff's voltage law", "ohm's law"],
    "nodal analysis": ["kirchhoff's current law", "conductance"],
    "rlc resonance": ["ac circuits", "inductive reactance", "capacitive reactance"],
    "op-amp circuits": ["ideal op-amp model", "negative feedback", "virtual ground"],

    # Signals & Systems
    "fourier transform": ["fourier series", "continuous-time signals", "complex exponentials"],
    "frequency response": ["fourier transform", "transfer function", "bode plot"],
    "laplace transform": ["fourier transform", "differential equations", "region of convergence"],
    "z-transform": ["discrete-time signals", "sampling theorem", "power series"],
    "convolution": ["impulse response", "linear time-invariant systems"],

    # Computer Science / Algorithms
    "binary search trees": ["binary trees", "recursion", "arrays"],
    "dijkstra's algorithm": ["graph representation", "breadth first search", "priority queues"],
    "dynamic programming": ["recursion", "memoization", "optimal substructure"],
    "quicksort": ["recursion", "divide and conquer", "partitioning"],

    # Physics / Mechanics
    "rotational dynamics": ["newton's laws", "torque", "moment of inertia"],
    "simple harmonic motion": ["hooke's law", "restoring force", "conservation of energy"],
    "electromagnetic induction": ["faraday's law", "magnetic flux", "lenz's law"],
}


def find_prerequisite_topics(
    target_topic: str,
    available_topics: List[str]
) -> List[str]:
    """
    Find prerequisite topics for a given topic from the available syllabus topics.
    Uses:
    1. Direct academic dependency dictionary matching.
    2. Syllabus sequence (topics ordered before this topic in the same unit).
    """
    target_lower = target_topic.lower().strip()
    prereqs: List[str] = []

    # 1. Match against known academic dependency table
    for concept_key, reqs in ACADEMIC_PREREQUISITES.items():
        if concept_key in target_lower:
            for req in reqs:
                for cand in available_topics:
                    cand_lower = cand.lower().strip()
                    if req in cand_lower and cand_lower != target_lower and cand not in prereqs:
                        prereqs.append(cand)

    # 2. Sequential syllabus heuristic: if target topic is in the list, earlier topics in that list
    # may be foundational
    if target_topic in available_topics:
        idx = available_topics.index(target_topic)
        if idx > 0 and len(prereqs) == 0:
            # The immediately preceding topic in the unit is often a direct prerequisite
            prereqs.append(available_topics[idx - 1])

    return prereqs


# ─────────────────────────────────────────────────────────────────────────────
# TOPIC PROGRESS STORAGE & RETRIEVAL
# ─────────────────────────────────────────────────────────────────────────────

def get_student_topic_progress(
    student_id: str,
    mongo_db: Any = None,
    sqlite_conn: Any = None
) -> Dict[str, Dict[str, Any]]:
    """
    Retrieve stored progress per topic for this student.
    Returns mapping: f"{subject}::{topic}" -> progress record.
    """
    clean_id = str(student_id or "").strip()
    progress_map: Dict[str, Dict[str, Any]] = {}

    if mongo_db is not None:
        try:
            records = list(mongo_db["blind_topic_progress"].find({"student_id": clean_id}))
            for r in records:
                key = f"{r.get('subject')}::{r.get('topic')}"
                progress_map[key] = {
                    "subject": r.get("subject"),
                    "unit": r.get("unit"),
                    "topic": r.get("topic"),
                    "subtopic": r.get("subtopic"),
                    "status": r.get("status", "not_started"),
                    "completed_steps": r.get("completed_steps") or [],
                    "attempts_count": r.get("attempts_count", 0),
                    "mastery_score": float(r.get("mastery_score") or 0.0),
                    "last_studied_at": r.get("last_studied_at")
                }
        except Exception as exc:
            logger.debug("[AdaptivePath] Mongo get progress error: %s", exc)
    elif sqlite_conn is not None:
        try:
            cursor = sqlite_conn.cursor()
            cursor.execute("SELECT * FROM blind_topic_progress WHERE student_id = ?", (clean_id,))
            rows = cursor.fetchall()
            for row in rows:
                r = dict(row)
                key = f"{r.get('subject')}::{r.get('topic')}"
                completed_steps = []
                try:
                    completed_steps = json.loads(r.get("completed_steps") or "[]")
                except Exception:
                    completed_steps = []

                progress_map[key] = {
                    "subject": r.get("subject"),
                    "unit": r.get("unit"),
                    "topic": r.get("topic"),
                    "subtopic": r.get("subtopic"),
                    "status": r.get("status", "not_started"),
                    "completed_steps": completed_steps,
                    "attempts_count": r.get("attempts_count", 0),
                    "mastery_score": float(r.get("mastery_score") or 0.0),
                    "last_studied_at": r.get("last_studied_at")
                }
        except Exception as exc:
            logger.debug("[AdaptivePath] SQLite get progress error: %s", exc)

    return progress_map


def save_student_step_completion(
    student_id: str,
    subject: str,
    topic: str,
    step_id: str,
    unit: str = "",
    subtopic: str = "",
    mongo_db: Any = None,
    sqlite_conn: Any = None
) -> Dict[str, Any]:
    """
    Mark a specific learning path step as completed without resetting historical progress.
    """
    clean_id = str(student_id or "").strip()
    now = datetime.now(timezone.utc)

    # Fetch existing record
    existing = get_student_topic_progress(clean_id, mongo_db, sqlite_conn).get(f"{subject}::{topic}")
    completed_steps = list(existing.get("completed_steps", [])) if existing else []
    if step_id not in completed_steps:
        completed_steps.append(step_id)

    status = "in_progress"
    if len(completed_steps) >= 5:
        status = "mastered"

    if mongo_db is not None:
        try:
            mongo_db["blind_topic_progress"].update_one(
                {"student_id": clean_id, "subject": subject, "topic": topic},
                {"$set": {
                    "student_id": clean_id,
                    "subject": subject,
                    "unit": unit or (existing.get("unit") if existing else ""),
                    "topic": topic,
                    "subtopic": subtopic or topic,
                    "status": status,
                    "completed_steps": completed_steps,
                    "last_studied_at": now.isoformat(),
                    "updated_at": now
                }},
                upsert=True
            )
        except Exception as exc:
            logger.error("[AdaptivePath] Mongo save step completion error: %s", exc)
    elif sqlite_conn is not None:
        try:
            cursor = sqlite_conn.cursor()
            cursor.execute("""
                INSERT INTO blind_topic_progress
                (student_id, subject, unit, topic, subtopic, status, completed_steps, last_studied_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id, subject, topic) DO UPDATE SET
                    status = excluded.status,
                    completed_steps = excluded.completed_steps,
                    last_studied_at = excluded.last_studied_at,
                    updated_at = excluded.updated_at
            """, (
                clean_id, subject, unit or (existing.get("unit") if existing else ""),
                topic, subtopic or topic, status, json.dumps(completed_steps),
                now.isoformat(), now.isoformat()
            ))
            sqlite_conn.commit()
        except Exception as exc:
            logger.error("[AdaptivePath] SQLite save step completion error: %s", exc)

    return {
        "success": True,
        "step_id": step_id,
        "subject": subject,
        "topic": topic,
        "completed_steps": completed_steps,
        "status": status
    }


# ─────────────────────────────────────────────────────────────────────────────
# CORE ADAPTIVE PATH ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def generate_adaptive_learning_path(
    student_id: str,
    student_name: str,
    syllabus_doc: Dict[str, Any] = None,
    mongo_db: Any = None,
    sqlite_conn: Any = None
) -> Dict[str, Any]:
    """
    Intelligent recommendation engine using student's actual syllabus and identified learning gaps.
    Prioritizes:
    1. Prerequisite foundational gaps (prerequisite of a struggled topic).
    2. Confirmed repeated mistakes.
    3. Active learning gaps (Needs more practice).
    4. Demonstrated improvement (re-check / solidify).
    5. Next syllabus learning objective in sequence.
    """
    clean_id = str(student_id or "").strip()

    # 1. Fetch authentic learning gap analysis
    gap_analysis = analyze_student_learning_gaps(
        student_id=clean_id,
        student_name=student_name,
        syllabus_doc=syllabus_doc or {},
        mongo_db=mongo_db,
        sqlite_conn=sqlite_conn
    )
    learning_gaps = gap_analysis.get("learning_gaps", [])
    topic_status_map = gap_analysis.get("topic_status_map", {})

    # 2. Fetch student's durable topic progress
    progress_map = get_student_topic_progress(clean_id, mongo_db, sqlite_conn)

    # 3. Build syllabus catalog
    syllabus_subjects = []
    all_syllabus_topics: List[Dict[str, Any]] = []
    if syllabus_doc and isinstance(syllabus_doc, dict):
        raw_subjects = syllabus_doc.get("subjects") or []
        chapters_dict = syllabus_doc.get("chapters") or syllabus_doc.get("units") or {}

        for s in raw_subjects:
            s_name = s.get("name") if isinstance(s, dict) else str(s)
            if not s_name:
                continue
            syllabus_subjects.append(s_name)
            s_units = chapters_dict.get(s_name) or []
            if isinstance(s_units, list):
                for u in s_units:
                    if isinstance(u, dict):
                        u_name = u.get("name") or u.get("title") or "Unit"
                        concepts = u.get("concepts") or u.get("topics") or []
                        for c in concepts:
                            all_syllabus_topics.append({
                                "subject": s_name,
                                "unit": u_name,
                                "topic": str(c)
                            })
                    elif isinstance(u, str):
                        all_syllabus_topics.append({
                            "subject": s_name,
                            "unit": u,
                            "topic": u
                        })

    # Available topic names per subject
    subject_topics: Dict[str, List[str]] = {}
    for item in all_syllabus_topics:
        s = item["subject"]
        if s not in subject_topics:
            subject_topics[s] = []
        if item["topic"] not in subject_topics[s]:
            subject_topics[s].append(item["topic"])

    # 4. Map Gaps by topic
    gaps_by_topic: Dict[str, List[Dict[str, Any]]] = {}
    for g in learning_gaps:
        k = f"{g['subject']}::{g['topic']}"
        if k not in gaps_by_topic:
            gaps_by_topic[k] = []
        gaps_by_topic[k].append(g)

    # 5. Determine Topic Priorities with Prerequisite Blocker Detection
    # Priority buckets:
    # Bucket 1: Prerequisite Foundational Topics blocking struggled topics
    # Bucket 2: Confirmed Repeated Difficulties
    # Bucket 3: Single Gaps (Needs More Practice)
    # Bucket 4: Topics In Progress / Demonstrated Improvement
    # Bucket 5: Next Unstarted Syllabus Topic
    priority_queue: List[Dict[str, Any]] = []

    # Check for prerequisite blockers
    prereq_blockers_assigned = set()
    for k, gaps in gaps_by_topic.items():
        s_name, t_name = k.split("::", 1)
        available = subject_topics.get(s_name, [])
        prereqs = find_prerequisite_topics(t_name, available)

        for pr in prereqs:
            pr_key = f"{s_name}::{pr}"
            pr_status = topic_status_map.get(pr_key, TOPIC_STATUS["NOT_STARTED"])
            # If prerequisite has gaps or is not mastered, prioritize prerequisite first!
            if pr_status != TOPIC_STATUS["UNDERSTANDING_DEMONSTRATED"] and pr_key not in prereq_blockers_assigned:
                prereq_blockers_assigned.add(pr_key)
                unit_name = next((x["unit"] for x in all_syllabus_topics if x["subject"] == s_name and x["topic"] == pr), "Core Unit")
                priority_queue.append({
                    "subject": s_name,
                    "unit": unit_name,
                    "topic": pr,
                    "reason_type": "prerequisite_blocker",
                    "blocks_topic": t_name,
                    "associated_gaps": gaps,
                    "score_weight": 100,  # Highest priority
                    "current_status": pr_status
                })

    # Add topics with confirmed repeated mistakes
    for k, gaps in gaps_by_topic.items():
        s_name, t_name = k.split("::", 1)
        if any(g.get("evidence_strength") == EVIDENCE_STRENGTH["CONFIRMED_REPEATED"] for g in gaps):
            if not any(pq["subject"] == s_name and pq["topic"] == t_name for pq in priority_queue):
                unit_name = next((x["unit"] for x in all_syllabus_topics if x["subject"] == s_name and x["topic"] == t_name), "Unit")
                priority_queue.append({
                    "subject": s_name,
                    "unit": unit_name,
                    "topic": t_name,
                    "reason_type": "confirmed_repeated_gap",
                    "associated_gaps": gaps,
                    "score_weight": 85,
                    "current_status": topic_status_map.get(k, TOPIC_STATUS["NEEDS_PRACTICE"])
                })

    # Add other topics with learning gaps
    for k, gaps in gaps_by_topic.items():
        s_name, t_name = k.split("::", 1)
        if not any(pq["subject"] == s_name and pq["topic"] == t_name for pq in priority_queue):
            unit_name = next((x["unit"] for x in all_syllabus_topics if x["subject"] == s_name and x["topic"] == t_name), "Unit")
            priority_queue.append({
                "subject": s_name,
                "unit": unit_name,
                "topic": t_name,
                "reason_type": "needs_practice",
                "associated_gaps": gaps,
                "score_weight": 70,
                "current_status": topic_status_map.get(k, TOPIC_STATUS["NEEDS_PRACTICE"])
            })

    # Add in-progress topics
    for k, st in topic_status_map.items():
        if st == TOPIC_STATUS["IN_PROGRESS"]:
            s_name, t_name = k.split("::", 1)
            if not any(pq["subject"] == s_name and pq["topic"] == t_name for pq in priority_queue):
                unit_name = next((x["unit"] for x in all_syllabus_topics if x["subject"] == s_name and x["topic"] == t_name), "Unit")
                priority_queue.append({
                    "subject": s_name,
                    "unit": unit_name,
                    "topic": t_name,
                    "reason_type": "in_progress",
                    "associated_gaps": [],
                    "score_weight": 50,
                    "current_status": st
                })

    # Next un-started syllabus topic
    for item in all_syllabus_topics:
        s_name = item["subject"]
        t_name = item["topic"]
        k = f"{s_name}::{t_name}"
        st = topic_status_map.get(k, TOPIC_STATUS["NOT_STARTED"])
        if st == TOPIC_STATUS["NOT_STARTED"]:
            if not any(pq["subject"] == s_name and pq["topic"] == t_name for pq in priority_queue):
                priority_queue.append({
                    "subject": s_name,
                    "unit": item["unit"],
                    "topic": t_name,
                    "reason_type": "next_syllabus_objective",
                    "associated_gaps": [],
                    "score_weight": 30,
                    "current_status": st
                })
                # Add only first 2 unstarted topics to keep queue focused
                if len([p for p in priority_queue if p["reason_type"] == "next_syllabus_objective"]) >= 2:
                    break

    # If priority queue is completely empty (no syllabus uploaded or all mastered)
    if not priority_queue:
        if all_syllabus_topics:
            first_topic = all_syllabus_topics[0]
            priority_queue.append({
                "subject": first_topic["subject"],
                "unit": first_topic["unit"],
                "topic": first_topic["topic"],
                "reason_type": "next_syllabus_objective",
                "associated_gaps": [],
                "score_weight": 10,
                "current_status": TOPIC_STATUS["NOT_STARTED"]
            })
        else:
            priority_queue.append({
                "subject": "General Academic",
                "unit": "Unit 1: Fundamentals",
                "topic": "Core Foundations",
                "reason_type": "next_syllabus_objective",
                "associated_gaps": [],
                "score_weight": 10,
                "current_status": TOPIC_STATUS["NOT_STARTED"]
            })

    # Sort priority queue by weight descending
    priority_queue.sort(key=lambda x: x["score_weight"], reverse=True)

    # 6. Build Sequenced Steps for the Top Priority Topics
    # We construct a transparent 7-step learning progression grounded in the primary focus topic
    steps: List[Dict[str, Any]] = []
    primary = priority_queue[0]
    p_subject = primary["subject"]
    p_unit = primary["unit"]
    p_topic = primary["topic"]
    p_reason = primary["reason_type"]
    p_gaps = primary["associated_gaps"]
    progress_record = progress_map.get(f"{p_subject}::{p_topic}", {})
    completed_step_ids = set(progress_record.get("completed_steps") or [])

    # Case A: Topic is prioritized because it's a Prerequisite Blocker
    if p_reason == "prerequisite_blocker":
        blocked_topic = primary.get("blocks_topic", "Advanced Concept")
        first_gap = p_gaps[0] if p_gaps else {}
        evidence_desc = (
            f"You attempted '{blocked_topic}' but struggled with '{first_gap.get('mistake_nature', 'the concept')}'. "
            f"'{p_topic}' is the foundational prerequisite required to understand '{blocked_topic}'."
        )

        steps.append({
            "step_id": f"step_{p_topic}_1_prereq",
            "step_number": 1,
            "subject": p_subject,
            "unit": p_unit,
            "topic": p_topic,
            "subtopic": p_topic,
            "step_type": "revise_prerequisite",
            "title": f"Revise Prerequisite: {p_topic}",
            "what_to_study": f"Foundational principles of {p_topic} required before {blocked_topic}",
            "why_recommended": (
                f"Weakness in {blocked_topic} is directly caused by unmastered prerequisite concepts in {p_topic}. "
                f"Mastering this foundation eliminates confusion in advanced derivations."
            ),
            "evidence_basis": evidence_desc,
            "activity_type": "Audio Intuition Walkthrough",
            "activity_description": f"Listen to the Concept Breakdown audio explaining the physical meaning and equations of {p_topic}.",
            "mastery_check": f"Confirm core definitions and governing laws of {p_topic} via audio Q&A.",
            "completed": f"step_{p_topic}_1_prereq" in completed_step_ids
        })

        steps.append({
            "step_id": f"step_{p_topic}_2_breakdown",
            "step_number": 2,
            "subject": p_subject,
            "unit": p_unit,
            "topic": p_topic,
            "subtopic": p_topic,
            "step_type": "concept_breakdown",
            "title": f"Step-by-Step Reasoning on {p_topic}",
            "what_to_study": f"Algebraic and conceptual formulation of {p_topic}",
            "why_recommended": f"Builds the logical bridge between {p_topic} and {blocked_topic}.",
            "evidence_basis": f"Past attempts showed difficulty in formula application and missing reasoning steps.",
            "activity_type": "Audio Step-by-Step Explanation",
            "activity_description": "Follow the audio walkthrough breaking the law into 3 concise mathematical steps.",
            "mastery_check": "Identify correct formula substitution without careless arithmetic slips.",
            "completed": f"step_{p_topic}_2_breakdown" in completed_step_ids
        })

        steps.append({
            "step_id": f"step_{p_topic}_3_example",
            "step_number": 3,
            "subject": p_subject,
            "unit": p_unit,
            "topic": p_topic,
            "subtopic": p_topic,
            "step_type": "guided_example",
            "title": f"Guided Example on {p_topic}",
            "what_to_study": f"Standard numerical or theoretical example of {p_topic}",
            "why_recommended": "Demonstrates how theoretical definitions apply to concrete problem setups.",
            "evidence_basis": "Provides a verified model answer to contrast with past errors.",
            "activity_type": "Guided Audio Example",
            "activity_description": "Listen to the narrator solve a benchmark problem step by step with spoken reasoning.",
            "mastery_check": "Explain the final step and unit verification in your own words.",
            "completed": f"step_{p_topic}_3_example" in completed_step_ids
        })

        steps.append({
            "step_id": f"step_{p_topic}_4_practice",
            "step_number": 4,
            "subject": p_subject,
            "unit": p_unit,
            "topic": p_topic,
            "subtopic": p_topic,
            "step_type": "independent_practice",
            "title": f"Independent Checkpoint on {p_topic}",
            "what_to_study": f"Solve a checkpoint problem on {p_topic}",
            "why_recommended": f"Validates that {p_topic} is truly understood before returning to {blocked_topic}.",
            "evidence_basis": "Requires an authentic student submission to verify gap resolution.",
            "activity_type": "Interactive Audio Checkpoint",
            "activity_description": "Type or speak your answer to the checkpoint question.",
            "mastery_check": "Achieve score >= 80% with no conceptual or formula selection errors.",
            "completed": f"step_{p_topic}_4_practice" in completed_step_ids
        })

        steps.append({
            "step_id": f"step_{blocked_topic}_5_advance",
            "step_number": 5,
            "subject": p_subject,
            "unit": p_unit,
            "topic": blocked_topic,
            "subtopic": blocked_topic,
            "step_type": "next_objective",
            "title": f"Resume Advanced Topic: {blocked_topic}",
            "what_to_study": f"Re-apply mastered foundations of {p_topic} to {blocked_topic}",
            "why_recommended": f"Now that {p_topic} is resolved, you are fully equipped to master {blocked_topic}.",
            "evidence_basis": f"Resolves the original learning gap observed in {blocked_topic}.",
            "activity_type": "Advanced Topic Audio Lesson",
            "activity_description": f"Learn {blocked_topic} using the 10-step structured audio workflow.",
            "mastery_check": f"Successfully solve the question previously answered incorrectly on {blocked_topic}.",
            "completed": f"step_{blocked_topic}_5_advance" in completed_step_ids
        })

    # Case B: Topic has Active Learning Gaps (Confirmed Repeated or Needs Practice)
    elif p_gaps:
        primary_gap = p_gaps[0]
        mistake_nature = primary_gap.get("mistake_nature", MISTAKE_TYPES["CONCEPTUAL_MISUNDERSTANDING"])
        why_gap = primary_gap.get("why_learning_gap", "Demonstrated difficulty in past attempts.")
        q_ref = primary_gap.get("question_ref", "Practice assessment")
        ev_strength = primary_gap.get("evidence_strength", EVIDENCE_STRENGTH["CONFIRMED_REPEATED"])

        steps.append({
            "step_id": f"step_{p_topic}_1_review",
            "step_number": 1,
            "subject": p_subject,
            "unit": p_unit,
            "topic": p_topic,
            "subtopic": primary_gap.get("subtopic") or p_topic,
            "step_type": "concept_breakdown",
            "title": f"Revise Core Meaning: {p_topic}",
            "what_to_study": f"Fundamental conceptual intuition and definition of {p_topic}",
            "why_recommended": (
                f"In your recent attempt on '{q_ref}', you encountered '{mistake_nature}'. "
                f"Revisiting core meaning addresses the underlying root cause."
            ),
            "evidence_basis": f"Evidence strength: {ev_strength}. {why_gap}",
            "activity_type": "Concept Breakdown Audio",
            "activity_description": f"Listen to an intuitive, jargon-free audio explanation of {p_topic}.",
            "mastery_check": "Student can state the primary definition and boundary conditions.",
            "completed": f"step_{p_topic}_1_review" in completed_step_ids
        })

        # Adaptive step depending on mistake nature
        if mistake_nature == MISTAKE_TYPES["CALCULATION_MISTAKE"]:
            step2_title = f"Calculation Verification & Arithmetic Strategy on {p_topic}"
            step2_what = "Intermediate arithmetic checks, signs, and SI unit conversions"
            step2_why = "Your conceptual reasoning is sound, but arithmetic computation caused loss of marks."
            step2_act = "Arithmetic Check Drill"
        elif mistake_nature in [MISTAKE_TYPES["INCORRECT_FORMULA_SELECTION"], MISTAKE_TYPES["INCORRECT_FORMULA_APPLICATION"]]:
            step2_title = f"Formula Selection & Boundary Conditions for {p_topic}"
            step2_what = "When to select this formula vs alternative formulas, and explicit variable substitution"
            step2_why = "Past submission showed substitution into the wrong variable positions."
            step2_act = "Formula Mapping Audio Lesson"
        elif mistake_nature in [MISTAKE_TYPES["DIAGRAM_INTERPRETATION_DIFFICULTY"], MISTAKE_TYPES["GRAPH_UNDERSTANDING_DIFFICULTY"]]:
            step2_title = f"Concept-to-Sense Visual Breakdown: {p_topic}"
            step2_what = "Spatial and component relationships in the schematic or coordinate axes"
            step2_why = "Evidence showed misinterpretation of schematic polarities or graph slopes."
            step2_act = "Concept-to-Sense Audio Navigation"
        else:
            step2_title = f"Step-by-Step Reasoning for {p_topic}"
            step2_what = "Logical progression from fundamental laws to final result"
            step2_why = "Builds structured thinking to prevent conceptual misunderstandings."
            step2_act = "Detailed Subject Explanation"

        steps.append({
            "step_id": f"step_{p_topic}_2_targeted",
            "step_number": 2,
            "subject": p_subject,
            "unit": p_unit,
            "topic": p_topic,
            "subtopic": p_topic,
            "step_type": "guided_example",
            "title": step2_title,
            "what_to_study": step2_what,
            "why_recommended": step2_why,
            "evidence_basis": f"Observed gap: {mistake_nature}. Recommended action: {primary_gap.get('recommended_action')}",
            "activity_type": step2_act,
            "activity_description": "Follow a targeted worked example directly resolving the specific mistake type.",
            "mastery_check": "Verify all intermediate steps with zero skipped reasoning.",
            "completed": f"step_{p_topic}_2_targeted" in completed_step_ids
        })

        steps.append({
            "step_id": f"step_{p_topic}_3_guided",
            "step_number": 3,
            "subject": p_subject,
            "unit": p_unit,
            "topic": p_topic,
            "subtopic": p_topic,
            "step_type": "guided_example",
            "title": f"Solve Guided Examples for {p_topic}",
            "what_to_study": "Practice standard problems with step-by-step guidance",
            "why_recommended": "Reinforces correct problem-solving sequence in a supportive environment.",
            "evidence_basis": "Prepares the student to transition from passive listening to active problem solving.",
            "activity_type": "Interactive Guided Example",
            "activity_description": "Listen to the example prompt and verify each intermediate answer step.",
            "mastery_check": "Identify the critical transformation step without hints.",
            "completed": f"step_{p_topic}_3_guided" in completed_step_ids
        })

        steps.append({
            "step_id": f"step_{p_topic}_4_practice",
            "step_number": 4,
            "subject": p_subject,
            "unit": p_unit,
            "topic": p_topic,
            "subtopic": p_topic,
            "step_type": "independent_practice",
            "title": f"Attempt Independent Practice on {p_topic}",
            "what_to_study": "Unassisted problem solving on a fresh syllabus question",
            "why_recommended": "Proves authentic mastery without relying on guided hints.",
            "evidence_basis": "Directly replaces the previous incorrect attempt with a fresh submission.",
            "activity_type": "Independent Audio Practice",
            "activity_description": "Submit your response in the Practice Checkpoint box.",
            "mastery_check": "Achieve score >= 75% on the practice checkpoint.",
            "completed": f"step_{p_topic}_4_practice" in completed_step_ids
        })

        steps.append({
            "step_id": f"step_{p_topic}_5_mastery",
            "step_number": 5,
            "subject": p_subject,
            "unit": p_unit,
            "topic": p_topic,
            "subtopic": p_topic,
            "step_type": "mastery_assessment",
            "title": f"Complete Short Mastery Assessment on {p_topic}",
            "what_to_study": "Comprehensive concept check covering definition, formula, and application",
            "why_recommended": "Updates syllabus topic status from 'Needs more practice' to 'Understanding demonstrated'.",
            "evidence_basis": "Two consecutive successful attempts are required for verified syllabus mastery.",
            "activity_type": "Self-Evaluation Mastery Check",
            "activity_description": "Complete a 3-question Self-Evaluation assessment.",
            "mastery_check": "Score >= 80% on mastery evaluation.",
            "completed": f"step_{p_topic}_5_mastery" in completed_step_ids
        })

    # Case C: Next Syllabus Learning Objective (No active gaps, continuing syllabus)
    else:
        steps.append({
            "step_id": f"step_{p_topic}_1_intro",
            "step_number": 1,
            "subject": p_subject,
            "unit": p_unit,
            "topic": p_topic,
            "subtopic": p_topic,
            "step_type": "concept_breakdown",
            "title": f"Explore New Syllabus Objective: {p_topic}",
            "what_to_study": f"Introduction and importance of {p_topic} in {p_unit}",
            "why_recommended": (
                f"You have demonstrated solid understanding of foundational prerequisites. "
                f"'{p_topic}' is the next logical objective in your official syllabus."
            ),
            "evidence_basis": "No active learning gaps blocking this unit. Progression is on schedule.",
            "activity_type": "10-Step Structured Audio Lesson",
            "activity_description": f"Listen to the 10-step structured teaching lesson for {p_topic}.",
            "mastery_check": "Recall core concepts and terminology during the lesson check.",
            "completed": f"step_{p_topic}_1_intro" in completed_step_ids
        })

        steps.append({
            "step_id": f"step_{p_topic}_2_reasoning",
            "step_number": 2,
            "subject": p_subject,
            "unit": p_unit,
            "topic": p_topic,
            "subtopic": p_topic,
            "step_type": "concept_breakdown",
            "title": f"Step-by-Step Reasoning & Terminology for {p_topic}",
            "what_to_study": f"Mathematical equations, scientific terminology, and derivation for {p_topic}",
            "why_recommended": "Builds in-depth academic mastery aligned with university examination criteria.",
            "evidence_basis": "Syllabus unit learning objective.",
            "activity_type": "Audio Deep-Dive Explanation",
            "activity_description": "Follow the structured explanation with audio pause controls.",
            "mastery_check": "Explain the step-by-step reasoning behind the governing principle.",
            "completed": f"step_{p_topic}_2_reasoning" in completed_step_ids
        })

        steps.append({
            "step_id": f"step_{p_topic}_3_examples",
            "step_number": 3,
            "subject": p_subject,
            "unit": p_unit,
            "topic": p_topic,
            "subtopic": p_topic,
            "step_type": "guided_example",
            "title": f"Solve Guided Examples for {p_topic}",
            "what_to_study": f"Practical applications and benchmark numerical examples of {p_topic}",
            "why_recommended": "Connects theoretical principles to real-world exam and industry problems.",
            "evidence_basis": "Standard syllabus learning sequence.",
            "activity_type": "Guided Audio Example",
            "activity_description": "Work through a fully explained example step by step.",
            "mastery_check": "Verify final result and units.",
            "completed": f"step_{p_topic}_3_examples" in completed_step_ids
        })

        steps.append({
            "step_id": f"step_{p_topic}_4_practice",
            "step_number": 4,
            "subject": p_subject,
            "unit": p_unit,
            "topic": p_topic,
            "subtopic": p_topic,
            "step_type": "independent_practice",
            "title": f"Attempt Independent Practice on {p_topic}",
            "what_to_study": "Checkpoint questions to test initial retention",
            "why_recommended": "Provides authentic evidence required to validate topic learning.",
            "evidence_basis": "Initial attempt recording for this syllabus topic.",
            "activity_type": "Checkpoint Practice Question",
            "activity_description": "Type or dictate response in the Practice Checkpoint box.",
            "mastery_check": "Score >= 70% to establish baseline competency.",
            "completed": f"step_{p_topic}_4_practice" in completed_step_ids
        })

        steps.append({
            "step_id": f"step_{p_topic}_5_mastery",
            "step_number": 5,
            "subject": p_subject,
            "unit": p_unit,
            "topic": p_topic,
            "subtopic": p_topic,
            "step_type": "mastery_assessment",
            "title": f"Mastery Assessment for {p_topic}",
            "what_to_study": "Comprehensive knowledge challenge or self-evaluation",
            "why_recommended": "Transitions this topic into 'Understanding demonstrated' status.",
            "evidence_basis": "Assessment evidence required for syllabus progression.",
            "activity_type": "Self-Evaluation Assessment",
            "activity_description": "Complete self-evaluation on this topic.",
            "mastery_check": "Achieve score >= 80% to certify understanding.",
            "completed": f"step_{p_topic}_5_mastery" in completed_step_ids
        })

    # 7. Generate Spoken Audio Scripts for Voice Commands (Prompt 4 Requirement 4)
    next_incomplete_step = next((s for s in steps if not s.get("completed")), steps[0])

    # Audio 1: "What should I study next?"
    study_next_audio = (
        f"Your top recommended study priority is {primary['topic']} in {primary['subject']}, "
        f"{primary['unit']}. Currently at {next_incomplete_step['title']}. "
        f"{next_incomplete_step['why_recommended']}"
    )

    # Audio 2: "Why was this topic recommended?"
    why_recommended_audio = (
        f"{primary['topic']} was recommended because: {next_incomplete_step['why_recommended']} "
        f"Evidence: {next_incomplete_step['evidence_basis']} "
        f"Next activity: {next_incomplete_step['activity_description']}"
    )

    # Audio 3: "Show my learning progress."
    mastered_count = sum(1 for st in topic_status_map.values() if st == TOPIC_STATUS["UNDERSTANDING_DEMONSTRATED"])
    struggling_count = sum(1 for st in topic_status_map.values() if st == TOPIC_STATUS["NEEDS_PRACTICE"])
    in_progress_count = sum(1 for st in topic_status_map.values() if st == TOPIC_STATUS["IN_PROGRESS"])
    progress_audio = (
        f"Hello {student_name}. Across your syllabus, {mastered_count} topic{'' if mastered_count == 1 else 's'} "
        f"have demonstrated understanding, {in_progress_count} are in progress, and {struggling_count} "
        f"need more practice. You have completed {len(completed_step_ids)} step{'' if len(completed_step_ids) == 1 else 's'} "
        f"for {p_topic}."
    )

    response_payload = {
        "success": True,
        "student_id": clean_id,
        "student_name": student_name,
        "focus_subject": p_subject,
        "focus_unit": p_unit,
        "focus_topic": p_topic,
        "reason_type": p_reason,
        "priority_score": primary["score_weight"],
        "steps": steps,
        "priority_queue": priority_queue[:5],
        "active_step": next_incomplete_step,
        "completed_count": sum(1 for s in steps if s.get("completed")),
        "total_steps": len(steps),
        "audio_scripts": {
            "study_next": study_next_audio,
            "why_recommended": why_recommended_audio,
            "progress_summary": progress_audio
        }
    }

    # Persist the active learning path to database for durable caching
    if mongo_db is not None:
        try:
            mongo_db["blind_learning_paths"].update_one(
                {"student_id": clean_id},
                {"$set": {
                    "student_id": clean_id,
                    "path_data": response_payload,
                    "updated_at": datetime.now(timezone.utc)
                }},
                upsert=True
            )
        except Exception as exc:
            logger.debug("[AdaptivePath] Mongo save path error: %s", exc)
    elif sqlite_conn is not None:
        try:
            cursor = sqlite_conn.cursor()
            cursor.execute("""
                INSERT INTO blind_learning_paths (student_id, path_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(student_id) DO UPDATE SET
                    path_json = excluded.path_json,
                    updated_at = excluded.updated_at
            """, (clean_id, json.dumps(response_payload), datetime.now(timezone.utc).isoformat()))
            sqlite_conn.commit()
        except Exception as exc:
            logger.debug("[AdaptivePath] SQLite save path error: %s", exc)

    return response_payload


# ─────────────────────────────────────────────────────────────────────────────
# ADAPTIVE TEACHING & AUDIO COMMAND EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def handle_learning_path_command(
    command: str,
    student_id: str,
    student_name: str,
    step_id: Optional[str] = None,
    syllabus_doc: Dict[str, Any] = None,
    mongo_db: Any = None,
    sqlite_conn: Any = None
) -> Dict[str, Any]:
    """
    Process voice commands and interactive adaptive actions:
    - "What should I study next?"
    - "Why was this topic recommended?"
    - "Start learning."
    - "Give me another example."
    - "Show my learning progress."
    """
    cmd = (command or "").strip().lower()
    clean_id = str(student_id or "").strip()

    # Generate current fresh path
    path_data = generate_adaptive_learning_path(
        student_id=clean_id,
        student_name=student_name,
        syllabus_doc=syllabus_doc or {},
        mongo_db=mongo_db,
        sqlite_conn=sqlite_conn
    )
    active_step = path_data.get("active_step") or {}
    audio_scripts = path_data.get("audio_scripts") or {}

    # Command 1: What should I study next?
    if any(q in cmd for q in ["what should i study next", "what to study", "study next", "what_next"]):
        return {
            "success": True,
            "command": "what_should_i_study_next",
            "spoken_response": audio_scripts.get("study_next", ""),
            "active_step": active_step,
            "action": "navigate_to_step"
        }

    # Command 2: Why was this topic recommended?
    if any(q in cmd for q in ["why was this topic recommended", "why recommended", "why this topic", "why_recommended"]):
        return {
            "success": True,
            "command": "why_was_this_topic_recommended",
            "spoken_response": audio_scripts.get("why_recommended", ""),
            "active_step": active_step,
            "action": "explain_transparency"
        }

    # Command 3: Show my learning progress.
    if any(q in cmd for q in ["show my learning progress", "my progress", "learning progress", "show_progress"]):
        return {
            "success": True,
            "command": "show_my_learning_progress",
            "spoken_response": audio_scripts.get("progress_summary", ""),
            "progress_stats": {
                "completed_steps": path_data.get("completed_count", 0),
                "total_steps": path_data.get("total_steps", 0),
                "priority_queue": path_data.get("priority_queue", [])
            },
            "action": "display_progress"
        }

    # Command 4: Start learning.
    if any(q in cmd for q in ["start learning", "start", "begin", "start_learning"]):
        step_type = active_step.get("step_type", "concept_breakdown")
        suggested_mode = "simple"
        if step_type == "revise_prerequisite":
            suggested_mode = "simple"
        elif step_type == "concept_breakdown":
            suggested_mode = "structured_10_step"
        elif step_type == "guided_example":
            suggested_mode = "detailed"
        elif step_type == "mastery_assessment":
            suggested_mode = "quick_revision"

        spoken_msg = (
            f"Starting {active_step.get('title', 'your recommended step')}. "
            f"Loading {active_step.get('topic')} from {active_step.get('subject')} in {suggested_mode} mode."
        )
        return {
            "success": True,
            "command": "start_learning",
            "spoken_response": spoken_msg,
            "active_step": active_step,
            "suggested_teaching_mode": suggested_mode,
            "action": "load_lesson"
        }

    # Command 5: Give me another example (Adaptive Struggle Intervention)
    if any(q in cmd for q in ["give me another example", "another example", "more examples", "another_example"]):
        topic = active_step.get("topic") or path_data.get("focus_topic", "Current Topic")
        subject = active_step.get("subject") or path_data.get("focus_subject", "Academic")

        example_content = generate_adaptive_worked_example(
            topic=topic,
            subject=subject,
            step_title=active_step.get("title", "")
        )
        return {
            "success": True,
            "command": "give_me_another_example",
            "spoken_response": (
                f"Here is another worked example for {topic}. "
                f"{example_content['spoken_narrative']}"
            ),
            "example": example_content,
            "action": "display_example"
        }

    # Default fallback
    return {
        "success": True,
        "command": "unknown",
        "spoken_response": (
            "I can answer: 'What should I study next?', 'Why was this topic recommended?', "
            "'Start learning', 'Give me another example', or 'Show my learning progress'."
        ),
        "available_commands": [
            "What should I study next?",
            "Why was this topic recommended?",
            "Start learning.",
            "Give me another example.",
            "Show my learning progress."
        ]
    }


def generate_adaptive_worked_example(
    topic: str,
    subject: str,
    step_title: str = ""
) -> Dict[str, Any]:
    """
    Generate a concrete, audio-friendly worked example tailored to the student's struggle topic.
    Breaks down step-by-step reasoning and shows intermediate calculation/verification.
    """
    t_lower = topic.lower()

    if "thevenin" in t_lower or "circuit" in t_lower:
        problem = "A 24 Volt DC source is connected across a series combination of a 40 Ohm and a 60 Ohm resistor. Find the Thevenin voltage and equivalent resistance across the 60 Ohm resistor."
        steps = [
            "Step 1: Identify load terminals. The 60 Ohm resistor is our target load.",
            "Step 2: Find Thevenin Voltage Vth. Open-circuit the load resistor. Using voltage division: Vth = 24 Volts times (60 / (40 + 60)) = 24 times 0.6 = 14.4 Volts.",
            "Step 3: Find Thevenin Resistance Rth. Deactivate the 24V independent voltage source by replacing it with a short circuit.",
            "Step 4: Looking back from load terminals, 40 Ohms and 60 Ohms appear in parallel: Rth = (40 times 60) / (40 + 60) = 2400 / 100 = 24 Ohms.",
            "Step 5: Final Verification. The equivalent circuit is a 14.4 Volt independent DC voltage source in series with a 24 Ohm internal resistor."
        ]
        spoken = (
            "Problem: Find Thevenin voltage and resistance for a 24-volt source connected across a 40-ohm and 60-ohm divider. "
            "First, find Vth using voltage division: 24 times 60 divided by 100 equals 14.4 volts. "
            "Next, find Rth by shorting the source. 40 ohms in parallel with 60 ohms equals 2400 divided by 100, which is 24 ohms. "
            "The Thevenin equivalent is 14.4 volts in series with 24 ohms."
        )
    elif "differentiation" in t_lower or "calculus" in t_lower or "chain rule" in t_lower:
        problem = "Differentiate the composite function y = (3x^2 + 5)^4 with respect to x."
        steps = [
            "Step 1: Recognize outer and inner functions. Outer function is u^4 where u = 3x^2 + 5.",
            "Step 2: Differentiate outer function with respect to u: d/du (u^4) = 4u^3.",
            "Step 3: Differentiate inner function with respect to x: d/dx (3x^2 + 5) = 6x.",
            "Step 4: Apply Chain Rule: dy/dx = (d/du) times (du/dx) = 4(3x^2 + 5)^3 times (6x).",
            "Step 5: Multiply algebraic coefficients: dy/dx = 24x(3x^2 + 5)^3."
        ]
        spoken = (
            "Problem: Differentiate y equals (3x squared plus 5) raised to the 4th power. "
            "By the chain rule, first differentiate the outer power: 4 times (3x squared plus 5) cubed. "
            "Then multiply by the derivative of the inside, which is 6x. "
            "Multiplying 4 by 6x gives the final answer: 24x times (3x squared plus 5) cubed."
        )
    else:
        problem = f"Standard benchmark problem applying the principles of {topic} in {subject}."
        steps = [
            f"Step 1: State the governing definition and boundary constraints of {topic}.",
            "Step 2: Substitute explicit numerical given quantities with consistent SI units.",
            "Step 3: Solve algebraic intermediate terms step-by-step to prevent calculation slips.",
            "Step 4: Verify the result against standard physical laws."
        ]
        spoken = (
            f"Here is a guided walkthrough for {topic}. First, state the governing boundary conditions. "
            f"Second, substitute the known quantities with SI units. "
            f"Third, calculate intermediate steps carefully without skipping arithmetic. "
            f"Finally, check that the dimensions and units match your expected outcome."
        )

    return {
        "topic": topic,
        "subject": subject,
        "problem_statement": problem,
        "worked_steps": steps,
        "spoken_narrative": spoken
    }

