import io
import sqlite3
from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from openpyxl import load_workbook

from database.database import get_db
from routes.decorators import role_required

employer_bp = Blueprint("employer", __name__, url_prefix="/employer")
VACANCY_TYPES = {"Internship", "Entry-level Job"}
VACANCY_STATUSES = {"draft", "active", "closed"}
APPLICATION_STATUSES = {"Applied", "Shortlisted", "Selected", "Rejected"}
EXCEL_HEADERS = {
    "title": "title",
    "type": "vacancy_type",
    "vacancy type": "vacancy_type",
    "vacancy_type": "vacancy_type",
    "location": "location",
    "salary": "salary",
    "salary / stipend": "salary",
    "salary/stipend": "salary",
    "stipend": "salary",
    "deadline": "deadline",
    "skills": "skills",
    "eligibility": "eligibility",
    "description": "description",
    "role description": "description",
}


def experience_requirement_invalid(vacancy_type, eligibility):
    if vacancy_type != "Entry-level Job":
        return False
    text = (eligibility or "").strip().lower()
    if not text:
        return False
    terms = (
        "year experience",
        "years experience",
        "year of experience",
        "years of experience",
        "yr experience",
        "yrs experience",
        "yr of experience",
        "yrs of experience",
        "work experience",
        "professional experience",
        "prior experience",
        "previous experience",
        "relevant experience",
        "industry experience",
        "experience required",
        "experience mandatory",
        "minimum experience",
    )
    return any(term in text for term in terms)


def deadline_invalid(deadline):
    if not deadline:
        return False
    try:
        return date.fromisoformat(deadline) < date.today()
    except ValueError:
        return True


def vacancy_form(form):
    title = form.get("title", "").strip()
    vacancy_type = form.get("vacancy_type", "").strip()
    location = form.get("location", "").strip()
    description = form.get("description", "").strip()
    eligibility = form.get("eligibility", "").strip()
    deadline = form.get("deadline") or None
    if not title or not location or not description:
        return None, "Title, location and description are required."
    if vacancy_type not in VACANCY_TYPES:
        return None, "Choose a valid vacancy type."
    if experience_requirement_invalid(vacancy_type, eligibility):
        return (
            None,
            "Entry-level Jobs cannot require prior work experience. For roles requiring experience, publish an Internship instead.",
        )
    if deadline_invalid(deadline):
        return None, "Application deadline must be today or a future date."
    return {
        "title": title,
        "vacancy_type": vacancy_type,
        "description": description,
        "location": location,
        "salary": form.get("salary", "").strip(),
        "skills": form.get("skills", "").strip(),
        "eligibility": eligibility,
        "deadline": deadline,
    }, None


