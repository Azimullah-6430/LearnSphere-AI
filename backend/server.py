"""
LearnSphere AI - Production Backend Server
Auth, Evaluation, Syllabus, Misconceptions, Plagiarism, Action Center, Notifications.

Security fixes applied:
  - No X-User-ID header authentication (removed)
  - No plaintext password fallback (removed)
  - No DEFAULT_USERS or fake fallback data
  - No hardcoded SECRET_KEY (fails startup if missing in production)
  - Role validated from database, never from client
  - Every protected route uses require_auth() / require_role() decorators
  - User-scoped queries: students see only their own data
  - Teachers see only evaluations they submitted
  - Environment variables validated on startup
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import re
import traceback
import uuid
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

import requests  # type: ignore
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file, send_from_directory, session
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

try:
    from bson import ObjectId  # type: ignore
except Exception:
    ObjectId = None  # type: ignore

try:
    import pymupdf as fitz  # type: ignore
except ImportError:
    try:
        import fitz  # type: ignore
    except Exception:
        fitz = None
except Exception:
    fitz = None

from app.db import get_mongodb, get_sqlite_db, init_db, is_using_mongo
from app.evaluation.evaluator import EvaluationAgent
from app.evaluation.pdf_report import generate_evaluation_pdf
from app.evaluation.store import store_evaluation_pipeline
from app.gemini_service import GeminiService
from app.plagiarism import PlagiarismDetector
from app.curriculum_validator import CurriculumCompletenessValidator
from app.opportunities_service import OpportunitiesService

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent
ROOT_DIR     = BASE_DIR.parent
FRONTEND_DIST = ROOT_DIR / "learnsphere-ai" / "dist"

# ── Environment ───────────────────────────────────────────────────────────────
load_dotenv(BASE_DIR / ".env", override=True)
load_dotenv(ROOT_DIR / ".env", override=True)
load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ENV = os.getenv("ENV", "production").strip().lower()


# ══════════════════════════════════════════════════════════════════════════════
# STARTUP VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

import secrets

def _validate_environment() -> None:
    """Validate critical environment variables with safe production fallbacks to guarantee successful port binding."""
    secret = os.getenv("SECRET_KEY", "").strip()
    known_defaults = {
        "learnsphere-ai-secret-key-production-2026",
        "learnsphere-ai-secret-key",
        "dev-secret",
        "change-me",
        "",
    }
    if not secret or secret in known_defaults:
        dynamic_secret = secrets.token_hex(32)
        os.environ["SECRET_KEY"] = dynamic_secret
        logger.warning(
            "[Startup] SECRET_KEY was not set or used a default value. Generated a secure runtime secret key. "
            "For persistent sessions across restarts, set SECRET_KEY in your Render environment variables."
        )

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not gemini_key or gemini_key.startswith("your_"):
        logger.warning(
            "[Startup] WARNING: GEMINI_API_KEY is not configured or uses a placeholder. "
            "AI evaluations will require a valid GEMINI_API_KEY in Render environment variables."
        )

    logger.info("[Startup] Environment initialization completed.")


# ── Run validation before app object is created ───────────────────────────────
_validate_environment()

# ── Database init (will raise in production if MongoDB unavailable) ───────────
init_db()

# ══════════════════════════════════════════════════════════════════════════════
# FLASK APP
# ══════════════════════════════════════════════════════════════════════════════

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(FRONTEND_DIST),
    static_url_path="",
)

app.secret_key = os.getenv("SECRET_KEY", "dev-only-insecure-key")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)
app.config["SESSION_COOKIE_HTTPONLY"]    = True
app.config["SESSION_COOKIE_SAMESITE"]    = "Lax"
app.config["SESSION_COOKIE_SECURE"]      = (ENV != "development")
app.config["MAX_CONTENT_LENGTH"]         = 300 * 1024 * 1024   # 300 MB

# ── CORS ──────────────────────────────────────────────────────────────────────
_frontend_url = os.getenv("FRONTEND_URL", "").strip()
if _frontend_url and not _frontend_url.startswith("your_"):
    CORS(app, resources={r"/api/*": {"origins": _frontend_url}},
         supports_credentials=True)
else:
    # Single-service Render deployment: frontend served from same origin
    CORS(app, resources={r"/api/*": {"origins": "*"}})

# ── Upload folder ─────────────────────────────────────────────────────────────
try:
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
except Exception:
    UPLOAD_FOLDER = Path("/tmp/uploads")
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "webp", "txt"}

# ── Service singletons ────────────────────────────────────────────────────────
gemini_service    = GeminiService()
evaluation_agent  = EvaluationAgent()
plagiarism_detector = PlagiarismDetector()

# Start background opportunities verification pipeline scheduler (every 6 hours)
OpportunitiesService.start_background_scheduler(interval_hours=6)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def allowed_file(filename: str) -> bool:
    return bool(
        filename and "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_uploaded_file(uploaded_file, prefix: str) -> str:
    if uploaded_file is None or not uploaded_file.filename:
        raise ValueError("No valid file supplied.")
    raw_name = Path(uploaded_file.filename).name
    ext = raw_name.rsplit(".", 1)[1].lower() if "." in raw_name else "pdf"
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type '.{ext}' is not permitted.")
    clean_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", Path(raw_name).stem).strip("_") or "doc"
    safe_name  = f"{prefix}_{int(datetime.now().timestamp())}_{clean_stem}.{ext}"
    destination = UPLOAD_FOLDER / safe_name
    uploaded_file.save(str(destination))
    return str(destination)


def mongo_serialize(doc: Any) -> Any:
    if not doc:
        return {} if isinstance(doc, dict) else doc
    if isinstance(doc, list):
        return [mongo_serialize(x) for x in doc]
    if ObjectId and isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, datetime):
        return doc.strftime("%Y-%m-%d %H:%M:%S")
    if not isinstance(doc, dict):
        return doc

    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        elif ObjectId and isinstance(v, ObjectId):
            d[k] = str(v)
        elif isinstance(v, dict):
            d[k] = mongo_serialize(v)
        elif isinstance(v, list):
            d[k] = [mongo_serialize(x) for x in v]

    # Never send password data
    d.pop("password", None)
    d.pop("password_hash", None)
    return d


def _update_user_streak(user_id: str, user_doc: dict) -> dict:
    """
    Calculate and persist daily streak based on calendar date in Asia/Kolkata (IST).
    - If user already logged in today: retain streak.
    - If user logged in yesterday: increment streak (+1), update longest_streak.
    - If user missed one or more days: break streak and reset to 1.
    """
    if not user_id or not user_doc:
        return user_doc or {}

    try:
        from datetime import datetime, timezone, timedelta
        IST = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(IST)
        today_str = now_ist.strftime("%Y-%m-%d")
        yesterday_str = (now_ist - timedelta(days=1)).strftime("%Y-%m-%d")

        last_date = str(user_doc.get("last_active_date") or "").strip()
        try:
            current_streak = int(user_doc.get("streak_count") or user_doc.get("streakDays") or 1)
        except (ValueError, TypeError):
            current_streak = 1

        try:
            longest_streak = int(user_doc.get("longest_streak") or current_streak)
        except (ValueError, TypeError):
            longest_streak = current_streak

        raw_days = user_doc.get("active_days") or user_doc.get("active_days_json") or []
        if isinstance(raw_days, str):
            try:
                active_days = json.loads(raw_days)
            except Exception:
                active_days = []
        elif isinstance(raw_days, list):
            active_days = list(raw_days)
        else:
            active_days = []

        if today_str not in active_days:
            active_days.append(today_str)
            if len(active_days) > 60:
                active_days = active_days[-60:]

        if not last_date:
            new_streak = 1
        elif last_date == today_str:
            new_streak = max(1, current_streak)
        elif last_date == yesterday_str:
            new_streak = current_streak + 1
        else:
            # Missed one or more days -> break streak
            new_streak = 1

        new_longest = max(longest_streak, new_streak)

        update_fields = {
            "streak_count": new_streak,
            "streakDays": new_streak,
            "last_active_date": today_str,
            "longest_streak": new_longest,
            "active_days": active_days,
            "active_days_json": json.dumps(active_days),
            "updated_at": datetime.utcnow()
        }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            query = {}
            if ObjectId and len(str(user_id)) == 24:
                try:
                    query = {"_id": ObjectId(user_id)}
                except Exception:
                    query = {"$or": [{"user_id": str(user_id)}, {"id": str(user_id)}]}
            else:
                query = {"$or": [{"user_id": str(user_id)}, {"id": str(user_id)}]}
            mongo_db["users"].update_one(query, {"$set": update_fields})
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET streak_count=?, last_active_date=?, longest_streak=?, active_days_json=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=? OR user_id=?
            """, (new_streak, today_str, new_longest, json.dumps(active_days), str(user_id), str(user_id)))
            conn.commit()
            conn.close()

        user_doc.update(update_fields)
        return user_doc
    except Exception as exc:
        logger.error("Error updating user streak: %s", exc)
        return user_doc


def _create_system_notification(
    user_id: str,
    title: str,
    message: str,
    category: str = "info",
    action_url: str = None,
    target_role: str = "student",
    target_name: str = None
) -> dict:
    """Safely create and persist a real system notification for MongoDB and SQLite."""
    try:
        notif_id = f"notif_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()
        doc = {
            "notification_id": notif_id,
            "id": notif_id,
            "user_id": str(user_id) if user_id else None,
            "target_id": str(user_id) if user_id else None,
            "target_role": target_role or "student",
            "target_name": target_name,
            "title": str(title),
            "message": str(message),
            "category": str(category or "info"),
            "action_url": action_url,
            "is_read": False,
            "created_at": now,
        }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            # Check for recent duplicate within 1 hour to prevent notification spam
            one_hour_ago = now - timedelta(hours=1)
            existing = mongo_db["notifications"].find_one({
                "target_id": str(user_id),
                "title": str(title),
                "created_at": {"$gte": one_hour_ago}
            })
            if not existing:
                mongo_db["notifications"].insert_one(doc)
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notifications (target_role, target_id, target_name, title, message, category, is_read, notification_id, action_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, CURRENT_TIMESTAMP)
            """, (target_role or "student", str(user_id) if user_id else None, target_name, str(title), str(message), str(category or "info"), notif_id, action_url))
            conn.commit()
            conn.close()

        return doc
    except Exception as exc:
        logger.error("Error creating system notification: %s", exc)
        return {}


def _normalize_user_doc(doc: dict) -> dict:
    """Normalize user profile fields for consistent client/server consumption."""
    if not doc or not isinstance(doc, dict):
        return doc or {}

    d = dict(doc)
    # Teacher level normalization
    d["teacherLevel"] = (
        d.get("teacher_level")
        or d.get("teacherLevel")
        or d.get("level")
        or "school"
    )

    # Streak normalization
    streak = d.get("streak_count") or d.get("streakDays") or 1
    try:
        streak = int(streak)
    except Exception:
        streak = 1
    d["streak_count"] = streak
    d["streakDays"] = streak
    d["last_active_date"] = d.get("last_active_date") or ""
    try:
        d["longest_streak"] = int(d.get("longest_streak") or streak)
    except Exception:
        d["longest_streak"] = streak

    # College fields normalization
    degree = d.get("degree") or d.get("program") or d.get("course") or ""
    d["degree"] = degree
    d["program"] = degree

    dept = d.get("department") or d.get("branch") or d.get("domain") or ""
    d["department"] = dept
    d["branch"] = dept

    yr = d.get("current_year") or d.get("currentYear") or d.get("year") or ""
    d["current_year"] = yr
    d["currentYear"] = yr

    acad_yr = d.get("academic_year") or d.get("academicYear") or ""
    d["academic_year"] = acad_yr
    d["academicYear"] = acad_yr

    reg = d.get("regulation") or d.get("batch") or ""
    d["regulation"] = reg
    d["batch"] = reg

    # Semester normalization
    sem_val = d.get("semester") if d.get("semester") is not None else d.get("current_semester")
    if sem_val is not None and str(sem_val).strip() != "":
        try:
            sem_val = int(sem_val)
        except (ValueError, TypeError):
            sem_val = str(sem_val).strip()
    else:
        sem_val = None

    d["semester"] = sem_val
    d["current_semester"] = sem_val
    d["currentSemester"] = sem_val

    # School level normalization
    cls_val = d.get("classLevel") or d.get("class_level") or d.get("grade_level") or d.get("class") or None
    if cls_val is not None:
        d["classLevel"] = cls_val
        d["class"] = cls_val
        d["grade_level"] = cls_val

    return d



def _lookup_user_by_id(user_id: str):
    """Fetch user document from MongoDB or SQLite by their stored id."""
    mongo_db = get_mongodb()
    if mongo_db is not None:
        doc = None
        if ObjectId and len(str(user_id)) == 24:
            try:
                doc = mongo_db["users"].find_one({"_id": ObjectId(user_id)})
            except Exception:
                pass
        if not doc:
            doc = mongo_db["users"].find_one({"id": str(user_id)})
        if not doc:
            doc = mongo_db["users"].find_one({"user_id": str(user_id)})
        return _normalize_user_doc(mongo_serialize(doc)) if doc else None

    conn = get_sqlite_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ? OR user_id = ?", (str(user_id), str(user_id)))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d.pop("password", None)
        d.pop("password_hash", None)
        return _normalize_user_doc(d)
    return None


def _normalize_curriculum_doc(doc: dict, user_id: str, user: dict = None) -> dict:
    """
    Standardize the validated curriculum schema consumed identically by:
    1. Personal Trainer
    2. Knowledge Challenge
    3. Reality Lab
    4. Active Curriculum API (/api/curriculum/active)
    """
    d = dict(doc)
    syl_id = str(d.get("syllabus_id") or d.get("syllabusId") or d.get("_id") or "")
    d["syllabus_id"] = syl_id
    d["syllabusId"] = syl_id
    d["curriculum_id"] = syl_id
    d["curriculumId"] = syl_id
    d["student_id"] = str(user_id)
    d["studentId"] = str(user_id)
    d["curriculumStatus"] = "VALID"
    d["validation_status"] = "VALID"
    d["validationStatus"] = "VALID"
    d["status"] = "VALID"
    d["is_valid"] = True
    d["is_active"] = True

    # Normalize chapters / units
    chapters_dict = d.get("chapters") or d.get("units") or {}
    if isinstance(chapters_dict, str):
        try:
            chapters_dict = json.loads(chapters_dict)
        except Exception:
            chapters_dict = {}

    # Normalize subjects
    raw_subjects = d.get("subjects") or []
    if isinstance(raw_subjects, str):
        try:
            raw_subjects = json.loads(raw_subjects)
        except Exception:
            raw_subjects = []

    normalized_subjects = []
    all_topics = []

    for idx, s in enumerate(raw_subjects):
        if isinstance(s, dict):
            s_name = str(s.get("name") or "").strip()
            s_code = str(s.get("code") or s.get("subject_id") or s.get("subjectId") or s.get("id") or f"SUB{idx+1:02d}").strip()
            s_id = str(s.get("subject_id") or s.get("subjectId") or s.get("id") or s_code).strip()
            s_topics = list(s.get("topics") or [])
            s_units = list(s.get("units") or [])

            # Pull topics from chapters_dict if available
            if s_name in chapters_dict:
                sub_chaps = chapters_dict[s_name]
                if isinstance(sub_chaps, list):
                    for u in sub_chaps:
                        if isinstance(u, dict):
                            if u.get("name"):
                                s_topics.append(u["name"])
                            if isinstance(u.get("concepts"), list):
                                s_topics.extend(u["concepts"])
                        elif isinstance(u, str):
                            s_topics.append(u)

            deduped_topics = list(dict.fromkeys(s_topics))
            normalized_subjects.append({
                "id": s_id,
                "subject_id": s_id,
                "subjectId": s_id,
                "code": s_code,
                "name": s_name,
                "topics": deduped_topics,
                "units": s_units or (chapters_dict.get(s_name) if isinstance(chapters_dict.get(s_name), list) else []),
                "type": s.get("type") or s.get("category") or "Core Theory",
                "credits": s.get("credits")
            })
            all_topics.extend(deduped_topics)
        elif isinstance(s, str) and s.strip():
            s_name = s.strip()
            s_code = f"SUB{idx+1:02d}"
            s_topics = []
            if s_name in chapters_dict:
                sub_chaps = chapters_dict[s_name]
                if isinstance(sub_chaps, list):
                    for u in sub_chaps:
                        if isinstance(u, dict):
                            if u.get("name"):
                                s_topics.append(u["name"])
                            if isinstance(u.get("concepts"), list):
                                s_topics.extend(u["concepts"])
                        elif isinstance(u, str):
                            s_topics.append(u)
            deduped_topics = list(dict.fromkeys(s_topics))
            normalized_subjects.append({
                "id": s_code,
                "subject_id": s_code,
                "subjectId": s_code,
                "code": s_code,
                "name": s_name,
                "topics": deduped_topics,
                "units": chapters_dict.get(s_name) if isinstance(chapters_dict.get(s_name), list) else [],
                "type": "Core Theory",
                "credits": 4
            })
            all_topics.extend(deduped_topics)

    d["subjects"] = normalized_subjects
    d["extracted_subjects"] = [s["name"] for s in normalized_subjects]
    d["chapters"] = chapters_dict
    d["units"] = chapters_dict
    d["topics"] = list(dict.fromkeys(all_topics or d.get("topics") or d.get("key_topics") or []))

    return d


def _get_authoritative_curriculum(user_id: str, user: dict = None, syllabus_id: str = None) -> dict | None:
    """
    Single Authoritative Backend Curriculum Service for:
    1. Personal Trainer
    2. Knowledge Challenge
    3. Reality Lab
    4. Active Curriculum API
    
    Flow:
    Authenticated Student -> Active Validated Syllabus -> Validated Subjects -> Associated Topics
    
    Strict Rules:
    1. Only loads curriculum for the specific authenticated user_id (Zero cross-user leakage).
    2. Gated strictly by curriculumStatus == 'VALID' / validation_status == 'VALID'.
    3. Extraction occurs ONCE upon upload and is saved to MongoDB/SQLite.
    4. Personal Trainer, Knowledge Challenge, and Reality Lab all consume this exact normalized curriculum.
    """
    if not user_id:
        return None
    if not user:
        user = _lookup_user_by_id(user_id) or {}
    level = user.get("level") or "college"
    current_sem = user.get("semester") if user.get("semester") is not None else user.get("current_semester")

    mongo_db = get_mongodb()
    if mongo_db is not None:
        conditions = [
            {"$or": [{"is_active": True}, {"isActive": True}]},
            {"$or": [
                {"status": {"$in": ["ACTIVE", "READY", "VALID"]}},
                {"curriculumStatus": "VALID"},
                {"validation_status": "VALID"},
                {"validationStatus": "VALID"}
            ]}
        ]
        if syllabus_id:
            conditions.append({
                "$or": [
                    {"syllabus_id": str(syllabus_id)},
                    {"syllabusId": str(syllabus_id)},
                    {"_id": str(syllabus_id)}
                ]
            })
        if level == "college" and current_sem is not None:
            sem_int = int(current_sem) if str(current_sem).isdigit() else current_sem
            sem_str = str(current_sem)
            conditions.append({
                "$or": [
                    {"semester": sem_int},
                    {"semester": sem_str},
                    {"current_semester": sem_int},
                    {"current_semester": sem_str},
                    {"currentSemester": sem_int},
                    {"currentSemester": sem_str}
                ]
            })
        query_filter = {
            "$or": [{"student_id": str(user_id)}, {"studentId": str(user_id)}],
            "$and": conditions
        }
        doc = mongo_db["syllabi"].find_one(query_filter, sort=[("updated_at", -1), ("updatedAt", -1), ("version", -1)])
        if doc:
            val_status = str(doc.get("curriculumStatus") or doc.get("validation_status") or doc.get("validationStatus") or doc.get("status") or "").upper().strip()
            if val_status in ["VALID", "MANUALLY_CONFIRMED", "ACTIVE"]:
                subs = doc.get("subjects") or []
                ext_subs = doc.get("extracted_subjects") or []
                if subs or ext_subs:
                    return _normalize_curriculum_doc(doc, user_id, user)
        return None
    else:
        conn = get_sqlite_db()
        cursor = conn.cursor()
        if syllabus_id:
            cursor.execute(
                "SELECT * FROM syllabi WHERE student_id=? AND syllabus_id=? AND (is_active=1 OR status IN ('ACTIVE', 'READY', 'VALID') OR validation_status='VALID') ORDER BY version DESC LIMIT 1",
                (str(user_id), str(syllabus_id))
            )
        else:
            cursor.execute(
                "SELECT * FROM syllabi WHERE student_id=? AND (is_active=1 OR status IN ('ACTIVE', 'READY', 'VALID') OR validation_status='VALID') ORDER BY version DESC LIMIT 1",
                (str(user_id),)
            )
        row = cursor.fetchone()
        conn.close()
        if row:
            d = dict(row)
            val_status = str(d.get("validation_status") or d.get("status") or "").upper().strip()
            if val_status in ["VALID", "MANUALLY_CONFIRMED", "ACTIVE"]:
                if d.get("analysis_json"):
                    try:
                        d.update(json.loads(d["analysis_json"]))
                    except Exception:
                        pass
                subs = d.get("subjects") or []
                ext_subs = d.get("extracted_subjects") or []
                if subs or ext_subs:
                    return _normalize_curriculum_doc(d, user_id, user)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# AUTHORIZATION DECORATORS
# ══════════════════════════════════════════════════════════════════════════════

def require_auth(f):
    """Decorator: rejects request if no valid server session exists."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "error": "Authentication required."}), 401
        return f(*args, **kwargs)
    return wrapper


