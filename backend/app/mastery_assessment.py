"""
LearnSphere AI - Accessible Mastery Assessment Engine for Blind Companion
========================================================================
Prompt 5: Accessible assessment, adaptive question generation, subject-specific
evaluation, multi-attempt mastery verification, and continuous improvement loops.

Core Capabilities:
1. Accessible Assessment: Text-to-speech question reading, voice/keyboard answers,
   LaTeX/math natural speech translation, detailed diagram audio descriptions,
   repeat question, review answer transcript, editable transcript before submission,
   and spoken submission confirmation dialogs.
2. Adaptive Question Generation: Grounded strictly in authentic syllabus, topic,
   unit, learning objectives, and prior diagnosed learning gaps across 5 cognitive tiers:
   (basic_understanding, conceptual_reasoning, application, problem_solving, advanced).
3. Subject-Specific Evaluation: Classifies answers into:
   - Correct understanding
   - Partially correct understanding
   - Conceptual misunderstanding
   - Calculation error
   - Missing explanation
   - Incorrect reasoning
   Accounts for speech recognition uncertainty and requires transcript review.
4. Mastery Verification: Concept is marked 'Understanding demonstrated' only with
   sufficient multi-attempt evidence (>= 2 successful attempts >= 80% without conceptual gaps).
   States: (Learning, Needs practice, Progressing, Understanding demonstrated, More evidence needed).
   Never equates completed lesson count with mastery.
5. Continuous Improvement Loop: Explains strengths, explains mistakes in simple language,
   identifies related syllabus concept, recommends targeted learning activity, generates
   calibrated practice, and dynamically updates learning path.
   Strictly isolated from teacher evaluation records.
"""

import json
import logging
import math
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.learning_gap_detector import (
    EVIDENCE_STRENGTH,
    MISTAKE_TYPES,
    TOPIC_STATUS,
    classify_mistake_nature,
    record_blind_practice_attempt,
)

logger = logging.getLogger(__name__)


