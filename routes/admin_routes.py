import os
import sqlite3

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import get_admin_credentials
from database.database import get_db
from routes.decorators import role_required
from security import valid_website_url

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    return role_required("admin")(view)


def admin_credentials_valid(email, password):
    configured_email, configured_password_hash = get_admin_credentials()
    if not configured_email or not configured_password_hash:
        return False
    try:
        return email == configured_email and check_password_hash(
            configured_password_hash, password
        )
    except (ValueError, TypeError):
        return False


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        login_email = "admin@123" if email == "admin" else email
        if admin_credentials_valid(login_email, password):
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
        "jobs": db.execute("SELECT COUNT(*) c FROM vacancies").fetchone()["c"],
        "live_jobs": db.execute("SELECT COUNT(*) c FROM vacancies WHERE status='active' AND moderation_status='approved'").fetchone()["c"],
        "pending_jobs": db.execute("SELECT COUNT(*) c FROM vacancies WHERE moderation_status='pending'").fetchone()["c"],
        "applications": db.execute("SELECT COUNT(*) FROM applications").fetchone()[0],
    }
    return render_template("admin/dashboard.html", stats=stats)


@admin_bp.get("/jobs")
@admin_required
def jobs():
    db = get_db()
    q = request.args.get("q", "").strip()
    moderation = request.args.get("moderation", "").strip().lower()

    clauses = ["1=1"]
    args = []
    if q:
        clauses.append(
            "(v.title LIKE ? OR COALESCE(ep.organization_name, '') LIKE ? "
            "OR v.location LIKE ? OR COALESCE(u.email, '') LIKE ?)"
        )
        term = f"%{q}%"
        args += [term] * 4
    if moderation in {"pending", "approved", "rejected"}:
        clauses.append("v.moderation_status=?")
        args.append(moderation)

    rows = db.execute(
        """SELECT v.*, COALESCE(ep.organization_name, 'Unknown company') AS organization_name,
                  COALESCE(u.email, '—') AS employer_email,
                  (SELECT COUNT(*) FROM applications a WHERE a.vacancy_id=v.id) AS application_count
           FROM vacancies v
           LEFT JOIN employer_profiles ep ON ep.user_id=v.employer_id
           LEFT JOIN users u ON u.id=v.employer_id
           WHERE """ + " AND ".join(clauses) + """
           ORDER BY v.id DESC""",
        args,
    ).fetchall()

    counts = {
        "total": db.execute("SELECT COUNT(*) FROM vacancies").fetchone()[0],
        "pending": db.execute("SELECT COUNT(*) FROM vacancies WHERE moderation_status='pending'").fetchone()[0],
        "approved": db.execute("SELECT COUNT(*) FROM vacancies WHERE moderation_status='approved'").fetchone()[0],
        "rejected": db.execute("SELECT COUNT(*) FROM vacancies WHERE moderation_status='rejected'").fetchone()[0],
    }
    return render_template("admin/jobs.html", jobs=rows, counts=counts, q=q, moderation=moderation)


@admin_bp.get("/applications")
@admin_required
def applications():
    db = get_db()
    q = request.args.get("q", "").strip()
    clauses = ["1=1"]
    args = []
    if q:
        clauses.append(
            "(v.title LIKE ? OR ep.organization_name LIKE ? OR u.name LIKE ? OR u.email LIKE ?)"
        )
        term = f"%{q}%"
        args += [term] * 4

    rows = db.execute(
        """SELECT a.id, a.status, a.applied_at, v.id AS vacancy_id, v.title,
                  v.vacancy_type, COALESCE(ep.organization_name, 'Unknown company') AS organization_name,
                  u.id AS student_id, u.name AS student_name, u.email AS student_email,
                  sp.college, sp.education, sp.skills, sp.resume_filename,
                  'Company Job' AS application_source
           FROM applications a
           JOIN vacancies v ON v.id=a.vacancy_id
           LEFT JOIN employer_profiles ep ON ep.user_id=v.employer_id
           JOIN users u ON u.id=a.student_id
           LEFT JOIN student_profiles sp ON sp.user_id=u.id
           WHERE """ + " AND ".join(clauses) + """
           ORDER BY a.applied_at DESC, a.id DESC""",
        args,
    ).fetchall()
    total = db.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    return render_template("admin/applications.html", applications=rows, total=total, q=q)


