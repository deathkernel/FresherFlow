from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from database.database import get_db

auth_bp = Blueprint("auth", __name__)
ALLOWED_RESUME_EXTENSIONS = {"pdf", "doc", "docx"}


def allowed_resume(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_RESUME_EXTENSIONS


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")
        session.clear()
        session["user_id"] = user["id"]
        session["name"] = user["name"]
        session["role"] = user["role"]
        return redirect(url_for("student.dashboard" if user["role"] == "student" else "employer.dashboard"))
    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        form = request.form
        name = form.get("name", "").strip()
        email = form.get("email", "").strip().lower()
        password = form.get("password", "")
        confirm_password = form.get("confirm_password", "")
        role = form.get("role", "student")

        if not name or not email or len(password) < 6 or password != confirm_password or role not in {"student", "employer"}:
            flash("Please complete the form and make sure both passwords match.", "error")
            return render_template("register.html")

        db = get_db()
        try:
            cur = db.execute(
                "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                (name, email, generate_password_hash(password), role),
            )
            user_id = cur.lastrowid

            if role == "student":
                resume = request.files.get("resume")
                resume_filename = None
                if resume and resume.filename:
                    if not allowed_resume(resume.filename):
                        db.rollback()
                        flash("Resume must be a PDF, DOC or DOCX file.", "error")
                        return render_template("register.html")
                    resume_filename = f"{user_id}_{secure_filename(resume.filename)}"
                    Path(current_app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
                    resume.save(Path(current_app.config["UPLOAD_FOLDER"]) / resume_filename)

                db.execute(
                    """INSERT INTO student_profiles
                    (user_id,phone,education,college,graduation_year,skills,certifications,preferred_job_type,preferred_location,resume_filename,profile_strength)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        user_id,
                        form.get("phone", "").strip(),
                        form.get("education", "").strip(),
                        form.get("college", "").strip(),
                        form.get("graduation_year", "").strip(),
                        form.get("skills", "").strip(),
                        form.get("certifications", "").strip(),
                        form.get("preferred_job_type", "Both"),
                        form.get("preferred_location", "").strip(),
                        resume_filename,
                        100 if resume_filename else 80,
                    ),
                )
            else:
                organization = form.get("organization_name", "").strip() or name
                db.execute(
                    """INSERT INTO employer_profiles(user_id,organization_name,organization_type,website,location,description)
                    VALUES(?,?,?,?,?,?)""",
                    (
                        user_id,
                        organization,
                        form.get("organization_type", "").strip(),
                        form.get("website", "").strip(),
                        form.get("location", "").strip(),
                        form.get("description", "").strip(),
                    ),
                )
            db.commit()
        except Exception:
            db.rollback()
            flash("That email is already registered or the submitted data is invalid.", "error")
            return render_template("register.html")

        flash("Account created. Please sign in.", "success")
        return redirect(url_for("auth.login"))

    selected_role = request.args.get("role", "student")
    if selected_role not in {"student", "employer"}:
        selected_role = "student"
    return render_template("register.html", selected_role=selected_role)


@auth_bp.get("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))
