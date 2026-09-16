"""Remove demo-seeded vacancies while preserving external API jobs."""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "instance" / "fresherflow.db"


def main() -> int:
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return 1

    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    before = db.execute("SELECT COUNT(*) FROM vacancies").fetchone()[0]

    # demo_seed.py creates employers with this unique email prefix.
    cursor = db.execute(
        """DELETE FROM vacancies
           WHERE employer_id IN (
               SELECT id FROM users WHERE email LIKE 'demo.employer%@fresherflow.local'
           )"""
    )
    deleted = cursor.rowcount
    db.commit()

    after = db.execute("SELECT COUNT(*) FROM vacancies").fetchone()[0]
    external = db.execute("SELECT COUNT(*) FROM external_jobs").fetchone()[0]
    db.close()

    print(f"Demo vacancies before: {before}")
    print(f"Demo vacancies deleted: {deleted}")
    print(f"Vacancies remaining: {after}")
    print(f"External API jobs preserved: {external}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
