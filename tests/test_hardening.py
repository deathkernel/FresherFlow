from datetime import date, timedelta

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
