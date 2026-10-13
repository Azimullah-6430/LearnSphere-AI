"""
LearnSphere AI - Student Roster Parser
Parses student rosters from Excel (.xlsx, .xls), CSV (.csv), Word (.docx), PDF (.pdf), and manual text.
Extracts student names, roll numbers, identifiers, emails, and sections.
Performs header detection, whitespace normalization, duplicate checks, and confidence scoring.
"""

import os
import re
import csv
import io
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Maximum file size: 10 MB
MAX_ROSTER_FILE_SIZE = 10 * 1024 * 1024

SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".tsv", ".txt", ".docx", ".pdf"}

# Header normalization tokens
HEADER_PATTERNS = {
    "rollNo": [
        "student id", "student_id", "studentid", "roll no", "roll no.", "roll_no", "rollno",
        "roll number", "roll_number", "roll", "reg no", "reg no.", "reg_no", "regno",
        "register no", "register number", "registration no", "registration number", "rrn",
        "admission no", "adm no", "enrollment no", "enrollment number",
        "hall ticket no", "usn", "matric no", "roll_num", "student_code", "id", "code"
    ],
    "email": [
        "student email", "email address", "email id", "email_id", "email", "e-mail",
        "contact email", "mail"
    ],
    "section": [
        "class section", "section", "sec", "division", "div", "batch", "group"
    ],
    "serial": [
        "serial number", "serial no", "s.no", "sno", "sl.no", "sl no", "sr.no", "sr no",
        "no.", "no", "#"
    ],
    "name": [
        "student name", "student_name", "studentname", "name of student", "name of the student",
        "candidate name", "full name", "full_name", "fullname", "pupil name", "learner name",
        "scholars name", "name", "student"
    ]
}

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
GENERAL_EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

# Non-student noise row detection (e.g., summary rows in school sheets)
NOISE_ROW_PATTERNS = [
    r"^total\b", r"^count\b", r"^boys\b", r"^girls\b", r"^present\b", r"^absent\b",
    r"^signature\b", r"^teacher\b", r"^principal\b", r"^date\b", r"^page\s+\d+"
]


def clean_cell_text(val: Any) -> str:
    """Normalize text: strip excess whitespace while preserving legitimate spaces/initials."""
    if val is None:
        return ""
    text = str(val).strip()
    # Collapse multiple whitespace characters into single space
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def normalize_student_name(raw_name: str) -> str:
    """Clean student name, removing leading numeric bullets while preserving legitimate names."""
    cleaned = clean_cell_text(raw_name)
    # Remove leading numbering if present, e.g. "1. John Doe" or "12) Priya Sharma" or "3 - Alex"
    cleaned = re.sub(r"^\d+[\.\)\-\:]\s*", "", cleaned)
    # Collapse internal spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def is_noise_row(row_cells: List[str]) -> bool:
    """Check if row contains total, count, or signature metadata instead of student data."""
    combined = " ".join(c.lower() for c in row_cells).strip()
    if not combined:
        return True
    for pat in NOISE_ROW_PATTERNS:
        if re.search(pat, combined):
            return True
    return False


def match_header_column(header_cell: str) -> Optional[str]:
    """Map a column header string to one of: name, rollNo, email, section, serial."""
    norm = re.sub(r"[^a-zA-Z0-9\s]", " ", header_cell.lower()).strip()
    norm = re.sub(r"\s+", " ", norm)

    # 1. Exact match check first across all patterns
    for field, variations in HEADER_PATTERNS.items():
        if norm in variations:
            return field

    # 2. Multi-word prefix/suffix with specific fields checked before generic 'name'
    for field in ["rollNo", "email", "section", "serial", "name"]:
        for var in HEADER_PATTERNS[field]:
            if norm == var or norm.startswith(var + " ") or norm.endswith(" " + var):
                return field
    return None


