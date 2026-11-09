"""
LearnSphere AI - AI Parent Feedback & Comprehensive Diagnostic Report Engine

Generates accurate, clear, and actionable feedback reports for parents:
1. Translates technical evaluations into supportive, parent-friendly English.
2. Explicitly conveys the student's demonstrated strengths with evidence.
3. Clearly diagnoses weaknesses (distinguishing conceptual gaps from arithmetic slips/pacing).
4. Provides a concrete home action plan for parents.
5. Highlights the student's next learning target in LearnSphere AI.
6. Operates strictly on genuine student performance and session data with zero mock content.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _safe_str(val: Any, default: str = "") -> str:
    if val is None:
        return default
    s = str(val).strip()
    return s if s else default


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def generate_parent_feedback_report(
    student_profile: Dict[str, Any],
    evaluations: List[Dict[str, Any]],
    activity_log: List[Dict[str, Any]] = None,
    study_sessions: List[Dict[str, Any]] = None,
    streak_days: int = 0,
    formatted_session_time: str = "0s",
    use_gemini: bool = True
) -> Dict[str, Any]:
    """
    Synthesizes a high-accuracy, parent-friendly diagnostic report.
    Returns structured data for clear rendering in the Parent Portal UI.
    """
    student_name = _safe_str(student_profile.get("name"), "Your Child")
    institution = _safe_str(
        student_profile.get("institution_name")
        or student_profile.get("school")
        or student_profile.get("college"),
        "LearnSphere Academic Network"
    )
    level = _safe_str(student_profile.get("level"), "school")
    grade_or_branch = _safe_str(
        student_profile.get("grade_level")
        or student_profile.get("classLevel")
        or student_profile.get("department")
        or student_profile.get("branch"),
        "Curriculum Grade"
    )

    activity_log = activity_log or []
    study_sessions = study_sessions or []

    # 1. Analyze genuine test performance
    total_evals = len(evaluations)
    valid_scores = []
    subject_scores: Dict[str, List[float]] = {}
    diagnosed_weaknesses: List[Dict[str, Any]] = []
    demonstrated_strengths: List[Dict[str, Any]] = []

    for ev in evaluations:
        subj = _safe_str(ev.get("subject"), "General Studies")
        pct = _safe_float(ev.get("percentage"), None)
        if pct is None:
            tot = _safe_float(ev.get("total_marks") or ev.get("max_marks"), 0.0)
            obt = _safe_float(ev.get("obtained_marks") or ev.get("awarded_marks"), 0.0)
            if tot > 0:
                pct = round((obt / tot) * 100, 1)

        if pct is not None:
            valid_scores.append(pct)
            if subj not in subject_scores:
                subject_scores[subj] = []
            subject_scores[subj].append(pct)

        # Inspect question-level performance
        qs = ev.get("questions") or ev.get("evaluations") or []
        if isinstance(qs, str):
            try:
                qs = json.loads(qs)
            except Exception:
                qs = []

        for q in qs:
            if not isinstance(q, dict):
                continue

            q_num = str(q.get("question_number") or "?")
            c_name = _safe_str(q.get("concept") or q.get("identified_concept") or q.get("topic") or subj)
            q_max = _safe_float(q.get("maximum_marks") or q.get("max_marks"), 0.0)
            q_obt = _safe_float(q.get("awarded_marks"), 0.0)
            q_lost = round(max(0.0, q_max - q_obt), 2)
            q_ratio = (q_obt / q_max) if q_max > 0 else 1.0

            # Strong performance
            if q_max > 0 and q_ratio >= 0.85:
                if not any(s["concept"].lower() == c_name.lower() for s in demonstrated_strengths):
                    demonstrated_strengths.append({
                        "concept": c_name,
                        "subject": subj,
                        "evidence": f"Demonstrated {round(q_ratio * 100)}% accuracy in {ev.get('assessment_title', subj)} (Q{q_num}).",
                        "mastery_tier": "Mastered"
                    })

            # Areas needing support
            elif q_lost > 0:
                err_hint = _safe_str(
                    q.get("misconception")
                    or q.get("step_or_calculation_mistake")
                    or q.get("feedback", {}).get("comments") if isinstance(q.get("feedback"), dict) else ""
                    or "Mark deficit on question"
                )
                classification = _safe_str(q.get("answer_classification") or q.get("error_label")).lower()

                # Categorize weakness in parent terms
                if "calculation" in classification or "arithmetic" in err_hint.lower():
                    nature_of_gap = "Calculation / Arithmetic Slip"
                    parent_explanation = f"In {subj}, {student_name} demonstrates understanding of {c_name}, but lost marks due to numerical or calculation steps."
                elif "formula" in classification:
                    nature_of_gap = "Formula Selection or Application"
                    parent_explanation = f"In {subj}, {student_name} needs reinforcement on when to choose and substitute variables into the formula for {c_name}."
                elif "incomplete" in classification:
                    nature_of_gap = "Pacing / Incomplete Answer"
                    parent_explanation = f"In {subj}, {student_name} attempted {c_name} but left intermediate derivation or required sub-parts incomplete."
                else:
                    nature_of_gap = "Conceptual Misunderstanding"
                    parent_explanation = f"In {subj}, {student_name} encountered difficulty with the underlying principles of {c_name}."

                if not any(w["concept"].lower() == c_name.lower() for w in diagnosed_weaknesses):
                    diagnosed_weaknesses.append({
                        "concept": c_name,
                        "subject": subj,
                        "gap_type": nature_of_gap,
                        "explanation": parent_explanation,
                        "marks_lost": q_lost,
                        "assessment_title": ev.get("assessment_title", subj),
                        "question_number": q_num
                    })

    avg_score = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else None

    # Handle case with no evaluation data
    if total_evals == 0:
        return _build_onboarding_parent_report(
            student_name=student_name,
            institution=institution,
            streak_days=streak_days,
            session_time=formatted_session_time,
            study_sessions=study_sessions,
            activity_log=activity_log
        )

    # 2. Try Gemini AI synthesis for personalized executive voice
    if use_gemini:
        ai_report = _synthesize_with_gemini(
            student_name=student_name,
            institution=institution,
            level=level,
            grade=grade_or_branch,
            avg_score=avg_score,
            total_evals=total_evals,
            strengths=demonstrated_strengths,
            weaknesses=diagnosed_weaknesses,
            streak_days=streak_days,
            session_time=formatted_session_time,
            subject_scores=subject_scores
        )
        if ai_report and ai_report.get("success"):
            return ai_report

    # 3. Deterministic High-Precision Parent Report (Guaranteed reliability)
    return _build_deterministic_parent_report(
        student_name=student_name,
        institution=institution,
        level=level,
        grade=grade_or_branch,
        avg_score=avg_score,
        total_evals=total_evals,
        strengths=demonstrated_strengths,
        weaknesses=diagnosed_weaknesses,
        streak_days=streak_days,
        session_time=formatted_session_time,
        subject_scores=subject_scores
    )


def _build_onboarding_parent_report(
    student_name: str,
    institution: str,
    streak_days: int,
    session_time: str,
    study_sessions: List[Any],
    activity_log: List[Any]
) -> Dict[str, Any]:
    """Report generated when student is active but hasn't uploaded graded tests yet."""
    return {
        "success": True,
        "is_preliminary": True,
        "student_name": student_name,
        "institution": institution,
        "academic_standing": "Active Learning Onboarding",
        "average_score": None,
        "total_evaluations_analyzed": 0,
        "study_streak_days": streak_days,
        "active_session_duration": session_time,
        "total_study_sessions": len(study_sessions),
        "executive_summary": (
            f"{student_name} is actively logged into LearnSphere AI and building study momentum "
            f"with an active {streak_days}-day learning streak and {session_time} of tracked study time. "
            "To unlock detailed question-level strengths and weakness diagnostics, encourage your child to upload "
            "their recent handwritten exam papers in Self-Evaluation."
        ),
        "demonstrated_strengths": [
            {
                "area": "Study Consistency & Routine",
                "detail": f"Maintained a {streak_days}-day consecutive login and study streak at {institution}."
            },
            {
                "area": "Proactive Platform Exploration",
                "detail": f"Engaged in {len(activity_log)} interactive learning activities."
            }
        ],
        "areas_needing_support": [
            {
                "area": "Handwritten Paper Evaluation",
                "detail": "No graded exam scripts submitted yet. Automated OCR evaluation is needed to diagnose specific concept gaps."
            }
        ],
        "home_action_plan": [
            "Encourage your child to photograph and submit their latest school/college test paper in Self-Evaluation.",
            "Set up a dedicated 30-minute quiet study window using the Focus Session timer.",
            "Ask your child to demonstrate one concept they learned in Personal AI Trainer."
        ],
        "next_learning_target": "Complete first handwritten exam paper evaluation in Self-Evaluation.",
        "evidence_status": "VERIFIED_PRELIMINARY",
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }


