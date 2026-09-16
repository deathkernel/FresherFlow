import os

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from admin_config import get_admin_credentials
from database.database import get_db
from routes.decorators import role_required
from services.public_jobs import fetch_all

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    return role_required("admin")(view)


def admin_credentials_valid(email, password):
    configured_email, configured_password = get_admin_credentials()
    return bool(email == configured_email and password == configured_password)


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
@admin_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("admin.login"))


@admin_bp.get("/")
@admin_required
def dashboard():
    db = get_db()
    stats = {
        "companies": db.execute("SELECT COUNT(*) c FROM employer_profiles").fetchone()["c"],
        "active_companies": db.execute("SELECT COUNT(*) c FROM employer_profiles WHERE account_status='active'").fetchone()["c"],
        "pending_jobs": db.execute("SELECT COUNT(*) c FROM vacancies WHERE moderation_status='pending'").fetchone()["c"],
        "approved_jobs": db.execute("SELECT COUNT(*) c FROM vacancies WHERE moderation_status='approved'").fetchone()["c"],
        "rejected_jobs": db.execute("SELECT COUNT(*) c FROM vacancies WHERE moderation_status='rejected'").fetchone()["c"],
        "api_jobs": db.execute("SELECT COUNT(*) c FROM external_jobs").fetchone()["c"],
        "applications": db.execute("SELECT COUNT(*) FROM applications").fetchone()[0] + db.execute("SELECT COUNT(*) FROM external_applications").fetchone()[0],
    }
    q = request.args.get("q", "").strip()
    moderation = request.args.get("moderation", "").strip().lower()
    account = request.args.get("account", "").strip().lower()
    job_clauses = ["1=1"]
    job_args = []
    if q:
        job_clauses.append("(v.title LIKE ? OR COALESCE(ep.organization_name, '') LIKE ? OR v.location LIKE ? OR COALESCE(u.email, '') LIKE ?)")
        term = f"%{q}%"
        job_args += [term, term, term, term]
    if moderation in {"pending", "approved", "rejected"}:
        job_clauses.append("v.moderation_status=?")
        job_args.append(moderation)
    jobs = db.execute("""
        SELECT v.*, COALESCE(ep.organization_name, 'Unknown company') AS organization_name,
               COALESCE(u.email, '—') AS employer_email,
               (SELECT COUNT(*) FROM applications a WHERE a.vacancy_id=v.id) AS application_count
        FROM vacancies v
        LEFT JOIN employer_profiles ep ON ep.user_id=v.employer_id
        LEFT JOIN users u ON u.id=v.employer_id
        WHERE """ + " AND ".join(job_clauses) + " ORDER BY v.id DESC LIMIT 100", job_args).fetchall()

    application_clauses = ["1=1"]
    application_args = []
    if q:
        application_clauses.append("(title LIKE ? OR organization_name LIKE ? OR student_name LIKE ? OR student_email LIKE ?)")
        term = f"%{q}%"
        application_args += [term, term, term, term]
    applications = db.execute("""
        SELECT * FROM (
            SELECT a.id, a.status, a.applied_at,
                   v.id AS vacancy_id, v.title, v.vacancy_type,
                   COALESCE(ep.organization_name, 'Unknown company') AS organization_name,
                   u.id AS student_id, u.name AS student_name, u.email AS student_email,
                   sp.college, sp.education, sp.skills, sp.resume_filename,
                   'Company Job' AS application_source
            FROM applications a
            JOIN vacancies v ON v.id=a.vacancy_id
            LEFT JOIN employer_profiles ep ON ep.user_id=v.employer_id
            JOIN users u ON u.id=a.student_id
            LEFT JOIN student_profiles sp ON sp.user_id=u.id

            UNION ALL

            SELECT ea.id, ea.status, ea.applied_at,
                   ej.id AS vacancy_id, ej.title, ej.job_type AS vacancy_type,
                   COALESCE(ej.company, 'External company') AS organization_name,
                   u.id AS student_id, u.name AS student_name, u.email AS student_email,
                   sp.college, sp.education, sp.skills, sp.resume_filename,
                   'Public/API Job' AS application_source
            FROM external_applications ea
            JOIN external_jobs ej ON ej.id=ea.external_job_id
            JOIN users u ON u.id=ea.student_id
            LEFT JOIN student_profiles sp ON sp.user_id=u.id
        )
        WHERE """ + " AND ".join(application_clauses) + " ORDER BY applied_at DESC, id DESC LIMIT 500", application_args).fetchall()

    company_clauses = ["1=1"]
    company_args = []
    if q:
        company_clauses.append("(ep.organization_name LIKE ? OR u.email LIKE ? OR ep.location LIKE ?)")
        company_args += [f"%{q}%"] * 3
    if account in {"active", "suspended"}:
        company_clauses.append("ep.account_status=?")
        company_args.append(account)
    companies = db.execute("SELECT ep.*, u.name contact_name, u.email FROM employer_profiles ep JOIN users u ON u.id=ep.user_id WHERE " + " AND ".join(company_clauses) + " ORDER BY ep.id DESC LIMIT 100", company_args).fetchall()
    return render_template("admin/dashboard.html", stats=stats, jobs=jobs, applications=applications, companies=companies, q=q, moderation=moderation, account=account)


