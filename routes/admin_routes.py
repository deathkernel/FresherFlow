import csv
import hashlib
import io
import os
import sqlite3
from datetime import date
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    Response,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from config import get_admin_credentials
from database.database import get_db
from routes.decorators import role_required
from security import (
    client_login_ip_key,
    client_login_key,
    clear_login_failures,
    login_is_locked,
    record_login_failure,
    valid_website_url,
)


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    return role_required("admin")(view)



def audit(action, target_type=None, target_id=None, details=None):
    db = get_db()
    db.execute(
        """INSERT INTO audit_log
           (actor_type, actor_id, action, target_type, target_id, details, ip_address)
           VALUES(?,?,?,?,?,?,?)""",
        (
            "admin",
            str(session.get("user_id", "admin")),
            action,
            target_type,
            str(target_id) if target_id is not None else None,
            details,
            request.remote_addr,
        ),
    )

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
        login_email = email
        db = get_db()
        login_key = client_login_key(request, "admin", login_email)
        ip_key = client_login_ip_key(request, "admin")
        if login_is_locked(db, login_key) or login_is_locked(db, ip_key):
            flash("Too many failed attempts. Please try again in a few minutes.", "error")
            return render_template("admin/login.html")
        if admin_credentials_valid(login_email, password):
            clear_login_failures(db, login_key)
            session.clear()
            session["user_id"] = "admin"
            session["name"] = "Administrator"
            session["role"] = "admin"
            _, configured_hash = get_admin_credentials()
            session["auth_version"] = hashlib.sha256(
                configured_hash.encode("utf-8")
            ).hexdigest()
            session.permanent = True
            return redirect(url_for("admin.dashboard"))
        record_login_failure(db, login_key)
        record_login_failure(db, ip_key, max_failures=20)
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
        "companies": db.execute(
            "SELECT COUNT(*) c FROM employer_profiles"
        ).fetchone()["c"],
        "active_companies": db.execute(
            "SELECT COUNT(*) c FROM employer_profiles "
            "WHERE account_status='active'"
        ).fetchone()["c"],
        "jobs": db.execute(
            "SELECT COUNT(*) c FROM vacancies"
        ).fetchone()["c"],
        "live_jobs": db.execute(
            "SELECT COUNT(*) c FROM vacancies v "
            "JOIN employer_profiles ep ON ep.user_id=v.employer_id "
            "WHERE v.status='active' AND v.moderation_status='approved' "
            "AND ep.account_status='active' AND ep.verification_status='verified' "
            "AND (v.deadline IS NULL OR trim(v.deadline)='' "
            "OR v.deadline>=date('now','localtime'))"
        ).fetchone()["c"],
        "pending_jobs": db.execute(
            "SELECT COUNT(*) c FROM vacancies "
            "WHERE moderation_status='pending'"
        ).fetchone()["c"],
        "applications": db.execute(
            "SELECT COUNT(*) FROM applications"
        ).fetchone()[0],
    }
    return render_template("admin/dashboard.html", stats=stats)


