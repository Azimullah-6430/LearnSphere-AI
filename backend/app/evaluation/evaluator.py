import os
import json
import base64
import random
import time
import traceback
import re
from typing import Any, Dict, List, Optional
from pathlib import Path

import requests  # type: ignore
from dotenv import load_dotenv

load_dotenv(override=True)


class EvaluationAgent:
    """Multimodal examination evaluator for printed QPs and handwritten scripts."""

    def __init__(self):
        # Primary model for strict paper evaluation
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        self.api_url = (
            "https://generativelanguage.googleapis.com"
            f"/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        )
        self.timeout = 180
        self.max_retries = 4

        print("=" * 70)
        print("LEARNSPHERE EVALUATION AGENT INITIALIZED")
        print(f"PRIMARY MODEL: {self.model}")
        print("API KEY STATUS:", "CONFIGURED (Live Multimodal)" if self.api_key else "NOT CONFIGURED")
        print("=" * 70)

    @property
    def api_key(self) -> str:
        """Read fresh on every access across all possible env variable names."""
        for key in ("GEMINI_API_KEY", "Gemini_API_Key_6", "GEMINI_API_KEY_6", "GOOGLE_API_KEY"):
            val = os.getenv(key, "").strip()
            if val:
                return val
        return ""

    def evaluate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes strict paper evaluation based ONLY on the uploaded Question Paper and Answer Script.
        """
        print("=" * 70)
        print("EVALUATION PIPELINE STARTED")
        print("=" * 70)

        request = self._normalize_request(request)
        self._validate_request(request)

        subject = request.get("subject", "General")
        student_name = request.get("student_name", "Student")
        roll_number = request.get("roll_number", "N/A")
        
        level = request.get("level", "school") # 'school' or 'college'
        board = request.get("board", "CBSE")
        stream = request.get("stream", "Science")
        semester = request.get("semester", "")

        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured in backend/.env. "
                "Please add a valid GEMINI_API_KEY to perform paper-based evaluation."
            )

        print(f"[1/3] Reading Question Paper structure for {subject} ({level.upper()})...")
        qp = self.analyze_question_paper(
            question_paper=request["question_paper"],
            level=level,
            board=board,
            stream=stream,
            semester=semester,
            syllabus=request.get("syllabus")
        )
        qp = self._normalize_question_paper(qp)
        self._validate_question_paper_structure(qp)

        print(f"Detected total marks from QP: {qp['total_marks']}")
        print(f"Detected questions from QP: {len(qp['questions'])}")

        print(f"[2/3] Evaluating handwritten answer script strictly against question paper...")
        result = self.evaluate_visual_script(
            question_paper=request["question_paper"],
            answer_script=request["answer_script"],
            question_paper_structure=qp,
            subject=subject,
            rubrics=request.get("rubrics"),
            syllabus=request.get("syllabus"),
            level=level
        )

        print("[3/3] Validating and calculating final marks...")
        result = self._normalize_evaluations(result)
        final = self.calculate_final_result(qp, result)

        final["student"] = {
            "name": student_name,
            "roll_number": roll_number,
            "subject": subject,
            "level": level,
            "board": board,
            "stream": stream,
            "semester": semester
        }
        final["question_paper"] = qp

        print("=" * 70)
        print("EVALUATION COMPLETED SUCCESSFULLY")
        print(f"FINAL SCORE: {final.get('obtained_marks')}/{final.get('total_marks')} ({final.get('percentage')}%)")
        print("=" * 70)
        return final

    def _normalize_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(request, dict):
            raise ValueError("Evaluation request must be an object.")

        normalized = dict(request)
        for field in ("question_paper", "answer_script", "rubrics", "syllabus"):
            value = normalized.get(field)
            if isinstance(value, str) and value.strip():
                normalized[field] = {"path": value.strip()}
            elif isinstance(value, dict):
                if not value.get("path"):
                    for key in ("filepath", "file_path", "saved_path", "filename"):
                        if value.get(key):
                            value = dict(value)
                            value["path"] = value[key]
                            break
                normalized[field] = value
        return normalized

    def _validate_request(self, request: Dict[str, Any]) -> None:
        for field in ("question_paper", "answer_script", "subject"):
            if not request.get(field):
                raise ValueError(f"Missing required input file/field: {field}")

        self._validate_file(request["question_paper"], "Question paper")
        self._validate_file(request["answer_script"], "Answer script")

    def _validate_file(self, info: Dict[str, Any], label: str) -> None:
        if not isinstance(info, dict) or not info.get("path"):
            raise ValueError(f"{label} path is missing.")
        path = info.get("path")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"{label} file not found: {path}")

    def analyze_question_paper(
        self,
        question_paper: Dict[str, Any],
        level: str = "school",
        board: str = "CBSE",
        stream: str = "Science",
        semester: Any = "",
        syllabus: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        prompt = f"""
You are a senior examination paper structure extraction specialist.
ACADEMIC LEVEL: {level.upper()} ({board} / {stream} / Semester: {semester})

Inspect EVERY PAGE of the uploaded question paper carefully.
Extract the EXACT total marks and question structure printed on the paper.

EXTRACTION RULES:
1. Uploaded Question Paper is the ONLY source of truth.
2. Extract EXACT printed total marks and maximum marks per question.
3. Preserve exact question numbers: 1, 1(a), 2(b), Q3, etc.
4. Extract exact question text, options (for MCQ), and key concepts required.

Return ONLY valid JSON in this exact format:
{{
  "subject": "",
  "total_marks": 100,
  "questions": [
    {{
      "question_number": "1",
      "question_text": "Exact question text extracted from paper",
      "maximum_marks": 5,
      "question_type": "short_answer|mcq|long_answer|numerical|derivation"
    }}
  ]
}}
"""
        files = [question_paper]
        if syllabus:
            files.append(syllabus)
        text = self._call_gemini(prompt, files)
        return self._parse_json_response(text, "question paper extraction")

    def _normalize_question_paper(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("Question paper response must be a JSON object.")
        total = self._number(data.get("total_marks"))
        raw = data.get("questions", [])
        if not isinstance(raw, list) or not raw:
            raise ValueError("No questions could be extracted from the uploaded question paper.")

        questions = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            qno = item.get("question_number", item.get("number"))
            marks = self._number(item.get("maximum_marks", item.get("max_marks")))
            if qno is not None and marks is not None:
                questions.append({
                    "question_number": str(qno).strip(),
                    "question_text": str(item.get("question_text", "")),
                    "maximum_marks": float(marks),
                    "question_type": str(item.get("question_type", "short_answer")),
                })

        if not questions:
            raise ValueError("Could not extract valid question marks from the question paper.")

        if not total:
            total = sum(q["maximum_marks"] for q in questions)

        return {"total_marks": float(total), "questions": questions}

    def _validate_question_paper_structure(self, qp: Dict[str, Any]) -> None:
        if not qp.get("questions"):
            raise ValueError("No valid questions found in Question Paper.")

    def evaluate_visual_script(
        self,
        question_paper: Dict[str, Any],
        answer_script: Dict[str, Any],
        question_paper_structure: Dict[str, Any],
        subject: str,
        rubrics: Optional[Dict[str, Any]],
        syllabus: Optional[Dict[str, Any]],
        level: str = "school"
    ) -> Dict[str, Any]:
        syllabus_text = "A syllabus reference document was provided. Ensure answer evaluation aligns strictly with syllabus criteria." if syllabus else ""

        prompt = f"""
You are a HIGH-ACCURACY (>90% PRECISION), STRICT, HONEST, and ADAPTIVE MASTER EXAMINATION EVALUATOR.
SUBJECT: {subject}
ACADEMIC LEVEL: {level.upper()}

QUESTION PAPER STRUCTURE (source of truth for marks & questions):
{json.dumps(question_paper_structure, ensure_ascii=False, indent=2)}

{syllabus_text}

STRICT MASTER EVALUATOR & HANDWRITING ADAPTATION INSTRUCTIONS:
1. HANDWRITING ADAPTATION & ACCURACY (>90% TARGET):
   - Read EVERY PAGE of the uploaded student answer script carefully.
   - Adapt to all kinds of handwriting styles: neat, cursive, messy, faint pencil, scratched-out text, and varying scan orientations.
   - Recognize handwritten text in ANY language: English, Tamil, Hindi, Telugu, Kannada, Malayalam, Marathi, Bengali, Gujarati, Punjabi, Urdu, Sanskrit, French, German, Spanish, etc.
   - Evaluate the response with extreme precision (>90% accuracy target).

2. UNREADABLE / BAD HANDWRITING SAFETY RULE:
   - IF the handwriting is extremely bad, smudged, or distorted such that words or mathematical steps CANNOT be parsed with at least 80% confidence:
     - Set top-level "is_unreadable": true, "assigned_to_teacher": true, and "unreadable_reason": "Handwriting is too illegible or faint for reliable automated AI evaluation. Assigned to teacher for manual grading and mark allotment."
     - Still extract as much as possible for each question, noting "[Unreadable Script / Assigned to Teacher]" in answer_summary.

3. MULTI-SUBJECT & ACADEMIC DOMAIN PRECISION:
   - Evaluate Mathematics, Physics, Chemistry, Engineering (CS/IT, Electronics, Electrical, Mechanical, Civil, AI/ML, Data Science), Medical, Humanities, Arts, and Commerce with exact subject-specific rigor.
   - Verify step-by-step mathematical proofs, chemical equations, algorithmic code/logic, circuit parameters, and theoretical derivations.

4. STRICT HUMAN TEACHER MARKING RULES:
   - Grade with 100% honesty and accuracy like a strict real human senior examiner. Do NOT inflate marks.
   - Award full marks ONLY if the answer is completely correct and includes required working/steps.
   - Award partial credit ONLY when steps are mathematically/conceptually sound. Deduct marks for incorrect steps, calculation errors, or omitted reasoning.

5. CHOICE OPTION / OR QUESTION RULE:
   - If multiple options are attempted for an internal choice question (e.g. Q2A OR Q2B), evaluate BOTH fully, but mark the FIRST attempted choice option with its earned marks.
   - Mark the second attempted choice option with awarded_marks: 0, set "is_extra_choice": true, and add note: "Choice Option Rule: Both choice options attempted. Marks allotted for first attempt only as per exam rules."

Return ONLY valid JSON format:
{{
  "is_unreadable": false,
  "assigned_to_teacher": false,
  "unreadable_reason": "",
  "evaluations": [
    {{
      "question_number": "1",
      "answer_present": true,
      "maximum_marks": 5,
      "awarded_marks": 4,
      "question_type": "short_answer",
      "correct": true,
      "is_extra_choice": false,
      "confidence": 0.98,
      "is_unreadable": false,
      "answer_summary": "Faithful description of student's handwritten response (including native language translation if written in Tamil/Hindi/Telugu/etc.)",
      "feedback": {{
        "what_was_done_well": ["Specific correct steps, formulas, and reasoning"],
        "missing_points": ["Specific errors, calculation slips, missing steps, or incorrect formulas"],
        "expected_answer": "Complete standard solution and step-by-step marking scheme",
        "improvement": "Targeted advice explaining how the student can improve and avoid losing marks"
      }}
    }}
  ],
  "overall_feedback": "Honest, comprehensive teacher summary detailing overall performance, domain strengths, weaknesses, and key areas of improvement."
}}
"""
        files = [question_paper, answer_script]
        if rubrics:
            files.append(rubrics)
        if syllabus:
            files.append(syllabus)

        text = self._call_gemini(prompt, files)
        return self._parse_json_response(text, "visual script evaluation")

    def _normalize_evaluations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("Evaluation output must be a JSON object.")
        raw = data.get("evaluations", [])
        if not isinstance(raw, list):
            raw = []
        clean = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            qno = item.get("question_number")
            if qno is None:
                continue
            clean.append({
                "question_number": str(qno).strip(),
                "answer_present": bool(item.get("answer_present", True)),
                "maximum_marks": self._number(item.get("maximum_marks", 0)) or 0.0,
                "awarded_marks": self._number(item.get("awarded_marks", 0)) or 0.0,
                "question_type": str(item.get("question_type", "")),
                "correct": bool(item.get("correct", False)),
                "confidence": float(item.get("confidence", 0.9)),
                "is_unreadable": bool(item.get("is_unreadable", False)),
                "answer_summary": str(item.get("answer_summary", "")),
                "feedback": {
                    "what_was_done_well": self._as_list(item.get("feedback", {}).get("what_was_done_well", [])),
                    "missing_points": self._as_list(item.get("feedback", {}).get("missing_points", [])),
                    "expected_answer": str(item.get("feedback", {}).get("expected_answer", "")),
                    "improvement": str(item.get("feedback", {}).get("improvement", "")),
                },
            })
        data["evaluations"] = clean
        data["is_unreadable"] = bool(data.get("is_unreadable", False))
        data["assigned_to_teacher"] = bool(data.get("assigned_to_teacher", False))
        data["unreadable_reason"] = str(data.get("unreadable_reason", ""))
        return data

    def calculate_final_result(self, qp: Dict[str, Any], ai: Dict[str, Any]) -> Dict[str, Any]:
        raw_evals = ai.get("evaluations", [])
        
        def parse_qno_structure(qno_str: str) -> dict:
            s = str(qno_str or "").strip()
            
            # Pattern 1: Main number + dot/space + option letter + subpart (roman/digit in parens or dots)
            # e.g., 7.a (i), 7.a(ii), 7.a.1, Q7.a(i), 7.b (ii)
            m = re.match(r"^[qQ]?(\d+)[\.\_\-\s]*([a-zA-Z])[\.\_\-\s]*\(?([iIvVxX\d]+)\)?$", s)
            if m:
                main_q = m.group(1)
                opt_let = m.group(2).lower()
                subpart = m.group(3).lower()
                return {
                    "main_q": main_q,
                    "choice_option": f"{main_q}.{opt_let}",
                    "subpart": subpart,
                    "is_choice": True
                }

            # Pattern 2: Main number + dot/space + option letter (e.g. 7.a, 7.b, Q6.a, 6.b)
            m = re.match(r"^[qQ]?(\d+)[\.\_\-\s]*([a-zA-Z])$", s)
            if m:
                main_q = m.group(1)
                opt_let = m.group(2).lower()
                return {
                    "main_q": main_q,
                    "choice_option": f"{main_q}.{opt_let}",
                    "subpart": "",
                    "is_choice": True
                }

            # Pattern 3: Main number + subpart in parens (e.g., 5(i), 5(a), Q2(b))
            m = re.match(r"^[qQ]?(\d+)[\.\_\-\s]*\(([a-zA-Z\d]+)\)$", s)
            if m:
                main_q = m.group(1)
                part = m.group(2).lower()
                if len(part) == 1 and part in ('a', 'b', 'c', 'd'):
                    return {
                        "main_q": main_q,
                        "choice_option": f"{main_q}.{part}",
                        "subpart": "",
                        "is_choice": True
                    }
                else:
                    return {
                        "main_q": main_q,
                        "choice_option": f"{main_q}.{part}",
                        "subpart": part,
                        "is_choice": False
                    }

            # Pattern 4: Plain question number, e.g. 1, 2, Q3
            m = re.match(r"^[qQ]?(\d+)$", s)
            if m:
                return {
                    "main_q": m.group(1),
                    "choice_option": None,
                    "subpart": "",
                    "is_choice": False
                }

            return {
                "main_q": s.lower(),
                "choice_option": None,
                "subpart": "",
                "is_choice": False
            }

        eval_map = {self._normalize_qno(e.get("question_number", "")): e for e in raw_evals}
        
        qp_questions = qp.get("questions", [])
        all_qnos = []
        for q in qp_questions:
            all_qnos.append(str(q["question_number"]))
        for e in raw_evals:
            qno = str(e.get("question_number", ""))
            if qno and qno not in all_qnos:
                all_qnos.append(qno)

        final_evaluations = []
        choice_group_attempts = {}

        for qno in all_qnos:
            key = self._normalize_qno(qno)
            e = eval_map.get(key)
            qp_match = next((q for q in qp_questions if self._normalize_qno(q["question_number"]) == key), None)
            max_marks = float(qp_match["maximum_marks"]) if qp_match else float(e.get("maximum_marks", 5.0) if e else 5.0)
            q_type = qp_match.get("question_type") if qp_match else (e.get("question_type") if e else "short_answer")

            if e is None:
                e_item = {
                    "question_number": qno,
                    "answer_present": False,
                    "maximum_marks": max_marks,
                    "awarded_marks": 0.0,
                    "question_type": q_type,
                    "correct": False,
                    "confidence": 1.0,
                    "is_extra_choice": False,
                    "answer_summary": "No response detected in handwritten script.",
                    "feedback": {
                        "what_was_done_well": [],
                        "missing_points": ["No answer detected for this question."],
                        "expected_answer": "",
                        "improvement": "Attempt this question with proper step-by-step working."
                    }
                }
            else:
                e_item = dict(e)
                awarded = self._number(e_item.get("awarded_marks", 0)) or 0.0
                e_item["maximum_marks"] = max_marks
                e_item["awarded_marks"] = round(max(0.0, min(awarded, max_marks)), 2)
                e_item["is_extra_choice"] = bool(e_item.get("is_extra_choice", False))

            parsed = parse_qno_structure(qno)
            e_item["_parsed"] = parsed

            if parsed["is_choice"] and parsed["choice_option"]:
                main_q = parsed["main_q"]
                opt = parsed["choice_option"]
                if main_q not in choice_group_attempts:
                    choice_group_attempts[main_q] = {}
                if opt not in choice_group_attempts[main_q]:
                    choice_group_attempts[main_q][opt] = []
                if e_item.get("answer_present", True):
                    choice_group_attempts[main_q][opt].append(e_item)

            final_evaluations.append(e_item)

        # Enforce Choice Option Rule per choice_option (7.a vs 7.b)
        for main_q, options_map in choice_group_attempts.items():
            if len(options_map) > 1:
                attempted_options = list(options_map.keys())
                first_option = attempted_options[0]
                
                for extra_option in attempted_options[1:]:
                    for extra_item in options_map[extra_option]:
                        extra_item["is_extra_choice"] = True
                        extra_item["awarded_marks"] = 0.0
                        
                        fb = extra_item.get("feedback")
                        if not isinstance(fb, dict):
                            fb = {}
                            extra_item["feedback"] = fb
                        
                        miss = fb.get("missing_points") or []
                        if not isinstance(miss, list): miss = [str(miss)]
                        miss.insert(0, f"Choice Option Rule: Both choice options ({first_option.upper()} and {extra_option.upper()}) were attempted for Question {main_q}. As per examination rules, marks are allotted for all sub-parts of the first attempted choice option ({first_option.upper()}). This second choice option attempt ({extra_option.upper()}) is evaluated for feedback only with 0 marks allotted to total score.")
                        fb["missing_points"] = miss
                        extra_item["feedback"] = fb

        for item in final_evaluations:
            item.pop("_parsed", None)

        # Compute accurate total marks
        unique_slot_max_marks = 0.0
        seen_choice_slots = set()
        for q in final_evaluations:
            qno = str(q.get("question_number", ""))
            parsed = parse_qno_structure(qno)
            m_marks = float(q.get("maximum_marks", 0))
            if parsed["is_choice"] and parsed["choice_option"]:
                opt = parsed["choice_option"]
                if opt not in seen_choice_slots:
                    seen_choice_slots.add(opt)
                    unique_slot_max_marks += m_marks
            else:
                unique_slot_max_marks += m_marks

        total = float(qp.get("total_marks") or unique_slot_max_marks or 100.0)

        obtained = round(sum(float(e.get("awarded_marks", 0)) for e in final_evaluations if not e.get("is_extra_choice")), 2)
        obtained = min(total, max(0.0, obtained))
        percentage = round((obtained / total) * 100, 2) if total > 0 else 0.0

        return {
            "obtained_marks": obtained,
            "total_marks": total,
            "percentage": percentage,
            "grade": self._grade(percentage),
            "is_unreadable": bool(ai.get("is_unreadable", False)),
            "assigned_to_teacher": bool(ai.get("assigned_to_teacher", False)),
            "unreadable_reason": str(ai.get("unreadable_reason", "")),
            "evaluations": final_evaluations,
            "overall_feedback": str(ai.get("overall_feedback", "Strict paper evaluation completed."))
        }

    def _call_gemini(self, prompt: str, files: Optional[List[Dict[str, Any]]] = None) -> str:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured in backend/.env.")

        parts = [{"text": prompt}]
        for info in files or []:
            if not isinstance(info, dict):
                continue
            path = info.get("path")
            if path and os.path.isfile(path):
                with open(path, "rb") as fh:
                    encoded = base64.b64encode(fh.read()).decode("utf-8")
                parts.append({"inline_data": {"mime_type": self._guess_mime(path), "data": encoded}})

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        }
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}

        candidate_models = [
            self.model,
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.7-flash",
            "gemini-3.8-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-pro-preview",
            "gemini-flash-latest",
            "gemini-pro-latest"
        ]
        unique_models = []
        for m in candidate_models:
            if m and m not in unique_models:
                unique_models.append(m)

        last_error = None
        for model_name in unique_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            for attempt in range(2):
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                    if response.status_code == 200:
                        data = response.json()
                        candidates = data.get("candidates", [])
                        if not candidates:
                            raise RuntimeError("Gemini API returned no response candidates.")
                        parts_resp = candidates[0].get("content", {}).get("parts", [])
                        texts = [p.get("text", "") for p in parts_resp if isinstance(p, dict) and p.get("text")]
                        return "\n".join(texts)
                    
                    if response.status_code in (404, 400):
                        last_error = f"HTTP {response.status_code} for model '{model_name}': {response.text}"
                        print(f"[Gemini] Model '{model_name}' returned {response.status_code}. Falling back to next available model...")
                        break
                    
                    if response.status_code in (429, 500, 502, 503, 504):
                        time.sleep(2)
                        continue

                    last_error = f"HTTP {response.status_code} for model '{model_name}': {response.text}"
                    break
                except requests.exceptions.RequestException as exc:
                    last_error = str(exc)
                    time.sleep(2)

        raise RuntimeError(f"Gemini API request failed across all candidate models. Last error: {last_error}")

    @staticmethod
    def _number(value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value)
        try:
            m = re.search(r"-?\d+(?:\.\d+)?", str(value))
            return float(m.group()) if m else None
        except Exception:
            return None

    @staticmethod
    def _as_list(value: Any) -> List[Any]:
        return value if isinstance(value, list) else [value] if value else []

    @staticmethod
    def _guess_mime(path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        return {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(ext, "application/octet-stream")

    @staticmethod
    def _normalize_qno(value: Any) -> str:
        return re.sub(r"\s+", "", re.sub(r"^q\s*\.?\s*", "", re.sub(r"^question\s*", "", str(value or "").strip().lower())))

    @staticmethod
    def _grade(p: float) -> str:
        if p >= 90: return "A+"
        if p >= 80: return "A"
        if p >= 70: return "B+"
        if p >= 60: return "B"
        if p >= 50: return "C"
        if p >= 40: return "D"
        return "F"

    @staticmethod
    def _parse_json_response(text: str, context: str) -> Dict[str, Any]:
        cleaned = re.sub(r"^```(?:json)?\s*", "", str(text).strip(), flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start >= 0 and end > start:
                return json.loads(cleaned[start:end+1])
            raise RuntimeError(f"Failed to parse JSON from Gemini for {context}.")
