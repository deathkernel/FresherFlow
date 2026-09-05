from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from database.database import get_db

auth_bp = Blueprint("auth", __name__)

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
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")
        if not name or not email or len(password) < 6 or role not in {"student", "employer"}:
            flash("Please complete all fields. Password must be at least 6 characters.", "error")
            return render_template("register.html")
        db = get_db()
        try:
            cur = db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)", (name, email, generate_password_hash(password), role))
            user_id = cur.lastrowid
            if role == "student":
                db.execute("INSERT INTO student_profiles(user_id) VALUES(?)", (user_id,))
            else:
                db.execute("INSERT INTO employer_profiles(user_id,organization_name) VALUES(?,?)", (user_id, name))
            db.commit()
        except Exception:
            db.rollback()
            flash("That email is already registered.", "error")
            return render_template("register.html")
        flash("Account created. Please sign in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("register.html")

@auth_bp.get("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))
