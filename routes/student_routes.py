import secrets
import sqlite3
from datetime import date
from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from database.database import get_db
from routes.decorators import role_required
from security import calculate_profile_strength, valid_resume_upload

student_bp = Blueprint("student", __name__, url_prefix="/student")


def deadline_passed(deadline):
    if not deadline:
        return False
    try:
        return date.fromisoformat(deadline) < date.today()
    except ValueError:
        return True


@student_bp.get("/dashboard")
@role_required("student")
def dashboard():
    db = get_db()
    uid = session["user_id"]
    stats = {
        "applications": db.execute(
            "SELECT COUNT(*) c FROM applications WHERE student_id=?", (uid,)
        ).fetchone()["c"],
        "shortlisted": db.execute(
            "SELECT COUNT(*) c FROM applications "
            "WHERE student_id=? AND status='Shortlisted'",
            (uid,),
        ).fetchone()["c"],
        "selected": db.execute(
            "SELECT COUNT(*) c FROM applications "
            "WHERE student_id=? AND status='Selected'",
            (uid,),
        ).fetchone()["c"],
        "saved": db.execute(
            "SELECT COUNT(*) c FROM saved_jobs WHERE student_id=?", (uid,)
        ).fetchone()["c"],
        "available_jobs": db.execute(
            "SELECT COUNT(*) c FROM vacancies v "
            "JOIN employer_profiles ep ON ep.user_id=v.employer_id "
            "WHERE v.status='active' "
            "AND v.moderation_status='approved' "
            "AND ep.account_status='active' AND ep.verification_status='verified' "
            "AND (v.deadline IS NULL OR "
            "v.deadline>=date('now','localtime'))"
        ).fetchone()["c"],
    }
    jobs = db.execute(
        "SELECT v.*,ep.organization_name,0 is_external,NULL apply_url "
        "FROM vacancies v JOIN employer_profiles ep ON ep.user_id=v.employer_id "
        "WHERE v.status='active' AND v.moderation_status='approved' "
        "AND ep.account_status='active' AND ep.verification_status='verified' "
        "AND (v.deadline IS NULL OR v.deadline>=date('now','localtime')) "
        "ORDER BY v.id DESC LIMIT 6"
    ).fetchall()
    return render_template("student/dashboard.html", stats=stats, jobs=jobs)


@student_bp.route("/profile", methods=["GET", "POST"])
@role_required("student")
def profile():
    db = get_db()
    uid = session["user_id"]
    if request.method == "POST":
        fields = [
            request.form.get(key, "").strip()
            for key in (
                "phone",
                "education",
                "college",
                "graduation_year",
                "skills",
                "certifications",
                "preferred_job_type",
                "preferred_location",
            )
        ]
        resume = request.files.get("resume")
        existing = db.execute(
            "SELECT resume_filename FROM student_profiles WHERE user_id=?",
            (uid,),
        ).fetchone()
        old_resume_filename = existing["resume_filename"] if existing else None
        resume_filename = old_resume_filename
        new_resume_path = None

        if resume and resume.filename:
            if not valid_resume_upload(resume):
                flash(
                    "Resume must be a valid PDF, DOC or DOCX file under 5 MB.", "error"
                )
                return redirect(url_for("student.profile"))
            safe_name = secure_filename(resume.filename) or "resume"
            resume_filename = f"{uid}_{uuid4().hex}_{safe_name}"
            upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
            upload_dir.mkdir(parents=True, exist_ok=True)
            new_resume_path = upload_dir / resume_filename
            try:
                resume.save(new_resume_path)
            except OSError:
                current_app.logger.exception(
                    "Resume upload failed during profile update"
                )
                flash("The resume could not be saved. Please try again.", "error")
                return redirect(url_for("student.profile"))

        strength = calculate_profile_strength(fields, bool(resume_filename))
        try:
            db.execute(
                "UPDATE student_profiles SET "
            "phone=?, education=?, college=?, graduation_year=?, "
            "skills=?, certifications=?, preferred_job_type=?, preferred_location=?, "
            "resume_filename=?, profile_strength=? WHERE user_id=?",
                (*fields, resume_filename, strength, uid),
            )
            db.commit()
        except sqlite3.DatabaseError:
            db.rollback()
            if new_resume_path:
                new_resume_path.unlink(missing_ok=True)
            current_app.logger.exception("Student profile update failed")
            flash("The student profile could not be updated. Please try again.", "error")
            return redirect(url_for("student.profile"))

        if (
            new_resume_path
            and old_resume_filename
            and old_resume_filename != resume_filename
        ):
            try:
                (Path(current_app.config["UPLOAD_FOLDER"]) / old_resume_filename).unlink(
                    missing_ok=True
                )
            except OSError:
                current_app.logger.warning(
                    "Could not remove previous resume %s", old_resume_filename
                )

        flash("Student profile updated successfully.", "success")
        return redirect(url_for("student.profile"))

    profile_data = db.execute(
        "SELECT * FROM student_profiles WHERE user_id=?", (uid,)
    ).fetchone()
    user = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return render_template(
        "student/profile.html",
        profile=profile_data,
        user=user,
        edit_mode=request.args.get("edit") == "1",
    )


