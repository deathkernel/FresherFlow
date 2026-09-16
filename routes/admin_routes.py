import os

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.database import get_db
from routes.decorators import role_required
from services.public_jobs import fetch_all

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    return role_required("admin")(view)


def admin_credentials_valid(email, password):
    configured_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    configured_password = os.environ.get("ADMIN_PASSWORD", "")
    return bool(configured_email and configured_password and email == configured_email and password == configured_password)


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if admin_credentials_valid(email, password):
            session.clear()
            session["user_id"] = "admin"
            session["name"] = "Administrator"
            session["role"] = "admin"
            session.permanent = True
            return redirect(url_for("admin.dashboard"))
        flash("Invalid admin credentials.", "error")
    return render_template("admin/login.html")


@admin_bp.post("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("admin.login"))


@admin_bp.get("/")
@admin_required
def dashboard():
    db = get_db()
    stats = {
        "total": db.execute("SELECT COUNT(*) c FROM external_jobs").fetchone()["c"],
        "active": db.execute("SELECT COUNT(*) c FROM external_jobs WHERE active=1").fetchone()["c"],
        "inactive": db.execute("SELECT COUNT(*) c FROM external_jobs WHERE active=0").fetchone()["c"],
        "himalayas": db.execute("SELECT COUNT(*) c FROM external_jobs WHERE source='himalayas'").fetchone()["c"],
        "jobicy": db.execute("SELECT COUNT(*) c FROM external_jobs WHERE source='jobicy'").fetchone()["c"],
    }
    q = request.args.get("q", "").strip()
    source = request.args.get("source", "").strip().lower()
    status = request.args.get("status", "").strip().lower()
    clauses = ["1=1"]
    args = []
    if q:
        clauses.append("(title LIKE ? OR company LIKE ? OR skills LIKE ? OR location LIKE ?)")
        args.extend([f"%{q}%"] * 4)
    if source in {"himalayas", "jobicy"}:
        clauses.append("source=?")
        args.append(source)
    if status == "active":
        clauses.append("active=1")
    elif status == "inactive":
        clauses.append("active=0")
    jobs = db.execute(
        "SELECT * FROM external_jobs WHERE " + " AND ".join(clauses) + " ORDER BY COALESCE(posted_at, created_at) DESC LIMIT 100",
        args,
    ).fetchall()
    return render_template("admin/dashboard.html", stats=stats, jobs=jobs, q=q, source=source, status=status)


@admin_bp.get("/jobs/<int:job_id>")
@admin_required
def job_detail(job_id):
    job = get_db().execute("SELECT * FROM external_jobs WHERE id=?", (job_id,)).fetchone()
    if not job:
        return render_template("404.html"), 404
    return render_template("admin/job-detail.html", job=job)


@admin_bp.post("/jobs/<int:job_id>/toggle")
@admin_required
def toggle_job(job_id):
    db = get_db()
    job = db.execute("SELECT active FROM external_jobs WHERE id=?", (job_id,)).fetchone()
    if not job:
        return render_template("404.html"), 404
    new_status = 0 if job["active"] else 1
    db.execute("UPDATE external_jobs SET active=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (new_status, job_id))
    db.commit()
    flash("Job activated." if new_status else "Job hidden from students.", "success")
    return redirect(request.referrer or url_for("admin.dashboard"))


@admin_bp.post("/sync")
@admin_required
def sync_jobs():
    db = get_db()
    jobs, errors = fetch_all()
    inserted = 0
    updated = 0
    for job in jobs:
        before = db.execute("SELECT id FROM external_jobs WHERE source=? AND source_id=?", (job["source"], job["source_id"])).fetchone()
        db.execute(
            """INSERT INTO external_jobs
            (source,source_id,title,company,location,job_type,description,skills,salary,apply_url,posted_at,source_url,active,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(source,source_id) DO UPDATE SET
              title=excluded.title, company=excluded.company, location=excluded.location,
              job_type=excluded.job_type, description=excluded.description, skills=excluded.skills,
              salary=excluded.salary, apply_url=excluded.apply_url, posted_at=excluded.posted_at,
              source_url=excluded.source_url, updated_at=CURRENT_TIMESTAMP""",
            (job["source"], job["source_id"], job["title"], job["company"], job["location"], job["job_type"], job["description"], job["skills"], job["salary"], job["apply_url"], job["posted_at"], job["source_url"], 1),
        )
        updated += 1
        if before is None:
            inserted += 1
    db.commit()
    if errors:
        flash(f"Sync completed with {len(errors)} source error(s). {inserted} new jobs processed.", "error")
    else:
        flash(f"Sync complete: {inserted} new jobs, {updated - inserted} updated.", "success")
    return redirect(url_for("admin.dashboard"))
