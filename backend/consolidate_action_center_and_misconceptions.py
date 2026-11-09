"""
LearnSphere AI - Offline Migration & Consolidation Script
Consolidates Action Center items and Misconceptions on a per-student basis.
Creates automated database backups before applying changes.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Set up path so backend imports work
sys.path.insert(0, os.path.dirname(__file__))

from app.db import get_mongodb, get_sqlite_db
from app.evaluation.action_center import derive_action_items_from_evaluation, consolidate_action_items_by_student
from app.evaluation.misconceptions import group_misconceptions_by_student

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ConsolidationMigration")


def run_mongo_migration(mongo_db):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_action_col = f"action_items_backup_{timestamp}"
    backup_misc_col = f"misconceptions_backup_{timestamp}"

    logger.info("Starting MongoDB consolidation...")

    # 1. Backup action_items
    all_actions = list(mongo_db["action_items"].find({}))
    if all_actions:
        mongo_db[backup_action_col].insert_many(all_actions)
        logger.info(f"Backed up {len(all_actions)} action_items to '{backup_action_col}'.")
    else:
        logger.info("No action_items found to back up.")

    # 2. Backup misconceptions
    all_misc = list(mongo_db["misconceptions"].find({}))
    if all_misc:
        mongo_db[backup_misc_col].insert_many(all_misc)
        logger.info(f"Backed up {len(all_misc)} misconceptions to '{backup_misc_col}'.")
    else:
        logger.info("No misconceptions found to back up.")

    # 3. Consolidate Action Items
    evaluations = list(mongo_db["evaluations"].find({"evaluation_source": "TEACHER_EVALUATION"}))
    logger.info(f"Processing {len(evaluations)} completed teacher evaluations...")

    class_lookup = {}
    for tc in mongo_db["teacher_classes"].find({}):
        cid = str(tc.get("id") or "")
        cname = tc.get("name") or tc.get("grade_level") or cid
        if cid:
            class_lookup[cid] = cname

    consolidated_count = 0
    for ev in evaluations:
        eid = str(ev.get("id") or ev.get("_id") or ev.get("evaluation_id"))
        derived = derive_action_items_from_evaluation(ev, class_lookup, mongo_db=mongo_db)
        if derived:
            # Delete scattered per-question items for this evaluation
            mongo_db["action_items"].delete_many({
                "evaluation_id": eid,
                "evaluation_source": "TEACHER_EVALUATION",
            })
            for it in derived:
                mongo_db["action_items"].update_one({"id": it["id"]}, {"$set": it}, upsert=True)
                consolidated_count += 1

    logger.info(f"MongoDB consolidation complete: {consolidated_count} student-consolidated action items saved.")
    return True


def run_sqlite_migration():
    conn = get_sqlite_db()
    cursor = conn.cursor()
    logger.info("Starting SQLite consolidation...")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_table = f"action_items_backup_{timestamp}"

    try:
        cursor.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM action_items")
        cursor.execute("SELECT COUNT(*) FROM action_items")
        total_before = cursor.fetchone()[0]
        logger.info(f"Backed up {total_before} action_items to '{backup_table}'.")
    except Exception as e:
        logger.warning(f"SQLite backup notice: {e}")

    # Fetch classes
    cursor.execute("SELECT id, name, grade_level FROM teacher_classes")
    class_lookup = {str(r[0]): (r[1] or r[2] or str(r[0])) for r in cursor.fetchall()}

    cursor.execute("SELECT * FROM evaluations WHERE evaluation_source = 'TEACHER_EVALUATION'")
    eval_rows = [dict(r) for r in cursor.fetchall()]

    consolidated_count = 0
    for ev in eval_rows:
        eid = str(ev.get("id"))
        try:
            ev["questions"] = json.loads(ev.get("questions_json") or "[]")
        except Exception:
            ev["questions"] = []

        derived = derive_action_items_from_evaluation(ev, class_lookup, sqlite_conn=conn)
        if derived:
            cursor.execute("DELETE FROM action_items WHERE evaluation_id = ?", (eid,))
            for act in derived:
                cursor.execute(
                    """INSERT OR REPLACE INTO action_items 
                       (id, teacher_id, student_id, evaluation_id, student_name, roll_number,
                        academic_status, subject, topic, skill_or_topic, assessment_title, class_name,
                        question_num, total_marks, maximum_marks, marks_lost, loss_ratio,
                        affected_questions, marks_lost_per_question, exact_question,
                        student_answer, misconception, evidence, correct_understanding, issue,
                        priority, severity, priority_reason, source_link, action, recommended_action,
                        category, status, is_unreadable,
                        evaluation_source, created_by_user_id, created_by_role, class_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        act["id"], act.get("teacher_id"), act.get("student_id"), act.get("evaluation_id"),
                        act.get("student_name"), act.get("roll_number"), act.get("academic_status"),
                        act.get("subject"), act.get("topic"), act.get("skill_or_topic"),
                        act.get("assessment_title"), act.get("class_name"),
                        act.get("question_num"), act.get("total_marks"),
                        act.get("maximum_marks"), act.get("marks_lost"), act.get("loss_ratio", 0),
                        json.dumps(act.get("affected_questions", [])),
                        json.dumps(act.get("marks_lost_per_question", {})), act.get("exact_question"),
                        act.get("student_answer"), act.get("misconception"), act.get("evidence"),
                        act.get("correct_understanding"), act.get("issue"), act.get("priority"),
                        act.get("severity"), act.get("priority_reason"), act.get("source_link"),
                        act.get("action"), act.get("recommended_action"),
                        act.get("category"), act.get("status"), 1 if act.get("is_unreadable") else 0,
                        act.get("evaluation_source"), act.get("created_by_user_id"), act.get("created_by_role"),
                        act.get("class_id")
                    )
                )
                consolidated_count += 1

    conn.commit()
    conn.close()
    logger.info(f"SQLite consolidation complete: {consolidated_count} student-consolidated action items saved.")
    return True


if __name__ == "__main__":
    mongo_db = get_mongodb()
    if mongo_db is not None:
        run_mongo_migration(mongo_db)
    else:
        run_sqlite_migration()

