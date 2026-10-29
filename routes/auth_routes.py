from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from database.database import get_db
from security import (
    client_login_ip_key,
    client_login_key,
    clear_login_failures,
    login_is_locked,
    record_login_failure,
)


auth_bp = Blueprint("auth", __name__)


def login_target(role):
    targets = {
        "student": "student.dashboard",
        "employer": "employer.dashboard",
    }
    return targets.get(role, "auth.login")


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
        login_key = client_login_key(request, "user", email)
        ip_key = client_login_ip_key(request, "user")
        if login_is_locked(db, login_key) or login_is_locked(db, ip_key):
            flash("Too many failed attempts. Please try again in a few minutes.", "error")
            return render_template("login.html", login_context=login_context)
        user = db.execute(
            "SELECT * FROM users WHERE email=? AND role=?",
            (email, login_context),
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            if user["role"] == "employer":
                profile = db.execute(
                    "SELECT account_status FROM employer_profiles WHERE user_id=?",
                    (user["id"],),
                ).fetchone()
                if profile and profile["account_status"] == "suspended":
                    flash(
                        "This employer account is currently suspended. Please contact support.",
                        "error",
                    )
                    return render_template(
                        "login.html", login_context=login_context
                    )

            clear_login_failures(db, login_key)
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            session["auth_version"] = user["auth_version"]
            session.permanent = True
            return redirect(url_for(login_target(user["role"])))

        record_login_failure(db, login_key)
        record_login_failure(db, ip_key, max_failures=20)
        flash("Invalid email or password.", "error")
        return render_template("login.html", login_context=login_context)

    return render_login()


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        flash(
            "Student accounts are created by your college. Please contact your college representative.",
            "error",
        )
        return render_template("register.html"), 403
    return render_template("register.html")


@auth_bp.post("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))