def detect_table_structure(rows: List[List[str]]) -> Tuple[int, Dict[str, int]]:
    """
    Detect the header row index and column mappings.
    Returns: (header_row_index, {'name': col_idx, 'rollNo': col_idx, ...})
    """
    best_header_idx = -1
    best_mapping: Dict[str, int] = {}
    best_score = 0

    # Search through the first 10 rows for candidate headers
    for idx in range(min(10, len(rows))):
        row = [clean_cell_text(c) for c in rows[idx]]
        mapping: Dict[str, int] = {}
        matched_fields = set()

        for col_idx, cell in enumerate(row):
            field = match_header_column(cell)
            if field and field not in mapping:
                mapping[field] = col_idx
                matched_fields.add(field)

        score = 0
        if "name" in mapping:
            score += 10
        if "rollNo" in mapping:
            score += 8
        if "email" in mapping:
            score += 5
        if "section" in mapping:
            score += 4
        if "serial" in mapping:
            score += 2

        if score > best_score and "name" in mapping:
            best_score = score
            best_header_idx = idx
            best_mapping = mapping

    # If no explicit header row was identified, infer columns by analyzing data patterns
    if best_header_idx == -1 or "name" not in best_mapping:
        best_header_idx = -1
        inferred_mapping = _infer_columns_from_data(rows)
        return (best_header_idx, inferred_mapping)

    return (best_header_idx, best_mapping)


def _infer_columns_from_data(rows: List[List[str]]) -> Dict[str, int]:
    """Heuristically infer columns when no clear header row exists."""
    mapping: Dict[str, int] = {}
    if not rows:
        return mapping

    # Check non-empty sample rows
    sample_rows = [r for r in rows if any(c.strip() for c in r)][:10]
    if not sample_rows:
        return mapping

    num_cols = max(len(r) for r in sample_rows)
    col_scores: Dict[int, Dict[str, int]] = {
        i: {"name": 0, "rollNo": 0, "email": 0, "section": 0, "serial": 0}
        for i in range(num_cols)
    }

    for r in sample_rows:
        for c_idx, cell in enumerate(r):
            text = clean_cell_text(cell)
            if not text:
                continue

            if EMAIL_REGEX.match(text):
                col_scores[c_idx]["email"] += 5
            elif re.match(r"^\d{1,3}$", text):
                col_scores[c_idx]["serial"] += 2
                col_scores[c_idx]["rollNo"] += 1
            elif re.match(r"^[A-Za-z0-9\-_/]{2,18}$", text) and any(ch.isdigit() for ch in text):
                col_scores[c_idx]["rollNo"] += 4
            elif re.match(r"^[A-Za-z\s\.\']{3,50}$", text) and " " in text:
                col_scores[c_idx]["name"] += 4
            elif re.match(r"^[A-Za-z]{1,3}$", text):
                col_scores[c_idx]["section"] += 3

    # Pick best column for name
    name_col = max(col_scores.keys(), key=lambda i: col_scores[i]["name"], default=None)
    if name_col is not None and col_scores[name_col]["name"] > 0:
        mapping["name"] = name_col

    # Pick rollNo
    for i in col_scores:
        if i != name_col and col_scores[i]["rollNo"] > 0:
            if "rollNo" not in mapping or col_scores[i]["rollNo"] > col_scores[mapping["rollNo"]]["rollNo"]:
                mapping["rollNo"] = i

    # Pick email
    for i in col_scores:
        if i not in mapping.values() and col_scores[i]["email"] > 0:
            mapping["email"] = i

    # Pick section
    for i in col_scores:
        if i not in mapping.values() and col_scores[i]["section"] > 0:
            mapping["section"] = i

    # Default fallback: if 2 columns and no mapping found, col 0 is rollNo, col 1 is name
    if "name" not in mapping and num_cols >= 2:
        mapping["rollNo"] = 0
        mapping["name"] = 1
    elif "name" not in mapping and num_cols == 1:
        mapping["name"] = 0

    return mapping


def _extract_from_csv(file_bytes: bytes) -> List[List[str]]:
    """Parse CSV / TSV text handling varied encodings and delimiters."""
    raw_str = ""
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            raw_str = file_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if not raw_str:
        raw_str = file_bytes.decode("utf-8", errors="ignore")

    lines = raw_str.splitlines()
    if not lines:
        return []

    # Detect delimiter
    sample = "\n".join(lines[:10])
    delimiter = ","
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except Exception:
        if "\t" in lines[0] and "," not in lines[0]:
            delimiter = "\t"
        elif ";" in lines[0] and "," not in lines[0]:
            delimiter = ";"
        elif "|" in lines[0] and "," not in lines[0]:
            delimiter = "|"

    reader = csv.reader(lines, delimiter=delimiter)
    return [[clean_cell_text(cell) for cell in row] for row in reader]


