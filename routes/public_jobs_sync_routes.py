import os
import sqlite3
from hmac import compare_digest

from flask import Blueprint, jsonify, request

from database.database import get_db
from services.public_jobs import fetch_all

public_jobs_sync_bp = Blueprint("public_jobs_sync", __name__)


@public_jobs_sync_bp.post("/api/internal/public-jobs/sync")
def sync_public_jobs():
    expected = os.environ.get("PUBLIC_JOB_SYNC_TOKEN", "").strip()
    provided = request.headers.get("X-FresherFlow-Sync-Token", "")
    if not expected or not provided or not compare_digest(provided, expected):
        return jsonify({"error": "Unauthorized"}), 401

    jobs, errors = fetch_all()
    db = get_db()
    inserted = updated = 0
    for job in jobs:
        if not job["source"] or not job["source_id"] or not job["title"] or not job["apply_url"]:
            continue
        existing = db.execute(
            "SELECT id FROM external_jobs WHERE source=? AND source_id=?",
            (job["source"], job["source_id"]),
        ).fetchone()
        values = (
            job["title"], job["company"], job["location"], job["job_type"],
            job["description"], job["skills"], job["salary"], job["apply_url"],
            job["posted_at"], job["source_url"],
        )
        if existing:
            db.execute(
                """UPDATE external_jobs SET title=?, company=?, location=?, job_type=?,
                description=?, skills=?, salary=?, apply_url=?, posted_at=?, source_url=?,
                updated_at=CURRENT_TIMESTAMP, active=1 WHERE id=?""",
                (*values, existing["id"]),
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
    return jsonify({"inserted": inserted, "updated": updated, "source_errors": errors})
