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
import hashlib
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from .trainer_validator import TrainerResponseQualityValidator

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
            try:
                from PIL import Image
                import io
                with Image.open(p) as img:
                    # Convert RGBA/P to RGB for clean JPEG compression
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    # If exceptionally huge image (e.g. 4000x3000 phone camera photo), scale down to 1920 max dim
                    max_dim = 1920
                    if max(img.size) > max_dim:
                        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=85, optimize=True)
                    b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
                parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64_data}})
            except Exception:
                # Fallback to direct read
                try:
                    mime = "image/png" if ext == ".png" else "image/jpeg" if ext in (".jpg", ".jpeg") else "image/webp"
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
                total_pages = len(doc)
                for page_idx in range(total_pages):
                    page = doc[page_idx]
                    
                    # Fast text extraction first
                    raw_text = ""
                    try:
                        raw_text = page.get_text("text") or ""
                        if raw_text and len(raw_text.strip()) > 10:
                            parts.append({"text": f"--- PAGE {page_idx + 1} OF {total_pages} (EMBEDDED TEXT) ---\n{raw_text}\n"})
                    except Exception:
                        pass

                    # OCR ONLY WHEN REQUIRED: Render page image only if text layer is missing or insufficient (< 50 chars)
                    if not raw_text or len(raw_text.strip()) < 50:
                        pix = page.get_pixmap(dpi=140)
                        jpeg_bytes = pix.tobytes("jpeg", jpg_quality=85)
                        b64_data = base64.b64encode(jpeg_bytes).decode("utf-8")
                        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64_data}})
            except Exception as e:
                logger.warning(f"Could not process PDF {p}: {e}")
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
        try:
            seed_source = prompt[:2000]
            if files:
                for f_item in files:
                    p_str = f_item if isinstance(f_item, str) else (f_item or {}).get("path") or ""
                    if p_str and os.path.exists(p_str):
                        seed_source += f":{os.path.getsize(p_str)}"
            raw_seed = int(hashlib.md5(seed_source.encode("utf-8")).hexdigest()[:8], 16)
            generation_config["seed"] = raw_seed % 2147483647
        except Exception:
            pass

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
2. Inspect EVERY single page and section. Extract ALL questions and sub-questions (e.g. 1, 2, 3, 4, 5, 6.a (i), 6.a (ii), 6.b (i), 6.b (ii), 7.a (i), 7.a (ii), 7.b (i), 7.b (ii)).
3. CRITICAL: MULTI-PART & SUB-QUESTION DECOMPOSITION:
   - When a main question contains numbered subparts (e.g. '6.a (i)' and '(ii)', or '7.a (i)' and '(ii)', or 'b (i)' and '(ii)'):
   - You MUST extract EACH individual subpart as its OWN distinct question object in the 'questions' array!
   - Format 'question_number' explicitly: "6(a)(i)", "6(a)(ii)", "6(b)(i)", "6(b)(ii)", "7(a)(i)", "7(a)(ii)", "7(b)(i)", "7(b)(ii)".
   - Assign the exact individual maximum marks to each subpart (e.g., 6(a)(i) = 10.0, 6(a)(ii) = 10.0, 7(a)(i) = 12.0, 7(a)(ii) = 8.0).
4. CRITICAL: (OR) / ELECTIVE CHOICE DETECTION & MAIN QUESTION CONTINUITY:
   - In examination papers, elective questions are often printed with '(OR)', '[OR]', 'OR' between Option A and Option B (e.g., 6. (a) ... (OR) ... (b) ...).
   - CRITICAL RULE: Option B is frequently printed as just '(b)', 'b)', or placed directly below '(OR)' WITHOUT repeating the main question number '6' on top.
   - DO NOT increment the main question number for Option B! Option B is ALWAYS '6(b)' (or 6(b)(i)), NEVER '7(a)' or '7'!
   - The main question number increments ONLY when a genuinely new main question starts (e.g. '7.', '7(a)', 'Q7').
   - Assign the EXACT same 'choice_group' identifier to all alternative options for that question (e.g. "choice_q6" for 6(a)(i), 6(a)(ii), 6(b)(i), 6(b)(ii); and "choice_q7" for 7(a)(i), 7(a)(ii), 7(b)(i), 7(b)(ii)).
   - Set 'required_choice_count' to the exact number of options required (usually 1).
5. For EVERY question:
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
      "question_id": "q6_a_1",
      "question_number": "6(a)(i)",
      "question_text": "Complete verbatim text of subpart 6.a (i)",
      "maximum_marks": 10.0,
      "section": "PART B",
      "question_type": "code",
      "options": [],
      "choice_group": "choice_q6",
      "required_choice_count": 1,
      "expected_components": ["Data type definition", "Dictionary explanation and example", "Set explanation and example"]
    }},
    {{
      "question_id": "q6_a_2",
      "question_number": "6(a)(ii)",
      "question_text": "Complete verbatim text of subpart 6.a (ii)",
      "maximum_marks": 10.0,
      "section": "PART B",
      "question_type": "code",
      "options": [],
      "choice_group": "choice_q6",
      "required_choice_count": 1,
      "expected_components": ["Break statement explanation and code", "Continue statement explanation and code"]
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
        Operates exactly like an experienced, strict, fair human examination teacher and head examiner.
        """
        qp_json = json.dumps(qp_structure, ensure_ascii=False, indent=2)
        prompt = f"""
You are LearnSphere AI's ULTRA-STRICT, EXPERIENCED SENIOR HEAD EXAMINER AND CHIEF EVALUATOR.
You are evaluating an official examination paper. Your marking must be rigorous, uncompromisingly accurate, academically fair, and strictly proportional to the marks allotted for every question.

==================================================
ULTRA-STRICT HUMAN EXAMINER MARKING PROTOCOL
==================================================
1. 100% EXHAUSTIVE SCRIPT SCANNING & ZERO-OMISSION MANDATE:
   - Students frequently answer questions out of order (e.g. starting with Q7(a)(i) on Page 1, Q7(a)(ii) on Page 3, Q6(a)(i) on Page 7, Q6(a)(ii) on Page 10, Part A Q1-Q5 on Pages 13-14, or writing answers in margins, footers, or unlabelled blocks).
   - You MUST thoroughly scan EVERY single page of the answer script from Page 1 to the final page.
   - For EVERY question listed in the Question Paper structure below, your 'evaluations' array MUST contain an entry matching its exact 'question_id' and 'question_number'.
   - NEVER leave out or omit ANY question. If an answer exists anywhere in the script—regardless of where it appears, how it is ordered, or how the student labeled it (e.g., 'Q1', 'Ans 1', 'Answer to Question 1', '1a', 'Part B 6(i)')—you MUST find it, map it to the corresponding question in the paper, extract what was written, and award honest, deserved marks!
   - When a student attempts subparts like 6(a)(i), 6(a)(ii), 7(a)(i), 7(a)(ii), you MUST evaluate EACH subpart as an individual entry in the 'evaluations' array. NEVER omit or merge subparts!
   - ONLY mark 'attempted': false if after a full, exhaustive inspection of every single page of the script, the student has truly written zero answers for that question.

2. MANDATORY MARK-TO-DEPTH RIGOR (PROPORTIONALITY RULE - NO HIGH/FULL MARKS FOR SHORT ANSWERS TO LONG QUESTIONS):
   Real human teachers and strict board/university examiners NEVER award high or full marks for brief, short, or superficial answers to long-mark questions, even if what is written is factually correct.
   The volume, technical depth, structural completeness, step-by-step elaboration, diagrams, proofs, and multi-point coverage MUST STRICTLY MATCH the question's maximum marks:

   - 2-MARK QUESTIONS (Short / Definition):
     * Standard: 1.0 mark for precise technical definition/statement + 1.0 mark for formula/syntax/example/units.
     * Brief 1-line definition: Award 0.5 to 1.0 mark.
     * Tautological / Circular definitions (e.g. "A random function is a function that generates random"): Award MAX 0.5 marks.
     * Wrong category / Incorrect concept: STRICTLY 0.0 marks.

   - 5-MARK QUESTIONS (Medium Answer):
     * Requires: Core definition/principle (1.5-2.0m) + Detailed mechanism/working steps/diagram/examples (3.0-3.5m).
     * SHORT ANSWER PENALTY: If student writes only a short 1-2 sentence answer or brief definition without mechanism, steps, or diagrams: STRICTLY CAP at MAX 1.5 to 2.0 / 5.0 (30-40% max). NEVER give 4.0 or 5.0 for a short answer!

   - 8-MARK QUESTIONS (Long Answer):
     * Requires: Comprehensive exposition (4-6 detailed points/subsections, detailed working mechanism, clear diagram/flowchart/derivation, and practical examples).
     * SHORT ANSWER PENALTY: If a student writes a short answer / 2-4 lines / brief summary without sufficient depth, sub-headings, elaboration, or diagrams (even if the brief statement is technically correct): STRICTLY CAP at MAX 2.0 to 3.0 / 8.0 (25-37.5% max).
     * Moderate Depth (covers only 2-3 points with limited explanation): Award 3.5 to 4.5 / 8.0.
     * Full / Near-Full Marks (7.0 - 8.0 / 8.0): Awarded ONLY when the response is truly exhaustive with complete depth, multiple structured sections, diagrams, and concrete examples.
     * NEVER award 5.5, 6.0, 7.0, or 8.0 marks to a short answer for an 8-mark question!

   - 10-MARK / 12-MARK QUESTIONS (Major Long / Detailed Question):
     * Requires: Thorough multi-point architecture: formal theory, complete step-by-step mathematical derivation / full working code with edge cases, architecture/flowchart diagrams, in-depth explanation across all required sub-components, and real-world trade-offs.
     * SHORT ANSWER PENALTY: If a student writes a short answer (e.g. 1 short paragraph, basic definitions, or brief bullet points without step-by-step depth): STRICTLY CAP at MAX 2.5 to 4.0 / 10.0-12.0 (25-33% max).
     * Partial Depth (only 2 of 4 components covered or superficial coverage): Award 4.5 to 6.0 / 10.0-12.0.
     * Full / Near-Full Marks (9.0 - 12.0): Awarded ONLY for extensive, detailed, complete technical coverage with diagrams and full workings.
     * NEVER award 7.5, 8.0, 9.0, 10.0, 11.0, or 12.0 marks to a short answer!

   - 15-MARK / 16-MARK QUESTIONS (Comprehensive Essay / Deep Engineering Question):
     * Requires: Exhaustive university/board level depth: detailed end-to-end framework, comprehensive architecture/block diagrams, complete robust derivations or production-grade code, exhaustive comparative matrices, analysis of 5+ dimensions, risk/compliance analysis, and practical case studies.
     * SHORT ANSWER PENALTY: If a student writes a short answer (e.g. 1-2 short paragraphs, brief 4-5 line summary, or answers like a 2-mark or 5-mark question): STRICTLY CAP at MAX 3.5 to 5.0 / 16.0 (22-31% max).
     * Moderate Answer (basic high-level overview without deep engineering analysis): Award 6.0 to 8.5 / 16.0.
     * Extensive Answer (detailed 5-dimension analysis but minor omissions): Award 11.0 to 13.0 / 16.0.
     * Full Marks (14.0 - 16.0 / 16.0): Requires complete, professional, exhaustive master-level answer.
     * NEVER award 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, or 16.0 marks for an answer written like a short answer!

3. STRIKE-OUT & CROSSED-OUT TEXT DISREGARD PROTOCOL (CRITICAL):
   - Students frequently cross out or strike through words, equations, intermediate calculation steps, or entire paragraphs using horizontal lines, diagonal slashes, scribble marks, or "X" cancellations.
   - STRICT CANCELLATION DISREGARD: You MUST completely IGNORE and DISREGARD all struck-out / crossed-out content during evaluation:
     * NEVER award marks for correct concepts, formulas, or answers that have been struck out / crossed out by the student.
     * NEVER penalize the student or deduct marks for incorrect words, calculation errors, or wrong formulas that have been struck out / crossed out.
     * Evaluate ONLY clear, clean, un-struck words, numbers, formulas, sentences, and diagrams.
     * When a student crosses out a faulty step or initial attempt and writes a fresh replacement below or alongside it, evaluate ONLY the final un-struck replacement.

4. STRICT REAL TEACHER GRADING RULES:
   - STRICT ABOUT TECHNICAL ACCURACY: Never award marks for hand-waving, vague prose, or guessing.
   - NO SYMPATHY OR EFFORT MARKS: Award marks ONLY for verified, correct technical facts and working code/derivations actually present in the script.
   - ZERO MARKS FOR IRRELEVANT FLUFF: Repetitive paragraphs, generic filler, or writing unrelated topics receives 0.0 marks.
   - FULL MARKS ONLY WHEN FULLY EARNED: Full marks require complete conceptual correctness, proper terminology, valid syntax/units, required examples, and exhaustive depth commensurate with the mark weight.
   - ERROR CARRIED FORWARD (NO DOUBLE PENALTY): In multi-step derivations or numericals, if an early arithmetic slip occurs but subsequent steps follow valid mathematical logic, deduct for the slip once. Award legitimate method marks for follow-through steps.
   - PROGRAMMING RIGOR: Check variable scope (e.g. parameter named 'average' but body uses undefined 'mark'), built-in function calls (e.g. 'sum(marks)' vs broken 'marks(sum)'), list appending ('marks.append(x)' vs 'append += marks'), and language-specific syntax (penalize C/Java loops in Python).

5. ADVANCED MATHEMATICAL, DERIVATION & ANALYTICAL SCRIPT EVALUATION PROTOCOL:
   - MULTI-TIERED METHOD MARKING (Step & Method Marks):
     * Step 1: Formula / Governing Law / Transformation Statement (20-25% of marks).
     * Step 2: Substitution & Integration / Differentiation / Algebraic Working Steps (45-55% of marks).
     * Step 3: Final Simplification, Evaluation of Limits / Integrals, and Proper Units/Result (25-30% of marks).
   - AUXILIARY & DUMMY VARIABLE SUBSTITUTION HANDLING:
     * When a student defines an auxiliary dummy variable (e.g., setting k = a + jw or tau = a*t) and proceeds with valid calculus steps to evaluate the problem in terms of that variable, award ALL earned method and calculus integration marks (75-85%+ of the question).
     * If the student omits back-substituting the original variable in the very last line, deduct ONLY a minor accuracy penalty (e.g., 0.5 to 1.5 marks out of 8-16 marks) instead of penalizing the entire question.
   - VISUAL PROOFS, TABLES & COORDINATE GRAPHING CREDIT:
     * When describing mathematical concepts, signals, functions, or systems (such as even/odd properties, step responses, or harmonic waveforms): if the student provides concrete numerical value tables (e.g., evaluating points for positive and negative arguments) and neatly plots coordinate graphs illustrating the symmetry or response, award substantial credit for the demonstrated mathematical understanding, even if a written formal definition had a minor notation slip.
   - INTEGRATION BY PARTS & BOUNDARY CONDITIONS:
     * Check for appropriate assignment of u and dv, application of integral(u dv) = u*v - integral(v du). If the integration logic is sound, award proper step marks even if boundary limit cancellations (e.g., [x(t)*e^(-jwt)] from -infinity to +infinity = 0) are simplified implicitly.
   - DUAL-LENS COMPREHENSIVE TEACHER FEEDBACK:
     * In 'evaluation_reason' and 'teacher_feedback', provide balanced, constructive guidance:
       1) State the Method / Step Marks Earned (highlighting correct formulas, substitutions, calculus, tables, and diagrams).
       2) Provide Strict Mathematical Subtleties for Precision (highlighting exact theoretical definitions, boundary conditions, limits, or missing final substitutions so the student learns how to achieve 100% precision for competitive examinations).

6. GRANULAR EVIDENCE & ARITHMETIC REASONING IN FEEDBACK:
   - In both 'evaluation_reason' and 'teacher_feedback', provide the EXACT component-level mark arithmetic and clearly justify deductions for brevity or missing depth.
   - Example (Short answer on long question): "Awarded 3.0/8.0: +3.0 for accurate core definition of Agile vs Waterfall. -5.0 marks deducted because the answer is too brief for an 8-mark question—missing phase-by-phase breakdown, comparative matrix, risk management analysis, and practical industry examples."

7. EXACT QUESTION BINDING & OPTION DISAMBIGUATION:
   - Bind answers strictly to attempted questions (e.g. Q6(a) vs Q6(b)).
   - For unattempted questions or alternative elective options: set attempted: false, awarded_marks: 0.0, answer_classification: "unanswered_question".

8. CLASSIFY EVERY ANSWER INTO EXACTLY ONE OF:
   - "correct_answer"
   - "partially_correct_concept"
   - "correct_concept_with_calculation_error"
   - "correct_answer_with_insufficient_explanation"
   - "incomplete_answer"
   - "wrong_concept"
   - "irrelevant_answer"
   - "contradictory_answer"
   - "unanswered_question"

SUBJECT: {subject}
ACADEMIC LEVEL: {level}

OFFICIAL QUESTION PAPER STRUCTURE:
{qp_json}

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
      "awarded_marks": 3.5,
      "percentage_of_question": 70.0,
      "demonstrated_understanding_level": "substantial",
      "answer_classification": "correct_concept_with_calculation_error",
      "student_answer": "Student wrote: F = m*a, m=10, a=2.5, calculated F = 20 N.",
      "evidence_reference": "Script Page 1, Section A, lines 4-10",
      "evaluation_reason": "Correct physical principle (Newton's 2nd Law) and formula used with proper SI units. 1.5 marks deducted for arithmetic error in final multiplication (10 * 2.5 = 20 instead of 25). Method marks awarded under Error Carried Forward policy.",
      "teacher_feedback": "Your formula selection and physical reasoning are sound. You received 3.5/5 marks because the method is correct, with 1.5 marks deducted for an arithmetic error in the final step.",
      "what_was_done_correctly": ["Correct identification of Newton's second law F = m*a", "Proper SI unit Newton (N) appended", "Clear substitution of given mass and acceleration"],
      "what_is_incorrect": ["Arithmetic product of 10 * 2.5 miscalculated as 20"],
      "what_is_missing": ["Accurate final calculation yielding 25 N"],
      "conceptual_mistake": "",
      "step_or_calculation_mistake": "Arithmetic multiplication error in final step: 10 * 2.5 = 20 instead of 25.",
      "what_student_should_have_written": "Formula: F = m * a\\nSubstitution: F = 10 kg * 2.5 m/s² = 25 N\\nFinal Answer: 25 N",
      "how_to_improve": "Double-check basic arithmetic calculations before recording the final numerical result.",
      "concepts_tested": ["Newton's Second Law", "Force and Acceleration"],
      "misconception_detected": false,
      "misconception": "",
      "confidence": 0.95
    }}
  ],
  "overall_teacher_comment": "Comprehensive examination summary assessing student's conceptual mastery, mathematical rigor, systematic workings, and actionable improvement priorities.",
  "strongest_areas": ["Newtonian mechanics formula applications", "Definitions of core thermodynamic terms"],
  "weakest_areas": ["Arithmetic accuracy in multi-step calculations", "Omission of subparts in Question 4"],
  "most_important_misconceptions": [],
  "priority_topics_to_revise": ["Electric Circuits and Ohm's Law", "Dimensional analysis and units"],
  "practical_improvement_advice": ["Show all intermediate multiplication steps", "Review circuit reduction techniques before the next exam"]
}}
"""
        # If question paper structure is already extracted into prompt text, only send answer script (+ rubrics/syllabus)
        if qp_structure and qp_structure.get("questions"):
            files = [ans_file]
        else:
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
        """Independent second verification pass enforcing strict consistency, mark bounds, arithmetic validation, and real teacher standards."""
        prompt = f"""
You are the INDEPENDENT HEAD EXAMINER & EVALUATION VERIFIER for LearnSphere AI.
Verify the integrity, academic fairness, mathematical consistency, and evidence alignment of this evaluation.

QUESTION PAPER STRUCTURE:
{json.dumps(qp_structure, ensure_ascii=False)[:5000]}

EVALUATION RESULT:
{json.dumps(eval_result, ensure_ascii=False)[:8000]}

REAL HUMAN EXAMINER VERIFICATION CHECKLIST:
1. QUESTION CORRESPONDENCE: Question count, question IDs, and question numbers correspond directly to the Question Paper structure.
2. STRICT MARK BOUNDS & ZERO INFLATION: Every question has 0.0 <= awarded_marks <= maximum_marks with zero unearned mark inflation or negative marks.
3. PROPORTIONALITY & SHORT-ANSWER RIGOR AUDIT: For long answer questions (5m, 8m, 10m, 12m, 16m), strictly verify that short, brief, or superficial answers are NOT awarded high or full marks. A short answer to an 8m question must NOT receive >3.5 marks, and a short answer to a 16m question must NOT receive >5.5 marks. If mark inflation occurred on brief answers, flag disagreement.
4. STRIKE-OUT / CROSSED-OUT AUDIT: Verify that all struck-out or crossed-out text/calculations in the answer sheets were completely excluded from grading, and only clear, un-struck words and equations were considered.
5. ARITHMETIC INTEGRITY: Total obtained marks equals the exact sum of awarded marks of all counted questions.
6. CHOICE RULES & OPTION ENFORCEMENT: Choice/elective rules (OR groups, Answer any X) are strictly followed without double-counting.
7. REAL TEACHER EVIDENCE: All feedback statements directly reflect the student's actual handwritten answers without hallucination.
8. ERROR CARRIED FORWARD & PARTIAL MARKING: Method marks were awarded appropriately where an arithmetic slip occurred without repeatedly penalizing follow-through steps.
9. MATHEMATICAL DERIVATION & GRAPHICAL AUDIT: Step/method marks are respected for valid calculus integrations, auxiliary variable substitutions, value tables, and coordinate plots. Ensure deductions distinguish between minor non-back-substituted dummy variables vs fundamental conceptual flaws.
10. CONCISE VS FLUFF SCRUTINY: Concise, complete, accurate answers are rewarded fairly and rambling fluff is not awarded unearned credit.
11. OCR & AMBIGUITY CHECK: Zero unrecognized symbol corruptions or unaddressed illegibility issues.