@admin_bp.get("/companies")
@admin_required
def companies():
    db = get_db()
    q = request.args.get("q", "").strip()
    account = request.args.get("account", "").strip().lower()
    clauses = ["1=1"]
    args = []
    if q:
        clauses.append(
            "(ep.organization_name LIKE ? OR u.email LIKE ? OR ep.location LIKE ?)"
        )
        term = f"%{q}%"
        args += [term] * 3
    if account in {"active", "suspended"}:
        clauses.append("ep.account_status=?")
        args.append(account)

    rows = db.execute(
        """SELECT ep.*, u.name contact_name, u.email
           FROM employer_profiles ep
           JOIN users u ON u.id=ep.user_id
           WHERE """ + " AND ".join(clauses) + """
           ORDER BY ep.id DESC""",
        args,
    ).fetchall()
    counts = {
        "total": db.execute("SELECT COUNT(*) FROM employer_profiles").fetchone()[0],
        "active": db.execute("SELECT COUNT(*) FROM employer_profiles WHERE account_status='active'").fetchone()[0],
        "suspended": db.execute("SELECT COUNT(*) FROM employer_profiles WHERE account_status='suspended'").fetchone()[0],
    }
    return render_template("admin/companies.html", companies=rows, counts=counts, q=q, account=account)


@admin_bp.get("/companies/add")
@admin_required
def add_company_page():
    return render_template("admin/add-employer.html")

@admin_bp.get("/students/<int:student_id>")
@admin_required
def student_profile(student_id):
    db = get_db()
    user = db.execute("SELECT id, name, email, role FROM users WHERE id=? AND role='student'", (student_id,)).fetchone()
    if not user:
        return render_template("404.html"), 404
    profile = db.execute("SELECT * FROM student_profiles WHERE user_id=?", (student_id,)).fetchone()
    if not profile:
        profile = {"profile_strength": 0, "phone": None, "education": None, "college": None, "graduation_year": None, "skills": None, "certifications": None, "preferred_job_type": None, "preferred_location": None, "resume_filename": None}
    applications = db.execute(
        """SELECT a.id, a.status, a.applied_at, v.id AS vacancy_id, v.title, v.vacancy_type,
                  COALESCE(ep.organization_name, 'Unknown company') AS organization_name, 'Company Job' AS application_source
           FROM applications a JOIN vacancies v ON v.id=a.vacancy_id LEFT JOIN employer_profiles ep ON ep.user_id=v.employer_id
           WHERE a.student_id=? ORDER BY a.applied_at DESC, a.id DESC""", (student_id,)
    ).fetchall()
    return render_template("admin/student-profile.html", user=user, profile=profile, applications=applications)


