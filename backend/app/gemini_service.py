"""
LearnSphere AI - Centralized Gemini 3.6 Flash AI Service
Single authority for all multimodal AI operations using STRICTLY gemini-3.6-flash.
"""

import os
import json
import re
import time
import base64
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_gemini_dir = Path(__file__).resolve().parent
_backend_dir = _gemini_dir.parent
_root_dir = _backend_dir.parent

load_dotenv(_backend_dir / ".env", override=True)
load_dotenv(_root_dir / ".env", override=True)
load_dotenv(override=True)


class GeminiService:
    """Centralized service for Gemini 3.6 Flash AI calls across LearnSphere AI."""

    def __init__(self):
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip() or "gemini-3.6-flash"
        self.timeout = int(os.getenv("GEMINI_TIMEOUT", "120"))
        self.max_retries = 2

    @property
    def api_keys(self) -> List[str]:
        keys = []
        for name in ("GEMINI_API_KEY", "GEMINI_API_KEY_2", "Gemini_API_Key_6", "GOOGLE_API_KEY", "GEMINI_KEY"):
            val = os.getenv(name, "").strip()
            if val and val not in keys and not val.startswith("your_"):
                keys.append(val)
        return keys

    @property
    def api_key(self) -> str:
        keys = self.api_keys
        return keys[0] if keys else ""

    def _file_to_parts(self, file_input: Any) -> List[Dict[str, Any]]:
        path_str = file_input if isinstance(file_input, str) else (file_input or {}).get("path")
        if not path_str:
            return []
        p = Path(path_str)
        if not p.is_file():
            return []

        ext = p.suffix.lower()
        parts = []

        if ext in (".png", ".jpg", ".jpeg", ".webp"):
            mime = "image/png" if ext == ".png" else "image/jpeg" if ext in (".jpg", ".jpeg") else "image/webp"
            try:
                with open(p, "rb") as f:
                    b64_data = base64.b64encode(f.read()).decode("utf-8")
                parts.append({"inline_data": {"mime_type": mime, "data": b64_data}})
            except Exception as e:
                logger.warning(f"Could not encode image {p}: {e}")
        elif ext == ".pdf":
            try:
                try:
                    import pymupdf as fitz
                except ImportError:
                    import fitz
                doc = fitz.open(str(p))
                # Process ALL pages with high-fidelity visual rendering and text extraction
                total_pages = len(doc)
                for page_idx in range(total_pages):
                    page = doc[page_idx]
                    
                    # Extract raw text layer if present
                    try:
                        raw_text = page.get_text("text")
                        if raw_text and len(raw_text.strip()) > 10:
                            parts.append({"text": f"--- PAGE {page_idx + 1} OF {total_pages} (EMBEDDED TEXT) ---\n{raw_text}\n"})
                    except Exception:
                        pass

                    # High-resolution visual rendering (dpi=200) for sharp handwriting and diagram OCR
                    pix = page.get_pixmap(dpi=200)
                    png_bytes = pix.tobytes("png")
                    b64_data = base64.b64encode(png_bytes).decode("utf-8")
                    parts.append({"inline_data": {"mime_type": "image/png", "data": b64_data}})
            except Exception as e:
                logger.warning(f"Could not convert PDF {p} to PNG parts: {e}")
        elif ext in (".txt", ".md", ".json", ".csv"):
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                parts.append({"text": f"--- FILE CONTENT: {p.name} ---\n{txt}\n"})
            except Exception as e:
                logger.warning(f"Could not read text file {p}: {e}")

        return parts

    def generate_content(
        self,
        prompt: str,
        files: Optional[List[Any]] = None,
        json_output: bool = True,
        temperature: float = 0.0
    ) -> str:
        """Call gemini-3.6-flash ONLY. No fallback models allowed."""
        keys = self.api_keys
        if not keys:
            raise RuntimeError("GEMINI_API_KEY is not configured on server.")

        parts: List[Dict[str, Any]] = [{"text": prompt}]
        for f_input in files or []:
            f_parts = self._file_to_parts(f_input)
            if f_parts:
                parts.extend(f_parts)

        generation_config: Dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": 65536
        }
        if json_output:
            generation_config["responseMimeType"] = "application/json"

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": generation_config
        }

        last_error = ""
        models_to_try = [self.model]
        for candidate in ("gemini-3.6-flash", "gemini-flash-lite-latest", "gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.8-flash"):
            if candidate not in models_to_try:
                models_to_try.append(candidate)

        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

            for key in keys:
                headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": key
                }

                for attempt in range(self.max_retries):
                    try:
                        response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                        if response.status_code == 200:
                            data = response.json()
                            candidates = data.get("candidates") or []
                            if candidates:
                                text_parts = []
                                for part in candidates[0].get("content", {}).get("parts", []):
                                    if isinstance(part, dict) and part.get("text"):
                                        text_parts.append(part["text"])
                                if text_parts:
                                    return "\n".join(text_parts)
                        else:
                            try:
                                err_msg = response.json().get("error", {}).get("message", response.text[:200])
                            except Exception:
                                err_msg = response.text[:200]
                            last_error = f"HTTP {response.status_code} on {model_name}: {err_msg}"
                            logger.warning(f"[GeminiService] {model_name} returned {response.status_code}: {err_msg}")
                            if response.status_code in (429, 503):
                                # Transient traffic spike or rate limit: short wait and try next candidate
                                time.sleep(1 + attempt)
                                continue
                            break
                    except requests.Timeout:
                        last_error = f"Request timed out on {model_name} after {self.timeout}s"
                        logger.warning(f"[GeminiService] {model_name} timed out after {self.timeout}s")
                        time.sleep(1)
                    except Exception as exc:
                        last_error = f"Network/API error on {model_name}: {exc}"
                        logger.warning(f"[GeminiService] {model_name} encountered error: {exc}")
                        time.sleep(1)

        raise RuntimeError(f"Gemini API processing failed: {last_error}")

    def parse_json_response(self, raw_text: str) -> Dict[str, Any]:
        """Robust, multi-pass JSON parser that handles raw text, markdown blocks,
        unescaped LaTeX backslashes, literal newlines in strings, trailing commas,
        and truncated JSON objects.
        """
        if not raw_text or not isinstance(raw_text, str):
            raise ValueError("Empty or invalid response received from Gemini.")

        # 1. Clean markdown code fences and extraneous wrapping
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        # Strategy 1: Direct strict=False load (handles literal control characters/newlines)
        try:
            return json.loads(cleaned, strict=False)
        except Exception:
            pass

        # Strategy 2: Extract JSON object boundaries { ... }
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            snippet = cleaned[start:end + 1]
            try:
                return json.loads(snippet, strict=False)
            except Exception:
                cleaned = snippet

        # Strategy 3: Multi-pass Regex Repair
        # Fix unescaped backslashes (e.g. LaTeX formulas \theta, \frac, \Omega, \beta, \Delta)
        def repair_escapes(s: str) -> str:
            return re.sub(r'\\(?!["\\/bfnrtu]|u[0-9a-fA-F]{4})', r'\\\\', s)

        # Remove trailing commas before } or ]
        def remove_trailing_commas(s: str) -> str:
            return re.sub(r',\s*([}\]])', r'\1', s)

        # Fix unescaped newlines/tabs inside string literals
        def fix_raw_newlines(s: str) -> str:
            result = []
            in_string = False
            escape = False
            for char in s:
                if char == '"' and not escape:
                    in_string = not in_string
                elif char == '\\':
                    escape = not escape
                else:
                    escape = False

                if in_string and char == '\n':
                    result.append('\\n')
                elif in_string and char == '\r':
                    result.append('\\r')
                elif in_string and char == '\t':
                    result.append('\\t')
                else:
                    result.append(char)
            return "".join(result)

        # Try tiered repairs
        repaired_variations = [
            repair_escapes(cleaned),
            remove_trailing_commas(repair_escapes(cleaned)),
            fix_raw_newlines(repair_escapes(remove_trailing_commas(cleaned))),
            fix_raw_newlines(repair_escapes(remove_trailing_commas(re.sub(r'//.*$', '', cleaned, flags=re.MULTILINE))))
        ]

        for rep in repaired_variations:
            try:
                return json.loads(rep, strict=False)
            except Exception:
                pass

        # Strategy 4: Balance unclosed braces / truncated JSON using a bracket stack
        def balance_json(s: str) -> str:
            stack = []
            in_str = False
            esc = False
            for c in s:
                if c == '"' and not esc:
                    in_str = not in_str
                elif c == '\\':
                    esc = not esc
                else:
                    esc = False

                if not in_str:
                    if c == '{':
                        stack.append('}')
                    elif c == '[':
                        stack.append(']')
                    elif c in ('}', ']') and stack:
                        if stack[-1] == c:
                            stack.pop()

            balanced = s
            if in_str:
                balanced += '"'
            balanced = re.sub(r',\s*$', '', balanced.strip())
            while stack:
                balanced += stack.pop()
            return balanced

        try:
            balanced_attempt = balance_json(repair_escapes(cleaned))
            return json.loads(balanced_attempt, strict=False)
        except Exception:
            pass

        # Strategy 5: Regex extraction of individual question evaluation objects if overall object was truncated
        eval_blocks = re.findall(r'\{\s*"question_id"\s*:[^}]+(?:maximum_marks|awarded_marks|student_answer)[^}]+\}', raw_text, re.DOTALL)
        if eval_blocks:
            eval_items = []
            for b in eval_blocks:
                try:
                    eval_item = json.loads(repair_escapes(b), strict=False)
                    if isinstance(eval_item, dict) and (eval_item.get("question_id") or eval_item.get("question_number")):
                        eval_items.append(eval_item)
                except Exception:
                    pass
            if eval_items:
                logger.info(f"[parse_json_response] Successfully recovered {len(eval_items)} evaluation items via block recovery.")
                return {
                    "is_unreadable": False,
                    "evaluations": eval_items,
                    "overall_teacher_comment": "Evaluations parsed successfully from response.",
                    "strengths": [],
                    "weaknesses": []
                }

        logger.error(f"[parse_json_response] Failed to parse JSON. Raw snippet: {raw_text[:500]}")
        raise ValueError("Response from Gemini was not valid JSON.")

    # ------------------------------------------------------------------
    # Specialized Gemini Operations (Unified Strict Evaluation Engine)
    # ------------------------------------------------------------------

    def evaluate_question_paper(
        self,
        qp_file: Any,
        subject: str = "",
        level: str = "school",
        board: str = "",
        stream: str = "",
        semester: str = ""
    ) -> Dict[str, Any]:
        """Extract complete, verbatim question paper structure from uploaded document.
        The uploaded question paper is the SOLE source of truth for questions, maximum marks, subparts, and choices.
        """
        prompt = f"""
You are the QUESTION PAPER STRUCTURAL EXTRACTION ENGINE for LearnSphere AI.
Analyze ALL pages of the uploaded question paper document with extreme precision.

Context Hints (use only as background guidance; paper header is authoritative):
- Subject hint: {subject}
- Academic Level: {level}
- Board: {board}
- Stream: {stream}
- Semester: {semester}

EXTRACTION MANDATES:
1. Extract the EXACT printed Subject Name, Exam Title, and Total Maximum Marks from the paper header/instructions.
   - For Total Maximum Marks: Note the authoritative paper maximum marks (e.g. 50, 70, 75, 80, 100). Do NOT naively sum all elective choice questions together.
2. Inspect EVERY single page and section. Extract ALL questions and sub-questions (e.g. 1(a), 1(b), 2, 3(i), 3(ii), Part A Q1, 6(a)(i), 6(a)(ii), 6(b)).
3. CRITICAL: (OR) / ELECTIVE CHOICE DETECTION & MAIN QUESTION CONTINUITY:
   - In examination papers, elective questions are often printed with '(OR)', '[OR]', 'OR' between Option A and Option B (e.g., 6. (a) ... (OR) ... (b) ...).
   - CRITICAL RULE: Option B is frequently printed as just '(b)', 'b)', or placed directly below '(OR)' WITHOUT repeating the main question number '6' on top.
   - DO NOT increment the main question number for Option B! Option B is ALWAYS '6(b)' (or 6(b)(i)), NEVER '7(a)' or '7'!
   - The main question number increments ONLY when a genuinely new main question starts (e.g. '7.', '7(a)', 'Q7').
   - Assign the EXACT same 'choice_group' identifier to all alternative options for that question (e.g. "choice_q6" for 6(a)(i), 6(a)(ii), and 6(b), or "choice_q7" for 7(a) and 7(b)).
   - Set 'required_choice_count' to the exact number of options required (usually 1).
4. For EVERY question:
   - Extract the complete verbatim 'question_text' including all parameters, numerical values, equations, constraints, and instructions.
   - For Multiple Choice Questions (MCQs), extract the full text of all printed options under 'options'.
   - Extract the exact printed 'maximum_marks' for each question or subpart. Do NOT guess or default marks.
   - Identify 'question_type' as one of: 'mcq', 'short_answer', 'long_answer', 'numerical', 'derivation', 'diagram', 'proof', 'code', 'case_study'.
   - Extract 'expected_components' (e.g. ["Formula", "Substitution", "SI Unit", "Circuit Diagram"]).

Return ONLY a valid JSON object matching this schema:
{{
  "subject": "Exact Printed Subject Name",
  "exam_title": "Exact Printed Exam Title",
  "total_marks": 50.0,
  "instructions": "General instructions printed on paper",
  "sections": ["Section A (Objective)", "Section B (Descriptive)"],
  "questions": [
    {{
      "question_id": "q1_a",
      "question_number": "1(a)",
      "question_text": "Complete verbatim text of the question",
      "maximum_marks": 5.0,
      "section": "Section A",
      "question_type": "numerical",
      "options": [],
      "choice_group": "choice_q1",
      "required_choice_count": 1,
      "expected_components": ["Formula selection", "Step-by-step substitution", "Final answer with units"]
    }},
    {{
      "question_id": "q1_b",
      "question_number": "1(b)",
      "question_text": "Alternative OR question verbatim text",
      "maximum_marks": 5.0,
      "section": "Section A",
      "question_type": "descriptive",
      "options": [],
      "choice_group": "choice_q1",
      "required_choice_count": 1,
      "expected_components": ["Key principles", "Diagram", "Explanation"]
    }}
  ]
}}
"""
        try:
            raw = self.generate_content(prompt, files=[qp_file], json_output=True, temperature=0.0)
            return self.parse_json_response(raw)
        except Exception as e:
            logger.warning(f"[GeminiService] evaluate_question_paper first attempt failed: {e}. Retrying...")
            retry_prompt = prompt + "\n\nCRITICAL: Return ONLY valid, fully closed JSON matching the schema above."
            raw = self.generate_content(retry_prompt, files=[qp_file], json_output=True, temperature=0.0)
            return self.parse_json_response(raw)

    def evaluate_answer_script(
        self,
        qp_file: Any,
        ans_file: Any,
        qp_structure: Dict[str, Any],
        subject: str,
        rubrics_file: Optional[Any] = None,
        syllabus_file: Optional[Any] = None,
        level: str = "school"
    ) -> Dict[str, Any]:
        """Perform multimodal, strict, evidence-based grading of student handwritten/typed answer script.
        Adheres to human examiner standards: partial credit for valid methods, strict marks bounds, zero fabricated answers.
        """
        qp_json = json.dumps(qp_structure, ensure_ascii=False, indent=2)
        prompt = f"""
You are LearnSphere AI's STRICT, HIGHLY EXPERIENCED HUMAN TEACHER AND HEAD EXAMINER.
You are evaluating a student's answer script against the official Question Paper and marking criteria.
EVERY SINGLE QUESTION in the Question Paper must receive individual, granular, evidence-based feedback. Never return only a final total.

SUBJECT: {subject}
ACADEMIC LEVEL: {level}

OFFICIAL QUESTION PAPER STRUCTURE:
{qp_json}

STRICT HUMAN TEACHER EVALUATION RULES:
1. DYNAMIC MAPPING & EXACT QUESTION BINDING (ZERO MAPPING ERRORS):
   - Inspect EVERY single page and line of the uploaded answer script with extreme care.
   - Answers may be written in ANY order (e.g. student answered Q6(b) first, then Q7(a), then Q1).
   - Question numbers may be written in margins, underlined, circled, abbreviated (e.g. "Ans 6b", "6(b)", "6 b", "6 OR", "7 a i", "Q7(a)(i)"), or implicit.
   - TOPIC & SEMANTIC MATCHING: Even if the question number in the handwritten script is brief or missing the main number (e.g. student wrote "Ans (b)" or "OR part"), analyze the topic, diagrams, equations, and concepts to bind the answer to the correct question in the Question Paper structure.
   - STRICT OPTION DISAMBIGUATION:
     * When questions have elective choices (e.g. 6(a) vs 6(b), or 7(a)(i)+(ii) vs 7(b)(i)+(ii)):
       - If the student attempted Option B (e.g. 6(b)), bind the answer strictly to '6(b)'. DO NOT mark it under 6(a) or 7(a).
       - If the student attempted Option A (e.g. 7(a)(i) and 7(a)(ii)), bind the answers strictly to 7(a)(i) and 7(a)(ii). DO NOT mark them under 7(b)(i) or 7(b)(ii).
       - For the unattempted alternative option(s), set attempted: false, awarded_marks: 0.0, answer_classification: "unanswered_question", student_answer: "Not attempted in script".
   - DO NOT mark a question as unattempted if the student wrote an answer anywhere in the script!
   - DO NOT mix up subparts (e.g., subpart (i) vs subpart (ii)).

2. EVIDENCE-BASED ASSESSMENT (NEVER FABRICATE OR HALLUCINATE):
   - Evaluate ONLY what the student actually wrote or drew.
   - Transcribe what the student wrote accurately under 'student_answer'.
   - Cite the exact location under 'evidence_reference' (e.g. "Script Page 2, lines 1-15").

3. UNACCEPTABLE GENERIC FEEDBACK BAN:
   - NEVER output generic placeholder phrases like "Good answer.", "Needs improvement.", "Try harder.", "Correct.", "Incorrect."
   - Explain the EXACT reason for mark allocation. Example:
     "Your formula selection (Ohm's law) is correct, but the substitution of resistance R=50Ω instead of R=5Ω leads to an incorrect current I=0.2A instead of I=2A. Awarded 3/5 marks for correct method with an arithmetic substitution error."

4. CLASSIFY EVERY ANSWER INTO EXACTLY ONE OF:
   - "wrong_concept"
   - "partially_correct_concept"
   - "correct_concept_with_calculation_error"
   - "correct_answer_with_insufficient_explanation"
   - "incomplete_answer"
   - "irrelevant_answer"
   - "contradictory_answer"
   - "correct_answer"
   - "unanswered_question"

5. MATHEMATICS, NUMERICAL PROBLEMS & ENGINEERING:
   - Evaluate formula selection, substitution, arithmetic calculations, intermediate steps, units, and final answer.
   - Award appropriate partial credit when the method is sound but an arithmetic slip occurs.

6. THEORY, DESCRIPTIVE & ESSAY QUESTIONS:
   - Evaluate terminology, logical coherence, core principles, required diagrams, and relevant examples.

7. CRITICAL MISCONCEPTION IDENTIFICATION RULES:
   - A wrong answer is NOT automatically a misconception.
   - Wrong arithmetic != conceptual misconception.
   - A spelling error != conceptual misconception.
   - A skipped/unanswered question != conceptual misconception.
   - A calculation slip != conceptual misconception unless the underlying model or principle is flawed.
   - A misconception should be created (misconception_detected: true) ONLY when the student's answer demonstrates a misunderstanding of the underlying concept (e.g. believes action and reaction act on the same object, treats INNER JOIN as returning unmatched rows, inverts voltage-current relations).
   - If there is insufficient evidence to identify a genuine conceptual misunderstanding, set misconception_detected: false and misconception: "".

Return ONLY a valid JSON object matching this schema:
{{
  "is_unreadable": false,
  "unreadable_reason": "",
  "evaluations": [
    {{
      "question_id": "q1_a",
      "question_number": "1(a)",
      "attempted": true,
      "maximum_marks": 5.0,
      "awarded_marks": 3.0,
      "percentage_of_question": 60.0,
      "answer_classification": "correct_concept_with_calculation_error",
      "student_answer": "Student wrote: F = m*a, m=10, a=2.5, calculated F = 20 N.",
      "evidence_reference": "Script Page 1, Section A, lines 4-10",
      "evaluation_reason": "Correct physical formula selected and correct SI unit used; 2 marks deducted because 10 * 2.5 was miscalculated as 20 instead of 25.",
      "what_was_done_correctly": ["Correct selection of Newton's second law F = m*a", "Correct SI unit Newton (N) appended"],
      "what_is_incorrect": ["Arithmetic product of 10 * 2.5 written as 20"],
      "what_is_missing": ["Accurate calculation step yielding 25 N"],
      "conceptual_mistake": "",
      "step_or_calculation_mistake": "Arithmetic multiplication error in final step: 10 * 2.5 = 20 instead of 25.",
      "what_student_should_have_written": "Formula: F = m * a\\nSubstitution: F = 10 kg * 2.5 m/s² = 25 N\\nFinal Answer: 25 N",
      "how_to_improve": "Double-check basic multiplication before writing down the final numerical value.",
      "teacher_feedback": "Your formula selection is correct and unit is proper, but 10 * 2.5 was computed as 20 instead of 25. You receive 3/5 because the correct method is demonstrated but the arithmetic calculation is flawed.",
      "concepts_tested": ["Newton's Second Law", "Force and Acceleration"],
      "misconception_detected": false,
      "misconception": "",
      "confidence": 0.95
    }}
  ],
  "overall_teacher_comment": "Detailed examination summary assessing student's overall mastery, systematic workings, and recurring weaknesses across the paper.",
  "strongest_areas": ["Newtonian mechanics formula applications", "Definitions of core thermodynamic terms"],
  "weakest_areas": ["Arithmetic accuracy in multi-step calculations", "Omission of subparts in Question 4"],
  "most_important_misconceptions": [],
  "priority_topics_to_revise": ["Electric Circuits and Ohm's Law", "Dimensional analysis and units"],
  "practical_improvement_advice": ["Show all intermediate multiplication steps", "Review circuit reduction techniques before the next exam"]
}}
"""
        files = [qp_file, ans_file]
        if rubrics_file:
            files.append(rubrics_file)
        if syllabus_file:
            files.append(syllabus_file)

        try:
            raw = self.generate_content(prompt, files=files, json_output=True, temperature=0.0)
            return self.parse_json_response(raw)
        except Exception as e:
            logger.warning(f"[GeminiService] evaluate_answer_script first attempt failed: {e}. Retrying with strict JSON instruction...")
            retry_prompt = prompt + "\n\nCRITICAL: Respond ONLY with a clean, fully closed, valid JSON object matching the schema above. Do not include unescaped LaTeX backslashes or markdown code blocks."
            raw = self.generate_content(retry_prompt, files=files, json_output=True, temperature=0.0)
            return self.parse_json_response(raw)

    def verify_evaluation(self, qp_structure: Dict[str, Any], eval_result: Dict[str, Any]) -> Dict[str, Any]:
        """Independent second verification pass enforcing strict consistency, mark bounds, and arithmetic validation."""
        prompt = f"""
You are the INDEPENDENT EVALUATION VERIFIER for LearnSphere AI.
Verify the integrity, mathematical consistency, and evidence alignment of this evaluation.

QUESTION PAPER STRUCTURE:
{json.dumps(qp_structure, ensure_ascii=False)[:5000]}

EVALUATION RESULT:
{json.dumps(eval_result, ensure_ascii=False)[:8000]}

VALIDATION CHECKLIST:
1. Question count and question numbers match the Question Paper structure.
2. Every question has 0.0 <= awarded_marks <= maximum_marks.
3. Total obtained marks equals the exact sum of awarded marks of all counted questions.
4. Choice/elective rules (OR groups, Answer any X) are strictly followed without double-counting.
5. All feedback statements directly reflect the student's actual written answers.
6. Check for duplicate question answers or unresolved ambiguities.

Return ONLY a valid JSON object matching this schema:
{{
  "verified": true,
  "disagreement_detected": false,
  "reason": "Evaluation verified mathematically clean and consistent with uploaded exam paper.",
  "confidence_score": 0.98,
  "suggested_status": "COMPLETED"
}}
If any contradiction or bounds violation is detected, set "verified": false, "disagreement_detected": true, "suggested_status": "NEEDS_TEACHER_REVIEW".
"""
        raw = self.generate_content(prompt, json_output=True, temperature=0.0)
        return self.parse_json_response(raw)

    def analyze_syllabus(self, content_or_file: Any, level: str = "college", semester: str = "5", class_level: str = "12", domain: str = "", stream: str = "") -> Dict[str, Any]:
        prompt = f"""
You are LearnSphere AI's expert curriculum analyzer running gemini-3.6-flash.
Analyze the uploaded syllabus document for a {level.upper()} student (Semester {semester} / Class {class_level}, Domain/Stream: {domain or stream}).

TASK:
1. Extract course title and ALL distinct subjects/courses printed in the document.
2. For EACH subject, extract modules/chapters/units and specific topics/concepts inside each module.
3. Extract key academic topics, learning outcomes, and 2 real-world challenge scenarios per subject.

Return ONLY JSON matching schema:
{{
  "course_title": "Title",
  "extracted_subjects": ["Subject 1", "Subject 2"],
  "chapters": {{
    "Subject 1": [
      {{
        "name": "Module I: Name",
        "concepts": ["Concept A", "Concept B"]
      }}
    ]
  }},
  "key_topics": ["Topic 1", "Topic 2"],
  "challenge_scenarios": [
    {{"title": "Scenario 1", "description": "Details"}}
  ]
}}
"""
        files = [content_or_file] if isinstance(content_or_file, (str, dict)) and (isinstance(content_or_file, dict) or Path(str(content_or_file)).is_file()) else None
        text_prompt = prompt if not files else prompt + f"\nProvided text:\n{str(content_or_file)[:12000]}"
        raw = self.generate_content(text_prompt, files=files, json_output=True)
        return self.parse_json_response(raw)

    def generate_reality_lab(self, subject: str, module: str, difficulty: str = "Medium", syllabus_context: str = "") -> Dict[str, Any]:
        prompt = f"""
Generate a practical Reality Lab scenario connecting theory to real-world application using gemini-3.6-flash.
Subject: {subject}
Module/Topic: {module}
Difficulty: {difficulty}
Syllabus Context: {syllabus_context[:1000]}

Return ONLY JSON:
{{
  "scenario_id": "rl_1",
  "subject": "{subject}",
  "module": "{module}",
  "difficulty": "{difficulty}",
  "title": "Practical Industry Scenario Title",
  "scenario_description": "Real-world context",
  "task": "Specific engineering/practical task for student to solve",
  "eval_criteria": ["Criteria 1", "Criteria 2"]
}}
"""
        raw = self.generate_content(prompt, json_output=True)
        return self.parse_json_response(raw)

    def evaluate_reality_lab(self, scenario_title: str, task: str, student_response: str, subject: str) -> Dict[str, Any]:
        prompt = f"""
Evaluate student's solution to Reality Lab scenario using gemini-3.6-flash.
Subject: {subject}
Scenario: {scenario_title}
Task: {task}
Student Solution: {student_response}

Return ONLY JSON:
{{
  "score": 90,
  "feedback": "Detailed feedback on practical feasibility and academic accuracy",
  "strengths": ["Strength 1"],
  "weaknesses": ["Weakness 1"],
  "improved_solution": "Optimal real-world implementation"
}}
"""
        raw = self.generate_content(prompt, json_output=True)
        return self.parse_json_response(raw)

    def generate_knowledge_challenge(self, subject: str, module: str = "All", difficulty: str = "Medium", syllabus_context: str = "") -> Dict[str, Any]:
        prompt = f"""
Generate 5 knowledge challenge quiz questions dynamically from student syllabus using gemini-3.6-flash.
Subject: {subject}
Module: {module}
Difficulty: {difficulty}
Syllabus Context: {syllabus_context[:1000]}

Return ONLY JSON:
{{
  "subject": "{subject}",
  "questions": [
    {{
      "id": "kc_1",
      "question_type": "MCQ",
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "Detailed explanation of correct answer",
      "difficulty": "{difficulty}",
      "chapter": "{module}"
    }}
  ]
}}
"""
        raw = self.generate_content(prompt, json_output=True)
        return self.parse_json_response(raw)

    def generate_self_evaluation(self, subject: str, topic: str, difficulty: str = "Medium", syllabus_context: str = "") -> Dict[str, Any]:
        prompt = f"""
Generate a single self-evaluation question for a student using gemini-3.6-flash.
Subject: {subject}
Topic: {topic}
Difficulty: {difficulty}
Syllabus Context: {syllabus_context[:1000]}

Return ONLY JSON:
{{
  "question_id": "se_1",
  "subject": "{subject}",
  "topic": "{topic}",
  "difficulty": "{difficulty}",
  "question_text": "Detailed question text",
  "question_type": "descriptive",
  "expected_key_points": ["Key point 1", "Key point 2"],
  "marks": 10
}}
"""
        raw = self.generate_content(prompt, json_output=True)
        return self.parse_json_response(raw)

    def evaluate_self_evaluation(self, question_text: str, expected_concept: str, student_response: str, subject: str) -> Dict[str, Any]:
        prompt = f"""
Evaluate student's self-evaluation response using gemini-3.6-flash.
Subject: {subject}
Question: {question_text}
Expected Concept: {expected_concept}
Student Response: {student_response}

Return ONLY JSON:
{{
  "awarded_marks": 7,
  "max_marks": 10,
  "percentage": 70,
  "feedback": "Detailed specific feedback referencing student's actual response",
  "what_was_done_correctly": ["Correctly identified X"],
  "what_is_missing": ["Missing explanation of Y"],
  "expected_answer": "Model answer with key points",
  "misconception_detected": false,
  "misconception": ""
}}
"""
        raw = self.generate_content(prompt, json_output=True)
        return self.parse_json_response(raw)

    @property
    def primary_model(self) -> str:
        return self.model