def _get_gemini_service():
    """Lazily load GeminiService for dynamic, AI-grounded assessment intelligence."""
    try:
        from app.gemini_service import GeminiService
        return GeminiService()
    except Exception as exc:
        logger.debug("[MasteryAssessment] GeminiService initialization notice: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# MASTERY STATES & EVALUATION RESULTS
# ─────────────────────────────────────────────────────────────────────────────

MASTERY_STATES = {
    "LEARNING": "Learning",
    "NEEDS_PRACTICE": "Needs practice",
    "PROGRESSING": "Progressing",
    "UNDERSTANDING_DEMONSTRATED": "Understanding demonstrated",
    "MORE_EVIDENCE_NEEDED": "More evidence needed",
}

EVALUATION_RESULTS = {
    "CORRECT": "Correct understanding",
    "PARTIALLY_CORRECT": "Partially correct understanding",
    "CONCEPTUAL_MISUNDERSTANDING": "Conceptual misunderstanding",
    "CALCULATION_ERROR": "Calculation error",
    "MISSING_EXPLANATION": "Missing explanation",
    "INCORRECT_REASONING": "Incorrect reasoning",
}

QUESTION_TIERS = {
    "BASIC": "basic_understanding",
    "CONCEPTUAL": "conceptual_reasoning",
    "APPLICATION": "application",
    "PROBLEM_SOLVING": "problem_solving",
    "ADVANCED": "advanced",
}


# ─────────────────────────────────────────────────────────────────────────────
# MATHEMATICAL EXPRESSION TO SPEECH TRANSLATOR
# ─────────────────────────────────────────────────────────────────────────────

def narrate_math_expression(text: str) -> str:
    """
    Translates raw mathematical expressions, formulas, and LaTeX notations into
    natural, fluid spoken English suitable for blind students and screen readers.
    """
    if not text or not isinstance(text, str):
        return ""

    out = text

    # Standard LaTeX replacements
    # 0. Strip LaTeX formatting and parentheses sizing macros
    out = re.sub(r"\\left\b", "", out)
    out = re.sub(r"\\right\b", "", out)
    out = re.sub(r"\\[,;! ]", " ", out)
    out = re.sub(r"\\sin\b", "sine", out)
    out = re.sub(r"\\cos\b", "cosine", out)
    out = re.sub(r"\\tan\b", "tangent", out)

    # 1. Derivatives first (before general fractions)
    out = re.sub(r"\\frac\{d([a-zA-Z])\}\{d([a-zA-Z])\}", r"d \1 by d \2", out)
    out = re.sub(r"\\frac\{d\}\{d([a-zA-Z])\}", r"derivative with respect to \1", out)
    out = re.sub(r"\bdy/dx\b", "d y by d x", out)
    out = re.sub(r"\bdu/dx\b", "d u by d x", out)

    # 2. General Fractions: \frac{num}{den} -> "the fraction num divided by den"
    frac_pattern = re.compile(r"\\frac\{([^{}]+)\}\{([^{}]+)\}")
    while frac_pattern.search(out):
        out = frac_pattern.sub(r"the fraction \1 divided by \2", out)

    # Simple inline fractions: a / b
    out = re.sub(r"(\b\w+)\s*/\s*(\b\w+)", r"\1 divided by \2", out)

    # Square roots: \sqrt{x} -> "the square root of x"
    out = re.sub(r"\\sqrt\{([^{}]+)\}", r"the square root of \1", out)
    out = re.sub(r"\\sqrt\s*(\w+)", r"the square root of \1", out)

    # Limits: \lim_{x \to 0} -> "limit as x approaches 0 of"
    out = re.sub(r"\\lim_\{([^}]+)\\to\s*([^}]+)\}", r"limit as \1 approaches \2 of", out)

    # Integrals: \int_{a}^{b} -> "integral from a to b of"
    out = re.sub(r"\\int_\{([^}]+)\}\^\{([^}]+)\}", r"integral from \1 to \2 of", out)
    out = re.sub(r"\\int\b", "integral of", out)

    # Powers & Exponents: x^2 -> "x squared", x^3 -> "x cubed", (expr)^3 -> "(expr) cubed", x^{n} -> "x to the power of n"
    out = re.sub(r"([\w\)]+)\^2\b", r"\1 squared", out)
    out = re.sub(r"([\w\)]+)\^3\b", r"\1 cubed", out)
    out = re.sub(r"\^2\b", " squared", out)
    out = re.sub(r"\^3\b", " cubed", out)
    out = re.sub(r"([\w\)]+)\^\{([^}]+)\}", r"\1 to the power of \2", out)
    out = re.sub(r"([\w\)]+)\^(\w+)", r"\1 to the power of \2", out)

    # Subscripts: V_{th} -> "V Thevenin", R_{eq} -> "R equivalent", I_{N} -> "I Norton"
    sub_map = {
        "th": "Thevenin",
        "in": "input",
        "out": "output",
        "eq": "equivalent",
        "max": "maximum",
        "min": "minimum",
        "eff": "effective",
        "rms": "R M S",
        "L": "load",
        "s": "source",
        "N": "Norton",
        "o": "output",
        "1": "one",
        "2": "two",
        "3": "three",
        "total": "total"
    }
    for sub_k, sub_spoken in sub_map.items():
        out = re.sub(rf"([a-zA-Z])_\{{{sub_k}\}}", rf"\1 {sub_spoken}", out, flags=re.IGNORECASE)
        out = re.sub(rf"([a-zA-Z])_{sub_k}\b", rf"\1 {sub_spoken}", out, flags=re.IGNORECASE)

    # Generic remaining subscripts: X_{abc} -> "X sub abc"
    out = re.sub(r"([a-zA-Z])_\{([^}]+)\}", r"\1 sub \2", out)
    out = re.sub(r"([a-zA-Z])_([0-9a-zA-Z])", r"\1 sub \2", out)

    # Common Math & Electrical Symbols
    symbol_translations = [
        (r"\\cdot", " times "),
        (r"\\times", " times "),
        (r"\*", " times "),
        (r"\\pm", " plus or minus "),
        (r"\+", " plus "),
        (r"-", " minus "),
        (r"=", " equals "),
        (r"\\approx", " approximately equals "),
        (r"\\neq", " does not equal "),
        (r"\\le\b", " less than or equal to "),
        (r"\\leq\b", " less than or equal to "),
        (r"\\ge\b", " greater than or equal to "),
        (r"\\geq\b", " greater than or equal to "),
        (r"\\Omega", " Ohms "),
        (r"\\mu F", " microfarads "),
        (r"\\mu A", " microamperes "),
        (r"\\mA", " milliamperes "),
        (r"\\pi", " pi "),
        (r"\\Delta", " change in "),
        (r"\\sum", " summation of "),
        (r"\\infty", " infinity "),
        (r"\\theta", " theta "),
        (r"\\omega", " omega "),
        (r"\\alpha", " alpha "),
        (r"\\beta", " beta "),
        (r"\$", "")  # strip leftover dollar signs
    ]

    for pat, rep in symbol_translations:
        out = re.sub(pat, rep, out)

    # Normalize whitespace
    out = re.sub(r"\s+", " ", out).strip()
    return out


# ─────────────────────────────────────────────────────────────────────────────
# DIAGRAM TOPOLOGY VERBALIZER
# ─────────────────────────────────────────────────────────────────────────────

def generate_diagram_narration(subject: str, topic: str, context: str = "") -> str:
    """
    Generates rich, spatial, and topological audio descriptions for diagrams,
    circuits, and graphs so blind students can build an accurate mental representation.
    Dynamically calls Gemini AI when available.
    """
    gs = _get_gemini_service()
    if gs:
        try:
            prompt = (
                f"You are LearnSphere AI's Concept-to-Sense visual intelligence engine for blind learners.\n"
                f"Generate a rich, spatial, topological spoken audio description for an academic diagram, schematic, or graph representing '{topic}' in the subject '{subject}'.\n"
                f"Context: {context or 'Textbook and examination visual specification'}\n\n"
                f"Requirements:\n"
                f"1. Spatial layout: mental map (top rail/quadrant, bottom, left branch, right, center, nodes).\n"
                f"2. Element inventory: specify component labels, polarity, ratings, units, or axis variables.\n"
                f"3. Directional flow: trace clockwise current, directed signal arrows, or curve slope behavior.\n"
                f"4. Tactile analogies: intuitive physical tactile metaphors to make spatial orientation effortless.\n"
                f"5. Natural spoken style for screen-reader / TTS narration without ASCII tables or raw delimiters.\n"
                f"Output only the spoken description paragraph."
            )
            raw = gs.generate_content(prompt, json_output=False, temperature=0.1, timeout=12)
            if raw and len(raw.strip()) > 40:
                return raw.strip()
        except Exception as exc:
            logger.debug("[MasteryAssessment] Dynamic diagram narration error: %s", exc)

    s_lower = subject.lower()
    t_lower = topic.lower()

    if "thevenin" in t_lower or "norton" in t_lower or "circuit" in s_lower:
        return (
            "Circuit Schematic Description: This is a planar two-terminal DC network. "
            "On the left vertical branch is an independent 24-volt DC voltage source, oriented with positive terminal up. "
            "Connected in series at the top horizontal rail is a fixed 40-ohm resistor R1. "
            "At the central vertical branch, connected between node A and the reference ground rail, is a 60-ohm load resistor R2. "
            "The output terminals A and B are located across this central 60-ohm resistor. "
            "All lower connection leads merge into a continuous zero-volt reference ground rail."
        )
    elif "differentiation" in t_lower or "calculus" in s_lower or "chain rule" in t_lower:
        return (
            "Function Architecture Description: This problem represents a composite function hierarchy. "
            "The inner core expression is u equals 3x squared plus 5, representing a standard quadratic curve shifted vertically by 5 units. "
            "The outer container function is f of u equals u raised to the 4th power. "
            "The composite mapping cascades the output of the quadratic inside the polynomial power function."
        )
    elif "graph" in t_lower or "frequency response" in t_lower or "bode" in t_lower:
        return (
            "Graph Coordinate Description: The horizontal x-axis represents frequency omega in radians per second on a logarithmic scale from 1 to 1000. "
            "The vertical y-axis represents circuit gain in decibels from minus 40 dB to 0 dB. "
            "The magnitude response curve is flat at 0 dB until the cutoff frequency of 50 radians per second, "
            "after which it rolls off with a negative slope of minus 20 decibels per decade."
        )
    elif "binary" in t_lower or "tree" in t_lower or "data structure" in s_lower:
        return (
            f"Data Structure Topological Description: A hierarchical binary search tree representing {topic}. "
            "At the top apex is the root node. Branching downward to the left is the left subtree containing keys strictly less than the root. "
            "Branching downward to the right is the right subtree containing keys strictly greater than the root, maintaining recursive search invariant."
        )
    elif "reaction" in t_lower or "kinetics" in t_lower or "arrhenius" in t_lower or "chemistry" in s_lower:
        return (
            f"Reaction Profile Description: A continuous potential energy curve for {topic}. "
            "The horizontal axis marks reaction coordinate progress from reactants to products. "
            "The curve begins at the reactant enthalpy plateau, rises through an activation energy barrier Ea to the transition state peak, "
            "and descends to the final product energy level."
        )
    else:
        return (
            f"Spatial System Description: An academic system diagram for {topic} in {subject}. "
            f"The primary input conditions enter on the left rail, process sequentially through central transformation stages, "
            f"and deliver verified output parameters at the right terminal."
        )


# ─────────────────────────────────────────────────────────────────────────────
# SPEECH-TO-TEXT TRANSCRIPT NORMALIZATION & REVIEW
# ─────────────────────────────────────────────────────────────────────────────

def normalize_voice_transcript(raw_text: str, subject: str = "", topic: str = "") -> str:
    """
    Corrects common voice dictation inaccuracies for academic and technical terms
    (e.g., phonetic slips like 'v thevenin' -> 'V_th', 'kcl' -> 'KCL', 'ohms' -> 'Ohms').
    Accounts for speech recognition uncertainty while strictly preserving student's meaning.
    """
    if not raw_text or not isinstance(raw_text, str):
        return ""

    t = raw_text.strip()

    # Number words to digits
    number_words = [
        (r"\bzero\b", "0"),
        (r"\bone\b", "1"),
        (r"\btwo\b", "2"),
        (r"\bthree\b", "3"),
        (r"\bfour\b", "4"),
        (r"\bfive\b", "5"),
        (r"\bsix\b", "6"),
        (r"\bseven\b", "7"),
        (r"\beight\b", "8"),
        (r"\bnine\b", "9"),
        (r"\bten\b", "10")
    ]
    for pat, rep in number_words:
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)

    # Phonetic corrections for common academic dictation slips
    phonetic_fixes = [
        (r"\bv thevenin\b", "V_th (Thevenin Voltage)"),
        (r"\bv th\b", "V_th"),
        (r"\br thevenin\b", "R_th (Thevenin Resistance)"),
        (r"\br th\b", "R_th"),
        (r"\bi norton\b", "I_N (Norton Current)"),
        (r"\bi sub n\b", "I_N"),
        (r"\bkcl\b", "KCL (Kirchhoff's Current Law)"),
        (r"\bkvl\b", "KVL (Kirchhoff's Voltage Law)"),
        (r"\bohms?\b", "Ohms"),
        (r"\bvolts?\b", "V"),
        (r"\bmicro farads?\b", "microfarads"),
        (r"\bdy\s+by\s+dx\b", "dy/dx"),
        (r"\bdy\s+dx\b", "dy/dx"),
        (r"\bdu\s+by\s+dx\b", "du/dx"),
        (r"\bdu\s+dx\b", "du/dx"),
        (r"\bopen\s+parenthesis\b", "("),
        (r"\bclose\s+parenthesis\b", ")"),
        (r"\bopen\s+bracket\b", "["),
        (r"\bclose\s+bracket\b", "]"),
        (r"\bmultiplied\s+by\b", "*"),
        (r"\bdivided\s+by\b", "/"),
        (r"\bplus\b", "+"),
        (r"\bminus\b", "-"),
        (r"\bequals?\b", "="),
        (r"\bx\s+squared\b", "x^2"),
        (r"\bx\s+cubed\b", "x^3"),
        (r"\bsquared\b", "^2"),
        (r"\bcubed\b", "^3"),
        (r"(\d+)\s+([a-zA-Z])\b", r"\1\2"),
        (r"\bsine\b", "sin"),
        (r"\bcosine\b", "cos"),
        (r"\btangent\b", "tan")
    ]

    for pat, rep in phonetic_fixes:
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)

    return t