def normalize_excel_header(value):
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def excel_cell_text(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def bulk_vacancy_forms(form):
    titles = form.getlist("title")
    types = form.getlist("vacancy_type")
    locations = form.getlist("location")
    descriptions = form.getlist("description")
    salaries = form.getlist("salary")
    skills = form.getlist("skills")
    eligibilities = form.getlist("eligibility")
    deadlines = form.getlist("deadline")
    count = len(titles)
    if (
        not count
        or count != len(types)
        or count != len(locations)
        or count != len(descriptions)
    ):
        return None, "Please complete each vacancy card before publishing."
    vacancies = []
    for i in range(count):
        data = {
            "title": titles[i].strip(),
            "vacancy_type": types[i].strip(),
            "location": locations[i].strip(),
            "description": descriptions[i].strip(),
            "salary": salaries[i].strip() if i < len(salaries) else "",
            "skills": skills[i].strip() if i < len(skills) else "",
            "eligibility": eligibilities[i].strip() if i < len(eligibilities) else "",
            "deadline": deadlines[i] if i < len(deadlines) else None,
        }
        if not data["title"] or not data["location"] or not data["description"]:
            return None, f"Vacancy {i+1}: title, location and description are required."
        if data["vacancy_type"] not in VACANCY_TYPES:
            return None, f"Vacancy {i+1}: choose a valid vacancy type."
        if experience_requirement_invalid(data["vacancy_type"], data["eligibility"]):
            return (
                None,
                f"Vacancy {i+1}: Entry-level Jobs cannot require prior work experience.",
            )
        if deadline_invalid(data["deadline"]):
            return None, f"Vacancy {i+1}: application deadline must be today or a future date."
        vacancies.append(data)
    return vacancies, None


def excel_vacancy_forms(file_storage):
    filename = (file_storage.filename or "").strip().lower()
    if not filename.endswith(".xlsx"):
        return None, "Please upload an Excel .xlsx file."
    try:
        workbook = load_workbook(
            filename=io.BytesIO(file_storage.read()), read_only=True, data_only=True
        )
    except Exception:
        return None, "The Excel file could not be read. Please upload a valid .xlsx file."

    try:
        sheet = workbook.active
        rows = sheet.iter_rows(values_only=True)
        try:
            header_row = next(rows)
        except StopIteration:
            return None, "The Excel file is empty."

        headers = {}
        for index, value in enumerate(header_row):
            normalized = normalize_excel_header(value)
            if normalized in EXCEL_HEADERS:
                headers[EXCEL_HEADERS[normalized]] = index

        required = {"title", "vacancy_type", "location", "description"}
        missing = required - set(headers)
        if missing:
            return None, "Missing required Excel columns: " + ", ".join(sorted(missing)) + "."

        vacancies = []
        for row_number, row in enumerate(rows, start=2):
            if not any(value not in (None, "") for value in row):
                continue
            data = {}
            for field in EXCEL_HEADERS.values():
                index = headers.get(field)
                data[field] = excel_cell_text(row[index]) if index is not None and index < len(row) else ""
            data["deadline"] = data["deadline"] or None
            if not data["title"] or not data["location"] or not data["description"]:
                return None, f"Excel row {row_number}: title, location and description are required."
            if data["vacancy_type"] not in VACANCY_TYPES:
                return None, f"Excel row {row_number}: type must be Internship or Entry-level Job."
            if experience_requirement_invalid(data["vacancy_type"], data["eligibility"]):
                return None, f"Excel row {row_number}: Entry-level Jobs cannot require prior work experience."
            if deadline_invalid(data["deadline"]):
                return None, f"Excel row {row_number}: application deadline must be today or a future date."
            vacancies.append(data)

        if not vacancies:
            return None, "No vacancy rows were found in the Excel file."
        return vacancies, None
    finally:
        workbook.close()


@employer_bp.get("/dashboard")
@role_required("employer")
def dashboard():
    db = get_db()
    uid = session["user_id"]
    stats = {
        "vacancies": db.execute(
            "SELECT COUNT(*) c FROM vacancies WHERE employer_id=? AND status='active' AND moderation_status='approved'",
            (uid,),
        ).fetchone()["c"],
        "applications": db.execute(
            "SELECT COUNT(*) c FROM applications a JOIN vacancies v ON v.id=a.vacancy_id WHERE v.employer_id=?",
            (uid,),
        ).fetchone()["c"],
        "shortlisted": db.execute(
            "SELECT COUNT(*) c FROM applications a JOIN vacancies v ON v.id=a.vacancy_id WHERE v.employer_id=? AND a.status='Shortlisted'",
            (uid,),
        ).fetchone()["c"],
        "selected": db.execute(
            "SELECT COUNT(*) c FROM applications a JOIN vacancies v ON v.id=a.vacancy_id WHERE v.employer_id=? AND a.status='Selected'",
            (uid,),
        ).fetchone()["c"],
    }
    applications = db.execute(
        "SELECT a.*,v.title,u.name,u.email FROM applications a JOIN vacancies v ON v.id=a.vacancy_id JOIN users u ON u.id=a.student_id WHERE v.employer_id=? ORDER BY a.id DESC LIMIT 8",
        (uid,),
    ).fetchall()
    return render_template(
        "employer/dashboard.html", stats=stats, applications=applications
    )


@employer_bp.route("/profile", methods=["GET", "POST"])
@role_required("employer")
def profile():
    db = get_db()
    uid = session["user_id"]
    if request.method == "POST":
        data = [
            request.form.get(k, "").strip()
            for k in (
                "organization_name",
                "organization_type",
                "website",
                "location",
                "description",
            )
        ]
        if not data[0]:
            flash("Organization name is required.", "error")
            return redirect(url_for("employer.profile"))
        db.execute(
            "UPDATE employer_profiles SET organization_name=?,organization_type=?,website=?,location=?,description=? WHERE user_id=?",
            (*data, uid),
        )
        db.commit()
        flash("Organization profile updated.", "success")
        return redirect(url_for("employer.profile"))
    profile = db.execute(
        "SELECT * FROM employer_profiles WHERE user_id=?", (uid,)
    ).fetchone()
    return render_template("employer/profile.html", profile=profile)


@employer_bp.route("/vacancies/new", methods=["GET", "POST"])
@role_required("employer")
def new_vacancy():
    if request.method == "POST":
        data, error = vacancy_form(request.form)
        if error:
            flash(error, "error")
            return render_template("employer/post-vacancy.html")
        status = "draft"
        db = get_db()
        try:
            db.execute(
                "INSERT INTO vacancies(employer_id,title,vacancy_type,description,location,salary,skills,eligibility,deadline,status,moderation_status) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    session["user_id"],
                    data["title"],
                    data["vacancy_type"],
                    data["description"],
                    data["location"],
                    data["salary"],
                    data["skills"],
                    data["eligibility"],
                    data["deadline"],
                    status,
                    "pending",
                ),
            )
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            flash("The vacancy could not be saved.", "error")
            return render_template("employer/post-vacancy.html")
        flash(
            (
                "Vacancy submitted for developer review."
                if request.form.get("publish") == "1"
                else "Vacancy saved as draft."
            ),
            "success",
        )
        return redirect(url_for("employer.vacancies"))
    return render_template("employer/post-vacancy.html")


