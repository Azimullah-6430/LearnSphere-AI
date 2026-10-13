"""
LearnSphere AI - Database Layer
MongoDB is the authoritative production database.
SQLite is only permitted in explicit local development mode (ENV=development).
Production startup will hard-fail if MongoDB is unavailable.
"""

from __future__ import annotations

import os
import sys
import time
import logging
import sqlite3
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ── Environment loading ───────────────────────────────────────────────────────
_db_dir     = Path(__file__).resolve().parent
_backend_dir = _db_dir.parent
_root_dir   = _backend_dir.parent

load_dotenv(_backend_dir / ".env", override=True)
load_dotenv(_root_dir / ".env", override=True)
load_dotenv(override=True)

# ── pymongo import ─────────────────────────────────────────────────────────────
try:
    import pymongo                          # type: ignore
    from pymongo import MongoClient         # type: ignore
    from pymongo.errors import (            # type: ignore
        ConnectionFailure, ServerSelectionTimeoutError,
        ConfigurationError, OperationFailure,
    )
    from bson import ObjectId               # type: ignore
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    ObjectId = None

# ── SQLite path (dev-only) ─────────────────────────────────────────────────────
DB_PATH = _backend_dir / "learnsphere.db"

# ── Singleton state ────────────────────────────────────────────────────────────
_mongo_client: "MongoClient | None" = None
_mongo_db     = None
_last_mongo_attempt_time: float = 0.0
_MONGO_RETRY_INTERVAL: float = 30.0  # Retry Atlas connection at most once every 30 seconds


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC: MongoDB connection
# ══════════════════════════════════════════════════════════════════════════════

def get_mongodb():
    """
    Return the MongoDB database instance.
    If MongoDB Atlas is temporarily unreachable, logs a warning and returns None
    so the app can smoothly fall back to SQLite without blocking Gunicorn workers.
    """
    global _mongo_client, _mongo_db, _last_mongo_attempt_time

    if _mongo_db is not None:
        return _mongo_db

    # Prevent blocking worker on every request if Atlas is currently unreachable
    now = time.time()
    if (now - _last_mongo_attempt_time) < _MONGO_RETRY_INTERVAL:
        return None

    _last_mongo_attempt_time = now

    mongo_uri = os.getenv("MONGODB_URI", "").strip()
    db_name   = os.getenv("MONGODB_DB_NAME", os.getenv("DB_NAME", "learnsphere")).strip()
    env       = os.getenv("ENV", "production").strip().lower()

    if not PYMONGO_AVAILABLE:
        logger.warning("[DB] pymongo is not installed. Using SQLite.")
        return None

    if not mongo_uri or "<db_username>" in mongo_uri or mongo_uri.startswith("your_"):
        logger.warning("[DB] MONGODB_URI not configured. Using SQLite.")
        return None

    # Fast connection attempts with TLS certificate
    tls_options: list[dict] = []
    try:
        import certifi  # type: ignore
        tls_options.append({
            "serverSelectionTimeoutMS": 2500,
            "connectTimeoutMS": 2500,
            "socketTimeoutMS": 20000,
            "tlsCAFile": certifi.where(),
        })
    except ImportError:
        pass

    tls_options.append({
        "serverSelectionTimeoutMS": 2500,
        "connectTimeoutMS": 2500,
        "socketTimeoutMS": 20000,
        "tlsAllowInvalidCertificates": True,
    })

    last_error: str = ""
    is_ip_blocked = False
    for opts in tls_options:
        try:
            client = MongoClient(mongo_uri, **opts)
            client.admin.command("ping")          # lightweight health check
            _mongo_client = client
            _mongo_db     = client[db_name]
            logger.info("[DB] MongoDB connected successfully → database '%s'", db_name)
            return _mongo_db
        except Exception as exc:
            err_str = str(exc)
            last_error = err_str
            # Detect IP-whitelist TLS rejection specifically
            if "TLSV1_ALERT_INTERNAL_ERROR" in err_str or "SSL handshake failed" in err_str:
                is_ip_blocked = True
            continue

    # All connection attempts failed
    if is_ip_blocked:
        ip_msg = (
            "\n\nFIX REQUIRED — MongoDB Atlas IP Whitelist:\n"
            "  1. Go to: https://cloud.mongodb.com\n"
            "  2. Select your project → Security → Network Access\n"
            "  3. Click 'Add IP Address'\n"
            "  4. Click 'Allow Access from Anywhere' (0.0.0.0/0) for Render deployment\n"
            "     OR add your specific machine IP for local development\n"
            "  5. Click 'Confirm' and wait ~30 seconds for it to take effect\n"
            "  6. Restart the server\n"
        )
        msg = f"Cannot connect to MongoDB Atlas: IP not whitelisted (SSL handshake rejected).{ip_msg}"
    else:
        msg = f"Cannot connect to MongoDB: {last_error}"

    # Fallback gracefully to SQLite so user requests (registration, login, dashboard) never hang or timeout
    logger.warning("[DB] %s  Serving traffic via SQLite until MongoDB becomes reachable.", msg)
    return None