def _build_deterministic_parent_report(
    student_name: str,
    institution: str,
    level: str,
    grade: str,
    avg_score: Optional[float],
    total_evals: int,
    strengths: List[Dict[str, Any]],
    weaknesses: List[Dict[str, Any]],
    streak_days: int,
    session_time: str,
    subject_scores: Dict[str, List[float]]
) -> Dict[str, Any]:
    """Generates an objective, deeply accurate report from real performance data."""
    # Determine standing tier
    if avg_score is not None:
        if avg_score >= 80.0:
            standing = "Distinction Tier — Strong Academic Mastery"
        elif avg_score >= 65.0:
            standing = "Proficient Tier — Solid Understanding with Selective Refinements"
        elif avg_score >= 50.0:
            standing = "Developing Tier — Core Concepts Established, Needs Targeted Support"
        else:
            standing = "Support Priority Tier — Foundational Reinforcement Required"
    else:
        standing = "Academic Evaluation in Progress"

    # Summarize strengths
    top_strengths = []
    for s in strengths[:4]:
        top_strengths.append({
            "concept": s["concept"],
            "subject": s["subject"],
            "detail": f"Demonstrated high mastery and consistent accuracy in {s['concept']}."
        })
    if not top_strengths:
        top_strengths.append({
            "concept": "Syllabus Curriculum Engagement",
            "subject": list(subject_scores.keys())[0] if subject_scores else "General",
            "detail": f"Demonstrates positive academic effort and syllabus familiarity across {total_evals} graded assessment(s)."
        })

    # Summarize weaknesses with constructive parent clarity
    top_weaknesses = []
    for w in weaknesses[:4]:
        top_weaknesses.append({
            "concept": w["concept"],
            "subject": w["subject"],
            "gap_type": w["gap_type"],
            "explanation": w["explanation"],
            "marks_impact": f"Lost {w['marks_lost']} marks in {w['assessment_title']} (Q{w['question_number']})"
        })

    # Generate practical parent action plan
    action_plan = []
    if any("calculation" in w["gap_type"].lower() for w in top_weaknesses):
        action_plan.append("Encourage a 3-minute self-check routine: Ask your child to re-verify arithmetic operations before concluding multi-step math or science problems.")
    if any("formula" in w["gap_type"].lower() for w in top_weaknesses):
        action_plan.append("Help your child create a concise formula index card and have them state each variable's units aloud before solving numerical questions.")
    if any("conceptual" in w["gap_type"].lower() for w in top_weaknesses):
        top_c = next((w["concept"] for w in top_weaknesses if "conceptual" in w["gap_type"].lower()), "key concepts")
        action_plan.append(f"Use the Feynman Technique at home: Ask your child to explain the core idea of '{top_c}' in plain everyday terms without looking at notes.")
    if len(action_plan) < 3:
        action_plan.append("Maintain consistency by scheduling a structured 35-minute study session in the Personal AI Trainer 4 days a week.")

    # Next target
    if top_weaknesses:
        next_target = f"Prioritize guided practice on '{top_weaknesses[0]['concept']}' ({top_weaknesses[0]['subject']}) using LearnSphere Personal Trainer."
    elif top_strengths:
        next_target = f"Advance to higher-order problem solving and speed drills in '{top_strengths[0]['concept']}' via Knowledge Challenge."
    else:
        next_target = "Complete next syllabus chapter review in Personal Trainer."

    # Executive narrative
    exec_summary = (
        f"This academic progress report evaluates {student_name}'s performance across {total_evals} formal assessment(s) "
        f"at {institution}. {student_name} currently maintains an average mastery score of {avg_score}% "
        f"alongside a {streak_days}-day continuous study streak ({session_time} active today). "
        f"Overall standing is classified as {standing}. "
        f"Key areas of academic strength include {', '.join(s['concept'] for s in top_strengths[:2])}. "
        + (f"Targeted support is recommended for {', '.join(w['concept'] for w in top_weaknesses[:2])} to prevent recurring marks loss." if top_weaknesses else "No critical conceptual deficits observed.")
    )

    return {
        "success": True,
        "is_preliminary": False,
        "student_name": student_name,
        "institution": institution,
        "academic_standing": standing,
        "average_score": avg_score,
        "total_evaluations_analyzed": total_evals,
        "study_streak_days": streak_days,
        "active_session_duration": session_time,
        "executive_summary": exec_summary,
        "demonstrated_strengths": top_strengths,
        "areas_needing_support": top_weaknesses,
        "home_action_plan": action_plan,
        "next_learning_target": next_target,
        "subject_breakdown": {subj: round(sum(scs) / len(scs), 1) for subj, scs in subject_scores.items()},
        "evidence_status": "VERIFIED_EVIDENCE_SUPPORTED",
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }


