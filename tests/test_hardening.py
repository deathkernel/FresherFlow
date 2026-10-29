from datetime import date, timedelta
from pathlib import Path

import pytest
from werkzeug.security import check_password_hash, generate_password_hash

from app import create_app
from config import Config
from database.database import get_db


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "fresherflow.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    app = create_app()
    app.config.update(TESTING=True)
    return app


def csrf(client, path):
    client.get(path)
    with client.session_transaction() as session:
        return session["csrf_token"]


def seed_employer(app, email="employer@example.com", password="employer-password-123"):
    with app.app_context():
        db = get_db()
        cur = db.execute(
            "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
            ("Test Recruiter", email, generate_password_hash(password), "employer"),
        )
        db.execute(
            """INSERT INTO employer_profiles
            (company_id,user_id,organization_name,account_status,verification_status)
            VALUES(?,?,?,?,?)""",
            (
                f"FF-CMP-{cur.lastrowid:06d}",
                cur.lastrowid,
                "Test Company",
                "active",
                "verified",
            ),
        )
        db.commit()


def login(client, role, email, password):
    token = csrf(client, f"/login?role={role}")
    return client.post(
        f"/login?role={role}",
        data={"csrf_token": token, "email": email, "password": password},
        follow_redirects=False,
    )


def test_unauthenticated_protected_routes_keep_the_correct_login_context(app):
    client = app.test_client()

    employer = client.get("/employer/dashboard", follow_redirects=False)
    assert employer.status_code == 302
    assert employer.headers["Location"].endswith("/login?role=employer")

    student = client.get("/student/dashboard", follow_redirects=False)
    assert student.status_code == 302
    assert student.headers["Location"].endswith("/login?role=student")

    admin = client.get("/admin/", follow_redirects=False)
    assert admin.status_code == 302
    assert admin.headers["Location"].endswith("/admin/login")


def test_global_error_pages_are_branded(app):
    client = app.test_client()

    not_found = client.get("/route-that-does-not-exist")
    assert not_found.status_code == 404
    assert b"This page took a wrong turn." in not_found.data

    bad_request = client.post(
        "/login?role=student",
        data={"csrf_token": "invalid-token"},
        follow_redirects=False,
    )
    assert bad_request.status_code == 400
    assert b"Bad request" in bad_request.data