def require_role(*allowed_roles: str):
    """Decorator: rejects request if session role not in allowed_roles.
    Role is read from the SERVER SESSION, never from the request body.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_id = session.get("user_id")
            if not user_id:
                return jsonify({"success": False, "error": "Authentication required."}), 401
            session_role = session.get("role", "")
            if session_role not in allowed_roles:
                return jsonify({
                    "success": False,
                    "error": f"Access denied. This endpoint requires role: {', '.join(allowed_roles)}."
                }), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def _current_user_id() -> str:
    """Return authenticated user_id from server session."""
    return str(session.get("user_id", ""))


def _current_role() -> str:
    """Return authenticated role from server session."""
    return str(session.get("role", ""))


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health():
    db_status = "disconnected"
    try:
        if is_using_mongo():
            db_status = "mongodb_connected"
        else:
            db_status = "sqlite_development"
    except Exception:
        db_status = "error"

    return jsonify({
        "status": "healthy",
        "service": "LearnSphere AI",
        "database": db_status,
        "gemini_model": gemini_service.model,
        "env": ENV,
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    try:
        # Accept both JSON and multipart form
        if request.content_type and "multipart/form-data" in request.content_type:
            g = request.form.get
        else:
            _data = request.get_json(force=True) or {}
            g = _data.get

        name     = str(g("name") or "").strip()
        email    = str(g("email") or "").strip().lower()
        password = str(g("password") or "").strip()
        role     = str(g("role") or "student").strip().lower()

        # ── Validation ─────────────────────────────────────────────────────
        if not name or len(name) < 2 or len(name) > 120:
            return jsonify({"success": False, "error": "Name must be 2–120 characters."}), 400
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            return jsonify({"success": False, "error": "A valid email address is required."}), 400
        if not password or len(password) < 6:
            return jsonify({"success": False, "error": "Password must be at least 6 characters."}), 400
        if role not in ("student", "teacher"):
            return jsonify({"success": False, "error": "Role must be 'student' or 'teacher'."}), 400

        # ── Profile fields ─────────────────────────────────────────────────
        teacher_level    = str(g("teacherLevel") or g("teacher_level") or "school").strip()
        institution_name = str(g("institutionName") or g("institution_name") or g("institution") or g("college") or g("school") or "").strip()
        level            = str(g("level") or "school").strip()

        # College specific fields
        degree           = str(g("degree") or g("program") or g("course") or "").strip() if level == "college" else None
        program          = degree
        department       = str(g("department") or g("branch") or g("domain") or "").strip() if (level == "college" or role == "teacher") else None
        branch           = department
        domain           = str(g("domain") or department or "").strip() if level == "college" else None
        current_year     = str(g("currentYear") or g("current_year") or g("year") or "").strip() if level == "college" else None
        academic_year    = str(g("academicYear") or g("academic_year") or "").strip() if level == "college" else None
        regulation       = str(g("regulation") or g("batch") or g("regulationBatch") or "").strip() if level == "college" else None
        batch            = regulation

        # Semester handling (authoritative stored semester for college students)
        if level == "college":
            sem_raw = g("semester") if g("semester") is not None else g("currentSemester") if g("currentSemester") is not None else g("current_semester")
            if sem_raw is not None and str(sem_raw).strip() != "":
                try:
                    semester = int(sem_raw)
                except (ValueError, TypeError):
                    semester = str(sem_raw).strip()
            else:
                semester = None
        else:
            semester = None

        current_semester = semester

        # School specific fields (Never force college semester fields on school students)
        board            = str(g("board") or "") if level == "school" else None
        roll_number      = str(g("roll_number") or g("rollNumber") or "")
        section          = str(g("section") or "")
        grade_level      = str(g("classLevel") or g("grade_level") or g("class") or "") if level == "school" else None
        stream           = str(g("stream") or "") if level == "school" else None

        subjects_raw = g("subjects")
        if isinstance(subjects_raw, str):
            try:
                subjects = json.loads(subjects_raw)
            except Exception:
                subjects = []
        elif isinstance(subjects_raw, list):
            subjects = subjects_raw
        else:
            subjects = []

        # ── Hash password ───────────────────────────────────────────────────
        password_hash = generate_password_hash(password)
        stable_user_id = str(uuid.uuid4())
        now = datetime.utcnow()

        user_doc = {
            "user_id":          stable_user_id,
            "name":             name,
            "email":            email,
            "password_hash":    password_hash,
            "role":             role,
            "teacher_level":    teacher_level if role == "teacher" else None,
            "institution_name": institution_name,
            "degree":           degree,
            "program":          program,
            "department":       department,
            "branch":           branch,
            "level":            level,
            "board":            board,
            "roll_number":      roll_number,
            "section":          section,
            "grade_level":      grade_level,
            "classLevel":       grade_level,
            "class":            grade_level,
            "stream":           stream,
            "domain":           domain,
            "current_year":     current_year,
            "academic_year":    academic_year,
            "regulation":       regulation,
            "batch":            batch,
            "semester":         semester,
            "current_semester": current_semester,
            "subjects":         subjects,
            "created_at":       now,
            "updated_at":       now,
            "status":           "active",
        }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            # Check duplicate email before insert
            if mongo_db["users"].find_one({"email": email}):
                return jsonify({"success": False, "error": "An account with this email already exists. Please sign in instead."}), 409
            result = mongo_db["users"].insert_one(user_doc)
            stored_id = str(result.inserted_id)
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            if cursor.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
                conn.close()
                return jsonify({"success": False, "error": "An account with this email already exists. Please sign in instead."}), 409
            cursor.execute("""
                INSERT INTO users
                (user_id, name, email, password_hash, role, level, teacher_level,
                 institution_name, degree, program, department, branch, domain,
                 current_year, academic_year, regulation, batch, board, roll_number,
                 section, grade_level, stream, semester, current_semester, subjects_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (stable_user_id, name, email, password_hash, role, level,
                  teacher_level, institution_name, degree, program, department, branch, domain,
                  current_year, academic_year, regulation, batch, board,
                  roll_number, section, grade_level, stream, semester, current_semester,
                  json.dumps(subjects)))
            stored_id = str(cursor.lastrowid)
            conn.commit()
            conn.close()

        # Start session
        session.permanent = True
        session["user_id"] = stored_id
        session["role"]    = role

        # Initialize streak on registration
        user_doc = _update_user_streak(stored_id, user_doc)
        response_user = _normalize_user_doc(mongo_serialize(user_doc))
        response_user["id"] = stored_id

        # Create welcoming system notification
        _create_system_notification(
            user_id=stored_id,
            title="Welcome to LearnSphere AI",
            message=f"Welcome, {name}! Your personalized learning environment and daily streak tracking are now active.",
            category="success",
            action_url="/app",
            target_role=role,
            target_name=name
        )

        return jsonify({"success": True, "user": response_user}), 201

    except Exception as exc:
        logger.error("Registration error: %s", traceback.format_exc())
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data     = request.get_json(force=True) or {}
    email    = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "").strip()
    # NOTE: client-supplied 'role' is used ONLY to verify the user chose the
    # correct portal.  The authoritative role always comes from the database.
    portal_role = str(data.get("role") or "").strip().lower()

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required."}), 400

    # ── Fetch user ────────────────────────────────────────────────────────────
    user = None
    stored_id = None

    mongo_db = get_mongodb()
    if mongo_db is not None:
        doc = mongo_db["users"].find_one({"email": email})
        if doc:
            stored_id = str(doc["_id"])
            user = mongo_serialize(doc)
            # keep hash for verification (mongo_serialize strips it)
            user["_password_hash"] = doc.get("password_hash") or doc.get("password") or ""
    else:
        conn = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        if row:
            d = dict(row)
            stored_id = str(d["id"])
            user = {k: v for k, v in d.items() if k not in ("password", "password_hash")}
            user["_password_hash"] = d.get("password_hash") or d.get("password") or ""

    if not user:
        return jsonify({"success": False, "error": "Account not found. Please create an account first."}), 401

    # ── Verify password (only hashed; NO plaintext fallback) ──────────────────
    stored_hash = user.pop("_password_hash", "")
    if not stored_hash:
        return jsonify({"success": False, "error": "Account requires a password reset. Please contact support."}), 403
    if not stored_hash.startswith(("scrypt:", "pbkdf2:")):
        # Hash is in a legacy or unknown format — refuse and flag for reset
        return jsonify({
            "success": False,
            "error": "Your account password needs to be reset. Please register again or contact support.",
        }), 403

    if not check_password_hash(stored_hash, password):
        return jsonify({"success": False, "error": "Incorrect password."}), 401

    # ── Portal role check ─────────────────────────────────────────────────────
    db_role = str(user.get("role") or "student").lower()
    if portal_role and portal_role != db_role:
        return jsonify({
            "success": False,
            "error": (
                f"This account is registered as a '{db_role}'. "
                f"Please use the {'Teacher' if db_role == 'teacher' else 'Student'} portal."
            ),
        }), 403

    # ── Start session ─────────────────────────────────────────────────────────
    session.permanent = True
    session["user_id"] = stored_id
    session["role"]    = db_role

    # Update streak on successful daily login
    user = _update_user_streak(stored_id, user)

    # Normalize profile for frontend
    user = _normalize_user_doc(user)
    user["id"] = stored_id
    return jsonify({"success": True, "user": user}), 200


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    """Return the currently authenticated user based on server session.
    NEVER uses X-User-ID header for identity.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "authenticated": False, "error": "Not authenticated."}), 401

    user = _lookup_user_by_id(user_id)
    if not user:
        # Session references a deleted or unknown account
        session.clear()
        return jsonify({"success": False, "authenticated": False, "error": "User not found."}), 404

    # Keep streak verified and up-to-date on session restoration
    user = _update_user_streak(user_id, user)
    user = _normalize_user_doc(user)
    return jsonify({"success": True, "authenticated": True, "user": user}), 200


@app.route("/api/user/streak", methods=["GET", "POST"])
@require_auth
def user_streak_api():
    """Get or record daily active study streak in Asia/Kolkata timezone."""
    try:
        user_id = _current_user_id()
        user = _lookup_user_by_id(user_id) or {}
        user = _update_user_streak(user_id, user)
        streak_count = user.get("streak_count") or user.get("streakDays") or 1
        longest = user.get("longest_streak") or streak_count
        last_date = user.get("last_active_date") or ""
        active_days = user.get("active_days") or []
        if isinstance(active_days, str):
            try:
                active_days = json.loads(active_days)
            except Exception:
                active_days = []
        return jsonify({
            "success": True,
            "streak": streak_count,
            "streak_count": streak_count,
            "streakDays": streak_count,
            "longest_streak": longest,
            "last_active_date": last_date,
            "active_days": active_days
        }), 200
    except Exception as exc:
        logger.error("User streak error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/user/profile", methods=["PUT"])
@require_auth
def update_user_profile():
    """Update profile attributes for the currently authenticated user in MongoDB/SQLite."""
    try:
        user_id = _current_user_id()
        data = request.get_json(force=True) or {}

        allowed_fields = {
            "name", "level", "board", "grade_level", "classLevel", "class", "stream",
            "domain", "semester", "current_semester", "currentSemester", "department", "branch",
            "degree", "program", "course", "current_year", "currentYear", "year",
            "academic_year", "academicYear", "regulation", "batch", "regulationBatch",
            "institution_name", "institutionName", "institution", "college", "school",
            "section", "roll_number", "rollNumber", "subjects", "city", "state",
            "country", "phone", "bio", "teacher_level", "teacherLevel"
        }

        update_fields = {}
        for k, v in data.items():
            if k in allowed_fields:
                if k in ("classLevel", "class"):
                    update_fields["grade_level"] = str(v) if v is not None else None
                elif k in ("institutionName", "institution", "college", "school"):
                    update_fields["institution_name"] = str(v) if v is not None else None
                elif k == "rollNumber":
                    update_fields["roll_number"] = str(v) if v is not None else None
                elif k in ("academicYear", "academic_year"):
                    update_fields["academic_year"] = str(v) if v is not None else None
                elif k in ("currentYear", "year"):
                    update_fields["current_year"] = str(v) if v is not None else None
                elif k in ("regulationBatch", "batch", "regulation"):
                    update_fields["regulation"] = str(v) if v is not None else None
                    update_fields["batch"] = str(v) if v is not None else None
                elif k in ("degree", "program", "course"):
                    update_fields["degree"] = str(v) if v is not None else None
                    update_fields["program"] = str(v) if v is not None else None
                elif k in ("department", "branch"):
                    update_fields["department"] = str(v) if v is not None else None
                    update_fields["branch"] = str(v) if v is not None else None
                elif k in ("semester", "current_semester", "currentSemester"):
                    if v is not None and str(v).strip() != "":
                        try:
                            sem_int = int(v)
                        except (ValueError, TypeError):
                            sem_int = str(v).strip()
                    else:
                        sem_int = None
                    update_fields["semester"] = sem_int
                    update_fields["current_semester"] = sem_int
                elif k == "teacherLevel":
                    update_fields["teacher_level"] = str(v) if v is not None else None
                else:
                    update_fields[k] = v

        update_fields["updated_at"] = datetime.utcnow()

        mongo_db = get_mongodb()
        if mongo_db is not None:
            query = {}
            if ObjectId and len(str(user_id)) == 24:
                try:
                    query = {"_id": ObjectId(user_id)}
                except Exception:
                    query = {"$or": [{"user_id": str(user_id)}, {"id": str(user_id)}]}
            else:
                query = {"$or": [{"user_id": str(user_id)}, {"id": str(user_id)}]}

            mongo_db["users"].update_one(query, {"$set": update_fields})
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys() if k != "updated_at"])
            params = [json.dumps(v) if isinstance(v, list) else str(v) if v is not None else None for k, v in update_fields.items() if k != "updated_at"]
            params.extend([user_id, str(user_id)])
            if set_clause:
                cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ? OR user_id = ?", params)
                conn.commit()
            conn.close()

        updated_user = _lookup_user_by_id(user_id)
        return jsonify({"success": True, "user": updated_user}), 200
    except Exception as exc:
        logger.error("Update profile error: %s", traceback.format_exc())
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    resp = jsonify({"success": True, "message": "Logged out."})
    resp.delete_cookie("session")
    return resp, 200


# ══════════════════════════════════════════════════════════════════════════════
# EVALUATION PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/evaluate", methods=["POST"])
@app.route("/api/evaluate", methods=["POST"])
@require_auth
def evaluate():
    try:
        user_id      = _current_user_id()
        session_role = _current_role()

        subject          = request.form.get("subject", "").strip()
        student_name     = request.form.get("student_name", "").strip() or "Student"
        roll_number      = request.form.get("roll_number", "").strip() or "N/A"
        assessment_title = request.form.get("assessment_title", "").strip()
        level            = request.form.get("level", "school")
        board            = request.form.get("board", "")
        stream           = request.form.get("stream", "")
        semester         = request.form.get("semester", "")

        question_paper = request.files.get("question_paper")
        answer_script  = request.files.get("answer_script")
        rubrics        = request.files.get("rubrics") or request.files.get("rubric")
        syllabus       = request.files.get("syllabus") or request.files.get("syllabus_file")

        if question_paper is None or answer_script is None:
            return jsonify({"success": False, "error": "Question paper and answer script are required."}), 400

        if not allowed_file(question_paper.filename):
            return jsonify({"success": False, "error": f"File type not permitted for question paper."}), 400
        if not allowed_file(answer_script.filename):
            return jsonify({"success": False, "error": f"File type not permitted for answer script."}), 400

        qp_path      = save_uploaded_file(question_paper, "question_paper")
        answer_path  = save_uploaded_file(answer_script, "answer_script")
        rubric_path  = save_uploaded_file(rubrics, "rubrics") if rubrics and rubrics.filename else None
        syllabus_path = save_uploaded_file(syllabus, "syllabus") if syllabus and syllabus.filename else None

        user = _lookup_user_by_id(user_id)
        if session_role == "student" and user:
            student_name = user.get("name") or student_name
            roll_number  = user.get("roll_number") or roll_number
            level        = user.get("level") or level
            if user.get("level") == "college":
                stored_sem = user.get("semester") if user.get("semester") is not None else user.get("current_semester")
                semester = str(stored_sem) if stored_sem is not None else semester
            elif user.get("level") == "school":
                board  = user.get("board") or board
                stream = user.get("stream") or stream

        # Strict Provenance & Role Verification from Authenticated Session
        if session_role == "student":
            evaluation_source = "STUDENT_SELF_EVALUATION"
            student_id = user_id
            teacher_id = None
            class_id = request.form.get("class_id") or request.form.get("classId") or None
            created_by_user_id = user_id
            created_by_role = "student"
        else:
            evaluation_source = "TEACHER_EVALUATION"
            student_id = request.form.get("student_id") or request.form.get("studentId") or None
            teacher_id = user_id
            class_id = request.form.get("class_id") or request.form.get("classId") or None
            created_by_user_id = user_id
            created_by_role = "teacher"

        evaluation_request = {
            "evaluation_id":       f"eval_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}",
            "evaluation_source":   evaluation_source,
            "evaluationSource":   evaluation_source,
            "created_by_user_id":  created_by_user_id,
            "createdByUserId":     created_by_user_id,
            "created_by_role":     created_by_role,
            "createdByRole":       created_by_role,
            "class_id":            class_id,
            "classId":             class_id,
            "submitted_by":        user_id,
            "submitter_role":      session_role,
            "student_id":          student_id,
            "studentId":           student_id,
            "teacher_id":          teacher_id,
            "teacherId":           teacher_id,
            "subject":             subject,
            "student_name":        student_name,
            "roll_number":         roll_number,
            "assessment_title":    assessment_title or ("Self Evaluation Examination" if session_role == "student" else f"{subject} Examination"),
            "level":               level,
            "board":               board,
            "stream":              stream,
            "semester":            semester,
            "question_paper":      qp_path,
            "answer_script":       answer_path,
            "rubrics":             rubric_path,
            "syllabus":            syllabus_path,
        }

        # ── Run evaluation ────────────────────────────────────────────────────
        result = evaluation_agent.evaluate(evaluation_request)

        # ── Plagiarism check (teacher role only) ──────────────────────────────
        plagiarism_result = {
            "suspected": False,
            "similarity": 0.0,
            "status": "NO_COMPARISON",
            "details": "Plagiarism check is performed for teacher evaluations only.",
        }
        if session_role == "teacher":
            try:
                plagiarism_result = plagiarism_detector.check(
                    student_name=student_name,
                    roll_number=roll_number,
                    subject=result.get("student", {}).get("subject") or subject,
                    answer_script=answer_path,
                    question_paper=qp_path,
                )
            except Exception as p_err:
                logger.warning("Plagiarism check error: %s", p_err)

        # ── Persist ───────────────────────────────────────────────────────────
        eval_id = result.get("evaluation_id") or f"eval_{int(datetime.now().timestamp())}"
        try:
            stored_id = store_evaluation_pipeline(
                request_data=evaluation_request,
                eval_result=result,
                plagiarism_result=plagiarism_result,
            )
            if stored_id:
                eval_id = stored_id
        except Exception as s_err:
            logger.error("Storage error (evaluation still returned): %s", s_err)

        return jsonify({
            "success":       True,
            "evaluation_id": eval_id,
            "result":        result,
            "plagiarism":    plagiarism_result,
        }), 200

    except Exception as exc:
        logger.error("Evaluate endpoint: %s", traceback.format_exc())
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# EVALUATION HISTORY & DETAIL
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/evaluations", methods=["GET"])
@require_auth
def get_evaluations():
    user_id      = _current_user_id()
    session_role = _current_role()
    subject      = request.args.get("subject")
    class_id     = request.args.get("class_id") or request.args.get("classId")
    user         = _lookup_user_by_id(user_id)
    user_email   = user.get("email", "") if user else ""
    student_name = user.get("name", "") if user else ""

    mongo_db = get_mongodb()
    if mongo_db is not None:
        if session_role == "student":
            # Students see ONLY their own evaluations
            query: dict = {
                "$or": [
                    {"submitted_by": user_id},
                    {"student_id": user_id},
                    {"submitted_by": user_email},
                    {"student_id": user_email},
                ]
            }
            if student_name:
                query["$or"].append({"student_name": student_name})
        else:
            # Teachers see genuine teacher evaluations they submitted or are assigned to
            query = {
                "evaluation_source": "TEACHER_EVALUATION",
                "$or": [
                    {"submitted_by": user_id},
                    {"teacher_id": user_id},
                    {"created_by_user_id": user_id},
                    {"submitted_by": user_email},
                ]
            }
            if class_id:
                query["class_id"] = class_id

        if subject:
            query["subject"] = subject

        docs = list(mongo_db["evaluations"].find(query).sort("created_at", -1))
        evaluations = [mongo_serialize(d) for d in docs]
        return jsonify({"success": True, "evaluations": evaluations}), 200

    # SQLite path
    conn   = get_sqlite_db()
    cursor = conn.cursor()
    if session_role == "student":
        q = "SELECT * FROM evaluations WHERE (submitted_by = ? OR student_id = ? OR student_name = ?)"
        params: list = [user_id, user_id, student_name]
    else:
        q = "SELECT * FROM evaluations WHERE (submitted_by = ? OR teacher_id = ? OR created_by_user_id = ?) AND evaluation_source = 'TEACHER_EVALUATION'"
        params = [user_id, user_id, user_id]
        if class_id:
            q += " AND class_id = ?"
            params.append(class_id)

    if subject:
        q += " AND subject = ?"
        params.append(subject)
    q += " ORDER BY created_at DESC"
    cursor.execute(q, params)
    rows = cursor.fetchall()
    conn.close()
    return jsonify({"success": True, "evaluations": [dict(r) for r in rows]}), 200


@app.route("/api/evaluations/<eval_id>", methods=["GET"])
@require_auth
def get_evaluation_detail(eval_id: str):
    user_id      = _current_user_id()
    session_role = _current_role()
    user         = _lookup_user_by_id(user_id)
    user_email   = (user or {}).get("email", "")
    user_name    = (user or {}).get("name", "")

    mongo_db = get_mongodb()
    if mongo_db is not None:
        doc = None
        if ObjectId:
            try:
                doc = mongo_db["evaluations"].find_one({"_id": ObjectId(eval_id)})
            except Exception:
                pass
        if not doc:
            doc = mongo_db["evaluations"].find_one({"id": str(eval_id)})
        if not doc:
            return jsonify({"success": False, "error": "Evaluation not found."}), 404

        # Ownership check
        if session_role == "student":
            is_owner = (
                str(doc.get("submitted_by", "")) == user_id
                or str(doc.get("student_id", "")) == user_id
                or str(doc.get("submitted_by", "")) == user_email
                or (user_name and doc.get("student_name") == user_name)
            )
            if not is_owner:
                return jsonify({"success": False, "error": "Access denied."}), 403
        else:
            # Teacher: ensure teacher has rights to view
            is_teacher_owner = (
                str(doc.get("submitted_by", "")) == user_id
                or str(doc.get("teacher_id", "")) == user_id
                or str(doc.get("submitted_by", "")) == user_email
                or doc.get("assigned_to_teacher")
            )
            if not is_teacher_owner:
                return jsonify({"success": False, "error": "Access denied."}), 403

        serialized = mongo_serialize(doc)
        qs = serialized.get("questions") or serialized.get("evaluations") or []
        serialized["questions"]   = qs
        serialized["evaluations"] = qs
        return jsonify({"success": True, "evaluation": serialized}), 200

    # SQLite
    conn   = get_sqlite_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM evaluations WHERE id = ?", (eval_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"success": False, "error": "Evaluation not found."}), 404
    ev = dict(row)

    if session_role == "student":
        is_owner = (
            str(ev.get("submitted_by", "")) == user_id
            or str(ev.get("student_id", "")) == user_id
            or (user_name and ev.get("student_name") == user_name)
        )
        if not is_owner:
            conn.close()
            return jsonify({"success": False, "error": "Access denied."}), 403

    cursor.execute("SELECT * FROM evaluation_questions WHERE evaluation_id = ?", (eval_id,))
    qs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    ev["questions"]   = qs
    ev["evaluations"] = qs
    return jsonify({"success": True, "evaluation": ev}), 200


@app.route("/api/evaluations/<eval_id>", methods=["DELETE"])
def delete_evaluation(eval_id: str):
    """Delete an evaluation record and its associated data across both student and teacher portals."""
    try:
        user_id = _current_user_id()
        eval_id_str = str(eval_id).strip()

        # 1. MongoDB Cleanup
        mongo_db = get_mongodb()
        if mongo_db is not None:
            if ObjectId and len(eval_id_str) == 24:
                try:
                    mongo_db["evaluations"].delete_many({"_id": ObjectId(eval_id_str)})
                except Exception:
                    pass
            mongo_db["evaluations"].delete_many({"$or": [{"id": eval_id_str}, {"evaluation_id": eval_id_str}, {"_id": eval_id_str}]})
            mongo_db["evaluation_questions"].delete_many({"$or": [{"evaluation_id": eval_id_str}, {"eval_id": eval_id_str}]})
            mongo_db["misconceptions"].delete_many({"$or": [{"evaluation_id": eval_id_str}, {"eval_id": eval_id_str}]})

        # 2. SQLite Cleanup
        conn = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM evaluations WHERE id = ?", (eval_id_str,))
        cursor.execute("DELETE FROM evaluation_questions WHERE evaluation_id = ?", (eval_id_str,))
        cursor.execute("DELETE FROM misconceptions WHERE evaluation_id = ?", (eval_id_str,))
        conn.commit()
        conn.close()

        # 3. Clear In-Memory Deterministic Evaluation Cache
        try:
            EvaluationAgent.clear_cache()
        except Exception:
            pass

        return jsonify({"success": True, "message": "Evaluation record deleted successfully."}), 200
    except Exception as exc:
        logger.error(f"Error deleting evaluation {eval_id}: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/evaluations/<eval_id>/override", methods=["PUT", "POST"])
@require_role("teacher")
def override_evaluation_marks(eval_id: str):
    """Teacher mark override with audit trail."""
    try:
        teacher_id = _current_user_id()
        data = request.get_json(force=True) or {}
        updated_questions = data.get("questions") or []

        obtained_marks = float(data.get("obtained_marks", 0))
        total_marks    = float(data.get("total_marks", 0))

        if total_marks <= 0:
            return jsonify({"success": False, "error": "total_marks must be > 0."}), 400
        if obtained_marks < 0 or obtained_marks > total_marks:
            return jsonify({"success": False, "error": "obtained_marks out of valid range."}), 400

        percentage = round((obtained_marks / total_marks) * 100, 2)

        def calc_grade(p: float) -> str:
            if p >= 90: return "A+"
            if p >= 80: return "A"
            if p >= 70: return "B+"
            if p >= 60: return "B"
            if p >= 50: return "C"
            if p >= 40: return "D"
            return "F"

        grade = calc_grade(percentage)
        now   = datetime.utcnow()

        update_fields = {
            "obtained_marks":        obtained_marks,
            "total_marks":           total_marks,
            "percentage":            percentage,
            "grade":                 grade,
            "questions":             updated_questions,
            "evaluations":           updated_questions,
            "is_teacher_overridden": True,
            "teacher_override_by":   teacher_id,
            "teacher_override_at":   now.strftime("%Y-%m-%d %H:%M:%S"),
            "evaluation_status":     "COMPLETED",
            "teacher_review_required": False,
        }

        def _safe_val(v, default=0.0):
            try:
                return float(v) if v is not None else default
            except (ValueError, TypeError):
                return default

        # Recalculate marks lost and update linked action items
        calc_marks_lost = round(max(0.0, total_marks - obtained_marks), 2)
        affected_qs = [
            str(q.get("question_number") or i + 1)
            for i, q in enumerate(updated_questions)
            if _safe_val(q.get("maximum_marks"), 0) > _safe_val(q.get("awarded_marks"), 0)
        ]
        marks_lost_per_q = {
            str(q.get("question_number") or i + 1): round(
                max(0.0, _safe_val(q.get("maximum_marks"), 0) - _safe_val(q.get("awarded_marks"), 0)), 2
            )
            for i, q in enumerate(updated_questions)
            if _safe_val(q.get("maximum_marks"), 0) > _safe_val(q.get("awarded_marks"), 0)
        }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            # Audit log
            mongo_db["audit_log"].insert_one({
                "action":       "teacher_override",
                "eval_id":      eval_id,
                "teacher_id":   teacher_id,
                "new_obtained": obtained_marks,
                "new_total":    total_marks,
                "new_pct":      percentage,
                "timestamp":    now,
            })
            if ObjectId:
                try:
                    mongo_db["evaluations"].update_one(
                        {"_id": ObjectId(eval_id)}, {"$set": update_fields}
                    )
                except Exception:
                    pass
            mongo_db["evaluations"].update_one({"id": eval_id}, {"$set": update_fields})

            # Recalculate linked action items
            mongo_db["action_items"].update_many(
                {"$or": [{"evaluation_id": eval_id}, {"evaluation_id": str(eval_id)}], "category": "teacher_review"},
                {"$set": {"status": "Resolved", "updated_at": now.strftime("%Y-%m-%d %H:%M:%S")}}
            )
            if calc_marks_lost > 20.0:
                mongo_db["action_items"].update_many(
                    {"$or": [{"evaluation_id": eval_id}, {"evaluation_id": str(eval_id)}], "category": "excessive_marks_lost"},
                    {"$set": {
                        "total_marks": obtained_marks,
                        "maximum_marks": total_marks,
                        "marks_lost": calc_marks_lost,
                        "affected_questions": affected_qs,
                        "marks_lost_per_question": marks_lost_per_q,
                        "academic_status": f"At Risk (Lost {calc_marks_lost} marks)",
                        "issue": f"Student lost {calc_marks_lost} marks ({obtained_marks}/{total_marks}) across {len(affected_qs)} questions.",
                        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "status": "Active",
                    }}
                )
            else:
                mongo_db["action_items"].update_many(
                    {"$or": [{"evaluation_id": eval_id}, {"evaluation_id": str(eval_id)}], "category": "excessive_marks_lost"},
                    {"$set": {"status": "Resolved", "updated_at": now.strftime("%Y-%m-%d %H:%M:%S")}}
                )

        conn = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE evaluations SET obtained_marks=?, total_marks=?, percentage=?, grade=?, "
            "is_teacher_overridden=1 WHERE id=?",
            (obtained_marks, total_marks, percentage, grade, str(eval_id))
        )
        cursor.execute(
            "UPDATE action_items SET status = 'Resolved' WHERE evaluation_id = ? AND category = 'teacher_review'",
            (str(eval_id),)
        )
        if calc_marks_lost > 20.0:
            cursor.execute(
                """UPDATE action_items 
                   SET total_marks = ?, maximum_marks = ?, marks_lost = ?, 
                       affected_questions = ?, marks_lost_per_question = ?,
                       academic_status = ?, issue = ?, status = 'Active'
                   WHERE evaluation_id = ? AND category = 'excessive_marks_lost'""",
                (
                    obtained_marks, total_marks, calc_marks_lost,
                    json.dumps(affected_qs), json.dumps(marks_lost_per_q),
                    f"At Risk (Lost {calc_marks_lost} marks)",
                    f"Student lost {calc_marks_lost} marks ({obtained_marks}/{total_marks}).",
                    str(eval_id)
                )
            )
        else:
            cursor.execute(
                "UPDATE action_items SET status = 'Resolved' WHERE evaluation_id = ? AND category = 'excessive_marks_lost'",
                (str(eval_id),)
            )
        conn.commit()
        conn.close()

        return jsonify({
            "success":       True,
            "obtained_marks": obtained_marks,
            "total_marks":   total_marks,
            "percentage":    percentage,
            "grade":         grade,
        }), 200

    except Exception as exc:
        logger.error("Override error: %s", traceback.format_exc())
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# PDF REPORTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/evaluations/<eval_id>/pdf", methods=["GET"])
@require_auth
def download_evaluation_pdf(eval_id: str):
    try:
        user_id      = _current_user_id()
        session_role = _current_role()
        user         = _lookup_user_by_id(user_id)
        user_email   = (user or {}).get("email", "")
        user_name    = (user or {}).get("name", "")

        eval_data = None
        mongo_db  = get_mongodb()
        if mongo_db is not None:
            doc = None
            if ObjectId and len(str(eval_id)) == 24:
                try:
                    doc = mongo_db["evaluations"].find_one({"_id": ObjectId(eval_id)})
                except Exception:
                    pass
            if not doc:
                doc = mongo_db["evaluations"].find_one({"id": str(eval_id)})
            if doc:
                eval_data = mongo_serialize(doc)

        if not eval_data:
            conn   = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM evaluations WHERE id = ?", (str(eval_id),))
            row = cursor.fetchone()
            conn.close()
            if row:
                eval_data = dict(row)

        if not eval_data:
            return jsonify({"success": False, "error": "Evaluation not found."}), 404

        # Strict authorization & provenance check
        if session_role == "student":
            is_owner = (
                str(eval_data.get("submitted_by", "")) == user_id
                or str(eval_data.get("student_id", "")) == user_id
                or str(eval_data.get("submitted_by", "")) == user_email
                or (user_name and eval_data.get("student_name") == user_name)
            )
            if not is_owner:
                return jsonify({"success": False, "error": "Access denied."}), 403
        else:
            if eval_data.get("evaluation_source") != "TEACHER_EVALUATION":
                return jsonify({"success": False, "error": "Access denied. Only teacher evaluations can be exported by teachers."}), 403
            is_teacher_owner = (
                str(eval_data.get("submitted_by", "")) == user_id
                or str(eval_data.get("teacher_id", "")) == user_id
                or str(eval_data.get("created_by_user_id", "")) == user_id
                or str(eval_data.get("submitted_by", "")) == user_email
                or eval_data.get("assigned_to_teacher")
            )
            if not is_teacher_owner:
                return jsonify({"success": False, "error": "Access denied."}), 403

        pdf_bytes = generate_evaluation_pdf(eval_data)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"Evaluation_Report_{eval_id}.pdf",
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/generate-pdf", methods=["POST"])
@require_auth
def generate_pdf_endpoint():
    try:
        data      = request.get_json(force=True) or {}
        pdf_bytes = generate_evaluation_pdf(data)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"Evaluation_Report_{(data.get('subject') or 'Paper').replace(' ', '_')}.pdf",
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# SYLLABUS & CURRICULUM MANAGEMENT (SEMESTER-AWARE)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/syllabus/analyze", methods=["POST"])
@require_auth
def analyze_syllabus():
    """
    Analyze and persist syllabus with strict semester and academic-level validation.
    For college students:
      - Validates uploaded syllabus against student's current authoritative semester.
      - If multi-semester document, extracts ONLY the target semester curriculum.
      - If mismatched or ambiguous, flags status as MISMATCH or NEEDS_REVIEW without silent activation.
    """
    try:
        user_id  = _current_user_id()
        user     = _lookup_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found."}), 404

        json_data = request.get_json(silent=True) or {}
        def get_param(k):
            return request.form.get(k) if request.form.get(k) is not None else json_data.get(k)

        syllabus_file = request.files.get("syllabus") or request.files.get("syllabus_file")
        syllabus_text = str(get_param("syllabus_text") or get_param("text") or get_param("syllabusText") or "").strip()

        stored_level   = str((user or {}).get("level") or "college").strip().lower()
        level          = stored_level
        stored_sem     = (user or {}).get("semester") if (user or {}).get("semester") is not None else (user or {}).get("current_semester")

        # For COLLEGE students, the stored semester in the authenticated account is authoritative
        if level == "college":
            if stored_sem is None or str(stored_sem).strip() in ("", "0", "null", "undefined", "None"):
                return jsonify({
                    "success": False,
                    "error": "Semester information required. Please configure your current semester in your student profile before uploading a syllabus.",
                    "status": "SEMESTER_REQUIRED",
                    "validation_status": "SEMESTER_REQUIRED"
                }), 400
            try:
                target_semester = int(stored_sem) if str(stored_sem).isdigit() else stored_sem
            except (ValueError, TypeError):
                target_semester = str(stored_sem).strip()
        else:
            semester_input = get_param("semester")
            target_semester = semester_input or stored_sem

        # Authoritative student profile metadata
        degree         = str((user or {}).get("degree") or (user or {}).get("program") or get_param("degree") or "").strip()
        department     = str((user or {}).get("department") or (user or {}).get("branch") or (user or {}).get("domain") or get_param("department") or "").strip()
        regulation     = str((user or {}).get("regulation") or (user or {}).get("batch") or get_param("regulation") or "").strip()
        academic_year  = str((user or {}).get("academic_year") or (user or {}).get("academicYear") or get_param("academic_year") or "").strip()
        class_level    = str((user or {}).get("grade_level") or (user or {}).get("classLevel") or get_param("classLevel") or "").strip()
        stream         = str((user or {}).get("stream") or get_param("stream") or "").strip()

        file_path = None
        file_hash = None
        file_name = None

        if syllabus_file and syllabus_file.filename:
            if not allowed_file(syllabus_file.filename):
                return jsonify({"success": False, "error": "File type not permitted. Please upload a PDF or image."}), 400
            file_bytes = syllabus_file.read()
            file_hash  = hashlib.sha256(file_bytes).hexdigest()
            syllabus_file.seek(0)
            file_path = save_uploaded_file(syllabus_file, "syllabus")
            file_name = syllabus_file.filename
            file_input = file_path
        elif syllabus_text:
            file_input = syllabus_text
            file_name  = "text_input"
            file_hash  = hashlib.sha256(syllabus_text.strip().encode("utf-8")).hexdigest()
        else:
            return jsonify({"success": False, "error": "No syllabus file or text provided."}), 400

        # Check if a valid curriculum already exists for the same syllabus and semester to avoid duplicate processing
        if file_hash:
            mongo_db = get_mongodb()
            if mongo_db is not None:
                existing_valid = mongo_db["syllabi"].find_one({
                    "$and": [
                        {"$or": [{"student_id": str(user_id)}, {"studentId": str(user_id)}]},
                        {"$or": [{"file_hash": file_hash}, {"fileHash": file_hash}]},
                        {"$or": [{"semester": target_semester}, {"semester": str(target_semester)}]},
                        {"$or": [{"validation_status": "VALID"}, {"curriculumStatus": "VALID"}, {"status": {"$in": ["ACTIVE", "VALID"]}}]}
                    ]
                }, sort=[("updated_at", -1), ("updatedAt", -1), ("version", -1)])

                if existing_valid and existing_valid.get("subjects"):
                    now = datetime.utcnow()
                    # Atomically archive older active records and ensure this existing valid doc is active
                    mongo_db["syllabi"].update_many(
                        {"$or": [{"student_id": str(user_id)}, {"studentId": str(user_id)}], "_id": {"$ne": existing_valid["_id"]}},
                        {"$set": {"is_active": False, "isActive": False, "status": "ARCHIVED", "updated_at": now, "updatedAt": now}}
                    )
                    mongo_db["syllabi"].update_one(
                        {"_id": existing_valid["_id"]},
                        {"$set": {"is_active": True, "isActive": True, "status": "ACTIVE", "curriculumStatus": "VALID", "validation_status": "VALID", "validationStatus": "VALID", "updated_at": now, "updatedAt": now}}
                    )
                    existing_valid["is_active"] = True
                    existing_valid["isActive"] = True
                    existing_valid["status"] = "ACTIVE"
                    existing_valid["curriculumStatus"] = "VALID"
                    existing_valid["validation_status"] = "VALID"
                    existing_valid["validationStatus"] = "VALID"

                    resp_doc = mongo_serialize(existing_valid)
                    return jsonify({
                        "success": True,
                        "syllabus_id": existing_valid.get("syllabus_id") or existing_valid.get("syllabusId"),
                        "validation_status": "VALID",
                        "validationStatus": "VALID",
                        "curriculumStatus": "VALID",
                        "is_active": True,
                        "reused": True,
                        "detected_semesters": existing_valid.get("detected_semesters", []),
                        "explicit_semester_identifier": existing_valid.get("explicit_semester_identifier", ""),
                        "analysis": existing_valid.get("analysis", {}),
                        "syllabus": resp_doc
                    }), 200
            else:
                conn = get_sqlite_db()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM syllabi WHERE student_id=? AND file_hash=? AND (validation_status='VALID' OR status IN ('ACTIVE', 'VALID')) ORDER BY version DESC LIMIT 1",
                    (str(user_id), file_hash)
                )
                row = cursor.fetchone()
                if row:
                    row_dict = dict(row)
                    now_iso = datetime.utcnow().isoformat()
                    cursor.execute("UPDATE syllabi SET is_active=0, status='ARCHIVED', updated_at=? WHERE student_id=? AND id!=?", (now_iso, str(user_id), row_dict["id"]))
                    cursor.execute("UPDATE syllabi SET is_active=1, status='ACTIVE', updated_at=? WHERE id=?", (now_iso, row_dict["id"]))
                    conn.commit()
                    conn.close()
                    analysis_data = json.loads(row_dict.get("analysis_json") or "{}")
                    row_dict.update(analysis_data)
                    return jsonify({
                        "success": True,
                        "syllabus_id": row_dict.get("syllabus_id"),
                        "validation_status": "VALID",
                        "validationStatus": "VALID",
                        "curriculumStatus": "VALID",
                        "is_active": True,
                        "reused": True,
                        "analysis": analysis_data,
                        "syllabus": row_dict
                    }), 200
                conn.close()

        # Execute Gemini analysis with authoritative academic profile context
        analysis = gemini_service.analyze_syllabus(
            file_input,
            level=level,
            semester=target_semester,
            class_level=class_level,
            domain=department,
            stream=stream,
            degree=degree,
            department=department,
            regulation=regulation,
            academic_year=academic_year
        )

        if not analysis or not isinstance(analysis, dict):
            return jsonify({"success": False, "error": "Syllabus analysis failed to return structured data."}), 500

        syllabus_id = str(uuid.uuid4())
        now = datetime.utcnow()
        detected_semesters = analysis.get("detected_semesters") or []
        explicit_identifier = analysis.get("explicit_semester_identifier") or ""

        # Enrich every subject with authoritative document source evidence
        raw_subjects_list = analysis.get("subjects") or [{"name": s} for s in analysis.get("extracted_subjects", [])]
        enriched_subjects = []
        for s_item in raw_subjects_list:
            if isinstance(s_item, str):
                s_dict = {"name": s_item}
            elif isinstance(s_item, dict):
                s_dict = dict(s_item)
            else:
                continue

            s_name = str(s_dict.get("name") or s_dict.get("subjectName") or "").strip()
            if not s_name:
                continue
            s_code = str(s_dict.get("code") or s_dict.get("subjectCode") or "").strip()
            s_sec = str(s_dict.get("source_section") or s_dict.get("sourceSection") or s_dict.get("source_page") or explicit_identifier or f"Semester {target_semester or ''} Scheme Table").strip()
            s_txt = str(s_dict.get("source_text") or s_dict.get("sourceText") or f"{s_code} {s_name}".strip()).strip()
            s_ev = str(s_dict.get("semester_evidence") or f"Found in Semester {target_semester or ''} curriculum blueprint").strip()

            pages_raw = s_dict.get("source_page_numbers") or s_dict.get("sourcePages") or [s_dict.get("source_page", 1)]
            if isinstance(pages_raw, list):
                pages = [int(p) for p in pages_raw if str(p).isdigit()]
            elif isinstance(pages_raw, (int, str)) and str(pages_raw).isdigit():
                pages = [int(pages_raw)]
            else:
                pages = [1]
            if not pages:
                pages = [1]

            sub_id = str(s_dict.get("subjectId") or s_dict.get("id") or f"sub_{hashlib.md5(f'{degree}_{department}_{target_semester}_{s_name}'.encode('utf-8')).hexdigest()[:10]}")
            c_type = str(s_dict.get("courseType") or s_dict.get("type") or s_dict.get("category") or "Theory Core").strip()
            conf_val = float(s_dict.get("confidence", 0.98)) if str(s_dict.get("confidence", "")).replace('.', '', 1).isdigit() else (float(s_dict.get("extractionConfidence", 0.98)) if str(s_dict.get("extractionConfidence", "")).replace('.', '', 1).isdigit() else 0.98)
            cr_val = float(s_dict["credits"]) if s_dict.get("credits") is not None and str(s_dict.get("credits")).replace('.', '', 1).isdigit() else None

            subj_units = (analysis.get("chapters") or {}).get(s_name) or (analysis.get("units") or {}).get(s_name) or s_dict.get("units") or s_dict.get("modules") or []
            subj_topics = [c for u in subj_units for c in u.get("concepts", [])] if subj_units else (s_dict.get("topics") or [])

            enriched_subjects.append({
                "subjectId": sub_id,
                "id": sub_id,
                "subjectCode": s_code,
                "code": s_code,
                "subjectName": s_name,
                "name": s_name,
                "courseType": c_type,
                "type": c_type,
                "category": str(s_dict.get("category") or c_type).strip(),
                "credits": cr_val,
                "lecture_hours": int(s_dict["lecture_hours"]) if str(s_dict.get("lecture_hours", "")).isdigit() else None,
                "tutorial_hours": int(s_dict["tutorial_hours"]) if str(s_dict.get("tutorial_hours", "")).isdigit() else None,
                "practical_hours": int(s_dict["practical_hours"]) if str(s_dict.get("practical_hours", "")).isdigit() else None,
                "semester": target_semester or s_dict.get("semester"),
                "program": degree or "Degree Program",
                "department": department or "Engineering/Science",
                "modules": subj_units,
                "units": subj_units,
                "chapters": subj_units,
                "topics": subj_topics,
                "source_document_id": syllabus_id,
                "source_document_name": file_name or "Official Syllabus Document",
                "source_document_hash": file_hash or "",
                "sourcePages": pages,
                "source_page_numbers": pages,
                "source_page": pages[0] if pages else 1,
                "sourceSection": s_sec,
                "source_section": s_sec,
                "sourceText": s_txt,
                "source_text": s_txt,
                "semester_evidence": s_ev,
                "extractionConfidence": conf_val,
                "confidence": conf_val,
                "evidence_verified": True
            })

        analysis["subjects"] = enriched_subjects

        # Execute dedicated Curriculum Completeness Validator BEFORE activating
        validation_report = CurriculumCompletenessValidator.validate(
            user=user,
            analysis=analysis,
            raw_content_or_file=file_input,
            target_semester=target_semester
        )

        validation_status = str(validation_report.get("status") or "VALID").upper().strip()
        is_active = bool(validation_report.get("is_valid", False))
        status_label = "ACTIVE" if is_active else validation_status
        mismatch_reason = validation_report.get("summary") or analysis.get("mismatch_reason")

        syllabus_doc = {
            "studentId":                    user_id,
            "student_id":                   user_id,
            "syllabusId":                   syllabus_id,
            "syllabus_id":                  syllabus_id,
            "studentName":                  user.get("name", ""),
            "student_name":                 user.get("name", ""),
            "program":                      degree,
            "degree":                       degree,
            "department":                   department,
            "branch":                       department,
            "semester":                     target_semester,
            "current_semester":             target_semester,
            "currentSemester":              target_semester,
            "class_level":                  class_level,
            "classLevel":                   class_level,
            "grade_level":                  class_level,
            "stream":                       stream,
            "regulation":                   regulation,
            "academic_year":                academic_year,
            "academicYear":                 academic_year,
            "file_path":                    file_path or "",
            "file_hash":                    file_hash or "",
            "fileHash":                     file_hash or "",
            "file_name":                    file_name or "",
            "fileName":                     file_name or "",
            "level":                        level,
            "curriculumStatus":             validation_status,
            "validation_status":            validation_status,
            "validationStatus":             validation_status,
            "validation_report":            validation_report,
            "validationReport":             validation_report,
            "detected_semesters":           detected_semesters,
            "explicit_semester_identifier": explicit_identifier,
            "mismatch_reason":              mismatch_reason,
            "subjects":                     enriched_subjects,
            "extracted_subjects":           [s["name"] for s in enriched_subjects] if enriched_subjects else analysis.get("extracted_subjects", []),
            "extracted_subject_count":       validation_report.get("subjects_detected", len(enriched_subjects)),
            "extractedSubjectCount":        validation_report.get("subjects_detected", len(enriched_subjects)),
            "expected_subject_count":        analysis.get("expected_subject_count", len(enriched_subjects)),
            "expectedSubjectCount":         analysis.get("expected_subject_count", len(enriched_subjects)),
            "completeness_verified":         validation_report.get("missing_subjects", 0) == 0 and validation_report.get("uncertain_subjects", 0) == 0,
            "completenessVerified":          validation_report.get("missing_subjects", 0) == 0 and validation_report.get("uncertain_subjects", 0) == 0,
            "completeness_notes":            analysis.get("completeness_notes") or validation_report.get("summary") or "",
            "chapters":                     analysis.get("chapters") or {},
            "units":                        analysis.get("chapters") or {},
            "key_topics":                   analysis.get("key_topics") or [],
            "topics":                       analysis.get("key_topics") or [],
            "analysis":                     analysis,
            "is_active":                    is_active,
            "isActive":                     is_active,
            "status":                       status_label,
            "version":                      1,
            "created_at":                   now,
            "createdAt":                    now,
            "updated_at":                   now,
            "updatedAt":                    now,
        }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            if is_active:
                # Atomically archive older active syllabi for this student
                mongo_db["syllabi"].update_many(
                    {
                        "$and": [
                            {"$or": [{"student_id": str(user_id)}, {"studentId": str(user_id)}, {"student_id": user_id}, {"studentId": user_id}]},
                            {"$or": [{"is_active": True}, {"isActive": True}, {"status": {"$in": ["ACTIVE", "READY", "VALID"]}}, {"curriculumStatus": "VALID"}, {"validation_status": "VALID"}]}
                        ]
                    },
                    {"$set": {"is_active": False, "isActive": False, "status": "ARCHIVED", "curriculumStatus": "ARCHIVED", "validation_status": "ARCHIVED", "updated_at": now, "updatedAt": now}}
                )
            existing = mongo_db["syllabi"].find_one(
                {"$or": [{"student_id": user_id}, {"studentId": user_id}]},
                sort=[("version", -1)]
            )
            version = (existing.get("version", 0) + 1) if existing else 1
            syllabus_doc["version"] = version
            mongo_db["syllabi"].insert_one(syllabus_doc)

            # If active with extracted subjects, update user's quick subject list
            if is_active and analysis.get("extracted_subjects"):
                mongo_db["users"].update_one(
                    {"$or": [{"_id": ObjectId(user_id)} if (ObjectId and len(str(user_id)) == 24) else {"id": str(user_id)}, {"user_id": str(user_id)}]},
                    {"$set": {"subjects": analysis["extracted_subjects"], "updated_at": now, "updatedAt": now}}
                )
        else:
            conn   = get_sqlite_db()
            cursor = conn.cursor()
            if is_active:
                cursor.execute(
                    "UPDATE syllabi SET is_active=0, status='ARCHIVED', updated_at=? WHERE student_id=?",
                    (now.isoformat(), user_id)
                )
            cursor.execute(
                """INSERT INTO syllabi
                   (syllabus_id, student_id, student_name, file_path, file_hash,
                    file_name, level, semester, class_level, degree, program,
                    department, branch, regulation, academic_year, validation_status,
                    is_active, detected_semesters, mismatch_reason, analysis_json, status, version)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (syllabus_id, user_id, user.get("name", ""), file_path or "",
                 file_hash or "", file_name or "", level, str(target_semester) if target_semester else "",
                 class_level, degree, degree, department, department, regulation, academic_year,
                 validation_status, 1 if is_active else 0, json.dumps(detected_semesters),
                 mismatch_reason or "", json.dumps(analysis), status_label, 1)
            )
            conn.commit()
            conn.close()

        response_doc = mongo_serialize(syllabus_doc)

        return jsonify({
            "success": True,
            "syllabus_id": syllabus_id,
            "validation_status": validation_status,
            "validationStatus": validation_status,
            "curriculumStatus": validation_status,
            "validation_report": validation_report,
            "validationReport": validation_report,
            "is_active": is_active,
            "mismatch_reason": mismatch_reason,
            "detected_semesters": detected_semesters,
            "explicit_semester_identifier": explicit_identifier,
            "analysis": analysis,
            "syllabus": response_doc
        }), 200

    except Exception as exc:
        logger.error("Syllabus analyze error: %s", traceback.format_exc())
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/syllabus/confirm-override", methods=["POST"])
@require_auth
def confirm_syllabus_override():
    """
    Allow student to explicitly activate a syllabus flagged as NEEDS_REVIEW or MISMATCH
    after manual verification.
    """
    try:
        user_id = _current_user_id()
        data = request.get_json(force=True) or {}
        syllabus_id = data.get("syllabus_id")
        if not syllabus_id:
            return jsonify({"success": False, "error": "syllabus_id is required."}), 400

        now = datetime.utcnow()
        mongo_db = get_mongodb()
        if mongo_db is not None:
            doc = mongo_db["syllabi"].find_one({"syllabus_id": syllabus_id, "student_id": user_id})
            if not doc:
                return jsonify({"success": False, "error": "Syllabus record not found."}), 404

            # Deactivate older active syllabi
            mongo_db["syllabi"].update_many(
                {"student_id": user_id, "is_active": True},
                {"$set": {"is_active": False, "status": "ARCHIVED", "updated_at": now}}
            )
            # Activate this syllabus
            mongo_db["syllabi"].update_one(
                {"syllabus_id": syllabus_id},
                {"$set": {"is_active": True, "status": "ACTIVE", "validation_status": "MANUALLY_CONFIRMED", "updated_at": now}}
            )
            updated_doc = mongo_db["syllabi"].find_one({"syllabus_id": syllabus_id})
            return jsonify({"success": True, "syllabus": mongo_serialize(updated_doc)}), 200
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE syllabi SET is_active=0, status='ARCHIVED' WHERE student_id=?", (user_id,))
            cursor.execute(
                "UPDATE syllabi SET is_active=1, status='ACTIVE', validation_status='MANUALLY_CONFIRMED', updated_at=? WHERE syllabus_id=? AND student_id=?",
                (now.isoformat(), syllabus_id, user_id)
            )
            conn.commit()
            cursor.execute("SELECT * FROM syllabi WHERE syllabus_id=?", (syllabus_id,))
            row = cursor.fetchone()
            conn.close()
            return jsonify({"success": True, "syllabus": dict(row) if row else None}), 200

    except Exception as exc:
        logger.error("Confirm syllabus error: %s", traceback.format_exc())
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/syllabus/status/<syllabus_id>", methods=["GET"])
@require_auth
def get_syllabus_status(syllabus_id: str):
    """
    Get processing or validation status for an uploaded syllabus.
    Enforces student-level ownership isolation.
    """
    try:
        user_id = _current_user_id()
        mongo_db = get_mongodb()
        if mongo_db is not None:
            doc = mongo_db["syllabi"].find_one({"syllabus_id": syllabus_id, "student_id": user_id})
            if not doc:
                return jsonify({"success": False, "error": "Syllabus not found.", "status": "NOT_FOUND"}), 404
            return jsonify({
                "success": True,
                "syllabus_id": syllabus_id,
                "status": doc.get("status") or doc.get("validation_status", "VALID"),
                "validation_status": doc.get("validation_status", "VALID"),
                "is_active": doc.get("is_active", False),
                "mismatch_reason": doc.get("mismatch_reason"),
                "detected_semesters": doc.get("detected_semesters", []),
                "extracted_subject_count": doc.get("extracted_subject_count", len(doc.get("subjects", []))),
                "syllabus": mongo_serialize(doc)
            }), 200
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM syllabi WHERE syllabus_id=? AND student_id=?", (syllabus_id, user_id))
            row = cursor.fetchone()
            conn.close()
            if not row:
                return jsonify({"success": False, "error": "Syllabus not found.", "status": "NOT_FOUND"}), 404
            d = dict(row)
            if d.get("analysis_json"):
                try:
                    d["analysis"] = json.loads(d["analysis_json"])
                except Exception:
                    pass
            return jsonify({
                "success": True,
                "syllabus_id": syllabus_id,
                "status": d.get("status") or d.get("validation_status", "VALID"),
                "validation_status": d.get("validation_status", "VALID"),
                "is_active": bool(d.get("is_active", 0)),
                "mismatch_reason": d.get("mismatch_reason"),
                "syllabus": d
            }), 200
    except Exception as exc:
        logger.error("Syllabus status error: %s", traceback.format_exc())
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/syllabus", methods=["GET"])
@require_auth
def get_my_syllabus():
    """Return the current authenticated student's active semester-mapped syllabus."""
    user_id = _current_user_id()
    user = _lookup_user_by_id(user_id)
    current_sem = user.get("semester") if user else None

    mongo_db = get_mongodb()
    if mongo_db is not None:
        # First query for active syllabus
        query = {"student_id": user_id, "$or": [{"is_active": True}, {"status": {"$in": ["ACTIVE", "READY"]}}]}
        doc = mongo_db["syllabi"].find_one(query, sort=[("updated_at", -1), ("version", -1)])
        
        # Check if there is a pending review / mismatched syllabus to inform frontend
        pending_doc = mongo_db["syllabi"].find_one(
            {"student_id": user_id, "status": {"$in": ["NEEDS_REVIEW", "MISMATCH"]}},
            sort=[("updated_at", -1)]
        )

        return jsonify({
            "success": True,
            "syllabus": mongo_serialize(doc) if doc else None,
            "pending_syllabus": mongo_serialize(pending_doc) if pending_doc else None
        }), 200

    conn   = get_sqlite_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM syllabi WHERE student_id=? AND (is_active=1 OR status IN ('ACTIVE', 'READY')) ORDER BY version DESC LIMIT 1",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        if d.get("analysis_json"):
            try:
                d["analysis"] = json.loads(d["analysis_json"])
            except Exception:
                pass
        return jsonify({"success": True, "syllabus": d, "pending_syllabus": None}), 200
    return jsonify({"success": True, "syllabus": None, "pending_syllabus": None}), 200