@student_bp.route("/verification", methods=["GET", "POST"])
@role_required("student")
def verification():
    db = get_db()
    student_id = session["user_id"]
    if request.method == "POST":
        college_id = request.form.get("college_id", type=int)
        enrollment_number = request.form.get("enrollment_number", "").strip()[:80]
        graduation_year = request.form.get("graduation_year", "").strip()
        if not college_id or not enrollment_number or not graduation_year.isdigit() or not 2000 <= int(graduation_year) <= 2100:
            flash("Enter a college, enrollment number and valid graduation year.", "error")
            return redirect(url_for("student.verification"))
        college = db.execute("SELECT id FROM colleges WHERE id=? AND status='active'", (college_id,)).fetchone()
        if not college:
            flash("Choose an active college from the list.", "error")
            return redirect(url_for("student.verification"))
        existing = db.execute("SELECT id, status, admin_status FROM student_verification_requests WHERE student_id=?", (student_id,)).fetchone()
        can_resubmit = existing and (existing["status"] == "college_rejected" or (existing["status"] == "college_approved" and existing["admin_status"] == "rejected"))
        if existing and not can_resubmit:
            flash("You already have a verification request in progress or approved.", "error")
            return redirect(url_for("student.verification"))
        try:
            if existing:
                db.execute(
                    "UPDATE student_verification_requests SET college_id=?, enrollment_number=?, graduation_year=?, status='pending', reviewer_id=NULL, reviewer_note=NULL, submitted_at=CURRENT_TIMESTAMP, reviewed_at=NULL, admin_status='pending', admin_review_note=NULL, admin_reviewed_at=NULL WHERE id=? AND student_id=?",
                    (college_id, enrollment_number, graduation_year, existing["id"], student_id),
                )
                request_id = existing["id"]
            else:
                cursor = db.execute(
                    "INSERT INTO student_verification_requests(student_id, college_id, enrollment_number, graduation_year) VALUES(?,?,?,?)",
                    (student_id, college_id, enrollment_number, graduation_year),
                )
                request_id = cursor.lastrowid
            db.execute(
                "INSERT INTO audit_log(actor_type, actor_id, action, target_type, target_id, details, ip_address) VALUES('student', ?, 'submit_college_verification', 'student_verification_request', ?, ?, ?)",
                (str(student_id), str(request_id), "College ID: " + str(college_id), request.remote_addr),
            )
            db.commit()
        except sqlite3.DatabaseError:
            db.rollback()
            flash("Your verification request could not be saved. Please try again.", "error")
            return redirect(url_for("student.verification"))
        flash("Your college verification request has been submitted.", "success")
        return redirect(url_for("student.verification"))

    verification = db.execute(
        "SELECT r.*, c.name AS college_name FROM student_verification_requests r JOIN colleges c ON c.id=r.college_id WHERE r.student_id=?",
        (student_id,),
    ).fetchone()
    colleges = db.execute("SELECT id, name FROM colleges WHERE status='active' ORDER BY name COLLATE NOCASE").fetchall()
    return render_template("student/verification.html", verification=verification, colleges=colleges)


