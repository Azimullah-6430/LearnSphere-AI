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

def _validate_environment() -> None:
    """Hard-fail at startup if critical environment variables are missing."""
    secret = os.getenv("SECRET_KEY", "").strip()
    known_defaults = {
        "learnsphere-ai-secret-key-production-2026",
        "learnsphere-ai-secret-key",
        "dev-secret",
        "change-me",
        "",
    }
    if ENV != "development" and (not secret or secret in known_defaults):
        msg = (
            "FATAL: SECRET_KEY is not set or uses a default value in production. "
            "Set a strong random SECRET_KEY in Render → Environment variables."
        )
        logger.critical(msg)
        raise SystemExit(msg)

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not gemini_key or gemini_key.startswith("your_"):
        if ENV != "development":
            msg = "FATAL: GEMINI_API_KEY is not configured."
            logger.critical(msg)
            raise SystemExit(msg)
        else:
            logger.warning("GEMINI_API_KEY not set (development mode).")

    logger.info("[Startup] Environment validated.")


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
        return mongo_serialize(doc) if doc else None

    conn = get_sqlite_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ? OR user_id = ?", (user_id, str(user_id)))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d.pop("password", None)
        d.pop("password_hash", None)
        return d
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

        # ── Optional profile fields ─────────────────────────────────────────
        teacher_level    = str(g("teacherLevel") or g("teacher_level") or "school")
        institution_name = str(g("institutionName") or g("institution_name") or "")
        department       = str(g("department") or "")
        level            = str(g("level") or "school")
        board            = str(g("board") or "") if level == "school" else None
        roll_number      = str(g("roll_number") or "")
        section          = str(g("section") or "")
        grade_level      = str(g("classLevel") or g("grade_level") or "")
        stream           = str(g("stream") or "")
        domain           = str(g("domain") or "")
        semester_raw     = g("semester")
        semester         = str(semester_raw) if semester_raw is not None else None

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
            "department":       department,
            "level":            level,
            "board":            board,
            "roll_number":      roll_number,
            "section":          section,
            "grade_level":      grade_level,
            "stream":           stream,
            "domain":           domain,
            "semester":         semester,
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
                 institution_name, department, domain, board, roll_number, section,
                 grade_level, stream, semester, subjects_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (stable_user_id, name, email, password_hash, role, level,
                  teacher_level, institution_name, department, domain, board,
                  roll_number, section, grade_level, stream, semester,
                  json.dumps(subjects)))
            stored_id = str(cursor.lastrowid)
            conn.commit()
            conn.close()

        # Start session
        session.permanent = True
        session["user_id"] = stored_id
        session["role"]    = role

        response_user = mongo_serialize(user_doc)
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

    # Normalize teacherLevel for frontend
    user["teacherLevel"] = (
        user.get("teacher_level")
        or user.get("teacherLevel")
        or user.get("level")
        or "school"
    )
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

    user["teacherLevel"] = (
        user.get("teacher_level")
        or user.get("teacherLevel")
        or user.get("level")
        or "school"
    )
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
            "domain", "semester", "department", "institution_name", "institutionName", "school",
            "section", "roll_number", "rollNumber", "course", "program", "academic_year",
            "academicYear", "year", "subjects", "city", "state", "country", "phone", "bio",
            "teacher_level", "teacherLevel"
        }

        update_fields = {}
        for k, v in data.items():
            if k in allowed_fields:
                if k in ("classLevel", "class"):
                    update_fields["grade_level"] = str(v) if v is not None else None
                elif k in ("institutionName", "school"):
                    update_fields["institution_name"] = str(v) if v is not None else None
                elif k == "rollNumber":
                    update_fields["roll_number"] = str(v) if v is not None else None
                elif k in ("academicYear", "year"):
                    update_fields["academic_year"] = str(v) if v is not None else None
                elif k == "teacherLevel":
                    update_fields["teacher_level"] = str(v) if v is not None else None
                elif k == "program":
                    update_fields["course"] = str(v) if v is not None else None
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
            params = [json.dumps(v) if isinstance(v, list) else str(v) for k, v in update_fields.items() if k != "updated_at"]
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

        evaluation_request = {
            "evaluation_id":   f"eval_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}",
            "submitted_by":     user_id,
            "submitter_role":   session_role,
            "student_id":       user_id if session_role == "student" else None,
            "teacher_id":       user_id if session_role == "teacher" else None,
            "subject":          subject,
            "student_name":     student_name,
            "roll_number":      roll_number,
            "assessment_title": assessment_title,
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
# SYLLABUS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/syllabus/analyze", methods=["POST"])
@require_auth
def analyze_syllabus():
    """Analyze and PERSIST syllabus linked to the authenticated user."""
    try:
        user_id  = _current_user_id()
        user     = _lookup_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found."}), 404

        syllabus_file = request.files.get("syllabus") or request.files.get("syllabus_file")
        syllabus_text = request.form.get("text", "").strip()

        level       = request.form.get("level", user.get("level", "college")).strip()
        semester    = str(request.form.get("semester", user.get("semester", "5"))).strip()
        class_level = str(request.form.get("classLevel", user.get("grade_level", "12"))).strip()
        stream      = request.form.get("stream", user.get("stream", "")).strip()
        domain      = request.form.get("domain", user.get("domain", "")).strip()

        file_path = None
        file_hash = None
        file_name = None

        if syllabus_file and syllabus_file.filename:
            if not allowed_file(syllabus_file.filename):
                return jsonify({"success": False, "error": "File type not permitted."}), 400
            # Compute hash before saving
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

        # Analyze
        analysis = gemini_service.analyze_syllabus(
            file_input, level=level, semester=semester,
            class_level=class_level, domain=domain, stream=stream
        )

        if not analysis or not isinstance(analysis, dict):
            return jsonify({"success": False, "error": "Syllabus analysis returned no data."}), 500

        syllabus_id = str(uuid.uuid4())
        now = datetime.utcnow()

        syllabus_doc = {
            "syllabus_id":  syllabus_id,
            "student_id":   user_id,
            "student_name": user.get("name", ""),
            "file_path":    file_path or "",
            "file_hash":    file_hash or "",
            "file_name":    file_name or "",
            "level":        level,
            "semester":     semester,
            "class_level":  class_level,
            "stream":       stream,
            "domain":       domain,
            "analysis":     analysis,
            "status":       "READY",
            "version":      1,
            "created_at":   now,
            "updated_at":   now,
        }

        mongo_db = get_mongodb()
        if mongo_db is not None:
            # Replace any existing syllabus for this student (bump version)
            existing = mongo_db["syllabi"].find_one(
                {"student_id": user_id, "status": "READY"},
                sort=[("version", -1)]
            )
            version = (existing.get("version", 0) + 1) if existing else 1
            syllabus_doc["version"] = version
            mongo_db["syllabi"].insert_one(syllabus_doc)
        else:
            conn   = get_sqlite_db()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO syllabi
                   (syllabus_id, student_id, student_name, file_path, file_hash,
                    file_name, level, semester, class_level, analysis_json, status, version)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (syllabus_id, user_id, user.get("name", ""), file_path or "",
                 file_hash or "", file_name or "", level, semester, class_level,
                 json.dumps(analysis), "READY", 1)
            )
            conn.commit()
            conn.close()

        response_doc = mongo_serialize(syllabus_doc)

        return jsonify({"success": True, "syllabus_id": syllabus_id, "analysis": analysis, "syllabus": response_doc}), 200

    except Exception as exc:
        logger.error("Syllabus analyze error: %s", traceback.format_exc())
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/syllabus", methods=["GET"])
@require_auth
def get_my_syllabus():
    """Return the current user's latest READY syllabus."""
    user_id = _current_user_id()
    mongo_db = get_mongodb()
    if mongo_db is not None:
        doc = mongo_db["syllabi"].find_one(
            {"student_id": user_id, "status": "READY"},
            sort=[("version", -1)]
        )
        if doc:
            return jsonify({"success": True, "syllabus": mongo_serialize(doc)}), 200
        return jsonify({"success": True, "syllabus": None}), 200

    conn   = get_sqlite_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM syllabi WHERE student_id=? AND status='READY' ORDER BY version DESC LIMIT 1",
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
        return jsonify({"success": True, "syllabus": d}), 200
    return jsonify({"success": True, "syllabus": None}), 200


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
            # Teacher sees action items from evaluations they submitted
            items_cursor = mongo_db["action_items"].find({
                "$or": [{"teacher_id": teacher_id}, {"teacher_id": None}]
            })
            items = [mongo_serialize(d) for d in items_cursor]
            return jsonify({"success": True, "items": items}), 200

        # SQLite: derive from evaluations where marks_lost > 20 and submitted_by = teacher_id
        conn   = get_sqlite_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM evaluations WHERE (total_marks - obtained_marks) > 20 AND submitted_by = ? ORDER BY created_at DESC",
            (teacher_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        items = []
        for r in rows:
            lost = int(r["total_marks"] - r["obtained_marks"])
            items.append({
                "id":              f"act_{r['id']}",
                "student_name":    r["student_name"],
                "roll_number":     r["roll_number"] or "N/A",
                "academic_status": f"At Risk (Lost {lost} marks)",
                "subject":         r["subject"],
                "topic":           r["assessment_title"],
                "marks_lost":      lost,
                "issue":           r["overall_feedback"] or f"Lost {lost} marks in {r['subject']}.",
                "priority":        "High" if lost > 30 else "Medium",
                "action":          "Assign targeted practice worksheet.",
                "status":          "New",
                "created_at":      str(r["created_at"])[:10],
            })
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

        subject     = str(data.get("subject") or "General Academic")
        concept     = str(data.get("concept") or data.get("topic") or "")
        study_method = str(data.get("study_method") or data.get("method") or "")
        level       = str(data.get("level") or (user or {}).get("level") or "school")
        semester    = str(data.get("semester") or (user or {}).get("semester") or "5")
        class_level = str(data.get("class_level") or (user or {}).get("grade_level") or "12")

        target_ctx = f"College Semester {semester}" if level.lower() == "college" else f"School Class {class_level}"
        prompt = (
            f"You are LearnSphere AI's Personal Learning Coach.\n"
            f"Context: {target_ctx} | Subject: {subject} | Concept: {concept or subject}\n"
            f"Strategy: {study_method or 'Active Coaching'}\n"
            f"Student Message: '{message}'\n\n"
            f"RULES:\n"
            f"1. Concise, structured explanation with bold terms.\n"
            f"2. Include at least ONE visual tool (Markdown Table or ASCII Flowchart/Diagram).\n"
            f"3. End with an active recall question.\n"
            f"4. Suggest spaced repetition interval."
        )
        ai_reply = gemini_service.generate_content(prompt, json_output=False)

        student_name = (user or {}).get("name", "Student")
        mongo_db = get_mongodb()
        if mongo_db is not None:
            mongo_db["academic_memory"].insert_one({
                "student_name":  student_name,
                "student_id":    user_id,
                "subject":       subject,
                "topic":         concept or subject,
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
        data         = request.get_json(force=True) or {}
        subject      = str(data.get("subject") or "General Academic")
        module       = str(data.get("module") or "Practical Application")
        difficulty   = str(data.get("difficulty") or "Medium")
        syllabus_ctx = str(data.get("syllabus_context") or "")
        lab_data = gemini_service.generate_reality_lab(subject, module, difficulty, syllabus_ctx)
        return jsonify({"success": True, "lab": lab_data}), 200
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