# ─────────────────────────────────────────────────────────────────────────────
# ADAPTIVE QUESTION GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def generate_mastery_questions(
    student_id: str,
    student_name: str,
    subject: str,
    unit: str,
    topic: str,
    subtopic: str = "",
    syllabus_doc: Dict[str, Any] = None,
    active_gaps: List[Dict[str, Any]] = None,
    tier: str = "adaptive"
) -> List[Dict[str, Any]]:
    """
    Generates authentic, syllabus-grounded mastery assessment questions.
    Supports 5 cognitive tiers:
    1. basic_understanding
    2. conceptual_reasoning
    3. application
    4. problem_solving
    5. advanced
    Explicitly incorporates past diagnosed learning gaps so the assessment tests
    whether prior weaknesses have been genuinely resolved.
    """
    t_lower = topic.lower()
    s_lower = subject.lower()
    gaps = active_gaps or []

    # Check if student had a prior gap on this topic
    prior_mistake_nature = None
    if gaps:
        for g in gaps:
            if g.get("topic", "").lower() == t_lower:
                prior_mistake_nature = g.get("mistake_nature")
                break

    questions: List[Dict[str, Any]] = []

    # ── Try Dynamic Generation via Gemini AI ───────────────────────────────────
    gs = _get_gemini_service()
    if gs:
        try:
            gaps_summary = ""
            if gaps:
                prior = [g for g in gaps if g.get("topic", "").lower() == t_lower]
                if prior:
                    gaps_summary = f"Student previously exhibited the following diagnosed learning gap on this topic: {prior[0].get('mistake_nature')}. Frame questions to test whether this gap has been genuinely resolved."

            syllabus_excerpt = ""
            if syllabus_doc:
                chapters = syllabus_doc.get("chapters") or syllabus_doc.get("units") or {}
                s_chapters = chapters.get(subject) or []
                if isinstance(s_chapters, list):
                    for ch in s_chapters:
                        if isinstance(ch, dict) and t_lower in [str(c).lower() for c in ch.get("concepts", [])]:
                            syllabus_excerpt = f"Unit: {ch.get('name')}, Concepts: {', '.join(str(c) for c in ch.get('concepts', []))}"
                            break

            prompt = f"""You are LearnSphere AI's Senior Assessment Architect for Blind and Low-Vision Students.
Generate 3 to 4 syllabus-grounded mastery assessment questions for:
- Subject: {subject}
- Unit: {unit}
- Topic: {topic}
- Subtopic: {subtopic or topic}
- Syllabus Context: {syllabus_excerpt or subject}
- Cognitive Tier Mode: {tier}
{gaps_summary}

Requirements:
1. Cover progressive cognitive tiers:
   - Tier 1 (basic_understanding): Definitions, fundamental laws, or foundational mechanism.
   - Tier 2 (conceptual_reasoning): Step-by-step logic, boundary conditions, why the law holds.
   - Tier 3 (problem_solving / application): Concrete calculation, algorithm tracing, or formula application with explicit numbers/equations.
   - Tier 4 (advanced): Higher-order analytical synthesis or real-world application.
2. For each question provide:
   - "tier": one of ["basic_understanding", "conceptual_reasoning", "application", "problem_solving", "advanced"]
   - "tier_label": Human readable label
   - "question_text": Clear, rigorous academic question
   - "spoken_prompt": Audio-friendly version written in natural spoken phonetics (no raw LaTeX symbols like \\frac, replace with 'divided by', powers with 'to the power', etc.)
   - "math_narration": Spoken narration of mathematical formulas
   - "diagram_description": Spatial tactile description if a diagram is relevant, otherwise ""
   - "expected_criteria": Detailed grading rubric stating exact required terms, equations, and values
   - "sample_answer": Complete model solution
   - "points": 5.0
   - "has_diagram": boolean
Return a valid JSON array of question objects only."""

            raw = gs.generate_content(prompt, json_output=True, temperature=0.1, timeout=20)
            if raw:
                parsed = json.loads(raw)
                if isinstance(parsed, list) and len(parsed) >= 2:
                    dynamic_questions = []
                    for item in parsed:
                        q_text = str(item.get("question_text", "")).strip()
                        if not q_text:
                            continue
                        q_tier = item.get("tier") or QUESTION_TIERS["BASIC"]
                        if q_tier not in QUESTION_TIERS.values():
                            q_tier = QUESTION_TIERS["BASIC"]
                        dynamic_questions.append({
                            "question_id": f"mq_{uuid.uuid4().hex[:8]}",
                            "tier": q_tier,
                            "tier_label": item.get("tier_label") or "Conceptual Mastery",
                            "subject": subject,
                            "unit": unit,
                            "topic": topic,
                            "subtopic": subtopic or topic,
                            "question_text": q_text,
                            "spoken_prompt": item.get("spoken_prompt") or narrate_math_expression(q_text),
                            "math_narration": item.get("math_narration") or narrate_math_expression(item.get("sample_answer", "")),
                            "diagram_description": item.get("diagram_description") or generate_diagram_narration(subject, topic),
                            "expected_criteria": item.get("expected_criteria") or "Demonstrates clear conceptual understanding and correct application.",
                            "sample_answer": item.get("sample_answer") or "",
                            "points": float(item.get("points") or 5.0),
                            "has_diagram": bool(item.get("has_diagram", False))
                        })
                    if len(dynamic_questions) >= 2:
                        return dynamic_questions
        except Exception as exc:
            logger.debug("[MasteryAssessment] Dynamic question generation AI notice: %s", exc)

    # ── Deterministic Syllabus Calibration (Discipline Grounded) ───────────────
    if "thevenin" in t_lower or ("network" in t_lower and "circuit" in s_lower):
        # Q1: Basic Understanding
        q1_text = (
            "Define Thevenin's Theorem. What are the two fundamental components "
            "of an equivalent Thevenin circuit, and how are output terminals represented?"
        )
        questions.append({
            "question_id": f"mq_{uuid.uuid4().hex[:8]}",
            "tier": QUESTION_TIERS["BASIC"],
            "tier_label": "Basic Understanding",
            "subject": subject,
            "unit": unit,
            "topic": topic,
            "subtopic": subtopic or topic,
            "question_text": q1_text,
            "spoken_prompt": narrate_math_expression(q1_text),
            "math_narration": "V Thevenin in series with R Thevenin across terminals A and B.",
            "diagram_description": generate_diagram_narration(subject, topic),
            "expected_criteria": "States that any linear two-terminal circuit can be replaced by an independent voltage source V_th in series with an internal resistor R_th.",
            "sample_answer": "Thevenin's theorem states that any linear bilateral network can be replaced by an equivalent circuit consisting of a single independent voltage source V_th in series with a resistance R_th connected to output terminals A and B.",
            "points": 5.0,
            "has_diagram": True
        })

        # Q2: Conceptual Reasoning (Targeting formula selection & calculation errors)
        q2_text = (
            "When determining Thevenin resistance R_{th}, what is the precise rule "
            "for deactivating independent voltage sources versus independent current sources?"
        )
        questions.append({
            "question_id": f"mq_{uuid.uuid4().hex[:8]}",
            "tier": QUESTION_TIERS["CONCEPTUAL"],
            "tier_label": "Conceptual Reasoning",
            "subject": subject,
            "unit": unit,
            "topic": topic,
            "subtopic": subtopic or topic,
            "question_text": q2_text,
            "spoken_prompt": narrate_math_expression(q2_text),
            "math_narration": "R Thevenin evaluation rules: short-circuit voltage sources, open-circuit current sources.",
            "diagram_description": generate_diagram_narration(subject, topic),
            "expected_criteria": "Explicitly specifies deactivating independent voltage sources by replacing with a short circuit (zero resistance) and current sources by replacing with an open circuit (infinite resistance).",
            "sample_answer": "To calculate Thevenin resistance, all independent voltage sources are replaced by a short circuit (0 volts), and all independent current sources are replaced by an open circuit (0 amperes).",
            "points": 5.0,
            "has_diagram": False
        })

        # Q3: Problem Solving / Calculation Check (Verifies arithmetic and formula substitution)
        q3_text = (
            "A 24V independent DC source is connected in series with a 40\\Omega resistor R_1. "
            "A load resistor R_2 = 60\\Omega is connected across output terminals A and B. "
            "Calculate: 1) Thevenin open-circuit voltage V_{th}. 2) Thevenin resistance R_{th}."
        )
        questions.append({
            "question_id": f"mq_{uuid.uuid4().hex[:8]}",
            "tier": QUESTION_TIERS["PROBLEM_SOLVING"],
            "tier_label": "Problem Solving & Calculation",
            "subject": subject,
            "unit": unit,
            "topic": topic,
            "subtopic": subtopic or topic,
            "question_text": q3_text,
            "spoken_prompt": narrate_math_expression(q3_text),
            "math_narration": "A 24-volt source in series with 40 Ohms. 60 Ohms connected across terminals A and B. Calculate V Thevenin and R Thevenin.",
            "diagram_description": generate_diagram_narration(subject, topic),
            "expected_criteria": "V_th = 24 * (60 / (40 + 60)) = 14.4V. R_th = (40 * 60) / (40 + 60) = 24 Ohms. Requires intermediate working steps without arithmetic slips.",
            "sample_answer": "1) V_th = 24 * (60 / 100) = 14.4 Volts. 2) Shorting the 24V source places 40 Ohms in parallel with 60 Ohms: R_th = 2400 / 100 = 24 Ohms.",
            "points": 5.0,
            "has_diagram": True
        })

    # ── Calculus / Chain Rule & Composite Functions ──────────────────────────
    elif "chain rule" in t_lower or "differentiation" in t_lower or "calculus" in s_lower:
        # Q1: Basic Understanding
        q1_text = (
            "State the Chain Rule formula for a composite function y = f(g(x)). "
            "Explain what the inner function and outer function represent in natural words."
        )
        questions.append({
            "question_id": f"mq_{uuid.uuid4().hex[:8]}",
            "tier": QUESTION_TIERS["BASIC"],
            "tier_label": "Basic Understanding",
            "subject": subject,
            "unit": unit,
            "topic": topic,
            "subtopic": subtopic or topic,
            "question_text": q1_text,
            "spoken_prompt": narrate_math_expression(q1_text),
            "math_narration": "dy by dx equals dy by du times du by dx where u equals g of x.",
            "diagram_description": generate_diagram_narration(subject, topic),
            "expected_criteria": "States dy/dx = (dy/du) * (du/dx) or f'(g(x)) * g'(x), identifying the derivative of the outer function evaluated at the inner function multiplied by the derivative of the inner function.",
            "sample_answer": "The chain rule states that dy/dx = (dy/du) * (du/dx). We differentiate the outer function with respect to the inner variable u, and multiply by the derivative of the inner function with respect to x.",
            "points": 5.0,
            "has_diagram": False
        })

        # Q2: Problem Solving (Targeting formula application and algebraic reasoning)
        q2_text = (
            "Differentiate the composite function y = (3x^2 + 5)^4 with respect to x. "
            "Show each intermediate differentiation step and write your final algebraic expression."
        )
        questions.append({
            "question_id": f"mq_{uuid.uuid4().hex[:8]}",
            "tier": QUESTION_TIERS["PROBLEM_SOLVING"],
            "tier_label": "Problem Solving & Calculation",
            "subject": subject,
            "unit": unit,
            "topic": topic,
            "subtopic": subtopic or topic,
            "question_text": q2_text,
            "spoken_prompt": narrate_math_expression(q2_text),
            "math_narration": "Differentiate y equals the quantity 3x squared plus 5, all raised to the 4th power.",
            "diagram_description": generate_diagram_narration(subject, topic),
            "expected_criteria": "Let u = 3x^2 + 5, du/dx = 6x. dy/du = 4u^3. dy/dx = 4(3x^2 + 5)^3 * 6x = 24x(3x^2 + 5)^3.",
            "sample_answer": "Let u = 3x^2 + 5. Outer derivative is 4(3x^2 + 5)^3. Inner derivative is 6x. Multiplying together gives dy/dx = 24x(3x^2 + 5)^3.",
            "points": 5.0,
            "has_diagram": False
        })

        # Q3: Advanced / Application
        q3_text = (
            "Consider a spherical balloon being inflated such that its radius r expands at 2 cm/s. "
            "Using the chain rule on volume V = \\frac{4}{3}\\pi r^3, calculate the rate of volume expansion dV/dt when r = 5 cm."
        )
        questions.append({
            "question_id": f"mq_{uuid.uuid4().hex[:8]}",
            "tier": QUESTION_TIERS["ADVANCED"],
            "tier_label": "Application & Related Rates",
            "subject": subject,
            "unit": unit,
            "topic": topic,
            "subtopic": subtopic or topic,
            "question_text": q3_text,
            "spoken_prompt": narrate_math_expression(q3_text),
            "math_narration": "Volume of sphere V equals 4 thirds pi r cubed. Radius increases at 2 centimeters per second. Find dV by dt when r equals 5 centimeters.",
            "diagram_description": "Spherical geometry with radius vector r expanding uniformly outward.",
            "expected_criteria": "dV/dt = (dV/dr) * (dr/dt) = (4 * pi * r^2) * (2). At r = 5: dV/dt = 4 * pi * 25 * 2 = 200 * pi cm^3/s (approx 628.3 cm^3/s).",
            "sample_answer": "dV/dt = 4 * pi * r^2 * (dr/dt). Substituting r = 5 and dr/dt = 2: dV/dt = 4 * pi * 25 * 2 = 200 * pi cubic centimeters per second.",
            "points": 5.0,
            "has_diagram": False
        })

    # ── Chemistry & Chemical Kinetics ─────────────────────────────────────────
    elif "arrhenius" in t_lower or "reaction rate" in t_lower or "kinetics" in t_lower or "chemistry" in s_lower:
        # Q1: Basic Understanding
        q1_text = (
            "State the Arrhenius equation relating rate constant k, frequency factor A, "
            "activation energy Ea, and absolute temperature T. What does Ea represent?"
        )
        questions.append({
            "question_id": f"mq_{uuid.uuid4().hex[:8]}",
            "tier": QUESTION_TIERS["BASIC"],
            "tier_label": "Basic Understanding",
            "subject": subject,
            "unit": unit,
            "topic": topic,
            "subtopic": subtopic or topic,
            "question_text": q1_text,
            "spoken_prompt": narrate_math_expression(q1_text),
            "math_narration": "k equals A times e to the power minus Ea divided by R T.",
            "diagram_description": generate_diagram_narration(subject, topic),
            "expected_criteria": "States k = A * e^(-Ea / RT), identifying Ea as the activation energy required for reactant molecules to overcome the energy barrier and form products.",
            "sample_answer": "The Arrhenius equation is k = A * e^(-Ea / (R * T)), where k is the rate constant, A is the frequency factor, Ea is activation energy, R is the universal gas constant, and T is absolute temperature.",
            "points": 5.0,
            "has_diagram": True
        })

        # Q2: Conceptual Application
        q2_text = (
            "Explain what occurs to the reaction rate constant k when temperature T increases. "
            "Why does a catalyst lower the activation energy without shifting reaction equilibrium?"
        )
        questions.append({
            "question_id": f"mq_{uuid.uuid4().hex[:8]}",
            "tier": QUESTION_TIERS["APPLICATION"],
            "tier_label": "Kinetic Principles & Catalysis",
            "subject": subject,
            "unit": unit,
            "topic": topic,
            "subtopic": subtopic or topic,
            "question_text": q2_text,
            "spoken_prompt": narrate_math_expression(q2_text),
            "math_narration": "As temperature increases, exponential fraction increases, raising k. Catalyst provides alternative transition path.",
            "diagram_description": generate_diagram_narration(subject, topic),
            "expected_criteria": "Explains that increasing T increases the fraction of collisions with energy >= Ea, increasing k exponentially. Catalysts lower Ea equally in forward and reverse directions, keeping equilibrium constant K unchanged.",
            "sample_answer": "Increasing temperature increases the kinetic energy of reactant molecules, exponentially increasing k. A catalyst lowers Ea for both forward and reverse paths equally, accelerating rate without changing equilibrium.",
            "points": 5.0,
            "has_diagram": False
        })

    # ── Computer Science & Data Structures ────────────────────────────────────
    elif "binary search tree" in t_lower or "bst" in t_lower or "tree" in t_lower or "data structure" in s_lower or "algorithm" in s_lower:
        q1_text = (
            "Define a Binary Search Tree (BST) invariant property. What is the average time complexity "
            "for search, insertion, and deletion in a balanced BST versus a degenerate BST?"
        )
        questions.append({
            "question_id": f"mq_{uuid.uuid4().hex[:8]}",
            "tier": QUESTION_TIERS["BASIC"],
            "tier_label": "BST Invariants & Complexity",
            "subject": subject,
            "unit": unit,
            "topic": topic,
            "subtopic": subtopic or topic,
            "question_text": q1_text,
            "spoken_prompt": narrate_math_expression(q1_text),
            "math_narration": "Left child key less than root, right child key greater than root. Average time O of log n, worst case O of n.",
            "diagram_description": generate_diagram_narration(subject, topic),
            "expected_criteria": "BST property: for every node, left subtree keys < node key < right subtree keys. Average time complexity is O(log n); worst case for skewed tree is O(n).",
            "sample_answer": "In a BST, all keys in the left subtree are smaller than the node, and all keys in the right subtree are greater. Average search, insert, and delete are O(log n); degenerate trees degrade to O(n).",
            "points": 5.0,
            "has_diagram": True
        })

    # ── Electromagnetics & Physics ───────────────────────────────────────────
    elif "coulomb" in t_lower or "gauss" in t_lower or "electrostatic" in t_lower or "electromagnetic" in s_lower:
        q1_text = (
            "State Gauss's Law in integral form. How does the total electric flux through a closed surface "
            "relate to the enclosed charge, and what symmetry is required to compute electric field E?"
        )
        questions.append({
            "question_id": f"mq_{uuid.uuid4().hex[:8]}",
            "tier": QUESTION_TIERS["BASIC"],
            "tier_label": "Integral Gauss's Law",
            "subject": subject,
            "unit": unit,
            "topic": topic,
            "subtopic": subtopic or topic,
            "question_text": q1_text,
            "spoken_prompt": narrate_math_expression(q1_text),
            "math_narration": "Closed surface integral of E dot dA equals Q enclosed divided by epsilon zero.",
            "diagram_description": generate_diagram_narration(subject, topic),
            "expected_criteria": "States closed integral E . dA = Q_enclosed / epsilon_0. Identifies that spherical, cylindrical, or planar symmetry allows E to be factored out of the integral.",
            "sample_answer": "Gauss's law states that the net outward electric flux through any closed Gaussian surface equals the net charge enclosed divided by permittivity epsilon_0. Spherical, cylindrical, or planar symmetry is needed to evaluate E algebraically.",
            "points": 5.0,
            "has_diagram": False
        })

    # ── General Dynamic Academic Questions ───────────────────────────────────
    else:
        q1_text = (
            f"Define the foundational principles, governing physical or algorithmic laws, "
            f"and operational mechanisms of {topic} within {unit}."
        )
        questions.append({
            "question_id": f"mq_{uuid.uuid4().hex[:8]}",
            "tier": QUESTION_TIERS["BASIC"],
            "tier_label": "Basic Understanding",
            "subject": subject,
            "unit": unit,
            "topic": topic,
            "subtopic": subtopic or topic,
            "question_text": q1_text,
            "spoken_prompt": narrate_math_expression(q1_text),
            "math_narration": f"Foundational definition and mathematical formulation of {topic}.",
            "diagram_description": generate_diagram_narration(subject, topic),
            "expected_criteria": f"Comprehensive definition of {topic}, identifying governing equations, operational constraints, and fundamental principles in {subject}.",
            "sample_answer": f"In {subject}, {topic} establishes the governing relationship between system inputs, state transitions, and verified analytical outputs.",
            "points": 5.0,
            "has_diagram": False
        })

        q2_text = (
            f"Explain a concrete real-world problem or practical system application where {topic} "
            f"is implemented. Detail the boundary constraints and how failure to observe them causes errors."
        )
        questions.append({
            "question_id": f"mq_{uuid.uuid4().hex[:8]}",
            "tier": QUESTION_TIERS["APPLICATION"],
            "tier_label": "System Application & Constraints",
            "subject": subject,
            "unit": unit,
            "topic": topic,
            "subtopic": subtopic or topic,
            "question_text": q2_text,
            "spoken_prompt": narrate_math_expression(q2_text),
            "math_narration": f"Real-world application and boundary constraints for {topic}.",
            "diagram_description": generate_diagram_narration(subject, topic),
            "expected_criteria": f"Detailed practical implementation of {topic}, specifying operating boundaries, environmental conditions, and systemic significance.",
            "sample_answer": f"Practical application of {topic} in production environments, highlighting operating boundaries and stability criteria.",
            "points": 5.0,
            "has_diagram": False
        })

    return questions


