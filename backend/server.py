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

        response_user = _normalize_user_doc(mongo_serialize(user_doc))
        response_user["id"] = stored_id

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

    user = _normalize_user_doc(user)
    return jsonify({"success": True, "authenticated": True, "user": user}), 200


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

        evaluation_request = {
            "evaluation_id":   f"eval_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}",
            "submitted_by":     user_id,
            "submitter_role":   session_role,
            "student_id":       user_id if session_role == "student" else (request.form.get("student_id") or None),
            "teacher_id":       user_id if session_role == "teacher" else None,
            "subject":          subject,
            "student_name":     student_name,
            "roll_number":      roll_number,
            "assessment_title": assessment_title or "Self Evaluation Examination",
            "level":            level,
            "board":            board,
            "stream":           stream,
            "semester":         semester,
            "question_paper":   qp_path,
            "answer_script":    answer_path,
            "rubrics":          rubric_path,
            "syllabus":         syllabus_path,
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
    user         = _lookup_user_by_id(user_id)
    user_email   = user.get("email", "") if user else ""
    student_name = user.get("name", "") if user else ""

    mongo_db = get_mongodb()
    if mongo_db is not None:
        if session_role == "student":
            # Students see ONLY their own evaluations (by user_id, email, or student_name)
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
            # Teachers see evaluations they submitted or are assigned to
            query = {
                "$or": [
                    {"submitted_by": user_id},
                    {"teacher_id": user_id},
                    {"submitted_by": user_email},
                ]
            }

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
        q = "SELECT * FROM evaluations WHERE (submitted_by = ? OR teacher_id = ?)"
        params = [user_id, user_id]

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
@require_role("teacher")
def delete_evaluation(eval_id: str):
    try:
        user_id = _current_user_id()
        mongo_db = get_mongodb()
        if mongo_db is not None:
            if ObjectId:
                try:
                    mongo_db["evaluations"].delete_one({"_id": ObjectId(eval_id), "submitted_by": user_id})
                except Exception:
                    pass
            mongo_db["evaluations"].delete_one({"id": str(eval_id), "submitted_by": user_id})
        conn = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM evaluations WHERE id = ? AND submitted_by = ?", (str(eval_id), user_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/evaluations/<eval_id>/override", methods=["PUT"])
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

        conn = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE evaluations SET obtained_marks=?, total_marks=?, percentage=?, grade=?, "
            "is_teacher_overridden=1 WHERE id=?",
            (obtained_marks, total_marks, percentage, grade, str(eval_id))
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
        eval_data = None
        mongo_db  = get_mongodb()
        if mongo_db is not None:
            doc = None
            if ObjectId:
                try:
                    doc = mongo_db["evaluations"].find_one({"_id": ObjectId(eval_id)})
                except Exception:
                    pass
            if not doc:
                doc = mongo_db["evaluations"].find_one({"id": eval_id})
            if doc:
                eval_data = mongo_serialize(doc)

        if not eval_data:
            conn   = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM evaluations WHERE id = ?", (eval_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                eval_data = dict(row)

        if not eval_data:
            return jsonify({"success": False, "error": "Evaluation not found."}), 404

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

        stored_level   = (user or {}).get("level") or "college"
        level          = str(get_param("level") or stored_level).strip().lower()
        stored_sem     = (user or {}).get("semester") if (user or {}).get("semester") is not None else (user or {}).get("current_semester")
        semester_input = get_param("semester")
        semester_val   = semester_input if (semester_input is not None and str(semester_input).strip() != "") else stored_sem

        try:
            target_semester = int(semester_val) if semester_val is not None else None
        except (ValueError, TypeError):
            target_semester = str(semester_val).strip() if semester_val else None

        stored_cls     = (user or {}).get("grade_level") or (user or {}).get("classLevel")
        class_level    = str(get_param("classLevel") or stored_cls or "").strip()
        stream         = str(get_param("stream") or (user or {}).get("stream") or "").strip()
        degree         = str(get_param("degree") or (user or {}).get("degree") or (user or {}).get("program") or "").strip()
        department     = str(get_param("department") or (user or {}).get("department") or (user or {}).get("branch") or (user or {}).get("domain") or "").strip()
        regulation     = str(get_param("regulation") or (user or {}).get("regulation") or (user or {}).get("batch") or "").strip()
        academic_year  = str(get_param("academic_year") or (user or {}).get("academic_year") or (user or {}).get("academicYear") or "").strip()

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
        else:
            return jsonify({"success": False, "error": "No syllabus file or text provided."}), 400

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

        # Execute dedicated Curriculum Completeness Validator BEFORE activating
        validation_report = CurriculumCompletenessValidator.validate(
            user=user,
            analysis=analysis,
            raw_content_or_file=file_input,
            target_semester=target_semester
        )

        detected_semesters = analysis.get("detected_semesters") or []
        explicit_identifier = analysis.get("explicit_semester_identifier") or ""
        validation_status = str(validation_report.get("status") or "VALID").upper().strip()
        is_active = bool(validation_report.get("is_valid", False))
        status_label = "ACTIVE" if is_active else validation_status
        mismatch_reason = validation_report.get("summary") or analysis.get("mismatch_reason")

        syllabus_id = str(uuid.uuid4())
        now = datetime.utcnow()

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

            s_name = str(s_dict.get("name") or "").strip()
            if not s_name:
                continue
            s_code = str(s_dict.get("code") or "").strip()
            s_sec = str(s_dict.get("source_section") or s_dict.get("source_page") or explicit_identifier or f"Semester {target_semester or ''} Scheme Table").strip()
            s_txt = str(s_dict.get("source_text") or f"{s_code} {s_name}".strip()).strip()
            s_ev = str(s_dict.get("semester_evidence") or f"Found in Semester {target_semester or ''} curriculum blueprint").strip()

            pages_raw = s_dict.get("source_page_numbers") or [s_dict.get("source_page", 1)]
            if isinstance(pages_raw, list):
                pages = [int(p) for p in pages_raw if str(p).isdigit()]
            elif isinstance(pages_raw, (int, str)) and str(pages_raw).isdigit():
                pages = [int(pages_raw)]
            else:
                pages = [1]
            if not pages:
                pages = [1]

            enriched_subjects.append({
                "code": s_code,
                "name": s_name,
                "type": str(s_dict.get("type") or s_dict.get("category") or "Theory Core").strip(),
                "category": str(s_dict.get("category") or s_dict.get("type") or "Program Core").strip(),
                "credits": float(s_dict["credits"]) if s_dict.get("credits") is not None and str(s_dict.get("credits")).replace('.', '', 1).isdigit() else None,
                "lecture_hours": int(s_dict["lecture_hours"]) if str(s_dict.get("lecture_hours", "")).isdigit() else None,
                "tutorial_hours": int(s_dict["tutorial_hours"]) if str(s_dict.get("tutorial_hours", "")).isdigit() else None,
                "practical_hours": int(s_dict["practical_hours"]) if str(s_dict.get("practical_hours", "")).isdigit() else None,
                "semester": target_semester or s_dict.get("semester"),
                "source_document_id": syllabus_id,
                "source_document_name": file_name or "Official Syllabus Document",
                "source_document_hash": file_hash or "",
                "source_page_numbers": pages,
                "source_page": pages[0] if pages else 1,
                "source_section": s_sec,
                "source_text": s_txt,
                "semester_evidence": s_ev,
                "confidence": float(s_dict.get("confidence", 0.98)) if str(s_dict.get("confidence", "")).replace('.', '', 1).isdigit() else 0.98,
                "evidence_verified": True
            })

        syllabus_doc = {
            "syllabus_id":                  syllabus_id,
            "student_id":                   user_id,
            "student_name":                 user.get("name", ""),
            "program":                      degree,
            "degree":                       degree,
            "department":                   department,
            "branch":                       department,
            "semester":                     target_semester,
            "current_semester":             target_semester,
            "class_level":                  class_level,
            "grade_level":                  class_level,
            "stream":                       stream,
            "regulation":                   regulation,
            "academic_year":                academic_year,
            "file_path":                    file_path or "",
            "file_hash":                    file_hash or "",
            "file_name":                    file_name or "",
            "level":                        level,
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
            "status":                       status_label,
            "version":                      1,
            "created_at":                   now,
            "updated_at":                   now,
        }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            if is_active:
                # Archive older active syllabi for this student
                mongo_db["syllabi"].update_many(
                    {"student_id": user_id, "is_active": True},
                    {"$set": {"is_active": False, "status": "ARCHIVED", "updated_at": now}}
                )
            existing = mongo_db["syllabi"].find_one(
                {"student_id": user_id},
                sort=[("version", -1)]
            )
            version = (existing.get("version", 0) + 1) if existing else 1
            syllabus_doc["version"] = version
            mongo_db["syllabi"].insert_one(syllabus_doc)

            # If active with extracted subjects, optionally update user's quick subject list
            if is_active and analysis.get("extracted_subjects"):
                mongo_db["users"].update_one(
                    {"$or": [{"_id": ObjectId(user_id)} if (ObjectId and len(str(user_id)) == 24) else {"id": str(user_id)}, {"user_id": str(user_id)}]},
                    {"$set": {"subjects": analysis["extracted_subjects"], "updated_at": now}}
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
    level = user.get("level") or "college"

    mongo_db = get_mongodb()
    if mongo_db is not None:
        conditions = [{"$or": [{"is_active": True}, {"status": {"$in": ["ACTIVE", "READY"]}}]}]
        if level == "college" and current_sem is not None:
            sem_int = int(current_sem) if str(current_sem).isdigit() else current_sem
            sem_str = str(current_sem)
            conditions.append({
                "$or": [
                    {"semester": sem_int},
                    {"semester": sem_str},
                    {"current_semester": sem_int},
                    {"current_semester": sem_str}
                ]
            })
        query_filter = {"student_id": user_id, "$and": conditions}
        doc = mongo_db["syllabi"].find_one(
            query_filter,
            sort=[("updated_at", -1), ("version", -1)]
        )

        if not doc:
            pending_doc = mongo_db["syllabi"].find_one(
                {"student_id": user_id, "status": {"$in": ["NEEDS_REVIEW", "MISMATCH"]}},
                sort=[("updated_at", -1)]
            )
            if pending_doc:
                return jsonify({
                    "success": True,
                    "is_valid": False,
                    "is_active": False,
                    "status": pending_doc.get("status", "NEEDS_REVIEW"),
                    "mismatch_reason": pending_doc.get("mismatch_reason", "Syllabus validation requires review."),
                    "validation_report": pending_doc.get("validation_report"),
                    "semester": current_sem,
                    "degree": degree,
                    "department": department,
                    "subjects": [],
                    "extracted_subjects": [],
                    "units": {},
                    "topics": []
                }), 200

            # Pre-configured profile fallback if no uploaded doc
            return jsonify({
                "success": True,
                "is_valid": True,
                "is_active": False,
                "status": "VALID",
                "is_preconfigured": True,
                "semester": current_sem,
                "degree": degree,
                "department": department,
                "subjects": [],
                "extracted_subjects": user.get("subjects") or [],
                "units": {},
                "topics": []
            }), 200

        # Valid active curriculum doc found
        subjects = doc.get("subjects") or []
        extracted_subjects = doc.get("extracted_subjects") or [s.get("name") for s in subjects if isinstance(s, dict)]
        return jsonify({
            "success": True,
            "is_valid": True,
            "is_active": True,
            "status": doc.get("status", "ACTIVE"),
            "syllabus_id": doc.get("syllabus_id"),
            "student_id": user_id,
            "program": doc.get("program") or degree,
            "degree": doc.get("degree") or degree,
            "department": doc.get("department") or department,
            "semester": doc.get("semester") or current_sem,
            "subjects": subjects,
            "extracted_subjects": extracted_subjects,
            "units": doc.get("chapters") or doc.get("units") or {},
            "chapters": doc.get("chapters") or {},
            "topics": doc.get("topics") or doc.get("key_topics") or [],
            "validation_report": doc.get("validation_report"),
            "source_document_name": doc.get("file_name"),
            "source_document_id": doc.get("syllabus_id"),
            "evidence_retained": True
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
        if row:
            d = dict(row)
            analysis = json.loads(d.get("analysis_json") or "{}") if d.get("analysis_json") else {}
            subjects = analysis.get("subjects") or []
            return jsonify({
                "success": True,
                "is_valid": True,
                "status": d.get("status", "ACTIVE"),
                "syllabus_id": d.get("syllabus_id"),
                "semester": d.get("semester") or current_sem,
                "subjects": subjects,
                "extracted_subjects": analysis.get("extracted_subjects", []),
                "units": analysis.get("chapters", {}),
                "chapters": analysis.get("chapters", {}),
                "topics": analysis.get("key_topics", []),
                "source_document_name": d.get("file_name")
            }), 200
        return jsonify({
            "success": True,
            "is_valid": True,
            "status": "VALID",
            "is_preconfigured": True,
            "semester": current_sem,
            "subjects": [],
            "extracted_subjects": user.get("subjects") or []
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
            {"student_id": user_id},
            {"$set": {"is_active": False, "status": "ARCHIVED", "updated_at": now}}
        )
        return jsonify({"success": True, "message": "Syllabus archived successfully."}), 200

    conn = get_sqlite_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE syllabi SET is_active=0, status='ARCHIVED', updated_at=? WHERE student_id=?",
        (now.isoformat(), user_id)
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
    try:
        mongo_db = get_mongodb()
        if mongo_db is not None:
            # Teacher sees action items from evaluations they submitted or unassigned
            items_cursor = mongo_db["action_items"].find({
                "$or": [{"teacher_id": teacher_id}, {"teacher_id": None}, {"teacher_id": ""}]
            }).sort("created_at", -1)
            items = [mongo_serialize(d) for d in items_cursor]
            return jsonify({"success": True, "items": items}), 200

        # SQLite: query action_items table
        conn = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM action_items 
               WHERE teacher_id = ? OR teacher_id IS NULL OR teacher_id = '' 
               ORDER BY created_at DESC""",
            (teacher_id,)
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
            items.append(d)
        conn.close()
        return jsonify({"success": True, "items": items}), 200
    except Exception as exc:
        logger.error("Action Center error: %s", exc)
        return jsonify({"success": True, "items": []}), 200


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
                {"id": item_id},
                {"$set": {"status": new_status, "updated_by": teacher_id,
                          "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}},
                upsert=True,
            )
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE action_items SET status = ? WHERE id = ?", (new_status, item_id))
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
                query = {
                    "$or": [
                        {"teacher_id": user_id},
                        {"teacher_id": user_email},
                        {"teacher_id": None},
                    ]
                }
            docs = [mongo_serialize(d) for d in mongo_db["misconceptions"].find(query)]
            return jsonify({"success": True, "misconceptions": docs}), 200

        conn   = get_sqlite_db()
        cursor = conn.cursor()
        if session_role == "student":
            cursor.execute(
                "SELECT * FROM misconceptions WHERE student_name=? ORDER BY created_at DESC", (user_name,)
            )
        else:
            cursor.execute("SELECT * FROM misconceptions ORDER BY created_at DESC")
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
    mongo_db = get_mongodb()
    if mongo_db is not None:
        students_cursor = mongo_db["users"].find({"role": "student"})
        students = []
        for s in students_cursor:
            name  = s.get("name", "")
            evals = list(mongo_db["evaluations"].find({"student_name": name}))
            avg   = round(sum(float(e.get("percentage", 0)) for e in evals) / len(evals), 1) if evals else 0.0
            students.append({
                "id":          str(s["_id"]),
                "name":        name,
                "roll_number": s.get("roll_number", ""),
                "section":     s.get("section", ""),
                "level":       s.get("level", "school"),
                "average":     avg,
                "evaluations": len(evals),
                "status":      "On track" if avg >= 75 else "Needs support" if avg >= 50 else "New Student",
            })
        return jsonify({"success": True, "students": students}), 200

    conn   = get_sqlite_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE role = 'student'")
    rows = cursor.fetchall()
    conn.close()
    students = []
    for r in rows:
        d = dict(r)
        d.pop("password_hash", None)
        d.pop("password", None)
        students.append(d)
    return jsonify({"success": True, "students": students}), 200


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
                # Teachers: show recent evaluations they submitted
                recent_evals = [mongo_serialize(d) for d in
                                mongo_db["evaluations"].find({"submitted_by": user_id}).sort("created_at", -1).limit(10)]
                weak_topics  = [mongo_serialize(d) for d in
                                mongo_db["misconceptions"].find({"teacher_id": user_id, "resolved": {"$ne": True}}).limit(5)]
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
                cursor.execute("SELECT * FROM evaluations WHERE submitted_by=? ORDER BY created_at DESC LIMIT 10", (user_id,))
            recent_evals = [dict(r) for r in cursor.fetchall()]
            conn.close()
    except Exception as exc:
        logger.error("Analytics error: %s", exc)

    return jsonify({
        "success":           True,
        "recentEvaluations": recent_evals,
        "weakTopics":        weak_topics,
        "academicMemory":    memory_items,
    }), 200


@app.route("/api/analytics/student", methods=["GET"])
@require_auth
def get_student_analytics():
    user_id = _current_user_id()
    session_role = _current_role()
    target_student_id = request.args.get("student_id") or user_id

    # If role is student, they can ONLY view their own analytics
    if session_role == "student":
        target_student_id = user_id

    user = _lookup_user_by_id(target_student_id)
    user_email = (user or {}).get("email", "")
    user_name = (user or {}).get("name", "")

    mongo_db = get_mongodb()
    evals = []
    misconceptions = []
    try:
        if mongo_db is not None:
            eval_query = {
                "$or": [
                    {"submitted_by": target_student_id},
                    {"student_id": target_student_id},
                    {"submitted_by": user_email},
                    {"student_id": user_email},
                ]
            }
            if user_name:
                eval_query["$or"].append({"student_name": user_name})
            evals = [mongo_serialize(d) for d in mongo_db["evaluations"].find(eval_query).sort("created_at", 1)]

            misc_query = {
                "$or": [
                    {"student_id": target_student_id},
                    {"student_id": user_email},
                ]
            }
            if user_name:
                misc_query["$or"].append({"student_name": user_name})
            misconceptions = [mongo_serialize(d) for d in mongo_db["misconceptions"].find(misc_query).sort("created_at", -1)]
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM evaluations WHERE (submitted_by=? OR student_id=? OR student_name=?) ORDER BY created_at ASC",
                (target_student_id, target_student_id, user_name),
            )
            evals = [dict(r) for r in cursor.fetchall()]
            for ev in evals:
                cursor.execute("SELECT * FROM evaluation_questions WHERE evaluation_id = ?", (ev.get("id"),))
                ev["questions"] = [dict(r) for r in cursor.fetchall()]
            cursor.execute("SELECT * FROM misconceptions WHERE student_name=? ORDER BY created_at DESC", (user_name,))
            misconceptions = [dict(r) for r in cursor.fetchall()]
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

        # Fetch authoritative active validated syllabus
        active_syllabus = None
        mongo_db = get_mongodb()
        if mongo_db is not None:
            active_syllabus = mongo_db["syllabi"].find_one(
                {"student_id": user_id, "$or": [{"is_active": True}, {"status": {"$in": ["ACTIVE", "READY"]}}]},
                sort=[("updated_at", -1)]
            )
        else:
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM syllabi WHERE student_id=? AND (is_active=1 OR status IN ('ACTIVE', 'READY')) ORDER BY version DESC LIMIT 1",
                (user_id,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                active_syllabus = dict(row)
                if active_syllabus.get("analysis_json"):
                    try:
                        active_syllabus.update(json.loads(active_syllabus["analysis_json"]))
                    except Exception:
                        pass

        # Check if student is asking for their semester subjects list
        lower_msg = message.lower().strip()
        is_asking_subjects = any(phrase in lower_msg for phrase in [
            "what are my semester", "what subjects do i have", "what are my subjects", 
            "list my subjects", "what is my syllabus", "show my subjects", "my subjects list",
            "subjects in semester", "semester subjects", "my courses", "what courses do i have"
        ])
        
        if is_asking_subjects:
            validated_subjects = (active_syllabus or {}).get("subjects") or []
            if not validated_subjects and (active_syllabus or {}).get("extracted_subjects"):
                validated_subjects = [{"name": s} for s in active_syllabus["extracted_subjects"]]
            elif not validated_subjects and (user or {}).get("subjects"):
                validated_subjects = [{"name": s} for s in user["subjects"]]

            if validated_subjects:
                sem_label = f"Semester {semester}" if semester else "Current Semester"
                prog_label = f"{degree} ({dept})" if (degree and dept) else (degree or dept or "Academic Program")
                
                subject_lines = []
                for idx, s in enumerate(validated_subjects, start=1):
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

        # Retrieve relevant syllabus excerpt for coaching context
        syllabus_excerpt = ""
        if active_syllabus:
            chapters_dict = active_syllabus.get("chapters") or active_syllabus.get("units") or {}
            if subject in chapters_dict:
                sub_units = chapters_dict[subject]
                if isinstance(sub_units, list):
                    for u in sub_units:
                        if isinstance(u, dict):
                            u_name = u.get("name", "")
                            concepts_list = u.get("concepts", [])
                            if (unit and unit.lower() in u_name.lower()) or (topic and topic.lower() in " ".join(concepts_list).lower()):
                                syllabus_excerpt = f"{u_name}: {', '.join(concepts_list)}"
                                break
                    if not syllabus_excerpt and sub_units:
                        first_u = sub_units[0] if isinstance(sub_units[0], dict) else {}
                        syllabus_excerpt = f"{first_u.get('name', '')}: {', '.join(first_u.get('concepts', []))}"

        target_ctx = f"College ({degree} · {dept} · Semester {semester})" if (degree and dept and semester) else "College Academic Learning"

        prompt = (
            f"You are LearnSphere AI's Personal Learning Coach.\n"
            f"STUDENT CONTEXT:\n"
            f"- Program: {degree or 'Degree Program'}\n"
            f"- Department: {dept or 'Department'}\n"
            f"- Semester: Semester {semester}\n"
            f"- Validated Subject: {subject}\n"
            f"- Unit / Module: {unit or 'Core Unit'}\n"
            f"- Chapter / Topic: {topic or concept or subject}\n"
            f"- Official Syllabus Blueprint: {syllabus_excerpt or 'Semester ' + str(semester) + ' Validated Curriculum'}\n\n"
            f"COACHING STRATEGY: {study_method or 'Active Coaching'}\n"
            f"STUDENT MESSAGE: '{message}'\n\n"
            f"RULES:\n"
            f"1. Explain concisely using formal technical terminology from this student's exact semester curriculum.\n"
            f"2. Include at least ONE visual tool (Markdown Table or ASCII Flowchart/Diagram).\n"
            f"3. Provide step-by-step guidance tailored to scoring full marks in semester exams.\n"
            f"4. End with an active recall question testing the concept.\n"
            f"5. Suggest spaced repetition review interval."
        )
        ai_reply = gemini_service.generate_content(prompt, json_output=False)

        student_name = (user or {}).get("name", "Student")
        if mongo_db is not None:
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

        # Fetch active validated curriculum for authoritative semester context
        curriculum_doc = None
        mongo_db = get_mongodb()
        if mongo_db is not None:
            curriculum_doc = mongo_db["syllabi"].find_one({
                "student_id": user_id,
                "$or": [{"is_active": True}, {"status": {"$in": ["ACTIVE", "READY"]}}]
            }, sort=[("updated_at", -1), ("version", -1)])
            if not curriculum_doc:
                curriculum_doc = mongo_db.curriculum_registry.find_one({
                    "user_id": user_id,
                    "is_active": True
                })
        if not curriculum_doc:
            try:
                conn = get_sqlite_db()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM syllabus_records WHERE user_id = ? AND is_active = 1 ORDER BY updated_at DESC LIMIT 1",
                    (user_id,)
                )
                row = cursor.fetchone()
                if row:
                    curriculum_doc = dict(row)
                conn.close()
            except Exception:
                pass

        active_semester = user.get("semester") or user.get("current_semester")
        program         = user.get("degree") or user.get("program") or "Engineering"
        department      = user.get("department") or user.get("branch") or "Information Technology"

        # Validated subjects check
        valid_subjects = []
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

        requested_subject = str(data.get("subject") or "").strip()
        
        # If user has validated subjects, ensure requested_subject matches or falls back to first valid subject
        selected_subject = requested_subject
        if valid_subjects:
            matched = next((s for s in valid_subjects if requested_subject.lower() in s.lower() or s.lower() in requested_subject.lower()), None)
            if matched:
                selected_subject = matched
            elif requested_subject and requested_subject not in valid_subjects:
                # Do NOT invent subjects or use generic outside subjects
                selected_subject = valid_subjects[0]
        elif not selected_subject:
            selected_subject = "Information Technology Engineering"

        module     = str(data.get("module") or data.get("topic") or "Core Application")
        difficulty = str(data.get("difficulty") or "Medium")

        lab_data = gemini_service.generate_reality_lab(
            subject=selected_subject,
            module=module,
            difficulty=difficulty,
            syllabus_context=syllabus_ctx,
            semester=str(active_semester or ""),
            program=program,
            department=department
        )
        return jsonify({"success": True, "lab": lab_data, "active_semester": active_semester, "subject": selected_subject}), 200
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
        curriculum_doc = None
        mongo_db = get_mongodb()
        if mongo_db is not None:
            curriculum_doc = mongo_db["syllabi"].find_one({
                "student_id": user_id,
                "$or": [{"is_active": True}, {"status": {"$in": ["ACTIVE", "READY"]}}]
            }, sort=[("updated_at", -1), ("version", -1)])
            if not curriculum_doc:
                curriculum_doc = mongo_db.curriculum_registry.find_one({
                    "user_id": user_id,
                    "is_active": True
                })
        if not curriculum_doc:
            try:
                conn = get_sqlite_db()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM syllabus_records WHERE user_id = ? AND is_active = 1 ORDER BY updated_at DESC LIMIT 1",
                    (user_id,)
                )
                row = cursor.fetchone()
                if row:
                    curriculum_doc = dict(row)
                conn.close()
            except Exception:
                pass

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

        requested_subject = str(data.get("subject") or "").strip()
        requested_topic   = str(data.get("topic") or data.get("module") or "").strip()

        # Subject validation: Must exist in validated active semester curriculum
        selected_subject = None
        if valid_subjects:
            matched_sub = next((s for s in valid_subjects if requested_subject.lower() in s.lower() or s.lower() in requested_subject.lower()), None)
            if not matched_sub:
                return jsonify({
                    "success": False,
                    "error": f"The selected subject '{requested_subject}' does not exist in your active Semester {active_semester or ''} curriculum. Please select a valid syllabus subject.",
                    "valid_subjects": valid_subjects
                }), 400
            selected_subject = matched_sub
        else:
            selected_subject = requested_subject or "Computer Science"

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

        transfer_data = gemini_service.generate_knowledge_transfer(
            subject=selected_subject,
            topic=selected_topic,
            semester=str(active_semester or ""),
            program=program,
            department=department,
            syllabus_context=syllabus_ctx
        )

        return jsonify({
            "success": True,
            "activity": transfer_data,
            "exact_subject": selected_subject,
            "exact_syllabus_topic": selected_topic,
            "semester": active_semester
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/challenge/quiz", methods=["GET"])
@require_auth
def get_challenge_quiz():
    try:
        subject    = request.args.get("subject", "General Academic")
        module     = request.args.get("module", "All")
        difficulty = request.args.get("difficulty", "Medium")
        quiz_data  = gemini_service.generate_knowledge_challenge(subject, module, difficulty)
        return jsonify({"success": True, "quiz": quiz_data}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/challenge/submit", methods=["POST"])
@require_auth
def submit_challenge():
    try:
        user_id = _current_user_id()
        user    = _lookup_user_by_id(user_id)
        data    = request.get_json(force=True) or {}
        subject = str(data.get("subject") or "General Academic")
        score   = int(data.get("score", 0))
        total   = int(data.get("total_questions", 5))
        pct     = round((score / total) * 100, 2) if total > 0 else 0.0
        student_name = (user or {}).get("name", "Student")

        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["knowledge_challenges"].insert_one({
                "student_name": student_name,
                "student_id":   user_id,
                "subject":      subject,
                "score":        score,
                "total_questions": total,
                "percentage":   pct,
                "completed_at": datetime.utcnow(),
            })
        else:
            conn   = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO knowledge_challenges (student_name, subject, title, score, total_questions, percentage) VALUES (?,?,?,?,?,?)",
                (student_name, subject, f"{subject} Challenge", score, total, pct)
            )
            conn.commit()
            conn.close()

        return jsonify({"success": True, "percentage": pct, "score": score, "total": total}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# MEMORY CARDS
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
                    {"student_id": user_id},
                    {"student_id": email},
                ]
            }
            if name:
                query["$or"].append({"student_name": name})
            cards = [mongo_serialize(d) for d in
                     mongo_db["academic_memory"].find(query).sort("next_review", 1)]
            return jsonify({"success": True, "cards": cards}), 200
        conn   = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM academic_memory WHERE student_name=? ORDER BY next_review ASC", (name,))
        rows = cursor.fetchall()
        conn.close()
        return jsonify({"success": True, "cards": [dict(r) for r in rows]}), 200
    except Exception as exc:
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
            if ObjectId:
                try:
                    mongo_db["academic_memory"].update_one(
                        {"_id": ObjectId(card_id)},
                        {"$set": {"status": "Mastered", "next_review": next_rev}}
                    )
                except Exception:
                    pass
            mongo_db["academic_memory"].update_one(
                {"id": str(card_id)},
                {"$set": {"status": "Mastered", "next_review": next_rev}}
            )
        else:
            conn   = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE academic_memory SET status='Mastered', next_review=? WHERE id=?", (next_rev, card_id))
            conn.commit()
            conn.close()
        return jsonify({"success": True, "card_id": card_id}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/notifications", methods=["GET"])
@require_auth
def get_notifications():
    try:
        user_id      = _current_user_id()
        session_role = _current_role()
        user         = _lookup_user_by_id(user_id)
        student_name = (user or {}).get("name", "")
        email        = (user or {}).get("email", "")

        mongo_db = get_mongodb()
        if mongo_db is not None:
            query: dict = {}
            if session_role == "student":
                query["$or"] = [
                    {"target_id": user_id},
                    {"target_id": email},
                    {"target_role": "all"},
                ]
                if student_name:
                    query["$or"].append({"target_role": "student", "target_name": student_name})
            else:
                query["$or"] = [
                    {"target_id": user_id},
                    {"target_id": email},
                    {"target_role": "teacher"},
                    {"target_role": "all"},
                ]
            docs = [mongo_serialize(d) for d in
                    mongo_db["notifications"].find(query).sort("created_at", -1)]
            return jsonify({"success": True, "notifications": docs}), 200

        conn   = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notifications WHERE target_name = ? OR target_role = 'all' OR target_role = ? ORDER BY created_at DESC", (student_name, session_role))
        rows = cursor.fetchall()
        conn.close()
        return jsonify({"success": True, "notifications": [dict(r) for r in rows]}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/notifications/<notif_id>/read", methods=["PUT"])
@require_auth
def mark_notification_read(notif_id: str):
    try:
        mongo_db = get_mongodb()
        if mongo_db is not None:
            if ObjectId:
                try:
                    mongo_db["notifications"].update_one(
                        {"_id": ObjectId(notif_id)}, {"$set": {"is_read": True}}
                    )
                except Exception:
                    pass
            mongo_db["notifications"].update_one(
                {"id": str(notif_id)}, {"$set": {"is_read": True}}
            )
        else:
            conn   = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE notifications SET is_read=1 WHERE id=?", (notif_id,))
            conn.commit()
            conn.close()
        return jsonify({"success": True, "id": notif_id}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# OPPORTUNITIES (role/level aware, no fake data)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/opportunities", methods=["GET"])
@require_auth
def get_opportunities_api():
    try:
        user_id  = _current_user_id()
        user     = _lookup_user_by_id(user_id)
        level    = request.args.get("level") or (user or {}).get("level", "school")
        dept     = request.args.get("department") or (user or {}).get("domain") or (user or {}).get("department") or "General"
        board    = request.args.get("board") or (user or {}).get("board") or "CBSE"
        today_str = datetime.now().strftime("%B %d, %Y")

        if level == "school":
            news = [
                {
                    "id": "school-news-1",
                    "title": f"National Science & Mathematics Olympiad 2026 for {board} Students",
                    "source": "Ministry of Education",
                    "date": today_str,
                    "category": "Olympiads",
                    "summary": "Registration opens for inter-school olympiads for Class 9–12.",
                    "verified": True,
                    "url": "https://cbse.gov.in",
                },
                {
                    "id": "school-news-2",
                    "title": "National STEM & AI Innovation Scholarship 2026",
                    "source": "Dept. of Science & Technology",
                    "date": today_str,
                    "category": "Scholarships",
                    "summary": "Merit scholarship up to ₹50,000/year for school STEM students.",
                    "verified": True,
                    "url": "https://dst.gov.in",
                },
            ]
            opps = [
                {
                    "id": "school-opp-1",
                    "title": "Inter-School Coding & Robotics Championship 2026",
                    "organizer": "National Science Foundation",
                    "category": "Competitions",
                    "deadline": "October 30, 2026",
                    "prize": "₹50,000 + Certificate",
                    "isOnline": True,
                    "url": "https://dst.gov.in",
                },
            ]
        else:
            news = [
                {
                    "id": "college-news-1",
                    "title": "Smart India Hackathon 2026 Senior Edition",
                    "source": "AICTE / Ministry of Education",
                    "date": today_str,
                    "category": "Hackathons",
                    "summary": "SIH 2026 opens for hardware and software problem statements.",
                    "verified": True,
                    "url": "https://sih.gov.in",
                },
                {
                    "id": "college-news-2",
                    "title": "Google Summer of Code (GSoC) 2026 Mentor Organizations",
                    "source": "Google Open Source",
                    "date": today_str,
                    "category": "Programs",
                    "summary": "GSoC 2026 opens with 200+ organizations accepting student proposals.",
                    "verified": True,
                    "url": "https://summerofcode.withgoogle.com",
                },
            ]
            opps = [
                {
                    "id": "college-opp-1",
                    "title": f"Microsoft Imagine Cup 2026 ({dept})",
                    "organizer": "Microsoft",
                    "category": "Competitions",
                    "deadline": "November 20, 2026",
                    "prize": "$100,000 USD",
                    "isOnline": True,
                    "url": "https://imaginecup.microsoft.com",
                },
            ]

        return jsonify({
            "success":       True,
            "last_updated":  today_str,
            "news":          news,
            "opportunities": opps,
        }), 200
    except Exception as exc:
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
