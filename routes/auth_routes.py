import sqlite3
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from database.database import get_db

auth_bp = Blueprint("auth", __name__)
ALLOWED_RESUME_EXTENSIONS = {"pdf", "doc", "docx"}
MIN_PASSWORD_LENGTH = 12


def allowed_resume(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_RESUME_EXTENSIONS


def login_target(role):
    return {"student": "student.dashboard", "employer": "employer.dashboard"}.get(role, "auth.login")


def render_login():
    context = request.args.get("role", "student")
    if context not in {"student", "employer"}:
        context = "student"
    return render_template("login.html", login_context=context)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    login_context = request.args.get("role", "student")
    if login_context not in {"student", "employer"}:
        login_context = "student"

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=? AND role IN ('student','employer')", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            if user["role"] == "employer":
                profile = db.execute("SELECT account_status, verification_status FROM employer_profiles WHERE user_id=?", (user["id"],)).fetchone()
                if profile and profile["account_status"] == "suspended":
                    flash("This employer account is currently suspended. Please contact support.", "error")
                    return render_template("login.html", login_context=login_context)
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            session.permanent = True
            return redirect(url_for(login_target(user["role"])))

        flash("Invalid email or password.", "error")
        return render_template("login.html", login_context=login_context)

    return render_login()


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        form = request.form
        name = form.get("name", "").strip()
        email = form.get("email", "").strip().lower()
        password = form.get("password", "")
        confirm_password = form.get("confirm_password", "")
        role = form.get("role", "student")
        if not name or not email or len(password) < MIN_PASSWORD_LENGTH or password != confirm_password or role not in {"student", "employer"}:
            flash(f"Please complete the form and use a password of at least {MIN_PASSWORD_LENGTH} characters.", "error")
            selected_role = role if role in {"student", "employer"} else "student"
            return render_template("register.html", selected_role=selected_role)
        db = get_db(); resume_path = None
        try:
            cur = db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)", (name, email, generate_password_hash(password), role))
            user_id = cur.lastrowid
            if role == "student":
                resume = request.files.get("resume"); resume_filename = None
                if resume and resume.filename:
                    if not allowed_resume(resume.filename):
                        db.rollback(); flash("Resume must be a PDF, DOC or DOCX file.", "error"); return render_template("register.html", selected_role="student")
                    resume_filename = f"{user_id}_{secure_filename(resume.filename)}"
                    upload_dir = Path(current_app.config["UPLOAD_FOLDER"]); upload_dir.mkdir(parents=True, exist_ok=True)
                    resume_path = upload_dir / resume_filename; resume.save(resume_path)
                db.execute("""INSERT INTO student_profiles
                    (user_id,phone,education,college,graduation_year,skills,certifications,preferred_job_type,preferred_location,resume_filename,profile_strength)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (user_id, form.get("phone", "").strip(), form.get("education", "").strip(), form.get("college", "").strip(), form.get("graduation_year", "").strip(), form.get("skills", "").strip(), form.get("certifications", "").strip(), form.get("preferred_job_type", "Both"), form.get("preferred_location", "").strip(), resume_filename, 100 if resume_filename else 80))
            else:
                organization = form.get("organization_name", "").strip() or name
                db.execute("""INSERT INTO employer_profiles(user_id,organization_name,organization_type,website,location,description,account_status,verification_status)
                    VALUES(?,?,?,?,?,?,?,?)""", (user_id, organization, form.get("organization_type", "").strip(), form.get("website", "").strip(), form.get("location", "").strip(), form.get("description", "").strip(), "active", "pending"))
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            if resume_path: resume_path.unlink(missing_ok=True)
            flash("That email is already registered or the submitted data is invalid.", "error"); return render_template("register.html", selected_role=role if role in {"student", "employer"} else "student")
        except OSError:
            db.rollback()
            if resume_path: resume_path.unlink(missing_ok=True)
            current_app.logger.exception("Resume upload failed during registration")
            flash("The resume could not be saved. Please try again.", "error"); return render_template("register.html", selected_role="student")
        flash("Account created. Please sign in.", "success")
        return redirect(url_for("auth.login"))
    selected_role = request.args.get("role", "student")
    if selected_role not in {"student", "employer"}: selected_role = "student"
    return render_template("register.html", selected_role=selected_role)


@auth_bp.post("/logout")
def logout():
    session.clear(); flash("You have been logged out.", "success"); return redirect(url_for("index"))
