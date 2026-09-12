import os

from flask import Flask, redirect, render_template, request, session, url_for

from config import Config
from database.database import close_db, init_db
from routes.auth_routes import auth_bp
from routes.employer_routes import employer_bp
from routes.student_routes import student_bp
from security import csrf_token, validate_csrf


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    init_db(app.config["DATABASE"])
    app.teardown_appcontext(close_db)
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def protect_forms():
        if request.method == "POST":
            validate_csrf(request.form.get("csrf_token"))

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; font-src 'self' https://cdn.jsdelivr.net; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'")
        if request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(employer_bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/student-panel")
    def student_panel():
        if session.get("user_id") and session.get("role") == "student":
            return redirect(url_for("student.dashboard"))
        return redirect(url_for("auth.login", role="student"))

    @app.get("/employer-panel")
    def employer_panel():
        if session.get("user_id") and session.get("role") == "employer":
            return redirect(url_for("employer.dashboard"))
        return redirect(url_for("auth.login", role="employer"))

    @app.get("/dashboard")
    def dashboard_redirect():
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        role = session.get("role")
        targets = {"student": "student.dashboard", "employer": "employer.dashboard"}
        return redirect(url_for(targets.get(role, "auth.login")))

    return app


app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print("\nFresherFlow is running:")
    print(f"  Student Panel : http://127.0.0.1:{port}/student-panel")
    print(f"  Employer Panel: http://127.0.0.1:{port}/employer-panel")
    print("\nBoth panels use the same FresherFlow backend/database, while role-based access keeps their experiences separate.\n")
    app.run(host=host, port=port, debug=debug)