@admin_bp.get("/companies/<int:user_id>")
@admin_required
def company_detail(user_id):
    db = get_db()
    company = db.execute("SELECT ep.*,u.name contact_name,u.email FROM employer_profiles ep JOIN users u ON u.id=ep.user_id WHERE ep.user_id=?", (user_id,)).fetchone()
    if not company:
        return render_template("404.html"), 404
    jobs = db.execute("SELECT * FROM vacancies WHERE employer_id=? ORDER BY id DESC", (user_id,)).fetchall()
    return render_template("admin/company-detail.html", company=company, jobs=jobs)


@admin_bp.post("/companies/<int:user_id>/status")
@admin_required
def company_status(user_id):
    status = request.form.get("status")
    if status not in {"active", "suspended"}:
        return redirect(url_for("admin.dashboard"))
    db = get_db()
    db.execute("UPDATE employer_profiles SET account_status=? WHERE user_id=?", (status, user_id))
    db.commit()
    flash(f"Company account marked {status}.", "success")
    return redirect(request.referrer or url_for("admin.dashboard"))


@admin_bp.post("/vacancies/<int:vacancy_id>/moderate")
@admin_required
def moderate_vacancy(vacancy_id):
    decision = request.form.get("decision")
    note = request.form.get("note", "").strip() or None
    if decision not in {"approved", "rejected"}:
        return redirect(url_for("admin.dashboard"))
    db = get_db()
    job = db.execute("SELECT id FROM vacancies WHERE id=?", (vacancy_id,)).fetchone()
    if not job:
        return render_template("404.html"), 404
    status = "active" if decision == "approved" else "closed"
    db.execute("UPDATE vacancies SET moderation_status=?, moderation_note=?, moderated_at=CURRENT_TIMESTAMP, status=? WHERE id=?", (decision, note, status, vacancy_id))
    db.commit()
    flash(f"Job {decision}.", "success")
    return redirect(request.referrer or url_for("admin.dashboard"))


@admin_bp.get("/jobs/<int:job_id>")
@admin_required
def job_detail(job_id):
    db = get_db()
    job = db.execute("SELECT v.*,ep.organization_name,u.email employer_email,(SELECT COUNT(*) FROM applications a WHERE a.vacancy_id=v.id) application_count FROM vacancies v JOIN employer_profiles ep ON ep.user_id=v.employer_id JOIN users u ON u.id=v.employer_id WHERE v.id=?", (job_id,)).fetchone()
    if not job:
        return render_template("404.html"), 404
    applications = db.execute("SELECT a.*,u.name,u.email,sp.education,sp.college,sp.skills,sp.resume_filename FROM applications a JOIN users u ON u.id=a.student_id LEFT JOIN student_profiles sp ON sp.user_id=u.id WHERE a.vacancy_id=? ORDER BY a.id DESC", (job_id,)).fetchall()
    return render_template("admin/job-detail.html", job=job, applications=applications, internal=True)


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
    inserted = updated = 0
    for job in jobs:
        before = db.execute("SELECT id FROM external_jobs WHERE source=? AND source_id=?", (job["source"], job["source_id"])).fetchone()
        db.execute("""INSERT INTO external_jobs (source,source_id,title,company,location,job_type,description,skills,salary,apply_url,posted_at,source_url,active,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(source,source_id) DO UPDATE SET title=excluded.title,company=excluded.company,location=excluded.location,job_type=excluded.job_type,description=excluded.description,skills=excluded.skills,salary=excluded.salary,apply_url=excluded.apply_url,posted_at=excluded.posted_at,source_url=excluded.source_url,updated_at=CURRENT_TIMESTAMP""", (job["source"],job["source_id"],job["title"],job["company"],job["location"],job["job_type"],job["description"],job["skills"],job["salary"],job["apply_url"],job["posted_at"],job["source_url"],1))
        updated += 1
        if before is None:
            inserted += 1
    db.commit()
    flash(f"Sync complete: {inserted} new jobs, {updated - inserted} updated." if not errors else f"Sync completed with {len(errors)} source error(s).", "success" if not errors else "error")
    return redirect(url_for("admin.dashboard"))