def _extract_from_excel(file_bytes: bytes, filename: str) -> List[List[str]]:
    """Parse Excel spreadsheets (.xlsx, .xls) extracting cell strings."""
    rows: List[List[str]] = []
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".xlsx":
        try:
            import openpyxl
            wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), data_only=True, read_only=True)
            sheet = wb.active
            for row in sheet.iter_rows(values_only=True):
                if row and any(c is not None and str(c).strip() for c in row):
                    rows.append([clean_cell_text(c) for c in row])
            wb.close()
            return rows
        except Exception as e:
            logger.warning(f"[RosterParser] openpyxl extraction error: {e}")

    # Fallback for .xls or if openpyxl failed
    try:
        import xlrd
        book = xlrd.open_workbook(file_contents=file_bytes)
        sheet = book.sheet_by_index(0)
        for r_idx in range(sheet.nrows):
            row = sheet.row_values(r_idx)
            rows.append([clean_cell_text(c) for c in row])
        return rows
    except Exception as e:
        logger.warning(f"[RosterParser] xlrd extraction error: {e}")

    # Fallback: attempt to treat as CSV
    try:
        return _extract_from_csv(file_bytes)
    except Exception:
        return []


def _extract_from_docx(file_bytes: bytes) -> List[List[str]]:
    """Parse Word documents (.docx) extracting tables and bulleted lists."""
    rows: List[List[str]] = []
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))

        # 1. Process all tables in doc
        for table in doc.tables:
            for row in table.rows:
                cells = [clean_cell_text(cell.text) for cell in row.cells]
                # Avoid duplicate cells resulting from merged headers
                deduped = []
                for c in cells:
                    if not deduped or c != deduped[-1]:
                        deduped.append(c)
                if any(deduped):
                    rows.append(deduped)

        # 2. If no table rows found, extract paragraphs (simple numbered / name list)
        if not rows:
            for p in doc.paragraphs:
                txt = clean_cell_text(p.text)
                if txt:
                    # If line has tab or comma separator, split it
                    if "\t" in txt:
                        rows.append([clean_cell_text(x) for x in txt.split("\t")])
                    elif "," in txt:
                        rows.append([clean_cell_text(x) for x in txt.split(",")])
                    else:
                        rows.append([txt])

    except Exception as e:
        logger.warning(f"[RosterParser] docx extraction error: {e}")

    return rows


def _extract_from_pdf(file_bytes: bytes) -> Tuple[List[List[str]], bool]:
    """
    Parse PDF documents using PyMuPDF (fitz).
    Handles multi-page tables, text columns, and identifies scanned PDFs.
    Returns: (rows, is_scanned)
    """
    rows: List[List[str]] = []
    is_scanned = False

    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        total_text_chars = 0

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text() or ""
            total_text_chars += len(text.strip())

            # Attempt structured table extraction if available
            table_found_on_page = False
            if hasattr(page, "find_tables"):
                try:
                    tables = page.find_tables()
                    for t in tables:
                        extracted = t.extract()
                        if extracted:
                            table_found_on_page = True
                            for r in extracted:
                                if any(clean_cell_text(c) for c in r):
                                    rows.append([clean_cell_text(c) for c in r])
                except Exception as tbl_err:
                    logger.debug(f"[RosterParser] PyMuPDF table extract note: {tbl_err}")

            # If no table extracted, fall back to layout blocks / line extraction
            if not table_found_on_page:
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                for line in lines:
                    if "\t" in line:
                        rows.append([clean_cell_text(x) for x in line.split("\t") if clean_cell_text(x)])
                    elif "," in line:
                        rows.append([clean_cell_text(x) for x in line.split(",") if clean_cell_text(x)])
                    elif re.search(r"\s{2,}", line):
                        cols = [clean_cell_text(x) for x in re.split(r"\s{2,}", line) if clean_cell_text(x)]
                        if cols:
                            rows.append(cols)
                    else:
                        m = re.match(r"^([A-Za-z0-9\-_/]{2,15})\s+(.+)$", line)
                        if m:
                            rows.append([clean_cell_text(m.group(1)), clean_cell_text(m.group(2))])
                        else:
                            rows.append([line])

        doc.close()

        # If very little text was found across all pages, document is likely scanned
        if total_text_chars < 30 and len(rows) < 2:
            is_scanned = True

    except Exception as e:
        logger.warning(f"[RosterParser] PyMuPDF extraction error: {e}")

    return rows, is_scanned