@admin_bp.post("/companies/add")
@admin_required
def add_company():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    organization = request.form.get("organization_name", "").strip() or name
    organization_type = request.form.get("organization_type", "").strip()
    location = request.form.get("location", "").strip()
    website = request.form.get("website", "").strip()
    description = request.form.get("description", "").strip()

    if not name or not email or not organization or len(password) < 12:
        flash("Name, email, organization and a password of at least 12 characters are required.", "error")
        return redirect(url_for("admin.add_company_page"))

    if not valid_website_url(website):
        flash("Website must be a valid http:// or https:// URL.", "error")
        return redirect(url_for("admin.add_company_page"))

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
            (name, email, generate_password_hash(password), "employer"),
        )
        db.execute(
            """INSERT INTO employer_profiles
            (company_id,user_id,organization_name,organization_type,website,location,description,account_status,verification_status,verified_at)
            VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
            (f"FF-CMP-{cur.lastrowid:06d}", cur.lastrowid, organization, organization_type, website, location, description, "active", "verified"),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        current_app.logger.exception("Admin employer creation failed")
        flash("Could not add employer. The email may already be registered.", "error")
        return redirect(url_for("admin.add_company_page"))

    flash(f"Employer account for {organization} added successfully.", "success")
    return redirect(url_for("admin.companies"))


@admin_bp.post("/companies/<int:user_id>/delete")
@admin_required
def delete_company(user_id):
    db = get_db()
    company = db.execute(
        "SELECT u.id, u.role, ep.organization_name FROM users u JOIN employer_profiles ep ON ep.user_id=u.id WHERE u.id=? AND u.role='employer'",
        (user_id,),
    ).fetchone()
    if not company:
        flash("Employer account not found.", "error")
        return redirect(url_for("admin.companies"))

    db.execute("DELETE FROM users WHERE id=? AND role='employer'", (user_id,))
    db.commit()
    flash(f"Employer account for {company['organization_name']} was removed.", "success")
    return redirect(url_for("admin.companies"))


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
        return redirect(url_for("admin.companies"))
    db = get_db()
    company = db.execute(
        "SELECT organization_name FROM employer_profiles ep JOIN users u ON u.id=ep.user_id WHERE ep.user_id=? AND u.role='employer'",
        (user_id,),
    ).fetchone()
    if not company:
        flash("Employer account not found.", "error")
        return redirect(url_for("admin.companies"))
    db.execute("UPDATE employer_profiles SET account_status=? WHERE user_id=?", (status, user_id))
    db.commit()
    flash(f"Company account marked {status}.", "success")
    return redirect(url_for("admin.companies"))


@admin_bp.post("/vacancies/<int:vacancy_id>/moderate")
@admin_required
def moderate_vacancy(vacancy_id):
    decision = request.form.get("decision")
    note = request.form.get("note", "").strip() or None
    if decision not in {"approved", "rejected"}:
        return redirect(url_for("admin.jobs"))
    db = get_db()
    job = db.execute("SELECT id, deadline FROM vacancies WHERE id=?", (vacancy_id,)).fetchone()
    if not job:
        return render_template("404.html"), 404
    if decision == "approved" and job["deadline"]:
        try:
            from datetime import date
            if date.fromisoformat(job["deadline"]) < date.today():
                flash("Expired vacancies cannot be approved.", "error")
                return redirect(url_for("admin.jobs"))
        except ValueError:
            flash("Vacancy has an invalid deadline and cannot be approved.", "error")
            return redirect(url_for("admin.jobs"))
    status = "active" if decision == "approved" else "closed"
    db.execute("UPDATE vacancies SET moderation_status=?, moderation_note=?, moderated_at=CURRENT_TIMESTAMP, status=? WHERE id=?", (decision, note, status, vacancy_id))
    db.commit()
    flash(f"Job {decision}.", "success")
    return redirect(url_for("admin.jobs"))


@admin_bp.post("/vacancies/bulk-moderate")
@admin_required
def bulk_moderate_vacancies():
    decision = request.form.get("decision", "").strip().lower()
    note = request.form.get("note", "").strip() or None
    selected_ids = []
    for raw_id in request.form.getlist("vacancy_ids"):
        try:
            vacancy_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if vacancy_id > 0 and vacancy_id not in selected_ids:
            selected_ids.append(vacancy_id)

    if decision not in {"approved", "rejected"}:
        flash("Choose Approve or Reject for the selected jobs.", "error")
        return redirect(url_for("admin.jobs"))

    if not selected_ids:
        flash("Select at least one job first.", "error")
        return redirect(url_for("admin.jobs"))

    db = get_db()
    placeholders = ",".join("?" for _ in selected_ids)
    jobs = db.execute(
        f"SELECT id, deadline, moderation_status FROM vacancies WHERE id IN ({placeholders})",
        selected_ids,
    ).fetchall()

    if len(jobs) != len(selected_ids):
        flash("One or more selected jobs could not be found.", "error")
        return redirect(url_for("admin.jobs"))

    if decision == "approved":
        expired = []
        for job in jobs:
            if job["deadline"]:
                try:
                    from datetime import date
                    if date.fromisoformat(job["deadline"]) < date.today():
                        expired.append(job["id"])
                except ValueError:
                    expired.append(job["id"])
        if expired:
            flash(
                f"{len(expired)} selected job(s) have an expired or invalid deadline. Nothing was approved.",
                "error",
            )
            return redirect(url_for("admin.jobs"))

    status = "active" if decision == "approved" else "closed"
    db.execute(
        f"""UPDATE vacancies
            SET moderation_status=?, moderation_note=?, moderated_at=CURRENT_TIMESTAMP, status=?
            WHERE id IN ({placeholders})""",
        [decision, note, status, *selected_ids],
    )
    db.commit()
    flash(f"{len(selected_ids)} job(s) {decision} successfully.", "success")
    return redirect(url_for("admin.jobs"))




@admin_bp.get("/students/<int:student_id>/resume")
@admin_required
def student_resume(student_id):
    db = get_db()
    profile = db.execute(
        "SELECT resume_filename FROM student_profiles WHERE user_id=?", (student_id,)
    ).fetchone()
    if not profile or not profile["resume_filename"]:
        return render_template("404.html"), 404
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        profile["resume_filename"],
        as_attachment=False,
    )

@admin_bp.get("/jobs/<int:job_id>")
@admin_required
def job_detail(job_id):
    db = get_db()
    job = db.execute("SELECT v.*,ep.organization_name,u.email employer_email,(SELECT COUNT(*) FROM applications a WHERE a.vacancy_id=v.id) application_count FROM vacancies v JOIN employer_profiles ep ON ep.user_id=v.employer_id JOIN users u ON u.id=v.employer_id WHERE v.id=?", (job_id,)).fetchone()
    if not job:
        return render_template("404.html"), 404
    applications = db.execute("SELECT a.*,u.name,u.email,sp.education,sp.college,sp.skills,sp.resume_filename FROM applications a JOIN users u ON u.id=a.student_id LEFT JOIN student_profiles sp ON sp.user_id=u.id WHERE a.vacancy_id=? ORDER BY a.id DESC", (job_id,)).fetchall()
    return render_template("admin/job-detail.html", job=job, applications=applications, internal=True)
