from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from database.database import get_db
from routes.decorators import role_required

employer_bp = Blueprint("employer", __name__, url_prefix="/employer")

@employer_bp.get("/dashboard")
@role_required("employer")
def dashboard():
    db = get_db(); uid = session["user_id"]
    stats = {
        "vacancies": db.execute("SELECT COUNT(*) c FROM vacancies WHERE employer_id=? AND status='active'", (uid,)).fetchone()["c"],
        "applications": db.execute("SELECT COUNT(*) c FROM applications a JOIN vacancies v ON v.id=a.vacancy_id WHERE v.employer_id=?", (uid,)).fetchone()["c"],
        "shortlisted": db.execute("SELECT COUNT(*) c FROM applications a JOIN vacancies v ON v.id=a.vacancy_id WHERE v.employer_id=? AND a.status='Shortlisted'", (uid,)).fetchone()["c"],
        "selected": db.execute("SELECT COUNT(*) c FROM applications a JOIN vacancies v ON v.id=a.vacancy_id WHERE v.employer_id=? AND a.status='Selected'", (uid,)).fetchone()["c"]
    }
    applications = db.execute("""SELECT a.*, v.title, u.name, u.email FROM applications a JOIN vacancies v ON v.id=a.vacancy_id
                               JOIN users u ON u.id=a.student_id WHERE v.employer_id=? ORDER BY a.id DESC LIMIT 8""", (uid,)).fetchall()
    return render_template("employer/dashboard.html", stats=stats, applications=applications)

@employer_bp.route("/profile", methods=["GET", "POST"])
@role_required("employer")
def profile():
    db = get_db(); uid = session["user_id"]
    if request.method == "POST":
        data = [request.form.get(k, "").strip() for k in ("organization_name", "organization_type", "website", "location", "description")]
        db.execute("UPDATE employer_profiles SET organization_name=?, organization_type=?, website=?, location=?, description=? WHERE user_id=?", (*data, uid))
        db.commit(); flash("Organization profile updated.", "success")
        return redirect(url_for("employer.profile"))
    profile = db.execute("SELECT * FROM employer_profiles WHERE user_id=?", (uid,)).fetchone()
    return render_template("employer/profile.html", profile=profile)

@employer_bp.route("/vacancies/new", methods=["GET", "POST"])
@role_required("employer")
def new_vacancy():
    if request.method == "POST":
        form = request.form
        status = "active" if form.get("publish") == "1" else "draft"
        db = get_db()
        db.execute("""INSERT INTO vacancies(employer_id,title,vacancy_type,description,location,salary,skills,eligibility,deadline,status)
                      VALUES(?,?,?,?,?,?,?,?,?,?)""", (session["user_id"], form.get("title",""), form.get("vacancy_type"), form.get("description",""), form.get("location",""), form.get("salary",""), form.get("skills",""), form.get("eligibility",""), form.get("deadline") or None, status))
        db.commit(); flash("Vacancy published." if status == "active" else "Vacancy saved as draft.", "success")
        return redirect(url_for("employer.vacancies"))
    return render_template("employer/post-vacancy.html")

@employer_bp.get("/vacancies")
@role_required("employer")
def vacancies():
    rows = get_db().execute("SELECT * FROM vacancies WHERE employer_id=? ORDER BY id DESC", (session["user_id"],)).fetchall()
    return render_template("employer/vacancies.html", vacancies=rows)

@employer_bp.route("/vacancies/<int:vacancy_id>/edit", methods=["GET", "POST"])
@role_required("employer")
def edit_vacancy(vacancy_id):
    db = get_db(); job = db.execute("SELECT * FROM vacancies WHERE id=? AND employer_id=?", (vacancy_id, session["user_id"])).fetchone()
    if not job: return render_template("404.html"), 404
    if request.method == "POST":
        f = request.form
        db.execute("""UPDATE vacancies SET title=?, vacancy_type=?, description=?, location=?, salary=?, skills=?, eligibility=?, deadline=? WHERE id=? AND employer_id=?""", (f.get("title"), f.get("vacancy_type"), f.get("description"), f.get("location"), f.get("salary"), f.get("skills"), f.get("eligibility"), f.get("deadline") or None, vacancy_id, session["user_id"]))
        db.commit(); flash("Vacancy updated.", "success"); return redirect(url_for("employer.vacancies"))
    return render_template("employer/edit-vacancy.html", job=job)

@employer_bp.post("/vacancies/<int:vacancy_id>/status")
@role_required("employer")
def vacancy_status(vacancy_id):
    status = request.form.get("status")
    if status not in {"draft", "active", "closed"}: return redirect(url_for("employer.vacancies"))
    db = get_db(); db.execute("UPDATE vacancies SET status=? WHERE id=? AND employer_id=?", (status, vacancy_id, session["user_id"])); db.commit()
    flash(f"Vacancy marked {status}.", "success"); return redirect(url_for("employer.vacancies"))

@employer_bp.get("/applications")
@role_required("employer")
def applications():
    rows = get_db().execute("""SELECT a.*, v.title, v.vacancy_type, u.name, u.email, sp.education, sp.skills, sp.resume_filename
                              FROM applications a JOIN vacancies v ON v.id=a.vacancy_id JOIN users u ON u.id=a.student_id
                              LEFT JOIN student_profiles sp ON sp.user_id=u.id WHERE v.employer_id=? ORDER BY a.id DESC""", (session["user_id"],)).fetchall()
    return render_template("employer/applications.html", applications=rows)

@employer_bp.post("/applications/<int:application_id>/status")
@role_required("employer")
def application_status(application_id):
    status = request.form.get("status")
    if status not in {"Applied", "Shortlisted", "Selected", "Rejected"}: return redirect(url_for("employer.applications"))
    db = get_db()
    db.execute("""UPDATE applications SET status=? WHERE id=? AND vacancy_id IN (SELECT id FROM vacancies WHERE employer_id=?)""", (status, application_id, session["user_id"]))
    db.commit(); flash(f"Application marked {status}.", "success")
    return redirect(request.referrer or url_for("employer.applications"))