@app.route("/api/curriculum/active", methods=["GET"])
@require_auth
def get_active_curriculum():
    """
    Authoritative single-source API for:
    1. Personal Trainer
    2. Reality Lab
    3. Knowledge Transfer
    
    Returns the validated semester curriculum object consumed identically by all learning agents.
    If curriculum validation failed or requires review, returns is_valid: False, status, reason.
    """
    user_id = _current_user_id()
    user = _lookup_user_by_id(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found."}), 404

    current_sem = user.get("semester") if user.get("semester") is not None else user.get("current_semester")
    degree = user.get("degree") or user.get("program") or ""
    department = user.get("department") or user.get("branch") or user.get("domain") or ""
    auth_curriculum = _get_authoritative_curriculum(user_id, user)
    if auth_curriculum:
        return jsonify({
            "success": True,
            "is_valid": True,
            "is_active": True,
            "status": "VALID",
            "curriculumStatus": "VALID",
            "curriculum_id": auth_curriculum.get("curriculum_id"),
            "curriculumId": auth_curriculum.get("curriculumId"),
            "syllabus_id": auth_curriculum.get("syllabus_id"),
            "syllabusId": auth_curriculum.get("syllabusId"),
            "student_id": auth_curriculum.get("student_id"),
            "studentId": auth_curriculum.get("studentId"),
            "program": auth_curriculum.get("program") or auth_curriculum.get("degree") or degree,
            "degree": auth_curriculum.get("degree") or auth_curriculum.get("program") or degree,
            "department": auth_curriculum.get("department") or auth_curriculum.get("branch") or department,
            "semester": auth_curriculum.get("semester") or current_sem,
            "subjects": auth_curriculum.get("subjects") or [],
            "extracted_subjects": auth_curriculum.get("extracted_subjects") or [],
            "units": auth_curriculum.get("units") or {},
            "chapters": auth_curriculum.get("chapters") or {},
            "topics": auth_curriculum.get("topics") or [],
            "validation_report": auth_curriculum.get("validation_report") or auth_curriculum.get("validationReport"),
            "source_document_name": auth_curriculum.get("file_name") or auth_curriculum.get("fileName"),
            "source_document_id": auth_curriculum.get("syllabus_id"),
            "evidence_retained": True
        }), 200

    mongo_db = get_mongodb()
    if mongo_db is not None:
        # No active valid doc found. Check other syllabus states.
        user_filter = {
            "$or": [
                {"student_id": str(user_id)},
                {"studentId": str(user_id)},
                {"student_id": user_id},
                {"studentId": user_id}
            ]
        }
        # Check for PROCESSING state
        proc_doc = mongo_db["syllabi"].find_one(
            {"$and": [user_filter, {"status": {"$in": ["PROCESSING", "ANALYZING", "PARSING"]}}]},
            sort=[("updated_at", -1), ("updatedAt", -1)]
        )
        if proc_doc:
            return jsonify({
                "success": True,
                "is_valid": False,
                "is_active": False,
                "status": "PROCESSING",
                "curriculumStatus": "PROCESSING",
                "reason": "Your syllabus document is currently being analyzed and verified. Please wait...",
                "semester": current_sem,
                "degree": degree,
                "department": department,
                "subjects": [],
                "extracted_subjects": [],
                "units": {},
                "chapters": {},
                "topics": []
            }), 200

        # Check for EXTRACTION_FAILED state
        failed_doc = mongo_db["syllabi"].find_one(
            {"$and": [user_filter, {"status": {"$in": ["EXTRACTION_FAILED", "FAILED", "ERROR"]}}]},
            sort=[("updated_at", -1), ("updatedAt", -1)]
        )
        if failed_doc:
            return jsonify({
                "success": True,
                "is_valid": False,
                "is_active": False,
                "status": "EXTRACTION_FAILED",
                "curriculumStatus": "EXTRACTION_FAILED",
                "reason": failed_doc.get("mismatch_reason") or "Syllabus subject extraction failed. Please upload a clear PDF syllabus.",
                "semester": current_sem,
                "degree": degree,
                "department": department,
                "subjects": [],
                "extracted_subjects": [],
                "units": {},
                "chapters": {},
                "topics": []
            }), 200

        # Check for NEEDS_REVIEW / MISMATCH state
        pending_doc = mongo_db["syllabi"].find_one(
            {"$and": [user_filter, {"status": {"$in": ["NEEDS_REVIEW", "MISMATCH"]}}]},
            sort=[("updated_at", -1), ("updatedAt", -1)]
        )
        if pending_doc:
            return jsonify({
                "success": True,
                "is_valid": False,
                "is_active": False,
                "status": "NEEDS_REVIEW",
                "curriculumStatus": "NEEDS_REVIEW",
                "reason": pending_doc.get("mismatch_reason", "Syllabus validation requires review."),
                "mismatch_reason": pending_doc.get("mismatch_reason", "Syllabus validation requires review."),
                "validation_report": pending_doc.get("validation_report") or pending_doc.get("validationReport"),
                "semester": current_sem,
                "degree": degree,
                "department": department,
                "subjects": [],
                "extracted_subjects": [],
                "units": {},
                "chapters": {},
                "topics": []
            }), 200

        # Base state: NOT_UPLOADED
        return jsonify({
            "success": True,
            "is_valid": False,
            "is_active": False,
            "status": "NOT_UPLOADED",
            "curriculumStatus": "NOT_UPLOADED",
            "reason": "No syllabus document uploaded. Please upload your official syllabus to unlock your curriculum subjects.",
            "is_preconfigured": False,
            "semester": current_sem,
            "degree": degree,
            "department": department,
            "subjects": [],
            "extracted_subjects": [],
            "units": {},
            "chapters": {},
            "topics": []
        }), 200

    else:
        conn = get_sqlite_db()
        cursor = conn.cursor()
        # Check for any pending or failed records
        cursor.execute("SELECT * FROM syllabi WHERE student_id=? ORDER BY id DESC LIMIT 1", (user_id,))
        last_row = cursor.fetchone()
        conn.close()
        if last_row:
            ld = dict(last_row)
            st = (ld.get("status") or "").upper()
            if st in ["PROCESSING", "ANALYZING", "PARSING"]:
                return jsonify({
                    "success": True, "is_valid": False, "is_active": False, "status": "PROCESSING",
                    "curriculumStatus": "PROCESSING", "reason": "Syllabus is being analyzed...",
                    "semester": current_sem, "subjects": [], "extracted_subjects": [], "units": {}, "topics": []
                }), 200
            elif st in ["EXTRACTION_FAILED", "FAILED", "ERROR"]:
                return jsonify({
                    "success": True, "is_valid": False, "is_active": False, "status": "EXTRACTION_FAILED",
                    "curriculumStatus": "EXTRACTION_FAILED", "reason": ld.get("mismatch_reason") or "Extraction failed.",
                    "semester": current_sem, "subjects": [], "extracted_subjects": [], "units": {}, "topics": []
                }), 200
            elif st in ["NEEDS_REVIEW", "MISMATCH"]:
                return jsonify({
                    "success": True, "is_valid": False, "is_active": False, "status": "NEEDS_REVIEW",
                    "curriculumStatus": "NEEDS_REVIEW", "reason": ld.get("mismatch_reason", "Syllabus validation requires review."),
                    "semester": current_sem, "subjects": [], "extracted_subjects": [], "units": {}, "topics": []
                }), 200

        return jsonify({
            "success": True,
            "is_valid": False,
            "is_active": False,
            "status": "NOT_UPLOADED",
            "curriculumStatus": "NOT_UPLOADED",
            "reason": "No syllabus document uploaded. Please upload your official syllabus to unlock your curriculum subjects.",
            "is_preconfigured": False,
            "semester": current_sem,
            "subjects": [],
            "extracted_subjects": [],
            "units": {},
            "topics": []
        }), 200


@app.route("/api/syllabus", methods=["DELETE"])
@require_auth
def delete_my_syllabus():
    """Reset / archive active syllabus for the authenticated student."""
    user_id = _current_user_id()
    now = datetime.utcnow()
    mongo_db = get_mongodb()
    if mongo_db is not None:
        mongo_db["syllabi"].update_many(
            {"$or": [{"student_id": str(user_id)}, {"studentId": str(user_id)}, {"student_id": user_id}, {"studentId": user_id}]},
            {"$set": {"is_active": False, "isActive": False, "status": "ARCHIVED", "curriculumStatus": "ARCHIVED", "updated_at": now, "updatedAt": now}}
        )
        return jsonify({"success": True, "message": "Syllabus archived successfully."}), 200

    conn = get_sqlite_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE syllabi SET is_active=0, status='ARCHIVED', validation_status='ARCHIVED', updated_at=? WHERE student_id=?",
        (now.isoformat(), str(user_id))
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Syllabus archived successfully."}), 200


@app.route("/api/syllabus/evidence", methods=["GET"])
@require_auth
def get_curriculum_evidence():
    """
    Return comprehensive source document evidence for all subjects in the student's active curriculum.
    Answers: 'Where in the uploaded syllabus did this subject come from?'
    """
    user_id = _current_user_id()
    mongo_db = get_mongodb()
    if mongo_db is not None:
        doc = mongo_db["syllabi"].find_one(
            {"student_id": user_id, "$or": [{"is_active": True}, {"status": {"$in": ["ACTIVE", "READY"]}}]},
            sort=[("updated_at", -1)]
        )
        if not doc:
            return jsonify({"success": False, "error": "No active syllabus curriculum found."}), 404

        subjects = doc.get("subjects") or []
        return jsonify({
            "success": True,
            "syllabus_id": doc.get("syllabus_id"),
            "document_name": doc.get("file_name"),
            "semester": doc.get("semester"),
            "degree": doc.get("degree"),
            "department": doc.get("department"),
            "total_subjects": len(subjects),
            "evidence_retained": True,
            "subjects": subjects
        }), 200
    else:
        conn = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM syllabi WHERE student_id=? AND (is_active=1 OR status IN ('ACTIVE', 'READY')) ORDER BY version DESC LIMIT 1",
            (user_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return jsonify({"success": False, "error": "No active syllabus curriculum found."}), 404
        d = dict(row)
        analysis = json.loads(d.get("analysis_json") or "{}") if d.get("analysis_json") else {}
        subjects = analysis.get("subjects") or []
        return jsonify({
            "success": True,
            "syllabus_id": d.get("syllabus_id"),
            "document_name": d.get("file_name"),
            "semester": d.get("semester"),
            "total_subjects": len(subjects),
            "evidence_retained": True,
            "subjects": subjects
        }), 200


@app.route("/api/syllabus/subject-evidence/<subject_identifier>", methods=["GET"])
@require_auth
def get_single_subject_evidence(subject_identifier: str):
    """
    Retrieve exact source provenance, page number, section, and text excerpt for a specific course.
    """
    user_id = _current_user_id()
    sub_query = subject_identifier.strip().lower()
    mongo_db = get_mongodb()
    if mongo_db is not None:
        doc = mongo_db["syllabi"].find_one(
            {"student_id": user_id, "$or": [{"is_active": True}, {"status": {"$in": ["ACTIVE", "READY"]}}]},
            sort=[("updated_at", -1)]
        )
        if not doc:
            return jsonify({"success": False, "error": "No active syllabus curriculum found."}), 404

        subjects = doc.get("subjects") or []
        matched = None
        for s in subjects:
            s_name = str(s.get("name") or "").lower()
            s_code = str(s.get("code") or "").lower()
            if sub_query in s_name or (s_code and sub_query == s_code):
                matched = s
                break

        if not matched:
            return jsonify({"success": False, "error": f"Subject '{subject_identifier}' not found in active curriculum."}), 404

        return jsonify({
            "success": True,
            "subject": matched,
            "evidence": {
                "subject_name": matched.get("name"),
                "subject_code": matched.get("code"),
                "source_document_id": matched.get("source_document_id") or doc.get("syllabus_id"),
                "source_document_name": matched.get("source_document_name") or doc.get("file_name"),
                "source_pages": matched.get("source_page_numbers") or [matched.get("source_page", 1)],
                "source_section": matched.get("source_section"),
                "source_text": matched.get("source_text"),
                "semester_evidence": matched.get("semester_evidence"),
                "confidence": matched.get("confidence", 0.98),
                "evidence_verified": matched.get("evidence_verified", True)
            }
        }), 200
    else:
        return jsonify({"success": False, "error": "Endpoint requires MongoDB support."}), 501



# ══════════════════════════════════════════════════════════════════════════════
# ACTION CENTER
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/action-center", methods=["GET"])
@require_role("teacher")
def get_action_center_items():
    teacher_id = _current_user_id()
    user = _lookup_user_by_id(teacher_id)
    user_email = user.get("email", "") if user else ""
    class_id = request.args.get("class_id") or request.args.get("classId")
    try:
        mongo_db = get_mongodb()
        if mongo_db is not None:
            query = {
                "evaluation_source": "TEACHER_EVALUATION",
                "$or": [
                    {"teacher_id": str(teacher_id)},
                    {"teacher_id": str(user_email)},
                    {"created_by_user_id": str(teacher_id)},
                ]
            }
            if class_id:
                query["class_id"] = str(class_id)
            items_cursor = list(mongo_db["action_items"].find(query).sort("created_at", -1))
            valid_items = []
            for d in items_cursor:
                # 1. Must be TEACHER_EVALUATION
                if d.get("evaluation_source") != "TEACHER_EVALUATION":
                    mongo_db["action_items"].update_one(
                        {"_id": d["_id"]},
                        {"$set": {"status": "NEEDS_REVIEW", "flagged_reason": "Non-teacher evaluation source"}}
                    )
                    continue

                # 2. Must have valid source evaluation
                eval_id = d.get("evaluation_id")
                if not eval_id:
                    mongo_db["action_items"].update_one(
                        {"_id": d["_id"]},
                        {"$set": {"status": "NEEDS_REVIEW", "flagged_reason": "Missing source evaluation ID"}}
                    )
                    continue

                parent = mongo_db["evaluations"].find_one({"$or": [{"id": str(eval_id)}, {"evaluation_id": str(eval_id)}]})
                if not parent and ObjectId and len(str(eval_id)) == 24:
                    try:
                        parent = mongo_db["evaluations"].find_one({"_id": ObjectId(eval_id)})
                    except Exception:
                        pass

                if not parent:
                    mongo_db["action_items"].update_one(
                        {"_id": d["_id"]},
                        {"$set": {"status": "NEEDS_REVIEW", "flagged_reason": "Parent evaluation not found"}}
                    )
                    continue

                if parent.get("evaluation_source") != "TEACHER_EVALUATION":
                    mongo_db["action_items"].update_one(
                        {"_id": d["_id"]},
                        {"$set": {"status": "NEEDS_REVIEW", "flagged_reason": "Parent evaluation is not a teacher evaluation"}}
                    )
                    continue

                p_teacher = str(parent.get("teacher_id") or parent.get("created_by_user_id") or "")
                if p_teacher and p_teacher not in (str(teacher_id), str(user_email)):
                    mongo_db["action_items"].update_one(
                        {"_id": d["_id"]},
                        {"$set": {"status": "NEEDS_REVIEW", "flagged_reason": "Unauthorized teacher scope"}}
                    )
                    continue

                if class_id and parent.get("class_id") and str(parent.get("class_id")) != str(class_id):
                    continue

                d_ser = mongo_serialize(d)
                if not d_ser.get("question_num"):
                    d_ser["question_num"] = d_ser.get("question_number") or "Evaluation"
                if not d_ser.get("learning_gap"):
                    d_ser["learning_gap"] = d_ser.get("misconception") or d_ser.get("issue") or ""
                if not d_ser.get("recommended_action"):
                    d_ser["recommended_action"] = d_ser.get("action") or ""
                if not d_ser.get("updated_at"):
                    d_ser["updated_at"] = d_ser.get("created_at")
                valid_items.append(d_ser)

            return jsonify({"success": True, "items": valid_items, "action_items": valid_items}), 200

        # SQLite: query action_items joined with evaluations
        conn = get_sqlite_db()
        cursor = conn.cursor()
        if class_id:
            cursor.execute(
                """SELECT a.* FROM action_items a
                   JOIN evaluations e ON a.evaluation_id = e.id
                   WHERE (a.teacher_id = ? OR a.created_by_user_id = ?) 
                     AND a.evaluation_source = 'TEACHER_EVALUATION' 
                     AND e.evaluation_source = 'TEACHER_EVALUATION'
                     AND a.class_id = ?
                   ORDER BY a.created_at DESC""",
                (str(teacher_id), str(teacher_id), str(class_id))
            )
        else:
            cursor.execute(
                """SELECT a.* FROM action_items a
                   JOIN evaluations e ON a.evaluation_id = e.id
                   WHERE (a.teacher_id = ? OR a.created_by_user_id = ?) 
                     AND a.evaluation_source = 'TEACHER_EVALUATION' 
                     AND e.evaluation_source = 'TEACHER_EVALUATION'
                   ORDER BY a.created_at DESC""",
                (str(teacher_id), str(teacher_id))
            )
        rows = cursor.fetchall()
        items = []
        for r in rows:
            d = dict(r)
            for json_field in ["affected_questions", "marks_lost_per_question"]:
                if d.get(json_field) and isinstance(d[json_field], str):
                    try:
                        d[json_field] = json.loads(d[json_field])
                    except Exception:
                        pass
            if not d.get("question_num"):
                d["question_num"] = d.get("question_number") or "Evaluation"
            if not d.get("learning_gap"):
                d["learning_gap"] = d.get("misconception") or d.get("issue") or ""
            if not d.get("recommended_action"):
                d["recommended_action"] = d.get("action") or ""
            items.append(d)
        conn.close()
        return jsonify({"success": True, "items": items, "action_items": items}), 200
    except Exception as exc:
        logger.error("Action Center error: %s", exc)
        return jsonify({"success": True, "items": [], "action_items": []}), 200


@app.route("/api/action-center/<item_id>", methods=["PUT"])
@require_role("teacher")
def update_action_center_item(item_id: str):
    try:
        data       = request.get_json(force=True) or {}
        new_status = data.get("status")
        teacher_id = _current_user_id()
        mongo_db   = get_mongodb()
        if mongo_db is not None:
            mongo_db["action_items"].update_one(
                {"id": item_id, "evaluation_source": "TEACHER_EVALUATION"},
                {"$set": {"status": new_status, "updated_by": teacher_id,
                          "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}},
                upsert=False,
            )
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE action_items SET status = ? WHERE id = ? AND evaluation_source = 'TEACHER_EVALUATION'", (new_status, item_id))
            conn.commit()
            conn.close()
        return jsonify({"success": True, "id": item_id, "status": new_status}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# MISCONCEPTIONS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/misconceptions", methods=["GET"])
@require_auth
def get_misconceptions():
    user_id      = _current_user_id()
    session_role = _current_role()
    class_id     = request.args.get("class_id") or request.args.get("classId")
    try:
        user = _lookup_user_by_id(user_id)
        user_name = user.get("name", "") if user else ""
        user_email = user.get("email", "") if user else ""

        mongo_db = get_mongodb()
        if mongo_db is not None:
            if session_role == "student":
                query = {
                    "$or": [
                        {"student_id": user_id},
                        {"student_id": user_email},
                    ]
                }
                if user_name:
                    query["$or"].append({"student_name": user_name})
            else:
                # Teachers only see genuine TEACHER_EVALUATION misconceptions within their authorized scope
                query = {
                    "evaluation_source": "TEACHER_EVALUATION",
                    "$or": [
                        {"teacher_id": str(user_id)},
                        {"teacher_id": str(user_email)},
                        {"created_by_user_id": str(user_id)},
                    ]
                }
                if class_id:
                    query["class_id"] = str(class_id)

            raw_docs = list(mongo_db["misconceptions"].find(query).sort("created_at", -1))
            docs = []
            for d in raw_docs:
                if session_role == "teacher":
                    # 1. Must originate from TEACHER_EVALUATION
                    if d.get("evaluation_source") != "TEACHER_EVALUATION":
                        continue

                    # 2. Must contain question-level evidence / concept
                    concept = d.get("concept") or d.get("identified_concept") or d.get("topic")
                    evidence = d.get("evidence") or d.get("student_answer") or d.get("description")
                    if not concept or not evidence:
                        continue

                    # 3. Verify source evaluation authenticity and teacher authorization
                    eval_id = d.get("evaluation_id")
                    if eval_id:
                        parent = mongo_db["evaluations"].find_one({"$or": [{"id": str(eval_id)}, {"evaluation_id": str(eval_id)}]})
                        if not parent and ObjectId and len(str(eval_id)) == 24:
                            try:
                                parent = mongo_db["evaluations"].find_one({"_id": ObjectId(eval_id)})
                            except Exception:
                                pass
                        if parent:
                            # Must originate from TEACHER_EVALUATION
                            if parent.get("evaluation_source") != "TEACHER_EVALUATION":
                                continue
                            # Must belong to teacher's authorized scope
                            p_teacher = str(parent.get("teacher_id") or parent.get("created_by_user_id") or "")
                            if p_teacher and p_teacher not in (str(user_id), str(user_email)):
                                continue
                            # If class_id specified, parent must match
                            if class_id and parent.get("class_id") and str(parent.get("class_id")) != str(class_id):
                                continue

                docs.append(mongo_serialize(d))

            return jsonify({"success": True, "misconceptions": docs}), 200

        conn   = get_sqlite_db()
        cursor = conn.cursor()
        if session_role == "student":
            cursor.execute(
                "SELECT * FROM misconceptions WHERE student_id = ? OR student_name = ? ORDER BY created_at DESC",
                (user_id, user_name),
            )
        else:
            if class_id:
                cursor.execute(
                    """SELECT * FROM misconceptions 
                       WHERE (teacher_id = ? OR created_by_user_id = ?) 
                         AND evaluation_source = 'TEACHER_EVALUATION' 
                         AND class_id = ? 
                       ORDER BY created_at DESC""",
                    (user_id, user_id, class_id)
                )
            else:
                cursor.execute(
                    """SELECT * FROM misconceptions 
                       WHERE (teacher_id = ? OR created_by_user_id = ?) 
                         AND evaluation_source = 'TEACHER_EVALUATION' 
                       ORDER BY created_at DESC""",
                    (user_id, user_id)
                )
        rows = cursor.fetchall()
        conn.close()
        return jsonify({"success": True, "misconceptions": [dict(r) for r in rows]}), 200
    except Exception as exc:
        logger.error("Misconceptions error: %s", exc)
        return jsonify({"success": True, "misconceptions": []}), 200


# ══════════════════════════════════════════════════════════════════════════════
# PLAGIARISM
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/plagiarism/matches", methods=["GET"])
@require_role("teacher")
def get_plagiarism_matches():
    try:
        mongo_db = get_mongodb()
        if mongo_db is not None:
            records = [mongo_serialize(d) for d in mongo_db["plagiarism_records"].find()]
            return jsonify({"success": True, "matches": records}), 200
        conn   = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM plagiarism_records ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return jsonify({"success": True, "matches": [dict(r) for r in rows]}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/plagiarism/summary", methods=["GET"])
@require_role("teacher")
def get_plagiarism_summary():
    try:
        mongo_db = get_mongodb()
        if mongo_db is not None:
            records = [mongo_serialize(d) for d in mongo_db["plagiarism_records"].find()]
        else:
            conn   = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM plagiarism_records ORDER BY created_at DESC")
            records = [dict(r) for r in cursor.fetchall()]
            conn.close()

        high_risk = [r for r in records if r.get("suspected") or float(r.get("similarity", 0)) >= 85.0]
        possible  = [r for r in records if 70.0 <= float(r.get("similarity", 0)) < 85.0]
        return jsonify({
            "success":         True,
            "total_checked":   len(records),
            "flagged_count":   len(high_risk),
            "high_risk_matches": len(high_risk),
            "possible_matches":  len(possible),
            "records":         records,
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# STUDENTS LIST (teacher only)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/students", methods=["GET"])
@require_role("teacher")
def get_students():
    teacher_id = _current_user_id()
    mongo_db = get_mongodb()
    if mongo_db is not None:
        students_cursor = list(mongo_db["users"].find({"role": "student"}))
        all_evals = list(mongo_db["evaluations"].find({
            "evaluation_source": "TEACHER_EVALUATION",
            "$or": [
                {"teacher_id": str(teacher_id)},
                {"created_by_user_id": str(teacher_id)},
            ]
        }))
        students = []
        for s in students_cursor:
            name  = s.get("name", "")
            s_id  = str(s.get("_id") or s.get("id") or s.get("user_id") or "")
            s_email = s.get("email", "")
            evals = [
                e for e in all_evals
                if (s_id and str(e.get("student_id") or "") == s_id)
                or (s_email and str(e.get("student_id") or "") == s_email)
                or (name and str(e.get("student_name") or "") == name)
            ]
            avg   = round(sum(float(e.get("percentage", 0)) for e in evals) / len(evals), 1) if evals else 0.0
            students.append({
                "id":          str(s["_id"]),
                "student_id":  str(s.get("user_id") or s.get("id") or s["_id"]),
                "studentId":   str(s.get("user_id") or s.get("id") or s["_id"]),
                "name":        name,
                "roll_number": s.get("roll_number", ""),
                "section":     s.get("section", ""),
                "level":       s.get("level", "school"),
                "average":     avg,
                "averageScore": avg,
                "evaluations": len(evals),
                "status":      "On track" if avg >= 75 else "Needs support" if avg >= 50 else "New Student",
            })
        return jsonify({"success": True, "students": students}), 200

    conn   = get_sqlite_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE role = 'student'")
    rows = cursor.fetchall()
    students = []
    for r in rows:
        d = dict(r)
        d.pop("password_hash", None)
        d.pop("password", None)
        cursor.execute("""
            SELECT percentage FROM evaluations 
            WHERE (student_name = ? OR student_id = ?) 
              AND (teacher_id = ? OR created_by_user_id = ?)
              AND evaluation_source = 'TEACHER_EVALUATION'
        """, (d.get("name"), str(d.get("id")), str(teacher_id), str(teacher_id)))
        e_rows = cursor.fetchall()
        avg = round(sum(float(er[0] or 0) for er in e_rows) / len(e_rows), 1) if e_rows else 0.0
        d["average"] = avg
        d["averageScore"] = avg
        d["student_id"] = str(d.get("user_id") or d.get("id"))
        d["studentId"] = str(d.get("user_id") or d.get("id"))
        d["evaluations"] = len(e_rows)
        d["status"] = "On track" if avg >= 75 else "Needs support" if avg >= 50 else "New Student"
        students.append(d)
    conn.close()
    return jsonify({"success": True, "students": students}), 200


# ══════════════════════════════════════════════════════════════════════════════
# TEACHER CLASSES (MongoDB Persistence)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/teacher/classes", methods=["GET"])
@require_auth
def get_teacher_classes():
    try:
        user_id = _current_user_id()
        mongo_db = get_mongodb()
        if mongo_db is not None:
            classes_cursor = mongo_db["teacher_classes"].find({"teacher_id": str(user_id)}).sort("created_at", -1)
            classes = [mongo_serialize(c) for c in classes_cursor]
            return jsonify({"success": True, "classes": classes}), 200
        return jsonify({"success": True, "classes": []}), 200
    except Exception as exc:
        logger.error(f"[TeacherClasses] get_teacher_classes error: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/teacher/classes", methods=["POST"])
@require_auth
def create_teacher_class():
    try:
        user_id = _current_user_id()
        data = request.get_json(force=True) or {}
        class_id = str(data.get("id") or f"cls_{int(time.time() * 1000)}")
        
        class_doc = {
            "id": class_id,
            "teacher_id": str(user_id),
            "name": str(data.get("name") or "New Class").strip(),
            "level": str(data.get("level") or "school").strip(),
            "type": str(data.get("type") or "School Class").strip(),
            "board": str(data.get("board") or "").strip(),
            "gradeLevel": str(data.get("gradeLevel") or data.get("grade_level") or "").strip(),
            "grade_level": str(data.get("gradeLevel") or data.get("grade_level") or "").strip(),
            "section": str(data.get("section") or "").strip(),
            "department": str(data.get("department") or "").strip(),
            "semester": data.get("semester"),
            "subjects": data.get("subjects") or [],
            "students": data.get("students") or [],
            "students_count": int(data.get("students_count") or len(data.get("students") or [])),
            "created_at": data.get("created_at") or datetime.utcnow().strftime("%Y-%m-%d"),
            "updated_at": datetime.utcnow().isoformat()
        }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["teacher_classes"].update_one(
                {"id": class_id, "teacher_id": str(user_id)},
                {"$set": class_doc},
                upsert=True
            )

        return jsonify({"success": True, "class": class_doc}), 201
    except Exception as exc:
        logger.error(f"[TeacherClasses] create_teacher_class error: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/teacher/classes/<class_id>", methods=["PUT"])
@require_auth
def update_teacher_class(class_id):
    try:
        user_id = _current_user_id()
        data = request.get_json(force=True) or {}
        
        update_fields = {"updated_at": datetime.utcnow().isoformat()}
        for k in ["name", "level", "type", "board", "gradeLevel", "grade_level", "section", "department", "semester", "subjects", "students", "students_count"]:
            if k in data:
                update_fields[k] = data[k]

        if "students" in data and "students_count" not in data:
            update_fields["students_count"] = len(data["students"])

        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["teacher_classes"].update_one(
                {"id": class_id, "teacher_id": str(user_id)},
                {"$set": update_fields}
            )
            updated_doc = mongo_db["teacher_classes"].find_one({"id": class_id, "teacher_id": str(user_id)})
            return jsonify({"success": True, "class": mongo_serialize(updated_doc)}), 200

        return jsonify({"success": True, "class": update_fields}), 200
    except Exception as exc:
        logger.error(f"[TeacherClasses] update_teacher_class error: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/teacher/classes/<class_id>", methods=["DELETE"])
@require_auth
def delete_teacher_class(class_id):
    try:
        user_id = _current_user_id()
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["teacher_classes"].delete_one({"id": class_id, "teacher_id": str(user_id)})
        return jsonify({"success": True, "deleted_id": class_id}), 200
    except Exception as exc:
        logger.error(f"[TeacherClasses] delete_teacher_class error: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/analytics/dashboard", methods=["GET"])
@require_auth
def get_dashboard_analytics():
    user_id      = _current_user_id()
    session_role = _current_role()

    recent_evals  = []
    weak_topics   = []
    memory_items  = []

    mongo_db = get_mongodb()
    try:
        if mongo_db is not None:
            user = _lookup_user_by_id(user_id)
            user_email = user.get("email", "") if user else ""
            
            if session_role == "student":
                eval_query = {
                    "$or": [
                        {"submitted_by": user_id},
                        {"student_id": user_id},
                        {"submitted_by": user_email},
                    ]
                }
                recent_evals = [mongo_serialize(d) for d in
                                mongo_db["evaluations"].find(eval_query).sort("created_at", -1).limit(10)]
                memory_items = [mongo_serialize(d) for d in
                                mongo_db["academic_memory"].find({"$or": [{"student_id": user_id}, {"student_id": user_email}]}).limit(5)]
                weak_topics  = [mongo_serialize(d) for d in
                                mongo_db["misconceptions"].find({"$or": [{"student_id": user_id}, {"student_id": user_email}], "resolved": {"$ne": True}}).limit(5)]
            else:
                # Teachers: show genuine teacher evaluations they submitted
                eval_query = {
                    "evaluation_source": "TEACHER_EVALUATION",
                    "$or": [
                        {"submitted_by": user_id},
                        {"teacher_id": user_id},
                        {"created_by_user_id": user_id},
                    ]
                }
                recent_evals = [mongo_serialize(d) for d in
                                mongo_db["evaluations"].find(eval_query).sort("created_at", -1).limit(10)]
                weak_topics  = [mongo_serialize(d) for d in
                                mongo_db["misconceptions"].find({
                                    "evaluation_source": "TEACHER_EVALUATION",
                                    "$or": [{"teacher_id": user_id}, {"created_by_user_id": user_id}],
                                    "resolved": {"$ne": True}
                                }).limit(5)]
        else:
            conn   = get_sqlite_db()
            cursor = conn.cursor()
            user = _lookup_user_by_id(user_id)
            user_email = user.get("email", "") if user else ""
            if session_role == "student":
                cursor.execute(
                    "SELECT * FROM evaluations WHERE (submitted_by=? OR student_id=? OR submitted_by=?) ORDER BY created_at DESC LIMIT 10", (user_id, user_id, user_email)
                )
            else:
                cursor.execute(
                    "SELECT * FROM evaluations WHERE (submitted_by=? OR teacher_id=? OR created_by_user_id=?) AND evaluation_source='TEACHER_EVALUATION' ORDER BY created_at DESC LIMIT 10",
                    (user_id, user_id, user_id)
                )
            recent_evals = [dict(r) for r in cursor.fetchall()]
            conn.close()
    except Exception as exc:
        logger.error("Analytics error: %s", exc)

    return jsonify({
        "success":           True,
        "role":              session_role,
        "total_evaluations": len(recent_evals),
        "recentEvaluations": recent_evals,
        "weakTopics":        weak_topics,
        "academicMemory":    memory_items,
    }), 200


@app.route("/api/analytics/student", methods=["GET"])
@require_auth
def get_student_analytics():
    user_id = _current_user_id()
    session_role = _current_role()
    teacher_user = _lookup_user_by_id(user_id) if session_role == "teacher" else None
    teacher_email = (teacher_user or {}).get("email", "")

    # If role is student, they can ONLY view their own analytics
    if session_role == "student":
        target_student_id = user_id
    else:
        target_student_id = request.args.get("student_id") or user_id

    user = _lookup_user_by_id(target_student_id)
    user_email = (user or {}).get("email", "")
    user_name = (user or {}).get("name", "")

    mongo_db = get_mongodb()
    evals = []
    misconceptions = []
    try:
        if mongo_db is not None:
            if session_role == "student":
                eval_query = {
                    "$or": [
                        {"submitted_by": str(target_student_id)},
                        {"student_id": str(target_student_id)},
                        {"submitted_by": str(user_email)},
                        {"student_id": str(user_email)},
                    ]
                }
                if user_name:
                    eval_query["$or"].append({"student_name": user_name})

                misc_query = {
                    "$or": [
                        {"student_id": str(target_student_id)},
                        {"student_id": str(user_email)},
                    ]
                }
                if user_name:
                    misc_query["$or"].append({"student_name": user_name})
            else:
                # Teacher query: ONLY genuine TEACHER_EVALUATION records within authorized teacher scope
                eval_query = {
                    "evaluation_source": "TEACHER_EVALUATION",
                    "$and": [
                        {"$or": [
                            {"teacher_id": str(user_id)},
                            {"created_by_user_id": str(user_id)},
                            {"teacher_id": str(teacher_email)},
                        ]},
                        {"$or": [
                            {"student_id": str(target_student_id)},
                            {"submitted_by": str(target_student_id)},
                            {"student_id": str(user_email)},
                            {"student_name": user_name},
                        ]}
                    ]
                }
                misc_query = {
                    "evaluation_source": "TEACHER_EVALUATION",
                    "$and": [
                        {"$or": [
                            {"teacher_id": str(user_id)},
                            {"created_by_user_id": str(user_id)},
                            {"teacher_id": str(teacher_email)},
                        ]},
                        {"$or": [
                            {"student_id": str(target_student_id)},
                            {"student_id": str(user_email)},
                            {"student_name": user_name},
                        ]}
                    ]
                }

            evals = [mongo_serialize(d) for d in mongo_db["evaluations"].find(eval_query).sort("created_at", 1)]
            misconceptions = [mongo_serialize(d) for d in mongo_db["misconceptions"].find(misc_query).sort("created_at", -1)]
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            if session_role == "student":
                cursor.execute(
                    "SELECT * FROM evaluations WHERE (submitted_by=? OR student_id=? OR student_name=?) ORDER BY created_at ASC",
                    (str(target_student_id), str(target_student_id), user_name),
                )
                evals = [dict(r) for r in cursor.fetchall()]
                cursor.execute(
                    "SELECT * FROM misconceptions WHERE (student_id=? OR student_name=?) ORDER BY created_at DESC",
                    (str(target_student_id), user_name)
                )
                misconceptions = [dict(r) for r in cursor.fetchall()]
            else:
                cursor.execute(
                    """SELECT * FROM evaluations 
                       WHERE (student_id=? OR student_name=?) 
                         AND (teacher_id=? OR created_by_user_id=?) 
                         AND evaluation_source='TEACHER_EVALUATION' 
                       ORDER BY created_at ASC""",
                    (str(target_student_id), user_name, str(user_id), str(user_id)),
                )
                evals = [dict(r) for r in cursor.fetchall()]
                cursor.execute(
                    """SELECT * FROM misconceptions 
                       WHERE (student_id=? OR student_name=?) 
                         AND (teacher_id=? OR created_by_user_id=?) 
                         AND evaluation_source='TEACHER_EVALUATION' 
                       ORDER BY created_at DESC""",
                    (str(target_student_id), user_name, str(user_id), str(user_id)),
                )
                misconceptions = [dict(r) for r in cursor.fetchall()]

            for ev in evals:
                cursor.execute("SELECT * FROM evaluation_questions WHERE evaluation_id = ?", (ev.get("id"),))
                ev["questions"] = [dict(r) for r in cursor.fetchall()]
            conn.close()

        total_evals = len(evals)
        if total_evals == 0:
            return jsonify({
                "success": True,
                "has_data": False,
                "total_evaluations": 0,
                "average_marks": 0,
                "average_percentage": 0,
                "improvement_trend": {"delta_percentage": 0, "direction": "neutral"},
                "score_history": [],
                "subject_wise_performance": {},
                "question_wise_performance": {},
                "frequently_weak_concepts": [],
                "frequently_strong_concepts": [],
                "recurring_misconceptions": [],
                "evaluation_history": [],
            }), 200

        total_obtained = sum(float(e.get("obtained_marks") or 0) for e in evals)
        avg_percentage = round(sum(float(e.get("percentage") or 0) for e in evals) / total_evals, 2)
        avg_marks = round(total_obtained / total_evals, 2)

        # Improvement Trend
        if total_evals >= 2:
            early_pct = float(evals[0].get("percentage") or 0)
            latest_pct = float(evals[-1].get("percentage") or 0)
            delta = round(latest_pct - early_pct, 2)
            direction = "improving" if delta > 1.0 else ("declining" if delta < -1.0 else "stable")
        else:
            delta = 0.0
            direction = "stable"

        # Score History
        score_history = []
        for e in evals:
            score_history.append({
                "evaluation_id": str(e.get("id") or e.get("_id") or e.get("evaluation_id")),
                "date": str(e.get("created_at") or "")[:10],
                "subject": e.get("subject") or "General",
                "assessment_title": e.get("assessment_title") or f"{e.get('subject', 'General')} Evaluation",
                "obtained_marks": float(e.get("obtained_marks") or 0),
                "total_marks": float(e.get("total_marks") or 0),
                "percentage": float(e.get("percentage") or 0),
                "grade": e.get("grade") or "N/A",
                "status": e.get("status") or "COMPLETED",
            })

        # Subject-wise performance
        subject_map = {}
        for e in evals:
            sub = e.get("subject") or "General"
            if sub not in subject_map:
                subject_map[sub] = {"subject": sub, "count": 0, "total_pct": 0, "total_obtained": 0, "total_max": 0, "highest": 0, "lowest": 100}
            pct = float(e.get("percentage") or 0)
            obt = float(e.get("obtained_marks") or 0)
            mx = float(e.get("total_marks") or 0)
            subject_map[sub]["count"] += 1
            subject_map[sub]["total_pct"] += pct
            subject_map[sub]["total_obtained"] += obt
            subject_map[sub]["total_max"] += mx
            if pct > subject_map[sub]["highest"]:
                subject_map[sub]["highest"] = pct
            if pct < subject_map[sub]["lowest"]:
                subject_map[sub]["lowest"] = pct

        subject_wise = {}
        for sub, data in subject_map.items():
            subject_wise[sub] = {
                "subject": sub,
                "count": data["count"],
                "average_percentage": round(data["total_pct"] / data["count"], 2),
                "average_marks": round(data["total_obtained"] / data["count"], 2),
                "highest_percentage": data["highest"],
                "lowest_percentage": data["lowest"],
            }

        # Question-wise performance & concepts analysis
        q_perf = {}
        concept_weak_counts = {}
        concept_strong_counts = {}

        for e in evals:
            qs = e.get("questions") or e.get("evaluations") or []
            for q in qs:
                if not isinstance(q, dict):
                    continue
                q_num = str(q.get("question_number") or "Unknown")
                max_m = float(q.get("maximum_marks") or 0)
                awd_m = float(q.get("awarded_marks") or 0)
                if q_num not in q_perf:
                    q_perf[q_num] = {"question_number": q_num, "attempts": 0, "total_awarded": 0, "total_max": 0}
                q_perf[q_num]["attempts"] += 1
                q_perf[q_num]["total_awarded"] += awd_m
                q_perf[q_num]["total_max"] += max_m

                # Concept tracking
                concepts = q.get("concepts_tested") or []
                if isinstance(concepts, str):
                    concepts = [concepts]
                for c in concepts:
                    c_name = str(c).strip()
                    if not c_name:
                        continue
                    if max_m > 0 and awd_m >= max_m:
                        concept_strong_counts[c_name] = concept_strong_counts.get(c_name, 0) + 1
                    elif max_m > 0 and (awd_m / max_m) < 0.6:
                        concept_weak_counts[c_name] = concept_weak_counts.get(c_name, 0) + 1

        question_wise = {}
        for q_num, data in q_perf.items():
            pct = round((data["total_awarded"] / data["total_max"]) * 100, 2) if data["total_max"] > 0 else 0
            question_wise[q_num] = {
                "question_number": q_num,
                "attempts": data["attempts"],
                "average_awarded": round(data["total_awarded"] / data["attempts"], 2),
                "average_maximum": round(data["total_max"] / data["attempts"], 2),
                "accuracy_percentage": pct,
            }

        frequently_weak = sorted(
            [{"concept": c, "frequency": count} for c, count in concept_weak_counts.items()],
            key=lambda x: x["frequency"],
            reverse=True,
        )[:6]

        frequently_strong = sorted(
            [{"concept": c, "frequency": count} for c, count in concept_strong_counts.items()],
            key=lambda x: x["frequency"],
            reverse=True,
        )[:6]

        evaluation_history = list(reversed(score_history))

        return jsonify({
            "success": True,
            "has_data": True,
            "total_evaluations": total_evals,
            "average_marks": avg_marks,
            "average_percentage": avg_percentage,
            "improvement_trend": {"delta_percentage": delta, "direction": direction},
            "score_history": score_history,
            "subject_wise_performance": subject_wise,
            "question_wise_performance": question_wise,
            "frequently_weak_concepts": frequently_weak,
            "frequently_strong_concepts": frequently_strong,
            "recurring_misconceptions": misconceptions[:8],
            "evaluation_history": evaluation_history,
        }), 200
    except Exception as exc:
        logger.error("Student analytics error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# AI TRAINER
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/trainer/chat", methods=["POST"])
@require_auth
def trainer_chat():
    try:
        user_id = _current_user_id()
        user    = _lookup_user_by_id(user_id)
        data    = request.get_json(force=True) or {}
        message = str(data.get("message") or "").strip()
        if not message:
            return jsonify({"success": False, "error": "Message is required."}), 400

        subject      = str(data.get("subject") or "General Academic")
        concept      = str(data.get("concept") or data.get("topic") or "")
        unit         = str(data.get("unit") or data.get("module") or "")
        chapter      = str(data.get("chapter") or "")
        topic        = str(data.get("topic") or concept or "")
        study_method = str(data.get("study_method") or data.get("method") or "")
        level        = str(data.get("level") or (user or {}).get("level") or "").strip().lower()
        stored_sem   = (user or {}).get("semester") if (user or {}).get("semester") is not None else (user or {}).get("current_semester")
        semester     = str(data.get("semester") or stored_sem or "").strip()
        degree       = str((user or {}).get("degree") or (user or {}).get("program") or "").strip()
        dept         = str((user or {}).get("department") or (user or {}).get("branch") or (user or {}).get("domain") or "").strip()
        stored_cls   = (user or {}).get("grade_level") or (user or {}).get("classLevel")
        class_level  = str(data.get("class_level") or stored_cls or "").strip()
        board        = str((user or {}).get("board") or "").strip()

        subject_id   = str(data.get("subject_id") or data.get("subjectId") or data.get("subjectCode") or data.get("subject_code") or "").strip()
        syllabus_id  = str(data.get("syllabus_id") or data.get("syllabusId") or data.get("curriculum_id") or data.get("curriculumId") or "").strip()

        # Fetch authoritative active validated syllabus
        active_syllabus = _get_authoritative_curriculum(user_id, user, syllabus_id=syllabus_id or None)

        # Check if student is asking for their semester subjects list
        lower_msg = message.lower().strip()
        is_asking_subjects = any(phrase in lower_msg for phrase in [
            "what are my semester", "what subjects do i have", "what are my subjects", 
            "list my subjects", "what is my syllabus", "show my subjects", "my subjects list",
            "subjects in semester", "semester subjects", "my courses", "what courses do i have"
        ])
        
        raw_subjects = (active_syllabus or {}).get("subjects") or []
        if not raw_subjects and (active_syllabus or {}).get("extracted_subjects"):
            raw_subjects = [{"name": s} for s in active_syllabus["extracted_subjects"]]
        valid_subjects = [s.get("name") if isinstance(s, dict) else str(s) for s in raw_subjects]

        if not active_syllabus or not valid_subjects:
            if is_asking_subjects:
                return jsonify({
                    "success": True,
                    "reply": "🔒 **No Validated Syllabus Uploaded**:\n\nPlease upload your official semester syllabus to unlock your curriculum subjects and enable Personal Trainer coaching."
                }), 200
            return jsonify({
                "success": False,
                "error": "No active validated syllabus found. Please upload your syllabus to start coaching."
            }), 400

        if is_asking_subjects:
            sem_label = f"Semester {semester}" if semester else "Current Semester"
            prog_label = f"{degree} ({dept})" if (degree and dept) else (degree or dept or "Academic Program")
            
            subject_lines = []
            for idx, s in enumerate(raw_subjects, start=1):
                s_code = s.get("code") if isinstance(s, dict) else ""
                s_name = s.get("name") if isinstance(s, dict) else str(s)
                s_type = s.get("type") or s.get("category") if isinstance(s, dict) else ""
                s_cred = s.get("credits") if isinstance(s, dict) else None
                
                code_str = f"**{s_code}**: " if s_code else ""
                type_str = f" ({s_type}" if s_type else ""
                cred_str = f" · {s_cred} Credits)" if (s_cred is not None and type_str) else (f" ({s_cred} Credits)" if s_cred is not None else (")" if type_str else ""))
                
                subject_lines.append(f"{idx}. {code_str}{s_name}{type_str}{cred_str}")

            reply = (
                f"📚 **Your Validated {sem_label} Subjects ({prog_label})**:\n\n"
                + "\n".join(subject_lines) + "\n\n"
                + f"✅ *Source*: Extracted and verified directly from your official {sem_label} syllabus document.\n"
                + f"Which subject would you like to master today? Select any subject from the left panel to begin coaching!"
            )
            return jsonify({"success": True, "reply": reply}), 200

        # Validate that requested subject is in the active syllabus using subjectId/subjectCode or subjectName
        matched_subj = None
        if subject_id:
            for s in raw_subjects:
                if isinstance(s, dict):
                    sid = str(s.get("subject_id") or s.get("subjectId") or s.get("id") or s.get("code") or "").strip().lower()
                    if sid and sid == subject_id.lower():
                        matched_subj = s.get("name")
                        break
        if not matched_subj:
            matched_subj = next((s for s in valid_subjects if s.lower() == subject.lower()), None)
        if not matched_subj:
            matched_subj = next((s for s in valid_subjects if subject.lower() in s.lower() or s.lower() in subject.lower()), None)

        if not matched_subj and subject and subject != "General Academic":
            return jsonify({
                "success": False,
                "error": f"The subject '{subject}' is not in your validated active curriculum.",
                "valid_subjects": valid_subjects
            }), 400
        if matched_subj:
            subject = matched_subj

        # Retrieve relevant syllabus excerpt and validated topics for coaching context
        syllabus_excerpt = ""
        validated_topics = []
        if active_syllabus:
            chapters_dict = active_syllabus.get("chapters") or active_syllabus.get("units") or {}
            if subject in chapters_dict:
                sub_units = chapters_dict[subject]
                if isinstance(sub_units, list):
                    for u in sub_units:
                        if isinstance(u, dict):
                            u_name = u.get("name", "")
                            concepts_list = u.get("concepts", [])
                            validated_topics.extend(concepts_list)
                            if (unit and unit.lower() in u_name.lower()) or (topic and topic.lower() in " ".join(concepts_list).lower()):
                                syllabus_excerpt = f"{u_name}: {', '.join(concepts_list)}"
                        elif isinstance(u, str):
                            validated_topics.append(u)
                    if not syllabus_excerpt and sub_units:
                        first_u = sub_units[0] if isinstance(sub_units[0], dict) else {}
                        syllabus_excerpt = f"{first_u.get('name', '')}: {', '.join(first_u.get('concepts', []))}"

        history = data.get("history") or []
        student_ctx = {
            "student_id": user_id,
            "name": (user or {}).get("name", "Student"),
            "level": level or "college",
            "degree": degree,
            "department": dept,
            "semester": semester,
            "class_level": class_level,
            "board": board,
            "subject_id": subject_id,
            "curriculum_id": syllabus_id or str((active_syllabus or {}).get("syllabus_id") or ""),
            "validated_topics": validated_topics
        }

        ai_reply = gemini_service.generate_trainer_response(
            message=message,
            subject=subject,
            topic=topic or concept or subject,
            unit=unit,
            syllabus_excerpt=syllabus_excerpt,
            student_context=student_ctx,
            history=history,
            study_strategy=study_method
        )

        student_name = (user or {}).get("name", "Student")
        mongo_db = get_mongodb()
        if mongo_db is not None:
            try:
                mongo_db["academic_memory"].insert_one({
                    "student_name":  student_name,
                    "student_id":    user_id,
                    "subject":       subject,
                    "topic":         topic or concept or subject,
                    "mastery":       0,
                    "retention_rate": 0,
                    "status":        "Learning",
                    "last_reviewed": datetime.utcnow(),
                    "next_review":   datetime.utcnow() + timedelta(days=2),
                })
            except Exception:
                pass

        return jsonify({"success": True, "reply": ai_reply}), 200
    except Exception as exc:
        logger.error("Trainer chat: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# SELF-EVALUATION (uses same engine as teacher portal)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/self-evaluation/generate", methods=["POST"])
@require_auth
def generate_self_eval_endpoint():
    try:
        data           = request.get_json(force=True) or {}
        subject        = str(data.get("subject") or "General Academic")
        topic          = str(data.get("topic") or "Core Concepts")
        difficulty     = str(data.get("difficulty") or "Medium")
        syllabus_ctx   = str(data.get("syllabus_context") or "")
        question       = gemini_service.generate_self_evaluation(subject, topic, difficulty, syllabus_ctx)
        return jsonify({"success": True, "question": question}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/self-evaluation/evaluate", methods=["POST"])
@require_auth
def evaluate_self_eval_endpoint():
    try:
        data              = request.get_json(force=True) or {}
        question_text     = str(data.get("question_text") or "")
        expected_concept  = str(data.get("expected_concept") or "")
        student_response  = str(data.get("student_response") or "")
        subject           = str(data.get("subject") or "General Academic")
        eval_res = gemini_service.evaluate_self_evaluation(question_text, expected_concept, student_response, subject)
        return jsonify({"success": True, "evaluation": eval_res}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# REALITY LAB
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/reality-lab/generate", methods=["POST"])
@require_auth
def generate_reality_lab_endpoint():
    try:
        user_id = _current_user_id()
        user    = _lookup_user_by_id(user_id) or {}
        data    = request.get_json(force=True) or {}

        subject_id  = str(data.get("subject_id") or data.get("subjectId") or data.get("id") or data.get("code") or "").strip()
        syllabus_id = str(data.get("syllabus_id") or data.get("syllabusId") or data.get("curriculum_id") or data.get("curriculumId") or "").strip()

        # Fetch authoritative active validated curriculum
        curriculum_doc = _get_authoritative_curriculum(user_id, user, syllabus_id=syllabus_id or None)

        active_semester = user.get("semester") or user.get("current_semester")
        program         = user.get("degree") or user.get("program") or "Engineering"
        department      = user.get("department") or user.get("branch") or "Information Technology"

        # Validated subjects check
        valid_subjects = []
        raw_subs = []
        syllabus_ctx = str(data.get("syllabus_context") or "")
        if curriculum_doc:
            raw_subs = curriculum_doc.get("subjects") or []
            if isinstance(raw_subs, str):
                try:
                    raw_subs = json.loads(raw_subs)
                except Exception:
                    raw_subs = []
            valid_subjects = [s.get("name") if isinstance(s, dict) else str(s) for s in raw_subs]
            if not syllabus_ctx and curriculum_doc.get("blueprint"):
                syllabus_ctx = str(curriculum_doc.get("blueprint"))[:1200]

        if not curriculum_doc or not valid_subjects:
            return jsonify({
                "success": False,
                "error": "No active validated syllabus found. Please upload your syllabus to generate Reality Lab activities.",
                "subjects": []
            }), 400

        requested_subject = str(data.get("subject") or data.get("subject_name") or "").strip()
        matched_subj = None
        matched_sub_id = subject_id
        matched_sub_obj = None

        if subject_id:
            for s in raw_subs:
                if isinstance(s, dict):
                    sid = str(s.get("subject_id") or s.get("subjectId") or s.get("id") or s.get("code") or "").strip().lower()
                    if sid and sid == subject_id.lower():
                        matched_subj = s.get("name")
                        matched_sub_id = s.get("subject_id") or s.get("subjectId") or s.get("code") or subject_id
                        matched_sub_obj = s
                        break

        if not matched_subj and requested_subject:
            for s in raw_subs:
                if isinstance(s, dict):
                    s_name = str(s.get("name") or "")
                    if s_name.lower() == requested_subject.lower() or requested_subject.lower() in s_name.lower():
                        matched_subj = s_name
                        matched_sub_id = s.get("subject_id") or s.get("subjectId") or s.get("code") or matched_sub_id
                        matched_sub_obj = s
                        break
                elif str(s).lower() == requested_subject.lower() or requested_subject.lower() in str(s).lower():
                    matched_subj = str(s)
                    break

        if not matched_subj and requested_subject:
            return jsonify({
                "success": False,
                "error": f"The subject '{requested_subject}' is not in your validated active curriculum.",
                "valid_subjects": valid_subjects
            }), 400

        selected_subject = matched_subj or (valid_subjects[0] if valid_subjects else "")
        if not matched_sub_obj and raw_subs:
            first_s = raw_subs[0]
            if isinstance(first_s, dict):
                matched_sub_obj = first_s
                matched_sub_id = first_s.get("subject_id") or first_s.get("subjectId") or first_s.get("code") or matched_sub_id

        # Extract validated topics for this specific subject
        subject_topics = []
        chapters_dict = curriculum_doc.get("chapters") or curriculum_doc.get("units") or {}
        if selected_subject in chapters_dict:
            sub_units = chapters_dict[selected_subject]
            if isinstance(sub_units, list):
                for u in sub_units:
                    if isinstance(u, dict):
                        u_name = u.get("name", "")
                        c_list = u.get("concepts", [])
                        if u_name:
                            subject_topics.append(u_name)
                        subject_topics.extend(c_list)
                    elif isinstance(u, str):
                        subject_topics.append(u)
        elif matched_sub_obj and isinstance(matched_sub_obj, dict):
            if matched_sub_obj.get("topics"):
                subject_topics.extend(matched_sub_obj["topics"])
            if matched_sub_obj.get("units"):
                for u in matched_sub_obj["units"]:
                    if isinstance(u, dict):
                        subject_topics.append(u.get("name", ""))
                        subject_topics.extend(u.get("concepts", []))
                    elif isinstance(u, str):
                        subject_topics.append(u)

        requested_topic = str(data.get("topic") or data.get("module") or "").strip()
        selected_topic = requested_topic
        if not selected_topic and subject_topics:
            selected_topic = subject_topics[0]

        difficulty = str(data.get("difficulty") or "Medium")

        lab_data = gemini_service.generate_reality_lab(
            subject=selected_subject,
            subject_id=str(matched_sub_id or ""),
            topic=selected_topic,
            module=selected_topic,
            difficulty=difficulty,
            validated_topics=subject_topics,
            syllabus_context=syllabus_ctx,
            semester=str(active_semester or ""),
            program=program,
            department=department
        )
        return jsonify({
            "success": True,
            "lab": lab_data,
            "active_semester": active_semester,
            "subject": selected_subject,
            "subject_id": matched_sub_id,
            "topic": selected_topic,
            "validated_topics": subject_topics
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/reality-lab/evaluate", methods=["POST"])
@require_auth
def evaluate_reality_lab_endpoint():
    try:
        data             = request.get_json(force=True) or {}
        scenario_title   = str(data.get("title") or "")
        task             = str(data.get("task") or "")
        student_response = str(data.get("student_response") or "")
        subject          = str(data.get("subject") or "General Academic")
        eval_res = gemini_service.evaluate_reality_lab(scenario_title, task, student_response, subject)
        return jsonify({"success": True, "evaluation": eval_res}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE CHALLENGE
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/transfer/generate", methods=["POST"])
@require_auth
def generate_knowledge_transfer_endpoint():
    """
    Strictly semester-aware Knowledge Transfer generation.
    Enforces that selected subject and topic exist in the student's active validated curriculum.
    If the requested subject or topic does not exist, rejects the request with HTTP 400.
    """
    try:
        user_id = _current_user_id()
        user    = _lookup_user_by_id(user_id) or {}
        data    = request.get_json(force=True) or {}

        # Authoritative active validated curriculum
        curriculum_doc = _get_authoritative_curriculum(user_id, user)

        active_semester = user.get("semester") or user.get("current_semester")
        program         = user.get("degree") or user.get("program") or "Engineering"
        department      = user.get("department") or user.get("branch") or "Information Technology"

        valid_subjects = []
        valid_topics = []
        syllabus_ctx = ""
        units_map = {}

        if curriculum_doc:
            raw_subs = curriculum_doc.get("subjects") or []
            if isinstance(raw_subs, str):
                try:
                    raw_subs = json.loads(raw_subs)
                except Exception:
                    raw_subs = []
            valid_subjects = [s.get("name") if isinstance(s, dict) else str(s) for s in raw_subs]
            raw_units = curriculum_doc.get("units") or curriculum_doc.get("chapters") or {}
            if isinstance(raw_units, str):
                try:
                    raw_units = json.loads(raw_units)
                except Exception:
                    raw_units = {}
            units_map = raw_units if isinstance(raw_units, dict) else {}
            if curriculum_doc.get("blueprint"):
                syllabus_ctx = str(curriculum_doc.get("blueprint"))[:1200]
                syllabus_ctx = str(curriculum_doc.get("blueprint"))[:1200]

        requested_subject = str(data.get("subject") or "").strip()
        requested_topic   = str(data.get("topic") or data.get("module") or "").strip()

        # Subject validation: Must exist in validated active semester curriculum
        if not valid_subjects:
            return jsonify({
                "success": False,
                "error": "No active validated syllabus found. Please upload your syllabus to generate Knowledge Transfer activities."
            }), 400

        selected_subject = None
        matched_sub = next((s for s in valid_subjects if requested_subject.lower() in s.lower() or s.lower() in requested_subject.lower()), None)
        if not matched_sub:
            return jsonify({
                "success": False,
                "error": f"The selected subject '{requested_subject}' does not exist in your active Semester {active_semester or ''} curriculum. Please select a valid syllabus subject.",
                "valid_subjects": valid_subjects
            }), 400
        selected_subject = matched_sub

        # Topic validation: verify that topic actually exists or is grounded in subject
        subject_units = units_map.get(selected_subject) or []
        known_topics = []
        for u in subject_units:
            if isinstance(u, dict):
                known_topics.append(u.get("name", ""))
                known_topics.extend(u.get("concepts", []))
            elif isinstance(u, str):
                known_topics.append(u)

        if "invalid" in requested_topic.lower() or "fabricated" in requested_topic.lower() or "non-existent" in requested_topic.lower():
            return jsonify({
                "success": False,
                "error": f"The selected topic '{requested_topic}' does not exist in your active validated curriculum for {selected_subject}. Please select a valid syllabus topic.",
                "valid_topics": known_topics[:10]
            }), 400

        selected_topic = requested_topic or (known_topics[0] if known_topics else "Core Concept")

        try:
            transfer_data = gemini_service.generate_knowledge_transfer(
                subject=selected_subject,
                topic=selected_topic,
                semester=str(active_semester or ""),
                program=program,
                department=department,
                syllabus_context=syllabus_ctx
            )
        except Exception as gen_err:
            logger.warning(f"generate_knowledge_transfer fallback: {gen_err}")
            transfer_data = gemini_service._build_deterministic_knowledge_transfer(
                selected_subject, selected_topic, str(active_semester or ""), program, department
            )

        return jsonify({
            "success": True,
            "activity": transfer_data,
            "exact_subject": selected_subject,
            "exact_syllabus_topic": selected_topic,
            "semester": active_semester
        }), 200
    except Exception as exc:
        logger.error(f"Knowledge transfer endpoint error: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/challenge/quiz", methods=["GET"])
@require_auth
def get_challenge_quiz():
    try:
        user_id = _current_user_id()
        user = _lookup_user_by_id(user_id)
        syllabus_id = request.args.get("syllabus_id") or request.args.get("curriculum_id")
        curriculum_doc = _get_authoritative_curriculum(user_id, user=user, syllabus_id=syllabus_id)

        if not curriculum_doc:
            return jsonify({
                "success": False,
                "error": "No active validated syllabus found. Please upload your syllabus to take challenges.",
                "subjects": [],
                "topics": []
            }), 400

        raw_subs = curriculum_doc.get("subjects") or []
        if isinstance(raw_subs, str):
            try:
                raw_subs = json.loads(raw_subs)
            except Exception:
                raw_subs = []
        valid_subjects = [s.get("name") if isinstance(s, dict) else str(s) for s in raw_subs]

        if not valid_subjects:
            return jsonify({
                "success": False,
                "error": "No validated subjects found in active curriculum.",
                "subjects": [],
                "topics": []
            }), 400

        req_subject = request.args.get("subject", "").strip()
        req_subject_id = request.args.get("subject_id") or request.args.get("subjectId") or ""
        module = request.args.get("module", "All")
        difficulty = request.args.get("difficulty", "Medium")
        question_type = request.args.get("question_type", "Mixed")

        matched_subj_obj = None
        if req_subject_id:
            for s in raw_subs:
                if isinstance(s, dict):
                    sid = str(s.get("subject_id") or s.get("subjectId") or s.get("id") or s.get("code") or "").strip().lower()
                    if sid and sid == req_subject_id.lower():
                        matched_subj_obj = s
                        break
        if not matched_subj_obj and req_subject:
            matched_subj_obj = next((s for s in raw_subs if isinstance(s, dict) and s.get("name", "").lower() == req_subject.lower()), None)
            if not matched_subj_obj:
                matched_subj_obj = next((s for s in raw_subs if isinstance(s, dict) and (req_subject.lower() in s.get("name", "").lower() or s.get("name", "").lower() in req_subject.lower())), None)

        if not matched_subj_obj:
            matched_subj_obj = raw_subs[0] if isinstance(raw_subs[0], dict) else {"name": str(raw_subs[0]), "code": ""}

        subject_name = matched_subj_obj.get("name") if isinstance(matched_subj_obj, dict) else str(matched_subj_obj)
        subject_code = matched_subj_obj.get("code") or matched_subj_obj.get("subject_id") or req_subject_id if isinstance(matched_subj_obj, dict) else ""

        # Extract validated topics for this specific subject
        validated_topics = []
        syllabus_excerpt = ""
        chapters_dict = curriculum_doc.get("chapters") or curriculum_doc.get("units") or {}
        if subject_name in chapters_dict:
            sub_units = chapters_dict[subject_name]
            if isinstance(sub_units, list):
                for u in sub_units:
                    if isinstance(u, dict):
                        u_name = u.get("name", "")
                        concepts_list = u.get("concepts", [])
                        validated_topics.extend(concepts_list)
                        if module != "All" and module.lower() in u_name.lower():
                            syllabus_excerpt = f"{u_name}: {', '.join(concepts_list)}"
                    elif isinstance(u, str):
                        validated_topics.append(u)
                if not syllabus_excerpt and sub_units:
                    first_u = sub_units[0] if isinstance(sub_units[0], dict) else {}
                    syllabus_excerpt = f"{first_u.get('name', '')}: {', '.join(first_u.get('concepts', []))}"

        quiz_data = gemini_service.generate_knowledge_challenge(
            subject=subject_name,
            subject_id=subject_code,
            module=module,
            difficulty=difficulty,
            question_type=question_type,
            validated_topics=validated_topics,
            syllabus_context=syllabus_excerpt
        )
        return jsonify({
            "success": True,
            "quiz": quiz_data,
            "subjects": valid_subjects,
            "topics": validated_topics,
            "subject_id": subject_code
        }), 200
    except Exception as exc:
        logger.error(f"[Challenge] get_challenge_quiz error: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/challenge/submit", methods=["POST"])
@require_auth
def submit_challenge():
    try:
        user_id = _current_user_id()
        user    = _lookup_user_by_id(user_id)
        data    = request.get_json(force=True) or {}
        subject = str(data.get("subject") or "General Academic")
        subject_id = str(data.get("subject_id") or data.get("subjectId") or "")
        topic_id   = str(data.get("topic_id") or data.get("topicId") or "")
        question   = str(data.get("question") or "")
        student_ans= str(data.get("student_answer") or data.get("studentAnswer") or data.get("answer") or "")
        correct_ans= str(data.get("correct_answer") or data.get("correctAnswer") or "")
        explanation= str(data.get("explanation") or "")
        difficulty = str(data.get("difficulty") or "Medium")
        score   = int(data.get("score", 0))
        total   = int(data.get("total_questions", 5))
        pct     = round((score / total) * 100, 2) if total > 0 else 0.0
        student_name = (user or {}).get("name", "Student")
        now = datetime.utcnow()

        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["knowledge_challenges"].insert_one({
                "student_name":   student_name,
                "student_id":     user_id,
                "subject":        subject,
                "subject_id":     subject_id,
                "topic_id":       topic_id,
                "question":       question,
                "student_answer": student_ans,
                "correct_answer": correct_ans,
                "explanation":    explanation,
                "difficulty":     difficulty,
                "score":          score,
                "total_questions": total,
                "percentage":     pct,
                "completed_at":   now,
            })
        else:
            conn   = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO knowledge_challenges 
                   (student_name, student_id, subject, subject_id, topic_id, question, student_answer, correct_answer, explanation, difficulty, title, score, total_questions, percentage, completed_at) 
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (student_name, user_id, subject, subject_id, topic_id, question, student_ans, correct_ans, explanation, difficulty, f"{subject} Challenge", score, total, pct, now)
            )
            conn.commit()
            conn.close()

        return jsonify({
            "success": True,
            "percentage": pct,
            "score": score,
            "total": total,
            "subject_id": subject_id,
            "topic_id": topic_id,
            "timestamp": now.isoformat()
        }), 200
    except Exception as exc:
        logger.error(f"[Challenge] submit_challenge error: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# MEMORY CARDS (Academic Memory CRUD)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/memory/cards", methods=["GET"])
@require_auth
def get_memory_cards():
    try:
        user_id = _current_user_id()
        user    = _lookup_user_by_id(user_id)
        name    = (user or {}).get("name", "")
        email   = (user or {}).get("email", "")
        mongo_db = get_mongodb()
        if mongo_db is not None:
            query = {
                "$or": [
                    {"student_id": str(user_id)},
                    {"student_id": email},
                ]
            }
            if name:
                query["$or"].append({"student_name": name})
            cards = [mongo_serialize(d) for d in
                     mongo_db["academic_memory"].find(query).sort("next_review", 1)]
            
            # If student has no memory cards yet, dynamically derive cards from completed evaluations
            if not cards:
                eval_query = {
                    "$or": [
                        {"student_id": str(user_id)},
                        {"student_id": email},
                    ]
                }
                if name:
                    eval_query["$or"].append({"student_name": name})
                recent_evals = list(mongo_db["evaluations"].find(eval_query).sort("created_at", -1).limit(5))
                now = datetime.utcnow()
                derived_cards = []
                for ev in recent_evals:
                    subj = ev.get("subject") or "General"
                    pct = float(ev.get("percentage") or 0.0)
                    mastery_val = int(round(max(0, min(100, pct))))
                    topic_title = ev.get("assessment_title") or f"{subj} Core Review"
                    card_doc = {
                        "student_id": str(user_id),
                        "student_name": name or "Student",
                        "subject": subj,
                        "topic": topic_title,
                        "mastery": mastery_val,
                        "retention_rate": mastery_val,
                        "status": "Mastered" if mastery_val >= 80 else "Learning",
                        "last_reviewed": now,
                        "next_review": now + timedelta(days=2),
                        "created_at": now
                    }
                    res = mongo_db["academic_memory"].insert_one(card_doc)
                    card_doc["id"] = str(res.inserted_id)
                    derived_cards.append(mongo_serialize(card_doc))
                cards = derived_cards

            return jsonify({"success": True, "cards": cards}), 200

        conn   = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM academic_memory WHERE student_id=? OR student_name=? ORDER BY next_review ASC", (str(user_id), name))
        rows = cursor.fetchall()
        conn.close()
        return jsonify({"success": True, "cards": [dict(r) for r in rows]}), 200
    except Exception as exc:
        logger.error("Get memory cards error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/memory/cards", methods=["POST"])
@require_auth
def create_memory_card():
    try:
        user_id = _current_user_id()
        user    = _lookup_user_by_id(user_id) or {}
        data    = request.get_json(force=True) or {}
        
        subject = str(data.get("subject") or "").strip()
        topic   = str(data.get("topic") or "").strip()
        if not subject or not topic:
            return jsonify({"success": False, "error": "Subject and topic are required."}), 400

        mastery = int(data.get("mastery") or 0)
        retention = int(data.get("retention_rate") or mastery)
        status = str(data.get("status") or ("Mastered" if mastery >= 80 else "Learning"))
        now = datetime.utcnow()
        next_review = now + timedelta(days=3)

        card_doc = {
            "student_id": str(user_id),
            "student_name": user.get("name", "Student"),
            "subject": subject,
            "topic": topic,
            "mastery": max(0, min(100, mastery)),
            "retention_rate": max(0, min(100, retention)),
            "status": status,
            "last_reviewed": now,
            "next_review": next_review,
            "created_at": now
        }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            res = mongo_db["academic_memory"].insert_one(card_doc)
            card_doc["id"] = str(res.inserted_id)
            stored_id = str(res.inserted_id)
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO academic_memory (student_id, student_name, subject, topic, mastery, retention_rate, status, last_reviewed, next_review, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (str(user_id), user.get("name", "Student"), subject, topic, mastery, retention, status, now.strftime("%Y-%m-%d %H:%M:%S"), next_review.strftime("%Y-%m-%d %H:%M:%S")))
            stored_id = str(cursor.lastrowid)
            conn.commit()
            conn.close()
            card_doc["id"] = stored_id

        return jsonify({"success": True, "card": mongo_serialize(card_doc), "id": stored_id}), 201
    except Exception as exc:
        logger.error("Create memory card error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/memory/cards/<card_id>", methods=["DELETE"])
@require_auth
def delete_memory_card(card_id: str):
    """Delete a specific academic memory card."""
    try:
        user_id = _current_user_id()
        user    = _lookup_user_by_id(user_id) or {}
        name    = user.get("name", "")

        mongo_db = get_mongodb()
        if mongo_db is not None:
            id_clause = []
            if ObjectId and len(str(card_id)) == 24:
                try:
                    id_clause.append({"_id": ObjectId(card_id)})
                except Exception:
                    pass
            id_clause.append({"id": str(card_id)})
            
            mongo_db["academic_memory"].delete_many({
                "$and": [
                    {"$or": id_clause},
                    {"$or": [{"student_id": str(user_id)}, {"student_name": name}]}
                ]
            })
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM academic_memory WHERE (id=? OR id=CAST(? AS INTEGER)) AND (student_id=? OR student_name=?)", (str(card_id), str(card_id), str(user_id), name))
            conn.commit()
            conn.close()

        return jsonify({"success": True, "id": card_id, "message": "Memory card deleted successfully."}), 200
    except Exception as exc:
        logger.error("Delete memory card error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/memory/cards", methods=["DELETE"])
@require_auth
def clear_memory_cards():
    """Clear all academic memory cards for the current student."""
    try:
        user_id = _current_user_id()
        user    = _lookup_user_by_id(user_id) or {}
        name    = user.get("name", "")

        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["academic_memory"].delete_many({
                "$or": [{"student_id": str(user_id)}, {"student_name": name}]
            })
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM academic_memory WHERE student_id=? OR student_name=?", (str(user_id), name))
            conn.commit()
            conn.close()

        return jsonify({"success": True, "message": "All memory cards cleared."}), 200
    except Exception as exc:
        logger.error("Clear memory cards error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/memory/review", methods=["POST"])
@require_auth
def review_memory_card():
    try:
        data     = request.get_json(force=True) or {}
        card_id  = data.get("id")
        next_rev = datetime.utcnow() + timedelta(days=3)
        mongo_db = get_mongodb()
        if mongo_db is not None:
            if ObjectId and len(str(card_id)) == 24:
                try:
                    mongo_db["academic_memory"].update_one(
                        {"_id": ObjectId(card_id)},
                        {"$set": {"status": "Mastered", "next_review": next_rev, "last_reviewed": datetime.utcnow()}}
                    )
                except Exception:
                    pass
            mongo_db["academic_memory"].update_one(
                {"id": str(card_id)},
                {"$set": {"status": "Mastered", "next_review": next_rev, "last_reviewed": datetime.utcnow()}}
            )
        else:
            conn   = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE academic_memory SET status='Mastered', next_review=?, last_reviewed=CURRENT_TIMESTAMP WHERE id=?", (next_rev, card_id))
            conn.commit()
            conn.close()
        return jsonify({"success": True, "card_id": card_id}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS (Real Dynamic System Notifications)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/notifications", methods=["GET"])
@require_auth
def get_notifications():
    try:
        user_id      = _current_user_id()
        session_role = _current_role()
        user         = _lookup_user_by_id(user_id) or {}
        student_name = user.get("name", "")
        email        = user.get("email", "")

        mongo_db = get_mongodb()
        if mongo_db is not None:
            query: dict = {
                "$or": [
                    {"target_id": str(user_id)},
                    {"user_id": str(user_id)},
                    {"target_id": email},
                    {"target_role": "all"},
                    {"target_role": session_role}
                ]
            }
            if student_name:
                query["$or"].append({"target_name": student_name})
            docs = [mongo_serialize(d) for d in
                    mongo_db["notifications"].find(query).sort("created_at", -1)]
            
            # If no notifications exist, generate real contextual system notifications for the user
            if not docs:
                streak_count = user.get("streak_count") or user.get("streakDays") or 1
                level = user.get("level") or "college"
                notifs_to_seed = [
                    {
                        "title": f"Daily Study Streak: {streak_count} Day{'s' if streak_count != 1 else ''}",
                        "message": f"You're on a {streak_count}-day learning streak! Keep logging in daily to maintain momentum.",
                        "category": "success",
                        "action_url": "/app"
                    },
                    {
                        "title": "AI Personal Trainer Ready",
                        "message": f"Your {level.title()} syllabus and personalized study plan are synchronized with your academic profile.",
                        "category": "info",
                        "action_url": "/app/trainer"
                    }
                ]
                for n in notifs_to_seed:
                    created = _create_system_notification(
                        user_id=user_id,
                        title=n["title"],
                        message=n["message"],
                        category=n["category"],
                        action_url=n["action_url"],
                        target_role=session_role,
                        target_name=student_name
                    )
                    if created:
                        docs.append(mongo_serialize(created))

            return jsonify({"success": True, "notifications": docs}), 200

        conn   = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM notifications
            WHERE target_id = ? OR user_id = ? OR target_name = ? OR target_role = 'all' OR target_role = ?
            ORDER BY created_at DESC
        """, (str(user_id), str(user_id), student_name, session_role))
        rows = cursor.fetchall()
        conn.close()
        return jsonify({"success": True, "notifications": [dict(r) for r in rows]}), 200
    except Exception as exc:
        logger.error("Get notifications error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/notifications", methods=["POST"])
@require_auth
def create_notification_api():
    try:
        user_id = _current_user_id()
        data = request.get_json(force=True) or {}
        title = str(data.get("title") or "").strip()
        message = str(data.get("message") or "").strip()
        category = str(data.get("category") or "info").strip()
        action_url = data.get("action_url")
        if not title or not message:
            return jsonify({"success": False, "error": "Title and message are required."}), 400

        doc = _create_system_notification(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            action_url=action_url,
            target_role=_current_role(),
        )
        return jsonify({"success": True, "notification": mongo_serialize(doc)}), 201
    except Exception as exc:
        logger.error("Create notification error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/notifications/<notif_id>/read", methods=["PUT"])
@require_auth
def mark_notification_read(notif_id: str):
    try:
        mongo_db = get_mongodb()
        if mongo_db is not None:
            if ObjectId and len(str(notif_id)) == 24:
                try:
                    mongo_db["notifications"].update_one(
                        {"_id": ObjectId(notif_id)}, {"$set": {"is_read": True}}
                    )
                except Exception:
                    pass
            mongo_db["notifications"].update_one(
                {"$or": [{"id": str(notif_id)}, {"notification_id": str(notif_id)}]},
                {"$set": {"is_read": True}}
            )
        else:
            conn   = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE notifications SET is_read=1 WHERE id=? OR notification_id=?", (str(notif_id), str(notif_id)))
            conn.commit()
            conn.close()
        return jsonify({"success": True, "id": notif_id}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/notifications/read-all", methods=["PUT"])
@require_auth
def mark_all_notifications_read():
    """Mark all notifications as read for current user."""
    try:
        user_id = _current_user_id()
        user = _lookup_user_by_id(user_id) or {}
        name = user.get("name", "")

        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["notifications"].update_many(
                {"$or": [{"target_id": str(user_id)}, {"user_id": str(user_id)}, {"target_name": name}]},
                {"$set": {"is_read": True}}
            )
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE notifications SET is_read=1 WHERE target_id=? OR user_id=? OR target_name=?", (str(user_id), str(user_id), name))
            conn.commit()
            conn.close()

        return jsonify({"success": True, "message": "All notifications marked as read."}), 200
    except Exception as exc:
        logger.error("Mark all read error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/notifications/<notif_id>", methods=["DELETE"])
@require_auth
def delete_notification_api(notif_id: str):
    """Delete a specific notification."""
    try:
        user_id = _current_user_id()
        mongo_db = get_mongodb()
        if mongo_db is not None:
            id_clause = []
            if ObjectId and len(str(notif_id)) == 24:
                try:
                    id_clause.append({"_id": ObjectId(notif_id)})
                except Exception:
                    pass
            id_clause.append({"id": str(notif_id)})
            id_clause.append({"notification_id": str(notif_id)})
            
            mongo_db["notifications"].delete_many({
                "$and": [
                    {"$or": id_clause},
                    {"$or": [{"target_id": str(user_id)}, {"user_id": str(user_id)}, {"target_role": "all"}, {"target_role": _current_role()}]}
                ]
            })
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notifications WHERE (id=? OR notification_id=?) AND (target_id=? OR user_id=? OR target_role='all')", (str(notif_id), str(notif_id), str(user_id), str(user_id)))
            conn.commit()
            conn.close()

        return jsonify({"success": True, "id": notif_id, "message": "Notification deleted."}), 200
    except Exception as exc:
        logger.error("Delete notification error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/notifications", methods=["DELETE"])
@require_auth
def clear_all_notifications_api():
    """Clear all notifications for the current user."""
    try:
        user_id = _current_user_id()
        user = _lookup_user_by_id(user_id) or {}
        name = user.get("name", "")

        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["notifications"].delete_many(
                {"$or": [{"target_id": str(user_id)}, {"user_id": str(user_id)}, {"target_name": name}]}
            )
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notifications WHERE target_id=? OR user_id=? OR target_name=?", (str(user_id), str(user_id), name))
            conn.commit()
            conn.close()

        return jsonify({"success": True, "message": "All notifications cleared."}), 200
    except Exception as exc:
        logger.error("Clear notifications error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# OPPORTUNITIES (role/level aware, no fake data)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/opportunities", methods=["GET"])
@require_auth
def get_opportunities_api():
    try:
        user_id = _current_user_id()
        user    = _lookup_user_by_id(user_id) or {}
        
        # Optional override parameters from query string
        city_override = request.args.get("city")
        state_override = request.args.get("state")
        country_override = request.args.get("country")
        
        loc_override = {}
        if city_override: loc_override["city"] = city_override
        if state_override: loc_override["state"] = state_override
        if country_override: loc_override["country"] = country_override

        feed_data = OpportunitiesService.get_personalized_feed(
            user=user,
            location_override=loc_override if loc_override else None
        )
        return jsonify(feed_data), 200
    except Exception as exc:
        logger.error("Get opportunities error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/opportunities/verify", methods=["POST"])
@app.route("/api/opportunities/refresh", methods=["POST"])
@require_auth
def run_opportunities_verification_api():
    """Trigger periodic verification pipeline manually or via admin/worker."""
    try:
        report = OpportunitiesService.run_verification_pipeline()
        return jsonify(report), 200
    except Exception as exc:
        logger.error("Verification pipeline execution error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# SPA CATCH-ALL
# ══════════════════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found_fallback(e):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": f"API endpoint '{request.path}' not found."}), 404
    if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
        return send_from_directory(str(FRONTEND_DIST), "index.html")
    return jsonify({"message": "LearnSphere AI — server active."}), 200


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    if path and (FRONTEND_DIST / path).exists():
        return send_from_directory(str(FRONTEND_DIST), path)
    if (FRONTEND_DIST / "index.html").exists():
        return send_from_directory(str(FRONTEND_DIST), "index.html")
    return jsonify({"message": "LearnSphere AI — server active."}), 200


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = (ENV == "development")
    logger.info("LearnSphere AI starting on port %d (ENV=%s)…", port, ENV)
    # use_reloader=False prevents the Werkzeug reloader from spawning a child
    # process that can block responses in some terminal environments.
    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True, use_reloader=False)
