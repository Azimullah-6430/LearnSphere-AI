"""
LearnSphere AI - Database Layer with MongoDB Atlas & Local Fallback
Connects to MongoDB Atlas using PyMongo and manages clean persistent collections.
"""

import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime

try:
    import pymongo  # type: ignore
    MongoClient = pymongo.MongoClient  # type: ignore
    PYMONGO_AVAILABLE = True
except Exception:
    MongoClient = None  # type: ignore
    PYMONGO_AVAILABLE = False

from dotenv import load_dotenv

_db_dir = Path(__file__).resolve().parent
_backend_dir = _db_dir.parent
_root_dir = _backend_dir.parent

load_dotenv(_backend_dir / ".env", override=True)
load_dotenv(_root_dir / ".env", override=True)
load_dotenv(override=True)

DB_PATH = Path(__file__).resolve().parent.parent / "learnsphere.db"

_mongo_client = None
_mongo_db = None
_use_mongo = False

def get_mongodb():
    """Returns MongoDB database instance or None if not configured/available."""
    global _mongo_client, _mongo_db, _use_mongo
    if _mongo_db is not None:
        try:
            _mongo_client.admin.command('ping')
            return _mongo_db
        except Exception:
            _mongo_db = None
            _mongo_client = None

    mongo_uri = os.getenv("MONGODB_URI", "").strip()
    db_name = os.getenv("DB_NAME", "learnsphere").strip()

    if PYMONGO_AVAILABLE and mongo_uri and "<db_username>" not in mongo_uri and not mongo_uri.startswith("your_"):
        client_options = [
            {"serverSelectionTimeoutMS": 4000},
            {"serverSelectionTimeoutMS": 4000, "tlsAllowInvalidCertificates": True},
            {"serverSelectionTimeoutMS": 4000, "tlsInsecure": True}
        ]
        try:
            import certifi
            client_options.insert(1, {"serverSelectionTimeoutMS": 4000, "tlsCAFile": certifi.where()})
        except ImportError:
            pass

        for opts in client_options:
            try:
                client = MongoClient(mongo_uri, **opts)
                client.admin.command('ping')
                _mongo_client = client
                _mongo_db = client[db_name]
                _use_mongo = True
                return _mongo_db
            except Exception:
                continue

        _use_mongo = False
        return None
    return None

def is_using_mongo() -> bool:
    return get_mongodb() is not None

def get_collection(collection_name: str):
    db = get_mongodb()
    if db is not None:
        return db[collection_name]
    return None

def get_sqlite_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

# Alias for backward compatibility
get_db = get_sqlite_db

def init_db():
    """Initialize MongoDB collections and SQLite fallback schema without fake demo data."""
    mongo_db = get_mongodb()
    if mongo_db is not None:
        _init_mongodb_indexes(mongo_db)
    # Always ensure SQLite schema is migrated cleanly as well
    _init_sqlite_schema()

def _init_mongodb_indexes(db):
    """Ensure indexes on MongoDB collections for persistent performance."""
    try:
        db["users"].create_index("email", unique=True)
        db["evaluations"].create_index("student_name")
        db["evaluations"].create_index("created_at")
    except Exception as e:
        print("[MongoDB] Index setup notice:", e)

def _init_sqlite_schema():
    conn = get_sqlite_db()
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        role TEXT NOT NULL DEFAULT 'student',
        level TEXT DEFAULT 'school',
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
    """)

    # Auto-migrate missing columns for pre-existing SQLite databases
    cursor.execute("PRAGMA table_info(users);")
    existing_cols = {row[1] for row in cursor.fetchall()}
    required_cols = {
        "password_hash": "TEXT",
        "role": "TEXT DEFAULT 'student'",
        "level": "TEXT DEFAULT 'school'",
        "teacher_level": "TEXT",
        "institution_name": "TEXT",
        "department": "TEXT",
        "domain": "TEXT",
        "board": "TEXT",
        "roll_number": "TEXT",
        "section": "TEXT",
        "grade_level": "TEXT",
        "stream": "TEXT",
        "semester": "INTEGER",
        "subjects_json": "TEXT",
        "syllabus_path": "TEXT",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    }
    for col_name, col_def in required_cols.items():
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def};")
            except Exception as e:
                print(f"[SQLite] Notice adding column {col_name}: {e}")

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT NOT NULL,
        roll_number TEXT,
        subject TEXT NOT NULL,
        assessment_title TEXT NOT NULL,
        total_marks REAL NOT NULL,
        obtained_marks REAL NOT NULL,
        percentage REAL NOT NULL,
        grade TEXT NOT NULL,
        status TEXT DEFAULT 'success',
        overall_feedback TEXT,
        evaluation_notes_json TEXT,
        question_paper_path TEXT,
        answer_script_path TEXT,
        rubrics_path TEXT,
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
        mastery INTEGER DEFAULT 50,
        last_reviewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        next_review TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        retention_rate INTEGER DEFAULT 75,
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
    """)
    conn.commit()
    conn.close()