@employer_bp.route("/vacancies/bulk-new", methods=["GET", "POST"])
@role_required("employer")
def bulk_new_vacancies():
    if request.method == "GET":
        return render_template("employer/bulk-vacancies.html")

    if request.form.get("import_excel") == "1":
        excel_file = request.files.get("excel_file")
        if not excel_file or not excel_file.filename:
            flash("Choose an Excel .xlsx file first.", "error")
            return render_template("employer/bulk-vacancies.html"), 400
        vacancies, error = excel_vacancy_forms(excel_file)
        if error:
            flash(error, "error")
            return render_template("employer/bulk-vacancies.html"), 400
    else:
        vacancies, error = bulk_vacancy_forms(request.form)
        if error:
            flash(error, "error")
            return render_template("employer/bulk-vacancies.html"), 400

    db = get_db()
    uid = session["user_id"]
    try:
        for data in vacancies:
            db.execute(
                "INSERT INTO vacancies(employer_id,title,vacancy_type,description,location,salary,skills,eligibility,deadline,status,moderation_status) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    uid,
                    data["title"],
                    data["vacancy_type"],
                    data["description"],
                    data["location"],
                    data["salary"],
                    data["skills"],
                    data["eligibility"],
                    data["deadline"],
                    "draft",
                    "pending",
                ),
            )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        flash(
            "None of the vacancies were imported because one or more entries were invalid.",
            "error",
        )
        return render_template("employer/bulk-vacancies.html"), 400
    flash(f"{len(vacancies)} vacancies imported and submitted for developer review.", "success")
    return redirect(url_for("employer.vacancies"))


@employer_bp.get("/vacancies")
@role_required("employer")
def vacancies():
    rows = (
        get_db()
        .execute(
            "SELECT * FROM vacancies WHERE employer_id=? ORDER BY id DESC",
            (session["user_id"],),
        )
        .fetchall()
    )
    return render_template("employer/vacancies.html", vacancies=rows)


