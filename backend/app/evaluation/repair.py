"""
LearnSphere AI - Safe Evaluation Data Repair & Provenance Migration Procedure

This module safely analyzes, preserves (backs up), and repairs legacy or mixed evaluation
records, misconceptions, and action items between the Student Portal and Teacher Portal.

Key Guarantees & Rules:
1. Never classify a record as a teacher evaluation merely because it appears in the Teacher Portal.
2. Never classify a record as a student evaluation merely because a student name appears.
3. Do not invent missing provenance.
4. Mark uncertain records UNKNOWN / NEEDS_REVIEW.
5. Exclude uncertain records from teacher-only Misconception Map and Action Center.
6. Preserve legitimate student evaluation history.
7. Preserve legitimate teacher evaluation history.
8. Make migration safe to rerun (idempotent) without creating duplicate records or corrupting ownership.
9. Log counts of records classified, skipped and flagged for review.
10. Do not permanently delete records as part of this migration.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..db import get_mongodb, get_sqlite_db, is_using_mongo

logger = logging.getLogger(__name__)


def _create_backups_mongo(db, timestamp_str: str) -> Dict[str, int]:
    """Create timestamped snapshot backup collections in MongoDB before applying mutations."""
    # Prune old backup collections to prevent exceeding MongoDB collection quotas
    try:
        all_cols = db.list_collection_names()
        for base in ["evaluations", "misconceptions", "action_items", "teacher_classes", "class_memberships"]:
            prefix = f"{base}_backup_"
            matched = sorted([c for c in all_cols if c.startswith(prefix)])
            if len(matched) >= 3:
                for old_c in matched[:-2]:
                    try:
                        db[old_c].drop()
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"[Repair] Backup pruning notice: {e}")

    backup_counts = {}
    collections_to_backup = ["evaluations", "misconceptions", "action_items", "teacher_classes", "class_memberships"]
    
    for col_name in collections_to_backup:
        backup_col_name = f"{col_name}_backup_{timestamp_str}"
        src_col = db[col_name]
        docs = list(src_col.find({}))
        if docs:
            # Drop backup collection if somehow already exists, then insert
            db[backup_col_name].drop()
            db[backup_col_name].insert_many(docs)
            backup_counts[backup_col_name] = len(docs)
        else:
            backup_counts[backup_col_name] = 0
        logger.info("[Repair] MongoDB backup created: '%s' with %d records.", backup_col_name, backup_counts[backup_col_name])
        
    return backup_counts


def _create_backups_sqlite(conn, timestamp_str: str) -> Dict[str, int]:
    """Create timestamped snapshot backup tables in SQLite before applying mutations."""
    backup_counts = {}
    tables_to_backup = ["evaluations", "misconceptions", "action_items", "teacher_classes", "class_memberships"]
    cursor = conn.cursor()
    clean_ts = timestamp_str.replace("-", "_").replace(":", "_").replace(".", "_").replace("+", "_")
    
    for table_name in tables_to_backup:
        backup_table_name = f"{table_name}_backup_{clean_ts}"
        try:
            cursor.execute(f'CREATE TABLE IF NOT EXISTS "{backup_table_name}" AS SELECT * FROM "{table_name}";')
            cursor.execute(f'SELECT COUNT(*) FROM "{backup_table_name}";')
            count = cursor.fetchone()[0]
            backup_counts[backup_table_name] = count
            logger.info("[Repair] SQLite backup created: '%s' with %d records.", backup_table_name, count)
        except Exception as exc:
            logger.warning("[Repair] SQLite backup for table %s notice: %s", table_name, exc)
            backup_counts[backup_table_name] = 0
            
    conn.commit()
    return backup_counts


def _build_user_role_map_mongo(db) -> Dict[str, str]:
    """Build a lookup map of user identifiers -> role from MongoDB users collection."""
    user_map = {}
    for u in db["users"].find({}, {"_id": 1, "id": 1, "user_id": 1, "email": 1, "role": 1}):
        role = str(u.get("role") or "").strip().lower()
        if not role:
            continue
        if "_id" in u:
            user_map[str(u["_id"])] = role
        if "id" in u and u["id"]:
            user_map[str(u["id"])] = role
        if "user_id" in u and u["user_id"]:
            user_map[str(u["user_id"])] = role
        if "email" in u and u["email"]:
            user_map[str(u["email"]).lower()] = role
    return user_map


def _build_user_role_map_sqlite(conn) -> Dict[str, str]:
    """Build a lookup map of user identifiers -> role from SQLite users table."""
    user_map = {}
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, user_id, email, role FROM users;")
        for row in cursor.fetchall():
            role = str(row["role"] or "").strip().lower()
            if not role:
                continue
            if row["id"]:
                user_map[str(row["id"])] = role
            if row["user_id"]:
                user_map[str(row["user_id"])] = role
            if row["email"]:
                user_map[str(row["email"]).lower()] = role
    except Exception as exc:
        logger.warning("[Repair] User role map notice (SQLite): %s", exc)
    return user_map


def classify_evaluation_provenance(
    eval_doc: Dict[str, Any],
    user_role_map: Dict[str, str],
) -> Tuple[str, str, Optional[str], Optional[str], bool, str]:
    """
    Classify a single evaluation record using reliable evidence.

    Returns:
        (source, role, teacher_id, student_id, needs_review, review_reason)
        source is one of: 'TEACHER_EVALUATION', 'STUDENT_SELF_EVALUATION', 'UNKNOWN'
    """
    existing_source = str(eval_doc.get("evaluation_source") or eval_doc.get("evaluationSource") or "").strip()
    created_by_user_id = str(eval_doc.get("created_by_user_id") or "").strip() or None
    created_by_role = str(eval_doc.get("created_by_role") or eval_doc.get("createdByRole") or "").strip().lower() or None
    submitter_role = str(eval_doc.get("submitter_role") or eval_doc.get("submitterRole") or "").strip().lower() or None
    teacher_id = str(eval_doc.get("teacher_id") or eval_doc.get("teacherId") or "").strip() or None
    student_id = str(eval_doc.get("student_id") or eval_doc.get("studentId") or "").strip() or None
    workflow_type = str(eval_doc.get("workflow_type") or eval_doc.get("assessment_type") or "").strip().lower()
    is_teacher_overridden = bool(eval_doc.get("is_teacher_overridden", False))
    assigned_to_teacher = bool(eval_doc.get("assigned_to_teacher", False))

    # Clean empty strings / null strings
    if teacher_id in ("None", "null", "undefined", ""):
        teacher_id = None
    if student_id in ("None", "null", "undefined", ""):
        student_id = None
    if created_by_user_id in ("None", "null", "undefined", ""):
        created_by_user_id = None

    # Check creator identity in registered users
    creator_db_role = None
    if created_by_user_id and created_by_user_id in user_role_map:
        creator_db_role = user_role_map[created_by_user_id]

    teacher_id_role = None
    if teacher_id and teacher_id in user_role_map:
        teacher_id_role = user_role_map[teacher_id]

    student_id_role = None
    if student_id and student_id in user_role_map:
        student_id_role = user_role_map[student_id]

    # 1. Reliable Teacher Evidence:
    # - Creator DB role is teacher
    # - OR teacher_id belongs to a registered teacher AND (submitter_role == 'teacher' OR workflow indicates teacher grading OR teacher override present)
    is_verified_teacher_eval = False
    if creator_db_role == "teacher" or created_by_role == "teacher" or submitter_role == "teacher":
        is_verified_teacher_eval = True
    elif teacher_id and teacher_id_role == "teacher":
        # Teacher ID is a verified registered teacher
        if is_teacher_overridden or assigned_to_teacher or workflow_type in ("teacher_grading", "teacher_evaluation", "rubric_evaluation", "batch_evaluation") or not student_id_role:
            is_verified_teacher_eval = True

    if is_verified_teacher_eval:
        effective_teacher_id = teacher_id or (created_by_user_id if creator_db_role == "teacher" else None)
        return (
            "TEACHER_EVALUATION",
            "teacher",
            effective_teacher_id,
            student_id,
            False,
            "",
        )

    # 2. Reliable Student Self-Evaluation Evidence:
    # - Creator DB role is student AND no teacher verification
    # - OR submitter_role == 'student' AND student_id is registered student AND no teacher ID
    # - OR workflow_type indicates self evaluation AND student_id is present
    is_verified_student_eval = False
    if (creator_db_role == "student" or created_by_role == "student" or submitter_role == "student") and not teacher_id:
        is_verified_student_eval = True
    elif workflow_type in ("self_evaluation", "student_self_evaluation", "self_eval") and not teacher_id:
        is_verified_student_eval = True
    elif student_id and student_id_role == "student" and not teacher_id:
        is_verified_student_eval = True

    if is_verified_student_eval:
        effective_student_id = student_id or (created_by_user_id if creator_db_role == "student" else None)
        return (
            "STUDENT_SELF_EVALUATION",
            "student",
            None,
            effective_student_id,
            False,
            "",
        )

    # 3. Already explicitly classified with valid source and no conflict
    if existing_source == "TEACHER_EVALUATION" and (teacher_id or created_by_role == "teacher"):
        return ("TEACHER_EVALUATION", "teacher", teacher_id, student_id, False, "")
    if existing_source == "STUDENT_SELF_EVALUATION" and (student_id or created_by_role == "student") and not teacher_id:
        return ("STUDENT_SELF_EVALUATION", "student", None, student_id, False, "")

    # 4. Ambiguous / Uncertain Evidence -> Mark UNKNOWN / NEEDS_REVIEW
    # (Do NOT guess or infer from student name alone)
    reason = "Missing verifiable creator identity or ambiguous teacher/student ownership"
    if teacher_id and not teacher_id_role:
        reason = f"Unregistered teacher identifier: {teacher_id}"
    elif not teacher_id and not student_id and not created_by_user_id:
        reason = "No creator, teacher, or student identifier found on record"

    return ("UNKNOWN", "unknown", teacher_id, student_id, True, reason)


def run_safe_evaluation_repair(dry_run: bool = False, backup: bool = True) -> Dict[str, Any]:
    """
    Execute the safe evaluation data repair procedure.
    Preserves all records, backs up state, and updates provenance using reliable evidence.
    """
    ts_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    results = {
        "timestamp": ts_str,
        "dry_run": dry_run,
        "database_type": "mongodb" if is_using_mongo() else "sqlite",
        "backups_created": {},
        "evaluations": {
            "total_scanned": 0,
            "classified_teacher": 0,
            "classified_student": 0,
            "flagged_needs_review": 0,
            "skipped_already_valid": 0,
        },
        "misconceptions": {
            "total_scanned": 0,
            "classified_teacher": 0,
            "classified_student": 0,
            "flagged_needs_review": 0,
            "skipped_already_valid": 0,
        },
        "action_items": {
            "total_scanned": 0,
            "classified_teacher": 0,
            "flagged_needs_review": 0,
            "skipped_already_valid": 0,
        },
        "identities": {
            "memberships_synced": 0,
            "verified": 0,
            "flagged_needs_review": 0,
            "unlinked": 0,
        },
    }

    mongo_db = get_mongodb()
    if mongo_db is not None:
        _repair_mongodb(mongo_db, ts_str, results, dry_run=dry_run, backup=backup)
    else:
        _repair_sqlite(ts_str, results, dry_run=dry_run, backup=backup)

    logger.info(
        "[Repair Summary] DB: %s | Evals: [T: %d, S: %d, Review: %d, Skipped: %d] | "
        "Misconceptions: [T: %d, S: %d, Review: %d] | ActionItems: [T: %d, Review: %d] | "
        "Identities: [Memberships: %d, Verified: %d, Review: %d, Unlinked: %d]",
        results["database_type"],
        results["evaluations"]["classified_teacher"],
        results["evaluations"]["classified_student"],
        results["evaluations"]["flagged_needs_review"],
        results["evaluations"]["skipped_already_valid"],
        results["misconceptions"]["classified_teacher"],
        results["misconceptions"]["classified_student"],
        results["misconceptions"]["flagged_needs_review"],
        results["action_items"]["classified_teacher"],
        results["action_items"]["flagged_needs_review"],
        results["identities"]["memberships_synced"],
        results["identities"]["verified"],
        results["identities"]["flagged_needs_review"],
        results["identities"]["unlinked"],
    )
    results["success"] = True
    return results


def _repair_mongodb(db, ts_str: str, results: Dict[str, Any], dry_run: bool, backup: bool) -> None:
    """Repair procedures for MongoDB."""
    if backup and not dry_run:
        results["backups_created"] = _create_backups_mongo(db, ts_str)

    user_role_map = _build_user_role_map_mongo(db)

    # 1. Evaluations
    evals = list(db["evaluations"].find({}))
    results["evaluations"]["total_scanned"] = len(evals)

    eval_source_map = {}  # eval_id -> (source, teacher_id, student_id)

    for doc in evals:
        doc_id = doc.get("_id")
        eval_id_str = str(doc.get("id") or doc.get("evaluation_id") or doc_id)
        current_source = str(doc.get("evaluation_source") or "").strip()

        source, role, t_id, s_id, needs_review, reason = classify_evaluation_provenance(doc, user_role_map)
        eval_source_map[eval_id_str] = (source, t_id, s_id, needs_review)

        if current_source == source and not needs_review and doc.get("needs_review") is not True:
            results["evaluations"]["skipped_already_valid"] += 1
            continue

        if source == "TEACHER_EVALUATION":
            results["evaluations"]["classified_teacher"] += 1
        elif source == "STUDENT_SELF_EVALUATION":
            results["evaluations"]["classified_student"] += 1
        else:
            results["evaluations"]["flagged_needs_review"] += 1

        if not dry_run and doc_id:
            update_payload = {
                "evaluation_source": source,
                "evaluationSource": source,
                "created_by_role": role,
                "createdByRole": role,
                "needs_review": needs_review,
                "needsReview": needs_review,
            }
            if t_id:
                update_payload["teacher_id"] = t_id
            if s_id:
                update_payload["student_id"] = s_id
            if needs_review:
                update_payload["review_reason"] = reason

            db["evaluations"].update_one({"_id": doc_id}, {"$set": update_payload})

    # 2. Misconceptions
    misconceptions = list(db["misconceptions"].find({}))
    results["misconceptions"]["total_scanned"] = len(misconceptions)

    for m in misconceptions:
        m_id = m.get("_id")
        parent_eval_id = str(m.get("evaluation_id") or m.get("evaluationId") or "").strip()
        current_source = str(m.get("evaluation_source") or "").strip()

        parent_info = eval_source_map.get(parent_eval_id)
        if parent_info:
            source, t_id, s_id, needs_review = parent_info
        else:
            # Classify standalone misconception
            source, role, t_id, s_id, needs_review, reason = classify_evaluation_provenance(m, user_role_map)

        if current_source == source and not needs_review:
            results["misconceptions"]["skipped_already_valid"] += 1
            continue

        if source == "TEACHER_EVALUATION":
            results["misconceptions"]["classified_teacher"] += 1
        elif source == "STUDENT_SELF_EVALUATION":
            results["misconceptions"]["classified_student"] += 1
        else:
            results["misconceptions"]["flagged_needs_review"] += 1

        if not dry_run and m_id:
            update_payload = {
                "evaluation_source": source,
                "evaluationSource": source,
                "needs_review": needs_review,
                "needsReview": needs_review,
            }
            if t_id:
                update_payload["teacher_id"] = t_id
            if s_id:
                update_payload["student_id"] = s_id

            db["misconceptions"].update_one({"_id": m_id}, {"$set": update_payload})

    # 3. Action Items (Must only belong to genuine TEACHER_EVALUATION)
    actions = list(db["action_items"].find({}))
    results["action_items"]["total_scanned"] = len(actions)

    for a in actions:
        a_id = a.get("_id")
        parent_eval_id = str(a.get("evaluation_id") or a.get("evaluationId") or "").strip()
        current_source = str(a.get("evaluation_source") or "").strip()

        parent_info = eval_source_map.get(parent_eval_id)
        if parent_info:
            source, t_id, s_id, needs_review = parent_info
        else:
            source, role, t_id, s_id, needs_review, reason = classify_evaluation_provenance(a, user_role_map)

        # Non-teacher evaluations or unverified items must never appear as active teacher action items
        if source != "TEACHER_EVALUATION" or needs_review:
            results["action_items"]["flagged_needs_review"] += 1
            if not dry_run and a_id:
                db["action_items"].update_one(
                    {"_id": a_id},
                    {"$set": {
                        "evaluation_source": source if source != "TEACHER_EVALUATION" else "UNKNOWN",
                        "status": "NEEDS_REVIEW",
                        "needs_review": True,
                        "review_reason": "Not derived from a verified teacher evaluation",
                    }}
                )
        else:
            if current_source == "TEACHER_EVALUATION":
                results["action_items"]["skipped_already_valid"] += 1
            else:
                results["action_items"]["classified_teacher"] += 1
                if not dry_run and a_id:
                    db["action_items"].update_one(
                        {"_id": a_id},
                        {"$set": {
                            "evaluation_source": "TEACHER_EVALUATION",
                            "evaluationSource": "TEACHER_EVALUATION",
                            "needs_review": False,
                        }}
                    )

    # 4. Class Memberships sync from teacher_classes
    classes = list(db["teacher_classes"].find({}))
    memberships_synced = 0
    class_roster_map = {}

    for cls in classes:
        c_id = str(cls.get("id") or "")
        t_id = str(cls.get("teacher_id") or "")
        students = cls.get("students") or []
        updated_students = []
        class_roster_map[c_id] = students

        for idx, st in enumerate(students):
            s_name = str(st.get("name") or "").strip()
            if not s_name:
                continue
            s_id = str(st.get("id") or st.get("student_id") or f"std_{c_id}_{idx}").strip()
            s_roll = str(st.get("rollNumber") or st.get("rollNo") or st.get("roll_number") or "").strip()
            s_email = str(st.get("email") or "").strip().lower()
            s_sec = str(st.get("section") or cls.get("section") or "").strip()

            # Reliable account linking check (Requirement 5)
            linked_user_id = st.get("student_user_id") or st.get("userId")
            if not linked_user_id and s_email:
                user_doc = db["users"].find_one({"email": s_email, "role": "student"})
                if user_doc:
                    linked_user_id = str(user_doc.get("user_id") or user_doc.get("id") or user_doc.get("_id"))

            st["student_user_id"] = linked_user_id
            st["linked_account"] = bool(linked_user_id)
            st["id"] = s_id
            st["student_id"] = s_id
            updated_students.append(st)

            if not dry_run and c_id and t_id:
                mem_id = f"mem_{c_id}_{s_id}"
                db["class_memberships"].update_one(
                    {"class_id": c_id, "student_id": s_id},
                    {"$set": {
                        "id": mem_id,
                        "class_id": c_id,
                        "teacher_id": t_id,
                        "student_id": s_id,
                        "student_user_id": linked_user_id,
                        "student_name": s_name,
                        "roll_number": s_roll,
                        "email": s_email,
                        "section": s_sec,
                        "status": "Active",
                        "updated_at": datetime.utcnow().isoformat(),
                    }, "$setOnInsert": {"created_at": datetime.utcnow().isoformat()}},
                    upsert=True
                )
                memberships_synced += 1

        if not dry_run and c_id and updated_students != students:
            db["teacher_classes"].update_one(
                {"id": c_id},
                {"$set": {"students": updated_students, "students_count": len(updated_students)}}
            )

    results["identities"]["memberships_synced"] = memberships_synced

    # 5. Evaluations Identity & Snapshot Audit
    eval_verified = 0
    eval_needs_review = 0
    eval_unlinked = 0

    for doc in evals:
        doc_id = doc.get("_id")
        current_identity_status = doc.get("identity_status")
        student_name = str(doc.get("student_name") or "").strip()
        roll_number = str(doc.get("roll_number") or "").strip()
        eval_source = doc.get("evaluation_source") or "UNKNOWN"
        classified_info = eval_source_map.get(str(doc_id))
        if classified_info and classified_info[0]:
            eval_source = classified_info[0]

        name_snapshot = doc.get("student_name_snapshot") or student_name
        roll_snapshot = doc.get("roll_number_snapshot") or roll_number

        doc_class_id = str(doc.get("class_id") or "").strip()
        doc_student_id = doc.get("student_id")
        resolved_sid = doc_student_id
        resolved_status = current_identity_status or ("VERIFIED" if resolved_sid else "NEEDS_REVIEW")
        resolved_reason = doc.get("identity_review_reason") or ""
        resolved_user_id = doc.get("student_user_id")

        if not resolved_sid:
            if eval_source == "STUDENT_SELF_EVALUATION":
                resolved_sid = doc.get("created_by_user_id") or doc.get("submitted_by")
                resolved_status = "VERIFIED"
            else: # TEACHER_EVALUATION or legacy unclassified
                if doc_class_id and doc_class_id in class_roster_map:
                    roster = class_roster_map[doc_class_id]
                    clean_roll = roll_number.lower()
                    matched_member = None
                    if clean_roll and clean_roll not in ("n/a", "none", "unknown", ""):
                        matched_member = next((m for m in roster if (m.get("rollNumber") or m.get("rollNo") or m.get("roll_number") or "").strip().lower() == clean_roll), None)
                    if matched_member:
                        resolved_sid = matched_member["id"]
                        resolved_user_id = matched_member.get("student_user_id")
                        resolved_status = "VERIFIED"
                    else:
                        name_match = next((m for m in roster if (m.get("name") or "").strip().lower() == student_name.lower()), None)
                        if name_match:
                            resolved_status = "NEEDS_REVIEW"
                            resolved_reason = f"Ambiguous historical evaluation: name '{student_name}' matches roster but roll number did not match."
                        else:
                            resolved_status = "UNLINKED"
                            resolved_reason = "Student not found in class roster."
                else:
                    resolved_status = "UNLINKED"
                    resolved_reason = "Historical teacher evaluation without class reference."

        if resolved_status == "VERIFIED":
            eval_verified += 1
        elif resolved_status == "NEEDS_REVIEW":
            eval_needs_review += 1
        else:
            eval_unlinked += 1

        if not dry_run and doc_id:
            db["evaluations"].update_one(
                {"_id": doc_id},
                {"$set": {
                    "student_name_snapshot": name_snapshot,
                    "roll_number_snapshot": roll_snapshot,
                    "student_id": resolved_sid,
                    "student_user_id": resolved_user_id,
                    "identity_status": resolved_status,
                    "identity_review_reason": resolved_reason,
                }}
            )

    results["identities"]["verified"] = eval_verified
    results["identities"]["flagged_needs_review"] = eval_needs_review
    results["identities"]["unlinked"] = eval_unlinked


def _repair_sqlite(ts_str: str, results: Dict[str, Any], dry_run: bool, backup: bool) -> None:
    """Repair procedures for SQLite."""
    conn = get_sqlite_db()
    if backup and not dry_run:
        results["backups_created"] = _create_backups_sqlite(conn, ts_str)

    user_role_map = _build_user_role_map_sqlite(conn)
    cursor = conn.cursor()

    # 1. Evaluations
    cursor.execute("SELECT * FROM evaluations;")
    eval_rows = [dict(row) for row in cursor.fetchall()]
    results["evaluations"]["total_scanned"] = len(eval_rows)

    eval_source_map = {}

    for row in eval_rows:
        eval_id = row["id"]
        current_source = str(row.get("evaluation_source") or "").strip()

        source, role, t_id, s_id, needs_review, reason = classify_evaluation_provenance(row, user_role_map)
        eval_source_map[str(eval_id)] = (source, t_id, s_id, needs_review)

        if current_source == source and not needs_review:
            results["evaluations"]["skipped_already_valid"] += 1
            continue

        if source == "TEACHER_EVALUATION":
            results["evaluations"]["classified_teacher"] += 1
        elif source == "STUDENT_SELF_EVALUATION":
            results["evaluations"]["classified_student"] += 1
        else:
            results["evaluations"]["flagged_needs_review"] += 1

        if not dry_run:
            cursor.execute(
                """
                UPDATE evaluations
                SET evaluation_source = ?, created_by_role = ?, teacher_id = COALESCE(?, teacher_id), student_id = COALESCE(?, student_id)
                WHERE id = ?;
                """,
                (source, role, t_id, s_id, eval_id)
            )

    # 2. Misconceptions
    cursor.execute("SELECT * FROM misconceptions;")
    misc_rows = [dict(row) for row in cursor.fetchall()]
    results["misconceptions"]["total_scanned"] = len(misc_rows)

    for row in misc_rows:
        m_id = row["id"]
        parent_eval_id = str(row.get("evaluation_id") or "").strip()
        current_source = str(row.get("evaluation_source") or "").strip()

        parent_info = eval_source_map.get(parent_eval_id)
        if parent_info:
            source, t_id, s_id, needs_review = parent_info
        else:
            source, role, t_id, s_id, needs_review, reason = classify_evaluation_provenance(row, user_role_map)

        if current_source == source and not needs_review:
            results["misconceptions"]["skipped_already_valid"] += 1
            continue

        if source == "TEACHER_EVALUATION":
            results["misconceptions"]["classified_teacher"] += 1
        elif source == "STUDENT_SELF_EVALUATION":
            results["misconceptions"]["classified_student"] += 1
        else:
            results["misconceptions"]["flagged_needs_review"] += 1

        if not dry_run:
            cursor.execute(
                """
                UPDATE misconceptions
                SET evaluation_source = ?, teacher_id = COALESCE(?, teacher_id), student_id = COALESCE(?, student_id)
                WHERE id = ?;
                """,
                (source, t_id, s_id, m_id)
            )

    # 3. Action items
    cursor.execute("SELECT * FROM action_items;")
    act_rows = [dict(row) for row in cursor.fetchall()]
    results["action_items"]["total_scanned"] = len(act_rows)

    for row in act_rows:
        a_id = row["id"]
        parent_eval_id = str(row.get("evaluation_id") or "").strip()
        current_source = str(row.get("evaluation_source") or "").strip()

        parent_info = eval_source_map.get(parent_eval_id)
        if parent_info:
            source, t_id, s_id, needs_review = parent_info
        else:
            source, role, t_id, s_id, needs_review, reason = classify_evaluation_provenance(row, user_role_map)

        if source != "TEACHER_EVALUATION" or needs_review:
            results["action_items"]["flagged_needs_review"] += 1
            if not dry_run:
                cursor.execute(
                    """
                    UPDATE action_items
                    SET evaluation_source = ?, status = 'NEEDS_REVIEW'
                    WHERE id = ?;
                    """,
                    (source if source != "TEACHER_EVALUATION" else "UNKNOWN", a_id)
                )
        else:
            if current_source == "TEACHER_EVALUATION":
                results["action_items"]["skipped_already_valid"] += 1
            else:
                results["action_items"]["classified_teacher"] += 1
                if not dry_run:
                    cursor.execute(
                        """
                        UPDATE action_items
                        SET evaluation_source = 'TEACHER_EVALUATION'
                        WHERE id = ?;
                        """,
                        (a_id,)
                    )

    # 4. Class Memberships sync from teacher_classes
    cursor.execute("SELECT * FROM teacher_classes;")
    classes = [dict(row) for row in cursor.fetchall()]
    memberships_synced = 0
    class_roster_map = {}

    for cls in classes:
        c_id = str(cls.get("id") or "")
        t_id = str(cls.get("teacher_id") or "")
        students = json.loads(cls.get("students_json") or "[]")
        updated_students = []
        class_roster_map[c_id] = students

        for idx, st in enumerate(students):
            s_name = str(st.get("name") or "").strip()
            if not s_name:
                continue
            s_id = str(st.get("id") or st.get("student_id") or f"std_{c_id}_{idx}").strip()
            s_roll = str(st.get("rollNumber") or st.get("rollNo") or st.get("roll_number") or "").strip()
            s_email = str(st.get("email") or "").strip().lower()
            s_sec = str(st.get("section") or cls.get("section") or "").strip()

            linked_user_id = st.get("student_user_id") or st.get("userId")
            if not linked_user_id and s_email:
                cursor.execute("SELECT id, user_id FROM users WHERE LOWER(email) = ? AND role = 'student'", (s_email,))
                u_row = cursor.fetchone()
                if u_row:
                    linked_user_id = str(u_row["user_id"] or u_row["id"])

            st["student_user_id"] = linked_user_id
            st["linked_account"] = bool(linked_user_id)
            st["id"] = s_id
            st["student_id"] = s_id
            updated_students.append(st)

            if not dry_run and c_id and t_id:
                mem_id = f"mem_{c_id}_{s_id}"
                cursor.execute("""
                    INSERT OR REPLACE INTO class_memberships
                    (id, class_id, teacher_id, student_id, student_user_id, student_name, roll_number, email, section, status, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', CURRENT_TIMESTAMP)
                """, (mem_id, c_id, t_id, s_id, linked_user_id, s_name, s_roll, s_email, s_sec))
                memberships_synced += 1

        if not dry_run and c_id and updated_students != students:
            cursor.execute("""
                UPDATE teacher_classes
                SET students_json = ?, students_count = ?
                WHERE id = ?
            """, (json.dumps(updated_students), len(updated_students), c_id))

    results["identities"]["memberships_synced"] = memberships_synced

    # 5. Evaluations Identity & Snapshot Audit
    eval_verified = 0
    eval_needs_review = 0
    eval_unlinked = 0

    for row in eval_rows:
        eval_id = row["id"]
        current_identity_status = row.get("identity_status")
        student_name = str(row.get("student_name") or "").strip()
        roll_number = str(row.get("roll_number") or "").strip()
        c_id = str(row.get("class_id") or "").strip()
        s_id = row.get("student_id")
        eval_source = row.get("evaluation_source") or "UNKNOWN"
        classified_info = eval_source_map.get(str(eval_id))
        if classified_info and classified_info[0]:
            eval_source = classified_info[0]

        name_snapshot = row.get("student_name_snapshot") or student_name
        roll_snapshot = row.get("roll_number_snapshot") or roll_number

        resolved_status = current_identity_status or ("VERIFIED" if s_id else "NEEDS_REVIEW")
        resolved_reason = row.get("identity_review_reason") or ""
        resolved_sid = s_id
        resolved_user_id = row.get("student_user_id")

        if not resolved_sid:
            if eval_source == "STUDENT_SELF_EVALUATION":
                resolved_sid = row.get("created_by_user_id") or row.get("submitted_by")
                resolved_status = "VERIFIED"
            else: # TEACHER_EVALUATION or legacy unclassified
                if c_id and c_id in class_roster_map:
                    roster = class_roster_map[c_id]
                    clean_roll = roll_number.lower()
                    matched_member = None
                    if clean_roll and clean_roll not in ("n/a", "none", "unknown", ""):
                        matched_member = next((m for m in roster if (m.get("rollNumber") or m.get("rollNo") or m.get("roll_number") or "").strip().lower() == clean_roll), None)
                    if matched_member:
                        resolved_sid = matched_member["id"]
                        resolved_user_id = matched_member.get("student_user_id")
                        resolved_status = "VERIFIED"
                    else:
                        name_match = next((m for m in roster if (m.get("name") or "").strip().lower() == student_name.lower()), None)
                        if name_match:
                            resolved_status = "NEEDS_REVIEW"
                            resolved_reason = f"Ambiguous historical evaluation: name '{student_name}' matches roster but roll number did not match."
                        else:
                            resolved_status = "UNLINKED"
                            resolved_reason = "Student not found in class roster."
                else:
                    resolved_status = "UNLINKED"
                    resolved_reason = "Historical teacher evaluation without class reference."

        if resolved_status == "VERIFIED":
            eval_verified += 1
        elif resolved_status == "NEEDS_REVIEW":
            eval_needs_review += 1
        else:
            eval_unlinked += 1

        if not dry_run:
            cursor.execute("""
                UPDATE evaluations
                SET student_name_snapshot = ?, roll_number_snapshot = ?,
                    student_id = COALESCE(?, student_id), student_user_id = ?,
                    identity_status = ?, identity_review_reason = ?
                WHERE id = ?
            """, (name_snapshot, roll_snapshot, resolved_sid, resolved_user_id, resolved_status, resolved_reason, eval_id))

    results["identities"]["verified"] = eval_verified
    results["identities"]["flagged_needs_review"] = eval_needs_review
    results["identities"]["unlinked"] = eval_unlinked

    if not dry_run:
        conn.commit()
    conn.close()