@student_bp.get("/resume")
@role_required("student")
def resume():
    profile = (
        get_db()
        .execute(
            "SELECT resume_filename FROM student_profiles WHERE user_id=?",
            (session["user_id"],),
        )
        .fetchone()
    )
    if not profile or not profile["resume_filename"]:
        return render_template("404.html"), 404
    response = send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        profile["resume_filename"],
        as_attachment=True,
    )
    response.headers["Cache-Control"] = "private, no-store"
    return response


@student_bp.get("/jobs")
@role_required("student")
def jobs():
    db = get_db()
    q = request.args.get("q", "").strip()
    typ = request.args.get("type", "").strip()
    location = request.args.get("location", "").strip()
    skill = request.args.get("skill", "").strip()
    sort = request.args.get("sort", "newest").strip()
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 24
    offset = (page - 1) * per_page
    uid = session["user_id"]
    sql = (
        "SELECT v.id,v.title,v.vacancy_type,v.description,v.location,v.salary,v.skills,"
        "ep.organization_name,EXISTS(SELECT 1 FROM saved_jobs s WHERE s.vacancy_id=v.id "
        "AND s.student_id=?) saved,EXISTS(SELECT 1 FROM applications a WHERE "
        "a.vacancy_id=v.id AND a.student_id=?) applied,0 is_external,NULL apply_url,"
        "NULL source,NULL source_url FROM vacancies v JOIN employer_profiles ep "
        "ON ep.user_id=v.employer_id WHERE v.status='active' AND v.moderation_status='approved' "
        "AND ep.account_status='active' AND ep.verification_status='verified' AND (v.deadline IS NULL OR v.deadline>=date('now','localtime'))"
    )
    args = [uid, uid]
    if q:
        sql += " AND (v.title LIKE ? OR ep.organization_name LIKE ? OR v.skills LIKE ?)"
        args += [f"%{q}%"] * 3
    if typ:
        sql += " AND v.vacancy_type=?"
        args.append(typ)
    if location:
        sql += " AND v.location LIKE ?"
        args.append(f"%{location}%")
    if skill:
        sql += " AND v.skills LIKE ?"
        args.append(f"%{skill}%")

    order_by = "v.id DESC"
    if sort == "deadline":
        order_by = "CASE WHEN v.deadline IS NULL THEN 1 ELSE 0 END, v.deadline ASC, v.id DESC"
    elif sort == "title":
        order_by = "LOWER(v.title) ASC, v.id DESC"

    jobs = db.execute(
        sql + " ORDER BY " + order_by + " LIMIT ? OFFSET ?",
        [*args, per_page, offset],
    ).fetchall()
    return render_template(
        "student/jobs.html",
        jobs=jobs,
        q=q,
        typ=typ,
        location=location,
        skill=skill,
        sort=sort,
        page=page,
        per_page=per_page,
        has_next=len(jobs) == per_page,
    )


@student_bp.get("/jobs/<int:vacancy_id>")
@role_required("student")
def job_details(vacancy_id):
    db = get_db()
    uid = session["user_id"]
    job = db.execute(
        "SELECT v.*,ep.organization_name,ep.website,ep.location employer_location "
        "FROM vacancies v JOIN employer_profiles ep ON ep.user_id=v.employer_id "
        "WHERE v.id=? AND v.status='active' AND v.moderation_status='approved' AND ep.account_status='active' AND ep.verification_status='verified' "
        "AND (v.deadline IS NULL OR v.deadline>=date('now','localtime'))",
        (vacancy_id,),
    ).fetchone()
    if not job:
        return render_template("404.html"), 404
    applied = db.execute(
        "SELECT 1 FROM applications WHERE vacancy_id=? AND student_id=?",
        (vacancy_id, uid),
    ).fetchone()
    saved = db.execute(
        "SELECT 1 FROM saved_jobs WHERE vacancy_id=? AND student_id=?",
        (vacancy_id, uid),
    ).fetchone()
    return render_template(
        "student/job-details.html", job=job, applied=bool(applied), saved=bool(saved)
    )