def _attempt_scanned_pdf_ocr(file_bytes: bytes) -> Tuple[List[List[str]], bool, str]:
    """
    Attempt OCR on scanned PDF pages when available, or flag for manual review.
    Returns: (rows, success, message)
    """
    rows: List[List[str]] = []
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        # Check pytesseract binary
        import pytesseract
        from PIL import Image

        for page_idx in range(min(5, len(doc))):
            page = doc[page_idx]
            pix = page.get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            page_text = pytesseract.image_to_string(img)
            for line in page_text.splitlines():
                line = clean_cell_text(line)
                if line:
                    if "\t" in line:
                        rows.append([clean_cell_text(x) for x in line.split("\t")])
                    elif "," in line:
                        rows.append([clean_cell_text(x) for x in line.split(",")])
                    else:
                        rows.append([line])
        doc.close()
        if rows:
            return rows, True, "OCR completed with local Tesseract engine."
    except Exception as ocr_err:
        logger.info(f"[RosterParser] Local Tesseract OCR unavailable: {ocr_err}")

    return [], False, "Scanned document detected with low extraction confidence. Please review or enter students manually."


def process_raw_table_to_roster(
    rows: List[List[str]],
    is_scanned: bool = False,
    low_confidence_msg: str = ""
) -> Dict[str, Any]:
    """
    Converts raw table rows into structured, validated student records.
    Detects headers, associates fields, normalizes names, checks duplicates.
    """
    if not rows:
        return {
            "success": True,
            "detected_fields": [],
            "students": [],
            "summary": {
                "total": 0,
                "valid": 0,
                "warnings": 0,
                "duplicates": 0,
                "low_confidence": is_scanned,
                "confidence_message": low_confidence_msg or ("No student entries found in document." if not is_scanned else "Scanned document detected.")
            }
        }

    header_idx, col_map = detect_table_structure(rows)
    name_col = col_map.get("name")
    roll_col = col_map.get("rollNo")
    email_col = col_map.get("email")
    sec_col = col_map.get("section")
    serial_col = col_map.get("serial")

    detected_fields = []
    if name_col is not None:
        detected_fields.append("name")
    if roll_col is not None:
        detected_fields.append("rollNo")
    if email_col is not None:
        detected_fields.append("email")
    if sec_col is not None:
        detected_fields.append("section")

    start_idx = header_idx + 1 if header_idx >= 0 else 0
    extracted_students: List[Dict[str, Any]] = []

    seen_rolls: Dict[str, int] = {}
    seen_emails: Dict[str, int] = {}
    seen_names: Dict[str, int] = {}

    row_counter = 0

    for idx in range(start_idx, len(rows)):
        raw_row = rows[idx]
        if not raw_row or not any(raw_row):
            continue

        if is_noise_row(raw_row):
            continue

        # Check if row is a repeated header row (multi-page tables)
        if any(match_header_column(c) == "name" for c in raw_row):
            continue

        # Extract values according to mapped columns
        student_name = ""
        roll_no = ""
        email = ""
        section = ""

        if name_col is not None and name_col < len(raw_row):
            student_name = normalize_student_name(raw_row[name_col])

        if roll_col is not None and roll_col < len(raw_row):
            roll_no = clean_cell_text(raw_row[roll_col])

        if email_col is not None and email_col < len(raw_row):
            email = clean_cell_text(raw_row[email_col])

        if sec_col is not None and sec_col < len(raw_row):
            section = clean_cell_text(raw_row[sec_col])

        # If name is still empty, attempt to extract from unmapped cells
        if not student_name:
            for c_idx, cell in enumerate(raw_row):
                if c_idx not in (roll_col, email_col, sec_col, serial_col):
                    cleaned = normalize_student_name(cell)
                    if cleaned and not cleaned.isdigit() and len(cleaned) >= 2:
                        student_name = cleaned
                        break

        # If roll_no was not found, check if an alphanumeric token exists in any cell
        if not roll_no:
            for c_idx, cell in enumerate(raw_row):
                if c_idx != name_col and c_idx != email_col:
                    t = clean_cell_text(cell)
                    if re.match(r"^[A-Za-z0-9\-_/]{2,15}$", t) and t.lower() != student_name.lower():
                        roll_no = t
                        break

        # Check for email inside raw row if missing
        if not email:
            for cell in raw_row:
                m_email = GENERAL_EMAIL_REGEX.search(cell)
                if m_email:
                    email = m_email.group(0).strip()
                    break

        # Discard empty rows
        if not student_name and not roll_no and not email:
            continue

        row_counter += 1
        issues: List[str] = []
        status = "valid"

        # Validate Name
        if not student_name or len(student_name) < 2:
            status = "needs_correction"
            issues.append("Missing or invalid student name")
        elif not any(c.isalpha() for c in student_name):
            status = "needs_correction"
            issues.append("Student name must contain letters")

        # Validate Email format if present
        if email and not EMAIL_REGEX.match(email):
            issues.append(f"Invalid email format: {email}")
            if status != "needs_correction":
                status = "warning"

        # Duplicate Checks using reliable identifiers first
        is_dup = False
        if roll_no:
            norm_roll = roll_no.lower()
            if norm_roll in seen_rolls:
                is_dup = True
                issues.append(f"Duplicate Roll No/ID '{roll_no}' (first seen at row {seen_rolls[norm_roll]})")
            else:
                seen_rolls[norm_roll] = row_counter

        if email:
            norm_email = email.lower()
            if norm_email in seen_emails:
                is_dup = True
                issues.append(f"Duplicate Email '{email}' (first seen at row {seen_emails[norm_email]})")
            else:
                seen_emails[norm_email] = row_counter

        if student_name:
            norm_name = student_name.lower()
            if norm_name in seen_names and not roll_no and not email:
                is_dup = True
                issues.append(f"Duplicate name '{student_name}' without unique identifier")
            elif norm_name in seen_names:
                issues.append(f"Same name '{student_name}' repeated with different identifier: please verify")
            else:
                seen_names[norm_name] = row_counter

        if is_dup:
            status = "warning"

        extracted_students.append({
            "temp_id": f"row_{row_counter}",
            "order": row_counter,
            "name": student_name,
            "rollNo": roll_no,
            "email": email,
            "section": section,
            "status": status,
            "issues": issues
        })

    valid_count = sum(1 for s in extracted_students if s["status"] == "valid")
    warning_count = sum(1 for s in extracted_students if s["status"] == "warning")
    correction_count = sum(1 for s in extracted_students if s["status"] == "needs_correction")
    dup_count = sum(1 for s in extracted_students if any("Duplicate" in iss for iss in s["issues"]))

    confidence_msg = ""
    if is_scanned:
        confidence_msg = low_confidence_msg or "Scanned document detected. Please review extracted rows carefully before confirming."
    elif correction_count > 0:
        confidence_msg = f"{correction_count} row(s) require manual correction."

    duplicate_rows = [
        {"name": s["name"], "rollNo": s.get("rollNo") or "", "email": s.get("email") or "", "row_index": s["order"]}
        for s in extracted_students if any("Duplicate" in iss for iss in s.get("issues", []))
    ]

    return {
        "success": True,
        "detected_fields": detected_fields,
        "students": extracted_students,
        "duplicates": duplicate_rows,
        "low_confidence": is_scanned,
        "low_confidence_reason": confidence_msg,
        "summary": {
            "total": len(extracted_students),
            "valid": valid_count,
            "warnings": warning_count,
            "needs_correction": correction_count,
            "duplicates": dup_count,
            "low_confidence": is_scanned,
            "confidence_message": confidence_msg
        }
    }