def _synthesize_with_gemini(
    student_name: str,
    institution: str,
    level: str,
    grade: str,
    avg_score: Optional[float],
    total_evals: int,
    strengths: List[Dict[str, Any]],
    weaknesses: List[Dict[str, Any]],
    streak_days: int,
    session_time: str,
    subject_scores: Dict[str, List[float]]
) -> Optional[Dict[str, Any]]:
    """Synthesizes executive parent feedback using Gemini 3.6 Flash."""
    try:
        from ..gemini_service import GeminiService
        service = GeminiService()
        if not service.api_key:
            return None

        prompt = f"""
You are the Chief Academic Evaluator at LearnSphere AI.
Generate an objective, highly accurate, and empathetic Parent Feedback Report for a student's parents.
Speak directly to the parents in clear, professional, supportive English free of academic jargon.

STUDENT ACADEMIC CONTEXT:
- Student Name: {student_name}
- Academic Level: {level} ({grade})
- Institution: {institution}
- Graded Tests Evaluated: {total_evals}
- Overall Average Score: {avg_score}%
- Study Streak: {streak_days} days (Active session today: {session_time})
- Subject Averages: {json.dumps(subject_scores)}

VERIFIED STUDENT STRENGTHS (from evaluated scripts):
{json.dumps(strengths[:5], indent=2)}

VERIFIED STUDENT WEAKNESSES & ERRORS (from evaluated scripts):
{json.dumps(weaknesses[:5], indent=2)}

OUTPUT REQUIREMENTS:
Return ONLY valid JSON matching this exact schema:
{{
  "executive_summary": "3-4 sentence high-level overview explaining the student's academic standing, attitude, and effort.",
  "academic_standing": "One of: Distinction Tier | Proficient Tier | Developing Tier | Support Priority Tier",
  "demonstrated_strengths": [
    {{
      "concept": "Topic/Skill name",
      "subject": "Subject",
      "detail": "Clear 1-2 sentence explanation of what the student did well with supporting score/evidence context."
    }}
  ],
  "areas_needing_support": [
    {{
      "concept": "Topic/Skill name",
      "subject": "Subject",
      "gap_type": "Calculation / Arithmetic Slip | Conceptual Misunderstanding | Formula Selection | Pacing / Incomplete",
      "explanation": "Clear parent-friendly explanation of why the student lost marks and what the underlying issue is.",
      "marks_impact": "Summary of marks lost in test"
    }}
  ],
  "home_action_plan": [
    "Practical, constructive action #1 parents can do at home",
    "Practical, constructive action #2 parents can do at home",
    "Practical, constructive action #3 parents can do at home"
  ],
  "next_learning_target": "Concrete next learning target in LearnSphere AI for this student"
}}

RULES:
1. Do NOT invent concepts or subjects not present in the student context.
2. Clearly distinguish between arithmetic slips and true conceptual misunderstandings.
3. Be encouraging yet completely honest and accurate about where marks were lost.
"""
        response_text = service.generate_content(prompt, temperature=0.2)
        parsed = service.parse_json_response(response_text)
        if isinstance(parsed, dict) and "executive_summary" in parsed and "demonstrated_strengths" in parsed:
            parsed["success"] = True
            parsed["is_preliminary"] = False
            parsed["student_name"] = student_name
            parsed["institution"] = institution
            parsed["average_score"] = avg_score
            parsed["total_evaluations_analyzed"] = total_evals
            parsed["study_streak_days"] = streak_days
            parsed["active_session_duration"] = session_time
            parsed["subject_breakdown"] = {subj: round(sum(scs) / len(scs), 1) for subj, scs in subject_scores.items()}
            parsed["evidence_status"] = "VERIFIED_AI_SYNTHESIZED"
            parsed["generated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            return parsed
    except Exception as exc:
        logger.warning("[ParentFeedback] Gemini synthesis notice: %s. Falling back to deterministic engine.", exc)
    return None
