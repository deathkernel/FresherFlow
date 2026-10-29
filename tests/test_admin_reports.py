import csv
import io
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from config import Config
from database.database import get_db


def csrf(client, path):
    client.get(path)
    with client.session_transaction() as session:
        return session["csrf_token"]


def admin_client(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "fresherflow.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setattr(
        Config,
        "VERIFICATION_UPLOAD_FOLDER",
        str(tmp_path / "verification-documents"),
    )
    password = "admin-reports-test-password-123"
    monkeypatch.setenv("FRESHERFLOW_ENV", "development")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", generate_password_hash(password))
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    token = csrf(client, "/admin/login")
    response = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "email": "admin@example.com",
            "password": password,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    return app, client


def seed_report_data(app):
    with app.app_context():
        db = get_db()
        student_id = db.execute(
            "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'student')",
            ("=2+2", "student@example.edu", generate_password_hash("student-test-password")),
        ).lastrowid
        db.execute(
            "INSERT INTO student_profiles(user_id,college,education) VALUES(?,?,?)",
            (student_id, "Example College", "B.Voc Software Development"),
        )
        employer_id = db.execute(
            "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'employer')",
            ("Hiring Team", "hr@example.com", generate_password_hash("employer-test-password")),
        ).lastrowid
        db.execute(
            """INSERT INTO employer_profiles
               (user_id,company_id,organization_name,account_status,
                verification_status,verified_at)
               VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)""",
            (employer_id, "FF-CMP-REPORT01", "Example Company", "active", "verified"),
        )
        vacancy_id = db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,status,
                moderation_status,deadline,vacancy_code)
               VALUES(?,?,?,?,?,'active','approved',?,?)""",
            (
                employer_id,
                "Junior Developer",
                "Entry-level Job",
                "A report test vacancy",
                "Pune",
                date.today().isoformat(),
                "FF-JOB-REPORT01",
            ),
        ).lastrowid
        db.execute(
            "INSERT INTO applications(vacancy_id,student_id,status) VALUES(?,?,'Applied')",
            (vacancy_id, student_id),
        )
        college_id = db.execute(
            "INSERT INTO colleges(name) VALUES(?)",
            ("Example College",),
        ).lastrowid
        db.execute(
            """INSERT INTO student_verification_requests
               (student_id,college_id,enrollment_number,graduation_year)
               VALUES(?,?,?,?)""",
            (student_id, college_id, "EC-2026-001", "2027"),
        )
        db.commit()


def test_admin_reports_export_filtered_csv_and_log_export(tmp_path, monkeypatch):
    app, client = admin_client(tmp_path, monkeypatch)
    seed_report_data(app)

    page = client.get("/admin/reports?report=applications")
    assert page.status_code == 200
    assert b"Reports &amp; exports" in page.data
    assert b"1" in page.data

    response = client.get("/admin/reports/export.csv?report=applications")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment; filename=\"fresherflow_applications.csv\"" == response.headers["Content-Disposition"]
    assert response.headers["Cache-Control"] == "private, no-store"
    parsed = list(csv.reader(io.StringIO(response.get_data(as_text=True))))
    assert parsed[0][0] == "Application ID"
    assert parsed[1][1] == "'=2+2"
    assert parsed[1][2] == "student@example.edu"
    assert parsed[1][4] == "Junior Developer"

    future = (date.today() + timedelta(days=2)).isoformat()
    filtered = client.get(
        f"/admin/reports/export.csv?report=applications&from_date={future}&to_date={future}"
    )
    assert filtered.status_code == 200
    filtered_rows = list(csv.reader(io.StringIO(filtered.get_data(as_text=True))))
    assert len(filtered_rows) == 1

    vacancies = client.get("/admin/reports/export.csv?report=vacancies")
    assert vacancies.status_code == 200
    assert b"FF-JOB-REPORT01" in vacancies.data

    college = client.get("/admin/reports/export.csv?report=college-verifications")
    assert college.status_code == 200
    assert b"EC-2026-001" in college.data

    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM audit_log WHERE action='export_admin_report'"
        ).fetchone()[0] == 4


def test_admin_reports_validate_filters_and_require_admin(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "fresherflow.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setattr(
        Config,
        "VERIFICATION_UPLOAD_FOLDER",
        str(tmp_path / "verification-documents"),
    )
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    assert client.get("/admin/reports/export.csv", follow_redirects=False).status_code == 302

    admin_app, admin = admin_client(tmp_path / "logged-in", monkeypatch)
    assert admin.get("/admin/reports/export.csv?report=unknown").status_code == 400
    assert admin.get(
        "/admin/reports?report=applications&from_date=2026-13-40"
    ).status_code == 400
    assert admin.get(
        "/admin/reports?report=applications&from_date=2026-11-20&to_date=2026-11-01"
    ).status_code == 400