def find_roster_duplicates(students: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect duplicate rows within a list of student records."""
    duplicates: List[Dict[str, Any]] = []
    seen_rolls: Dict[str, int] = {}
    seen_emails: Dict[str, int] = {}

    for idx, s in enumerate(students, start=1):
        roll = (s.get("rollNo") or s.get("roll_number") or "").strip().lower()
        email = (s.get("email") or "").strip().lower()
        is_dup = False
        matched_idx = None

        if roll:
            if roll in seen_rolls:
                is_dup = True
                matched_idx = seen_rolls[roll]
            else:
                seen_rolls[roll] = idx

        if email and not is_dup:
            if email in seen_emails:
                is_dup = True
                matched_idx = seen_emails[email]
            else:
                seen_emails[email] = idx

        if is_dup:
            duplicates.append({
                "row_index": idx,
                "matches_row": matched_idx,
                "name": s.get("name", ""),
                "rollNo": s.get("rollNo") or s.get("roll_number") or "",
                "email": s.get("email") or ""
            })

    return duplicates


def parse_roster_file(file_input: Any, filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entry point for parsing uploaded roster files.
    Accepts either raw bytes or a local file path.
    Validates file size, file extension, and routes to appropriate parser.
    """
    if isinstance(file_input, (str, os.PathLike)):
        if not filename:
            filename = os.path.basename(file_input)
        with open(file_input, "rb") as f:
            file_bytes = f.read()
    elif hasattr(file_input, "read"):
        file_bytes = file_input.read()
    else:
        file_bytes = bytes(file_input)

    filename = filename or "unnamed_roster"

    if len(file_bytes) > MAX_ROSTER_FILE_SIZE:
        return {
            "success": False,
            "error": f"File exceeds maximum allowed size of {MAX_ROSTER_FILE_SIZE // (1024 * 1024)}MB."
        }

    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return {
            "success": False,
            "error": f"Unsupported file type '{ext}'. Supported formats: .xlsx, .xls, .csv, .docx, .pdf, .txt."
        }

    try:
        if ext in (".csv", ".tsv", ".txt"):
            rows = _extract_from_csv(file_bytes)
            return process_raw_table_to_roster(rows, is_scanned=False)

        elif ext in (".xlsx", ".xls"):
            rows = _extract_from_excel(file_bytes, filename)
            return process_raw_table_to_roster(rows, is_scanned=False)

        elif ext == ".docx":
            rows = _extract_from_docx(file_bytes)
            return process_raw_table_to_roster(rows, is_scanned=False)

        elif ext == ".pdf":
            rows, is_scanned = _extract_from_pdf(file_bytes)
            low_msg = ""
            if is_scanned:
                ocr_rows, ocr_ok, ocr_msg = _attempt_scanned_pdf_ocr(file_bytes)
                if ocr_ok and ocr_rows:
                    rows = ocr_rows
                    low_msg = ocr_msg
                else:
                    low_msg = ocr_msg
            return process_raw_table_to_roster(rows, is_scanned=is_scanned, low_confidence_msg=low_msg)

        else:
            return {"success": False, "error": f"Parser for {ext} not implemented."}

    except Exception as exc:
        logger.error(f"[RosterParser] Exception parsing {filename}: {exc}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to parse file: {str(exc)}"
        }


def parse_manual_roster_text(raw_text: str) -> Dict[str, Any]:
    """Parse manual text entry / pasted roster lines."""
    if not raw_text or not raw_text.strip():
        return {
            "success": True,
            "detected_fields": [],
            "students": [],
            "summary": {"total": 0, "valid": 0, "warnings": 0, "needs_correction": 0, "duplicates": 0, "low_confidence": False}
        }

    lines = raw_text.splitlines()
    rows: List[List[str]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "\t" in line:
            rows.append([clean_cell_text(x) for x in line.split("\t") if clean_cell_text(x)])
        elif "," in line:
            rows.append([clean_cell_text(x) for x in line.split(",") if clean_cell_text(x)])
        elif ";" in line:
            rows.append([clean_cell_text(x) for x in line.split(";") if clean_cell_text(x)])
        elif "|" in line:
            rows.append([clean_cell_text(x) for x in line.split("|") if clean_cell_text(x)])
        elif re.search(r"\s{2,}", line):
            cols = [clean_cell_text(x) for x in re.split(r"\s{2,}", line) if clean_cell_text(x)]
            if cols:
                rows.append(cols)
        else:
            m = re.match(r"^([A-Za-z0-9\-_/]{2,15})\s+(.+)$", line)
            if m:
                rows.append([clean_cell_text(m.group(1)), clean_cell_text(m.group(2))])
            else:
                rows.append([line])

    return process_raw_table_to_roster(rows, is_scanned=False)