@employer_bp.route("/vacancies/<int:vacancy_id>/edit", methods=["GET", "POST"])
@role_required("employer")
def edit_vacancy(vacancy_id):
    db = get_db()
    job = db.execute(
        "SELECT * FROM vacancies WHERE id=? AND employer_id=?",
        (vacancy_id, session["user_id"]),
    ).fetchone()
    if not job:
        return render_template("404.html"), 404
    if request.method == "POST":
        data, error = vacancy_form(request.form)
        if error:
            flash(error, "error")
            return render_template("employer/edit-vacancy.html", job=job)
        try:
            db.execute(
                "UPDATE vacancies SET title=?,vacancy_type=?,description=?,location=?,salary=?,skills=?,eligibility=?,deadline=?,status='draft',moderation_status='pending',moderation_note=NULL,moderated_at=NULL WHERE id=? AND employer_id=?",
                (
                    data["title"],
                    data["vacancy_type"],
                    data["description"],
                    data["location"],
                    data["salary"],
                    data["skills"],
                    data["eligibility"],
                    data["deadline"],
                    vacancy_id,
                    session["user_id"],
                ),
            )
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            flash("The vacancy could not be updated.", "error")
            return render_template("employer/edit-vacancy.html", job=job)
        flash("Vacancy updated and resubmitted for developer review.", "success")
        return redirect(url_for("employer.vacancies"))
    return render_template("employer/edit-vacancy.html", job=job)


@employer_bp.post("/vacancies/<int:vacancy_id>/status")
@role_required("employer")
def vacancy_status(vacancy_id):
    status = request.form.get("status")
    if status not in VACANCY_STATUSES:
        return redirect(url_for("employer.vacancies"))
    db = get_db()
    job = db.execute(
        "SELECT vacancy_type,eligibility,deadline,moderation_status FROM vacancies WHERE id=? AND employer_id=?",
        (vacancy_id, session["user_id"]),
    ).fetchone()
    if not job:
        return redirect(url_for("employer.vacancies"))
    if status == "active" and job["moderation_status"] != "approved":
        flash(
            "A developer must approve this vacancy before it can be published.", "error"
        )
        return redirect(url_for("employer.vacancies"))
    if status == "active" and deadline_invalid(job["deadline"]):
        flash("The application deadline has passed or is invalid.", "error")
        return redirect(url_for("employer.vacancies"))
    if status == "active" and experience_requirement_invalid(
        job["vacancy_type"], job["eligibility"]
    ):
        flash("Entry-level Jobs cannot require prior work experience.", "error")
        return redirect(url_for("employer.vacancies"))
    db.execute(
        "UPDATE vacancies SET status=? WHERE id=? AND employer_id=?",
        (status, vacancy_id, session["user_id"]),
    )
    db.commit()
    flash(f"Vacancy marked {status}.", "success")
    return redirect(url_for("employer.vacancies"))


@employer_bp.get("/applications")
@role_required("employer")
def applications():
    rows = (
        get_db()
        .execute(
            "SELECT a.*,v.title,v.vacancy_type,u.name,u.email,sp.education,sp.skills,sp.resume_filename FROM applications a JOIN vacancies v ON v.id=a.vacancy_id JOIN users u ON u.id=a.student_id LEFT JOIN student_profiles sp ON sp.user_id=u.id WHERE v.employer_id=? ORDER BY a.id DESC",
            (session["user_id"],),
        )
        .fetchall()
    )
    return render_template("employer/applications.html", applications=rows)


@employer_bp.post("/applications/<int:application_id>/status")
@role_required("employer")
def application_status(application_id):
    status = request.form.get("status")
    if status not in APPLICATION_STATUSES:
        return redirect(url_for("employer.applications"))
    db = get_db()
    db.execute(
        "UPDATE applications SET status=? WHERE id=? AND vacancy_id IN (SELECT id FROM vacancies WHERE employer_id=?)",
        (status, application_id, session["user_id"]),
    )
    db.commit()
    flash(f"Application marked {status}.", "success")
    return redirect(request.referrer or url_for("employer.applications"))
