from flask import Blueprint, jsonify, render_template, request

from database.database import get_db

public_jobs_bp = Blueprint("public_jobs", __name__)


def _rows(query, args=()):
    return get_db().execute(query, args).fetchall()


@public_jobs_bp.get("/api/public-jobs")
def api_public_jobs():
    q = request.args.get("q", "").strip()
    source = request.args.get("source", "").strip().lower()
    limit = min(max(request.args.get("limit", 50, type=int), 1), 100)
    clauses = ["active=1"]
    args = []
    if q:
        clauses.append("(title LIKE ? OR company LIKE ? OR skills LIKE ? OR description LIKE ?)")
        args.extend([f"%{q}%"] * 4)
    if source:
        clauses.append("source=?")
        args.append(source)
    rows = _rows(
        "SELECT id, source, source_id, title, company, location, job_type, description, skills, salary, apply_url, posted_at, source_url "
        "FROM external_jobs WHERE " + " AND ".join(clauses) + " ORDER BY COALESCE(posted_at, created_at) DESC LIMIT ?",
        (*args, limit),
    )
    return jsonify({"count": len(rows), "jobs": [dict(row) for row in rows]})


@public_jobs_bp.get("/student/public-jobs")
def public_jobs_page():
    q = request.args.get("q", "").strip()
    source = request.args.get("source", "").strip().lower()
    clauses = ["active=1"]
    args = []
    if q:
        clauses.append("(title LIKE ? OR company LIKE ? OR skills LIKE ? OR description LIKE ?)")
        args.extend([f"%{q}%"] * 4)
    if source:
        clauses.append("source=?")
        args.append(source)
    jobs = _rows(
        "SELECT * FROM external_jobs WHERE " + " AND ".join(clauses) + " ORDER BY COALESCE(posted_at, created_at) DESC LIMIT 100",
        args,
    )
    return render_template("public_jobs.html", jobs=jobs, q=q, source=source)
