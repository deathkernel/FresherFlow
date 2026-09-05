from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for, send_from_directory
from werkzeug.utils import secure_filename
from database.database import get_db
from routes.decorators import role_required

student_bp = Blueprint("student", __name__, url_prefix="/student")
ALLOWED_RESUME_EXTENSIONS = {"pdf", "doc", "docx"}


def valid_resume(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_RESUME_EXTENSIONS


@student_bp.get("/dashboard")
@role_required("student")
def dashboard():
    db = get_db(); uid = session["user_id"]
    stats = {
        "applications": db.execute("SELECT COUNT(*) c FROM applications WHERE student_id=?", (uid,)).fetchone()["c"],
        "shortlisted": db.execute("SELECT COUNT(*) c FROM applications WHERE student_id=? AND status='Shortlisted'", (uid,)).fetchone()["c"],
        "selected": db.execute("SELECT COUNT(*) c FROM applications WHERE student_id=? AND status='Selected'", (uid,)).fetchone()["c"],
        "saved": db.execute("SELECT COUNT(*) c FROM saved_jobs WHERE student_id=?", (uid,)).fetchone()["c"]
    }
    jobs = db.execute("""SELECT v.*, ep.organization_name FROM vacancies v JOIN employer_profiles ep ON ep.user_id=v.employer_id
                        WHERE v.status='active' ORDER BY v.id DESC LIMIT 6""").fetchall()
    return render_template("student/dashboard.html", stats=stats, jobs=jobs)


@student_bp.route("/profile", methods=["GET", "POST"])
@role_required("student")
def profile():
    db = get_db(); uid = session["user_id"]
    if request.method == "POST":
        fields = [request.form.get(k, "").strip() for k in ("phone", "education", "college", "graduation_year", "skills", "certifications", "preferred_job_type", "preferred_location")]
        resume = request.files.get("resume")
        existing = db.execute("SELECT resume_filename FROM student_profiles WHERE user_id=?", (uid,)).fetchone()["resume_filename"]
        resume_filename = existing
        if resume and resume.filename:
            if not valid_resume(resume.filename):
                flash("Resume must be a PDF, DOC or DOCX file.", "error")
                return redirect(url_for("student.profile"))
            resume_filename = f"{uid}_{secure_filename(resume.filename)}"
            Path(current_app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
            resume.save(Path(current_app.config["UPLOAD_FOLDER"]) / resume_filename)
        filled = sum(bool(value) for value in fields)
        strength = min(100, 20 + filled * 10 + (10 if resume_filename else 0))
        db.execute("""UPDATE student_profiles SET phone=?, education=?, college=?, graduation_year=?, skills=?, certifications=?,
                    preferred_job_type=?, preferred_location=?, resume_filename=?, profile_strength=? WHERE user_id=?""",
                   (*fields, resume_filename, strength, uid))
        db.commit(); flash("Student profile updated successfully.", "success")
        return redirect(url_for("student.profile"))
    profile = db.execute("SELECT * FROM student_profiles WHERE user_id=?", (uid,)).fetchone()
    user = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return render_template("student/profile.html", profile=profile, user=user)


@student_bp.get("/resume")
@role_required("student")
def resume():
    profile = get_db().execute("SELECT resume_filename FROM student_profiles WHERE user_id=?", (session["user_id"],)).fetchone()
    if not profile or not profile["resume_filename"]:
        return render_template("404.html"), 404
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], profile["resume_filename"], as_attachment=False)


@student_bp.get("/jobs")
@role_required("student")
def jobs():
    db = get_db(); q = request.args.get("q", "").strip(); typ = request.args.get("type", "").strip()
    sql = """SELECT v.*, ep.organization_name, EXISTS(SELECT 1 FROM saved_jobs s WHERE s.vacancy_id=v.id AND s.student_id=?) saved,
              EXISTS(SELECT 1 FROM applications a WHERE a.vacancy_id=v.id AND a.student_id=?) applied
              FROM vacancies v JOIN employer_profiles ep ON ep.user_id=v.employer_id WHERE v.status='active'"""
    args = [session["user_id"], session["user_id"]]
    if q:
        sql += " AND (v.title LIKE ? OR ep.organization_name LIKE ? OR v.skills LIKE ?)"; args += [f"%{q}%"] * 3
    if typ:
        sql += " AND v.vacancy_type=?"; args.append(typ)
    rows = db.execute(sql + " ORDER BY v.id DESC", args).fetchall()
    return render_template("student/jobs.html", jobs=rows, q=q, typ=typ)


@student_bp.get("/jobs/<int:vacancy_id>")
@role_required("student")
def job_details(vacancy_id):
    db = get_db(); uid = session["user_id"]
    job = db.execute("""SELECT v.*, ep.organization_name, ep.website, ep.location employer_location FROM vacancies v
                       JOIN employer_profiles ep ON ep.user_id=v.employer_id WHERE v.id=? AND v.status='active'""", (vacancy_id,)).fetchone()
    if not job: return render_template("404.html"), 404
    applied = db.execute("SELECT 1 FROM applications WHERE vacancy_id=? AND student_id=?", (vacancy_id, uid)).fetchone()
    saved = db.execute("SELECT 1 FROM saved_jobs WHERE vacancy_id=? AND student_id=?", (vacancy_id, uid)).fetchone()
    return render_template("student/job-details.html", job=job, applied=bool(applied), saved=bool(saved))


@student_bp.post("/jobs/<int:vacancy_id>/apply")
@role_required("student")
def apply(vacancy_id):
    db = get_db()
    exists = db.execute("SELECT 1 FROM vacancies WHERE id=? AND status='active'", (vacancy_id,)).fetchone()
    if not exists:
        flash("This opportunity is no longer active.", "error")
        return redirect(url_for("student.jobs"))
    try:
        db.execute("INSERT INTO applications(vacancy_id,student_id) VALUES(?,?)", (vacancy_id, session["user_id"]))
        db.commit(); flash("Application submitted. Status: Applied.", "success")
    except Exception:
        db.rollback(); flash("You have already applied to this vacancy.", "error")
    return redirect(request.referrer or url_for("student.jobs"))


@student_bp.post("/jobs/<int:vacancy_id>/save")
@role_required("student")
def save(vacancy_id):
    db = get_db(); uid = session["user_id"]
    exists = db.execute("SELECT id FROM saved_jobs WHERE vacancy_id=? AND student_id=?", (vacancy_id, uid)).fetchone()
    if exists: db.execute("DELETE FROM saved_jobs WHERE id=?", (exists["id"],)); flash("Removed from saved jobs.", "success")
    else: db.execute("INSERT INTO saved_jobs(vacancy_id,student_id) VALUES(?,?)", (vacancy_id, uid)); flash("Saved for later.", "success")
    db.commit(); return redirect(request.referrer or url_for("student.jobs"))


@student_bp.get("/applications")
@role_required("student")
def applications():
    rows = get_db().execute("""SELECT a.*, v.title, v.vacancy_type, v.location, ep.organization_name FROM applications a
                              JOIN vacancies v ON v.id=a.vacancy_id JOIN employer_profiles ep ON ep.user_id=v.employer_id
                              WHERE a.student_id=? ORDER BY a.id DESC""", (session["user_id"],)).fetchall()
    return render_template("student/applications.html", applications=rows)
