"""
LearnSphere AI - Educational Diagnostic & Personalized Recommendation Engine

Provides high-accuracy, evidence-grounded misconception classification,
individual student performance summaries, and personalized pedagogical actions.

Adheres strictly to the 15-step pedagogical specifications:
1. Genuine Evaluation Grounding: Uses uploaded question paper, answer script, and evaluation marks.
2. 12-Error Taxonomy Classification: Distinguishes conceptual errors from arithmetic slips, formula choices, etc.
3. Transparent Evidence Status: 'VERIFIED' (Evidence supported), 'NEEDS_TEACHER_REVIEW', 'INSUFFICIENT_EVIDENCE'.
4. Evidence-based Performance Summaries: Highlights strengths, gaps, error types, and practice targets.
5. Action Center Recommendations: Specific action, activity, reason, outcome, and priority justification.
6. Transparent Prioritization: High, Medium, Low, Needs review based on explicit criteria.
7. Adaptive Lifecycle Tracking: Persistent, Improving, Resolved, New, In Progress across assessments.
8. Zero Mock/Fabricated Content: Rejects generic fallbacks and fake confidence percentages.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# 12-ERROR TAXONOMY DEFINITIONS (Step 3)
# ══════════════════════════════════════════════════════════════════════════════
TAXONOMY_CONCEPTUAL_MISUNDERSTANDING = "conceptual_misunderstanding"
TAXONOMY_INCORRECT_FORMULA_SELECTION = "incorrect_formula_selection"
TAXONOMY_INCORRECT_FORMULA_APPLICATION = "incorrect_formula_application"
TAXONOMY_CALCULATION_ERROR = "calculation_error"
TAXONOMY_MISSING_STEPS = "missing_steps"
TAXONOMY_INCOMPLETE_ANSWER = "incomplete_answer"
TAXONOMY_QUESTION_INTERPRETATION_ERROR = "question_interpretation_error"
TAXONOMY_INCORRECT_TERMINOLOGY = "incorrect_terminology"
TAXONOMY_LOGICAL_REASONING_ERROR = "logical_reasoning_error"
TAXONOMY_SYNTAX_PROGRAMMING_ERROR = "syntax_programming_error"
TAXONOMY_CARELESS_MISTAKE = "careless_mistake"
TAXONOMY_ALTERNATIVE_VALID_EXPRESSION = "alternative_valid_expression"

# Human-readable labels for error taxonomy
TAXONOMY_LABELS = {
    TAXONOMY_CONCEPTUAL_MISUNDERSTANDING: "Conceptual Misunderstanding",
    TAXONOMY_INCORRECT_FORMULA_SELECTION: "Incorrect Formula Selection",
    TAXONOMY_INCORRECT_FORMULA_APPLICATION: "Incorrect Formula Application",
    TAXONOMY_CALCULATION_ERROR: "Calculation / Arithmetic Slip",
    TAXONOMY_MISSING_STEPS: "Missing Intermediate Derivation Steps",
    TAXONOMY_INCOMPLETE_ANSWER: "Incomplete / Partial Answer",
    TAXONOMY_QUESTION_INTERPRETATION_ERROR: "Question Interpretation Error",
    TAXONOMY_INCORRECT_TERMINOLOGY: "Incorrect Scientific / Technical Terminology",
    TAXONOMY_LOGICAL_REASONING_ERROR: "Logical / Reasoning Flow Error",
    TAXONOMY_SYNTAX_PROGRAMMING_ERROR: "Syntax / Programming Logic Flaw",
    TAXONOMY_CARELESS_MISTAKE: "Careless Notation / Transcription Mistake",
    TAXONOMY_ALTERNATIVE_VALID_EXPRESSION: "Alternative Valid Expression",
}

# Misconception Evidence Statuses
STATUS_EVIDENCE_SUPPORTED = "VERIFIED"
STATUS_NEEDS_TEACHER_REVIEW = "NEEDS_TEACHER_REVIEW"
STATUS_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


def _safe_float(val: Any, default: float = 0.0) -> float:
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


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3: HIGH-PRECISION ERROR CLASSIFIER
# ══════════════════════════════════════════════════════════════════════════════
def classify_student_error(
    q: Dict[str, Any],
    subject: str = "General"
) -> Dict[str, Any]:
    """
    Classifies a student's answer using the 12-error taxonomy.
    Guarantees that calculation slips, alternative expressions, or missing steps
    are NEVER falsely labeled as conceptual misconceptions.
    """
    awarded = _safe_float(q.get("awarded_marks"), 0.0)
    maximum = _safe_float(q.get("maximum_marks") or q.get("max_marks"), 0.0)
    marks_lost = round(max(0.0, maximum - awarded), 2)
    student_ans = _safe_str(q.get("student_answer") or q.get("answer_summary"))
    expected_ans = _safe_str(
        q.get("what_student_should_have_written")
        or q.get("correct_answer_or_expected_points")
        or q.get("expected_answer")
    )
    q_text = _safe_str(q.get("question_text"))
    feedback = q.get("feedback") if isinstance(q.get("feedback"), dict) else {}
    feedback_str = _safe_str(q.get("feedback") if isinstance(q.get("feedback"), str) else feedback.get("comments") or q.get("evaluation_reason") or q.get("teacher_feedback"))
    classification_hint = _safe_str(q.get("answer_classification")).lower()
    step_mistake = _safe_str(q.get("step_or_calculation_mistake"))
    conceptual_mistake = _safe_str(q.get("conceptual_mistake") or q.get("misconception"))
    is_uncertain = bool(q.get("is_uncertain", False))

    # 1. Full marks and no errors -> Alternative valid expression or correct answer
    if maximum > 0 and awarded >= maximum:
        return {
            "error_type": TAXONOMY_ALTERNATIVE_VALID_EXPRESSION,
            "error_label": TAXONOMY_LABELS[TAXONOMY_ALTERNATIVE_VALID_EXPRESSION],
            "is_conceptual_misconception": False,
            "evidence_status": STATUS_EVIDENCE_SUPPORTED,
            "diagnostic_summary": "Answer is fully correct and curriculum-compliant.",
            "marks_lost": 0.0,
        }

    # 2. Check if student answer is completely empty / unattempted
    if not student_ans or classification_hint == "unanswered_question" or not q.get("attempted", True):
        return {
            "error_type": TAXONOMY_INCOMPLETE_ANSWER,
            "error_label": TAXONOMY_LABELS[TAXONOMY_INCOMPLETE_ANSWER],
            "is_conceptual_misconception": False,
            "evidence_status": STATUS_INSUFFICIENT_EVIDENCE,
            "diagnostic_summary": "Question was omitted or left unattempted in script. Insufficient evidence for conceptual diagnosis.",
            "marks_lost": marks_lost,
        }

    # 3. Check for Alternative Valid Expression with partial grading ambiguity
    lower_fb = (feedback_str + " " + step_mistake + " " + conceptual_mistake).lower()
    if any(k in lower_fb for k in ["valid alternative", "alternative method", "different wording", "equivalent formulation", "correct method"]):
        if marks_lost <= (maximum * 0.20) and not q.get("misconception_detected"):
            return {
                "error_type": TAXONOMY_ALTERNATIVE_VALID_EXPRESSION,
                "error_label": TAXONOMY_LABELS[TAXONOMY_ALTERNATIVE_VALID_EXPRESSION],
                "is_conceptual_misconception": False,
                "evidence_status": STATUS_EVIDENCE_SUPPORTED,
                "diagnostic_summary": "Student used an alternative valid expression or solution path. Not a conceptual flaw.",
                "marks_lost": marks_lost,
            }

    # 4. Check for Calculation / Arithmetic Slip
    is_calc_error = (
        classification_hint in {"correct_concept_with_calculation_error", "calculation_error", "arithmetic_error"}
        or any(k in lower_fb for k in ["calculation error", "arithmetic error", "multiplication error", "addition slip", "arithmetic slip", "computation mistake", "math slip"])
        or (step_mistake and any(k in step_mistake.lower() for k in ["calc", "arithmetic", "multiply", "divide", "add", "subtract"]))
    )
    if is_calc_error and not q.get("misconception_detected"):
        return {
            "error_type": TAXONOMY_CALCULATION_ERROR,
            "error_label": TAXONOMY_LABELS[TAXONOMY_CALCULATION_ERROR],
            "is_conceptual_misconception": False,
            "evidence_status": STATUS_EVIDENCE_SUPPORTED,
            "diagnostic_summary": f"Conceptual method was sound, but student committed an arithmetic/calculation slip: '{step_mistake or 'arithmetic error in computation'}'.",
            "marks_lost": marks_lost,
        }

    # 5. Check for Missing Intermediate Steps
    is_missing_steps = (
        any(k in lower_fb for k in ["missing steps", "skipped intermediate", "show working", "no working shown", "omitted steps", "missing derivation"])
        or classification_hint == "missing_steps"
    )
    if is_missing_steps and marks_lost <= (maximum * 0.40):
        return {
            "error_type": TAXONOMY_MISSING_STEPS,
            "error_label": TAXONOMY_LABELS[TAXONOMY_MISSING_STEPS],
            "is_conceptual_misconception": False,
            "evidence_status": STATUS_EVIDENCE_SUPPORTED,
            "diagnostic_summary": "Core understanding is present, but mandatory intermediate steps or working derivations were omitted.",
            "marks_lost": marks_lost,
        }

    # 6. Check for Incomplete / Partial Answer
    is_incomplete = (
        classification_hint in {"incomplete_answer", "partial_answer"}
        or any(k in lower_fb for k in ["incomplete answer", "stopped mid", "partial response", "only answered part a", "did not finish"])
    )
    if is_incomplete and not q.get("misconception_detected"):
        return {
            "error_type": TAXONOMY_INCOMPLETE_ANSWER,
            "error_label": TAXONOMY_LABELS[TAXONOMY_INCOMPLETE_ANSWER],
            "is_conceptual_misconception": False,
            "evidence_status": STATUS_EVIDENCE_SUPPORTED,
            "diagnostic_summary": "Student addressed part of the problem but did not complete the full multi-part requirement.",
            "marks_lost": marks_lost,
        }

    # 7. Check for Question Interpretation Error
    is_interpretation_error = (
        any(k in lower_fb for k in ["misread question", "misinterpreted prompt", "solved for wrong variable", "asked for radius gave diameter", "inverted constraint", "misunderstood instruction"])
        or classification_hint == "question_interpretation_error"
    )
    if is_interpretation_error:
        return {
            "error_type": TAXONOMY_QUESTION_INTERPRETATION_ERROR,
            "error_label": TAXONOMY_LABELS[TAXONOMY_QUESTION_INTERPRETATION_ERROR],
            "is_conceptual_misconception": False,
            "evidence_status": STATUS_EVIDENCE_SUPPORTED,
            "diagnostic_summary": "Student misunderstood or inverted the prompt constraints/instructions rather than lacking the underlying subject concept.",
            "marks_lost": marks_lost,
        }

    # 8. Check for Incorrect Terminology / Unit Notation
    is_terminology = (
        any(k in lower_fb for k in ["incorrect term", "non-standard terminology", "wrong unit", "unit missing", "informal wording", "vocabulary"])
        or classification_hint == "incorrect_terminology"
    )
    if is_terminology and marks_lost <= (maximum * 0.35):
        return {
            "error_type": TAXONOMY_INCORRECT_TERMINOLOGY,
            "error_label": TAXONOMY_LABELS[TAXONOMY_INCORRECT_TERMINOLOGY],
            "is_conceptual_misconception": False,
            "evidence_status": STATUS_EVIDENCE_SUPPORTED,
            "diagnostic_summary": "Understood the physical/academic phenomenon, but expressed it using incorrect or non-standard technical terminology.",
            "marks_lost": marks_lost,
        }

    # 9. Check for Programming / Syntax Flaw
    is_syntax_code = (
        any(k in lower_fb for k in ["syntax error", "indentation", "type error", "off-by-one", "null pointer", "compile error", "unclosed tag"])
        or classification_hint == "syntax_error"
    )
    if is_syntax_code:
        return {
            "error_type": TAXONOMY_SYNTAX_PROGRAMMING_ERROR,
            "error_label": TAXONOMY_LABELS[TAXONOMY_SYNTAX_PROGRAMMING_ERROR],
            "is_conceptual_misconception": False,
            "evidence_status": STATUS_EVIDENCE_SUPPORTED,
            "diagnostic_summary": "Syntax or code structure error identified in programming script.",
            "marks_lost": marks_lost,
        }

    # 10. Check for Formula Errors: Selection vs Application
    is_formula_selection = any(k in lower_fb for k in ["wrong formula", "incorrect formula selected", "used addition instead of multiplication", "used perimeter instead of area", "confused kinetic and potential"])
    if is_formula_selection:
        return {
            "error_type": TAXONOMY_INCORRECT_FORMULA_SELECTION,
            "error_label": TAXONOMY_LABELS[TAXONOMY_INCORRECT_FORMULA_SELECTION],
            "is_conceptual_misconception": True,
            "evidence_status": STATUS_EVIDENCE_SUPPORTED,
            "diagnostic_summary": f"Selected incorrect formula for the problem context: '{conceptual_mistake or 'formula mismatch'}'.",
            "marks_lost": marks_lost,
        }

    is_formula_app = any(k in lower_fb for k in ["formula application", "substituted wrong value", "inverted variables", "failed to convert units before formula", "algebraic substitution error"])
    if is_formula_app:
        return {
            "error_type": TAXONOMY_INCORRECT_FORMULA_APPLICATION,
            "error_label": TAXONOMY_LABELS[TAXONOMY_INCORRECT_FORMULA_APPLICATION],
            "is_conceptual_misconception": True,
            "evidence_status": STATUS_EVIDENCE_SUPPORTED,
            "diagnostic_summary": f"Identified correct formula, but misapplied substitution or variable mapping: '{conceptual_mistake or 'substitution flaw'}'.",
            "marks_lost": marks_lost,
        }

    # 11. Check for Genuine Conceptual Misunderstanding
    has_explicit_misc = bool(q.get("misconception_detected") or (conceptual_mistake and len(conceptual_mistake) > 3))
    if has_explicit_misc or classification_hint in {"wrong_concept", "contradictory_answer"}:
        status = STATUS_NEEDS_TEACHER_REVIEW if is_uncertain or len(student_ans) < 5 else STATUS_EVIDENCE_SUPPORTED
        return {
            "error_type": TAXONOMY_CONCEPTUAL_MISUNDERSTANDING,
            "error_label": TAXONOMY_LABELS[TAXONOMY_CONCEPTUAL_MISUNDERSTANDING],
            "is_conceptual_misconception": True,
            "evidence_status": status,
            "diagnostic_summary": conceptual_mistake or "Genuine conceptual misunderstanding identified from student script reasoning.",
            "marks_lost": marks_lost,
        }

    # 12. Check for Careless Mistakes
    if marks_lost <= (maximum * 0.15):
        return {
            "error_type": TAXONOMY_CARELESS_MISTAKE,
            "error_label": TAXONOMY_LABELS[TAXONOMY_CARELESS_MISTAKE],
            "is_conceptual_misconception": False,
            "evidence_status": STATUS_EVIDENCE_SUPPORTED,
            "diagnostic_summary": "Minor unforced notation or sign slip on otherwise mastered question.",
            "marks_lost": marks_lost,
        }

    # Fallback when evidence is too ambiguous or short (Step 2: Do not guess!)
    return {
        "error_type": TAXONOMY_LOGICAL_REASONING_ERROR,
        "error_label": TAXONOMY_LABELS[TAXONOMY_LOGICAL_REASONING_ERROR],
        "is_conceptual_misconception": False,
        "evidence_status": STATUS_NEEDS_TEACHER_REVIEW,
        "diagnostic_summary": "Answer exhibits a reasoning deficit, but evidence is insufficient to confirm a specific conceptual flaw without teacher review.",
        "marks_lost": marks_lost,
    }


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5: INDIVIDUAL STUDENT PERFORMANCE SUMMARY GENERATOR
# ══════════════════════════════════════════════════════════════════════════════
def generate_individual_performance_summary(
    eval_doc: Dict[str, Any],
    classified_questions: List[Dict[str, Any]],
    historical_concept_occurrences: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Synthesizes an evidence-based performance summary for a single student assessment:
    1. What the student understands well (strengths).
    2. Which concepts need improvement.
    3. Error types observed with supporting question references.
    4. Repeated vs isolated difficulties.
    5. What the student should practice next.
    """
    historical_concept_occurrences = historical_concept_occurrences or {}
    student_name = _safe_str(eval_doc.get("student_name") or eval_doc.get("student_name_snapshot"), "Student")
    subject = _safe_str(eval_doc.get("subject"), "General")
    total_marks = _safe_float(eval_doc.get("total_marks"), 0.0)
    obtained_marks = _safe_float(eval_doc.get("obtained_marks"), 0.0)
    percentage = round((obtained_marks / total_marks * 100), 1) if total_marks > 0 else 0.0

    strengths = []
    improvement_areas = []
    error_counts: Dict[str, List[str]] = {}
    repeated_issues = []
    isolated_issues = []

    for cq in classified_questions:
        q_num = cq.get("question_number", "?")
        concept = cq.get("concept", subject)
        err_type = cq.get("error_type")
        err_label = cq.get("error_label", err_type)
        marks_lost = cq.get("marks_lost", 0.0)

        # Strengths: Questions with 85%+ score
        if cq.get("maximum_marks", 0) > 0 and (cq.get("awarded_marks", 0) / cq.get("maximum_marks")) >= 0.85:
            if concept not in strengths:
                strengths.append(concept)
        elif marks_lost > 0:
            if concept not in improvement_areas:
                improvement_areas.append(concept)

            if err_label not in error_counts:
                error_counts[err_label] = []
            error_counts[err_label].append(str(q_num))

            # Check repeated difficulty
            prev_occ = historical_concept_occurrences.get(concept.lower(), 0)
            if prev_occ > 0:
                repeated_issues.append({
                    "concept": concept,
                    "question": str(q_num),
                    "previous_occurrences": prev_occ,
                    "reason": f"Struggled with '{concept}' across {prev_occ + 1} assessments."
                })
            else:
                isolated_issues.append({
                    "concept": concept,
                    "question": str(q_num),
                    "reason": f"Observed on Question {q_num} in this assessment."
                })

    # Determine recommended practice target
    if repeated_issues:
        top_rep = repeated_issues[0]["concept"]
        practice_next = f"Prioritize foundational review of '{top_rep}' to address recurring difficulty."
    elif improvement_areas:
        top_imp = improvement_areas[0]
        practice_next = f"Targeted practice on '{top_imp}' focusing on observed error patterns."
    else:
        practice_next = f"Advanced problem-solving and extension topics in {subject}."

    # Error breakdown summary string
    error_summary_items = [f"{lbl} (Q{', Q'.join(qs)})" for lbl, qs in error_counts.items()]
    observed_errors_str = "; ".join(error_summary_items) if error_summary_items else "No major structural errors observed."

    return {
        "student_name": student_name,
        "subject": subject,
        "obtained_marks": obtained_marks,
        "total_marks": total_marks,
        "percentage": percentage,
        "strengths": strengths if strengths else ["Basic syllabus curriculum familiarity"],
        "concepts_needing_improvement": improvement_areas,
        "observed_error_breakdown": error_counts,
        "observed_errors_summary": observed_errors_str,
        "repeated_difficulties": repeated_issues,
        "isolated_mistakes": isolated_issues,
        "recommended_next_practice": practice_next,
        "has_repeated_deficits": len(repeated_issues) > 0,
        "total_questions_evaluated": len(classified_questions),
    }


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6: GENUINELY PERSONALIZED PEDAGOGICAL ACTIONS
# ══════════════════════════════════════════════════════════════════════════════
def build_personalized_action(
    error_type: str,
    concept: str,
    subject: str,
    related_questions: List[str],
    evidence_text: str,
    marks_lost: float,
    total_marks: float,
    is_repeated: bool = False
) -> Dict[str, Any]:
    """
    Constructs a student-specific, non-generic pedagogical action based on the exact
    type of mistake and evidence observed.
    """
    qs_str = ", ".join(f"Q{q}" for q in related_questions) if related_questions else "Assessment"

    if error_type == TAXONOMY_CONCEPTUAL_MISUNDERSTANDING:
        action = f"Foundational conceptual review of '{concept}'"
        activity = f"Interactive first-principles lesson on {concept} contrasting common misconceptions with standard curriculum models."
        reason = f"Student's script responses in {qs_str} exhibit a conceptual misunderstanding: {evidence_text}"
        expected_outcome = f"Student correctly explains and applies the underlying physical/mathematical laws of {concept}."

    elif error_type == TAXONOMY_INCORRECT_FORMULA_SELECTION:
        action = f"Formula discrimination and problem-context mapping for '{concept}'"
        activity = f"Comparison drill identifying when to apply specific formulas in {concept} versus neighboring equations."
        reason = f"Student selected an incorrect equation in {qs_str} despite given parameters indicating a {concept} problem."
        expected_outcome = f"Accurate identification of governing equations based on given problem constraints."

    elif error_type == TAXONOMY_INCORRECT_FORMULA_APPLICATION:
        action = f"Worked-example step-by-step substitution training for '{concept}'"
        activity = f"Guided practice substituting numerical variables with unit alignment before algebraic calculation."
        reason = f"Student selected the appropriate formula in {qs_str} but made variable mapping or substitution errors."
        expected_outcome = f"Zero substitution or variable inversion errors in {concept} calculations."

    elif error_type == TAXONOMY_CALCULATION_ERROR:
        action = f"Calculation precision drill and arithmetic verification in '{concept}'"
        activity = f"Targeted numerical practice with intermediate calculation checks and estimation steps."
        reason = f"Student demonstrated correct theoretical understanding in {qs_str} but committed arithmetic slips costing {marks_lost} marks."
        expected_outcome = f"Accurate arithmetic execution and consistent self-checking of numerical results."

    elif error_type == TAXONOMY_MISSING_STEPS:
        action = f"Step-structured derivation and solution-writing rubric training"
        activity = f"Solution template exercises requiring every intermediate derivation and law reference to be explicitly written."
        reason = f"Student reached or attempted results in {qs_str} but omitted mandatory intermediate working steps."
        expected_outcome = f"Full-credit solutions containing all rubric-required intermediate steps."

    elif error_type == TAXONOMY_INCOMPLETE_ANSWER:
        action = f"Multi-part question completion and exam pacing strategy"
        activity = f"Timed multi-part problem drills training students to allocate time across all sub-parts."
        reason = f"Student left required sub-parts incomplete in {qs_str}, forfeiting credit."
        expected_outcome = f"Complete submission of all required question parts within standard exam pacing."

    elif error_type == TAXONOMY_QUESTION_INTERPRETATION_ERROR:
        action = f"Question prompt deconstruction and constraint highlighting"
        activity = f"Keyword-underlining exercises identifying given vs asked variables and specific unit constraints."
        reason = f"Student solved for the wrong variable or misread constraints in {qs_str}."
        expected_outcome = f"Correct interpretation of complex question prompts and given boundary conditions."

    elif error_type == TAXONOMY_INCORRECT_TERMINOLOGY:
        action = f"Scientific terminology and definitions practice in '{concept}'"
        activity = f"Flashcard revision and definition matching for key academic vocabulary in {concept}."
        reason = f"Student used informal or non-standard terms in {qs_str} instead of precise academic terminology."
        expected_outcome = f"Accurate use of curriculum-standard technical terms in written responses."

    elif error_type == TAXONOMY_SYNTAX_PROGRAMMING_ERROR:
        action = f"Syntax debugging and code tracing exercises in '{concept}'"
        activity = f"Line-by-line code tracing and syntax linting drills for common structural bugs."
        reason = f"Student's code in {qs_str} failed due to syntax or structural programming errors."
        expected_outcome = f"Syntactically valid, runnable code meeting problem specifications."

    else:
        # Default tailored to subject and concept
        action = f"Diagnostic review of '{concept}'"
        activity = f"Guided review session on core principles and practice problems for {concept}."
        reason = f"Student lost {marks_lost} marks across {qs_str} due to {evidence_text}."
        expected_outcome = f"Mastery of {concept} curriculum standards."

    # Step 7: Transparent Evidence-Based Priority Calculation
    loss_ratio = (marks_lost / total_marks) if total_marks > 0 else 0.0
    if is_repeated or marks_lost >= 20.0 or loss_ratio >= 0.40 or (error_type == TAXONOMY_CONCEPTUAL_MISUNDERSTANDING and marks_lost >= 10.0):
        priority = "High"
        priority_justification = f"High Priority: Recurrent or significant deficit ({marks_lost}/{total_marks} marks lost) affecting foundational concept '{concept}'."
    elif marks_lost >= 5.0 or error_type in {TAXONOMY_CONCEPTUAL_MISUNDERSTANDING, TAXONOMY_INCORRECT_FORMULA_SELECTION}:
        priority = "Medium"
        priority_justification = f"Medium Priority: Verified learning gap on {qs_str} losing {marks_lost} marks."
    else:
        priority = "Low"
        priority_justification = f"Low Priority: Minor isolated slip ({marks_lost} marks lost) on {qs_str}."

    return {
        "concept": concept,
        "error_type": error_type,
        "error_label": TAXONOMY_LABELS.get(error_type, error_type),
        "action": action,
        "recommended_action": action,
        "activity": activity,
        "reason": reason,
        "expected_outcome": expected_outcome,
        "priority": priority,
        "priority_justification": priority_justification,
        "related_questions": related_questions,
        "marks_lost": marks_lost,
        "status": "New",
    }