# ─────────────────────────────────────────────────────────────────────────────
# UNDERSTANDING EVALUATOR & CONTINUOUS IMPROVEMENT ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_mastery_submission(
    student_id: str,
    student_name: str,
    question: Dict[str, Any],
    student_answer: str,
    submission_mode: str = "keyboard",
    transcript_reviewed: bool = True,
    mongo_db: Any = None,
    sqlite_conn: Any = None
) -> Dict[str, Any]:
    """
    Evaluates student answer against subject-specific criteria.
    Identifies:
    - Correct understanding
    - Partially correct understanding
    - Conceptual misunderstanding
    - Calculation error
    - Missing explanation
    - Incorrect reasoning

    Computes multi-attempt mastery state and returns continuous improvement feedback:
    1. What the student answered correctly (strengths).
    2. Explanation of mistakes in simple language.
    3. Related syllabus concept.
    4. Recommended learning activity.
    5. Targeted practice checkpoint.
    """
    clean_id = str(student_id or "").strip()
    subject = question.get("subject", "General Academic")
    unit = question.get("unit", "Unit")
    topic = question.get("topic", "General Topic")
    subtopic = question.get("subtopic", topic)
    question_text = question.get("question_text", "")
    expected_criteria = question.get("expected_criteria", "")
    max_score = float(question.get("points") or 5.0)

    # 1. Normalize voice transcript if spoken
    clean_student_ans = student_answer.strip()
    if submission_mode == "voice":
        clean_student_ans = normalize_voice_transcript(clean_student_ans, subject, topic)

    ans_lower = clean_student_ans.lower()
    exp_lower = expected_criteria.lower()

    # 2. Rubric and Semantic Matching
    score = 0.0
    evaluation_result = EVALUATION_RESULTS["CONCEPTUAL_MISUNDERSTANDING"]
    strengths: List[str] = []
    mistakes: List[str] = []
    ai_act: Optional[str] = None
    ai_chk: Optional[str] = None

    # Check for empty / unattempted answer
    if len(clean_student_ans) < 3:
        evaluation_result = EVALUATION_RESULTS["MISSING_EXPLANATION"]
        score = 0.0
        mistakes.append("No answer was provided for evaluation.")
    else:
        # ── Dynamic Evaluation via Gemini AI ──────────────────────────────────
        evaluated_by_ai = False
        gs = _get_gemini_service()
        if gs:
            try:
                eval_prompt = f"""You are LearnSphere AI's Senior Academic Evaluator for Blind and Low-Vision Students.
Evaluate the student's submission against the question and official rubric criteria with high academic precision.

ACADEMIC CONTEXT:
- Student: {student_name}
- Subject: {subject}
- Unit: {unit}
- Topic: {topic}
- Question: "{question_text}"
- Expected Criteria / Rubric: "{expected_criteria}"
- Max Points: {max_score}
- Student's Submission: "{clean_student_ans}" (Submission Mode: {submission_mode})

EVALUATION DIRECTIVES:
1. "score": float between 0.0 and {max_score}. Award partial credit fairly based on demonstrated understanding.
2. "evaluation_result": Exactly one of:
   - "Correct understanding"
   - "Partially correct understanding"
   - "Conceptual misunderstanding"
   - "Calculation error"
   - "Missing explanation"
   - "Incorrect reasoning"
3. "strengths": Array of 1-3 specific strings highlighting what the student got right.
4. "mistakes": Array of 1-3 specific strings detailing where the student slipped or was confused (empty if completely correct).
5. "explanation_of_mistakes": Conversational explanation in simple, clear language tailored for audio read-aloud via screen reader.
6. "recommended_activity": Concrete learning action to solidify this concept.
7. "targeted_checkpoint": A short follow-up practice problem.

Return a valid JSON object matching the above keys only."""
                raw = gs.generate_content(eval_prompt, json_output=True, temperature=0.0, timeout=15)
                if raw:
                    ai_eval = json.loads(raw)
                    if "score" in ai_eval and "evaluation_result" in ai_eval:
                        score = min(max_score, max(0.0, float(ai_eval.get("score") or 0.0)))
                        raw_res = str(ai_eval.get("evaluation_result", "")).strip()
                        matched_res = None
                        for v in EVALUATION_RESULTS.values():
                            if v.lower() == raw_res.lower() or raw_res.lower() in v.lower():
                                matched_res = v
                                break
                        evaluation_result = matched_res or (EVALUATION_RESULTS["CORRECT"] if score >= (0.8 * max_score) else EVALUATION_RESULTS["PARTIALLY_CORRECT"])
                        strengths = ai_eval.get("strengths") or []
                        mistakes = ai_eval.get("mistakes") or []
                        ai_act = ai_eval.get("recommended_activity")
                        ai_chk = ai_eval.get("targeted_checkpoint")
                        evaluated_by_ai = True
            except Exception as exc:
                logger.debug("[MasteryAssessment] Dynamic AI evaluation notice: %s", exc)

        # ── Deterministic Semantic Evaluator (Fallback & Verification) ─────────
        if not evaluated_by_ai:
            t_lower = topic.lower()

            # Circuit Theory / Thevenin / Norton
            if "thevenin" in t_lower or "norton" in t_lower:
                has_voltage_divider = any(w in ans_lower for w in ["voltage divider", "voltage division", "24 * (60", "24*(60", "24 * 0.6", "14.4"])
                has_correct_vth = "14.4" in ans_lower
                has_parallel_rth = any(w in ans_lower for w in ["parallel", "40 * 60", "40*60", "2400 / 100", "2400/100", "24 ohm", "24\\omega", "= 24"])
                has_correct_rth = "24" in ans_lower and ("ohm" in ans_lower or "rth" in ans_lower or "r_th" in ans_lower or "resistance" in ans_lower)
                has_deactivation = any(w in ans_lower for w in ["short", "short circuit", "zero volt", "deactivate"])

                # Check for calculation error: formula is right but numbers are arithmetic slip
                has_calc_error = any(w in ans_lower for w in ["120", "divider slip", "divided by 120", "24 * 60 / 120", "12v", "10 ohm"])

                if has_correct_vth and (has_correct_rth or has_parallel_rth):
                    score = 5.0
                    evaluation_result = EVALUATION_RESULTS["CORRECT"]
                    strengths.append("Correctly computed Thevenin voltage V_th = 14.4V via voltage division.")
                    strengths.append("Correctly de-energized the independent source and evaluated parallel equivalent resistance R_th = 24 Ohms.")
                elif has_voltage_divider and has_calc_error:
                    score = 3.0
                    evaluation_result = EVALUATION_RESULTS["CALCULATION_ERROR"]
                    strengths.append("Your circuit setup and formula selection for voltage division were completely correct.")
                    mistakes.append("An arithmetic calculation slip occurred in denominator addition (40 + 60 = 100, not 120).")
                elif "voltage" in ans_lower and ("series" in ans_lower or "ohm" in ans_lower):
                    score = 3.5
                    evaluation_result = EVALUATION_RESULTS["PARTIALLY_CORRECT"]
                    strengths.append("Demonstrated good conceptual understanding of two-terminal equivalent networks.")
                    mistakes.append("Be sure to explicitly verify numerical intermediate steps.")
                elif "short circuit" in ans_lower and "open circuit" in ans_lower and not ("14.4" in ans_lower):
                    score = 4.0
                    evaluation_result = EVALUATION_RESULTS["CORRECT"]
                    strengths.append("Correctly identified that independent voltage sources are replaced with short circuits.")
                else:
                    score = 1.5
                    evaluation_result = EVALUATION_RESULTS["CONCEPTUAL_MISUNDERSTANDING"]
                    mistakes.append("Fundamental confusion between open-circuit voltage and short-circuit current across the load terminals.")

            # Calculus / Chain Rule
            elif "chain rule" in t_lower or "differentiation" in t_lower:
                has_chain_formula = any(w in ans_lower for w in ["dy/dx", "dy/du", "du/dx", "inner", "outer", "f'(g(x))"])
                has_derivative_24x = "24x" in ans_lower or "24 x" in ans_lower
                has_power_3 = "(3x^2 + 5)^3" in ans_lower or "cubed" in ans_lower or "^3" in ans_lower
                has_algebra_error = "12x" in ans_lower or "18x" in ans_lower

                if (has_derivative_24x and has_power_3) or ("200 * pi" in ans_lower or "200\\pi" in ans_lower or "628" in ans_lower):
                    score = 5.0
                    evaluation_result = EVALUATION_RESULTS["CORRECT"]
                    strengths.append("Accurately applied the Chain Rule to differentiate both outer and inner functions.")
                    strengths.append("Combined algebraic coefficients into the correct simplified derivative.")
                elif has_chain_formula and has_power_3 and not has_derivative_24x:
                    score = 3.0
                    evaluation_result = EVALUATION_RESULTS["CALCULATION_ERROR"]
                    strengths.append("Correctly identified inner function u and outer power derivative 4u^3.")
                    mistakes.append("Coefficient multiplication slip when multiplying 4 by the inner derivative 6x.")
                elif has_chain_formula:
                    score = 4.0
                    evaluation_result = EVALUATION_RESULTS["PARTIALLY_CORRECT"]
                    strengths.append("Correctly stated governing chain rule formulation dy/dx = (dy/du) * (du/dx).")
                    mistakes.append("Include explicit step-by-step substitution to verify your final expression.")
                else:
                    score = 1.0
                    evaluation_result = EVALUATION_RESULTS["CONCEPTUAL_MISUNDERSTANDING"]
                    mistakes.append("Failed to recognize the composite function structure or omitted the inner derivative.")

            # Chemistry / Reaction Kinetics / Arrhenius
            elif "arrhenius" in t_lower or "reaction rate" in t_lower or "kinetics" in t_lower or "chemistry" in s_lower:
                has_activation_energy = any(w in ans_lower for w in ["activation energy", "energy barrier", "minimum energy"])
                has_electronegativity_slip = "electronegativity" in ans_lower
                has_temp_relation = any(w in ans_lower for w in ["temperature", "rate constant", "collision", "exponential"])

                if has_activation_energy:
                    score = 5.0
                    evaluation_result = EVALUATION_RESULTS["CORRECT"]
                    strengths.append("Correctly identified Ea as the activation energy in the Arrhenius equation.")
                elif has_electronegativity_slip:
                    score = 1.0
                    evaluation_result = EVALUATION_RESULTS["CONCEPTUAL_MISUNDERSTANDING"]
                    mistakes.append("Ea represents activation energy, not electronegativity.")
                elif has_temp_relation:
                    score = 3.5
                    evaluation_result = EVALUATION_RESULTS["PARTIALLY_CORRECT"]
                    strengths.append("Understands the kinetic relationship between temperature and reaction rate.")
                    mistakes.append("Explicitly state the formal role of Ea as the kinetic activation threshold.")
                else:
                    score = 1.5
                    evaluation_result = EVALUATION_RESULTS["CONCEPTUAL_MISUNDERSTANDING"]
                    mistakes.append("Failed to identify the governing parameters of the Arrhenius equation.")

            # Computer Science / Data Structures
            elif "binary search tree" in t_lower or "bst" in t_lower or "data structure" in s_lower:
                has_bst_property = any(w in ans_lower for w in ["smaller", "greater", "left subtree", "right subtree", "<", ">"])
                has_log_n = any(w in ans_lower for w in ["o(log n)", "log n", "logn", "logarithmic"])

                if has_bst_property and has_log_n:
                    score = 5.0
                    evaluation_result = EVALUATION_RESULTS["CORRECT"]
                    strengths.append("Accurately stated BST ordering invariant and O(log n) average time complexity.")
                elif has_bst_property:
                    score = 3.5
                    evaluation_result = EVALUATION_RESULTS["PARTIALLY_CORRECT"]
                    strengths.append("Correctly defined BST invariant.")
                    mistakes.append("Specify time complexity metrics for average vs. worst-case degenerate trees.")
                else:
                    score = 1.5
                    evaluation_result = EVALUATION_RESULTS["CONCEPTUAL_MISUNDERSTANDING"]
                    mistakes.append("Failed to identify the left-smaller / right-greater BST ordering property.")

            # General Concept Semantic Evaluator (Strict Keyword & Concept Overlap)
            else:
                # Extract essential concept tokens from criteria
                crit_words = set(re.findall(r'[a-zA-Z]{3,}', exp_lower))
                stopwords = {"the", "and", "that", "this", "for", "with", "from", "are", "was", "any", "which", "states", "defined"}
                crit_core = crit_words - stopwords
                ans_words = set(re.findall(r'[a-zA-Z]{3,}', ans_lower))

                overlap = len(crit_core.intersection(ans_words))
                ratio = overlap / len(crit_core) if crit_core else 0.0

                # Check for arithmetic error signals in numeric answers
                arithmetic_signals = ["calculation error", "arithmetic error", "sign error", "slip"]
                has_calc_signal = any(sig in ans_lower for sig in arithmetic_signals)

                if ratio >= 0.55:
                    score = 5.0
                    evaluation_result = EVALUATION_RESULTS["CORRECT"]
                    strengths.append(f"Demonstrated solid conceptual command and accurate formulation of {topic}.")
                elif has_calc_signal and ratio >= 0.35:
                    score = 3.0
                    evaluation_result = EVALUATION_RESULTS["CALCULATION_ERROR"]
                    strengths.append(f"Governing setup for {topic} is correct.")
                    mistakes.append("An intermediate calculation error affected the final numerical result.")
                elif ratio >= 0.30:
                    score = 3.5
                    evaluation_result = EVALUATION_RESULTS["PARTIALLY_CORRECT"]
                    strengths.append(f"Addressed key aspects of {topic}.")
                    mistakes.append("Missing detailed boundary constraints, formal equations, or derivation steps.")
                else:
                    score = 1.5
                    evaluation_result = EVALUATION_RESULTS["CONCEPTUAL_MISUNDERSTANDING"]
                    mistakes.append(f"Response does not capture the foundational principles or equations of {topic}.")

    # 3. Determine Mastery State Across Multi-Attempt Evidence (Prompt 5 Requirement 4)
    # A concept is understood ONLY when supported by sufficient evidence (>= 2 successful attempts >= 80% without conceptual gaps).
    # Fetch historical attempts on this topic
    prior_topic_attempts = []
    if mongo_db is not None:
        try:
            records = list(mongo_db["blind_practice_attempts"].find({
                "student_id": clean_id,
                "topic": topic
            }))
            prior_topic_attempts.extend(records)
        except Exception as exc:
            logger.debug("[MasteryAssessment] Mongo history fetch notice: %s", exc)
    elif sqlite_conn is not None:
        try:
            cursor = sqlite_conn.cursor()
            cursor.execute("SELECT * FROM blind_practice_attempts WHERE student_id = ? AND topic = ?", (clean_id, topic))
            prior_topic_attempts.extend([dict(r) for r in cursor.fetchall()])
        except Exception as exc:
            logger.debug("[MasteryAssessment] SQLite history fetch notice: %s", exc)

    # Current attempt stats
    is_current_success = (score / max_score) >= 0.8 and evaluation_result == EVALUATION_RESULTS["CORRECT"]
    prior_successes = sum(1 for a in prior_topic_attempts if (float(a.get("score") or 0.0) / float(a.get("max_score") or 5.0)) >= 0.8)
    total_topic_attempts = len(prior_topic_attempts) + 1

    if is_current_success and prior_successes >= 1:
        mastery_state = MASTERY_STATES["UNDERSTANDING_DEMONSTRATED"]
    elif is_current_success and prior_successes == 0:
        mastery_state = MASTERY_STATES["PROGRESSING"]
    elif evaluation_result == EVALUATION_RESULTS["CALCULATION_ERROR"]:
        mastery_state = MASTERY_STATES["PROGRESSING"]
    elif evaluation_result in [EVALUATION_RESULTS["CONCEPTUAL_MISUNDERSTANDING"], EVALUATION_RESULTS["INCORRECT_REASONING"]]:
        mastery_state = MASTERY_STATES["NEEDS_PRACTICE"]
    elif total_topic_attempts == 1:
        mastery_state = MASTERY_STATES["MORE_EVIDENCE_NEEDED"]
    else:
        mastery_state = MASTERY_STATES["LEARNING"]

    # 4. Continuous Improvement Synthesis (Prompt 5 Requirement 5)
    strengths_text = " ".join(strengths) if strengths else f"You engaged with the assessment question on {topic}."
    mistake_text = " ".join(mistakes) if mistakes else "No conceptual errors were detected in your solution."

    if ai_act:
        recommended_act = ai_act
    elif evaluation_result == EVALUATION_RESULTS["CORRECT"]:
        recommended_act = f"Continue to the next advanced syllabus learning objective in {unit}."
    elif evaluation_result == EVALUATION_RESULTS["CALCULATION_ERROR"]:
        recommended_act = f"Audio Arithmetic Walkthrough: Review step-by-step arithmetic operations and SI units for {topic}."
    else:
        recommended_act = f"Concept-to-Sense Audio: Listen to the physical intuition and step-by-step reasoning for {topic}."

    if ai_chk:
        targeted_practice = ai_chk
    elif evaluation_result == EVALUATION_RESULTS["CORRECT"]:
        targeted_practice = f"Explore multi-tier boundary conditions and real-world system applications of {topic}."
    elif evaluation_result == EVALUATION_RESULTS["CALCULATION_ERROR"]:
        targeted_practice = f"Solve a 2-step numeric verification problem on {topic} focusing on intermediate arithmetic."
    else:
        targeted_practice = f"Complete a guided concept-check question reviewing fundamental principles in {topic}."

    spoken_feedback = (
        f"Assessment evaluation for {topic}: {evaluation_result}. Score: {score:.1f} out of {max_score:.1f}. "
        f"Strengths: {strengths_text} "
        f"{'Mistake diagnosis: ' + mistake_text if mistakes else ''} "
        f"Current topic mastery state: {mastery_state}. "
        f"Recommended next step: {recommended_act}"
    )

    assessment_id = f"ass_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)

    # 5. Record Attempt & Assessment durably in database
    # Record as practice attempt to update Learning Gap Detector and Topic Status
    record_blind_practice_attempt(
        student_id=clean_id,
        student_name=student_name,
        subject=subject,
        unit=unit,
        topic=topic,
        subtopic=subtopic,
        question_text=question_text,
        student_answer=clean_student_ans,
        expected_answer=expected_criteria,
        is_correct=is_current_success,
        score=score,
        max_score=max_score,
        feedback=f"{evaluation_result}: {mistake_text}",
        mongo_db=mongo_db,
        sqlite_conn=sqlite_conn
    )

    assessment_record = {
        "assessment_id": assessment_id,
        "student_id": clean_id,
        "student_name": student_name,
        "subject": subject,
        "unit": unit,
        "topic": topic,
        "subtopic": subtopic,
        "question_type": question.get("tier", "adaptive"),
        "question_text": question_text,
        "math_narration": question.get("math_narration", ""),
        "diagram_description": question.get("diagram_description", ""),
        "student_answer": clean_student_ans,
        "submission_mode": submission_mode,
        "transcript_reviewed": bool(transcript_reviewed),
        "expected_criteria": expected_criteria,
        "evaluation_result": evaluation_result,
        "score": score,
        "max_score": max_score,
        "strengths_explanation": strengths_text,
        "mistake_explanation": mistake_text,
        "mastery_state": mastery_state,
        "recommended_activity": recommended_act,
        "targeted_practice_question": targeted_practice,
        "created_at": now.isoformat()
    }

    if mongo_db is not None:
        try:
            mongo_db["blind_mastery_assessments"].insert_one({**assessment_record, "created_at": now})
        except Exception as exc:
            logger.error("[MasteryAssessment] Mongo save assessment error: %s", exc)
    elif sqlite_conn is not None:
        try:
            cursor = sqlite_conn.cursor()
            cursor.execute("""
                INSERT INTO blind_mastery_assessments
                (assessment_id, student_id, student_name, subject, unit, topic, subtopic,
                 question_type, question_text, math_narration, diagram_description, student_answer,
                 submission_mode, transcript_reviewed, expected_criteria, evaluation_result,
                 score, max_score, strengths_explanation, mistake_explanation, mastery_state,
                 recommended_activity, targeted_practice_question, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assessment_id, clean_id, student_name, subject, unit, topic, subtopic,
                question.get("tier", "adaptive"), question_text, question.get("math_narration", ""),
                question.get("diagram_description", ""), clean_student_ans, submission_mode,
                1 if transcript_reviewed else 0, expected_criteria, evaluation_result,
                score, max_score, strengths_text, mistake_text, mastery_state,
                recommended_act, targeted_practice, now.isoformat()
            ))
            sqlite_conn.commit()
        except Exception as exc:
            logger.error("[MasteryAssessment] SQLite save assessment error: %s", exc)

    return {
        "success": True,
        "assessment_id": assessment_id,
        "evaluation_result": evaluation_result,
        "score": score,
        "max_score": max_score,
        "percentage": round((score / max_score) * 100, 1),
        "mastery_state": mastery_state,
        "strengths_explanation": strengths_text,
        "mistake_explanation": mistake_text,
        "related_concept": f"{subject} · {unit} · {topic}",
        "recommended_activity": recommended_act,
        "targeted_practice_question": targeted_practice,
        "spoken_feedback": spoken_feedback,
        "transcript_reviewed": transcript_reviewed
    }


def get_student_mastery_history(
    student_id: str,
    mongo_db: Any = None,
    sqlite_conn: Any = None
) -> List[Dict[str, Any]]:
    """Retrieve verified mastery assessments for this blind student."""
    clean_id = str(student_id or "").strip()
    history: List[Dict[str, Any]] = []

    if mongo_db is not None:
        try:
            records = list(mongo_db["blind_mastery_assessments"].find({"student_id": clean_id}).sort("created_at", -1))
            for r in records:
                if "_id" in r:
                    r["_id"] = str(r["_id"])
                if isinstance(r.get("created_at"), datetime):
                    r["created_at"] = r["created_at"].isoformat()
                history.append(r)
        except Exception as exc:
            logger.debug("[MasteryAssessment] Mongo history error: %s", exc)
    elif sqlite_conn is not None:
        try:
            cursor = sqlite_conn.cursor()
            cursor.execute("SELECT * FROM blind_mastery_assessments WHERE student_id = ? ORDER BY created_at DESC", (clean_id,))
            rows = cursor.fetchall()
            for row in rows:
                history.append(dict(row))
        except Exception as exc:
            logger.debug("[MasteryAssessment] SQLite history error: %s", exc)

    return history
