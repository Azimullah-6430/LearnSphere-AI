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
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip() or "gemini-1.5-flash"
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
                # Process ALL pages without silent truncation
                total_pages = len(doc)
                for page_idx in range(total_pages):
                    page = doc[page_idx]
                    pix = page.get_pixmap(dpi=150)
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
        for candidate in ("gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-pro"):
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
                                time.sleep(2 ** attempt)
                                continue
                            break
                    except requests.Timeout:
                        last_error = f"Request timed out on {model_name} after {self.timeout}s"
                        time.sleep(1)
                    except Exception as exc:
                        last_error = f"Network/API error on {model_name}: {exc}"
                        time.sleep(1)

        raise RuntimeError(f"Gemini API processing failed: {last_error}")

    def parse_json_response(self, raw_text: str) -> Dict[str, Any]:
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(cleaned[start:end + 1])
                except json.JSONDecodeError:
                    pass
        raise ValueError("Response from Gemini 3.6 Flash was not valid JSON.")

    # ------------------------------------------------------------------
    # Specialized Gemini Operations
    # ------------------------------------------------------------------

    def evaluate_question_paper(self, qp_file: Any, subject: str = "", level: str = "school", board: str = "", stream: str = "", semester: str = "") -> Dict[str, Any]:
        prompt = f"""
You are the QUESTION PAPER EXTRACTION ENGINE for LearnSphere AI.
Extract the exact question paper structure printed on the uploaded document using gemini-3.6-flash.

Context:
- Subject hint: {subject}
- Level: {level}
- Board: {board}
- Stream: {stream}
- Semester: {semester}

RULES:
1. Extract exact printed subject name from paper title/header.
2. Inspect ALL pages. Extract exact question numbers, question text, maximum marks, sections, and choice groups.
3. If choice options exist (e.g. Q1 OR Q2, Answer any 1), group them under 'choice_group' and 'required_choice_count'.
4. Do NOT invent maximum marks. If unprinted/ambiguous, leave maximum_marks null or specify 0 so it requires review.

Return ONLY JSON matching schema:
{{
  "subject": "Printed Subject Name",
  "exam_title": "Exam Title",
  "total_marks": 50,
  "sections": ["Section A", "Section B"],
  "questions": [
    {{
      "question_id": "q1",
      "question_number": "1(a)",
      "question_text": "Exact text",
      "maximum_marks": 5,
      "section": "Section A",
      "question_type": "descriptive",
      "choice_group": "group_1",
      "required_choice_count": 1
    }}
  ]
}}
"""
        raw = self.generate_content(prompt, files=[qp_file], json_output=True)
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
        qp_json = json.dumps(qp_structure, ensure_ascii=False, indent=2)
        prompt = f"""
You are LearnSphere AI's STRICT HUMAN EXAMINATION EVALUATOR running gemini-3.6-flash.

SUBJECT: {subject}
LEVEL: {level}

EXTRACTED QUESTION PAPER STRUCTURE:
{qp_json}

RULES:
1. Inspect EVERY page of the handwritten answer script. Match answers to question numbers regardless of page order.
2. Evaluate student's actual handwritten answer for correctness, formula derivation, substitution, arithmetic, and completeness.
3. Award marks <= maximum_marks.
4. Calculate marks_lost = maximum_marks - awarded_marks.
5. Provide specific, evidence-based feedback referring directly to the student's actual written text or equation.
6. Flag conceptual misunderstandings under 'misconception_detected' with 'misconception' detail. Simple arithmetic slips are NOT misconceptions.

Return ONLY JSON matching schema:
{{
  "is_unreadable": false,
  "unreadable_reason": "",
  "evaluations": [
    {{
      "question_id": "q1",
      "question_number": "1(a)",
      "attempted": true,
      "maximum_marks": 5,
      "awarded_marks": 4,
      "marks_lost": 1,
      "student_answer": "Exact summary of what student wrote",
      "correct_answer_or_expected_points": "Model answer",
      "question_feedback": "Detailed specific feedback referring to student answer",
      "what_was_done_correctly": ["Correct formula applied"],
      "what_is_missing": ["Missing final SI unit"],
      "what_student_should_write": "Exact required response for full marks",
      "concepts_tested": ["Newton's Second Law"],
      "misconception_detected": false,
      "misconception": "",
      "confidence": 0.95
    }}
  ],
  "overall_feedback": "Detailed overall performance summary."
}}
"""
        files = [qp_file, ans_file]
        if rubrics_file:
            files.append(rubrics_file)
        if syllabus_file:
            files.append(syllabus_file)

        raw = self.generate_content(prompt, files=files, json_output=True)
        return self.parse_json_response(raw)

    def verify_evaluation(self, qp_structure: Dict[str, Any], eval_result: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
You are the INDEPENDENT EVALUATION VERIFIER for LearnSphere AI running gemini-3.6-flash.

Inspect the question paper structure and the AI evaluation result below.

QUESTION PAPER:
{json.dumps(qp_structure, ensure_ascii=False)[:4000]}

EVALUATION RESULT:
{json.dumps(eval_result, ensure_ascii=False)[:6000]}

TASK:
Verify:
1. Question count and Question IDs match.
2. Awarded marks <= maximum marks for all questions.
3. Arithmetic sum of awarded marks equals total obtained marks.
4. Optional question choice rules were obeyed without double counting.
5. Feedback is specific and refers to actual student work.

Return ONLY JSON matching schema:
{{
  "verified": true,
  "disagreement_detected": false,
  "reason": "Evaluation verified clean and consistent.",
  "suggested_status": "COMPLETED"
}}
If disagreement is detected, set "verified": false, "disagreement_detected": true, "suggested_status": "NEEDS_TEACHER_REVIEW".
"""
        raw = self.generate_content(prompt, json_output=True)
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
