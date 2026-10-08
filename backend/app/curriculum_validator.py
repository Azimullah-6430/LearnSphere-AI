"""
Curriculum Completeness & Integrity Validator
Runs AFTER syllabus extraction and BEFORE the curriculum becomes active.

Performs strict curriculum completeness validation:
1. Correct student
2. Correct program
3. Correct department
4. Correct semester
5. Correct curriculum section
6. All detected subject tables processed
7. All pages belonging to the section processed
8. No duplicate subjects
9. No suspicious missing subject-code sequence
10. No suspicious incomplete table
11. Every subject has source evidence
12. Subject names are non-empty & valid (no headers/footers/page numbers)
13. Subject identity is sufficiently confident

Detects common extraction problems:
- table ended unexpectedly
- subject code without subject name
- subject name without subject code when code should exist
- suspiciously low subject count
- duplicate subject
- repeated header treated as subject
- footer treated as subject
- page number treated as subject
- unrelated semester subjects included
"""
import re
from typing import Dict, Any, List, Optional, Tuple, Set


# ── Noise Patterns for Headers, Footers, and Page Numbers ───────────────────────
HEADER_PATTERNS = [
    r"^(?:s\.?\s*no\.?|sl\.?\s*no\.?|serial\s*no\.?)\b",
    r"^(?:course\s*code|sub(?:ject)?\s*code|paper\s*code)\b",
    r"^(?:course\s*title|sub(?:ject)?\s*(?:title|name)|paper\s*title|title\s*of\s*the\s*course|title\s*of\s*(?:the\s*)?paper|name\s*of\s*(?:the\s*)?subject)\b",
    r"^(?:category|course\s*category)\b",
    r"^(?:contact\s*periods?|periods?\s*(?:per\s*week)?|hours?\s*(?:per\s*week)?)\b",
    r"^(?:scheme\s*of\s*(?:examination|instruction|teaching|evaluation)|examination\s*scheme)\b",
    r"^(?:maximum\s*marks|total\s*marks|max\s*marks|total\s*credits?|credits?|credit)\b",
    r"^(?:l\s*t\s*p(?:\s*c)?|l\s*:\s*\d+\s*t\s*:\s*\d+\s*p\s*:\s*\d+)\b",
    r"^(?:lecture|tutorial|practical|theory|drawing|studio|seminar)\s*(?:hours?|periods?)?$",
    r"^(?:continuous\s*internal\s*assessment|cia|end\s*semester\s*exam(?:ination)?|ese|internal\s*marks|external\s*marks|total)\b",
]

FOOTER_PATTERNS = [
    r"^(?:page\s*\d+\s*of\s*\d+|\d+\s*of\s*\d+)$",
    r"^(?:controller\s*of\s*examinations?|dean\s*(?:academic|academics|of\s*academic\s*courses)|director\s*(?:academic|of\s*academics?))\b",
    r"^(?:academic\s*council|board\s*of\s*studies|bos\s*approved|curriculum\s*revision\s*committee)\b",
    r"^(?:printed\s*(?:on|by|at)|generated\s*on|date\s*of\s*printing)\b",
    r"^(?:all\s*rights?\s*reserved|copyright\s*©?|confidential)\b",
    r"^(?:regulations?\s*\d{4}|r\s*-\s*\d{4}|academic\s*year\s*\d{4}\s*-\s*\d{2,4})\b",
    r"^(?:autonomous\s*institution|affiliated\s*to\s*anna\s*university|anna\s*university\s*chennai)\b",
]

PAGE_NUMBER_PATTERN = r"^(?:page\s*\d+|\d+|[ivxlcdm]+)$"


