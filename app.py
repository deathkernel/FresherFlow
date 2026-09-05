from flask import session
from flask import Flask, redirect, url_for, render_template
import os
from config import Config
from database.database import close_db, init_db
from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from routes.employer_routes import employer_bp


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    init_db(app.config["DATABASE"])
    app.teardown_appcontext(close_db)
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(employer_bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/dashboard")
    def dashboard_redirect():
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        return redirect(url_for("student.dashboard" if session.get("role") == "student" else "employer.dashboard"))

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
