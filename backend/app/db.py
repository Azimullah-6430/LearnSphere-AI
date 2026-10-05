"""
LearnSphere AI - Database Layer
MongoDB is the authoritative production database.
SQLite is only permitted in explicit local development mode (ENV=development).
Production startup will hard-fail if MongoDB is unavailable.
"""

from __future__ import annotations

import os
import sys
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
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

# ── SQLite path (dev-only) ─────────────────────────────────────────────────────
DB_PATH = _backend_dir / "learnsphere.db"

# ── Singleton state ────────────────────────────────────────────────────────────
_mongo_client: "MongoClient | None" = None
_mongo_db     = None


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC: MongoDB connection
# ══════════════════════════════════════════════════════════════════════════════

def get_mongodb():
    """
    Return the MongoDB database instance.

    • Production  (ENV != 'development'): raises RuntimeError if unavailable.
    • Development (ENV == 'development'): logs a warning and returns None so
      the caller can fall back to SQLite.
    """
    global _mongo_client, _mongo_db

    if _mongo_db is not None:
        return _mongo_db

    mongo_uri = os.getenv("MONGODB_URI", "").strip()
    db_name   = os.getenv("MONGODB_DB_NAME", os.getenv("DB_NAME", "learnsphere")).strip()
    env       = os.getenv("ENV", "production").strip().lower()

    if not PYMONGO_AVAILABLE:
        msg = "pymongo is not installed. Add 'pymongo[srv]' to requirements.txt."
        if env == "development":
            logger.warning("[DB] %s  Falling back to SQLite.", msg)
            return None
        raise RuntimeError(msg)

    if not mongo_uri or "<db_username>" in mongo_uri or mongo_uri.startswith("your_"):
        msg = "MONGODB_URI is not set or contains a placeholder value."
        if env == "development":
            logger.warning("[DB] %s  Falling back to SQLite.", msg)
            return None
        raise RuntimeError(
            f"{msg}  "
            "Set MONGODB_URI in your environment (Render dashboard → Environment)."
        )

    # Try connection with TLS certificate, then without (for Atlas free-tier quirks)
    tls_options: list[dict] = []
    try:
        import certifi                                          # type: ignore
        tls_options.append({
            "serverSelectionTimeoutMS": 8000,
            "connectTimeoutMS": 8000,
            "tlsCAFile": certifi.where(),
        })
    except ImportError:
        pass

    tls_options.append({
        "serverSelectionTimeoutMS": 8000,
        "connectTimeoutMS": 8000,
    })
    tls_options.append({
        "serverSelectionTimeoutMS": 8000,
        "connectTimeoutMS": 8000,
        "tlsAllowInvalidCertificates": True,
    })
    # Final fallback: disable TLS hostname checking too (for Atlas IP-whitelist TLS errors)
    tls_options.append({
        "serverSelectionTimeoutMS": 8000,
        "connectTimeoutMS": 8000,
        "tlsAllowInvalidCertificates": True,
        "tlsAllowInvalidHostnames": True,
    })

    last_error: str = ""
    is_ip_blocked = False
    for opts in tls_options:
        try:
            client = MongoClient(mongo_uri, **opts)
            client.admin.command("ping")          # lightweight health check
            _mongo_client = client
            _mongo_db     = client[db_name]
            logger.info("[DB] MongoDB connected → database '%s'", db_name)
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

    if env == "development":
        logger.warning("[DB] %s  Falling back to SQLite for development.", msg)
        return None

    # Production: crash loudly instead of silently serving wrong data
    logger.critical("[DB] FATAL — %s", msg)
    raise RuntimeError(
        f"MongoDB connection failed in production: {last_error}\n"
        "Verify MONGODB_URI is correct and the Atlas cluster allows this IP.\n"
        "Go to MongoDB Atlas → Network Access → Add IP 0.0.0.0/0"
    )


def is_using_mongo() -> bool:
    """Returns True if MongoDB is connected."""
    try:
        return get_mongodb() is not None
    except RuntimeError:
        return False


def get_collection(collection_name: str):
    """Return a MongoDB collection or None (dev-only SQLite mode)."""
    db = get_mongodb()
    return db[collection_name] if db is not None else None


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC: SQLite (dev fallback)
# ══════════════════════════════════════════════════════════════════════════════

def get_sqlite_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
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
    For SQLite (dev): migrate schema.
    """
    try:
        mongo_db = get_mongodb()
    except RuntimeError as exc:
        logger.critical("[DB] init_db failed: %s", exc)
        raise

    if mongo_db is not None:
        _init_mongodb_indexes(mongo_db)
    else:
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
        db["evaluations"].create_index("student_name", background=True)
        db["evaluations"].create_index([("created_at", -1)], background=True)
        db["evaluations"].create_index("status", background=True)

        # syllabi
        db["syllabi"].create_index("student_id", background=True)
        db["syllabi"].create_index([("student_id", 1), ("status", 1)], background=True)

        # misconceptions
        db["misconceptions"].create_index("student_name", background=True)

        # plagiarism
        db["plagiarism_records"].create_index("file_hash", sparse=True, background=True)

        # notifications
        db["notifications"].create_index([("created_at", -1)], background=True)

        logger.info("[DB] MongoDB indexes verified.")
    except Exception as exc:
        # Non-fatal: indexes may already exist
        logger.warning("[DB] Index setup notice: %s", exc)


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
        department TEXT,
        domain TEXT,
        board TEXT,
        roll_number TEXT,
        section TEXT,
        grade_level TEXT,
        stream TEXT,
        semester INTEGER,
        subjects_json TEXT,
        syllabus_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        teacher_id TEXT,
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS misconceptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    """)

    # Auto-migrate: add any missing columns without breaking existing data
    cursor.execute("PRAGMA table_info(users);")
    existing_cols = {row[1] for row in cursor.fetchall()}
    needed_cols = {
        "user_id": "TEXT UNIQUE",
        "teacher_level": "TEXT",
        "institution_name": "TEXT",
        "department": "TEXT",
        "domain": "TEXT",
    }
    for col, defn in needed_cols.items():
        if col not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {defn};")
            except Exception as exc:
                logger.debug("[DB] SQLite column migration notice (%s): %s", col, exc)

    conn.commit()
    conn.close()
    logger.info("[DB] SQLite schema ready (development mode).")