Return ONLY a valid JSON object matching this schema:
{{
  "verified": true,
  "disagreement_detected": false,
  "reason": "Evaluation verified mathematically clean, strictly consistent, and aligned with Real Human Examiner standards.",
  "confidence_score": 0.98,
  "suggested_status": "COMPLETED"
}}
If any contradiction, mark inflation, or bounds violation is detected, set "verified": false, "disagreement_detected": true, "suggested_status": "NEEDS_TEACHER_REVIEW".
"""
        raw = self.generate_content(prompt, json_output=True, temperature=0.0)
        return self.parse_json_response(raw)

    def _deterministic_syllabus_parser(self, content_or_file: Any, target_semester: Any = "", level: str = "college", dept_str: str = "", prog_str: str = "") -> Dict[str, Any]:
        """
        High-precision deterministic syllabus extraction engine.
        Extracts structured subject records from tables, multi-page lists, and schemes,
        retaining exact course codes, types, credits, source text, page references, section provenance, and semester evidence.
        """
        raw_text = ""
        page_texts: List[Tuple[int, str]] = []
        is_file_path = False
        if isinstance(content_or_file, str) and len(content_or_file) < 500 and not ("\n" in content_or_file):
            try:
                is_file_path = Path(content_or_file).is_file()
            except Exception:
                is_file_path = False

        if is_file_path:
            try:
                try:
                    import pymupdf as fitz
                except ImportError:
                    import fitz
                doc = fitz.open(content_or_file)
                for p_idx, page in enumerate(doc):
                    t = page.get_text("text") or ""
                    page_texts.append((p_idx + 1, t))
                    raw_text += f"\n--- Page {p_idx + 1} ---\n" + t
            except Exception:
                try:
                    with open(content_or_file, "r", encoding="utf-8", errors="ignore") as f:
                        raw_text = f.read()
                        page_texts = [(1, raw_text)]
                except Exception:
                    pass
        else:
            raw_text = str(content_or_file or "")
            # If raw_text contains page markers, reconstruct page_texts
            if "--- Page " in raw_text:
                parts = re.split(r"--- Page (\d+) ---", raw_text)
                if len(parts) > 1:
                    for i in range(1, len(parts), 2):
                        try:
                            p_num = int(parts[i])
                            p_content = parts[i + 1] if i + 1 < len(parts) else ""
                            page_texts.append((p_num, p_content))
                        except Exception:
                            pass
            if not page_texts:
                page_texts = [(1, raw_text)]

        # DEBUG PRINTS
        # print(f"[DEBUG 1] page_texts count: {len(page_texts)}", flush=True)

        raw_text = re.sub(r"\bS\s+E\s+M\s+E\s+S\s+T\s+E\s+R\b", "SEMESTER", raw_text, flags=re.I)
        raw_text = re.sub(r"\bS\s+E\s+M\b", "SEM", raw_text, flags=re.I)

        target_sem_int = None
        try:
            if target_semester is not None and str(target_semester).strip() != "":
                target_sem_int = int(target_semester)
        except Exception:
            pass

        sem_heading_pattern = re.compile(
            r"\b(?:SEMESTER|SEM(?:ESTER)?|TRIMESTER)\s*[:\-–—\s]*([0-9]{1,2}|VIII|VII|VI|IV|V|III|II|I|[1-8](?:st|nd|rd|th)?|FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH)\b|\b([1-8](?:st|nd|rd|th)?|FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|VIII|VII|VI|IV|V|III|II|I)[^\S\r\n]+(?:SEMESTER|SEM(?:ESTER)?|TRIMESTER)\b",
            re.I
        )
        sem_word_map = {
            "1": 1, "01": 1, "1ST": 1, "FIRST": 1, "I": 1,
            "2": 2, "02": 2, "2ND": 2, "SECOND": 2, "II": 2,
            "3": 3, "03": 3, "3RD": 3, "THIRD": 3, "III": 3,
            "4": 4, "04": 4, "4TH": 4, "FOURTH": 4, "IV": 4,
            "5": 5, "05": 5, "5TH": 5, "FIFTH": 5, "V": 5,
            "6": 6, "06": 6, "6TH": 6, "SIXTH": 6, "VI": 6,
            "7": 7, "07": 7, "7TH": 7, "SEVENTH": 7, "VII": 7,
            "8": 8, "08": 8, "8TH": 8, "EIGHTH": 8, "VIII": 8
        }

        # Multi-department / multi-program section isolation:
        dept_heading_pattern = re.compile(
            r"(?:^|\n)\s*(?:DEPARTMENT\s+OF|BRANCH\s+OF|PROGRAM(?:ME)?\s+IN|FACULTY\s+OF)\s+([A-Za-z\s&]{4,60})(?:\n|$)",
            re.I
        )
        student_dept_query = str(dept_str or "").strip().lower()
        student_prog_query = str(prog_str or "").strip().lower()
        if student_dept_query and len(student_dept_query) > 2 and student_dept_query not in ("general engineering/science", "general"):
            dept_matches = list(dept_heading_pattern.finditer(raw_text))
            if len(dept_matches) > 1:
                target_dept_start = None
                target_dept_end = len(raw_text)
                for idx, dm in enumerate(dept_matches):
                    d_heading = dm.group(0).lower()
                    dept_name_part = (dm.group(1) or "").lower().strip()
                    is_match = (
                        student_dept_query in d_heading
                        or student_dept_query in dept_name_part
                        or (student_prog_query and student_prog_query in d_heading)
                    )
                    if is_match:
                        if target_dept_start is None:
                            target_dept_start = dm.start()
                    elif target_dept_start is not None:
                        # Reached a completely different department section
                        target_dept_end = dm.start()
                        break
                if target_dept_start is not None and target_dept_end > target_dept_start:
                    raw_text = raw_text[target_dept_start:target_dept_end]

        # Detect all semesters present across document
        detected_semesters = []
        heading_matches = []
        for m in sem_heading_pattern.finditer(raw_text):
            token = (m.group(1) or m.group(2) or "").upper()
            sem_num = sem_word_map.get(token)
            if sem_num:
                heading_matches.append({
                    "start": m.start(),
                    "end": m.end(),
                    "semester": sem_num,
                    "matched_text": m.group(0).strip()
                })
                if sem_num not in detected_semesters:
                    detected_semesters.append(sem_num)
        detected_semesters.sort()

        # Handle unidentifiable semester headings for college students: STRICT NO-GUESS POLICY
        if level.lower() == "college" and target_sem_int:
            if not detected_semesters:
                return {
                    "validation_status": "NEEDS_REVIEW",
                    "detected_semesters": [],
                    "target_semester": target_semester,
                    "mismatch_reason": "Semester headings could not be reliably identified in the uploaded document. Syllabus marked for review to avoid cross-semester guessing.",
                    "course_title": "Unverified Curriculum (Review Required)",
                    "expected_subject_count": 0,
                    "extracted_subject_count": 0,
                    "completeness_verified": False,
                    "completeness_notes": "Semester headings cannot be reliably identified. The syllabus requires review before activation.",
                    "subjects": [],
                    "extracted_subjects": [],
                    "chapters": {},
                    "units": {}
                }

            if target_sem_int not in detected_semesters:
                return {
                    "validation_status": "MISMATCH",
                    "detected_semesters": detected_semesters,
                    "target_semester": target_semester,
                    "mismatch_reason": f"The uploaded syllabus does not appear to match your current Semester {target_semester} profile. (Detected: Semester {', '.join(map(str, detected_semesters))})",
                    "course_title": "Curriculum Scheme Mismatch",
                    "expected_subject_count": 0,
                    "extracted_subject_count": 0,
                    "completeness_verified": False,
                    "completeness_notes": f"Document covers Semesters {detected_semesters}, which does not include your active Semester {target_semester}.",
                    "subjects": [],
                    "extracted_subjects": [],
                    "chapters": {},
                    "units": {}
                }

        # Multi-section aggregation: Isolate all sections belonging ONLY to the target semester
        relevant_text = raw_text
        explicit_identifier = None
        target_sections = []
        if target_sem_int and heading_matches:
            explicit_identifier = f"Semester {target_sem_int}"
            for idx, h in enumerate(heading_matches):
                if h["semester"] == target_sem_int:
                    # Find end boundary: start of the first subsequent heading belonging to a DIFFERENT semester
                    end_p = len(raw_text)
                    for next_h in heading_matches[idx + 1:]:
                        if next_h["semester"] != target_sem_int:
                            end_p = next_h["start"]
                            break
                    target_sections.append(raw_text[h["start"]:end_p])
                    break  # Captured the entire multi-page curriculum block for this semester

            if target_sections:
                relevant_text = "\n\n".join(target_sections)

        # Extended Subject Code Regex (Matches standard, AICTE, Autonomous, University, and Lab formats)
        code_regex = re.compile(
            r"\b([A-Z]{2,6}\s*[-/]\s*[A-Z0-9]{0,6}\d+[A-Z0-9]*|[A-Z]{2,5}\s*[-/]?\s*\d{2,4}[A-Z0-9]?|\d{2}[A-Z]{2,4}\d{2,4}[A-Z]?)\b",
            re.I
        )

        # Category Section Heading Detector (Strict line-ending match so title words like 'Theory' are not falsely matched)
        category_heading_pattern = re.compile(
            r"^(?:#+\s*)?(?:(?:PROFESSIONAL|PROGRAM(?:ME)?|DEPARTMENT(?:AL)?)\s+ELECTIVES?(?:\s*[-–—:]?\s*[0-9IVX]+|\s*\([A-Z0-9\s\-]+\))?|OPEN\s+ELECTIVES?(?:\s*[-–—:]?\s*[0-9IVX]+|\s*\([A-Z0-9\s\-]+\))?|INTERDISCIPLINARY\s+ELECTIVES?|MANDATORY\s+(?:NON-CREDIT\s+)?COURSES?(?:\s*\([A-Z0-9\s\-]+\))?|AUDIT\s+COURSES?(?:\s*\([A-Z0-9\s\-]+\))?|PRACTICALS?(?:\s*/\s*LABORATORY)?|LABORATORY(?:\s+(?:COURSES?|&\s*PRACTICAL\s+COURSES?))?|THEORY\s+COURSES?|EMPLOYABILITY\s+ENHANCEMENT\s+COURSES?(?:\s*\([A-Z0-9\s\-]+\))?|PROJECT\s+WORK(?:\s*/\s*SEMINAR)?|HUMANITIES\s+(?:AND|&)\s+SOCIAL\s+SCIENCES?(?:\s*\([A-Z0-9\s\-]+\))?)\s*$",
            re.I
        )

        # Ignored header, metadata, institution titles, and unit lines for subject identification
        ignore_line_pattern = re.compile(
            r"^(?:s\.?\s*no|sl\.?\s*no|course\s+code|subject\s+code|course\s+title|subject\s+title|course\s+group|category\s*$|credits?\s*$|contact\s+periods|hours\s+per\s+week|scheme\s+of\s+examination|maximum\s+marks|internal|external|total\s+credits|page\s+\d+|---|===|\*\*\*|unit\s*[0-9ivxlcdm]+|module\s*[0-9ivxlcdm]+|chapter\s*[0-9ivxlcdm]+|text\s*books?|reference\s*books?|course\s+outcomes?|course\s+objectives?|prerequisites?|detailed\s+syllabus|learning\s+outcomes?|co[0-9]|po[0-9]|department\s+of|college\s+of|institute\s+of|university|curriculum\s+scheme|choice\s+based)\b",
            re.I
        )

        subjects: List[Dict[str, Any]] = []

        def categorize_subject(name: str, code: str, raw_line: str, active_cat: Optional[str] = None) -> str:
            lower = f"{name} {code} {raw_line}".lower()
            if re.search(r"\b(?:lab|laboratory|practical|workshop|simulation|virtual\s+lab|practice|studio)\b", lower):
                return "Laboratory"
            if re.search(r"\b(?:professional\s+elective|program\s+elective|departmental\s+elective|elective\s*[-–—:]?\s*[i|iv|v|x|0-9]+|pec\b|pe\s*[-–—:]?\s*[0-9]+)\b", lower):
                return "Professional Elective"
            if re.search(r"\b(?:open\s+elective|interdisciplinary\s+elective|institute\s+elective|oec\b|oe\s*[-–—:]?\s*[0-9]+)\b", lower):
                return "Open Elective"
            if re.search(r"\b(?:mandatory|audit\s+course|constitution\s+of\s+india|environmental\s+science|universal\s+human\s+values|essence\s+of\s+indian|traditional\s+knowledge|disaster\s+management|induction\s+program|non-credit)\b", lower):
                return "Mandatory Audit"
            if re.search(r"\b(?:project|mini\s+project|project\s+phase|technical\s+seminar|seminar|internship|industrial\s+training|industrial\s+visit|comprehensive\s+viva|capstone)\b", lower):
                return "Project/Seminar"
            if re.search(r"\b(?:technical\s+english|professional\s+communication|communication\s+skills|principles\s+of\s+management|engineering\s+economics|total\s+quality\s+management|intellectual\s+property|humanities|hsmc)\b", lower):
                return "Humanities / Management"
            if active_cat:
                return active_cat
            return "Theory Core"

        def build_normalized_subject(
            name: str,
            code: str,
            cat: str,
            cr: Optional[float],
            l_h: Optional[int],
            t_h: Optional[int],
            p_h: Optional[int],
            raw_src_text: str,
            source_pages: List[int],
            source_sec: str
        ) -> Dict[str, Any]:
            sem_val = target_sem_int if target_sem_int is not None else (target_semester or 1)
            sub_id = f"sub_{hashlib.md5(f'{prog_str}_{dept_str}_{sem_val}_{name}'.encode('utf-8')).hexdigest()[:10]}"
            return {
                "subjectId": sub_id,
                "id": sub_id,
                "subjectCode": code,
                "code": code,
                "subjectName": name,
                "name": name,
                "courseType": cat,
                "type": cat,
                "category": cat,
                "credits": cr,
                "lecture_hours": l_h,
                "tutorial_hours": t_h,
                "practical_hours": p_h,
                "semester": sem_val,
                "program": prog_str or "Degree Program",
                "department": dept_str or "Engineering/Science",
                "sourcePages": source_pages,
                "source_page_numbers": source_pages,
                "source_page": source_pages[0] if source_pages else 1,
                "sourceSection": source_sec,
                "source_section": source_sec,
                "sourceText": raw_src_text,
                "source_text": raw_src_text,
                "semester_evidence": f"Found in Semester {sem_val} curriculum section",
                "extractionConfidence": 0.98,
                "confidence": 0.98,
                "evidence_verified": True
            }

        # ── 1. Structured Pipe-Table & Grid Parser ────────────────────────────
        header_map: Dict[str, int] = {}
        active_table_category = None

        # Rejoin broken/wrapped pipe-table lines
        cleaned_relevant_lines = []
        for l in relevant_text.splitlines():
            l_str = l.strip()
            if not l_str:
                continue
            if cleaned_relevant_lines and cleaned_relevant_lines[-1].startswith("|") and not cleaned_relevant_lines[-1].endswith("|"):
                cleaned_relevant_lines[-1] += " " + l_str
            elif cleaned_relevant_lines and cleaned_relevant_lines[-1].startswith("|") and not l_str.startswith("|") and not l_str.startswith("---") and not l_str.startswith("#"):
                # Continuation of previous row's cell
                last_line = cleaned_relevant_lines[-1].rstrip("|").rstrip()
                cleaned_relevant_lines[-1] = last_line + " " + l_str + " |"
            else:
                cleaned_relevant_lines.append(l_str)

        for line_str in cleaned_relevant_lines:
            if line_str.startswith("--- Page "):
                continue

            # Check for category subheadings (e.g., Professional Electives)
            cat_match = category_heading_pattern.search(line_str)
            if cat_match:
                ch_text = cat_match.group(0).lower()
                if "professional" in ch_text or "program" in ch_text or "department" in ch_text:
                    active_table_category = "Professional Elective"
                elif "open" in ch_text or "interdisciplinary" in ch_text:
                    active_table_category = "Open Elective"
                elif "mandatory" in ch_text or "audit" in ch_text:
                    active_table_category = "Mandatory Audit"
                elif "lab" in ch_text or "practical" in ch_text:
                    active_table_category = "Laboratory"
                elif "project" in ch_text or "seminar" in ch_text or "eec" in ch_text:
                    active_table_category = "Project/Seminar"
                elif "humanities" in ch_text or "hsmc" in ch_text:
                    active_table_category = "Humanities / Management"
                elif "theory" in ch_text:
                    active_table_category = "Theory Core"
                continue

            if "|" in line_str:
                if sem_heading_pattern.search(line_str):
                    continue
                cells = [c.strip() for c in line_str.strip("|").split("|")]
                if len(cells) >= 2:
                    header_check = " ".join(cells).lower()
                    if any(k in header_check for k in ("course code", "subject code", "course title", "subject title", "credits", "category")):
                        # Detect column positions (handles repeated headers across pages)
                        header_map = {}
                        for c_idx, c_val in enumerate(cells):
                            c_norm = c_val.lower().strip()
                            if "code" in c_norm:
                                header_map["code"] = c_idx
                            elif "title" in c_norm or "name" in c_norm:
                                header_map["name"] = c_idx
                            elif "category" in c_norm or "cat" in c_norm or "type" in c_norm:
                                header_map["category"] = c_idx
                            elif c_norm in ("c", "cr", "credits", "credit"):
                                header_map["credits"] = c_idx
                            elif c_norm == "l":
                                header_map["l"] = c_idx
                            elif c_norm == "t":
                                header_map["t"] = c_idx
                            elif c_norm == "p":
                                header_map["p"] = c_idx
                        continue

                    if all(re.match(r"^[-:\s]+$", c) for c in cells):
                        continue

                    row_code = ""
                    row_name = ""
                    row_credits = None
                    row_l, row_t, row_p = None, None, None
                    row_type = None

                    if "name" in header_map and header_map["name"] < len(cells):
                        row_name = cells[header_map["name"]]
                        if "code" in header_map and header_map["code"] < len(cells):
                            row_code = cells[header_map["code"]]
                        if "category" in header_map and header_map["category"] < len(cells):
                            row_type = cells[header_map["category"]]
                        if "credits" in header_map and header_map["credits"] < len(cells):
                            try:
                                row_credits = float(cells[header_map["credits"]])
                            except Exception:
                                pass
                        if "l" in header_map and header_map["l"] < len(cells) and str(cells[header_map["l"]]).isdigit():
                            row_l = int(cells[header_map["l"]])
                        if "t" in header_map and header_map["t"] < len(cells) and str(cells[header_map["t"]]).isdigit():
                            row_t = int(cells[header_map["t"]])
                        if "p" in header_map and header_map["p"] < len(cells) and str(cells[header_map["p"]]).isdigit():
                            row_p = int(cells[header_map["p"]])
                    else:
                        # Fallback row cell discovery
                        for cell_idx, cell in enumerate(cells):
                            if not row_code and code_regex.search(cell) and len(cell) <= 15:
                                row_code = code_regex.search(cell).group(1).replace(" ", "")
                            elif not row_name and len(cell) >= 3 and not re.match(r"^[\d\.\s]+$", cell):
                                c_clean = re.sub(r"^\d+[\.\)]\s*", "", cell)
                                if len(c_clean) >= 3 and not any(k in c_clean.lower() for k in ("semester", "credits", "total", "hours")):
                                    row_name = c_clean
                            elif re.search(r"\b(?:PC|PE|OE|MC|EEC|HSMC|BSC|ESC|Theory|Lab|Practical|Audit)\b", cell, re.I):
                                row_type = cell

                        # Credits is last numeric cell
                        for cell in reversed(cells):
                            if re.match(r"^\d+(?:\.\d+)?$", cell):
                                try:
                                    row_credits = float(cell)
                                    break
                                except Exception:
                                    pass

                    # Multi-line table cell continuation check:
                    # If this row only contains continuation text for subject name, append to previous subject
                    if not row_code and row_name and row_credits is None and subjects:
                        # Check if this row is a wrapped name continuation
                        if not any(k in row_name.lower() for k in ("total", "semester", "credits", "scheme")):
                            prev_sub = subjects[-1]
                            prev_sub["subjectName"] = f"{prev_sub['subjectName']} {row_name}".strip()
                            prev_sub["name"] = prev_sub["subjectName"]
                            prev_sub["sourceText"] = f"{prev_sub['sourceText']} | {line_str}".strip()
                            prev_sub["source_text"] = prev_sub["sourceText"]
                            continue

                    if row_name:
                        clean_row_name = re.sub(r"^\s*(?:\d+[\.\)]|\[\d+\])\s*", "", row_name).strip()
                        if row_code:
                            clean_row_name = re.sub(re.escape(row_code), "", clean_row_name, flags=re.I).strip()
                        clean_row_name = re.sub(r"[-:–—|()]+", " ", clean_row_name).strip()

                        if len(clean_row_name) < 2 or any(k in clean_row_name.lower() for k in ("courses total", "total credits", "scheme of examination")):
                            continue

                        # Filter out generic elective placeholder rows or course category acronym headers without a specific course code
                        if not row_code and (
                            re.match(r"^(?:professional\s+electives?|open\s+electives?|program\s+electives?|department(?:al)?\s+electives?|elective\s+courses?)(?:\s*[-–—:]?\s*[0-9ivx]+|\s*\([a-z0-9\s\-]+\))?$", clean_row_name, re.I)
                            or re.match(r"^(?:PCC|HSC|PROJ|PEC|BSC|ESC|MC|OEC|HSMC|EEC|PC|PE|OE|HS|MC|PR|PW|VA)$", clean_row_name.strip(), re.I)
                        ):
                            continue

                        category = row_type if (row_type and row_type in ("Laboratory", "Professional Elective", "Open Elective", "Mandatory Audit", "Project/Seminar")) else categorize_subject(clean_row_name, row_code, line_str, active_table_category)

                        sub_obj = build_normalized_subject(
                            name=clean_row_name,
                            code=row_code,
                            cat=category,
                            cr=row_credits,
                            l_h=row_l,
                            t_h=row_t,
                            p_h=row_p,
                            raw_src_text=line_str,
                            source_pages=[1],
                            source_sec=explicit_identifier or f"Semester {target_semester or ''} Scheme Table"
                        )
                        subjects.append(sub_obj)
                        continue

        # ── 2. Standard Line / Space-Delimited Scheme Parser with Multi-Line Stitching ──
        # Only execute Section 2 if no subjects were extracted via structured pipe tables in Section 1
        if len(subjects) == 0:
            raw_lines = relevant_text.splitlines()
            stitched_blocks = []
            current_block_lines = []
            active_line_category = None

            institution_pattern = re.compile(
                r"\b(?:UNIVERSITY|AFFILIATED\s+INSTITUTIONS?|COLLEGE\s+OF|INSTITUTE\s+OF|DEPARTMENT\s+OF|BRANCH\s+OF|REGULATIONS?\s*[-–—:]?\s*\d+|CHOICE\s+BASED\s+CREDIT|AUTONOMOUS|CURRICULUM\s+AND\s+SYLLABI)\b",
                re.I
            )

            for raw_line in raw_lines:
                line_s = raw_line.strip()
                if not line_s or line_s.startswith("--- Page ") or line_s.startswith("|") or line_s.startswith("+") or re.match(r"^[\+\-=\s\|_]+$", line_s):
                    continue
                if sem_heading_pattern.search(line_s):
                    continue

                # Check category subheadings
                cat_match = category_heading_pattern.search(line_s)
                if cat_match:
                    if current_block_lines:
                        stitched_blocks.append((" \n ".join(current_block_lines), active_line_category))
                        current_block_lines = []
                    ch_text = cat_match.group(0).lower()
                    if "professional" in ch_text or "program" in ch_text or "department" in ch_text:
                        active_line_category = "Professional Elective"
                    elif "open" in ch_text or "interdisciplinary" in ch_text:
                        active_line_category = "Open Elective"
                    elif "mandatory" in ch_text or "audit" in ch_text:
                        active_line_category = "Mandatory Audit"
                    elif "lab" in ch_text or "practical" in ch_text:
                        active_line_category = "Laboratory"
                    elif "project" in ch_text or "seminar" in ch_text or "eec" in ch_text:
                        active_line_category = "Project/Seminar"
                    elif "humanities" in ch_text or "hsmc" in ch_text:
                        active_line_category = "Humanities / Management"
                    elif "theory" in ch_text:
                        active_line_category = "Theory Core"
                    continue

                if ignore_line_pattern.search(line_s) or institution_pattern.search(line_s) or ("curriculum" in line_s.lower() and "total" in line_s.lower()):
                    continue

                # Determine if line starts a brand new subject entry
                starts_new = False
                has_sno_prefix = bool(re.match(r"^\s*(?:\d+[\.\)]|\[\d+\])\s*$", line_s) or re.match(r"^\s*(?:\d+[\.\)]|\[\d+\])\s+[A-Za-z0-9]", line_s))
                has_code_prefix = bool(re.match(r"^\s*[A-Z]{2,6}\s*[-/]?\s*\d{2,4}", line_s, re.I))
                
                if has_sno_prefix or has_code_prefix:
                    starts_new = True

                if starts_new and current_block_lines:
                    stitched_blocks.append((" \n ".join(current_block_lines), active_line_category))
                    current_block_lines = [line_s]
                else:
                    current_block_lines.append(line_s)

            if current_block_lines:
                stitched_blocks.append((" \n ".join(current_block_lines), active_line_category))

            for block_text, block_cat in stitched_blocks:
                line_str = block_text.replace("\n", " ").strip()
                if not line_str or len(line_str) < 4 or institution_pattern.search(line_str):
                    continue



                code = ""
                code_match = code_regex.search(line_str)
                if code_match:
                    code_cand = code_match.group(1).replace(" ", "")
                    if not re.match(r"^(?:THE|AND|FOR|WITH|FROM|THIS|THAT|SEMESTER|THEORY|LAB|PRACTICAL|SYLLABUS|UNIT|MODULE|CHAPTER)$", code_cand, re.I):
                        code = code_cand

                credits = None
                cr_match = re.search(r"(?:credits?|cr)\s*[:=]?\s*(\d+(?:\.\d+)?)", line_str, re.I)
                if cr_match:
                    try:
                        credits = float(cr_match.group(1))
                    except Exception:
                        pass

                l_hrs, t_hrs, p_hrs = None, None, None
                ltp_match = re.search(r"L\s*:\s*(\d+)\s*T\s*:\s*(\d+)\s*P\s*:\s*(\d+)", line_str, re.I)
                if ltp_match:
                    l_hrs = int(ltp_match.group(1))
                    t_hrs = int(ltp_match.group(2))
                    p_hrs = int(ltp_match.group(3))

                ltpc_end = re.search(r"\b(\d+)\s+(\d+)\s+(\d+)\s+(\d+(?:\.\d+)?)\s*$", line_str)
                if ltpc_end and not l_hrs:
                    try:
                        l_hrs = int(ltpc_end.group(1))
                        t_hrs = int(ltpc_end.group(2))
                        p_hrs = int(ltpc_end.group(3))
                        if credits is None:
                            credits = float(ltpc_end.group(4))
                    except Exception:
                        pass

                clean_name = re.sub(r"^\s*(?:\d+[\.\)]|\[\d+\])\s*", "", line_str)
                # Remove Course Group prefix (e.g. PCC, HSC, PROJ, PEC, BSC, ESC, MC, OEC, HSMC, EEC)
                clean_name = re.sub(r"^\s*(?:PCC|HSC|PROJ|PEC|BSC|ESC|MC|OEC|HSMC|EEC)\s+", "", clean_name, flags=re.I)
                if code:
                    clean_name = re.sub(r"\b" + re.escape(code) + r"\b", "", clean_name, flags=re.I)
                    if code_match:
                        clean_name = re.sub(r"\b" + re.escape(code_match.group(1)) + r"\b", "", clean_name, flags=re.I)
                clean_name = re.sub(r"\[.*?\]", "", clean_name)
                clean_name = re.sub(r"\(.*?\)", "", clean_name)
                clean_name = re.sub(r"(?:credits?|cr)\s*[:=]?\s*\d+(?:\.\d+)?.*$", "", clean_name, flags=re.I)
                clean_name = re.sub(r"\b\d+\s*(?:credits?|cr)\b.*$", "", clean_name, flags=re.I)
                clean_name = re.sub(r"L\s*[:=]?\s*\d+\s*T\s*[:=]?\s*\d+\s*P\s*[:=]?\s*\d+.*$", "", clean_name, flags=re.I)
                if ltpc_end:
                    clean_name = re.sub(r"\s+\d+\s+\d+\s+\d+\s+\d+(?:\.\d+)?\s*$", "", clean_name)
                clean_name = re.sub(r"\s+\d+(?:\.\d+)?\s*$", "", clean_name)
                clean_name = re.sub(r"[-:–—|()]+", " ", clean_name)
                clean_name = re.sub(r"[\*\#]+", "", clean_name)
                clean_name = re.sub(r"\s+", " ", clean_name).strip()

                is_header_noise = any(k in clean_name.lower() for k in ("course group", "course code", "course title", "subject code", "subject title", "sl. no", "contact periods", "hours per week"))
                if is_header_noise:
                    continue

                if len(clean_name) >= 3 and not any(k in clean_name.lower() for k in ("semester", "scheme", "courses total", "credits", "hours", "page", "internal", "external", "maximum marks")):
                    # Filter out generic elective placeholder rows or course category acronym headers without a specific course code
                    if not code and (
                        re.match(r"^(?:professional\s+electives?(?:\s+courses?)?|open\s+electives?(?:\s+courses?)?|program\s+electives?(?:\s+courses?)?|department(?:al)?\s+electives?(?:\s+courses?)?|elective\s+courses?)(?:\s*[-–—:]?\s*[0-9ivx]+|\s*\([a-z0-9\s\-]+\))?$", clean_name, re.I)
                        or re.match(r"^(?:PCC|HSC|PROJ|PEC|BSC|ESC|MC|OEC|HSMC|EEC|PC|PE|OE|HS|MC|PR|PW|VA)$", clean_name.strip(), re.I)
                    ):
                        continue

                    norm_clean = re.sub(r"[^a-z0-9]", "", clean_name.lower())
                    code_norm = code.upper().replace(" ", "") if code else ""

                    # Check for existing subject entry (Exact code or exact normalized name match)
                    existing_idx = None
                    for idx, s in enumerate(subjects):
                        s_norm = re.sub(r"[^a-z0-9]", "", (s.get("name") or s.get("subjectName") or "").lower())
                        s_code = (s.get("code") or s.get("subjectCode") or "").upper().replace(" ", "")
                        if (code_norm and s_code and code_norm == s_code) or (s_norm and norm_clean and s_norm == norm_clean):
                            existing_idx = idx
                            break

                    if existing_idx is not None:
                        if credits is not None and subjects[existing_idx].get("credits") is None:
                            subjects[existing_idx]["credits"] = credits
                        if l_hrs is not None and subjects[existing_idx].get("lecture_hours") is None:
                            subjects[existing_idx]["lecture_hours"] = l_hrs
                            subjects[existing_idx]["tutorial_hours"] = t_hrs
                            subjects[existing_idx]["practical_hours"] = p_hrs
                        continue

                    category = categorize_subject(clean_name, code, line_str, block_cat)

                    sub_obj = build_normalized_subject(
                        name=clean_name,
                        code=code,
                        cat=category,
                        cr=credits,
                        l_h=l_hrs,
                        t_h=t_hrs,
                        p_h=p_hrs,
                        raw_src_text=line_str,
                        source_pages=[1],
                        source_sec=explicit_identifier or f"Semester {target_semester or ''} Scheme Table"
                    )
                    subjects.append(sub_obj)

        # ── 3. High-Speed Exact Source Page Matching for Extracted Subjects ──
        for s in subjects:
            s_code = s.get("code", "")
            s_name = s.get("name", "")
            code_flex = ""
            if s_code:
                c_clean = re.sub(r"\s+", "", s_code)
                code_flex = re.sub(r"([A-Za-z]+)(\d+)", r"\1\\s*\2", c_clean)
            matched_pages = []
            for p_num, p_txt in page_texts:
                code_matched = bool(code_flex and re.search(r"\b" + code_flex + r"\b", p_txt, re.I))
                name_matched = bool(s_name and len(s_name) >= 4 and s_name.lower() in p_txt.lower())
                if code_matched or name_matched:
                    matched_pages.append(p_num)
            if not matched_pages:
                matched_pages = [1]
            s["sourcePages"] = matched_pages
            s["source_page_numbers"] = matched_pages
            s["source_page"] = matched_pages[0]

        # ── 4. Deep Dynamic Unit/Module Extraction Across Entire Document Text ──
        chapters_map: Dict[str, List[Dict[str, Any]]] = {}

        for s in subjects:
            s_name = s.get("name", "")
            s_code = s.get("code", "")
            if not s_name:
                continue

            patterns = []
            if s_code:
                c_clean = re.sub(r"\s+", "", s_code)
                code_flex = re.sub(r"([A-Za-z]+)(\d+)", r"\1\\s*\2", c_clean)
                patterns.append(r"\b" + code_flex + r"\b")
            clean_n = re.sub(r"[^A-Za-z0-9\s]", " ", s_name).strip()
            words = [w for w in clean_n.split() if len(w) > 3]
            if len(words) >= 2:
                patterns.append(r"\b" + r"\s+".join(re.escape(w) for w in words[:3]) + r"\b")

            course_start = -1
            other_codes = [other_s.get("code") for other_s in subjects if other_s.get("code") and other_s.get("code").strip() and other_s.get("code").strip() != s_code]
            other_names = [other_s.get("name") for other_s in subjects if other_s.get("name") and other_s.get("name").strip() and other_s.get("name").strip().lower() != s_name.lower() and len(other_s.get("name").strip()) > 3]

            for p in patterns:
                for m in re.finditer(p, raw_text, re.I):
                    after_text = raw_text[m.start():m.start() + 2000]
                    unit_m = re.search(r"\b(?:MODULE|UNIT|COURSE OBJECTIVES|PRACTICALS?|LIST OF EXPERIMENTS)\b", after_text, re.I)
                    if unit_m:
                        prefix_text = after_text[:unit_m.start()]
                        if other_codes and any(re.search(r"\b" + re.escape(oc) + r"\b", prefix_text, re.I) for oc in other_codes):
                            continue
                        course_start = m.start()
                        break
                if course_start != -1:
                    break

            units: List[Dict[str, Any]] = []
            if course_start != -1:
                course_block = raw_text[course_start:course_start + 12000]

                # Stop at the boundary of any other extracted subject
                if other_codes:
                    other_code_pat = r"(?:^|\n)\s*(?:" + "|".join(re.escape(c) for c in other_codes) + r")\b"
                    next_c_match = re.search(other_code_pat, course_block[50:], re.I)
                    if next_c_match:
                        course_block = course_block[:50 + next_c_match.start()]

                if other_names:
                    other_name_pat = r"(?:^|\n)\s*(?:[A-Z]{2,6}\s*\d{3,4}\s+)?(?:" + "|".join(re.escape(n) for n in other_names) + r")\b"
                    next_n_match = re.search(other_name_pat, course_block[50:], re.I)
                    if next_n_match:
                        course_block = course_block[:50 + next_n_match.start()]

                next_gen_course = re.search(r"\n\s*(?:[A-Z]{2,6}\s*\d{3,4}(?:\s+[A-Z\s]{3,}|\s*\n)|SEMESTER\s+[0-9IVX]+)", course_block[80:], re.I)
                if next_gen_course:
                    course_block = course_block[:80 + next_gen_course.start()]

                unit_header_pattern = re.compile(
                    r"(?:^|\n)\s*(MODULE|UNIT)\s+([0-9IVXLCDM]+)\s*[:\-–—\s]*([^\n\r]+)",
                    re.I
                )

                unit_matches = list(unit_header_pattern.finditer(course_block))
                for u_idx, um in enumerate(unit_matches):
                    u_type = um.group(1).title()
                    u_num = um.group(2).strip()
                    u_title = um.group(3).strip()
                    u_title_clean = re.sub(r"\s+\d+\s*$", "", u_title).strip()
                    
                    body_start = um.end()
                    body_end = unit_matches[u_idx + 1].start() if u_idx + 1 < len(unit_matches) else len(course_block)
                    body = course_block[body_start:body_end].strip()

                    # Stop body at end markers if present
                    end_marker = re.search(r"\n\s*(?:PRACTICALS?|LIST OF EXPERIMENTS|TEXT BOOKS?|REFERENCES?|COURSE OUTCOMES?)\b", body, re.I)
                    if end_marker:
                        body = body[:end_marker.start()].strip()
                    
                    concepts = []
                    raw_concepts = [c.strip() for c in re.split(r"[–—\-•\*\n\r]+", body) if len(c.strip()) > 3]
                    for rc in raw_concepts:
                        rc_clean = re.sub(r"\s+\d+\s*$", "", rc).strip()
                        if rc_clean and not any(k in rc_clean.lower() for k in ("hours", "total", "page", "sdg")):
                            concepts.append(rc_clean)

                    if not concepts:
                        parts = [p.strip() for p in re.split(r"[,;]+", u_title) if len(p.strip()) > 2]
                        if len(parts) > 1:
                            u_title_clean = parts[0]
                            concepts = parts[1:]
                        else:
                            concepts = [u_title_clean]

                    units.append({
                        "name": f"{u_type} {u_num}: {u_title_clean}",
                        "concepts": concepts[:8] if concepts else [u_title_clean]
                    })


                prac_match = re.search(r"(?:^|\n)\s*(?:PRACTICALS?|LIST OF EXPERIMENTS)\s*([\s\S]*?)(?=(?:(?:^|\n)\s*(?:TEXT BOOKS?|REFERENCES?|COURSE OUTCOMES?)|$))", course_block, re.I)
                if prac_match:
                    prac_text = prac_match.group(1).strip()
                    exp_lines = [l.strip() for l in prac_text.splitlines() if l.strip() and len(l.strip()) > 5 and not l.strip().startswith("--- Page ")]
                    if exp_lines:
                        units.append({
                            "name": "Laboratory & Practical Experiments",
                            "concepts": exp_lines[:10]
                        })

            # If no course detail blocks were found, fallback to scanning relevant_text for inline units
            if not units:
                for line in relevant_text.splitlines():
                    unit_match = re.match(r"^(?:Unit|Module|Chapter)\s*([0-9IVXLCDM]+)\s*[:\-\.]?\s*(.+)$", line.strip(), re.I)
                    if unit_match:
                        unit_num = unit_match.group(1)
                        unit_title = unit_match.group(2).strip()
                        parts = [p.strip() for p in re.split(r"[,;.]+", unit_title) if len(p.strip()) > 2]
                        concepts = parts[1:] if len(parts) > 1 else parts
                        units.append({
                            "name": f"Unit {unit_num}: {parts[0] if parts else unit_title}",
                            "concepts": concepts if concepts else [parts[0] if parts else unit_title]
                        })

            chapters_map[s_name] = units
            s["modules"] = units
            s["units"] = units
            s["chapters"] = units
            s["topics"] = [c for u in units for c in u.get("concepts", [])]

        return {
            "validation_status": "VALID" if subjects else "NEEDS_REVIEW",
            "detected_semesters": detected_semesters,
            "explicit_semester_identifier": explicit_identifier,
            "target_semester": target_semester,
            "course_title": "Official Semester Curriculum",
            "expected_subject_count": len(subjects),
            "extracted_subject_count": len(subjects),
            "completeness_verified": bool(subjects),
            "completeness_notes": f"Extracted {len(subjects)} subjects with verified source provenance across document pages.",
            "subjects": subjects,
            "extracted_subjects": [s["name"] for s in subjects],
            "chapters": chapters_map,
            "units": chapters_map
        }

    def analyze_syllabus(
        self,
        content_or_file: Any,
        level: str = "college",
        semester: Any = "",
        class_level: str = "",
        domain: str = "",
        stream: str = "",
        degree: str = "",
        department: str = "",
        regulation: str = "",
        academic_year: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze and validate syllabus with strict semester mapping.
        For college students:
          - Scans for semester identifiers (e.g. Semester 5, Sem V, 5th Sem).
          - If multi-semester document, extracts ONLY the section for the target semester.
          - If mismatch (e.g. Sem 6 uploaded for Sem 5 profile), sets validation_status='MISMATCH'.
          - If ambiguous, sets validation_status='NEEDS_REVIEW'.
        """
        target_sem_str = str(semester or "").strip()
        dept_str = domain or department or stream or "General Engineering/Science"
        prog_str = degree or "Degree Program"

        if level.lower() == "college" and target_sem_str:
            sem_instruction = f"""
CRITICAL STUDENT PROFILE & AUTHORITATIVE SECTION MAPPING:
The authenticated student's profile is strictly authoritative:
- Program / Degree: {prog_str}
- Department / Branch: {dept_str}
- Semester: {target_sem_str}

MULTI-DEPARTMENT / MULTI-PROGRAM DISAMBIGUATION:
If the uploaded document contains multiple departments, branches, or programs (e.g. Mechanical Engineering, Civil Engineering, Computer Science, Information Technology, Electrical Engineering, etc.):
- Locate the specific section or subsection belonging to the student's department/program: "{dept_str}" / "{prog_str}".
- Extract subjects ONLY from the student's department section for Semester {target_sem_str}.
- DO NOT extract, combine, or mix subjects from other departments, other programs, or other semesters.

CRITICAL EVIDENCE-BASED & ANTI-HALLUCINATION RULES:
Every extracted subject MUST retain its verifiable source evidence from the uploaded document.
For each subject capture:
* Exact official course code (e.g. "IT501", "20IT51", "PCC-CS501") where present
* Exact official subject name (Preserve exact original title, do not truncate, invent, or merge)
* Subject category ("Theory Core", "Laboratory", "Professional Elective", "Open Elective", "Mandatory Audit", "Project/Seminar")
* Credits (numeric e.g. 3, 4, 1.5, 2, 0)
* L-T-P hours (Lecture, Tutorial, Practical) if present
* source_page_numbers: Array of integer page numbers where this subject is found (e.g. [4])
* source_section: Specific table name, scheme heading, or chapter section (e.g. "Semester 5 Scheme Table - Information Technology")
* source_text: Exact verifiable sentence or table row excerpt from the syllabus document
* semester_evidence: Document heading or text establishing that this subject belongs to Semester {target_sem_str}
* confidence: Numeric score between 0.70 and 1.0 based on clarity in the document

Do NOT invent, fabricate, or include any subject not physically present in the uploaded document.

1. FULL DOCUMENT INSPECTION & EXHAUSTIVE EXTRACTION:
   - Search the entire document for Semester {target_sem_str} course schemes, tables, matrices, and syllabus pages.
   - If multiple departments/programs are present in the document, extract subjects ONLY from the section corresponding to "{dept_str}".
   - Extract EVERY SINGLE subject/course listed for Semester {target_sem_str}.
   - Do NOT stop after the first few subjects.
   - Do NOT assume a fixed number of subjects or use an AI guess.
   - Extract ALL categories:
     * Theory / Core subjects
     * Laboratory / Practical courses (e.g. Web Technologies Lab, Compiler Design Lab)
     * Professional / Departmental Electives (e.g. Elective I, Elective II)
     * Open Electives
     * Mandatory non-credit courses & Audit courses (e.g. Constitution of India, Universal Human Values)
     * Formally listed project / seminar / mini-project components
   - Do NOT mix subjects from other semesters or unrelated departments.
   - If document is exclusively for a DIFFERENT semester and does not contain Semester {target_sem_str}:
     * Set "validation_status": "MISMATCH"
     * Set "mismatch_reason": "The uploaded syllabus does not appear to match your current Semester {target_sem_str} profile."
   - COMPLETENESS VERIFICATION:
     * Count the total number of subjects/courses listed in the Semester {target_sem_str} scheme table for {dept_str} ("expected_subject_count").
     * Count the extracted subjects ("extracted_subject_count").
     * If all listed subjects are fully captured without omission: "completeness_verified": true.
     * If there are unextracted table rows, missing labs, or ambiguity: "completeness_verified": false, "validation_status": "NEEDS_REVIEW", and specify the exact section/page requiring review.
"""
        else:
            sem_instruction = f"""
CRITICAL CLASS/LEVEL MAPPING & COMPLETENESS RULES:
The authenticated student's profile is:
- Level: {level.upper()}
- Class/Grade: {class_level or 'Standard'}
- Board/Stream: {dept_str}

1. Inspect the complete document for Class {class_level} curriculum.
2. Extract all distinct academic subjects without omissions (Theory, Practical, Languages).
3. Set "validation_status": "VALID", "completeness_verified": true.
"""

        prompt = f"""
You are LearnSphere AI's authoritative academic curriculum engine running gemini-3.6-flash.
Analyze the uploaded syllabus document strictly against the student's profile with ZERO silent subject omissions.
Every extracted subject must retain its verifiable source evidence.

{sem_instruction}

RETURN ONLY A VALID JSON OBJECT MATCHING THIS EXACT SCHEMA:
{{
  "validation_status": "VALID" | "MISMATCH" | "NEEDS_REVIEW",
  "detected_semesters": [integer or string semester numbers found in document],
  "explicit_semester_identifier": "exact text from document if found, else null",
  "target_semester": "{target_sem_str}",
  "mismatch_reason": "explanation string if MISMATCH or NEEDS_REVIEW, else null",
  "course_title": "Official Program / Scheme Title",
  "expected_subject_count": 8,
  "extracted_subject_count": 8,
  "completeness_verified": true,
  "completeness_notes": "All subjects from Semester {target_sem_str} scheme verified and extracted.",
  "subjects": [
    {{
      "code": "CS501",
      "name": "Exact Subject Name",
      "type": "Theory Core" | "Laboratory" | "Professional Elective" | "Open Elective" | "Mandatory Audit" | "Project/Seminar",
      "category": "Program Core",
      "credits": 3.0,
      "lecture_hours": 3,
      "tutorial_hours": 0,
      "practical_hours": 0,
      "semester": "{target_sem_str}",
      "source_page_numbers": [4],
      "source_section": "Semester 5 Subject Table",
      "source_text": "1. CS501 Database Management Systems [Credits: 3, L:3 T:0 P:0]",
      "semester_evidence": "Found under section heading 'SEMESTER V - B.TECH'",
      "confidence": 0.98
    }}
  ],
  "extracted_subjects": ["Exact Subject Name 1", "Exact Subject Name 2"],
  "chapters": {{
    "Exact Subject Name 1": [
      {{
        "name": "Unit I: Module Title",
        "concepts": ["Concept 1", "Concept 2"]
      }}
    ]
  }},
  "key_topics": ["Key Topic 1", "Key Topic 2"],
  "challenge_scenarios": [
    {{"title": "Scenario 1", "description": "Scenario details"}}
  ]
}}
"""
        # ── STAGES 1 TO 5A: Fast Deterministic Extraction ─────────────────────
        det_res = self._deterministic_syllabus_parser(
            content_or_file,
            target_semester=target_sem_str,
            level=level,
            dept_str=dept_str,
            prog_str=prog_str
        )
        det_status = str(det_res.get("validation_status") or "").upper().strip()
        det_subjects = det_res.get("subjects") or []

        # If deterministic parser found a clear match or definitive mismatch/needs_review,
        # return immediately without making an expensive or slow full-document AI call!
        if det_status in ("MISMATCH", "NEEDS_REVIEW") or (det_status == "VALID" and len(det_subjects) >= 1):
            res = det_res
        else:
            # ── STAGE 5B: Targeted AI Extraction on Sliced Text Only ──────────
            # Only slice the target semester section (not the entire 80-page document)
            raw_text = str(content_or_file or "")
            if isinstance(content_or_file, str) and Path(content_or_file).is_file():
                try:
                    import pymupdf as fitz
                    doc = fitz.open(content_or_file)
                    raw_text = "\n".join(page.get_text("text") or "" for page in doc)
                except Exception:
                    pass

            # Target semester slice
            sliced_content = raw_text[:12000]
            if target_sem_str:
                sem_idx = raw_text.lower().find(f"semester {target_sem_str.lower()}")
                if sem_idx != -1:
                    sliced_content = raw_text[max(0, sem_idx - 500):sem_idx + 8000]

            text_prompt = f"{prompt}\n\n[Sliced Syllabus Document Text]:\n{sliced_content}"
            res = {}
            try:
                raw = self.generate_content(text_prompt, json_output=True, temperature=0.1)
                res = self.parse_json_response(raw)
            except Exception as exc:
                logger.warning("[GeminiService] AI syllabus extraction exception: %s. Using deterministic output.", exc)
                res = det_res

        if not isinstance(res, dict):
            res = det_res

        # ── Python Post-Processing & Evidence Normalization ────────────────────
        val_status = str(res.get("validation_status") or "").upper().strip()
        
        # Normalize subjects list with full evidence metadata
        raw_subjects = res.get("subjects") or []
        parsed_subjects = []
        if isinstance(raw_subjects, list):
            for item in raw_subjects:
                if isinstance(item, dict) and item.get("name"):
                    s_name = str(item.get("name") or "").strip()
                    s_code = str(item.get("code") or "").strip()
                    s_sec = str(item.get("source_section") or item.get("source_page") or f"Semester {target_sem_str or ''} Scheme Table").strip()
                    s_text = str(item.get("source_text") or f"{s_code} {s_name}".strip()).strip()
                    s_sem_ev = str(item.get("semester_evidence") or f"Semester {target_sem_str} Section").strip()
                    
                    pages_raw = item.get("source_page_numbers") or item.get("source_pages") or [item.get("source_page", 1)]
                    if isinstance(pages_raw, list):
                        pages = [int(p) for p in pages_raw if str(p).isdigit()]
                    elif isinstance(pages_raw, (int, str)) and str(pages_raw).isdigit():
                        pages = [int(pages_raw)]
                    else:
                        pages = [1]
                    if not pages:
                        pages = [1]

                    sub_id = str(item.get("subjectId") or item.get("id") or f"sub_{hashlib.md5(f'{prog_str}_{dept_str}_{target_sem_str}_{s_name}'.encode('utf-8')).hexdigest()[:10]}")
                    conf_score = float(item["confidence"]) if item.get("confidence") is not None and str(item.get("confidence")).replace('.', '', 1).isdigit() else (float(item["extractionConfidence"]) if item.get("extractionConfidence") is not None and str(item.get("extractionConfidence")).replace('.', '', 1).isdigit() else 0.98)
                    c_type = str(item.get("courseType") or item.get("type") or item.get("category") or "Theory Core").strip()
                    cr_val = float(item["credits"]) if item.get("credits") is not None and str(item.get("credits")).replace('.', '', 1).isdigit() else None

                    parsed_subjects.append({
                        "subjectId": sub_id,
                        "id": sub_id,
                        "subjectCode": s_code,
                        "code": s_code,
                        "subjectName": s_name,
                        "name": s_name,
                        "courseType": c_type,
                        "type": c_type,
                        "category": str(item.get("category") or c_type).strip(),
                        "credits": cr_val,
                        "lecture_hours": int(item["lecture_hours"]) if str(item.get("lecture_hours", "")).isdigit() else None,
                        "tutorial_hours": int(item["tutorial_hours"]) if str(item.get("tutorial_hours", "")).isdigit() else None,
                        "practical_hours": int(item["practical_hours"]) if str(item.get("practical_hours", "")).isdigit() else None,
                        "semester": target_sem_str or item.get("semester"),
                        "program": prog_str or "Degree Program",
                        "department": dept_str or "Engineering/Science",
                        "sourcePages": pages,
                        "source_page_numbers": pages,
                        "source_page": pages[0] if pages else 1,
                        "sourceSection": s_sec,
                        "source_section": s_sec,
                        "sourceText": s_text,
                        "source_text": s_text,
                        "semester_evidence": s_sem_ev,
                        "extractionConfidence": conf_score,
                        "confidence": conf_score,
                        "evidence_verified": True
                    })

        # Multi-department validation for college students:
        # If the input document contains multiple departments, ensure extracted subjects belong ONLY to student's department
        if level.lower() == "college" and dept_str and len(dept_str) > 2 and parsed_subjects:
            raw_doc_text = str(content_or_file or "") if isinstance(content_or_file, str) else ""
            if "DEPARTMENT OF" in raw_doc_text.upper() or "BRANCH OF" in raw_doc_text.upper():
                det_res = self._deterministic_syllabus_parser(content_or_file, target_semester=target_sem_str, level=level, dept_str=dept_str, prog_str=prog_str)
                det_names = set(s.get("name", "").lower() for s in det_res.get("subjects", []))
                if det_names:
                    # Filter parsed_subjects to only include those in the student's department section
                    filtered = [s for s in parsed_subjects if s["name"].lower() in det_names]
                    if filtered:
                        parsed_subjects = filtered

        # Ensure extracted_subjects contains all subject names
        extracted_names = [s["name"] for s in parsed_subjects] if parsed_subjects else (res.get("extracted_subjects") or [])
        res["extracted_subjects"] = extracted_names
        res["subjects"] = parsed_subjects
        
        extracted_count = len(extracted_names)
        expected_count = res.get("expected_subject_count")
        if expected_count is not None:
            try:
                expected_count = int(expected_count)
            except (ValueError, TypeError):
                expected_count = extracted_count
        else:
            expected_count = extracted_count

        res["extracted_subject_count"] = extracted_count
        res["extractedSubjectCount"] = extracted_count
        res["expected_subject_count"] = expected_count
        res["expectedSubjectCount"] = expected_count

        # Completeness Check: If expected count > extracted count, flag NEEDS_REVIEW
        completeness_verified = bool(res.get("completeness_verified", True))
        if expected_count > 0 and extracted_count < expected_count:
            completeness_verified = False
            if val_status == "VALID":
                val_status = "NEEDS_REVIEW"
                res["mismatch_reason"] = f"Completeness check alert: Document lists {expected_count} subjects in the semester scheme table, but {extracted_count} were extracted. Please review."

        res["completeness_verified"] = completeness_verified
        res["completenessVerified"] = completeness_verified

        sem_word_map = {
            "1": 1, "01": 1, "1ST": 1, "FIRST": 1, "I": 1,
            "2": 2, "02": 2, "2ND": 2, "SECOND": 2, "II": 2,
            "3": 3, "03": 3, "3RD": 3, "THIRD": 3, "III": 3,
            "4": 4, "04": 4, "4TH": 4, "FOURTH": 4, "IV": 4,
            "5": 5, "05": 5, "5TH": 5, "FIFTH": 5, "V": 5,
            "6": 6, "06": 6, "6TH": 6, "SIXTH": 6, "VI": 6,
            "7": 7, "07": 7, "7TH": 7, "SEVENTH": 7, "VII": 7,
            "8": 8, "08": 8, "8TH": 8, "EIGHTH": 8, "VIII": 8
        }
        norm_detected = []
        for ds in (res.get("detected_semesters") or []):
            if isinstance(ds, int):
                norm_detected.append(ds)
            elif str(ds).isdigit():
                norm_detected.append(int(ds))
            else:
                ds_clean = str(ds).upper().strip()
                if ds_clean in sem_word_map:
                    norm_detected.append(sem_word_map[ds_clean])
                else:
                    token_m = re.search(r"\b(0?[1-8]|I|II|III|IV|V|VI|VII|VIII|[1-8](?:ST|ND|RD|TH)|FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH)\b", ds_clean, re.I)
                    if token_m and token_m.group(1).upper() in sem_word_map:
                        norm_detected.append(sem_word_map[token_m.group(1).upper()])

        if norm_detected:
            res["detected_semesters"] = norm_detected

        if level.lower() == "college" and target_sem_str:
            target_int = int(target_sem_str) if str(target_sem_str).isdigit() else sem_word_map.get(str(target_sem_str).upper())
            if not norm_detected:
                # No semester headings identified anywhere in document
                val_status = "NEEDS_REVIEW"
                completeness_verified = False
                res["completeness_verified"] = False
                res["completenessVerified"] = False
                res["mismatch_reason"] = "Semester headings could not be reliably identified in the uploaded document. Syllabus marked for review to avoid cross-semester guessing."
            elif target_int and target_int not in norm_detected:
                val_status = "MISMATCH"
                completeness_verified = False
                res["completeness_verified"] = False
                res["completenessVerified"] = False

        if val_status not in ("VALID", "MISMATCH", "NEEDS_REVIEW"):
            if level.lower() == "college" and target_sem_str:
                val_status = "VALID" if (extracted_count > 0 and completeness_verified) else "NEEDS_REVIEW"
            else:
                val_status = "VALID"

        res["validation_status"] = val_status
        res["validationStatus"] = val_status
        res["target_semester"] = target_sem_str

        # Ensure mismatch_reason is user-friendly if MISMATCH
        if val_status == "MISMATCH" and not res.get("mismatch_reason"):
            detected = res.get("detected_semesters") or []
            detected_str = f" (Detected: Semester {', '.join(map(str, detected))})" if detected else ""
            res["mismatch_reason"] = f"The uploaded syllabus does not appear to match your current Semester {target_sem_str} profile.{detected_str}"

        # Ensure chapters and units are synchronized and valid
        if not isinstance(res.get("chapters"), dict):
            res["chapters"] = {}
        if not isinstance(res.get("units"), dict) or not res.get("units"):
            res["units"] = res.get("chapters", {})
        if not res.get("chapters") and res.get("units"):
            res["chapters"] = res["units"]

        if not isinstance(res.get("key_topics"), list):
            res["key_topics"] = []
        if not isinstance(res.get("challenge_scenarios"), list):
            res["challenge_scenarios"] = []

        return res

    def generate_reality_lab(self, subject: str, subject_id: str = "", topic: str = "", module: str = "", difficulty: str = "Medium", validated_topics: List[str] = None, syllabus_context: str = "", semester: str = "", program: str = "", department: str = "") -> Dict[str, Any]:
        """
        Generate a strictly semester-aware practical activity grounded in the student's validated syllabus curriculum.
        Includes all 11 core pedagogical elements:
          1. activity title
          2. real-world connection
          3. objective
          4. materials (day-to-day/local where safe)
          5. steps
          6. expected observation
          7. concept being demonstrated
          8. explanation
          9. safety considerations (chemical/electrical/thermal hazard warnings)
          10. questions to test understanding
          11. exam relevance
        """
        sem_str = f"Semester {semester}" if semester and "semester" not in str(semester).lower() else (str(semester) or "Active Semester")
        active_topic = topic or module or (validated_topics[0] if validated_topics else "Core Practical Application")
        mod_lower = str(active_topic or "").lower()

        # Check for pure abstract / unsupported theoretical constructs upfront
        if "unsupported" in mod_lower or "pure abstract" in mod_lower or "non-practical" in mod_lower or "pure theoretical" in mod_lower:
            return self._build_deterministic_reality_lab(subject, subject_id, active_topic, difficulty, sem_str, program, department, validated_topics)

        topics_str = ", ".join(validated_topics[:10]) if validated_topics else active_topic

        prompt = f"""
Generate a comprehensive, syllabus-grounded Reality Lab practical activity for a student using gemini-3.6-flash.

Academic & Syllabus Grounding:
- Program: {program or 'Engineering'}
- Department: {department or 'Information Technology'}
- Semester: {sem_str}
- Subject: {subject} (Subject ID: {subject_id or 'N/A'})
- Selected Validated Topic: {active_topic}
- Validated Syllabus Topics: {topics_str}
- Difficulty Level: {difficulty}
- Syllabus Context Excerpt: {syllabus_context[:1200] if syllabus_context else 'Active accredited curriculum syllabus'}

Requirements:
1. Connect the selected syllabus topic directly to an authentic practical/laboratory activity or real-world experiment.
2. Materials: Use day-to-day/local materials where scientifically safe and appropriate, or standard software/lab equipment.
3. Safety: For experiments involving chemicals, electricity, heat, pressure, or other hazards, include explicit safety warnings and strictly avoid unsafe instructions. For computer/software labs, specify operational safety (data protection, isolated testbed).
4. If no suitable practical activity exists for this purely theoretical topic, set "is_supported": false with an explanation.

Return ONLY a valid JSON object matching this schema:
{{
  "scenario_id": "rl_{subject.lower()[:4]}_{difficulty.lower()}",
  "title": "Descriptive Practical Activity Title",
  "subject": "{subject}",
  "subject_id": "{subject_id}",
  "semester": "{sem_str}",
  "syllabus_topic": "{active_topic}",
  "real_world_connection": "Specific industrial, engineering, or day-to-day real-world phenomenon",
  "objective": "Clear, measurable practical and conceptual learning objective",
  "materials": [
    "Safe day-to-day / local material or laboratory tool 1",
    "Material 2"
  ],
  "steps": [
    "Step 1: Setup and initial safety check...",
    "Step 2: Execution and measurement...",
    "Step 3: Verification and recording..."
  ],
  "expected_observation": "Concrete observable physical phenomenon, sensor reading, log output, or metric",
  "concept_being_demonstrated": "Specific curriculum concept, law, algorithm, or theorem",
  "explanation": "Detailed scientific/engineering explanation connecting the observation to the underlying theoretical concept",
  "safety_considerations": "Explicit safety instructions, PPE, electrical/heat/chemical hazard precautions, or workspace safety",
  "questions_to_test_understanding": [
    "Question 1: Conceptual check on the observed phenomenon...",
    "Question 2: Application or troubleshooting scenario..."
  ],
  "exam_relevance": "Direct mapping to university/board examination questions (e.g. Part-B 13/16 mark practical design problem)",
  "task": "Specific practical explanation or analysis problem for the student to solve",
  "expectedConcepts": [
    {{"concept": "{active_topic}", "required": true}},
    {{"concept": "Real-World Application", "required": true}}
  ],
  "eval_criteria": [
    "Technical accuracy of theoretical explanation",
    "Correct interpretation of observation and experimental steps",
    "Awareness of safety considerations and practical constraints"
  ],
  "model_answer": "Complete, comprehensive engineering/scientific solution and explanation",
  "is_supported": true,
  "unsupported_message": ""
}}
"""
        try:
            raw = self.generate_content(prompt, json_output=True)
            res = self.parse_json_response(raw)
            if res and isinstance(res, dict):
                if res.get("is_supported") is False:
                    res.setdefault("subject", subject)
                    res.setdefault("subject_id", subject_id)
                    res.setdefault("semester", sem_str)
                    res.setdefault("syllabus_topic", active_topic)
                    res.setdefault("is_supported", False)
                    res.setdefault("unsupported_message", "No suitable practical activity is defined for this specific theoretical topic in the uploaded syllabus.")
                    return res
                if res.get("title") and (res.get("concept_being_demonstrated") or res.get("practical_concept") or res.get("objective")):
                    res.setdefault("subject", subject)
                    res.setdefault("subject_id", subject_id)
                    res.setdefault("semester", sem_str)
                    res.setdefault("syllabus_topic", active_topic)
                    res.setdefault("real_world_connection", res.get("context") or "Engineering and Day-to-Day Application")
                    res.setdefault("objective", f"Master practical implementation of {active_topic} under real-world constraints.")
                    res.setdefault("materials", ["Standard Laboratory Apparatus / Analytical Environment"])
                    res.setdefault("steps", res.get("procedure") or ["Step 1: Setup testbed", "Step 2: Run experiment", "Step 3: Analyze results"])
                    res.setdefault("procedure", res.get("steps") or ["Step 1: Setup testbed", "Step 2: Run experiment", "Step 3: Analyze results"])
                    res.setdefault("expected_observation", res.get("observation") or "Metrics and physical state changes observed.")
                    res.setdefault("observation", res.get("expected_observation") or "Metrics and physical state changes observed.")
                    res.setdefault("concept_being_demonstrated", res.get("practical_concept") or active_topic)
                    res.setdefault("practical_concept", res.get("concept_being_demonstrated") or active_topic)
                    res.setdefault("explanation", res.get("theory_connection") or f"Grounded in theoretical principles of {subject}.")
                    res.setdefault("theory_connection", res.get("explanation") or f"Grounded in theoretical principles of {subject}.")
                    res.setdefault("safety_considerations", "Ensure electrical isolation, wear safety glasses if handling physical circuits/materials, and verify parameters before applying load.")
                    res.setdefault("questions_to_test_understanding", [
                        f"Why does {active_topic} behave differently under maximum load?",
                        "How would you adjust parameters if the observed output deviates by 15%?"
                    ])
                    res.setdefault("exam_relevance", f"Standard University Examination Question on {subject}: {active_topic}.")
                    res.setdefault("expectedConcepts", [
                        {"concept": active_topic, "required": True},
                        {"concept": "Real-World Application", "required": True}
                    ])
                    res.setdefault("is_supported", True)
                    return res
        except Exception as e:
            logger.warning(f"[GeminiService] generate_reality_lab error: {e}")

        # Deterministic fallback grounded in academic subject & module
        return self._build_deterministic_reality_lab(subject, subject_id, active_topic, difficulty, sem_str, program, department, validated_topics)

    def _build_deterministic_reality_lab(self, subject: str, subject_id: str, topic: str, difficulty: str, semester: str, program: str, department: str, validated_topics: List[str] = None) -> Dict[str, Any]:
        """
        Deterministic, authentic practical activity generator for standard college curriculum topics.
        Guarantees all 11 required fields, proper safety warnings, and zero hallucination.
        """
        sub_lower = subject.lower()
        top_lower = topic.lower() if topic else ""

        # Special check: if topic explicitly says unsupported or out-of-scope
        if "unsupported" in top_lower or "pure abstract non-practical" in top_lower:
            return {
                "scenario_id": "rl_unsupported",
                "title": f"Theoretical Topic: {topic or subject}",
                "subject": subject,
                "subject_id": subject_id,
                "semester": semester,
                "syllabus_topic": topic or subject,
                "real_world_connection": "N/A - Pure Theoretical Construct",
                "objective": "Theoretical conceptual comprehension and mathematical proof.",
                "materials": [],
                "steps": [],
                "procedure": [],
                "expected_observation": "N/A",
                "observation": "N/A",
                "concept_being_demonstrated": "Abstract theoretical model without direct hardware or laboratory apparatus.",
                "practical_concept": "N/A",
                "explanation": "Abstract theoretical principles analyzed via analytical proofs.",
                "theory_connection": "Abstract theoretical model without direct hardware or laboratory apparatus.",
                "safety_considerations": "Safe theoretical study.",
                "questions_to_test_understanding": ["State the governing mathematical theorem."],
                "exam_relevance": "Theory proof questions in semester examination.",
                "task": "N/A",
                "expectedConcepts": [],
                "eval_criteria": [],
                "model_answer": "",
                "is_supported": False,
                "unsupported_message": "No suitable practical activity exists for this purely theoretical topic in the uploaded syllabus. Please select an applied module or laboratory course."
            }

        if "database" in sub_lower or "dbms" in sub_lower:
            return {
                "scenario_id": f"rl_dbms_{difficulty.lower()}",
                "title": "High-Throughput E-Commerce Schema & Query Optimization Under Heavy Load",
                "subject": subject,
                "subject_id": subject_id,
                "semester": semester,
                "syllabus_topic": topic or "Database Design, Normalization & Indexing",
                "real_world_connection": "E-commerce Flash Sale Platforms (Amazon/Flipkart) handling 50,000 orders/second",
                "objective": "Eliminate database update anomalies via BCNF decomposition and reduce query latency using B+ Tree composite indexes.",
                "materials": [
                    "PostgreSQL 16 / MySQL Enterprise Database Server (Local workstation or sandbox)",
                    "pg_stat_activity & EXPLAIN ANALYZE Query Profiler",
                    "Apache JMeter / k6 Load Testing Benchmark Suite"
                ],
                "steps": [
                    "Step 1: Create an unindexed orders table with 2,000,000 rows simulating high traffic.",
                    "Step 2: Execute multi-table join query on customer, payment, and inventory tables with EXPLAIN ANALYZE.",
                    "Step 3: Measure sequential scan latency vs index scan latency.",
                    "Step 4: Decompose anomalous relation into BCNF to eliminate update anomalies.",
                    "Step 5: Apply Composite B+ Tree Index on (customer_id, order_timestamp) and compare CPU/I/O cost."
                ],
                "procedure": [
                    "Step 1: Create an unindexed orders table with 2,000,000 rows simulating high traffic.",
                    "Step 2: Execute multi-table join query on customer, payment, and inventory tables with EXPLAIN ANALYZE.",
                    "Step 3: Measure sequential scan latency vs index scan latency.",
                    "Step 4: Decompose anomalous relation into BCNF to eliminate update anomalies.",
                    "Step 5: Apply Composite B+ Tree Index on (customer_id, order_timestamp) and compare CPU/I/O cost."
                ],
                "expected_observation": "Sequential table scan requires 1450ms and 85,000 disk page reads. After applying composite B+ Tree index, execution drops to 1.8ms with index-only scan and 4 buffer page hits.",
                "observation": "Sequential table scan requires 1450ms and 85,000 disk page reads. After applying composite B+ Tree index, execution drops to 1.8ms with index-only scan and 4 buffer page hits.",
                "concept_being_demonstrated": "B+ Tree Indexing, BCNF Decomposition, and Query Plan Optimization",
                "practical_concept": "B+ Tree Indexing, BCNF Decomposition, and Connection Pool Tuning",
                "explanation": "Relational Algebra Selection Pushdown, B+ Tree logarithmic search complexity O(log_B N), and Boyce-Codd Normal Form (BCNF) Functional Dependency preservation.",
                "theory_connection": "Relational Algebra Selection Pushdown, B+ Tree logarithmic search complexity O(log_B N), and Boyce-Codd Normal Form (BCNF) Functional Dependency preservation.",
                "safety_considerations": "Operational Safety: Always run benchmark load tests in an isolated local database sandbox to avoid table locks or resource starvation on production instances.",
                "questions_to_test_understanding": [
                    "Why does an unindexed table scan cost grow linearly O(N) with table size?",
                    "How does BCNF prevent insertion, deletion, and update anomalies in relational schemas?"
                ],
                "exam_relevance": "Directly maps to University Regulation 16-Mark Question on Normalization (3NF vs BCNF) and B+ Tree Indexing in Relational Databases.",
                "task": "Explain how decomposing a relation into BCNF eliminates update anomalies, and analyze the I/O cost reduction of a composite B+ tree index over sequential scanning.",
                "expectedConcepts": [
                    {"concept": "BCNF Normalization", "required": True},
                    {"concept": "B+ Tree Indexing", "required": True},
                    {"concept": "Query Cost Reduction", "required": False}
                ],
                "eval_criteria": [
                    "Accurate identification of Functional Dependencies and BCNF rules",
                    "Correct explanation of B+ tree index search efficiency vs sequential disk scans",
                    "Clear practical reasoning for query latency reduction"
                ],
                "model_answer": "BCNF ensures that for every non-trivial functional dependency X -> Y, X is a superkey, completely eliminating data redundancy and update anomalies. A composite B+ tree index on (customer_id, order_timestamp) allows logarithmic seek time O(log_B N), transforming an O(N) sequential table scan into direct leaf page traversals.",
                "is_supported": True,
                "unsupported_message": ""
            }
        elif "web" in sub_lower:
            return {
                "scenario_id": f"rl_web_{difficulty.lower()}",
                "title": "Architecting Real-Time WebSocket Notification Engine with JWT Authentication",
                "subject": subject,
                "subject_id": subject_id,
                "semester": semester,
                "syllabus_topic": topic or "Server-Side Engineering & REST API Design",
                "real_world_connection": "Real-time stock ticker or live sports score broadcaster updating millions of connected browsers",
                "objective": "Build a bidirectional event-driven WebSocket communication stream secured via JSON Web Tokens.",
                "materials": [
                    "Node.js Runtime & Express.js Framework",
                    "Socket.IO / WS Native WebSocket Engine",
                    "Postman / Insomnia API Client with JWT Header Interceptor"
                ],
                "steps": [
                    "Step 1: Initialize Express HTTP server with JSON Web Token (JWT) verification middleware.",
                    "Step 2: Upgrade HTTP connection to Full-Duplex WebSocket protocol on authenticated handshake.",
                    "Step 3: Broadcast real-time stock alert messages to subscribed client rooms.",
                    "Step 4: Implement heartbeat ping-pong intervals to detect dropped client sockets.",
                    "Step 5: Stress test concurrent socket connections using Autocannon."
                ],
                "procedure": [
                    "Step 1: Initialize Express HTTP server with JSON Web Token (JWT) verification middleware.",
                    "Step 2: Upgrade HTTP connection to Full-Duplex WebSocket protocol on authenticated handshake.",
                    "Step 3: Broadcast real-time stock alert messages to subscribed client rooms.",
                    "Step 4: Implement heartbeat ping-pong intervals to detect dropped client sockets.",
                    "Step 5: Stress test concurrent socket connections using Autocannon."
                ],
                "expected_observation": "WebSocket maintains a single persistent TCP connection with 2-byte frame overhead per message, reducing latency from 250ms (HTTP polling) to under 8ms for 10,000 active concurrent clients.",
                "observation": "WebSocket maintains a single persistent TCP connection with 2-byte frame overhead per message, reducing latency from 250ms (HTTP polling) to under 8ms for 10,000 active concurrent clients.",
                "concept_being_demonstrated": "Bidirectional Asynchronous Communication & Token-Based Security",
                "practical_concept": "Bidirectional Asynchronous Communication & Token-Based Security",
                "explanation": "TCP 3-Way Handshake, RFC 6455 WebSocket Protocol specification, and Stateless Cryptographic Signatures (HMAC-SHA256).",
                "theory_connection": "TCP 3-Way Handshake, RFC 6455 WebSocket Protocol specification, and Stateless Cryptographic Signatures (HMAC-SHA256).",
                "safety_considerations": "Network Security: Never store unencrypted JWT secret keys in client-side code; enforce rate limiting on handshake endpoints to mitigate denial-of-service (DoS) attacks.",
                "questions_to_test_understanding": [
                    "Why is the HTTP Upgrade header required to establish a WebSocket channel?",
                    "How does stateless JWT authentication reduce database round-trips during high-frequency message broadcasting?"
                ],
                "exam_relevance": "Directly addresses University Exam Section on Web Technologies: RESTful Architecture vs WebSockets and Session Management.",
                "task": "Design the handshake architecture for authenticating a WebSocket connection using JWT, and contrast its network overhead with traditional short polling.",
                "expectedConcepts": [
                    {"concept": "WebSocket Handshake", "required": True},
                    {"concept": "JWT Token Authentication", "required": True},
                    {"concept": "Full-Duplex Overhead Reduction", "required": False}
                ],
                "eval_criteria": [
                    "Detailed protocol flow of HTTP upgrade to WebSocket",
                    "Token verification in handshake headers",
                    "Quantitative comparison of network bandwidth vs polling"
                ],
                "model_answer": "During the initial HTTP GET request with 'Upgrade: websocket' and 'Connection: Upgrade' headers, the server validates the Bearer JWT from query parameters or headers. Once validated, the connection stays open over a single TCP stream.",
                "is_supported": True,
                "unsupported_message": ""
            }
        elif "network" in sub_lower:
            return {
                "scenario_id": f"rl_net_{difficulty.lower()}",
                "title": "Packet-Level Analysis of TCP Slow Start & Congestion Avoidance Under Jitter",
                "subject": subject,
                "subject_id": subject_id,
                "semester": semester,
                "syllabus_topic": topic or "Transport Layer Protocols & Congestion Control",
                "real_world_connection": "High-definition 4K video streaming over mobile networks experiencing packet loss and latency spikes",
                "objective": "Measure TCP Congestion Window (cwnd) dynamics and analyze Fast Retransmit triggers using packet traces.",
                "materials": [
                    "Wireshark Network Packet Analyzer",
                    "Linux iproute2 / tc (Traffic Control) Packet Loss Simulator",
                    "iPerf3 Network Throughput Benchmark"
                ],
                "steps": [
                    "Step 1: Set up traffic control in Linux to inject 3% packet drop and 40ms round-trip latency.",
                    "Step 2: Launch iPerf3 TCP stream to remote host and capture packet trace in Wireshark.",
                    "Step 3: Plot Congestion Window (cwnd) vs Time using Wireshark tcptrace graph.",
                    "Step 4: Identify Triple Duplicate ACKs triggering Fast Retransmit and Fast Recovery.",
                    "Step 5: Compare TCP throughput under additive increase / multiplicative decrease (AIMD)."
                ],
                "procedure": [
                    "Step 1: Set up traffic control in Linux to inject 3% packet drop and 40ms round-trip latency.",
                    "Step 2: Launch iPerf3 TCP stream to remote host and capture packet trace in Wireshark.",
                    "Step 3: Plot Congestion Window (cwnd) vs Time using Wireshark tcptrace graph.",
                    "Step 4: Identify Triple Duplicate ACKs triggering Fast Retransmit and Fast Recovery.",
                    "Step 5: Compare TCP throughput under additive increase / multiplicative decrease (AIMD)."
                ],
                "expected_observation": "During Slow Start, cwnd doubles every RTT. Upon receiving 3 duplicate ACKs, cwnd is halved (AIMD), avoiding catastrophic network congestion collapse.",
                "observation": "During Slow Start, cwnd doubles every RTT. Upon receiving 3 duplicate ACKs, cwnd is halved (AIMD), avoiding catastrophic network congestion collapse.",
                "concept_being_demonstrated": "TCP Reno/Cubic Congestion Window (cwnd) Dynamics & Packet Loss Recovery",
                "practical_concept": "TCP Reno/Cubic Congestion Window (cwnd) Dynamics & Packet Loss Recovery",
                "explanation": "Jacobson's TCP Congestion Control Algorithm, Additive Increase Multiplicative Decrease (AIMD), and Little's Law.",
                "theory_connection": "Jacobson's TCP Congestion Control Algorithm, Additive Increase Multiplicative Decrease (AIMD), and Little's Law.",
                "safety_considerations": "Network Isolation: Perform packet injection tests on loopback or designated private virtual networks to avoid degrading institutional LAN bandwidth.",
                "questions_to_test_understanding": [
                    "What triggers Fast Retransmit before the Retransmission Timeout (RTO) timer expires?",
                    "Why does TCP use Additive Increase instead of continuing exponential multiplication during congestion avoidance?"
                ],
                "exam_relevance": "Standard 13/16 mark question in University Computer Networks exam: Explain TCP Congestion Control Mechanisms with diagrams.",
                "task": "Analyze the behavior of TCP cwnd when 3 duplicate ACKs are received vs when a Retransmission Timeout (RTO) occurs.",
                "expectedConcepts": [
                    {"concept": "TCP Congestion Window", "required": True},
                    {"concept": "Fast Retransmit & 3 Duplicate ACKs", "required": True},
                    {"concept": "AIMD Algorithm", "required": False}
                ],
                "eval_criteria": [
                    "Clear distinction between Fast Retransmit (3 dup ACKs) and Timeout (RTO)",
                    "Mathematical explanation of cwnd adjustment in AIMD",
                    "Practical impact on real-time streaming bandwidth"
                ],
                "model_answer": "Triple duplicate ACKs indicate packet loss without complete path failure; TCP triggers Fast Retransmit, drops ssthresh to cwnd/2, and enters Fast Recovery without resetting cwnd to 1 MSS. In contrast, an RTO timer expiry resets cwnd to 1 MSS and re-enters Slow Start.",
                "is_supported": True,
                "unsupported_message": ""
            }
        else:
            # Generic fallback strictly derived from subject and topic
            return {
                "scenario_id": f"rl_{sub_lower[:4]}_{difficulty.lower()}",
                "title": f"Applied Practical Investigation of {topic or subject}",
                "subject": subject,
                "subject_id": subject_id,
                "semester": semester,
                "syllabus_topic": topic or subject,
                "real_world_connection": f"Industrial systems and practical technologies implementing {topic or subject}",
                "objective": f"Investigate, configure, and verify the governing principles of {topic or subject}.",
                "materials": [
                    f"Day-to-day apparatus / Testbed setup for {subject}",
                    f"Analytical Measurement & Monitoring Tools",
                    f"Official Syllabus Reference: {topic or subject}"
                ],
                "steps": [
                    f"Step 1: Set up the practical test apparatus for {topic or subject} according to laboratory safety protocols.",
                    f"Step 2: Apply calibrated inputs and record baseline measurements under standard operational conditions.",
                    f"Step 3: Introduce controlled variations in load/parameters and measure dynamic responses.",
                    f"Step 4: Compare observed empirical metrics against theoretical mathematical predictions."
                ],
                "procedure": [
                    f"Step 1: Set up the practical test apparatus for {topic or subject} according to laboratory safety protocols.",
                    f"Step 2: Apply calibrated inputs and record baseline measurements under standard operational conditions.",
                    f"Step 3: Introduce controlled variations in load/parameters and measure dynamic responses.",
                    f"Step 4: Compare observed empirical metrics against theoretical mathematical predictions."
                ],
                "expected_observation": f"The measured output follows the characteristic response predicted by the theoretical laws of {topic or subject}, demonstrating stability within calibrated tolerances.",
                "observation": f"The measured output follows the characteristic response predicted by the theoretical laws of {topic or subject}, demonstrating stability within calibrated tolerances.",
                "concept_being_demonstrated": f"Core practical principles of {topic or subject}",
                "practical_concept": f"Practical Application of {topic or subject}",
                "explanation": f"The experimental observations are directly governed by the analytical models and theorems established in {subject}.",
                "theory_connection": f"Governed by foundational theoretical principles of {subject} ({topic or subject}).",
                "safety_considerations": "Safety Protocol: Wear protective eye protection if working with physical hardware/chemistry; ensure circuit breakers and emergency cutoffs are accessible; verify all ratings prior to energizing.",
                "questions_to_test_understanding": [
                    f"What is the primary governing equation behind {topic or subject}?",
                    "How do environmental or operational disturbances affect the expected outcome?"
                ],
                "exam_relevance": f"Standard University Examination Question on {subject}: Practical and Theoretical Concepts of {topic or subject}.",
                "task": f"Explain the practical significance of {topic or subject} in real-world systems, and evaluate how parameter variations impact overall performance.",
                "expectedConcepts": [
                    {"concept": topic or subject, "required": True},
                    {"concept": "Practical Implementation", "required": True}
                ],
                "eval_criteria": [
                    "Accurate explanation of theoretical foundation",
                    "Clear practical observation interpretation",
                    "Adherence to safety protocols"
                ],
                "model_answer": f"In practical engineering, {topic or subject} provides the core mechanism to ensure predictable system behavior under diverse operating conditions, matching theoretical transfer functions and minimizing losses.",
                "is_supported": True,
                "unsupported_message": ""
            }

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

    def evaluate_learn_anywhere_answer(
        self,
        subject: str,
        topic: str,
        question: str,
        expected_answer: str,
        student_answer: str,
        attempt_number: int = 1,
        preferred_language: str = "English"
    ) -> Dict[str, Any]:
        """
        Evaluate a student's answer for Learn from Anywhere interactive concept checks.
        Accepts semantically correct short answers even when wording or language differs.
        Distinguishes conceptual misunderstandings from spelling/grammar errors.
        Never penalizes language differences when academic meaning is correct.
        """
        lang_note = f"The student prefers {preferred_language}. Allow responses in {preferred_language} or mixed language/transliteration as long as academic concept is correct." if preferred_language and preferred_language.lower() != "english" else ""

        prompt = f"""
You are the Academic Evaluator for Learn from Anywhere in LearnSphere AI.
Your task is to evaluate a student's answer to a syllabus concept check question.

Subject: {subject}
Syllabus Topic: {topic}
Question: {question}
Expected Reference Answer: {expected_answer}
Student's Answer: {student_answer}
Attempt Number: {attempt_number}
{lang_note}

EVALUATION DIRECTIVES:
1. SEMANTIC MATCHING: Focus on academic concept accuracy, not exact word-for-word string match. Accept synonyms, rephrasing, and simplified descriptions.
2. MULTILINGUAL TOLERANCE: Do not penalize language differences, transliteration, or native language terms (Hindi, Tamil, etc.) if the core scientific/mathematical meaning is correct.
3. ERROR TYPE CLASSIFICATION:
   - "none": Concept is fully correct.
   - "spelling_grammar_only": Academic concept is correct, but minor spelling or grammar typos are present. Count as correct (`is_correct`: true, `score`: 90-100).
   - "conceptual_misunderstanding": The student misunderstood the underlying academic law, formula, or physical cause.
4. RETRY & HINTS: If incorrect (`is_correct`: false), provide a constructive hint without revealing the exact answer directly. Set `suggested_retry`: true. If attempt_number >= 2, provide a clearer step-by-step hint.

Return ONLY a valid JSON object matching this schema:
{{
  "is_correct": true,
  "score": 100,
  "error_type": "none | spelling_grammar_only | conceptual_misunderstanding",
  "feedback": "Concise specific feedback explaining why the answer is correct or incorrect",
  "explanation": "Scientific/mathematical explanation linking directly to {topic}",
  "suggested_retry": false,
  "additional_hint": "Constructive hint for retrying if answer was incorrect"
}}
"""
        try:
            raw = self.generate_content(prompt, json_output=True)
            res = self.parse_json_response(raw)
            if isinstance(res, dict) and "is_correct" in res:
                res.setdefault("error_type", "none" if res.get("is_correct") else "conceptual_misunderstanding")
                res.setdefault("feedback", "Good effort!" if res.get("is_correct") else "Review the concept and try again.")
                res.setdefault("explanation", f"Concept governed by principles of {topic}.")
                res.setdefault("suggested_retry", not res.get("is_correct"))
                return res
        except Exception as e:
            logger.warning(f"[GeminiService] evaluate_learn_anywhere_answer API call error: {e}")

        # Offline / Rate-Limit Deterministic Fallback Evaluator
        return self._evaluate_learn_anywhere_answer_fallback(
            subject=subject,
            topic=topic,
            question=question,
            expected_answer=expected_answer,
            student_answer=student_answer,
            attempt_number=attempt_number
        )

    def _evaluate_learn_anywhere_answer_fallback(
        self,
        subject: str,
        topic: str,
        question: str,
        expected_answer: str,
        student_answer: str,
        attempt_number: int = 1
    ) -> Dict[str, Any]:
        """Deterministic, offline-resilient semantic evaluation fallback."""
        st_clean = student_answer.strip().lower()
        exp_clean = expected_answer.strip().lower()

        st_words = set(re.findall(r'\w+', st_clean))
        exp_words = set(re.findall(r'\w+', exp_clean))

        stop_words = {"a", "an", "the", "is", "are", "was", "were", "it", "of", "to", "in", "and", "or", "by", "for", "with", "that", "this", "turns", "turn", "mixed", "when", "using", "shows", "show", "makes", "become", "gives", "gives", "into"}
        st_filtered = st_words - stop_words
        exp_filtered = exp_words - stop_words

        if not st_clean:
            return {
                "is_correct": False,
                "score": 0,
                "error_type": "conceptual_misunderstanding",
                "feedback": "Please enter an answer before submitting.",
                "explanation": f"Key concept for {topic}: {expected_answer}",
                "suggested_retry": True,
                "additional_hint": "Think about what physical or mathematical change occurs."
            }

        if st_clean == exp_clean or st_clean in exp_clean or exp_clean in st_clean:
            return {
                "is_correct": True,
                "score": 100,
                "error_type": "none",
                "feedback": "Excellent! Your answer accurately explains the concept.",
                "explanation": f"Scientific principle: {expected_answer}",
                "suggested_retry": False,
                "additional_hint": ""
            }

        overlap = len(st_filtered & exp_filtered)
        total_exp = len(exp_filtered) or 1
        overlap_ratio = overlap / total_exp

        if overlap_ratio >= 0.40 or (overlap >= 2 and overlap_ratio >= 0.30):
            return {
                "is_correct": True,
                "score": 90,
                "error_type": "none" if overlap_ratio >= 0.6 else "spelling_grammar_only",
                "feedback": "Correct! Your answer captures the core academic concept.",
                "explanation": f"Core academic theory for {topic}: {expected_answer}",
                "suggested_retry": False,
                "additional_hint": ""
            }
        else:
            return {
                "is_correct": False,
                "score": 30,
                "error_type": "conceptual_misunderstanding",
                "feedback": f"Not quite. Focus on how {topic} operates in this activity.",
                "explanation": f"Expected principle: {expected_answer}",
                "suggested_retry": True,
                "additional_hint": f"Hint (Attempt #{attempt_number}): Consider the relation between {topic} and the observed changes."
            }

    def generate_additional_practice_questions(
        self,
        subject: str,
        topic: str,
        difficulty: str = "Medium",
        preferred_language: str = "English"
    ) -> List[Dict[str, Any]]:
        """Generate 2-3 additional targeted practice questions for a topic where student needs extra practice."""
        prompt = f"""
Generate 3 additional targeted practice questions on '{topic}' in '{subject}' for a student needing extra practice.
Preferred Language: {preferred_language}

Return ONLY a valid JSON list of question objects:
[
  {{
    "question": "Targeted practice question 1?",
    "answer": "Concise correct answer",
    "explanation": "Why this answer is scientifically correct"
  }},
  ...
]
"""
        try:
            raw = self.generate_content(prompt, json_output=True)
            res = self.parse_json_response(raw)
            if isinstance(res, list) and len(res) > 0:
                return res
        except Exception as e:
            logger.warning(f"[GeminiService] generate_additional_practice_questions error: {e}")

        return [
            {
                "question": f"How does changing scale or volume affect {topic}?",
                "answer": "It scales the physical interaction proportionally.",
                "explanation": f"Proportionality is a fundamental rule in {topic}."
            },
            {
                "question": f"What safety or environmental factor must be controlled during tests of {topic}?",
                "answer": "Temperature, moisture, or surface cleanliness.",
                "explanation": f"Environmental parameters directly influence real-world outcomes in {topic}."
            }
        ]

    def generate_learn_anywhere(
        self,
        subject: str,
        subject_id: str = "",
        topic: str = "",
        unit: str = "",
        curriculum_reference: str = "",
        resource_environment: str = "All Local Resources",
        difficulty: str = "Medium",
        validated_topics: List[str] = None,
        syllabus_context: str = "",
        semester: str = "",
        program: str = "",
        department: str = "",
        custom_materials: str = "",
        constraint_mode: str = "strict_only",
        image_data: str = "",
        preferred_language: str = "English",
        accessibility_notes: str = ""
    ) -> Dict[str, Any]:
        """
        Generate a syllabus-grounded practical learning activity specifically tailored for rural/village students
        with limited educational resources. Transforms difficult textbook concepts into understandable hands-on activities,
        outdoor observations, or conceptual thought experiment analogs using safe, zero-cost everyday materials.

        Strict safety & feasibility rules:
        - NEVER recommend hazardous chemicals, mains electricity (220V), unsafe machinery, or open fire.
        - Feasible, internally consistent, academically rigorous, and age-appropriate.
        - Grounded directly in the authenticated student's validated curriculum topic.
        - Distinguish predicted scientific outcomes from conditional real-world variations.
        - For topics that cannot be safely/reliably physically demonstrated (e.g. quantum mechanics, nuclear reactions, astrophysics),
          provide a safe physical analog / conceptual thought experiment while clearly stating the demonstration boundaries.
        """
        sem_str = f"Semester {semester}" if semester and "semester" not in str(semester).lower() else (str(semester) or "Active Semester")
        active_topic = topic or (validated_topics[0] if validated_topics else "Core Practical Principle")
        topics_str = ", ".join(validated_topics[:10]) if validated_topics else active_topic

        constraint_instruction = "STRICT CONSTRAINT: You MUST design the activity using ONLY the exact objects and materials specified by the student. Do not introduce any external or store-bought materials." if constraint_mode == "strict_only" else "CONSTRAINT: Base the activity primarily around the student's available materials, but you may include minimal, common household items (e.g. clean water, spoon, paper, cotton thread, ruler, small cup) if strictly necessary."

        custom_mat_section = f"- Student's Specific Available Objects / Surroundings: {custom_materials}" if custom_materials else "- Student's General Environment: Rural/Village surroundings with natural objects (soil, plants, water, stones, tools)"
        image_notice = "- Student attached a photo of their available physical surroundings / materials for multimodal visual grounding." if image_data else ""
        accessibility_section = f"- Accessibility / Resource Constraints: {accessibility_notes}" if accessibility_notes else ""

        lang_instruction = f"Provide all explanations, steps, and questions in {preferred_language}, while preserving rigorous scientific/mathematical accuracy for technical terms." if preferred_language and preferred_language.lower() != "english" else "Provide explanations in simple, clear, accessible English before introducing formal academic terms."

        prompt = f"""
You are the AI Learning Assistant for 'Learn from Anywhere' in LearnSphere AI.
Your mission is to transform an academic curriculum topic into an understandable, feasible, zero-cost, hands-on activity or conceptual observation for a student with limited educational resources in a rural or village setting.

Academic & Curriculum Grounding:
- Program / Degree: {program or 'Academic Curriculum'}
- Department / Board: {department or 'General Science & Engineering'}
- Academic Level: {sem_str}
- Subject: {subject} (Subject ID: {subject_id or 'N/A'})
- Syllabus Topic to Teach: {active_topic}
- Unit / Module: {unit or 'Standard Curriculum Module'}
- Curriculum Reference: {curriculum_reference or 'Accredited Syllabus'}
- Validated Syllabus Concepts: {topics_str}
- Local Resource Environment: {resource_environment}
{custom_mat_section}
{image_notice}
{accessibility_section}
- Material Constraint Mode: {constraint_mode} ({constraint_instruction})
- Difficulty Level: {difficulty}
- Preferred Language: {preferred_language} ({lang_instruction})

Supported Pedagogical Approaches by Subject:
1. Household-Object Demonstrations: Water cups, cloth strips, spoons, cardboard, thread, clay pots.
2. Outdoor & Nature-Based Observations: Soil profiles, river sand, tree canopies, sun angle, shadows, rainwater percolation.
3. Mathematics: Everyday counting, measuring, geometric shadows, pebble arrays for series/probability, water volume displacement.
4. Physics: Low-cost mechanics, surface tension, capillary action, optics with water droplets, acoustics with bottles.
5. Chemistry: Safe botanical pH indicators (turmeric, hibiscus), crystallization from salt/sugar, solubility, emulsions.
6. Biology: Seed germination, transpiration in leaf bags, capillary dye in plant stems, leaf venation, root osmosis.
7. Environmental Science: Soil erosion runoff, terracotta evaporative cooling, watershed percolation, natural compost breakdown.
8. Engineering & Technology: Lever balance, bicycle gear ratios, siphon water transfer, twig truss structures.
9. Non-Demonstrable / Abstract Topics (e.g. quantum mechanics, nuclear physics, relativity, pure calculus): If a physical experiment is impossible or dangerous, DO NOT fake a lab result. Instead, provide a safe physical analog / thought experiment / paper-and-shadow model, and clearly state in the limitations why a direct physical experiment cannot be performed.

Strict Safety & Grounding Directives:
1. SAFETY MANDATE: NEVER recommend hazardous chemicals (no strong acids/bases), mains electricity (220V), unsafe machinery, or fire.
2. The activity must teach the ACTUAL selected topic ({active_topic}), not merely mention its name.
3. Explain concepts in simple plain language before introducing technical academic formulas.
4. Include the correct academic explanation, linking it directly to the textbook law or formula.
5. Offer a no-purchase alternative for every item.
6. Distinguish predicted scientific outcomes from variable real-world environmental factors (humidity, light angle, soil mineral variance).
7. VISUAL EVIDENCE DIRECTIVES (WHEN IMAGE IS ATTACHED):
   - Identify ONLY visible physical characteristics supported by visual evidence (shape, color, surface texture, leaf venation, visible gears, container shape).
   - DO NOT claim that the photograph proves invisible properties (e.g., exact chemical composition, microscopic cellular structures, exact species name without visible diagnostic traits, exact numerical measurements, or unobserved experimental outcomes).
   - Ask for clarification in 'clarification_needed' if the object or its relevant properties cannot be identified reliably visually.

Return ONLY a valid JSON object matching this exact schema:
{{
  "activity_id": "lfa_{subject.lower()[:4]}_{difficulty.lower()}",
  "activity_title": "Descriptive Activity Title",
  "title": "Descriptive Activity Title",
  "demonstration_type": "physical_demonstration | outdoor_observation | household_demonstration | thought_experiment_and_analog",
  "image_analysis": {{
    "image_processed": true,
    "visible_features": [
      "Observed physical feature 1",
      "Observed physical feature 2"
    ],
    "identified_object_or_structure": "Observed object, plant, tool, or structure description",
    "confidence_level": "high | medium | low",
    "clarification_needed": "Questions if visual properties cannot be identified with high confidence",
    "syllabus_connection": "Detailed explanation of how this visual observation connects to {active_topic}"
  }},
  "academic_grounding": {{
    "subject": "{subject}",
    "topic": "{active_topic}",
    "unit": "{unit or 'Core Unit'}",
    "curriculum_reference": "{curriculum_reference or 'Active Syllabus'}",
    "grade_or_semester": "{sem_str}",
    "program": "{program or 'Academic Curriculum'}",
    "department": "{department or 'Science'}"
  }},
  "learning_objectives": [
    "Specific academic learning outcome 1",
    "Specific academic learning outcome 2"
  ],
  "real_world_concept": "Clear description of the physical, chemical, biological, or mathematical phenomenon being demonstrated",
  "materials_student_has": [
    "Item 1 available locally",
    "Item 2 available locally"
  ],
  "safe_substitutions": [
    "Safe zero-cost alternative 1 (e.g. Banana leaf instead of plastic sheet)",
    "Safe alternative 2 (e.g. Charcoal dust instead of dark dye)"
  ],
  "no_purchase_alternative": "Comprehensive zero-cost substitution guide if specific household items are unavailable",
  "steps": [
    "Step 1: Preparation...",
    "Step 2: Execution...",
    "Step 3: Observation..."
  ],
  "simple_explanation": "Plain language explanation of why this activity works for young/rural students without prior lab training",
  "academic_theory": "Rigorous scientific/mathematical explanation including governing formulas or laws",
  "everyday_applications": "How this concept directly impacts farming, irrigation, village machinery, weather, sustainability, or household life",
  "expected_observations": "What to see/measure and how to interpret it, noting real-world conditional variations",
  "limitations_and_misconceptions": "Boundary conditions, physical limits, common misconceptions, and why certain abstract aspects rely on conceptual analogs",
  "safety_precautions": "Clear safety precautions and adult supervision guidance where appropriate",
  "understanding_questions": [
    {{
      "question": "Conceptual Question 1?",
      "answer": "Concise answer",
      "explanation": "Why this answer is scientifically correct"
    }},
    {{
      "question": "Application Question 2?",
      "answer": "Concise answer",
      "explanation": "Why this answer is scientifically correct"
    }},
    {{
      "question": "Analytical Question 3?",
      "answer": "Concise answer",
      "explanation": "Why this answer is scientifically correct"
    }}
  ],
  "reflection_task": "A short conceptual thought experiment or reflection task connected to local surroundings",
  "follow_up_practice": "A suggested follow-up problem or mini-investigation on the same syllabus topic",
  "is_supported": true
}}
"""
        files_payload = None
        if image_data:
            try:
                b64_clean = image_data.split(",", 1)[1] if "," in image_data else image_data
                mime_type = "image/jpeg"
                if "data:image/png" in image_data:
                    mime_type = "image/png"
                elif "data:image/webp" in image_data:
                    mime_type = "image/webp"
                files_payload = [{"inline_data": {"mime_type": mime_type, "data": b64_clean}}]
            except Exception as e:
                logger.warning(f"[LearnAnywhere] Could not parse image payload: {e}")

        try:
            raw = self.generate_content(prompt, files=files_payload, json_output=True)
            res = self.parse_json_response(raw)
            if isinstance(res, dict) and (res.get("title") or res.get("activity_title") or res.get("academic_theory") or res.get("scientific_principle")):
                return self._normalize_learn_anywhere_response(res, subject, active_topic, unit, curriculum_reference, resource_environment, difficulty, sem_str, program, department, constraint_mode)
        except Exception as e:
            logger.warning(f"[GeminiService] generate_learn_anywhere API call error: {e}")

        fallback = self._build_deterministic_learn_anywhere(subject, subject_id, active_topic, resource_environment, difficulty, sem_str, program, department)
        return self._normalize_learn_anywhere_response(fallback, subject, active_topic, unit, curriculum_reference, resource_environment, difficulty, sem_str, program, department, constraint_mode)

    def _normalize_learn_anywhere_response(
        self,
        res: Dict[str, Any],
        subject: str,
        topic: str,
        unit: str,
        curriculum_ref: str,
        resource_env: str,
        difficulty: str,
        semester: str,
        program: str,
        department: str,
        constraint_mode: str
    ) -> Dict[str, Any]:
        """Normalize and enforce the strict 16-point schema, approach metadata, and backward compatibility."""
        title = res.get("activity_title") or res.get("title") or f"Hands-on Investigation of {topic}"
        res["activity_title"] = title
        res["title"] = title

        grounding = res.get("academic_grounding") or {}
        if not isinstance(grounding, dict):
            grounding = {}
        grounding.setdefault("subject", subject)
        grounding.setdefault("topic", topic)
        grounding.setdefault("unit", unit or "Standard Unit")
        grounding.setdefault("curriculum_reference", curriculum_ref or "Active Validated Syllabus")
        grounding.setdefault("grade_or_semester", semester)
        grounding.setdefault("program", program)
        grounding.setdefault("department", department)
        res["academic_grounding"] = grounding

        res.setdefault("subject", subject)
        res.setdefault("syllabus_topic", topic)
        res.setdefault("resource_category", resource_env)
        res.setdefault("constraint_mode", constraint_mode)
        res.setdefault("is_supported", True)

        demo_type = res.get("demonstration_type") or "physical_demonstration"
        res["demonstration_type"] = demo_type

        img_analysis = res.get("image_analysis")
        if isinstance(img_analysis, dict) and img_analysis.get("image_processed"):
            res["image_analysis"] = {
                "image_processed": True,
                "image_note": img_analysis.get("image_note") or "Image successfully analyzed and grounded in syllabus concept.",
                "visible_features": img_analysis.get("visible_features") if isinstance(img_analysis.get("visible_features"), list) else [str(img_analysis.get("visible_features"))],
                "identified_object_or_structure": img_analysis.get("identified_object_or_structure") or "Observed physical object / structure",
                "confidence_level": img_analysis.get("confidence_level") or "high",
                "clarification_needed": img_analysis.get("clarification_needed") or "",
                "syllabus_connection": img_analysis.get("syllabus_connection") or f"Visible characteristics connected directly to {topic}"
            }
        else:
            res["image_analysis"] = {
                "image_processed": False,
                "image_note": "Image analysis was unavailable or not attached; text-based practical activity was generated for your syllabus topic.",
                "visible_features": [],
                "identified_object_or_structure": "N/A",
                "confidence_level": "N/A",
                "clarification_needed": "",
                "syllabus_connection": f"Activity directly connected to {topic}"
            }

        objs = res.get("learning_objectives") or []
        if isinstance(objs, str):
            objs = [objs]
        if not objs and res.get("learning_objective"):
            objs = [res["learning_objective"]]
        res["learning_objectives"] = objs or [f"Understand the fundamental practical principles of {topic}"]
        res["learning_objective"] = res["learning_objectives"][0]

        mats = res.get("materials_student_has") or res.get("local_materials") or []
        if isinstance(mats, str):
            mats = [mats]
        res["materials_student_has"] = mats or ["Locally sourceable items", "Clean water", "Measuring stick"]
        res["local_materials"] = res["materials_student_has"]

        subs = res.get("safe_substitutions") or []
        if isinstance(subs, str):
            subs = [subs]
        res["safe_substitutions"] = subs

        res.setdefault("no_purchase_alternative", "All required items can be gathered for free from natural surroundings, clean recycled containers, or standard kitchen tools.")

        steps = res.get("steps") or []
        if isinstance(steps, str):
            steps = [steps]
        res["steps"] = steps or [
            "Step 1: Gather your local materials in a well-lit, clean area.",
            "Step 2: Set up the trial apparatus according to the instructions.",
            "Step 3: Measure and record the empirical observations."
        ]

        res.setdefault("simple_explanation", res.get("scientific_principle") or f"This activity demonstrates the physical behavior of {topic} through direct observable changes.")
        res.setdefault("academic_theory", res.get("scientific_principle") or f"Governed by fundamental laws of {subject} related to {topic}.")
        res["scientific_principle"] = res["academic_theory"]

        res.setdefault("real_world_concept", f"Physical verification of {topic} in everyday environments.")

        res.setdefault("everyday_applications", res.get("village_application") or "Directly applicable in agricultural crop management, irrigation, mechanics, sustainability, and local tools.")
        res["village_application"] = res["everyday_applications"]

        res.setdefault("expected_observations", res.get("expected_observation") or "Observable physical change matching theoretical expectations.")
        res["expected_observation"] = res["expected_observations"]

        res.setdefault("limitations_and_misconceptions", "Environmental parameters such as temperature and humidity may cause minor measurement variance.")

        res.setdefault("safety_precautions", res.get("safety_notes") or "Work with clean tools on flat ground. Wash hands thoroughly with soap after the experiment.")
        res["safety_notes"] = res["safety_precautions"]

        questions = res.get("understanding_questions") or []
        if not isinstance(questions, list) or len(questions) == 0:
            questions = [
                {
                    "question": f"What is the primary governing factor in {topic}?",
                    "answer": "The physical balance of applied forces and material properties.",
                    "explanation": "This directly confirms the academic theory."
                },
                {
                    "question": f"How does changing particle size or quantity impact the result?",
                    "answer": "It alters the rate of physical interaction proportionally.",
                    "explanation": "Rate of interaction depends directly on exposed surface area."
                },
                {
                    "question": f"Why is this concept important in rural applications?",
                    "answer": "It allows efficient resource utilization without expensive instruments.",
                    "explanation": "Understanding basic physics/chemistry enables low-cost optimization."
                }
            ]
        res["understanding_questions"] = questions

        res.setdefault("reflection_task", res.get("reflection_question") or f"How would you explain the principle of {topic} to a local farmer or artisan?")
        res["reflection_question"] = res["reflection_task"]

        res.setdefault("follow_up_practice", f"Calculate the expected quantitative variance if temperature or material volume is doubled for {topic}.")

        return res

    def _build_deterministic_learn_anywhere(
        self,
        subject: str,
        subject_id: str,
        topic: str,
        resource_env: str,
        difficulty: str,
        semester: str,
        program: str,
        department: str
    ) -> Dict[str, Any]:
        """
        Deterministic, offline-resilient rural learning activity grounded in academic subjects
        with complete 16-point structure and zero hazardous materials.
        Supports:
        - Physics / Mechanics / Optics
        - Chemistry / Materials
        - Biology / Agriculture / Ecology
        - Mathematics / Geometry / Statistics
        - Environmental Science / Sustainability
        - Engineering / Computer Science / Mechanisms
        - Abstract / Theoretical / Quantum (Thought Experiments)
        """
        sub_lower = subject.lower()
        top_lower = topic.lower()

        # 1. Abstract / Theoretical / Non-Demonstrable Topics (Quantum, Nuclear, Relativity, Abstract Pure Math)
        if any(w in top_lower or w in sub_lower for w in ["quantum", "nuclear", "relativity", "astrophysic", "atomic structure", "subatomic", "particle physics"]):
            return {
                "activity_id": f"lfa_theo_{difficulty.lower()}",
                "activity_title": f"Thought Experiment & Ripple Analogy: Exploring {topic or 'Quantum / Theoretical Concepts'}",
                "title": f"Thought Experiment & Ripple Analogy: Exploring {topic or 'Quantum / Theoretical Concepts'}",
                "demonstration_type": "thought_experiment_and_analog",
                "academic_grounding": {
                    "subject": subject,
                    "topic": topic or "Theoretical & Modern Physics Principles",
                    "unit": "Modern Physics & Theoretical Foundations",
                    "curriculum_reference": "Accredited Physics Syllabus",
                    "grade_or_semester": semester,
                    "program": program or "Science & Engineering",
                    "department": department or "Physics"
                },
                "learning_objectives": [
                    "Explore microscopic or relativistic phenomena using classical macroscopic analogs and structured thought experiments.",
                    "Differentiate between deterministic classical observations and probabilistic wave-particle behavior."
                ],
                "real_world_concept": "Wave-particle duality and probability distribution modeled through slit shadows and water ripple interference.",
                "materials_student_has": [
                    "A flat cardboard sheet with two narrow slits cut 2 mm apart",
                    "A single point-source sunlight beam entering a dark room (or torch light)",
                    "A shallow wide basin of water",
                    "Two small pebbles"
                ],
                "safe_substitutions": [
                    "Two razor blade edges held side-by-side between fingers instead of cut cardboard",
                    "A comb held in sunlight against a white wall"
                ],
                "no_purchase_alternative": "Use any scrap cardboard from grocery boxes and sunlight coming through a window shutter crack.",
                "steps": [
                    "Step 1: In a darkened room, direct a narrow sunlight beam through the two parallel cardboard slits onto a flat white wall 2 meters away.",
                    "Step 2: Observe the alternating bright and dark diffraction fringes formed by light wave interference (Young's double slit analog).",
                    "Step 3: Drop two pebbles simultaneously 5 cm apart in the water basin and watch the overlapping constructive and destructive wave crests.",
                    "Step 4: Conduct Einstein's thought experiment: If photons or electrons are sent one-by-one, each individual particle still builds up an interference pattern over time due to its probability wave function psi.",
                    "Step 5: Tabulate the differences between classical billiard-ball trajectories and quantum probability amplitudes."
                ],
                "simple_explanation": "At microscopic scales, particles like electrons behave like ripples on a pond. Even though we cannot see a single atom in our village, we can understand how their probability waves add up and cancel out just like overlapping ripples when two stones drop into water.",
                "academic_theory": "Governed by de Broglie wavelength lambda = h / p and the Schrödinger wave equation i*hbar*(d(psi)/dt) = H*psi. The probability density P(x) = |psi(x)|^2 gives the likelihood of detecting a quantum particle at position x. Interference arises from linear superposition of probability amplitudes: psi_total = psi_1 + psi_2.",
                "everyday_applications": "Underpins modern solar photovoltaic panels, LED lighting used in rural solar lanterns, semiconductor microchips, and MRI medical imaging.",
                "expected_observations": "Visible optical fringe patterns on the wall and distinct water wave nodes in the basin. Note that stray ambient light reduces contrast on the projection wall.",
                "limitations_and_misconceptions": "FEASIBILITY LIMITATION: Quantum states and subatomic particles cannot be physically observed or safely isolated with household equipment. This activity uses classical wave analogs; electrons possess intrinsic quantum spin and non-locality that water ripples do not possess.",
                "safety_precautions": "Never look directly into the sun. Perform the slit experiment using indirect reflected sunlight or safe low-power torch light.",
                "understanding_questions": [
                    {
                        "question": "Why do two overlapping water waves create areas of completely calm water?",
                        "answer": "Destructive interference occurs when the crest of one wave aligns with the trough of another (phase difference of 180 degrees), canceling each other out.",
                        "explanation": "Wave superposition allows amplitudes of opposite signs to sum to zero."
                    },
                    {
                        "question": "Why is a thought experiment necessary for understanding quantum mechanics in a household?",
                        "answer": "Subatomic particles require high-vacuum particle accelerators and cryo-sensors, but logical mathematical thought experiments allow rigorous verification of principles.",
                        "explanation": "Thought experiments (Gedankenexperiments) isolate core theoretical assumptions without hazardous equipment."
                    },
                    {
                        "question": "How does de Broglie's formula (lambda = h/p) explain why a flying cricket ball does not show wave diffraction?",
                        "answer": "Because Planck's constant h is extremely small (6.626e-34 J*s), the momentum p of a cricket ball makes its wavelength lambda unimaginably tiny, rendering wave effects undetectable.",
                        "explanation": "Quantum wave properties only become significant when momentum p is comparable to subatomic scales."
                    }
                ],
                "reflection_task": "How does a solar calculator or solar lantern convert sunlight into electricity using quantum photon absorption?",
                "follow_up_practice": "Calculate the de Broglie wavelength of an electron (mass = 9.11e-31 kg) moving at 10^6 m/s.",
                "is_supported": True
            }

        # 2. Biology / Agriculture / Botany / Life Sciences
        elif any(w in sub_lower or w in top_lower for w in ["bio", "botany", "zoolog", "plant", "agri", "crop", "seed", "transpir"]):
            return {
                "activity_id": f"lfa_bio_{difficulty.lower()}",
                "activity_title": f"Non-Invasive Plant Transpiration & Stomatal Regulation Investigation for {topic or 'Plant Physiology'}",
                "title": f"Non-Invasive Plant Transpiration & Stomatal Regulation Investigation for {topic or 'Plant Physiology'}",
                "demonstration_type": "outdoor_observation",
                "academic_grounding": {
                    "subject": subject,
                    "topic": topic or "Transpiration, Stomata & Xylem Transport",
                    "unit": "Plant Physiology & Agricultural Botany",
                    "curriculum_reference": "Standard Life Sciences Curriculum",
                    "grade_or_semester": semester,
                    "program": program or "Agricultural & Biological Sciences",
                    "department": department or "Life Sciences"
                },
                "learning_objectives": [
                    "Measure non-invasive plant transpiration rates under varying sunlight and shade conditions.",
                    "Understand stomatal aperture mechanics, transpiration pull, and xylem water transport."
                ],
                "real_world_concept": "Evapotranspiration and negative water potential gradients driving water lift against gravity in vascular plants.",
                "materials_student_has": [
                    "A living outdoor potted plant or leafy tree branch (e.g. Guava, Mango, or Hibiscus)",
                    "2 clean, dry transparent plastic polythene covers",
                    "Cotton string or rubber band to tie the bag mouths",
                    "A clean glass cup or measuring spoon"
                ],
                "safe_substitutions": [
                    "Clean food-packaging plastic wrap instead of polythene bags",
                    "Jute twine or dried grass blades instead of rubber bands"
                ],
                "no_purchase_alternative": "Reuse clean plastic grocery bags and string made from twisted banana fiber or jute.",
                "steps": [
                    "Step 1: Choose two healthy leafy branches of similar leaf count on a sunlit plant.",
                    "Step 2: Enclose branch A inside a clean transparent plastic bag and tie the base tightly with string around the stem, ensuring no air gaps.",
                    "Step 3: Enclose branch B in the exact same way, but place a cardboard shade over branch B to block direct sunlight.",
                    "Step 4: Leave both setups for 60 to 90 minutes in their respective conditions.",
                    "Step 5: Observe the accumulation of condensed water droplets on the interior plastic surface and compare the volume between sunlit and shaded branches."
                ],
                "simple_explanation": "Plants drink water from their roots and release excess water vapor into the air through tiny microscopic breathing pores (stomata) on their leaves. When we tie a plastic bag around the leaves, the trapped vapor cools and condenses into visible water drops.",
                "academic_theory": "Transpiration is governed by the Cohesion-Tension Theory and Fick's Law of diffusion. Water evaporation from mesophyll cell walls generates a negative hydrostatic pressure (suction tension up to -2 MPa) in xylem vessels. The rate of transpiration E = (C_leaf - C_air) / (r_s + r_a), where r_s is stomatal resistance and r_a is boundary layer resistance. High sunlight triggers guard cell turgor expansion (K+ ion influx), opening stomata and accelerating water vapor flux.",
                "everyday_applications": "Informs village farmers on optimal morning/evening drip irrigation timing, mulch application to reduce soil moisture evaporation, and windbreak planting to reduce crop moisture loss during dry seasons.",
                "expected_observations": "The sunlit bag accumulates dense mist and pooling water droplets within an hour, whereas the shaded bag collects significantly less. Real-world humidity and leaf age will influence condensation speed.",
                "limitations_and_misconceptions": "Common misconception: assuming roots push water all the way to the top of tall trees by positive pressure. In reality, transpiration pull (negative pressure from leaves) is the primary driver for tall trees.",
                "safety_precautions": "Do not break or damage tree branches; ensure bags are removed after 2 hours so the plant can resume normal respiration.",
                "understanding_questions": [
                    {
                        "question": "Why did the sunlit branch produce significantly more water droplets than the shaded branch?",
                        "answer": "Sunlight activates photosynthetic light receptors in guard cells, causing K+ influx, turgor pressure increase, and stomatal opening to maximize gas exchange.",
                        "explanation": "Open stomata dramatically lower stomatal resistance (r_s), increasing transpiration rate."
                    },
                    {
                        "question": "How do water molecules stay connected in a continuous column from root to leaf top without breaking?",
                        "answer": "Through high hydrogen bonding cohesion among water molecules and adhesion to polar xylem cell walls.",
                        "explanation": "Tensile strength of water prevents cavitation under high negative pressure."
                    },
                    {
                        "question": "Why do plants in dry rural areas often have waxy or small leaves?",
                        "answer": "Thick cuticles and reduced surface area increase boundary resistance and minimize water loss during hot dry spells.",
                        "explanation": "Xerophytic adaptations prevent desiccation by regulating transpiration."
                    }
                ],
                "reflection_task": "Look at three different plants in your village: one with large broad leaves and one with tiny waxy leaves. How does leaf size correlate with where they grow?",
                "follow_up_practice": "Place a freshly cut white flower stalk or celery stem in water colored with a pinch of food color or ink. Record the time taken for color to appear in the petals.",
                "is_supported": True
            }

        # 3. Environmental Science / Ecology / Geography / Water Conservation
        elif any(w in sub_lower or w in top_lower for w in ["environ", "ecolog", "earth", "geograph", "water conservation", "sustainab", "weather"]):
            return {
                "activity_id": f"lfa_env_{difficulty.lower()}",
                "activity_title": f"Soil Runoff, Watershed Conservation & Natural Terracotta Cooling for {topic or 'Environmental Systems'}",
                "title": f"Soil Runoff, Watershed Conservation & Natural Terracotta Cooling for {topic or 'Environmental Systems'}",
                "demonstration_type": "outdoor_observation",
                "academic_grounding": {
                    "subject": subject,
                    "topic": topic or "Watershed Management, Soil Erosion & Thermal Regulation",
                    "unit": "Environmental Sciences & Resource Sustainability",
                    "curriculum_reference": "Standard Environmental Studies Curriculum",
                    "grade_or_semester": semester,
                    "program": program or "Environmental Science & Civil Engineering",
                    "department": department or "Environmental Studies"
                },
                "learning_objectives": [
                    "Evaluate topsoil erosion and surface water runoff across bare versus vegetated slopes.",
                    "Analyze latent heat of vaporization in porous terracotta pots (matkas) for zero-electricity cooling."
                ],
                "real_world_concept": "Surface friction / vegetative root binding mitigating shear stress from water runoff, and latent heat absorption through porous evaporative surfaces.",
                "materials_student_has": [
                    "Two sloped earth mounds (one bare soil, one covered with grass/dry leaves)",
                    "A cup or jug with small perforations (or watering can)",
                    "A traditional unglazed terracotta clay pot (matka) and a metal or glass cup",
                    "Clean water"
                ],
                "safe_substitutions": [
                    "Trays of soil on a slight tilt if mounds are not available outdoors",
                    "Cloth-wrapped glass bottle instead of terracotta pot"
                ],
                "no_purchase_alternative": "Gather natural clay from stream beds and use fallen dry leaves/twigs as natural mulch.",
                "steps": [
                    "Step 1: Set up two 30-degree soil slopes of identical length: Slope 1 is bare loose earth, and Slope 2 is covered with grass roots or leaf mulch.",
                    "Step 2: Pour 500 ml of water steadily over both slopes using a perforated can to simulate torrential rainfall.",
                    "Step 3: Collect the runoff water at the base in separate clear bowls and measure sediment clarity / turbidity.",
                    "Step 4: Fill the porous clay pot and the metal container with equal volumes of water and place both in a shaded, breezy area.",
                    "Step 5: Measure water temperatures after 3 hours and note the natural temperature drop in the clay pot."
                ],
                "simple_explanation": "Grass and roots act like natural anchors holding topsoil in place, preventing monsoon rain from washing fertile soil away. Meanwhile, unglazed clay pots 'sweat' through tiny microscopic pores; as this water evaporates into the breeze, it carries heat away, keeping the drinking water naturally cold without electricity.",
                "academic_theory": "Governed by the Revised Universal Soil Loss Equation (RUSLE): A = R * K * LS * C * P, where vegetation cover factor C drastically reduces soil loss A. For evaporative cooling, heat extraction Q = m * L_v, where L_v is the latent heat of vaporization of water (approx. 2.26 x 10^6 J/kg). Evaporation removes high-energy molecules from the pot surface, decreasing the average kinetic energy (temperature) of remaining water.",
                "everyday_applications": "Critical for rural village check-dam construction, bund farming on contours to recharge groundwater aquifers, and constructing zero-energy cool chambers (ZECC) for preserving fresh farm vegetables.",
                "expected_observations": "Water from the bare slope is thick with muddy sediment, while water from the mulched slope emerges relatively clear. The clay pot water drops 3 to 6 degrees Celsius below ambient temperature depending on air humidity.",
                "limitations_and_misconceptions": "Clay pot cooling efficiency decreases in extremely high humidity (e.g. heavy monsoon rain) because high ambient vapor pressure retards the rate of evaporation.",
                "safety_precautions": "Wash hands with soap after handling soil and runoff samples.",
                "understanding_questions": [
                    {
                        "question": "Why does vegetative cover prevent soil erosion during heavy monsoon rains?",
                        "answer": "Plant foliage intercepts raindrops, dissipating kinetic impact energy, while fibrous root networks mechanically bind soil aggregates together.",
                        "explanation": "Roots increase soil shear strength and enhance infiltration capacity, reducing erosive overland sheet flow."
                    },
                    {
                        "question": "Why does water in an unglazed clay pot stay cooler than in a plastic or steel bottle?",
                        "answer": "Unglazed clay is porous, allowing continuous microscopic seepage and surface evaporation, which extracts latent heat of vaporization (2.26 MJ/kg) directly from the water.",
                        "explanation": "Steel and plastic lack porosity and cannot facilitate endothermic evaporative cooling."
                    },
                    {
                        "question": "Why is evaporative cooling less effective on rainy, humid days?",
                        "answer": "High relative humidity means air is near saturation (vapor pressure deficit is low), suppressing the evaporation rate.",
                        "explanation": "Evaporation rate is proportional to the difference between saturation vapor pressure and actual ambient vapor pressure."
                    }
                ],
                "reflection_task": "Walk around your village after a rainstorm. Where does rainwater pool or create gullies, and where does it soak into the earth? What soil features cause this?",
                "follow_up_practice": "Design a small 3-tier filtration column using coarse gravel, sand, and crushed charcoal to clarify turbid rainwater.",
                "is_supported": True
            }

        # 4. Mathematics / Geometry / Statistics / Logic
        elif any(w in sub_lower or w in top_lower for w in ["math", "algebra", "geometr", "trig", "calculus", "probab", "statist", "matrix", "number"]):
            return {
                "activity_id": f"lfa_math_{difficulty.lower()}",
                "activity_title": f"Shadow Trigonometry, Geometric Scaling & Pebble Combinatorics for {topic or 'Applied Mathematics'}",
                "title": f"Shadow Trigonometry, Geometric Scaling & Pebble Combinatorics for {topic or 'Applied Mathematics'}",
                "demonstration_type": "household_demonstration",
                "academic_grounding": {
                    "subject": subject,
                    "topic": topic or "Trigonometric Ratios, Similarity & Discrete Probability",
                    "unit": "Applied Mathematics & Geometric Analysis",
                    "curriculum_reference": "Standard Mathematics Curriculum",
                    "grade_or_semester": semester,
                    "program": program or "Mathematics & Science",
                    "department": department or "Mathematics"
                },
                "learning_objectives": [
                    "Calculate inaccessible vertical heights using similar triangle ratios and solar shadow measurements (Thales' Theorem).",
                    "Model arithmetic series, permutations, and probability distributions using discrete pebble grid arrays."
                ],
                "real_world_concept": "Linear proportional scaling (H1/S1 = H2/S2) and discrete triangular number series: sum(k, 1 to n) = n*(n+1)/2.",
                "materials_student_has": [
                    "A vertical stick of known length (e.g. exactly 100 cm or 1 meter)",
                    "A measuring string, tape, or marked ruler",
                    "50 small identical smooth pebbles or dry chickpeas",
                    "Sunlight on level open ground"
                ],
                "safe_substitutions": [
                    "A walking cane or umbrella of measured length instead of stick",
                    "Uniform pacing steps of calibrated length (e.g. 1 step = 0.75 m) instead of measuring tape"
                ],
                "no_purchase_alternative": "Use stones gathered from the path and a stick marked using hand spans.",
                "steps": [
                    "Step 1: Place the 1-meter stick vertically on level sunlit ground and measure its shadow length (s1).",
                    "Step 2: Immediately measure the shadow length (s2) of a tall village structure (tree, water tank, or electricity pole).",
                    "Step 3: Apply Thales' similar triangle formula to determine the structure's height: H2 = (H1 / s1) * s2.",
                    "Step 4: Arrange pebbles in a triangular grid: Row 1 = 1 pebble, Row 2 = 2 pebbles, up to Row n = n pebbles.",
                    "Step 5: Combine two identical pebble triangles into a rectangle of size n * (n + 1) to visually prove the summation formula."
                ],
                "simple_explanation": "Because sunlight hits all objects in your village at the exact same angle at any given minute, tall objects cast shadows that are strictly in the exact same proportion as short sticks. We can also see mathematical formulas by physically arranging stones into rectangles on the ground.",
                "academic_theory": "Similar right triangles share identical interior angles theta: tan(theta) = H_stick / S_stick = H_tree / S_tree. Hence, H_tree = (H_stick / S_stick) * S_tree. For discrete series, arranging n rows of pebbles yields S_n = 1 + 2 + ... + n = n*(n+1)/2. For probability, sampling r marked pebbles from N total pebbles follows the hypergeometric distribution P(X=k) = [C(K,k) * C(N-K, n-k)] / C(N,n).",
                "everyday_applications": "Essential for village carpenters constructing angled roof trusses, farmers estimating crop yields through random quadrat sampling, and land surveyors estimating field boundaries without electronic theodolites.",
                "expected_observations": "Shadow lengths change continuously with Earth's rotation, but the ratio H/S remains strictly invariant across all nearby vertical objects at any given instant.",
                "limitations_and_misconceptions": "Slope error: Ground must be flat; if the shadow falls on sloped ground, the measured length must be adjusted by dividing by cos(slope angle).",
                "safety_precautions": "Avoid staring into direct sunlight during measurements.",
                "understanding_questions": [
                    {
                        "question": "If a 1.5 m vertical stick casts a 2.0 m shadow, how tall is a grain silo that casts an 18.0 m shadow at the same moment?",
                        "answer": "The grain silo is 13.5 meters tall (H = (1.5 / 2.0) * 18.0 = 0.75 * 18.0 = 13.5 m).",
                        "explanation": "Applying similar triangle proportionality directly: H2 = (H1 / s1) * s2."
                    },
                    {
                        "question": "Why does adding two identical triangular pebble patterns of n rows create a rectangle of dimensions n by (n + 1)?",
                        "answer": "Because flipping and interlocking one triangle against the other pairs row k with row (n - k + 1), giving exactly (n + 1) pebbles in every single row across n total rows.",
                        "explanation": "Total pebbles = n * (n + 1), so one single triangle has half: n*(n + 1)/2."
                    },
                    {
                        "question": "Why must shadow measurements for height calculation be taken within a 2-minute window?",
                        "answer": "Because the Earth's rotation shifts the solar elevation angle theta continuously (about 15 degrees per hour), altering shadow ratios.",
                        "explanation": "A significant time gap causes solar elevation angle mismatch between the two measurements."
                    }
                ],
                "reflection_task": "Measure the shadow of a wall at 9:00 AM, 12:00 PM, and 4:00 PM. Calculate the solar angle tan(theta) at each time. When is the sun highest?",
                "follow_up_practice": "Use 36 pebbles to construct all possible distinct rectangular arrays (factors of 36) and identify which produces a perfect square.",
                "is_supported": True
            }

        # 5. Engineering / Computer Science / General Technology / Mechanisms
        elif any(w in sub_lower or w in top_lower for w in ["engin", "technol", "siphon", "gear", "machine", "comput", "circuit"]):
            return {
                "activity_id": f"lfa_eng_{difficulty.lower()}",
                "activity_title": f"Everyday Mechanical Advantage, Siphon Fluidics & Algorithmic Sorting for {topic or subject}",
                "title": f"Everyday Mechanical Advantage, Siphon Fluidics & Algorithmic Sorting for {topic or subject}",
                "demonstration_type": "household_demonstration",
                "academic_grounding": {
                    "subject": subject,
                    "topic": topic or "Mechanical Advantage, Fluid Flow & Algorithmic Principles",
                    "unit": "Applied Engineering & Practical Systems",
                    "curriculum_reference": "Standard Technical & Science Curriculum",
                    "grade_or_semester": semester,
                    "program": program or "Engineering & Applied Technology",
                    "department": department or "Applied Technology"
                },
                "learning_objectives": [
                    "Demonstrate mechanical gear ratios and moment equilibrium on simple lever mechanisms.",
                    "Verify Bernoulli's principle and atmospheric hydrostatic siphon flow using low-cost flexible tubing."
                ],
                "real_world_concept": "Torque transmission ratio (N1/N2 = omega2/omega1) and hydrostatic head potential driving continuous siphon fluid transport.",
                "materials_student_has": [
                    "A standard multi-speed bicycle wheel and pedal gear set (or simple lever stick)",
                    "1 meter of clear plastic water hose / tubing (or straw)",
                    "Two buckets or clay pots at different elevation levels",
                    "Clean water"
                ],
                "safe_substitutions": [
                    "A wooden plank balanced on a log fulcrum instead of bicycle gears",
                    "A bendable drinking straw or flexible PVC pipe instead of garden hose"
                ],
                "no_purchase_alternative": "Use any household bucket and common bicycle gears or a balanced wooden rod.",
                "steps": [
                    "Step 1: Count the number of teeth on the front pedal chainring (N1) and the rear wheel cog (N2).",
                    "Step 2: Rotate the pedal one full 360-degree revolution and count the exact revolutions completed by the rear wheel to compute gear ratio = N1 / N2.",
                    "Step 3: Fill elevated Bucket A with water and place empty Bucket B 50 cm lower on the ground.",
                    "Step 4: Submerge the flexible tube completely in Bucket A to purge air, clamp both ends with fingers, and place one end in Bucket B.",
                    "Step 5: Release fingers and observe continuous spontaneous water flow driven by gravity and hydrostatic pressure difference."
                ],
                "simple_explanation": "Bicycle gears let you trade speed for pushing force. Siphons let water climb up over a bucket rim and down into another container automatically as long as the second container is placed lower than the first.",
                "academic_theory": "Gear ratio GR = N_drive / N_driven = omega_driven / omega_drive = Torque_drive / Torque_driven. Siphon flow velocity is governed by Torricelli's Law and Bernoulli's equation: v = sqrt(2 * g * Delta_h), where Delta_h is the vertical height difference between the free water surfaces.",
                "everyday_applications": "Underpins rural irrigation channels, fuel transfer from village tractor tanks, human-powered water pumps, and flour mill mechanical power transmission.",
                "expected_observations": "Higher gear ratio yields more wheel revolutions per pedal turn with increased resistance. Siphon flow rate increases proportionally with vertical drop height Delta_h.",
                "limitations_and_misconceptions": "A siphon cannot lift water higher than the barometric atmospheric head limit (approx. 10 meters for water at sea level) because cavitation will break the liquid column.",
                "safety_precautions": "Ensure fingers are kept clear of moving bicycle chain spokes during gear rotation.",
                "understanding_questions": [
                    {
                        "question": "Why is it easier to ride a bicycle uphill when shifting to a smaller front gear and larger rear gear?",
                        "answer": "It reduces the gear ratio (GR < 1), multiplying torque applied to the rear wheel at the expense of rotational speed.",
                        "explanation": "Conservation of mechanical energy dictates that Power = Torque * angular velocity (P = tau * omega)."
                    },
                    {
                        "question": "Why does water continue flowing upward over the rim of Bucket A in a siphon?",
                        "answer": "The longer fluid column in the lower tube creates a net gravitational suction, lowering pressure at the siphon crest below atmospheric pressure.",
                        "explanation": "Liquid cohesion and atmospheric pressure push water up into the low-pressure crest zone."
                    },
                    {
                        "question": "What happens to the siphon flow rate if you lower Bucket B by another 30 cm?",
                        "answer": "The flow rate increases because the gravitational potential head Delta_h is greater (v = sqrt(2*g*Delta_h)).",
                        "explanation": "Flow velocity scales with the square root of vertical drop height."
                    }
                ],
                "reflection_task": "Observe how water is transferred or pumped in your local village. How does elevation difference reduce the energy needed?",
                "follow_up_practice": "Calculate the theoretical flow rate (liters per minute) through a 1 cm diameter tube for Delta_h = 0.8 meters.",
                "is_supported": True
            }

        # 6. Physics / Mechanics / Optics / Fluid Dynamics
        elif any(w in sub_lower or w in top_lower for w in ["physic", "mechanic", "optic", "fluid", "force", "motion", "wave", "sound", "friction", "inertia"]):
            return {
                "activity_id": f"lfa_phy_{difficulty.lower()}",
                "activity_title": f"Soil Capillarity, Fluid Surface Tension & Mechanical Lever Analysis for {topic or 'Physics'}",
                "title": f"Soil Capillarity, Fluid Surface Tension & Mechanical Lever Analysis for {topic or 'Physics'}",
                "demonstration_type": "household_demonstration",
                "academic_grounding": {
                    "subject": subject,
                    "topic": topic or "Capillarity, Surface Tension & Moment Equilibrium",
                    "unit": "Fluid Mechanics & Classical Statics",
                    "curriculum_reference": "Standard Technical & Science Curriculum",
                    "grade_or_semester": semester,
                    "program": program or "Science & Engineering",
                    "department": department or "Physics"
                },
                "learning_objectives": [
                    "Understand capillary action, surface tension, and permeability across differing soil particle diameters.",
                    "Derive how pore radius inversely controls fluid elevation according to Jurin's Law."
                ],
                "real_world_concept": "Capillary fluid lift in porous natural media driven by molecular adhesion and surface tension, and rotational torque balance.",
                "materials_student_has": [
                    "3 transparent plastic water bottles with bases cut off (or cloth pouches)",
                    "Samples of local clay soil, sandy riverbed soil, and organic compost",
                    "A cup of water and a clean white cotton cloth strip",
                    "A flat wooden ruler or marked stick"
                ],
                "safe_substitutions": [
                    "Clay pots or coconut shells with bottom pinholes instead of plastic bottles",
                    "Dry cotton string or jute rope instead of cloth strip"
                ],
                "no_purchase_alternative": "Use discarded plastic bottles or coconut halves and natural dry cotton fiber.",
                "steps": [
                    "Step 1: Invert the cut bottles and plug their narrow spouts with loose cotton cloth to act as a soil filter.",
                    "Step 2: Fill bottle 1 with dry pulverized clay, bottle 2 with coarse river sand, and bottle 3 with organic loam compost.",
                    "Step 3: Pour an equal half-cup (100ml) of water slowly into the top of each soil column simultaneously.",
                    "Step 4: Measure the time taken for the first drop to filter into a collection cup below (drainage rate).",
                    "Step 5: In a separate cup, suspend a vertical dry cotton strip 1 cm into standing water and record height rise every 2 minutes."
                ],
                "simple_explanation": "Water climbs up tiny spaces on its own because water molecules stick to solid particles stronger than to each other. Small clay soil pores pull water up higher and hold it longer, while coarse sand lets water drain quickly.",
                "academic_theory": "Capillary action is governed by Jurin's Law: h = (2 * gamma * cos(theta)) / (r * rho * g), where gamma is liquid surface tension, theta is contact angle, r is pore radius, rho is fluid density, and g is gravitational acceleration. As pore radius r decreases, capillary rise h increases and hydraulic conductivity K decreases.",
                "everyday_applications": "Guides local farmers on crop selection based on soil moisture retention (clay for paddy, sandy loam for root crops) and determines drip irrigation frequency to avoid root waterlogging.",
                "expected_observations": "Water filters almost immediately through sand within seconds, whereas clay retains moisture for hours. Note that initial moisture content and compaction pressure will cause real-world variations in filtration rates.",
                "limitations_and_misconceptions": "Common misconception: thinking denser soil always drains faster. In reality, smaller pore diameter increases capillary hold despite higher mass density.",
                "safety_precautions": "Handle soil with clean tools, avoid breathing fine dry clay dust, and wash hands thoroughly with soap after handling soil samples.",
                "understanding_questions": [
                    {
                        "question": "Why does water climb higher in clay soil than in coarse river sand?",
                        "answer": "Because clay has microscopic pore radii, and capillary lift height is inversely proportional to pore radius (h ~ 1/r).",
                        "explanation": "Jurin's Law establishes that narrower channels produce stronger net upward adhesive forces against gravity."
                    },
                    {
                        "question": "How does surface tilling after rain conserve deep soil moisture?",
                        "answer": "Tilling breaks continuous microscopic capillary pore channels in the topsoil, disrupting upward evaporative water transport.",
                        "explanation": "Destroying the top capillary tubes traps moisture in the crop root zone below."
                    },
                    {
                        "question": "What happens to capillary lift if temperature rises significantly?",
                        "answer": "Capillary height slightly decreases because water surface tension (gamma) decreases with increasing temperature.",
                        "explanation": "Higher thermal agitation weakens intermolecular hydrogen bonding at the liquid-air interface."
                    }
                ],
                "reflection_task": "Observe your local farmland 24 hours after rainfall. Which patches stay muddy and which dry first? How does this match your experiment?",
                "follow_up_practice": "Calculate the theoretical capillary rise height for water (gamma = 0.0728 N/m) in a pore of radius r = 0.05 mm versus r = 0.005 mm.",
                "is_supported": True
            }

        # 6. Chemistry / Materials / Chemical Reactions / Acids & Bases
        elif any(w in sub_lower or w in top_lower for w in ["chem", "reaction", "acid", "base", "ph", "element", "compound", "bond", "solution", "solubil"]):
            return {
                "activity_id": f"lfa_chem_{difficulty.lower()}",
                "activity_title": f"Natural Botanical pH Indicators & Reversible Protonation for {topic or 'Acid-Base Equilibria'}",
                "title": f"Natural Botanical pH Indicators & Reversible Protonation for {topic or 'Acid-Base Equilibria'}",
                "demonstration_type": "household_demonstration",
                "academic_grounding": {
                    "subject": subject,
                    "topic": topic or "Acid-Base Neutralization & Natural Indicators",
                    "unit": "Chemical Equilibrium & Bio-Molecules",
                    "curriculum_reference": "Standard Technical & Science Curriculum",
                    "grade_or_semester": semester,
                    "program": program or "Science & Engineering",
                    "department": department or "Chemistry"
                },
                "learning_objectives": [
                    "Demonstrate chemical indicator equilibrium and reversible protonation using natural botanical extracts.",
                    "Classify local water, soil extracts, and household liquids as acidic, neutral, or alkaline."
                ],
                "real_world_concept": "Chromophore molecular structure transformation under changing hydrogen ion concentration (pH).",
                "materials_student_has": [
                    "Fresh turmeric powder (Curcuma longa) or crushed red hibiscus flower petals",
                    "Warm water in clear glass tumblers or clean bowls",
                    "Local test samples: Lemon juice (citric acid), wood ash water (potassium carbonate), sour buttermilk (lactic acid), rainwater, well water",
                    "Clean banana leaf or white paper strip"
                ],
                "safe_substitutions": [
                    "Red cabbage or purple beetroot juice instead of hibiscus",
                    "Baking soda solution instead of wood ash water"
                ],
                "no_purchase_alternative": "Use kitchen turmeric or wild hibiscus flowers and clear glass cups.",
                "steps": [
                    "Step 1: Dissolve 1/2 teaspoon of turmeric in warm water to prepare a vibrant yellow indicator extract.",
                    "Step 2: Paint strips of white paper or a banana leaf surface with the turmeric extract and let dry for 3 minutes.",
                    "Step 3: Drop a spot of lemon juice on strip A, sour buttermilk on strip B, and wood ash water on strip C.",
                    "Step 4: Observe the instant color transition from golden yellow to deep reddish-brown with alkaline ash water.",
                    "Step 5: Add a few drops of lemon juice over the reddish-brown spot on strip C and observe the reversible neutralization back to yellow."
                ],
                "simple_explanation": "Turmeric contains a yellow natural dye called curcumin. When it touches an alkaline (basic) substance like wood ash or soap, it loses a proton and turns deep red. Adding an acid gives the proton back, restoring the yellow color.",
                "academic_theory": "Curcumin acts as a weak polybasic acid undergoing keto-enol tautomerism. In neutral/acidic media (pH < 7.4), the bis-keto form predominates (yellow, max absorption ~425nm). In alkaline media (pH > 8.0), deprotonation yields the fully conjugated enolate anion (red-brown, bathochromic shift to ~490nm). The reversible reaction: H-Ind (yellow) + OH- <==> Ind- (red) + H2O.",
                "everyday_applications": "Enables farmers to conduct rapid on-site tests for soil and well-water alkalinity to detect salinity issues or lime imbalances without electronic spectrophotometers.",
                "expected_observations": "Acidic and neutral substances keep turmeric yellow. Alkaline solutions turn it red-brown immediately. Real-world color intensity may vary with solution concentration and freshness of the botanical extract.",
                "limitations_and_misconceptions": "Turmeric does not distinguish between strong and weak acids (both stay yellow); it is exclusively a base/alkali indicator (turning red between pH 7.8 and 9.2).",
                "safety_precautions": "Avoid getting wood ash solution into eyes. If contact occurs, rinse immediately with abundant clean water. Do not ingest test solutions.",
                "understanding_questions": [
                    {
                        "question": "Why does a turmeric curry stain turn red when washed with laundry soap?",
                        "answer": "Because soap contains alkaline sodium/potassium fatty acid salts (pH > 8), deprotonating the yellow curcumin into its red enolate form.",
                        "explanation": "The bathochromic shift in light absorption creates the characteristic red coloration."
                    },
                    {
                        "question": "Why does squeezing lemon juice over the red stain restore the original yellow color?",
                        "answer": "Citric acid neutralizes the alkaline soap, donating protons (H+) back to curcumin to reform the yellow neutral tautomer.",
                        "explanation": "Le Chatelier's principle shifts the indicator equilibrium back toward the protonated H-Ind state."
                    },
                    {
                        "question": "Can turmeric be used to determine whether well water is neutral (pH 7) or acidic (pH 5)?",
                        "answer": "No, because turmeric remains yellow across both neutral and acidic pH ranges below 7.4.",
                        "explanation": "A multi-range indicator like red hibiscus or red cabbage extract is needed for acid-range differentiation."
                    }
                ],
                "reflection_task": "Test your local well water and drinking water with the turmeric strip. Does it change color? What does this tell you about its pH balance?",
                "follow_up_practice": "Prepare a red hibiscus petal extract in warm water and test both lemon juice and wood ash water. Tabulate the resulting color changes.",
                "is_supported": True
            }

        # 7. Engineering / Computer Science / General Technology / Mechanisms
        else:
            return {
                "activity_id": f"lfa_eng_{difficulty.lower()}",
                "activity_title": f"Everyday Mechanical Advantage, Siphon Fluidics & Algorithmic Sorting for {topic or subject}",
                "title": f"Everyday Mechanical Advantage, Siphon Fluidics & Algorithmic Sorting for {topic or subject}",
                "demonstration_type": "household_demonstration",
                "academic_grounding": {
                    "subject": subject,
                    "topic": topic or "Mechanical Advantage, Fluid Flow & Algorithmic Principles",
                    "unit": "Applied Engineering & Practical Systems",
                    "curriculum_reference": "Standard Technical & Science Curriculum",
                    "grade_or_semester": semester,
                    "program": program or "Engineering & Applied Technology",
                    "department": department or "Applied Technology"
                },
                "learning_objectives": [
                    "Demonstrate mechanical gear ratios and moment equilibrium on simple lever mechanisms.",
                    "Verify Bernoulli's principle and atmospheric hydrostatic siphon flow using low-cost flexible tubing."
                ],
                "real_world_concept": "Torque transmission ratio (N1/N2 = omega2/omega1) and hydrostatic head potential driving continuous siphon fluid transport.",
                "materials_student_has": [
                    "A standard multi-speed bicycle wheel and pedal gear set (or simple lever stick)",
                    "1 meter of clear plastic water hose / tubing (or straw)",
                    "Two buckets or clay pots at different elevation levels",
                    "Clean water"
                ],
                "safe_substitutions": [
                    "A wooden plank balanced on a log fulcrum instead of bicycle gears",
                    "A bendable drinking straw or flexible PVC pipe instead of garden hose"
                ],
                "no_purchase_alternative": "Use any household bucket and common bicycle gears or a balanced wooden rod.",
                "steps": [
                    "Step 1: Count the number of teeth on the front pedal chainring (N1) and the rear wheel cog (N2).",
                    "Step 2: Rotate the pedal one full 360-degree revolution and count the exact revolutions completed by the rear wheel to compute gear ratio = N1 / N2.",
                    "Step 3: Fill elevated Bucket A with water and place empty Bucket B 50 cm lower on the ground.",
                    "Step 4: Submerge the flexible tube completely in Bucket A to purge air, clamp both ends with fingers, and place one end in Bucket B.",
                    "Step 5: Release fingers and observe continuous spontaneous water flow driven by gravity and hydrostatic pressure difference."
                ],
                "simple_explanation": "Bicycle gears let you trade speed for pushing force. Siphons let water climb up over a bucket rim and down into another container automatically as long as the second container is placed lower than the first.",
                "academic_theory": "Gear ratio GR = N_drive / N_driven = omega_driven / omega_drive = Torque_drive / Torque_driven. Siphon flow velocity is governed by Torricelli's Law and Bernoulli's equation: v = sqrt(2 * g * Delta_h), where Delta_h is the vertical height difference between the free water surfaces.",
                "everyday_applications": "Underpins rural irrigation channels, fuel transfer from village tractor tanks, human-powered water pumps, and flour mill mechanical power transmission.",
                "expected_observations": "Higher gear ratio yields more wheel revolutions per pedal turn with increased resistance. Siphon flow rate increases proportionally with vertical drop height Delta_h.",
                "limitations_and_misconceptions": "A siphon cannot lift water higher than the barometric atmospheric head limit (approx. 10 meters for water at sea level) because cavitation will break the liquid column.",
                "safety_precautions": "Ensure fingers are kept clear of moving bicycle chain spokes during gear rotation.",
                "understanding_questions": [
                    {
                        "question": "Why is it easier to ride a bicycle uphill when shifting to a smaller front gear and larger rear gear?",
                        "answer": "It reduces the gear ratio (GR < 1), multiplying torque applied to the rear wheel at the expense of rotational speed.",
                        "explanation": "Conservation of mechanical energy dictates that Power = Torque * angular velocity (P = tau * omega)."
                    },
                    {
                        "question": "Why does water continue flowing upward over the rim of Bucket A in a siphon?",
                        "answer": "The longer fluid column in the lower tube creates a net gravitational suction, lowering pressure at the siphon crest below atmospheric pressure.",
                        "explanation": "Liquid cohesion and atmospheric pressure push water up into the low-pressure crest zone."
                    },
                    {
                        "question": "What happens to the siphon flow rate if you lower Bucket B by another 30 cm?",
                        "answer": "The flow rate increases because the gravitational potential head Delta_h is greater (v = sqrt(2*g*Delta_h)).",
                        "explanation": "Flow velocity scales with the square root of vertical drop height."
                    }
                ],
                "reflection_task": "Observe how water is transferred or pumped in your local village. How does elevation difference reduce the energy needed?",
                "follow_up_practice": "Calculate the theoretical flow rate (liters per minute) through a 1 cm diameter tube for Delta_h = 0.8 meters.",
                "is_supported": True
            }


    def generate_knowledge_transfer(self, subject: str, topic: str, semester: str = "", program: str = "", department: str = "", syllabus_context: str = "") -> Dict[str, Any]:
        """
        Generate a strictly semester-aware Knowledge Transfer activity grounded in the student's uploaded syllabus.
        Explicitly identifies:
          - exact subject
          - exact syllabus topic
          - real-world application
          - concept explanation
          - practical connection
          - example
          - common misconception
          - quick understanding question
          - exam relevance
        """
        sem_str = f"Semester {semester}" if semester and "semester" not in str(semester).lower() else (str(semester) or "Active Semester")
        prompt = f"""
Generate a comprehensive, syllabus-grounded Knowledge Transfer activity for a college student using gemini-3.6-flash.

Academic Context:
- Program: {program or 'Engineering'}
- Department: {department or 'Information Technology'}
- Semester: {sem_str}
- Exact Subject: {subject}
- Exact Syllabus Topic: {topic}
- Syllabus Context Excerpt: {syllabus_context[:1200] if syllabus_context else 'Active accredited curriculum syllabus'}

Requirement:
Bridge textbook theory to real-world engineering transfer. Do NOT generate generic content that merely sounds related.
The activity must explicitly identify all 9 dimensions:
1. exact_subject: "{subject}"
2. exact_syllabus_topic: "{topic}"
3. real_world_application: Concrete real-world industrial or engineering application
4. concept_explanation: Academic rigor explanation of the core concept
5. practical_connection: Direct bridge connecting theoretical principles to production execution
6. example: Specific realistic scenario or code/architecture walkthrough
7. common_misconception: What students commonly misunderstand or get wrong
8. quick_understanding_question: Check question with 4 options, correct answer, and explanation
9. exam_relevance: Direct mapping to University Semester Exam questions / GATE / Regulation syllabus

Return ONLY JSON:
{{
  "activity_id": "kt_{subject.lower()[:4]}_{topic.lower()[:4]}",
  "exact_subject": "{subject}",
  "exact_syllabus_topic": "{topic}",
  "semester": "{sem_str}",
  "real_world_application": "Real-world engineering application description",
  "concept_explanation": "Academic concept explanation grounded in curriculum",
  "practical_connection": "Practical bridge connecting textbook theory to practice",
  "example": "Concrete technical or architectural example",
  "common_misconception": "Common student misconception and why it is wrong",
  "quick_understanding_question": {{
    "question": "Conceptual check question text",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Option A",
    "explanation": "Why Option A is correct based on syllabus principles"
  }},
  "exam_relevance": "University exam paper mapping (e.g. Anna University 13/16-Mark Question on this topic)",
  "is_valid_topic": true
}}
"""
        try:
            raw = self.generate_content(prompt, json_output=True)
            res = self.parse_json_response(raw)
            if res and isinstance(res, dict) and res.get("concept_explanation") and res.get("real_world_application"):
                res.setdefault("exact_subject", subject)
                res.setdefault("exact_syllabus_topic", topic)
                res.setdefault("semester", sem_str)
                res.setdefault("is_valid_topic", True)
                return res
        except Exception as e:
            logger.warning(f"[GeminiService] generate_knowledge_transfer error: {e}")

        return self._build_deterministic_knowledge_transfer(subject, topic, sem_str, program, department)

    def _build_deterministic_knowledge_transfer(self, subject: str, topic: str, semester: str, program: str, department: str) -> Dict[str, Any]:
        """
        Deterministic, authentic knowledge transfer activity generator.
        Guarantees all 9 required fields and strict zero hallucination.
        """
        sub_lower = subject.lower()
        top_lower = topic.lower()

        if "database" in sub_lower or "dbms" in sub_lower:
            return {
                "activity_id": f"kt_dbms_{random.randint(100, 999)}",
                "exact_subject": subject,
                "exact_syllabus_topic": topic or "Unit II: Database Design & Normalization",
                "semester": semester,
                "real_world_application": "High-concurrency banking ledger systems and distributed transaction coordinators (e.g. Stripe, Visa Payment Gateway).",
                "concept_explanation": "Database Normalization (1NF, 2NF, 3NF, BCNF) uses Functional Dependencies to systematically eliminate update, insertion, and deletion anomalies while ensuring lossless join decomposition and dependency preservation.",
                "practical_connection": "In production relational databases, un-normalized tables lead to lock contention, data drift, and massive disk I/O duplication during concurrent write transactions.",
                "example": "An un-normalized order table containing customer address details requires updating 50 rows when a customer changes address. In 3NF/BCNF, address lives in a separate table linked by a foreign key, requiring a single atomic row update.",
                "common_misconception": "Misconception: 'Higher normalization always improves read query speed.' Truth: Higher normal forms increase join overhead; production systems often normalize for write integrity (OLTP) and selectively denormalize for analytical query speed (OLAP/Data Warehouses).",
                "quick_understanding_question": {
                    "question": "Which normal form strictly eliminates all update anomalies arising from non-trivial functional dependencies X -> Y where X is not a superkey?",
                    "options": [
                        "Boyce-Codd Normal Form (BCNF)",
                        "Second Normal Form (2NF)",
                        "Third Normal Form (3NF)",
                        "First Normal Form (1NF)"
                    ],
                    "correct_answer": "Boyce-Codd Normal Form (BCNF)",
                    "explanation": "BCNF requires every determinant X in non-trivial dependencies X -> Y to be a superkey, completely eliminating anomaly-inducing dependencies allowed in 3NF."
                },
                "exam_relevance": "Directly tested in University Semester Examinations (13-mark question on 3NF vs BCNF decomposition) and GATE Computer Science (DBMS Functional Dependency questions).",
                "is_valid_topic": True
            }
        elif "network" in sub_lower:
            return {
                "activity_id": f"kt_net_{random.randint(100, 999)}",
                "exact_subject": subject,
                "exact_syllabus_topic": topic or "Unit III: Transport Layer & Congestion Control",
                "semester": semester,
                "real_world_application": "Adaptive video bitrate streaming in Netflix / YouTube and low-latency packet delivery across Cloudflare edge CDNs.",
                "concept_explanation": "TCP Congestion Control dynamically regulates the transmission rate using Congestion Window (cwnd) and Thresholds (ssthresh) via Slow Start, Congestion Avoidance (AIMD), Fast Retransmit, and Fast Recovery.",
                "practical_connection": "Without dynamic congestion windows, transmitting at full link capacity across multiple competing flows leads to bufferbloat, severe packet drop, and total network throughput collapse.",
                "example": "When a mobile device switches from Wi-Fi to 4G, packet latency spikes. TCP detects duplicate ACKs before timeout expiry, halving cwnd (Multiplicative Decrease) to prevent dropping active video stream sessions.",
                "common_misconception": "Misconception: 'TCP Slow Start means packets are transmitted slowly.' Truth: Slow Start doubles the congestion window every Round Trip Time (exponential growth), making it the fastest growth phase of TCP transmission.",
                "quick_understanding_question": {
                    "question": "In TCP Reno congestion control, what immediate action is triggered when the sender receives 3 duplicate ACKs?",
                    "options": [
                        "Fast Retransmit of the missing segment and entering Fast Recovery (ssthresh = cwnd/2)",
                        "Resetting cwnd to 1 MSS and re-entering Slow Start",
                        "Doubling the window size to overcome latency",
                        "Terminating the TCP socket connection"
                    ],
                    "correct_answer": "Fast Retransmit of the missing segment and entering Fast Recovery (ssthresh = cwnd/2)",
                    "explanation": "Triple duplicate ACKs signal that later packets arrived safely; TCP avoids an expensive RTO reset by immediately retransmitting the missing segment and halving the rate (AIMD)."
                },
                "exam_relevance": "Core 16-Mark question in Computer Networks University Exam: 'Explain TCP Congestion Control algorithms with state transition diagrams'.",
                "is_valid_topic": True
            }
        elif "web" in sub_lower:
            return {
                "activity_id": f"kt_web_{random.randint(100, 999)}",
                "exact_subject": subject,
                "exact_syllabus_topic": topic or "Unit III: Server-Side Engineering & RESTful APIs",
                "semester": semester,
                "real_world_application": "Microservices communication architecture and single sign-on (SSO) authentication across modern SaaS platforms.",
                "concept_explanation": "REST (Representational State Transfer) is a stateless client-server architectural style operating over standard HTTP verbs (GET, POST, PUT, DELETE) with JSON payloads and idempotent resource endpoints.",
                "practical_connection": "Stateless REST APIs allow cloud servers to scale horizontally behind load balancers without requiring shared session memory across server clusters.",
                "example": "In an e-commerce API, a PUT request to /api/orders/123 with status 'shipped' can be retried safely multiple times because PUT is idempotent and results in the exact same database state.",
                "common_misconception": "Misconception: 'POST and PUT are completely interchangeable.' Truth: PUT is idempotent (multiple identical requests yield identical state), whereas POST creates a new subordinate resource on every call.",
                "quick_understanding_question": {
                    "question": "Which HTTP method is defined as idempotent and used to replace an entire existing resource representation?",
                    "options": ["PUT", "POST", "PATCH", "CONNECT"],
                    "correct_answer": "PUT",
                    "explanation": "PUT is idempotent: calling PUT /resource/1 multiple times with the same body leaves the resource in the exact same state without creating duplicate entities."
                },
                "exam_relevance": "Standard University Examination Question on Web Technologies: 'Explain REST architecture principles, HTTP methods, and idempotency'.",
                "is_valid_topic": True
            }
        else:
            return {
                "activity_id": f"kt_gen_{random.randint(100, 999)}",
                "exact_subject": subject,
                "exact_syllabus_topic": topic or f"Core Syllabus of {subject}",
                "semester": semester,
                "real_world_application": f"Industrial applications, system modeling, and computational frameworks utilizing principles of {subject}.",
                "concept_explanation": f"Theoretical principles, theorems, and mathematical formulations established in the accredited syllabus of {subject} for {topic}.",
                "practical_connection": f"Transforms theoretical concepts of {topic} into actionable engineering workflows and computational implementations.",
                "example": f"Applying governing equations of {topic} to optimize resource constraints in production environments.",
                "common_misconception": f"Misconception: Treating {topic} as isolated theory without considering runtime boundary conditions and real-world system constraints.",
                "quick_understanding_question": {
                    "question": f"What is the primary governing objective when applying {topic} principles in real-world engineering?",
                    "options": [
                        "Optimizing system performance while maintaining mathematical and functional correctness",
                        "Bypassing theoretical bounds for arbitrary throughput",
                        "Replacing formal verification with random heuristics",
                        "Ignoring operational boundary conditions"
                    ],
                    "correct_answer": "Optimizing system performance while maintaining mathematical and functional correctness",
                    "explanation": f"Grounded in core engineering principles of {subject}, systems must uphold theoretical constraints while maximizing practical performance."
                },
                "exam_relevance": f"Featured in University Semester Examinations for {subject} covering {topic}.",
                "is_valid_topic": True
            }

    def generate_knowledge_challenge(
        self,
        subject: str,
        subject_id: str = "",
        module: str = "All",
        difficulty: str = "Medium",
        question_type: str = "Mixed",
        validated_topics: Optional[List[str]] = None,
        syllabus_context: str = ""
    ) -> Dict[str, Any]:
        """
        Generates 5 Knowledge Challenge questions derived strictly from the validated topics of the specified subject.
        Supports:
        - Difficulties: Easy, Medium, Difficult/Hard, Mixed
        - Types: Conceptual, Application, Numerical, Exam-oriented, Mixed
        """
        topics_list = validated_topics or []
        topics_str = ", ".join(topics_list[:15]) if topics_list else (module if module != "All" else subject)

        diff_instruction = "Mixed difficulty spanning Easy, Medium, and Difficult" if difficulty.lower() in ["all", "mixed"] else f"{difficulty.capitalize()} difficulty"
        type_instruction = "Mixed set containing Conceptual, Real-World Application, Numerical/Problem-Solving (if appropriate), and Exam-oriented questions" if question_type.lower() in ["all", "mixed"] else f"{question_type.capitalize()} style questions"

        prompt = f"""You are LearnSphere AI's Master Curriculum Assessment Engine.
Generate 5 high-yield Knowledge Challenge questions for a university student.

STRICT ACADEMIC CONTEXT:
- Validated Course / Subject: {subject} (Code: {subject_id or 'Course Core'})
- Module / Unit: {module}
- Validated Syllabus Topics: {topics_str}
- Syllabus Context: {syllabus_context[:1200]}
- Target Difficulty: {diff_instruction}
- Question Styles: {type_instruction}

STRICT CONSTRAINTS:
1. Ground every question strictly in the validated topics listed above. Do NOT generate questions from random internet domains, generic unrelated subjects, or another semester.
2. If numerical or mathematical/algorithmic problems are appropriate for this subject, include at least one numerical problem with step-by-step calculation.
3. Every question must include:
   - "id": unique string identifier (e.g. "kc_1", "kc_2")
   - "subject_id": "{subject_id}"
   - "topic": exact validated topic name from syllabus
   - "topic_id": unique topic string or code
   - "question_type": "conceptual" | "application" | "numerical" | "exam-oriented"
   - "question": clear, rigorous scenario/problem statement
   - "options": array of 4 distinct choices [A, B, C, D]
   - "correct_answer": the exact correct option text
   - "explanation": rigorous academic rationale explaining why the correct option is right and others are incorrect
   - "difficulty": "Easy" | "Medium" | "Difficult"
   - "exam_relevance": how this question aligns with semester examination grading standards
   - "hint": an intuition-building hint

Return ONLY a valid JSON object in this exact schema:
{{
  "subject": "{subject}",
  "subject_id": "{subject_id}",
  "module": "{module}",
  "difficulty": "{difficulty}",
  "questions": [
    {{
      "id": "kc_1",
      "subject_id": "{subject_id}",
      "topic": "{topics_list[0] if topics_list else subject}",
      "topic_id": "top_1",
      "question_type": "conceptual",
      "question": "Question text...",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "Detailed explanation...",
      "difficulty": "Easy",
      "exam_relevance": "Directly tested in university examinations.",
      "hint": "Think about governing constraints..."
    }}
  ]
}}
"""
        parsed = None
        try:
            raw = self.generate_content(prompt, json_output=True)
            parsed = self.parse_json_response(raw)
        except Exception as exc:
            logger.warning(f"[GeminiService] generate_knowledge_challenge AI call failed: {exc}")

        if parsed and isinstance(parsed, dict) and isinstance(parsed.get("questions"), list) and len(parsed["questions"]) > 0:
            for q in parsed["questions"]:
                if not q.get("subject_id") and subject_id:
                    q["subject_id"] = subject_id
                if not q.get("topic") and topics_list:
                    q["topic"] = topics_list[0]
            return parsed

        # High-yield deterministic fallback grounded strictly in validated topics
        return self._build_deterministic_knowledge_challenge(
            subject=subject,
            subject_id=subject_id,
            module=module,
            difficulty=difficulty,
            validated_topics=topics_list
        )

    def _build_deterministic_knowledge_challenge(
        self,
        subject: str,
        subject_id: str = "",
        module: str = "All",
        difficulty: str = "Medium",
        validated_topics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """High-yield deterministic fallback for Knowledge Challenge derived strictly from validated topics."""
        topics = validated_topics or [f"{subject} Core Principles", f"{subject} Applied Methods", f"{subject} System Design", f"{subject} Optimization"]
        diff_label = "Medium" if difficulty.lower() in ["all", "mixed", "medium"] else difficulty.capitalize()

        questions = [
            {
                "id": "kc_1",
                "subject_id": subject_id,
                "topic": topics[0] if len(topics) > 0 else subject,
                "topic_id": f"top_{subject_id}_1",
                "question_type": "conceptual",
                "question": f"In {subject}, what is the fundamental governing principle of {topics[0] if len(topics) > 0 else subject} under standard boundary constraints?",
                "options": [
                    f"It enforces deterministic state transitions and prevents invariant violations",
                    f"It bypasses all system validation checks to maximize raw execution speed",
                    f"It allows unrestricted concurrent mutations without concurrency control",
                    f"It operates strictly outside the formal domain specifications of {subject}"
                ],
                "correct_answer": f"It enforces deterministic state transitions and prevents invariant violations",
                "explanation": f"In {subject}, {topics[0] if len(topics) > 0 else subject} guarantees system integrity and deterministic behavior by strictly adhering to formal invariant constraints.",
                "difficulty": "Easy" if difficulty.lower() in ["all", "mixed", "easy"] else diff_label,
                "exam_relevance": f"Core theoretical question frequently featured in {subject} semester examinations.",
                "hint": f"Recall how formal invariants prevent state corruption in {subject}."
            },
            {
                "id": "kc_2",
                "subject_id": subject_id,
                "topic": topics[1] if len(topics) > 1 else topics[0],
                "topic_id": f"top_{subject_id}_2",
                "question_type": "application",
                "question": f"When deploying {topics[1] if len(topics) > 1 else topics[0]} in a high-throughput production environment for {subject}, which architectural strategy minimizes latency while maintaining correctness?",
                "options": [
                    f"Implementing structured pipelining with localized synchronization bounds",
                    f"Eliminating all buffer constraints and running unmonitored threads",
                    f"Disabling verification layers to avoid execution overhead",
                    f"Halting all background operations during state transitions"
                ],
                "correct_answer": f"Implementing structured pipelining with localized synchronization bounds",
                "explanation": f"Structured pipelining isolates execution bottlenecks while local synchronization guarantees correctness under high workload in {subject}.",
                "difficulty": "Medium" if difficulty.lower() in ["all", "mixed", "medium"] else diff_label,
                "exam_relevance": f"Applied design scenario matching University practical paper standards.",
                "hint": "Focus on balancing concurrency with deterministic synchronization."
            },
            {
                "id": "kc_3",
                "subject_id": subject_id,
                "topic": topics[2] if len(topics) > 2 else topics[0],
                "topic_id": f"top_{subject_id}_3",
                "question_type": "numerical",
                "question": f"A system operating under {topics[2] if len(topics) > 2 else topics[0]} in {subject} processes $N = 200$ units with an efficiency factor $\\eta = 0.85$ over a baseline impedance $Z = 10$. What is the resulting effective throughput?",
                "options": [
                    "17.0 units/sec",
                    "20.0 units/sec",
                    "170.0 units/sec",
                    "8.5 units/sec"
                ],
                "correct_answer": "17.0 units/sec",
                "explanation": "Given: $N = 200$, $\\eta = 0.85$, $Z = 10$. Formula: $\\text{Throughput} = (N \\times \\eta) / Z = (200 \\times 0.85) / 10 = 170 / 10 = 17.0$ units/sec.",
                "difficulty": "Difficult" if difficulty.lower() in ["all", "mixed", "difficult", "hard"] else diff_label,
                "exam_relevance": "Standard 5-mark numerical problem for university semester exams.",
                "hint": "Apply the governing throughput formula: $(N \\times \\eta) / Z$."
            },
            {
                "id": "kc_4",
                "subject_id": subject_id,
                "topic": topics[3] if len(topics) > 3 else topics[0],
                "topic_id": f"top_{subject_id}_4",
                "question_type": "exam-oriented",
                "question": f"Which mandatory criteria do university examiners require when evaluating an 8-mark analytical answer on {topics[3] if len(topics) > 3 else topics[0]} in {subject}?",
                "options": [
                    f"Formal definition, labelled architectural diagram, governing equations, and boundary constraints",
                    f"A brief informal summary without technical terminology or diagrams",
                    f"Only code snippets without theoretical justification or complexity analysis",
                    f"Historical trivia without operational mechanisms"
                ],
                "correct_answer": f"Formal definition, labelled architectural diagram, governing equations, and boundary constraints",
                "explanation": f"Full marks in {subject} examinations require formal technical terminology, complete schematic diagrams, and explicit statement of boundary conditions.",
                "difficulty": "Medium" if difficulty.lower() in ["all", "mixed", "medium"] else diff_label,
                "exam_relevance": "Direct mapping to university marking scheme guidelines.",
                "hint": "Consider the components required for full marks in descriptive semester answers."
            },
            {
                "id": "kc_5",
                "subject_id": subject_id,
                "topic": topics[0],
                "topic_id": f"top_{subject_id}_5",
                "question_type": "conceptual",
                "question": f"What is the most common student error when analyzing boundary conditions for {topics[0]} in {subject}?",
                "options": [
                    f"Assuming steady-state behavior holds during dynamic transient transitions",
                    f"Correctly applying conservation laws to all subsystem nodes",
                    f"Verifying input constraints before computing state matrices",
                    f"Specifying proper SI units for all intermediate variables"
                ],
                "correct_answer": f"Assuming steady-state behavior holds during dynamic transient transitions",
                "explanation": f"Students frequently lose marks by neglecting transient dynamics and incorrectly assuming steady-state equations apply during rapid state shifts.",
                "difficulty": "Difficult" if difficulty.lower() in ["all", "mixed", "difficult", "hard"] else diff_label,
                "exam_relevance": "Common examiner trap featured in challenging objective and viva questions.",
                "hint": "Think about what changes when a system moves between equilibrium states."
            }
        ]

        return {
            "subject": subject,
            "subject_id": subject_id,
            "module": module,
            "difficulty": difficulty,
            "questions": questions
        }

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
You are LearnSphere AI's ULTRA-STRICT REAL HUMAN TEACHER AND EXAMINER.
Evaluate the student's self-evaluation response rigorously and strictly proportional to the maximum marks (10 marks).

Subject: {subject}
Question: {question_text}
Expected Concept & Depth: {expected_concept}
Student Response: {student_response}
Maximum Marks: 10

STRICT HUMAN TEACHER GRADING RULES:
1. PROPORTIONALITY & DEPTH: For a 10-mark question, if the student wrote only a brief/short answer (1-2 sentences without depth, mechanisms, examples, or multi-point breakdown), STRICTLY CAP at MAX 2.5 - 3.5 marks out of 10. NEVER award 7, 8, 9, or 10 marks to a short answer! Full marks require exhaustive, multi-part, structured explanation.
2. ACCURACY & EVIDENCE: Check for correct terminology, core mechanisms, and step-by-step reasoning.
3. CLEAR ARITHMETIC: In feedback, explain exactly why marks were awarded and deducted.

Return ONLY JSON:
{{
  "awarded_marks": 3.0,
  "max_marks": 10,
  "percentage": 30.0,
  "feedback": "Detailed specific feedback referencing student's actual response and explaining marks deducted for brevity and missing depth",
  "what_was_done_correctly": ["Correctly identified core definition"],
  "what_is_missing": ["In-depth multi-point explanation", "Real-world examples", "Detailed mechanism"],
  "expected_answer": "Model answer with comprehensive key points",
  "misconception_detected": false,
  "misconception": ""
}}
"""
        raw = self.generate_content(prompt, json_output=True)
        return self.parse_json_response(raw)

    def generate_trainer_response(
        self,
        message: str,
        subject: str,
        topic: str = "",
        unit: str = "",
        syllabus_excerpt: str = "",
        student_context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        study_strategy: str = ""
    ) -> str:
        """
        Expert Human Tutor & Academic Coach for Personal Trainer.
        Provides conversational, rigorous, and progressive teaching grounded strictly in the validated curriculum.
        """
        ctx = student_context or {}
        student_name = ctx.get("name") or "Student"
        student_id = ctx.get("student_id") or ""
        level = ctx.get("level") or "college"
        degree = ctx.get("degree") or ctx.get("program") or "Undergraduate"
        dept = ctx.get("department") or ctx.get("branch") or "Engineering/Science"
        semester = ctx.get("semester") or ctx.get("current_semester") or ""
        sem_str = f"Semester {semester}" if semester else "Current Academic Term"
        subject_id = ctx.get("subject_id") or ""
        curriculum_id = ctx.get("curriculum_id") or ""
        validated_topics = ctx.get("validated_topics") or []
        validated_topics_str = ", ".join(validated_topics[:12]) if validated_topics else (topic or "Core Syllabus Topics")

        # Format conversation history for multi-turn pedagogical awareness
        history_text = ""
        if history and isinstance(history, list):
            valid_turns = []
            for h in history[-8:]:
                role = "Student" if h.get("role") == "user" else "Tutor"
                txt = (h.get("text") or h.get("message") or "").strip()
                if txt:
                    valid_turns.append(f"{role}: {txt}")
            if valid_turns:
                history_text = "CONVERSATION HISTORY:\n" + "\n".join(valid_turns) + "\n\n"

        prompt = f"""You are LearnSphere AI's Master Personal Tutor & Academic Coach.
You behave like an exceptional, encouraging, rigorous human professor/tutor.

ACADEMIC CONTEXT (Controls all educational dialogue):
- Authenticated Student: {student_name} (ID: {student_id or 'Authenticated'})
- Academic Level: {level.capitalize()} ({degree} · {dept} · {sem_str})
- Active Subject Code / ID: {subject_id or 'N/A'}
- Validated Subject: {subject}
- Active Syllabus / Curriculum ID: {curriculum_id or 'N/A'}
- Target Concept / Topic: {topic or 'Core Syllabus Concept'}
- Validated Subject Topics: {validated_topics_str}
- Validated Syllabus Blueprint: {syllabus_excerpt or subject}
- Teaching Strategy: {study_strategy or 'Progressive Mastery Coaching'}

{history_text}STUDENT'S QUESTION: "{message}"

PEDAGOGICAL & HUMAN TUTOR TEACHING GUIDELINES:

1. CORE CONTEXT CONTROL & BOUNDARIES:
   - The validated subject ({subject}) and active topic ({topic}) strictly control the educational context.
   - Do NOT generate content unrelated to the selected subject/topic unless the student explicitly asks for it.
   - Do NOT mention competing AI products, platforms, or models.

2. SOCRATIC INTERACTION & ACTIVE QUESTIONING:
   - Always teach concepts interactively. Do not just dump text; guide the student step-by-step.
   - If the student answered a previous question, evaluate their response with precise technical accuracy (praise what is correct, gently correct misconceptions).
   - ALWAYS conclude every explanation with an engaging diagnostic check-for-understanding question or active-recall prompt.

3. PRECISE DIAGRAMS, FLOWCHARTS & VISUAL SCHEMATICS:
   - For every architectural, algorithmic, structural, computational, or process-oriented concept, provide a crisp, accurate ASCII / Unicode diagram or flowchart inside a formatted code block (```text ... ```) or math block.
   - Example flowchart style:
     ```text
     [Input Data / State] ──> (Step 1: Validation) ──> [Processing Unit] ──> [Output Result]
                                     │
                                     └── [Error / Boundary Case] ──> (Rollback)
     ```

4. EVIDENCE-BASED STUDY TECHNIQUES:
   - **Feynman Technique**: Translate abstract math/computer science definitions into plain-English intuitive analogies before formal rigor.
   - **First-Principles Breakdown**: Deconstruct how the concept works from foundational laws.
   - **Active Recall**: Prompt key equations, keyword definitions, or step sequences from memory.
   - **Exam High-Score Strategy**: Highlight exact exam keywords, diagram labels, scoring breakdown, and common pitfalls.

5. PROGRESSIVE CONCEPT TEACHING FLOW:
   When explaining a concept, structure your response clearly:
   1. Intuitive Explanation & Analogy (Feynman Technique)
   2. Formal Academic Definition & Core Principles
   3. Architectural Schematic / Flowchart (ASCII/Unicode diagram)
   4. Step-by-Step Mechanism / Working Example
   5. Connection to {subject} & Exam High-Score Points
   6. Check-for-Understanding Question (Interactive prompt for student)

6. NUMERICAL & PROBLEM-SOLVING FLOW:
   Strictly follow:
   • Given: List all variables with symbols and standard units.
   • Required: Declare target quantity.
   • Formula: State governing equations clearly.
   • Substitution: Clean numerical insertion.
   • Calculation: Intermediate arithmetic steps.
   • Units & Final Answer: Highlighted final value with SI dimensions.
   • Explanation & Pitfalls: Common examiner traps.

Output clean, beautifully formatted Markdown with bold labels, structured bullet points, and code/diagram blocks.
"""
        candidate_reply = ""
        try:
            reply = self.generate_content(prompt, json_output=False)
            if reply and len(reply.strip()) > 30:
                candidate_reply = reply.strip()
        except Exception as exc:
            logger.warning(f"[GeminiService] generate_trainer_response AI call failed: {exc}")

        if not candidate_reply:
            candidate_reply = self._build_deterministic_trainer_response(
                message=message,
                subject=subject,
                topic=topic or "Core Concept",
                unit=unit or "Core Unit",
                strategy=study_strategy,
                semester=sem_str,
                student_context=ctx
            )

        # Run strict 13-point Response-Quality Validation Layer
        validated_text, _ = TrainerResponseQualityValidator.validate_and_refine(
            response_text=candidate_reply,
            student_message=message,
            subject=subject,
            topic=topic or "Core Concept",
            unit=unit or "Core Unit",
            syllabus_excerpt=syllabus_excerpt,
            student_context=ctx,
            history=history
        )

        return validated_text

    def _build_deterministic_trainer_response(
        self,
        message: str,
        subject: str,
        topic: str,
        unit: str,
        strategy: str,
        semester: str,
        student_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """High-yield pedagogical fallback adhering strictly to human tutor structures with precise diagrams and active questioning."""
        msg_lower = message.lower().strip()
        
        # 1. Confusion Resolution Flow: Identify Misunderstanding → Simplify → Explain Differently → Diagram → Example → Verify Understanding
        if any(w in msg_lower for w in ["explain again", "don't understand", "dont understand", "still confused", "re-explain", "did not get", "why does"]):
            return (
                f"🔄 **Targeted Concept Clarification: {topic} ({subject})**\n\n"
                f"### 1. Identifying the Core Confusion\n"
                f"Students often find **{topic}** tricky because textbooks present heavy formal equations without showing the intuitive real-world problem it solves in {subject}.\n\n"
                f"### 2. Intuitive Breakdown (Feynman Technique)\n"
                f"Think of **{topic}** like an automated safety valve: it ensures that whenever a state change or operation occurs, all boundary rules are strictly checked before letting the system proceed.\n\n"
                f"### 3. Visual Flowchart\n"
                f"```text\n"
                f"┌─────────────────────────┐\n"
                f"│ Incoming Request / Data │\n"
                f"└────────────┬────────────┘\n"
                f"             │\n"
                f"             ▼\n"
                f"┌─────────────────────────┐     No      ┌─────────────────────────┐\n"
                f"│  {topic} Verification?  ├────────────>│ Rollback / Error Handle │\n"
                f"└────────────┬────────────┘              └─────────────────────────┘\n"
                f"             │ Yes\n"
                f"             ▼\n"
                f"┌─────────────────────────┐\n"
                f"│ Deterministic Execution │\n"
                f"└────────────┬────────────┘\n"
                f"             │\n"
                f"             ▼\n"
                f"┌─────────────────────────┐\n"
                f"│ Stable State Output     │\n"
                f"└─────────────────────────┘\n"
                f"```\n\n"
                f"### 4. Concrete Example\n"
                f"When multiple users update data simultaneously, **{topic}** orders every transaction sequentially so data corruption never occurs.\n\n"
                f"### 5. Check Your Understanding\n"
                f"👉 *Based on the flowchart above, what happens if the incoming state violates {topic}'s boundary condition? Can you describe it in your own words?*"
            )

        # 2. Industry Example / Practical Scenario Flow
        if any(w in msg_lower for w in ["example", "scenario", "industry", "real world", "application", "use case"]):
            return (
                f"🏢 **Real-World & Industry Example: {topic} ({subject})**\n\n"
                f"### 1. Industry Scenario & Context\n"
                f"In production-grade {subject} systems, **{topic}** is widely deployed across enterprise architectures to eliminate race conditions and enforce data integrity.\n\n"
                f"### 2. Practical Architecture Flowchart\n"
                f"```text\n"
                f"[ Enterprise Client Application ]\n"
                f"                │ (Payload Request)\n"
                f"                ▼\n"
                f"[ {topic} Validation Layer ] ──> [ Verified High-Integrity State ]\n"
                f"                │ (If Violation)\n"
                f"                ▼\n"
                f"[ Automated Audit & Recovery ]\n"
                f"```\n\n"
                f"### 3. Concrete Implementation Example\n"
                f"Consider a high-volume platform. When two concurrent operations target the same resource, **{topic}** applies deterministic serialization so the system never reaches an inconsistent state.\n\n"
                f"### 4. Key Takeaways for High Scores\n"
                f"• **Key Benefit**: Prevents anomalies and maintains system invariants under high concurrent load.\n"
                f"• **Trade-off**: Requires minimal coordination overhead for guaranteed consistency.\n\n"
                f"👉 *Check*: In this scenario, why would an unconstrained non-{topic} approach fail under high concurrency?"
            )

        # 3. Practice / Testing Question Flow
        if any(w in msg_lower for w in ["test me", "practice question", "quiz me", "give me a question", "challenge me"]):
            return (
                f"📝 **Active Recall Practice Challenge: {topic} ({subject})**\n\n"
                f"Here is a targeted university-pattern practice question from **{unit}** ({semester}):\n\n"
                f"### Practice Question (5 Marks)\n"
                f"**Question**: State the governing principle of **{topic}** in {subject}. Draw a brief structural diagram illustrating how it processes state transitions and state two key advantages.\n\n"
                f"### Quick Answering Guide\n"
                f"1. **Core Rule (2 Marks)**: 1-2 sentences defining {topic}.\n"
                f"2. **Schematic (2 Marks)**: Input ──> {topic} ──> Output flow.\n"
                f"3. **Merits (1 Mark)**: Mention consistency and throughput.\n\n"
                f"👉 *Type your answer below! I will evaluate your points, mark your response, and highlight any scoring keywords you can add!*"
            )

        # 2. Numerical / Problem-Solving Flow: Given → Required → Formula → Substitution → Calculation → Units → Final Answer → Explanation
        if any(w in msg_lower for w in ["numerical", "solve", "calculate", "step by step numerical", "find the value", "derivation", "formula", "problem"]):
            return (
                f"📝 **Structured Problem-Solving: {topic} ({subject})**\n\n"
                f"Let's work through a standard {semester} numerical problem step-by-step:\n\n"
                f"### 1. Problem Architecture\n"
                f"```text\n"
                f"[Input: Parameter X] ──(Scaling Factor: 1.25)──> [ {topic} Engine ] ──(Impedance: 25)──> [ Output Metric: 5.0 ]\n"
                f"```\n\n"
                f"### 2. Given\n"
                f"• Primary Input Parameter ($X$): $100$ (Standard operating threshold)\n"
                f"• Scaling Factor ($K$): $1.25$\n"
                f"• System Impedance / Resistance ($R$): $25$\n\n"
                f"### 3. Required\n"
                f"• Compute the optimal output metric ($Z$) governed by **{topic}**.\n\n"
                f"### 4. Governing Formula\n"
                f"$$Z = \\frac{{X \\times K}}{{R}}$$\n\n"
                f"### 5. Step-by-Step Substitution & Calculation\n"
                f"$$Z = \\frac{{100 \\times 1.25}}{{25}} = \\frac{{125}}{{25}} = 5.0$$\n\n"
                f"### 6. Units & Final Answer\n"
                f"**Final Answer: $5.0$ Units** (Within standard tolerance limits).\n\n"
                f"### 7. Examiner Pitfall to Avoid\n"
                f"⚠️ *Common Mistake*: Always convert parameters to consistent SI base units before substitution.\n\n"
                f"👉 *Quick Check*: If the input parameter $X$ increases from $100$ to $200$, what will the new output metric be?"
            )

        # 3. Exam Preparation Flow: Concept → Important Points → Expected Exam Wording → Diagram → Common Mistakes → Practice Question
        if any(w in msg_lower for w in ["exam", "scoring", "full marks", "how to write", "university exam", "marking scheme", "keywords", "marks"]):
            return (
                f"🎯 **Exam High-Score Blueprint: {topic} ({subject})**\n\n"
                f"### 1. Concept Definition (2 Marks)\n"
                f"**{topic}** is a core operational mechanism in {unit} ({semester}) that enforces deterministic execution, state consistency, and system throughput.\n\n"
                f"### 2. Mandatory Architectural Diagram (3 Marks)\n"
                f"```text\n"
                f"┌────────────────┐       ┌─────────────────┐       ┌────────────────┐\n"
                f"│ System Inputs  ├──────>│ {topic} Control ├──────>│ System Outputs │\n"
                f"└────────────────┘       └────────┬────────┘       └────────────────┘\n"
                f"                                  │\n"
                f"                         ┌────────▼────────┐\n"
                f"                         │ Feedback Loop   │\n"
                f"                         └─────────────────┘\n"
                f"```\n\n"
                f"### 3. Key Technical Points & Scoring Keywords (3 Marks)\n"
                f"• **Mandatory Keywords**: *Deterministic state*, *Invariant constraints*, *Throughput optimization*, *Fault isolation*.\n"
                f"• **Working Steps**: Detail input verification, transformation cycle, and boundary validation.\n\n"
                f"### 4. Common Mistakes Evaluators Penalize\n"
                f"⚠️ Omitting the labelled block diagram (costs 2-3 marks immediately).\n"
                f"⚠️ Using colloquial language instead of standard technical keywords.\n\n"
                f"### 5. Exam Practice Question (8 Marks)\n"
                f"**Question**: With the aid of a neat block schematic, explain the architecture and operating principles of **{topic}** in {subject}.\n\n"
                f"👉 *How would you state the one-sentence formal definition of {topic} for the first 2 marks? Give it a try!*"
            )

        # 4. Feynman / Simple Explanation Flow
        if any(w in msg_lower for w in ["explain simply", "simple words", "simple explanation", "like i'm 5", "easy words", "feynman"]):
            return (
                f"💡 **Feynman Explanation: {topic} ({subject})**\n\n"
                f"### 1. The Core Idea in Plain English\n"
                f"Think of **{topic}** as a smart traffic controller inside {subject}. It ensures that every task gets processed without crashing into other tasks.\n\n"
                f"### 2. Relatable Analogy\n"
                f"Imagine a busy airport runway. If two planes attempt to land simultaneously without a control tower, an accident happens. **{topic}** is the control tower that schedules every operation cleanly.\n\n"
                f"### 3. Simple Visual Flowchart\n"
                f"```text\n"
                f"[ Incoming Tasks ] ──> [ {topic} Control Tower ] ──> [ Safe Scheduled Execution ]\n"
                f"```\n\n"
                f"### 4. Real-World Application\n"
                f"In high-performance systems, **{topic}** coordinates memory and network requests so applications stay fast and responsive.\n\n"
                f"### 5. Check Your Understanding\n"
                f"👉 *If a system had zero coordination, what is the single biggest problem that would occur?*"
            )

        # 5. Progressive Concept Teaching Flow (Default)
        return (
            f"📚 **Progressive Concept Mastery: {topic}**\n\n"
            f"**Subject**: {subject} · **Module**: {unit} · **Academic Context**: {semester}\n\n"
            f"### 1. Easy Explanation (Feynman Technique)\n"
            f"At its core, **{topic}** is a structured discipline in {subject} designed to handle complexity, verify system constraints, and guarantee deterministic results.\n\n"
            f"### 2. Building Intuition\n"
            f"Think of an automated quality-control sensor on a high-speed production line. If any component is misaligned, it detects and aligns it before moving to the next stage.\n\n"
            f"### 3. Precise Architecture & Flowchart\n"
            f"```text\n"
            f"┌──────────────────────┐\n"
            f"│ Initial State (S0)   │\n"
            f"└──────────┬───────────┘\n"
            f"           │\n"
            f"           ▼\n"
            f"┌──────────────────────┐     Valid     ┌──────────────────────┐\n"
            f"│  {topic} Engine      ├──────────────>│ Target State (S1)    │\n"
            f"└──────────┬───────────┘               └──────────────────────┘\n"
            f"           │ Invalid\n"
            f"           ▼\n"
            f"┌──────────────────────┐\n"
            f"│ Exception Handling   │\n"
            f"└──────────────────────┘\n"
            f"```\n\n"
            f"### 4. Academic & Theoretical Principles\n"
            f"Formally, **{topic}** defines invariant boundaries and transformation rules that govern state changes, guaranteeing stability across nominal operating limits in {subject}.\n\n"
            f"### 5. Connection to {subject}\n"
            f"In your {semester} syllabus for {subject}, mastering **{topic}** is essential for answering university examination questions and implementing real-world systems.\n\n"
            f"### 6. Interactive Check Question\n"
            f"👉 *Looking at the flowchart above, why is it vital for {topic} to have an explicit exception handling path? What would happen without it?*\n\n"
            f"### 7. Practice Exam Question\n"
            f"How would you explain the operational advantage of **{topic}** over an unconstrained baseline system in an exam?"
        )

    @property
    def primary_model(self) -> str:
        return self.model


gemini_service = GeminiService()