@student_bp.post("/jobs/<int:vacancy_id>/apply")
@role_required("student")
def apply(vacancy_id):
    db = get_db()
    uid = session["user_id"]
    vacancy = db.execute(
        "SELECT v.deadline FROM vacancies v JOIN employer_profiles ep ON ep.user_id=v.employer_id "
        "WHERE v.id=? AND v.status='active' AND v.moderation_status='approved' "
        "AND ep.account_status='active' AND ep.verification_status='verified' "
        "AND (v.deadline IS NULL OR v.deadline>=date('now','localtime'))",
        (vacancy_id,),
    ).fetchone()
    if not vacancy:
        flash("This opportunity is no longer active.", "error")
        return redirect(url_for("student.jobs"))
    if deadline_passed(vacancy["deadline"]):
        flash("Applications for this opportunity are closed.", "error")
        return redirect(url_for("student.jobs"))
    try:
        db.execute(
            "INSERT INTO applications(vacancy_id,student_id) VALUES(?,?)",
            (vacancy_id, uid),
        )
        db.commit()
        flash("Application submitted. Status: Applied.", "success")
    except sqlite3.IntegrityError:
        db.rollback()
        flash("You have already applied to this vacancy.", "error")
    return redirect(url_for("student.jobs"))


@student_bp.post("/jobs/<int:vacancy_id>/save")
@role_required("student")
def save(vacancy_id):
    db = get_db()
    uid = session["user_id"]
    job = db.execute(
        "SELECT v.id FROM vacancies v JOIN employer_profiles ep ON ep.user_id=v.employer_id "
        "WHERE v.id=? AND v.status='active' AND v.moderation_status='approved' "
        "AND ep.account_status='active' AND ep.verification_status='verified' AND (v.deadline IS NULL OR v.deadline>=date('now','localtime'))",
        (vacancy_id,),
    ).fetchone()
    if not job:
        flash("This opportunity is no longer available.", "error")
        return redirect(url_for("student.jobs"))
    exists = db.execute(
        "SELECT id FROM saved_jobs WHERE vacancy_id=? AND student_id=?",
        (vacancy_id, uid),
    ).fetchone()
    if exists:
        db.execute("DELETE FROM saved_jobs WHERE id=?", (exists["id"],))
        flash("Removed from saved jobs.", "success")
    else:
        db.execute(
            "INSERT INTO saved_jobs(vacancy_id,student_id) VALUES(?,?)",
            (vacancy_id, uid),
        )
        flash("Saved for later.", "success")
    db.commit()
    return redirect(url_for("student.jobs"))


@student_bp.get("/applications")
@role_required("student")
def applications():
    db = get_db()
    uid = session["user_id"]
    rows = db.execute(
        "SELECT a.id,a.title,a.vacancy_type,a.location,a.organization_name,a.applied_at,a.status,a.is_external,a.employer_id "
        "FROM (SELECT a.id,v.title,v.vacancy_type,v.location,ep.organization_name,v.employer_id,a.applied_at,a.status,0 is_external "
        "FROM applications a JOIN vacancies v ON v.id=a.vacancy_id JOIN employer_profiles ep ON ep.user_id=v.employer_id "
        "WHERE a.student_id=?) a ORDER BY a.applied_at DESC",
        (uid,),
    ).fetchall()
    return render_template("student/applications.html", applications=rows)


@student_bp.route("/change-password", methods=["GET", "POST"])
@role_required("student")
def change_password():
    db = get_db()
    user_id = session["user_id"]
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        user = db.execute(
            "SELECT password_hash FROM users WHERE id=? AND role='student'",
            (user_id,),
        ).fetchone()
        if not user or not check_password_hash(user["password_hash"], current_password):
            flash("Current password is incorrect.", "error")
            return render_template("student/change-password.html")
        if len(new_password) < 12:
            flash("New password must be at least 12 characters.", "error")
            return render_template("student/change-password.html")
        if new_password != confirm_password:
            flash("New password and confirmation do not match.", "error")
            return render_template("student/change-password.html")
        if new_password == current_password:
            flash("Choose a new password different from the current password.", "error")
            return render_template("student/change-password.html")
        new_auth_version = secrets.token_urlsafe(32)
        db.execute(
            "UPDATE users SET password_hash=?, auth_version=? WHERE id=? AND role='student'",
            (generate_password_hash(new_password), new_auth_version, user_id),
        )
        db.commit()
        session["auth_version"] = new_auth_version
        flash("Password changed successfully.", "success")
        return redirect(url_for("settings.preferences"))
    return render_template("student/change-password.html")