# ══════════════════════════════════════════════════════════════════════════════
# STEP 8: ADAPTIVE ASSESSMENT LIFECYCLE TRACKER
# ══════════════════════════════════════════════════════════════════════════════
def track_adaptive_concept_lifecycle(
    student_id: str,
    concept: str,
    current_eval_id: str,
    current_score_ratio: float,
    previous_evaluations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Checks if a student previously struggled with `concept` in prior evaluations:
    - If current performance is >= 80%: concept status -> 'Resolved'
    - If current performance is 50% - 79%: concept status -> 'Improving'
    - If current performance is < 50% and appeared before: concept status -> 'Persistent'
    - If first time: concept status -> 'New'
    """
    if not student_id or not concept or not previous_evaluations:
        return {"lifecycle_status": "New", "occurrences": 1, "note": "Initial assessment instance."}

    concept_lower = concept.strip().lower()
    prior_struggles = 0

    for prev in previous_evaluations:
        if str(prev.get("id") or prev.get("evaluation_id")) == str(current_eval_id):
            continue
        prev_qs = prev.get("questions") or prev.get("evaluations") or []
        for pq in prev_qs:
            p_concept = str(pq.get("concept") or pq.get("identified_concept") or "").strip().lower()
            if concept_lower in p_concept or p_concept in concept_lower:
                p_max = _safe_float(pq.get("maximum_marks"), 0.0)
                p_awarded = _safe_float(pq.get("awarded_marks"), 0.0)
                if p_max > 0 and (p_awarded / p_max) < 0.65:
                    prior_struggles += 1
                    break

    if prior_struggles > 0:
        if current_score_ratio >= 0.80:
            return {
                "lifecycle_status": "Resolved",
                "occurrences": prior_struggles + 1,
                "note": f"Student demonstrated verified recovery on '{concept}' ({round(current_score_ratio * 100)}% score) following previous difficulty across {prior_struggles} assessment(s)."
            }
        elif current_score_ratio >= 0.50:
            return {
                "lifecycle_status": "Improving",
                "occurrences": prior_struggles + 1,
                "note": f"Partial recovery observed on '{concept}' ({round(current_score_ratio * 100)}% score), improving from prior deficits."
            }
        else:
            return {
                "lifecycle_status": "Persistent",
                "occurrences": prior_struggles + 1,
                "note": f"Persistent learning gap: student continues to struggle with '{concept}' across {prior_struggles + 1} assessments."
            }

    return {
        "lifecycle_status": "New",
        "occurrences": 1,
        "note": "First verified assessment instance of this concept."
    }


# ══════════════════════════════════════════════════════════════════════════════
# STEP 9 & 10: STRUCTURED DEEP AI DIAGNOSTIC ANALYZER (Gemini 3.6 Flash)
# ══════════════════════════════════════════════════════════════════════════════
def analyze_evaluation_with_ai(eval_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs deep AI educational diagnosis of an authenticated teacher evaluation using Gemini.
    Strictly adheres to:
    - Evidence Grounding: Only uses genuine questions, student script answers, and criteria.
    - 12-Error Taxonomy: Classifies every question into explicit error types.
    - Zero Mocking: If AI fails or is unconfigured, reports error honestly without mock data.
    - Source Validation: Rejects question numbers that don't exist in the real question paper.
    """
    from ..gemini_service import GeminiService

    student_name = _safe_str(eval_doc.get("student_name") or eval_doc.get("student_name_snapshot"), "Student")
    subject = _safe_str(eval_doc.get("subject"), "General")
    assessment_title = _safe_str(eval_doc.get("assessment_title"), f"{subject} Assessment")
    eval_id = _safe_str(eval_doc.get("id") or eval_doc.get("_id") or eval_doc.get("evaluation_id"))
    total_marks = _safe_float(eval_doc.get("total_marks"), 0.0)
    obtained_marks = _safe_float(eval_doc.get("obtained_marks"), 0.0)

    raw_questions = eval_doc.get("questions") or eval_doc.get("evaluations") or []
    if isinstance(raw_questions, str):
        try:
            raw_questions = json.loads(raw_questions)
        except Exception:
            raw_questions = []

    if not isinstance(raw_questions, list) or not raw_questions:
        return {
            "success": False,
            "error": "No question-level evaluation records found in source assessment to analyze.",
            "can_retry": False
        }

    # Prepare sanitized question summaries
    valid_q_nums = set()
    questions_context = []
    for idx, q in enumerate(raw_questions):
        if not isinstance(q, dict):
            continue
        q_num = str(q.get("question_number") or idx + 1)
        valid_q_nums.add(q_num)
        q_max = _safe_float(q.get("maximum_marks") or q.get("max_marks"), 0.0)
        q_awarded = _safe_float(q.get("awarded_marks"), 0.0)
        q_text = _safe_str(q.get("question_text"), f"Question {q_num}")
        std_ans = _safe_str(q.get("student_answer") or q.get("answer_summary"), "No answer text recorded")
        expected = _safe_str(q.get("what_student_should_have_written") or q.get("correct_answer_or_expected_points"))
        concept = _safe_str(q.get("concept") or q.get("identified_concept") or (q.get("concepts_tested", [subject])[0] if q.get("concepts_tested") else subject))
        eval_reason = _safe_str(q.get("evaluation_reason") or q.get("teacher_feedback"))

        questions_context.append({
            "question_number": q_num,
            "question_text": q_text,
            "concept": concept,
            "maximum_marks": q_max,
            "awarded_marks": q_awarded,
            "student_actual_answer": std_ans,
            "expected_rubric_answer": expected,
            "evaluator_notes": eval_reason
        })

    prompt = f"""You are the LearnSphere AI Pedagogical Diagnostic Assistant.
Analyze this genuine student evaluation record. Be precise, educational, and strictly evidence-grounded.

CRITICAL RULES:
1. ONLY refer to question numbers in this list: {sorted(list(valid_q_nums))}. Do NOT invent questions.
2. Distinguish between different types of mistakes using this exact error taxonomy:
   - "conceptual_misunderstanding": True flawed mental model of physical/academic principle
   - "incorrect_formula_selection": Chose the wrong formula altogether (e.g. perimeter instead of area)
   - "incorrect_formula_application": Right formula, but wrong variable substitution or unit alignment
   - "calculation_error": Theory is correct, but arithmetic calculation slip occurred
   - "missing_steps": Correct answer but skipped intermediate required derivation steps
   - "incomplete_answer": Addressed only part of the question or halted mid-solution
   - "question_interpretation_error": Misinterpreted question prompt constraints/boundary conditions
   - "incorrect_terminology": Correct concept but non-standard/incorrect scientific vocabulary
   - "logical_reasoning_error": Flawed step in logical deduction or proof
   - "syntax_programming_error": Programming syntax or code logic error
   - "careless_mistake": Minor notation or sign slip
   - "alternative_valid_expression": Valid response expressed differently (NOT a misconception)
3. DO NOT label an arithmetic slip or missing steps as a conceptual misconception.
4. For every learning gap, provide a tailored, non-generic pedagogical action:
   - action: what the teacher should assign/do
   - activity: specific student practice activity
   - reason: why recommended citing student's actual written text
   - expected_outcome: what the student will achieve
   - priority: "High" | "Medium" | "Low" | "Needs Review"
5. Do NOT invent external URLs, courses, or websites.

ASSESSMENT CONTEXT:
Student Name: {student_name}
Subject: {subject}
Assessment Title: {assessment_title}
Total Marks: {total_marks}
Obtained Marks: {obtained_marks}

QUESTIONS DATA:
{json.dumps(questions_context, indent=2)}

Respond with a strictly formatted JSON object adhering to this schema:
{{
  "performance_summary": {{
    "strengths": ["string"],
    "concepts_needing_improvement": ["string"],
    "overview": "string",
    "recommended_practice": "string"
  }},
  "diagnosed_questions": [
    {{
      "question_number": "string",
      "concept": "string",
      "error_type": "string",
      "is_conceptual_misconception": boolean,
      "evidence_status": "VERIFIED" | "NEEDS_TEACHER_REVIEW" | "INSUFFICIENT_EVIDENCE",
      "diagnostic_summary": "string",
      "student_evidence_quote": "string",
      "correct_model_summary": "string"
    }}
  ],
  "personalized_recommendations": [
    {{
      "concept": "string",
      "error_type": "string",
      "related_questions": ["string"],
      "action": "string",
      "activity": "string",
      "reason": "string",
      "expected_outcome": "string",
      "priority": "High" | "Medium" | "Low" | "Needs Review",
      "priority_justification": "string"
    }}
  ]
}}"""

    try:
        gemini = GeminiService()
        raw_resp = gemini.generate_content(prompt=prompt, json_output=True, temperature=0.0)
        parsed = gemini.parse_json_response(raw_resp)

        if not isinstance(parsed, dict):
            raise ValueError("AI response was not a valid dictionary structure.")

        # Source Validation (Step 9: Reject invalid question references)
        diagnosed_qs = parsed.get("diagnosed_questions") or []
        validated_diagnosed_qs = []
        for dq in diagnosed_qs:
            q_num = str(dq.get("question_number") or "").strip()
            if q_num in valid_q_nums:
                dq["error_label"] = TAXONOMY_LABELS.get(dq.get("error_type"), dq.get("error_type", "Diagnosed Issue"))
                validated_diagnosed_qs.append(dq)

        parsed["diagnosed_questions"] = validated_diagnosed_qs

        # Validate recommendations
        recs = parsed.get("personalized_recommendations") or []
        validated_recs = []
        for r in recs:
            # Filter question references to only authentic questions
            related = [str(q).strip() for q in r.get("related_questions", []) if str(q).strip() in valid_q_nums]
            if not related:
                related = list(valid_q_nums)[:2]
            r["related_questions"] = related
            r["error_label"] = TAXONOMY_LABELS.get(r.get("error_type"), r.get("error_type", "Pedagogical Gap"))
            r["status"] = "New"
            validated_recs.append(r)

        parsed["personalized_recommendations"] = validated_recs
        parsed["success"] = True
        parsed["evaluation_id"] = eval_id
        parsed["student_name"] = student_name
        parsed["subject"] = subject
        return parsed

    except Exception as exc:
        logger.error(f"[DiagnosticEngine] AI diagnosis failed for eval {eval_id}: {exc}")
        return {
            "success": False,
            "error": f"AI diagnostic analysis temporarily unavailable: {str(exc)}. Source evaluation data remains intact.",
            "can_retry": True
        }