def test_employer_can_change_password_after_admin_provisioning(app):
    seed_employer(app)
    client = app.test_client()

    response = login(
        client,
        "employer",
        "employer@example.com",
        "employer-password-123",
    )
    assert response.status_code == 302

    page = client.get("/employer/password")
    assert page.status_code == 200
    assert b"Change password" in page.data

    token = csrf(client, "/employer/password")
    response = client.post(
        "/employer/password",
        data={
            "csrf_token": token,
            "current_password": "employer-password-123",
            "new_password": "replacement-password-123",
            "confirm_password": "replacement-password-123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/employer/profile")

    with app.app_context():
        row = get_db().execute(
            "SELECT password_hash FROM users WHERE email=?",
            ("employer@example.com",),
        ).fetchone()
        assert check_password_hash(row["password_hash"], "replacement-password-123")

    client.get("/employer/password")
    token = csrf(client, "/employer/password")
    response = client.post(
        "/employer/password",
        data={
            "csrf_token": token,
            "current_password": "wrong-password",
            "new_password": "replacement-password-456",
            "confirm_password": "replacement-password-456",
        },
    )
    assert response.status_code == 200
    assert b"Current password is incorrect." in response.data


def test_authenticated_admin_root_redirects_to_dashboard(app, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", generate_password_hash("a-strong-test-password"))
    client = app.test_client()

    token = csrf(client, "/admin/login")
    response = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "email": "admin@example.com",
            "password": "a-strong-test-password",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/")

    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/")


def test_admin_job_pagination_uses_filtered_match_count(app, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", generate_password_hash("a-strong-test-password"))
    seed_employer(app)
    with app.app_context():
        db = get_db()
        employer_id = db.execute(
            "SELECT id FROM users WHERE email=?", ("employer@example.com",)
        ).fetchone()["id"]
        for index in range(21):
            db.execute(
                """INSERT INTO vacancies
                   (employer_id, title, vacancy_type, description, location, status, moderation_status)
                   VALUES (?, ?, 'Entry-level Job', 'A test role', 'Pune', 'active', 'pending')""",
                (employer_id, f"Match role {index:02d}"),
            )
        db.execute(
            """INSERT INTO vacancies
               (employer_id, title, vacancy_type, description, location, status, moderation_status)
               VALUES (?, 'Unrelated role', 'Entry-level Job', 'A test role', 'Pune', 'active', 'pending')""",
            (employer_id,),
        )
        db.commit()

    client = app.test_client()
    token = csrf(client, "/admin/login")
    login_response = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "email": "admin@example.com",
            "password": "a-strong-test-password",
        },
        follow_redirects=False,
    )
    assert login_response.status_code == 302

    first_page = client.get("/admin/jobs?q=Match")
    assert first_page.status_code == 200
    assert b"21 matching vacancies" in first_page.data
    assert b"Next" in first_page.data

    last_page = client.get("/admin/jobs?q=Match&page=2")
    assert last_page.status_code == 200
    assert b"21 matching vacancies" in last_page.data
    assert b"Previous" in last_page.data
    assert b"Next" not in last_page.data

def test_admin_dashboard_live_jobs_excludes_unavailable_vacancies(app, monkeypatch):
    from datetime import date, timedelta

    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv(
        "ADMIN_PASSWORD_HASH",
        generate_password_hash("a-strong-test-password"),
    )
    seed_employer(app, email="verified@example.com")
    seed_employer(app, email="pending@example.com")
    with app.app_context():
        db = get_db()
        verified_id = db.execute(
            "SELECT id FROM users WHERE email=?", ("verified@example.com",)
        ).fetchone()["id"]
        pending_id = db.execute(
            "SELECT id FROM users WHERE email=?", ("pending@example.com",)
        ).fetchone()["id"]
        db.execute(
            "UPDATE employer_profiles SET verified_at=date('now') WHERE user_id=?",
            (verified_id,),
        )
        db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,status,moderation_status,deadline)
               VALUES(?, 'Visible role', 'Entry-level Job', 'Description', 'Pune', 'active', 'approved', ?)""",
            (verified_id, (date.today() + timedelta(days=7)).isoformat()),
        )
        db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,status,moderation_status,deadline)
               VALUES(?, 'Expired role', 'Entry-level Job', 'Description', 'Pune', 'active', 'approved', ?)""",
            (verified_id, (date.today() - timedelta(days=1)).isoformat()),
        )
        db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,status,moderation_status,deadline)
               VALUES(?, 'Unverified company role', 'Entry-level Job', 'Description', 'Pune', 'active', 'approved', ?)""",
            (pending_id, (date.today() + timedelta(days=7)).isoformat()),
        )
        db.execute(
            "UPDATE employer_profiles SET verification_status='pending' WHERE user_id=?",
            (pending_id,),
        )
        db.commit()

    import routes.admin_routes as admin_routes

    rendered_stats = {}
    real_render_template = admin_routes.render_template

    def capture_dashboard_stats(template, **context):
        if template == "admin/dashboard.html":
            rendered_stats.update(context["stats"])
        return real_render_template(template, **context)

    monkeypatch.setattr(admin_routes, "render_template", capture_dashboard_stats)

    client = app.test_client()
    token = csrf(client, "/admin/login")
    response = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "email": "admin@example.com",
            "password": "a-strong-test-password",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    dashboard = client.get("/admin/")
    assert dashboard.status_code == 200
    assert rendered_stats["live_jobs"] == 1


def test_registration_cleans_up_resume_after_database_error(app, monkeypatch):
    import sqlite3
    from io import BytesIO

    import routes.auth_routes as auth_routes

    real_get_db = auth_routes.get_db

    class FailingProfileInsert:
        def __init__(self, db):
            self.db = db

        def execute(self, sql, parameters=()):
            if sql.lstrip().startswith("INSERT INTO student_profiles"):
                raise sqlite3.OperationalError("simulated database failure")
            return self.db.execute(sql, parameters)

        def __getattr__(self, name):
            return getattr(self.db, name)

    monkeypatch.setattr(
        auth_routes,
        "get_db",
        lambda: FailingProfileInsert(real_get_db()),
    )
    client = app.test_client()
    token = csrf(client, "/register")
    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "name": "Test Student",
            "email": "student-db-error@example.com",
            "password": "student-password-123",
            "confirm_password": "student-password-123",
            "role": "student",
            "resume": (BytesIO(b"%PDF-1.7\nresume"), "resume.pdf"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    assert list(Path(app.config["UPLOAD_FOLDER"]).glob("*")) == []
    with app.app_context():
        assert get_db().execute(
            "SELECT 1 FROM users WHERE email=?",
            ("student-db-error@example.com",),
        ).fetchone() is None