ADMIN_REPORTS = {
    "applications": {
        "title": "Applications",
        "date_column": "a.applied_at",
        "columns": [
            ("Application ID", "application_id"),
            ("Student", "student_name"),
            ("Student email", "student_email"),
            ("College", "college"),
            ("Vacancy", "vacancy_title"),
            ("Vacancy type", "vacancy_type"),
            ("Company", "company"),
            ("Status", "status"),
            ("Applied at", "applied_at"),
        ],
        "sql": """SELECT a.id AS application_id, u.name AS student_name,
                         u.email AS student_email, COALESCE(sp.college, '') AS college,
                         v.title AS vacancy_title, v.vacancy_type,
                         COALESCE(ep.organization_name, 'Unknown company') AS company,
                         a.status, a.applied_at
                  FROM applications a
                  JOIN vacancies v ON v.id=a.vacancy_id
                  JOIN users u ON u.id=a.student_id
                  LEFT JOIN student_profiles sp ON sp.user_id=u.id
                  LEFT JOIN employer_profiles ep ON ep.user_id=v.employer_id""",
    },
    "vacancies": {
        "title": "Vacancies",
        "date_column": "v.created_at",
        "columns": [
            ("Vacancy ID", "vacancy_id"),
            ("Vacancy code", "vacancy_code"),
            ("Title", "title"),
            ("Type", "vacancy_type"),
            ("Company", "company"),
            ("Location", "location"),
            ("Publication status", "status"),
            ("Moderation status", "moderation_status"),
            ("Created at", "created_at"),
            ("Deadline", "deadline"),
        ],
        "sql": """SELECT v.id AS vacancy_id, v.vacancy_code, v.title, v.vacancy_type,
                         COALESCE(ep.organization_name, 'Unknown company') AS company,
                         v.location, v.status, v.moderation_status, v.created_at, v.deadline
                  FROM vacancies v
                  LEFT JOIN employer_profiles ep ON ep.user_id=v.employer_id""",
    },
    "college-verifications": {
        "title": "College verifications",
        "date_column": "r.submitted_at",
        "columns": [
            ("Request ID", "request_id"),
            ("Student", "student_name"),
            ("Student email", "student_email"),
            ("College", "college"),
            ("Enrollment number", "enrollment_number"),
            ("Graduation year", "graduation_year"),
            ("College decision", "college_status"),
            ("Admin decision", "admin_status"),
            ("Submitted at", "submitted_at"),
            ("College reviewed at", "reviewed_at"),
            ("Admin reviewed at", "admin_reviewed_at"),
            ("Valid until", "expires_at"),
        ],
        "sql": """SELECT r.id AS request_id, u.name AS student_name, u.email AS student_email,
                         c.name AS college, r.enrollment_number, r.graduation_year,
                         r.status AS college_status, r.admin_status, r.submitted_at,
                         r.reviewed_at, r.admin_reviewed_at, r.expires_at
                  FROM student_verification_requests r
                  JOIN users u ON u.id=r.student_id
                  JOIN colleges c ON c.id=r.college_id""",
    },
}


def _admin_report_filters():
    report_type = request.args.get("report", "applications").strip()
    if report_type not in ADMIN_REPORTS:
        from flask import abort
        abort(400, description="Choose a valid report type.")

    parsed_dates = {}
    for field in ("from_date", "to_date"):
        raw_value = request.args.get(field, "").strip()
        if not raw_value:
            parsed_dates[field] = ""
            continue
        try:
            parsed_dates[field] = date.fromisoformat(raw_value).isoformat()
        except ValueError:
            from flask import abort
            abort(400, description="Report dates must be valid YYYY-MM-DD dates.")

    if parsed_dates["from_date"] and parsed_dates["to_date"]:
        if parsed_dates["from_date"] > parsed_dates["to_date"]:
            from flask import abort
            abort(400, description="The start date must not be after the end date.")
    return report_type, parsed_dates["from_date"], parsed_dates["to_date"]


def _admin_report_rows(db, report_type, from_date="", to_date=""):
    report = ADMIN_REPORTS[report_type]
    clauses = []
    params = []
    if from_date:
        clauses.append(f"date({report['date_column']}) >= date(?)")
        params.append(from_date)
    if to_date:
        clauses.append(f"date({report['date_column']}) <= date(?)")
        params.append(to_date)
    sql = report["sql"]
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += f" ORDER BY {report['date_column']} DESC"
    rows = db.execute(sql, params).fetchall()
    return report, rows


def _csv_cell(value):
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return value
    text = str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


@admin_bp.get("/reports")
@admin_required
def reports():
    report_type, from_date, to_date = _admin_report_filters()
    report, rows = _admin_report_rows(get_db(), report_type, from_date, to_date)
    headers = [label for label, _key in report["columns"]]
    preview_rows = rows[:25]
    return render_template(
        "admin/reports.html",
        report_type=report_type,
        report_title=report["title"],
        report_options=[
            (key, value["title"]) for key, value in ADMIN_REPORTS.items()
        ],
        headers=headers,
        columns=[key for _label, key in report["columns"]],
        rows=preview_rows,
        row_count=len(rows),
        from_date=from_date,
        to_date=to_date,
    )


