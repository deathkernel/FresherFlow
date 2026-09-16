"""Sync public job APIs into FresherFlow's external_jobs table."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import Config  # noqa: E402
from database.database import init_db  # noqa: E402
from services.public_jobs import fetch_all  # noqa: E402


def main() -> int:
    init_db(Config.DATABASE)
    jobs, errors = fetch_all()
    db = sqlite3.connect(Config.DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    inserted = updated = 0
    for job in jobs:
        if (
            not job["source"]
            or not job["source_id"]
            or not job["title"]
            or not job["apply_url"]
        ):
            continue
        existing = db.execute(
            "SELECT id FROM external_jobs WHERE source=? AND source_id=?",
            (job["source"], job["source_id"]),
        ).fetchone()
        values = (
            job["title"],
            job["company"],
            job["location"],
            job["job_type"],
            job["description"],
            job["skills"],
            job["salary"],
            job["apply_url"],
            job["posted_at"],
            job["source_url"],
        )
        if existing:
            db.execute(
                """UPDATE external_jobs SET title=?, company=?, location=?, job_type=?,
                description=?, skills=?, salary=?, apply_url=?, posted_at=?, source_url=?,
                updated_at=CURRENT_TIMESTAMP, active=1 WHERE id=?""",
                (*values, existing[0]),
            )
            updated += 1
        else:
            db.execute(
                """INSERT INTO external_jobs
                (source, source_id, title, company, location, job_type, description,
                 skills, salary, apply_url, posted_at, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (job["source"], job["source_id"], *values),
            )
            inserted += 1
    db.commit()
    db.close()
    print(
        f"FresherFlow public job sync: {inserted} inserted, {updated} updated, {len(errors)} source errors"
    )
    for source, error in errors.items():
        print(f"::warning title={source}::{error}")
    # A partial sync is useful, but CI should fail if every source is unavailable.
    return 1 if errors and not jobs else 0


if __name__ == "__main__":
    raise SystemExit(main())