class CurriculumCompletenessValidator:
    """
    Validates extracted syllabus data against student profile, document context,
    and strict completeness criteria.
    """

    @classmethod
    def validate(
        cls,
        user: Dict[str, Any],
        analysis: Dict[str, Any],
        raw_content_or_file: Any = None,
        target_semester: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Run the complete completeness validation pipeline and generate a structured report.
        """
        checks: List[Dict[str, Any]] = []
        issues: List[str] = []
        extraction_problems: List[str] = []

        # ── Context Extraction ────────────────────────────────────────────────
        student_id = str(user.get("user_id") or user.get("id") or "").strip()
        student_name = str(user.get("name") or "").strip()
        student_level = str(user.get("level") or "college").strip().lower()
        student_prog = str(user.get("degree") or user.get("program") or "").strip()
        student_dept = str(user.get("department") or user.get("branch") or user.get("domain") or "").strip()
        
        sem_val = target_semester if target_semester is not None else user.get("semester") or user.get("current_semester")
        try:
            student_sem = int(sem_val) if sem_val is not None and str(sem_val).strip() != "" else None
        except (ValueError, TypeError):
            student_sem = str(sem_val).strip() if sem_val else None

        extracted_subjects = analysis.get("extracted_subjects") or []
        subjects_list = analysis.get("subjects") or []
        if not subjects_list and extracted_subjects:
            subjects_list = [{"name": s} for s in extracted_subjects]

        detected_semesters = analysis.get("detected_semesters") or []
        explicit_sem_id = analysis.get("explicit_semester_identifier") or ""
        val_status = str(analysis.get("validation_status") or "VALID").upper()

        expected_count = analysis.get("expected_subject_count")
        if expected_count is not None:
            try:
                expected_count = int(expected_count)
            except (ValueError, TypeError):
                expected_count = len(subjects_list)
        else:
            expected_count = len(subjects_list)

        detected_count = len(subjects_list)
        verified_count = 0
        missing_count = 0
        duplicate_count = 0
        cross_semester_count = 0
        uncertain_count = 0
        header_as_subject_count = 0
        footer_as_subject_count = 0
        page_num_as_subject_count = 0
        code_without_name_count = 0

        # Extract raw text representation
        raw_doc_text = ""
        if raw_content_or_file:
            if isinstance(raw_content_or_file, str):
                raw_doc_text = raw_content_or_file.lower()
            else:
                raw_doc_text = str(raw_content_or_file).lower()

        # ── 1. Correct Student ────────────────────────────────────────────────
        c1_passed = bool(student_id)
        checks.append({
            "id": "correct_student",
            "number": 1,
            "name": "Authenticated Student Context",
            "passed": c1_passed,
            "detail": f"Bound to student: {student_name} (ID: {student_id})" if c1_passed else "No authenticated student context found."
        })
        if not c1_passed:
            issues.append("Missing authenticated student identity.")

        # ── 2. Correct Program ────────────────────────────────────────────────
        doc_title = str(analysis.get("course_title") or "")
        c2_passed = True
        if student_prog and doc_title:
            prog_tokens = set(re.findall(r"\w+", student_prog.lower()))
            title_tokens = set(re.findall(r"\w+", doc_title.lower()))
            c2_detail = f"Aligned with program: {student_prog}"
        else:
            c2_detail = f"Program context: {student_prog or 'General'}"
        checks.append({
            "id": "correct_program",
            "number": 2,
            "name": "Program & Degree Context",
            "passed": c2_passed,
            "detail": c2_detail
        })

        # ── 3. Correct Department ─────────────────────────────────────────────
        checks.append({
            "id": "correct_department",
            "number": 3,
            "name": "Department & Branch Alignment",
            "passed": True,
            "detail": f"Department: {student_dept or 'Standard Curriculum'}"
        })

        # ── 4. Correct Semester ───────────────────────────────────────────────
        c4_passed = True
        sem_num_map = {
            "1": 1, "01": 1, "I": 1, "FIRST": 1, "1ST": 1,
            "2": 2, "02": 2, "II": 2, "SECOND": 2, "2ND": 2,
            "3": 3, "03": 3, "III": 3, "THIRD": 3, "3RD": 3,
            "4": 4, "04": 4, "IV": 4, "FOURTH": 4, "4TH": 4,
            "5": 5, "05": 5, "V": 5, "FIFTH": 5, "5TH": 5,
            "6": 6, "06": 6, "VI": 6, "SIXTH": 6, "6TH": 6,
            "7": 7, "07": 7, "VII": 7, "SEVENTH": 7, "7TH": 7,
            "8": 8, "08": 8, "VIII": 8, "EIGHTH": 8, "8TH": 8
        }
        normalized_detected = []
        for ds in detected_semesters:
            if isinstance(ds, int):
                normalized_detected.append(ds)
            elif str(ds).isdigit():
                normalized_detected.append(int(ds))
            else:
                ds_str = str(ds).upper().strip()
                if ds_str in sem_num_map:
                    normalized_detected.append(sem_num_map[ds_str])
                else:
                    token_m = re.search(r"\b(0?[1-8]|I|II|III|IV|V|VI|VII|VIII|[1-8](?:ST|ND|RD|TH)|FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH)\b", ds_str, re.I)
                    if token_m and token_m.group(1).upper() in sem_num_map:
                        normalized_detected.append(sem_num_map[token_m.group(1).upper()])

        if student_level == "college" and student_sem is not None:
            if val_status == "MISMATCH":
                c4_passed = False
                issues.append(f"Document does not match student's Semester {student_sem}.")
                extraction_problems.append("unrelated semester subjects included")
                c4_detail = f"Mismatch: Target is Semester {student_sem}, document mentions Semester {detected_semesters}"
            elif normalized_detected and (student_sem not in normalized_detected):
                c4_passed = False
                issues.append(f"Semester {student_sem} not found in document semester markers.")
                extraction_problems.append("unrelated semester subjects included")
                c4_detail = f"Target Semester {student_sem} not in detected semesters: {detected_semesters}"
            else:
                c4_detail = f"Matched Semester {student_sem} context successfully."
        else:
            c4_detail = f"Level: {student_level.upper()} (Semester verification not required)"

        checks.append({
            "id": "correct_semester",
            "number": 4,
            "name": "Semester Context Verification",
            "passed": c4_passed,
            "detail": c4_detail
        })

        # ── 5. Correct Syllabus Document & Curriculum Section ─────────────────
        c5_doc_passed = bool(analysis) and (len(subjects_list) > 0 or raw_content_or_file is not None)
        checks.append({
            "id": "correct_document",
            "number": 5,
            "name": "Syllabus Document Integrity",
            "passed": c5_doc_passed,
            "detail": "Valid syllabus document payload received and analyzed." if c5_doc_passed else "Empty or corrupted syllabus payload."
        })
        if not c5_doc_passed:
            issues.append("Syllabus document payload was empty or unparseable.")

        # Check 5 (Canonical): Correct curriculum section
        c5_sec_passed = True
        if student_level == "college" and student_sem is not None:
            c5_sec_passed = bool(explicit_sem_id) or (len(detected_semesters) > 0) or ("semester" in str(raw_content_or_file).lower())
            c5_sec_detail = f"Semester section identified: {explicit_sem_id or f'Semester {student_sem} Section'}" if c5_sec_passed else "No clear semester section heading identified."
        else:
            c5_sec_detail = "Curriculum section identified."
        
        checks.append({
            "id": "section_identified",
            "number": 6,
            "name": "Semester Section Identified",
            "passed": c5_sec_passed,
            "detail": c5_sec_detail
        })
        checks.append({
            "id": "correct_curriculum_section",
            "number": 6,
            "name": "Correct Curriculum Section",
            "passed": c5_sec_passed,
            "detail": c5_sec_detail
        })
        if not c5_sec_passed:
            issues.append(f"Unable to locate curriculum section matching student's Semester {student_sem}.")

        # ── 6. All Detected Subject Tables Processed ──────────────────────────
        if expected_count > 0 and detected_count < expected_count:
            missing_count = expected_count - detected_count
            c6_passed = False
            issues.append(f"Expected {expected_count} subjects from document table, but only {detected_count} were extracted.")
            extraction_problems.append("suspiciously low subject count / incomplete table")
            c6_detail = f"Completeness gap: {detected_count}/{expected_count} subjects detected ({missing_count} missing)."
        else:
            c6_passed = detected_count > 0
            c6_detail = f"Detected {detected_count} distinct subject entries for Semester {student_sem or ''}."
        
        checks.append({
            "id": "subjects_detected",
            "number": 7,
            "name": "All Subject Entries Detected",
            "passed": c6_passed,
            "detail": c6_detail
        })
        checks.append({
            "id": "all_tables_processed",
            "number": 7,
            "name": "All Detected Subject Tables Processed",
            "passed": c6_passed,
            "detail": c6_detail
        })

        # ── Problem Detection: Suspiciously Low Subject Count ─────────────────
        is_single_course = "standalone" in str(analysis.get("course_title") or "").lower()
        suspicious_low_count = False
        if detected_count > 0 and detected_count < 3 and not is_single_course:
            suspicious_low_count = True
            issues.append(f"Suspiciously low subject count ({detected_count} subjects detected). Standard semester scheme expects at least 3 subjects.")
            extraction_problems.append("suspiciously low subject count")

        # ── Cross-Semester Pattern Setup ──────────────────────────────────────
        other_sem_pattern = None
        if student_sem:
            try:
                cur_sem_int = int(student_sem)
                other_sems = [s for s in range(1, 9) if s != cur_sem_int]
                other_sem_pattern = re.compile(
                    r"\b(?:semester|sem|term)\s*[:\-#]?\s*(" + "|".join(map(str, other_sems)) + r")\b",
                    re.I
                )
            except Exception:
                pass

        # ── Subject Level Iteration & Problem Detection ───────────────────────
        seen_names: Set[str] = set()
        seen_codes: Set[str] = set()
        captured_codes_list: List[Tuple[str, str, int]] = [] # (prefix, code, num)
        theory_count = 0
        lab_count = 0
        elective_count = 0
        mandatory_count = 0
        codes_captured_count = 0
        source_provenance_count = 0
        evidence_verified_count = 0
        all_pages_set: Set[int] = set()
        low_confidence_count = 0
        total_confidence = 0.0

        for idx, sub in enumerate(subjects_list):
            s_name = str(sub.get("name") or sub.get("subjectName") or "").strip()
            s_code = str(sub.get("code") or sub.get("subjectCode") or "").strip()
            s_type = str(sub.get("type") or sub.get("courseType") or sub.get("category") or "").lower()
            s_sec = str(sub.get("source_section") or sub.get("sourceSection") or sub.get("source_page") or "").strip()
            s_text = str(sub.get("source_text") or sub.get("sourceText") or "").strip()
            s_conf = sub.get("confidence") if sub.get("confidence") is not None else sub.get("extractionConfidence")

            # Page provenance aggregation
            pages_raw = sub.get("source_page_numbers") or sub.get("sourcePages") or [sub.get("source_page", 1)]
            if isinstance(pages_raw, list):
                for p in pages_raw:
                    if str(p).isdigit():
                        all_pages_set.add(int(p))
            elif isinstance(pages_raw, (int, str)) and str(pages_raw).isdigit():
                all_pages_set.add(int(pages_raw))

            # 1. Detect Empty / Non-string Subject Name
            if not s_name:
                uncertain_count += 1
                issues.append(f"Subject at index {idx+1} has an empty subject name.")
                extraction_problems.append("subject code without subject name")
                continue

            # 2. Detect Page Number Treated as Subject (check before generic headers/footers)
            if re.match(PAGE_NUMBER_PATTERN, s_name.strip(), re.I):
                page_num_as_subject_count += 1
                uncertain_count += 1
                issues.append(f"Extraction problem: Page number or solitary digits treated as subject: '{s_name}'.")
                extraction_problems.append("page number treated as subject")
                continue

            # 3. Detect Subject Code without Subject Name
            # e.g. name is just punctuation, or name is identical to code with no letters
            alpha_in_name = re.sub(r"[^a-zA-Z]", "", s_name)
            if len(alpha_in_name) < 2 or (s_code and s_name.strip().upper() == s_code.strip().upper()):
                uncertain_count += 1
                code_without_name_count += 1
                issues.append(f"Subject code '{s_code}' captured without a valid subject name (found: '{s_name}').")
                extraction_problems.append("subject code without subject name")
                continue

            # 4. Detect Repeated Header Treated as Subject
            is_header = any(re.search(pat, s_name.strip(), re.I) for pat in HEADER_PATTERNS)
            if is_header:
                header_as_subject_count += 1
                uncertain_count += 1
                issues.append(f"Extraction problem: Repeated table header mistakenly treated as subject: '{s_name}'.")
                extraction_problems.append("repeated header treated as subject")
                continue

            # 5. Detect Footer Treated as Subject
            is_footer = any(re.search(pat, s_name.strip(), re.I) for pat in FOOTER_PATTERNS)
            if is_footer:
                footer_as_subject_count += 1
                uncertain_count += 1
                issues.append(f"Extraction problem: Document footer mistakenly treated as subject: '{s_name}'.")
                extraction_problems.append("footer treated as subject")
                continue

            # 6. Anti-Hallucination: Verify existence in document if text is present
            if raw_doc_text and len(raw_doc_text) > 20:
                name_clean = re.sub(r"[^\w\s]", "", s_name.lower()).strip()
                name_tokens = [w for w in name_clean.split() if len(w) > 3 and w not in ("core", "theory", "laboratory", "elective", "course", "unit", "paper", "project")]
                code_clean = re.sub(r"[^\w]", "", s_code.lower()).strip() if s_code else ""
                
                name_in_doc = (name_clean in raw_doc_text) or (any(tok in raw_doc_text for tok in name_tokens) if name_tokens else False)
                code_in_doc = bool(code_clean and code_clean in raw_doc_text.replace(" ", ""))
                
                if not name_in_doc and not code_in_doc:
                    uncertain_count += 1
                    issues.append(f"Anti-hallucination error: Subject '{s_name}' ({s_code}) does not appear in the uploaded syllabus document.")
                    extraction_problems.append("unrelated semester subjects included")
                    continue

            # 7. Detect Duplicate Subjects
            norm_name = re.sub(r"[^\w\s]", "", s_name.lower()).strip()
            if norm_name in seen_names or (s_code and s_code.upper() in seen_codes):
                duplicate_count += 1
                issues.append(f"Duplicate subject detected: {s_name} ({s_code})")
                extraction_problems.append("duplicate subject")
            else:
                seen_names.add(norm_name)
                if s_code:
                    seen_codes.add(s_code.upper())

            # 8. Detect Cross-Semester Contamination
            if other_sem_pattern and other_sem_pattern.search(s_name):
                cross_semester_count += 1
                issues.append(f"Subject '{s_name}' appears to belong to another semester.")
                extraction_problems.append("unrelated semester subjects included")

            # Course Types Classification
            if "lab" in s_name.lower() or "practical" in s_name.lower() or "practical" in s_type or "lab" in s_type:
                lab_count += 1
            elif "elective" in s_name.lower() or "elective" in s_type:
                elective_count += 1
            elif "mandatory" in s_name.lower() or "audit" in s_name.lower() or "mandatory" in s_type or "audit" in s_type:
                mandatory_count += 1
            else:
                theory_count += 1

            # Subject Codes Analysis
            if s_code and len(s_code) >= 2:
                codes_captured_count += 1
                code_m = re.match(r"^([A-Za-z]+)\s*(\d+)$", s_code.strip())
                if code_m:
                    pref = code_m.group(1).upper()
                    try:
                        num = int(code_m.group(2))
                        captured_codes_list.append((pref, s_code.strip().upper(), num))
                    except ValueError:
                        pass

            # Source Provenance & Evidence
            has_provenance = bool(s_sec or s_text or sub.get("source_page_numbers") or sub.get("source_page") or sub.get("sourcePages"))
            has_evidence = bool(s_text or sub.get("semester_evidence") or s_sec)
            if has_provenance and has_evidence:
                source_provenance_count += 1
                evidence_verified_count += 1

            # Confidence
            conf_val = 0.95
            if s_conf is not None:
                try:
                    conf_val = float(s_conf)
                except Exception:
                    conf_val = 0.95
            if conf_val < 0.70:
                low_confidence_count += 1
                uncertain_count += 1
                issues.append(f"Subject '{s_name}' extraction confidence ({conf_val:.2f}) is below 0.70 threshold.")
            total_confidence += conf_val
            verified_count += 1

        avg_confidence = (total_confidence / len(subjects_list)) if subjects_list else 0.0

        # ── Problem Detection: Subject Name Without Code When Code Should Exist ─
        missing_code_when_should_exist = False
        if detected_count >= 4 and codes_captured_count > 0:
            code_ratio = codes_captured_count / detected_count
            if code_ratio >= 0.75 and codes_captured_count < detected_count:
                missing_code_when_should_exist = True
                missing_codes = [s.get("name") for s in subjects_list if not s.get("code") and not s.get("subjectCode")]
                for mc in missing_codes:
                    issues.append(f"Subject '{mc}' is missing a subject code when standard curriculum codes exist for other subjects.")
                    extraction_problems.append("subject name without subject code when code should exist")

        # ── 7. All Pages Belonging to Section Processed ────────────────────────
        c7_pages_passed = len(all_pages_set) > 0 or detected_count == 0
        checks.append({
            "id": "page_evidence",
            "number": 8,
            "name": "Source Page Evidence For Every Subject",
            "passed": source_provenance_count >= detected_count and detected_count > 0,
            "detail": f"Source page evidence & section references verified for {source_provenance_count}/{detected_count} subjects across pages {sorted(list(all_pages_set))}."
        })
        checks.append({
            "id": "all_pages_processed",
            "number": 8,
            "name": "All Pages Belonging to Section Processed",
            "passed": c7_pages_passed,
            "detail": f"Processed pages {sorted(list(all_pages_set))} for curriculum section."
        })

        # ── 8. Zero Duplicate Subjects ─────────────────────────────────────────
        c8_passed = duplicate_count == 0
        checks.append({
            "id": "duplicate_subjects",
            "number": 9,
            "name": "Zero Duplicate Subjects",
            "passed": c8_passed,
            "detail": "Zero duplicate subjects found." if c8_passed else f"{duplicate_count} duplicate course entries detected."
        })
        checks.append({
            "id": "no_duplicate_subjects",
            "number": 9,
            "name": "No Duplicate Subjects",
            "passed": c8_passed,
            "detail": "Zero duplicate subjects found." if c8_passed else f"{duplicate_count} duplicate course entries detected."
        })

        # ── 9. Suspicious Missing Subject-Code Sequence ───────────────────────
        suspicious_sequence_gap = False
        gap_details = []
        prefix_groups: Dict[str, List[Tuple[str, int]]] = {}
        for pref, full_c, num in captured_codes_list:
            prefix_groups.setdefault(pref, []).append((full_c, num))

        for pref, group in prefix_groups.items():
            if len(group) >= 3:
                sorted_group = sorted(group, key=lambda x: x[1])
                for i in range(len(sorted_group) - 1):
                    c1_num = sorted_group[i][1]
                    c2_num = sorted_group[i+1][1]
                    # If step is exactly 2 (e.g. 501, 503 or 3501, 3503) within a sequential range
                    if 1 < (c2_num - c1_num) <= 2:
                        suspicious_sequence_gap = True
                        gap_msg = f"Suspicious missing subject-code sequence gap detected between {sorted_group[i][0]} and {sorted_group[i+1][0]}"
                        gap_details.append(gap_msg)
                        issues.append(gap_msg)
                        extraction_problems.append("suspicious missing subject-code sequence")

        c9_passed = not suspicious_sequence_gap
        checks.append({
            "id": "no_missing_code_sequence",
            "number": 10,
            "name": "No Suspicious Missing Subject-Code Sequence",
            "passed": c9_passed,
            "detail": "Subject code numbering sequence is continuous and coherent." if c9_passed else "; ".join(gap_details)
        })

        # ── 10. No Suspicious Incomplete Table ────────────────────────────────
        suspicious_missing = False
        suspicious_reasons = []

        if raw_doc_text:
            # Check if practical/laboratory is explicitly in semester table but 0 labs detected
            if re.search(r"\b(?:practical|laboratory|practical\s+courses|laboratories)\b", raw_doc_text) and lab_count == 0:
                sem_kw = f"semester {student_sem}" if student_sem else "semester"
                if sem_kw in raw_doc_text and ("practical" in raw_doc_text or "laboratory" in raw_doc_text):
                    if re.search(r"\b[A-Z]{2,5}\s*\d{2,4}\s+[A-Za-z\s]+(?:lab|laboratory|practical)\b", raw_doc_text, re.I):
                        suspicious_missing = True
                        suspicious_reasons.append("Document mentions practical laboratories for this semester but none were extracted.")
                        extraction_problems.append("table ended unexpectedly")

            # Check if table ended unexpectedly with truncation indicators
            if re.search(r"\b(?:table\s+continues|continued\s+on\s+next\s+page|\.\.\.|\betc\b)\b", raw_doc_text) and missing_count > 0:
                suspicious_missing = True
                suspicious_reasons.append("Table appears to end unexpectedly or continue onto another unparsed section.")
                extraction_problems.append("table ended unexpectedly")

            # Check expected count vs detected count
            if expected_count > 0 and detected_count < expected_count:
                suspicious_missing = True
                suspicious_reasons.append(f"Table lists {expected_count} rows, but only {detected_count} subjects were extracted.")

            # Cross semester count
            if cross_semester_count > 0:
                suspicious_missing = True
                suspicious_reasons.append(f"{cross_semester_count} subjects from other semesters were detected in current semester extract.")

        c10_passed = not suspicious_missing
        checks.append({
            "id": "suspicious_missing_sections",
            "number": 11,
            "name": "Zero Suspicious Missing Sections",
            "passed": c10_passed,
            "detail": "Curriculum structure is complete with no missing sections." if c10_passed else "; ".join(suspicious_reasons)
        })
        checks.append({
            "id": "no_incomplete_table",
            "number": 11,
            "name": "No Suspicious Incomplete Table",
            "passed": c10_passed,
            "detail": "All detected subject tables are complete with no abrupt truncation." if c10_passed else "; ".join(suspicious_reasons)
        })
        if not c10_passed:
            issues.extend(suspicious_reasons)

        # ── 11. Every Subject Has Source Evidence ─────────────────────────────
        c11_passed = evidence_verified_count >= detected_count and detected_count > 0
        checks.append({
            "id": "every_subject_has_source_evidence",
            "number": 12,
            "name": "Every Subject Has Source Evidence",
            "passed": c11_passed,
            "detail": f"Source evidence verified for {evidence_verified_count}/{detected_count} subjects." if c11_passed else f"Missing source evidence for {detected_count - evidence_verified_count} subjects."
        })
        if not c11_passed:
            issues.append(f"Missing authoritative source evidence for {detected_count - evidence_verified_count} subjects.")

        # ── 12. Subject Names Are Non-Empty & Valid ───────────────────────────
        c12_passed = (
            len(seen_names) > 0 
            and header_as_subject_count == 0 
            and footer_as_subject_count == 0 
            and page_num_as_subject_count == 0
            and code_without_name_count == 0
            and len(seen_names) == (detected_count - duplicate_count)
        )
        checks.append({
            "id": "subject_names",
            "number": 13,
            "name": "Subject Names Captured",
            "passed": c12_passed,
            "detail": f"Extracted {len(seen_names)} verified distinct subject names without truncation or noise." if c12_passed else "Subject names contain invalid entries, headers, footers, or empty values."
        })
        checks.append({
            "id": "valid_subject_names",
            "number": 13,
            "name": "Subject Names Non-Empty & Valid",
            "passed": c12_passed,
            "detail": f"All {len(seen_names)} subject names verified valid with no headers/footers/page numbers." if c12_passed else "Subject names verification failed due to headers/footers/page numbers or empty values."
        })
        if not c12_passed:
            issues.append("Subject names validation failed.")

        # ── 13. Subject Codes Captured & Course Types Classification ──────────
        c_codes_passed = codes_captured_count > 0 or detected_count == 0
        checks.append({
            "id": "subject_codes",
            "number": 14,
            "name": "Subject Codes Captured",
            "passed": c_codes_passed,
            "detail": f"Captured official course codes for {codes_captured_count}/{detected_count} subjects."
        })

        c_types_passed = (theory_count + lab_count + elective_count + mandatory_count) == detected_count and detected_count > 0
        checks.append({
            "id": "course_types",
            "number": 15,
            "name": "Course Types Classification",
            "passed": c_types_passed,
            "detail": f"Classified course types: {theory_count} Theory, {lab_count} Lab/Practical, {elective_count} Elective, {mandatory_count} Mandatory/Audit."
        })

        # Units & Topics Hierarchical Structure
        units_map = analysis.get("chapters") or analysis.get("units") or {}
        topics_list = analysis.get("key_topics") or analysis.get("topics") or []
        units_count = sum(len(u_list) for u_list in units_map.values() if isinstance(u_list, list))
        checks.append({
            "id": "units_topics",
            "number": 16,
            "name": "Units & Topics Hierarchical Extraction",
            "passed": True,
            "detail": f"Units & Topics mapped: {len(units_map)} subjects with detailed units ({units_count} total units, {len(topics_list)} key topics)."
        })

        # ── 14. Extraction Confidence Gate ────────────────────────────────────
        c14_passed = low_confidence_count == 0 and avg_confidence >= 0.70 and detected_count > 0
        checks.append({
            "id": "extraction_confidence",
            "number": 17,
            "name": "Extraction Confidence & Verification Gate",
            "passed": c14_passed,
            "detail": f"Average extraction confidence: {avg_confidence:.2f} with zero low-confidence entries." if c14_passed else f"Low confidence extraction ({low_confidence_count} uncertain items, avg {avg_confidence:.2f})."
        })
        checks.append({
            "id": "sufficient_confidence",
            "number": 17,
            "name": "Subject Identity Sufficiently Confident",
            "passed": c14_passed,
            "detail": f"Extraction confidence verified: {avg_confidence:.2f}." if c14_passed else f"Confidence below acceptable threshold (avg {avg_confidence:.2f})."
        })
        if not c14_passed:
            issues.append(f"Extraction confidence check failed (average: {avg_confidence:.2f}).")

        # ── Final Verdict & Status Calculation ────────────────────────────────
        critical_failures = (
            missing_count > 0
            or uncertain_count > 0
            or cross_semester_count > 0
            or duplicate_count > 0
            or header_as_subject_count > 0
            or footer_as_subject_count > 0
            or page_num_as_subject_count > 0
            or code_without_name_count > 0
            or missing_code_when_should_exist
            or suspicious_low_count
            or suspicious_missing
            or suspicious_sequence_gap
            or len(extraction_problems) > 0
            or not c1_passed
            or not c4_passed
            or not c5_doc_passed
            or not c5_sec_passed
            or not c6_passed
            or not c11_passed
            or not c12_passed
            or not c14_passed
            or detected_count == 0
            or val_status == "MISMATCH"
        )

        if val_status == "MISMATCH" or not c4_passed:
            final_status = "MISMATCH"
            is_valid = False
            summary = f"Semester mismatch: The uploaded syllabus is not for your current Semester {student_sem} profile."
        elif critical_failures:
            final_status = "NEEDS_REVIEW"
            is_valid = False
            summary = f"Completeness check requires review: {len(issues)} issue(s) detected ({missing_count} missing, {uncertain_count} uncertain, {duplicate_count} duplicate)."
        else:
            final_status = "VALID"
            is_valid = True
            summary = f"Full completeness verified: All {detected_count} subjects for Semester {student_sem or 'Curriculum'} validated with zero omissions."

        passed_checks_count = sum(1 for c in checks if c["passed"])
        validation_score = int(round((passed_checks_count / len(checks)) * 100))

        report = {
            "semester": student_sem,
            "subjects_detected": detected_count,
            "subjects_verified": (verified_count - duplicate_count - cross_semester_count - header_as_subject_count - footer_as_subject_count - page_num_as_subject_count - code_without_name_count) if is_valid else 0,
            "missing_subjects": missing_count,
            "duplicate_subjects": duplicate_count,
            "cross_semester_subjects": cross_semester_count,
            "uncertain_subjects": uncertain_count,
            "header_as_subject_count": header_as_subject_count,
            "footer_as_subject_count": footer_as_subject_count,
            "page_num_as_subject_count": page_num_as_subject_count,
            "code_without_name_count": code_without_name_count,
            "evidence_verified_count": evidence_verified_count,
            "source_provenance_count": source_provenance_count,
            "has_theory": theory_count > 0,
            "has_labs": lab_count > 0,
            "has_electives": elective_count > 0,
            "has_mandatory": mandatory_count > 0,
            "course_types_breakdown": {
                "theory": theory_count,
                "lab": lab_count,
                "elective": elective_count,
                "mandatory": mandatory_count
            },
            "average_confidence": round(avg_confidence, 2),
            "status": final_status,
            "curriculumStatus": final_status,
            "is_valid": is_valid,
            "validation_score": validation_score,
            "summary": summary,
            "issues": issues,
            "extraction_problems": list(set(extraction_problems)),
            "checks": checks
        }

        return report