@admin_bp.get("/reports/export.csv")
@admin_required
def export_report_csv():
    report_type, from_date, to_date = _admin_report_filters()
    report, rows = _admin_report_rows(get_db(), report_type, from_date, to_date)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([label for label, _key in report["columns"]])
    for row in rows:
        writer.writerow([_csv_cell(row[key]) for _label, key in report["columns"]])

    audit(
        "export_admin_report",
        "report",
        report_type,
        f"from={from_date or 'all'};to={to_date or 'all'};rows={len(rows)}",
    )
    get_db().commit()
    response = Response(output.getvalue(), mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = (
        f'attachment; filename="fresherflow_{report_type}.csv"'
    )
    response.headers["Cache-Control"] = "private, no-store"
    return response


@admin_bp.get("/jobs")
@admin_required
def jobs():
    db = get_db()
    q = request.args.get("q", "").strip()
    moderation = request.args.get("moderation", "").strip().lower()
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 20
    offset = (page - 1) * per_page

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

    total_matching = db.execute(
        """SELECT COUNT(*)
           FROM vacancies v
           LEFT JOIN employer_profiles ep ON ep.user_id=v.employer_id
           LEFT JOIN users u ON u.id=v.employer_id
           WHERE """ + " AND ".join(clauses),
        args,
    ).fetchone()[0]
    total_pages = max(1, (total_matching + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page

    rows = db.execute(
        """SELECT v.*, COALESCE(ep.organization_name, 'Unknown company') AS organization_name,
                  COALESCE(u.email, '—') AS employer_email,
                  (SELECT COUNT(*) FROM applications a WHERE a.vacancy_id=v.id) AS application_count
           FROM vacancies v
           LEFT JOIN employer_profiles ep ON ep.user_id=v.employer_id
           LEFT JOIN users u ON u.id=v.employer_id
           WHERE """ + " AND ".join(clauses) + """
           ORDER BY v.id DESC
           LIMIT ? OFFSET ?""",
        [*args, per_page, offset],
    ).fetchall()

    counts = {
        "total": db.execute("SELECT COUNT(*) FROM vacancies").fetchone()[0],
        "pending": db.execute("SELECT COUNT(*) FROM vacancies WHERE moderation_status='pending'").fetchone()[0],
        "approved": db.execute("SELECT COUNT(*) FROM vacancies WHERE moderation_status='approved'").fetchone()[0],
        "rejected": db.execute("SELECT COUNT(*) FROM vacancies WHERE moderation_status='rejected'").fetchone()[0],
    }
    return render_template(
        "admin/jobs.html",
        jobs=rows,
        counts=counts,
        q=q,
        moderation=moderation,
        page=page,
        per_page=per_page,
        total_matching=total_matching,
        total_pages=total_pages,
    )


@admin_bp.get("/applications")
@admin_required
def applications():
    db = get_db()
    q = request.args.get("q", "").strip()
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 20
    offset = (page - 1) * per_page
    clauses = ["1=1"]
    args = []
    if q:
        clauses.append(
            "(v.title LIKE ? OR ep.organization_name LIKE ? OR u.name LIKE ? OR u.email LIKE ?)"
        )
        term = f"%{q}%"
        args += [term] * 4

    total_matching = db.execute(
        """SELECT COUNT(*)
           FROM applications a
           JOIN vacancies v ON v.id=a.vacancy_id
           LEFT JOIN employer_profiles ep ON ep.user_id=v.employer_id
           JOIN users u ON u.id=a.student_id
           WHERE """ + " AND ".join(clauses),
        args,
    ).fetchone()[0]
    total_pages = max(1, (total_matching + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page

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
           ORDER BY a.applied_at DESC, a.id DESC
           LIMIT ? OFFSET ?""",
        [*args, per_page, offset],
    ).fetchall()
    total = db.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    return render_template(
        "admin/applications.html",
        applications=rows,
        total=total,
        total_matching=total_matching,
        total_pages=total_pages,
        q=q,
        page=page,
        per_page=per_page,
    )


@admin_bp.get("/companies")
@admin_required
def companies():
    db = get_db()
    q = request.args.get("q", "").strip()
    account = request.args.get("account", "").strip().lower()
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 20
    offset = (page - 1) * per_page
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

    total_matching = db.execute(
        """SELECT COUNT(*)
           FROM employer_profiles ep
           JOIN users u ON u.id=ep.user_id
           WHERE """ + " AND ".join(clauses),
        args,
    ).fetchone()[0]
    total_pages = max(1, (total_matching + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page

    rows = db.execute(
        """SELECT ep.*, u.name contact_name, u.email
           FROM employer_profiles ep
           JOIN users u ON u.id=ep.user_id
           WHERE """ + " AND ".join(clauses) + """
           ORDER BY ep.id DESC
           LIMIT ? OFFSET ?""",
        [*args, per_page, offset],
    ).fetchall()
    counts = {
        "total": db.execute("SELECT COUNT(*) FROM employer_profiles").fetchone()[0],
        "active": db.execute("SELECT COUNT(*) FROM employer_profiles WHERE account_status='active'").fetchone()[0],
        "suspended": db.execute("SELECT COUNT(*) FROM employer_profiles WHERE account_status='suspended'").fetchone()[0],
    }
    return render_template(
        "admin/companies.html",
        companies=rows,
        counts=counts,
        q=q,
        account=account,
        page=page,
        per_page=per_page,
        total_matching=total_matching,
        total_pages=total_pages,
    )


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
        audit("create_employer", "employer", cur.lastrowid, organization)
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
    audit("delete_employer", "employer", user_id, company["organization_name"])
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
    audit("change_employer_status", "employer", user_id, status)
    db.commit()
    flash(f"Company account marked {status}.", "success")
    return redirect(url_for("admin.companies"))


@admin_bp.post("/companies/<int:user_id>/verification")
@admin_required
def company_verification(user_id):
    decision = request.form.get("decision", "").strip().lower()
    note = request.form.get("note", "").strip()[:500] or None
    if decision not in {"verified", "pending", "rejected"}:
        flash("Choose a valid employer verification status.", "error")
        return redirect(url_for("admin.company_detail", user_id=user_id))

    db = get_db()
    company = db.execute(
        "SELECT organization_name FROM employer_profiles ep "
        "JOIN users u ON u.id=ep.user_id "
        "WHERE ep.user_id=? AND u.role='employer'",
        (user_id,),
    ).fetchone()
    if not company:
        return render_template("404.html"), 404

    db.execute(
        "UPDATE employer_profiles SET verification_status=?, verification_note=?, "
        "verified_at=CASE WHEN ?='verified' THEN CURRENT_TIMESTAMP ELSE NULL END "
        "WHERE user_id=?",
        (decision, note, decision, user_id),
    )
    audit("change_employer_verification", "employer", user_id, decision)
    db.commit()
    flash(f"Employer verification marked {decision}.", "success")
    return redirect(url_for("admin.company_detail", user_id=user_id))


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
    audit("moderate_vacancy", "vacancy", vacancy_id, decision)
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
            if len(selected_ids) > 100:
                flash("Moderate at most 100 jobs per batch.", "error")
                return redirect(url_for("admin.jobs"))

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
    audit(
        "bulk_moderate_vacancies",
        "vacancy",
        ",".join(map(str, selected_ids)),
        decision,
    )
    db.commit()
    flash(f"{len(selected_ids)} job(s) {decision} successfully.", "success")
    return redirect(url_for("admin.jobs"))




@admin_bp.get("/student-verifications")
@admin_required
def student_verifications():
    db = get_db()
    status = request.args.get("status", "pending").strip().lower()
    if status not in {"pending", "verified", "rejected", "all"}:
        status = "pending"
    clauses = ["r.status='college_approved'"]
    params = []
    if status != "all":
        clauses.append("r.admin_status=?")
        params.append(status)
    rows = db.execute(
        """SELECT r.*, u.name AS student_name, u.email AS student_email,
                  c.name AS college_name, sp.education
           FROM student_verification_requests r
           JOIN users u ON u.id=r.student_id
           JOIN colleges c ON c.id=r.college_id
           LEFT JOIN student_profiles sp ON sp.user_id=u.id
           WHERE """ + " AND ".join(clauses) + """
           ORDER BY CASE r.admin_status WHEN 'pending' THEN 0 ELSE 1 END,
                    r.submitted_at DESC, r.id DESC
           LIMIT 200""",
        params,
    ).fetchall()
    counts = {
        row["admin_status"]: row["total"]
        for row in db.execute(
            "SELECT admin_status, COUNT(*) AS total FROM student_verification_requests "
            "WHERE status='college_approved' GROUP BY admin_status"
        ).fetchall()
    }
    return render_template(
        "admin/student-verifications.html",
        requests=rows,
        counts=counts,
        status=status,
        today=date.today().isoformat(),
    )


@admin_bp.get("/student-verifications/<int:request_id>/document")
@admin_required
def student_verification_document(request_id):
    item = get_db().execute(
        "SELECT supporting_document_filename FROM student_verification_requests "
        "WHERE id=? AND status='college_approved'",
        (request_id,),
    ).fetchone()
    if not item or not item["supporting_document_filename"]:
        return render_template("404.html"), 404
    filename = item["supporting_document_filename"]
    response = send_from_directory(
        current_app.config["VERIFICATION_UPLOAD_FOLDER"],
        filename,
        as_attachment=True,
        download_name=f"college-supporting-document{Path(filename).suffix.lower()}",
    )
    response.headers["Cache-Control"] = "private, no-store"
    return response


@admin_bp.post("/student-verifications/<int:request_id>/decision")
@admin_required
def decide_student_verification(request_id):
    decision = request.form.get("decision", "").strip().lower()
    note = request.form.get("note", "").strip()[:500] or None
    expires_at = request.form.get("expires_at", "").strip() or None
    if decision not in {"verified", "rejected"}:
        flash("Choose final approve or reject.", "error")
        return redirect(url_for("admin.student_verifications"))
    if decision == "verified" and expires_at:
        try:
            expiry_date = date.fromisoformat(expires_at)
        except ValueError:
            flash("Enter a valid verification expiry date.", "error")
            return redirect(url_for("admin.student_verifications"))
        if expiry_date < date.today():
            flash("Verification expiry date cannot be in the past.", "error")
            return redirect(url_for("admin.student_verifications"))
    else:
        expires_at = None

    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        item = db.execute(
            "SELECT id, student_id, status, admin_status FROM student_verification_requests WHERE id=?",
            (request_id,),
        ).fetchone()
        if not item:
            db.rollback()
            return render_template("404.html"), 404
        if item["status"] != "college_approved" or item["admin_status"] != "pending":
            db.rollback()
            flash("This request is not awaiting final admin review.", "error")
            return redirect(url_for("admin.student_verifications"))
        cursor = db.execute(
            """UPDATE student_verification_requests
               SET admin_status=?, admin_review_note=?, admin_reviewed_at=CURRENT_TIMESTAMP,
                   expires_at=?
               WHERE id=? AND status='college_approved' AND admin_status='pending'""",
            (decision, note, expires_at, request_id),
        )
        if cursor.rowcount != 1:
            db.rollback()
            flash("This request was already reviewed. Refresh the queue.", "error")
            return redirect(url_for("admin.student_verifications"))
        audit("final_student_verification_" + decision, "student_verification_request", request_id, note)
        db.commit()
    except sqlite3.DatabaseError:
        db.rollback()
        current_app.logger.exception("Final student verification decision failed")
        flash("The final decision could not be saved. Please try again.", "error")
        return redirect(url_for("admin.student_verifications"))

    flash("Student verification marked " + decision + ".", "success")
    return redirect(url_for("admin.student_verifications"))


@admin_bp.get("/students/<int:student_id>/resume")
@admin_required
def student_resume(student_id):
    db = get_db()
    profile = db.execute(
        "SELECT resume_filename FROM student_profiles WHERE user_id=?", (student_id,)
    ).fetchone()
    if not profile or not profile["resume_filename"]:
        return render_template("404.html"), 404
    response = send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        profile["resume_filename"],
        as_attachment=True,
    )
    response.headers["Cache-Control"] = "private, no-store"
    return response

@admin_bp.get("/jobs/<int:job_id>")
@admin_required
def job_detail(job_id):
    db = get_db()
    job = db.execute("SELECT v.*,ep.organization_name,u.email employer_email,(SELECT COUNT(*) FROM applications a WHERE a.vacancy_id=v.id) application_count FROM vacancies v JOIN employer_profiles ep ON ep.user_id=v.employer_id JOIN users u ON u.id=v.employer_id WHERE v.id=?", (job_id,)).fetchone()
    if not job:
        return render_template("404.html"), 404
    applications = db.execute("SELECT a.*,u.name,u.email,sp.education,sp.college,sp.skills,sp.resume_filename FROM applications a JOIN users u ON u.id=a.student_id LEFT JOIN student_profiles sp ON sp.user_id=u.id WHERE a.vacancy_id=? ORDER BY a.id DESC", (job_id,)).fetchall()
    return render_template("admin/job-detail.html", job=job, applications=applications, internal=True)