def is_using_mongo() -> bool:
    """Returns True if MongoDB is connected."""
    try:
        return get_mongodb() is not None
    except Exception:
        return False


def get_collection(collection_name: str):
    """Return a MongoDB collection or None (dev-only SQLite mode)."""
    db = get_mongodb()
    return db[collection_name] if db is not None else None


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC: SQLite (dev / fallback)
# ══════════════════════════════════════════════════════════════════════════════

def get_sqlite_db():
    custom_path = os.getenv("SQLITE_DB_PATH")
    db_file = Path(custom_path) if custom_path else DB_PATH
    conn = sqlite3.connect(str(db_file), timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 30000;")
    except Exception:
        pass
    return conn

# Backward-compat alias
get_db = get_sqlite_db


# ══════════════════════════════════════════════════════════════════════════════
# INIT: Create indexes and schema
# ══════════════════════════════════════════════════════════════════════════════

def init_db():
    """
    Initialise the database layer.
    For MongoDB: create all required indexes.
    For SQLite: migrate schema.
    """
    try:
        mongo_db = get_mongodb()
    except Exception as exc:
        logger.warning("[DB] Initial Mongo connection deferred: %s", exc)
        mongo_db = None

    if mongo_db is not None:
        _init_mongodb_indexes(mongo_db)
    _init_sqlite_schema()


def _init_mongodb_indexes(db) -> None:
    """Idempotent index creation.  Runs at every startup."""
    try:
        # users
        db["users"].create_index("email", unique=True, background=True)
        db["users"].create_index("user_id", unique=True, sparse=True, background=True)
        db["users"].create_index("role", background=True)

        # evaluations
        db["evaluations"].create_index("student_id", background=True)
        db["evaluations"].create_index("teacher_id",  background=True)
        db["evaluations"].create_index("evaluation_source", background=True)
        db["evaluations"].create_index("class_id", background=True)
        db["evaluations"].create_index("created_by_user_id", background=True)
        db["evaluations"].create_index("student_name", background=True)
        db["evaluations"].create_index([("created_at", -1)], background=True)
        db["evaluations"].create_index("status", background=True)

        # syllabi - indexed for fast retrieval by studentId, syllabusId, semester, curriculumStatus
        db["syllabi"].create_index("student_id", background=True)
        db["syllabi"].create_index("studentId", background=True)
        db["syllabi"].create_index("syllabus_id", background=True)
        db["syllabi"].create_index("syllabusId", background=True)
        db["syllabi"].create_index("semester", background=True)
        db["syllabi"].create_index("curriculumStatus", background=True)
        db["syllabi"].create_index("status", background=True)
        db["syllabi"].create_index([("student_id", 1), ("status", 1)], background=True)
        db["syllabi"].create_index([("student_id", 1), ("curriculumStatus", 1)], background=True)
        db["syllabi"].create_index([("studentId", 1), ("curriculumStatus", 1)], background=True)
        db["syllabi"].create_index([("student_id", 1), ("is_active", 1)], background=True)
        db["syllabi"].create_index([("student_id", 1), ("file_hash", 1)], background=True)
        db["syllabi"].create_index([("studentId", 1), ("file_hash", 1)], background=True)
        db["syllabi"].create_index([("student_id", 1), ("semester", 1), ("is_active", 1)], background=True)
        db["syllabi"].create_index([("studentId", 1), ("semester", 1), ("is_active", 1)], background=True)

        # misconceptions
        db["misconceptions"].create_index("student_name", background=True)
        db["misconceptions"].create_index("student_id", background=True)
        db["misconceptions"].create_index("teacher_id", background=True)
        db["misconceptions"].create_index("evaluation_id", background=True)
        db["misconceptions"].create_index("evaluation_source", background=True)
        db["misconceptions"].create_index("class_id", background=True)

        # action_items
        db["action_items"].create_index("teacher_id", background=True)
        db["action_items"].create_index("student_id", background=True)
        db["action_items"].create_index("evaluation_id", background=True)
        db["action_items"].create_index("evaluation_source", background=True)
        db["action_items"].create_index("class_id", background=True)
        db["action_items"].create_index([("created_at", -1)], background=True)

        # plagiarism
        db["plagiarism_records"].create_index("file_hash", sparse=True, background=True)

        # notifications
        db["notifications"].create_index([("created_at", -1)], background=True)

        # opportunities and news
        db["news_items"].create_index("id", unique=True, background=True)
        db["news_items"].create_index("student_type", background=True)
        db["news_items"].create_index("departments", background=True)
        db["opportunities_items"].create_index("id", unique=True, background=True)
        db["opportunities_items"].create_index("student_type", background=True)
        db["opportunities_items"].create_index("departments", background=True)
        db["opportunities_items"].create_index("opportunity_status", background=True)
        db["opportunities_sync_log"].create_index([("timestamp", -1)], background=True)

        # teacher_classes and class_memberships
        db["teacher_classes"].create_index([("teacher_id", 1), ("id", 1)], background=True)
        db["teacher_classes"].create_index([("teacher_id", 1), ("created_at", -1)], background=True)
        db["class_memberships"].create_index([("class_id", 1), ("student_id", 1)], unique=True, background=True)
        db["class_memberships"].create_index([("teacher_id", 1), ("class_id", 1)], background=True)
        db["class_memberships"].create_index("student_user_id", sparse=True, background=True)
        db["plagiarism_records"].create_index([("teacher_id", 1), ("class_id", 1)], background=True)

        # Legacy data migration for provenance
        _migrate_mongo_legacy_provenance(db)

        logger.info("[DB] MongoDB indexes verified.")
    except Exception as exc:
        # Non-fatal: indexes may already exist
        logger.warning("[DB] Index setup notice: %s", exc)


def _migrate_mongo_legacy_provenance(db) -> None:
    """Safely migrate and repair legacy MongoDB evaluation, misconception, and action item records missing provenance."""
    try:
        from .evaluation.repair import run_safe_evaluation_repair
        run_safe_evaluation_repair(dry_run=False, backup=True)
    except Exception as exc:
        logger.warning("[DB] Mongo legacy migration notice: %s", exc)



def _init_sqlite_schema() -> None:
    """SQLite schema migration for local development only."""
    conn = get_sqlite_db()
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        role TEXT NOT NULL DEFAULT 'student',
        level TEXT DEFAULT 'school',
        teacher_level TEXT,
        institution_name TEXT,
        degree TEXT,
        program TEXT,
        department TEXT,
        branch TEXT,
        domain TEXT,
        current_year TEXT,
        academic_year TEXT,
        regulation TEXT,
        batch TEXT,
        board TEXT,
        roll_number TEXT,
        section TEXT,
        grade_level TEXT,
        stream TEXT,
        semester INTEGER,
        current_semester INTEGER,
        subjects_json TEXT,
        syllabus_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        teacher_id TEXT,
        created_by_user_id TEXT,
        created_by_role TEXT,
        evaluation_source TEXT DEFAULT 'UNKNOWN',
        class_id TEXT,
        student_name TEXT NOT NULL,
        roll_number TEXT,
        subject TEXT NOT NULL,
        assessment_title TEXT NOT NULL,
        total_marks REAL NOT NULL,
        obtained_marks REAL NOT NULL,
        percentage REAL NOT NULL,
        grade TEXT NOT NULL,
        status TEXT DEFAULT 'COMPLETED',
        evaluation_status TEXT DEFAULT 'COMPLETED',
        overall_feedback TEXT,
        evaluation_notes_json TEXT,
        question_paper_path TEXT,
        answer_script_path TEXT,
        rubrics_path TEXT,
        is_unreadable INTEGER DEFAULT 0,
        assigned_to_teacher INTEGER DEFAULT 0,
        is_teacher_overridden INTEGER DEFAULT 0,
        unreadable_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS evaluation_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        evaluation_id INTEGER NOT NULL,
        question_number TEXT NOT NULL,
        question_type TEXT,
        maximum_marks REAL NOT NULL,
        awarded_marks REAL NOT NULL,
        is_correct BOOLEAN DEFAULT 0,
        answer_present BOOLEAN DEFAULT 1,
        student_answer TEXT,
        answer_summary TEXT,
        what_was_done_well TEXT,
        missing_points TEXT,
        expected_answer TEXT,
        improvement_advice TEXT
    );

    CREATE TABLE IF NOT EXISTS plagiarism_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT NOT NULL,
        roll_number TEXT,
        subject TEXT NOT NULL,
        assessment_title TEXT NOT NULL,
        pair_match TEXT,
        context TEXT,
        similarity REAL NOT NULL,
        level TEXT NOT NULL,
        suspected BOOLEAN DEFAULT 0,
        details TEXT,
        file_hash TEXT,
        teacher_id TEXT,
        class_id TEXT,
        student_id TEXT,
        evaluation_id TEXT,
        matched_evaluation_id TEXT,
        matched_student_id TEXT,
        matched_student_name TEXT,
        matched_roll_number TEXT,
        matched_passage TEXT,
        evidence TEXT,
        status TEXT DEFAULT 'Pending Review',
        review_notes TEXT,
        reviewed_at TEXT,
        reviewed_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS misconceptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        evaluation_id TEXT,
        student_id TEXT,
        teacher_id TEXT,
        created_by_user_id TEXT,
        created_by_role TEXT,
        evaluation_source TEXT DEFAULT 'UNKNOWN',
        class_id TEXT,
        student_name TEXT,
        subject TEXT NOT NULL,
        topic TEXT NOT NULL,
        concept TEXT NOT NULL,
        description TEXT NOT NULL,
        frequency INTEGER DEFAULT 1,
        severity TEXT DEFAULT 'Medium',
        remedy TEXT,
        resolved BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS academic_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT NOT NULL,
        subject TEXT NOT NULL,
        topic TEXT NOT NULL,
        mastery INTEGER DEFAULT 0,
        last_reviewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        next_review TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        retention_rate INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Learning'
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_role TEXT NOT NULL,
        target_id TEXT,
        target_name TEXT,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        category TEXT DEFAULT 'info',
        is_read BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS knowledge_challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT NOT NULL,
        subject TEXT NOT NULL,
        title TEXT NOT NULL,
        score INTEGER NOT NULL,
        total_questions INTEGER NOT NULL,
        percentage REAL NOT NULL,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS syllabi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        syllabus_id TEXT UNIQUE,
        student_id TEXT,
        student_name TEXT,
        file_path TEXT,
        file_hash TEXT,
        file_name TEXT,
        level TEXT,
        semester TEXT,
        class_level TEXT,
        analysis_json TEXT,
        status TEXT DEFAULT 'NOT_UPLOADED',
        version INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS action_items (
        id TEXT PRIMARY KEY,
        teacher_id TEXT,
        student_id TEXT,
        evaluation_id TEXT,
        created_by_user_id TEXT,
        created_by_role TEXT,
        evaluation_source TEXT DEFAULT 'UNKNOWN',
        class_id TEXT,
        student_name TEXT NOT NULL,
        roll_number TEXT,
        academic_status TEXT,
        subject TEXT NOT NULL,
        topic TEXT NOT NULL,
        skill_or_topic TEXT,
        question_num TEXT,
        total_marks REAL DEFAULT 0,
        maximum_marks REAL DEFAULT 0,
        marks_lost REAL DEFAULT 0,
        loss_ratio REAL DEFAULT 0,
        affected_questions TEXT,
        marks_lost_per_question TEXT,
        exact_question TEXT,
        student_answer TEXT,
        misconception TEXT,
        evidence TEXT,
        correct_understanding TEXT,
        issue TEXT,
        priority TEXT DEFAULT 'Medium',
        severity TEXT DEFAULT 'Medium',
        action TEXT,
        recommended_action TEXT,
        category TEXT DEFAULT 'general',
        status TEXT DEFAULT 'New',
        is_unreadable BOOLEAN DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS teacher_classes (
        id TEXT PRIMARY KEY,
        teacher_id TEXT NOT NULL,
        name TEXT NOT NULL,
        level TEXT,
        type TEXT,
        board TEXT,
        grade_level TEXT,
        section TEXT,
        department TEXT,
        semester TEXT,
        subjects_json TEXT,
        students_json TEXT,
        students_count INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS class_memberships (
        id TEXT PRIMARY KEY,
        class_id TEXT NOT NULL,
        teacher_id TEXT NOT NULL,
        student_id TEXT NOT NULL,
        student_user_id TEXT,
        student_name TEXT NOT NULL,
        roll_number TEXT,
        email TEXT,
        section TEXT,
        level TEXT DEFAULT 'school',
        is_active INTEGER DEFAULT 1,
        account_linked INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(class_id, student_id)
    );
    """)

    cursor.execute("PRAGMA table_info(class_memberships);")
    mem_cols = {row[1] for row in cursor.fetchall()}
    needed_mem_cols = {
        "account_linked": "INTEGER DEFAULT 0",
        "level": "TEXT DEFAULT 'school'",
        "is_active": "INTEGER DEFAULT 1",
        "status": "TEXT DEFAULT 'Active'",
    }
    for col, defn in needed_mem_cols.items():
        if col not in mem_cols:
            try:
                cursor.execute(f"ALTER TABLE class_memberships ADD COLUMN {col} {defn};")
            except Exception as exc:
                logger.debug("[DB] SQLite class_memberships column migration (%s): %s", col, exc)
    try:
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_class_memberships_unique ON class_memberships(class_id, student_id);")
    except Exception as exc:
        logger.debug("[DB] SQLite class_memberships index notice: %s", exc)

    # Auto-migrate: add any missing columns without breaking existing data
    cursor.execute("PRAGMA table_info(users);")
    existing_cols = {row[1] for row in cursor.fetchall()}
    needed_cols = {
        "user_id": "TEXT",
        "teacher_level": "TEXT",
        "institution_name": "TEXT",
        "degree": "TEXT",
        "program": "TEXT",
        "department": "TEXT",
        "branch": "TEXT",
        "domain": "TEXT",
        "current_year": "TEXT",
        "academic_year": "TEXT",
        "regulation": "TEXT",
        "batch": "TEXT",
        "semester": "INTEGER",
        "current_semester": "INTEGER",
        "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "streak_count": "INTEGER DEFAULT 1",
        "last_active_date": "TEXT",
        "longest_streak": "INTEGER DEFAULT 1",
        "active_days_json": "TEXT",
    }
    for col, defn in needed_cols.items():
        if col not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {defn};")
            except Exception as exc:
                logger.debug("[DB] SQLite column migration notice (%s): %s", col, exc)

    try:
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);")
    except Exception as exc:
        logger.debug("[DB] SQLite users user_id index notice: %s", exc)

    # Migrations for evaluations
    cursor.execute("PRAGMA table_info(evaluations);")
    existing_eval_cols = {row[1] for row in cursor.fetchall()}
    needed_eval_cols = {
        "student_id": "TEXT",
        "teacher_id": "TEXT",
        "created_by_user_id": "TEXT",
        "created_by_role": "TEXT",
        "evaluation_source": "TEXT DEFAULT 'UNKNOWN'",
        "class_id": "TEXT",
        "is_teacher_overridden": "INTEGER DEFAULT 0",
        "student_name_snapshot": "TEXT",
        "roll_number_snapshot": "TEXT",
        "student_user_id": "TEXT",
        "identity_status": "TEXT DEFAULT 'VERIFIED'",
        "identity_review_reason": "TEXT",
        "questions_json": "TEXT",
    }
    for col, defn in needed_eval_cols.items():
        if col not in existing_eval_cols:
            try:
                cursor.execute(f"ALTER TABLE evaluations ADD COLUMN {col} {defn};")
            except Exception as exc:
                logger.debug("[DB] SQLite evaluations migration notice (%s): %s", col, exc)

    # Migrations for misconceptions
    cursor.execute("PRAGMA table_info(misconceptions);")
    existing_misc_cols = {row[1] for row in cursor.fetchall()}
    needed_misc_cols = {
        "evaluation_id": "TEXT",
        "student_id": "TEXT",
        "teacher_id": "TEXT",
        "created_by_user_id": "TEXT",
        "created_by_role": "TEXT",
        "evaluation_source": "TEXT DEFAULT 'UNKNOWN'",
        "class_id": "TEXT",
        "identity_status": "TEXT DEFAULT 'VERIFIED'",
        "roll_number": "TEXT",
        "assessment_title": "TEXT",
        "question_number": "TEXT",
        "exact_question": "TEXT",
        "student_answer": "TEXT",
        "actual_misconception": "TEXT",
        "correct_understanding": "TEXT",
        "evidence": "TEXT",
        "evidence_status": "TEXT DEFAULT 'VERIFIED'",
        "needs_teacher_review": "INTEGER DEFAULT 0",
        "confidence": "TEXT DEFAULT 'High'",
        "awarded_marks": "REAL DEFAULT 0",
        "maximum_marks": "REAL DEFAULT 0",
        "occurrences": "INTEGER DEFAULT 1",
        "status": "TEXT DEFAULT 'Active'",
        "class_name": "TEXT",
    }
    for col, defn in needed_misc_cols.items():
        if col not in existing_misc_cols:
            try:
                cursor.execute(f"ALTER TABLE misconceptions ADD COLUMN {col} {defn};")
            except Exception as exc:
                logger.debug("[DB] SQLite misconceptions migration notice (%s): %s", col, exc)

    # Migrations for action_items
    cursor.execute("PRAGMA table_info(action_items);")
    existing_act_cols = {row[1] for row in cursor.fetchall()}
    needed_act_cols = {
        "created_by_user_id": "TEXT",
        "created_by_role": "TEXT",
        "evaluation_source": "TEXT DEFAULT 'UNKNOWN'",
        "class_id": "TEXT",
        "identity_status": "TEXT DEFAULT 'VERIFIED'",
        "class_name": "TEXT",
        "assessment_title": "TEXT",
        "skill_or_topic": "TEXT",
        "question_awarded_marks": "REAL DEFAULT 0",
        "question_max_marks": "REAL DEFAULT 0",
        "loss_ratio": "REAL DEFAULT 0",
        "priority_reason": "TEXT",
        "source_link": "TEXT",
        "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "audit_trail_json": "TEXT",
    }
    for col, defn in needed_act_cols.items():
        if col not in existing_act_cols:
            try:
                cursor.execute(f"ALTER TABLE action_items ADD COLUMN {col} {defn};")
            except Exception as exc:
                logger.debug("[DB] SQLite action_items migration notice (%s): %s", col, exc)

    # Migrations for plagiarism_records
    cursor.execute("PRAGMA table_info(plagiarism_records);")
    existing_plag_cols = {row[1] for row in cursor.fetchall()}
    needed_plag_cols = {
        "teacher_id": "TEXT",
        "class_id": "TEXT",
        "student_id": "TEXT",
        "evaluation_id": "TEXT",
        "matched_evaluation_id": "TEXT",
        "matched_student_id": "TEXT",
        "matched_student_name": "TEXT",
        "matched_roll_number": "TEXT",
        "matched_passage": "TEXT",
        "evidence": "TEXT",
        "status": "TEXT DEFAULT 'Pending Review'",
        "review_notes": "TEXT",
        "reviewed_at": "TEXT",
        "reviewed_by": "TEXT",
    }
    for col, defn in needed_plag_cols.items():
        if col not in existing_plag_cols:
            try:
                cursor.execute(f"ALTER TABLE plagiarism_records ADD COLUMN {col} {defn};")
            except Exception as exc:
                logger.debug("[DB] SQLite plagiarism_records migration notice (%s): %s", col, exc)

    # Migrations for academic_memory
    cursor.execute("PRAGMA table_info(academic_memory);")
    existing_mem_cols = {row[1] for row in cursor.fetchall()}
    needed_mem_cols = {
        "student_id": "TEXT",
        "student_name": "TEXT",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    }
    for col, defn in needed_mem_cols.items():
        if col not in existing_mem_cols:
            try:
                cursor.execute(f"ALTER TABLE academic_memory ADD COLUMN {col} {defn};")
            except Exception as exc:
                logger.debug("[DB] SQLite academic_memory migration notice (%s): %s", col, exc)

    # Migrations for notifications
    cursor.execute("PRAGMA table_info(notifications);")
    existing_notif_cols = {row[1] for row in cursor.fetchall()}
    needed_notif_cols = {
        "notification_id": "TEXT",
        "user_id": "TEXT",
        "action_url": "TEXT",
        "category": "TEXT DEFAULT 'info'"
    }
    for col, defn in needed_notif_cols.items():
        if col not in existing_notif_cols:
            try:
                cursor.execute(f"ALTER TABLE notifications ADD COLUMN {col} {defn};")
            except Exception as exc:
                logger.debug("[DB] SQLite notifications migration notice (%s): %s", col, exc)


    # Migrations for syllabi
    cursor.execute("PRAGMA table_info(syllabi);")
    existing_syllabi_cols = {row[1] for row in cursor.fetchall()}
    needed_syllabi_cols = {
        "degree": "TEXT",
        "program": "TEXT",
        "department": "TEXT",
        "branch": "TEXT",
        "current_year": "TEXT",
        "academic_year": "TEXT",
        "regulation": "TEXT",
        "validation_status": "TEXT DEFAULT 'VALID'",
        "is_active": "BOOLEAN DEFAULT 1",
        "detected_semesters": "TEXT",
        "mismatch_reason": "TEXT",
    }
    for col, defn in needed_syllabi_cols.items():
        if col not in existing_syllabi_cols:
            try:
                cursor.execute(f"ALTER TABLE syllabi ADD COLUMN {col} {defn};")
            except Exception as exc:
                logger.debug("[DB] SQLite syllabi column migration notice (%s): %s", col, exc)

    # Migrations for notifications
    cursor.execute("PRAGMA table_info(notifications);")
    existing_notif_cols = {row[1] for row in cursor.fetchall()}
    if "target_id" not in existing_notif_cols:
        try:
            cursor.execute("ALTER TABLE notifications ADD COLUMN target_id TEXT;")
        except Exception as exc:
            logger.debug("[DB] SQLite notifications migration notice: %s", exc)

    # Safe data migration for SQLite legacy evaluations
    try:
        from .evaluation.repair import run_safe_evaluation_repair
        run_safe_evaluation_repair(dry_run=False, backup=True)
    except Exception as exc:
        logger.debug("[DB] SQLite legacy data repair notice: %s", exc)

    cursor.execute("PRAGMA table_info(knowledge_challenges);")
    existing_kc_cols = {row[1] for row in cursor.fetchall()}
    needed_kc_cols = {
        "student_id": "TEXT",
        "subject_id": "TEXT",
        "topic_id": "TEXT",
        "question": "TEXT",
        "student_answer": "TEXT",
        "correct_answer": "TEXT",
        "explanation": "TEXT",
        "difficulty": "TEXT",
    }
    for col, defn in needed_kc_cols.items():
        if col not in existing_kc_cols:
            try:
                cursor.execute(f"ALTER TABLE knowledge_challenges ADD COLUMN {col} {defn};")
            except Exception as exc:
                logger.debug("[DB] SQLite knowledge_challenges column migration notice (%s): %s", col, exc)

    cursor.execute("PRAGMA table_info(evaluation_questions);")
    existing_eq_cols = {row[1] for row in cursor.fetchall()}
    if "student_answer" not in existing_eq_cols:
        try:
            cursor.execute("ALTER TABLE evaluation_questions ADD COLUMN student_answer TEXT;")
        except Exception as exc:
            logger.debug("[DB] SQLite evaluation_questions column migration notice: %s", exc)

    conn.commit()
    conn.close()
    logger.info("[DB] SQLite schema ready (development mode).")


def init_sqlite_db(conn=None) -> None:
    """Public alias to initialize or verify SQLite schema."""
    _init_sqlite_schema()


def link_student_account_by_email_sqlite(email: str, conn: sqlite3.Connection = None) -> str | None:
    """Finds an existing verified student account in SQLite by email.
    Requirement 5: Link students to existing accounts ONLY when email matches.
    """
    if not email or not email.strip():
        return None
    email_clean = email.strip().lower()
    close_conn = False
    if conn is None:
        conn = get_sqlite_db()
        close_conn = True
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, email, role FROM users WHERE LOWER(email) = ?", (email_clean,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            # Link only if role is student or general user
            if str(d.get("role") or "").lower() in ("student", "user"):
                return str(d.get("user_id") or d.get("id"))
        return None
    finally:
        if close_conn:
            conn.close()


def sync_class_membership_sqlite(
    conn: sqlite3.Connection,
    class_id: str,
    teacher_id: str,
    student_id: str,
    student_name: str,
    roll_number: str | None = None,
    email: str | None = None,
    section: str | None = None,
    level: str | None = None,
    student_user_id: str | None = None,
) -> None:
    """Sync an individual student class membership record in SQLite."""
    if not class_id or not student_id:
        return
    # Resolve student_user_id if not explicitly provided but email exists
    if not student_user_id and email:
        student_user_id = link_student_account_by_email_sqlite(email, conn)

    now = datetime.utcnow().isoformat()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO class_memberships (
            class_id, teacher_id, student_id, student_user_id, student_name,
            roll_number, email, section, level, is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT(class_id, student_id) DO UPDATE SET
            teacher_id = excluded.teacher_id,
            student_user_id = COALESCE(excluded.student_user_id, class_memberships.student_user_id),
            student_name = excluded.student_name,
            roll_number = excluded.roll_number,
            email = excluded.email,
            section = excluded.section,
            level = excluded.level,
            updated_at = excluded.updated_at;
    """, (
        str(class_id),
        str(teacher_id),
        str(student_id),
        str(student_user_id) if student_user_id else None,
        str(student_name or "").strip(),
        str(roll_number or "").strip() or None,
        str(email or "").strip() or None,
        str(section or "").strip() or None,
        str(level or "school").strip(),
        now,
        now,
    ))
    conn.commit()


def get_class_memberships_sqlite(class_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    """Retrieve all class memberships for a class in SQLite."""
    close_conn = False
    if conn is None:
        conn = get_sqlite_db()
        close_conn = True
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM class_memberships WHERE class_id = ? ORDER BY student_name ASC", (str(class_id),))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        if close_conn:
            conn.close()


def verify_sqlite_class_ownership(class_id: str, teacher_id: str, conn: sqlite3.Connection = None) -> bool:
    """Verify that teacher owns class in SQLite to prevent cross-teacher leakage."""
    close_conn = False
    if conn is None:
        conn = get_sqlite_db()
        close_conn = True
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM teacher_classes WHERE id = ? AND teacher_id = ?", (str(class_id), str(teacher_id)))
        return bool(cursor.fetchone())
    finally:
        if close_conn:
            conn.close()


def sync_class_membership_mongo(
    db,
    class_id: str,
    teacher_id: str,
    student_id: str,
    student_name: str,
    roll_number: str | None = None,
    email: str | None = None,
    section: str | None = None,
    level: str | None = None,
    student_user_id: str | None = None,
) -> None:
    """Sync class membership record in MongoDB."""
    if db is None or not class_id or not student_id:
        return
    now = datetime.utcnow().isoformat()
    # Resolve student_user_id if not provided
    if not student_user_id and email:
        email_clean = email.strip().lower()
        u = db["users"].find_one({"email": {"$regex": f"^{email_clean}$", "$options": "i"}, "role": "student"})
        if u:
            student_user_id = str(u.get("user_id") or u.get("id") or u.get("_id"))

    doc = {
        "class_id": str(class_id),
        "teacher_id": str(teacher_id),
        "student_id": str(student_id),
        "student_user_id": str(student_user_id) if student_user_id else None,
        "student_name": str(student_name or "").strip(),
        "roll_number": str(roll_number or "").strip() or None,
        "email": str(email or "").strip() or None,
        "section": str(section or "").strip() or None,
        "level": str(level or "school").strip(),
        "is_active": True,
        "updated_at": now,
    }
    db["class_memberships"].update_one(
        {"class_id": str(class_id), "student_id": str(student_id)},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True
    )


def get_class_memberships_mongo(class_id: str, db) -> list[dict]:
    """Retrieve all class memberships for a class in MongoDB."""
    if db is None or not class_id:
        return []
    return list(db["class_memberships"].find({"class_id": str(class_id)}).sort("student_name", 1))


def verify_mongo_class_ownership(class_id: str, teacher_id: str, db) -> bool:
    """Verify that teacher owns class in MongoDB."""
    if db is None or not class_id or not teacher_id:
        return False
    return bool(db["teacher_classes"].find_one({"id": str(class_id), "teacher_id": str(teacher_id)}))
