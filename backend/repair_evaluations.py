"""
LearnSphere AI - Evaluation Repair CLI Script

Usage:
    python backend/repair_evaluations.py [--dry-run] [--no-backup]

Options:
    --dry-run     Perform inspection and classification without writing to database.
    --no-backup   Skip creating timestamped snapshot backups before mutation.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure backend root is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.evaluation.repair import run_safe_evaluation_repair
from app.db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("repair_cli")


def main():
    parser = argparse.ArgumentParser(description="LearnSphere AI - Safe Evaluation Provenance Repair")
    parser.add_argument("--dry-run", action="store_true", help="Analyze without writing changes")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating snapshot backup tables/collections")
    args = parser.parse_args()

    logger.info("Initializing database connection...")
    init_db()

    logger.info("Starting safe evaluation repair procedure (dry_run=%s, backup=%s)...", args.dry_run, not args.no_backup)
    results = run_safe_evaluation_repair(dry_run=args.dry_run, backup=not args.no_backup)

    print("\n" + "=" * 60)
    print("           REPAIR & PROVENANCE MIGRATION REPORT")
    print("=" * 60)
    print(json.dumps(results, indent=2))
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
