from datetime import date
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

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


def seed_student(app, email="student@example.com", password="student-password-123"):
    with app.app_context():
        db = get_db()
        cur = db.execute(
            "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
            ("Test Student", email, generate_password_hash(password), "student"),
        )
        db.execute(
            "INSERT INTO student_profiles(user_id,education,college) VALUES(?,?,?)",
            (cur.lastrowid, "B.Voc Software Development", "Test College"),
        )
        db.commit()


def seed_employer(
    app,
    email="employer@example.com",
    password="employer-password-123",
):
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
            (f"FF-CMP-{cur.lastrowid:06d}", cur.lastrowid, "Test Company", "active", "verified"),
        )
        db.commit()


def login(client, role, email, password):
    token = csrf(client, f"/login?role={role}")
    return client.post(
        f"/login?role={role}",
        data={"csrf_token": token, "email": email, "password": password},
        follow_redirects=False,
    )


def test_public_registration_rejects_employer_role(app):
    client = app.test_client()
    token = csrf(client, "/register")
    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "role": "employer",
            "name": "Blocked Recruiter",
            "email": "blocked@example.com",
            "password": "blocked-password-123",
            "confirm_password": "blocked-password-123",
        },
    )
    assert response.status_code == 200
    assert b"Employer accounts can only be created by an administrator." in response.data
    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM users WHERE email=?",
            ("blocked@example.com",),
        ).fetchone()[0] == 0


def test_login_context_enforces_role(app):
    seed_student(app)
    seed_employer(app)
    client = app.test_client()

    response = login(client, "student", "employer@example.com", "employer-password-123")
    assert response.status_code == 200
    assert b"Invalid email or password." in response.data

    response = login(client, "employer", "employer@example.com", "employer-password-123")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/employer/dashboard")


def test_publish_action_creates_active_pending_vacancy(app):
    seed_employer(app)
    client = app.test_client()
    response = login(client, "employer", "employer@example.com", "employer-password-123")
    assert response.status_code == 302

    token = csrf(client, "/employer/vacancies/new")
    response = client.post(
        "/employer/vacancies/new",
        data={
            "csrf_token": token,
            "title": "Python Developer",
            "vacancy_type": "Entry-level Job",
            "location": "Pune",
            "salary": "₹6 LPA",
            "skills": "Python, Flask",
            "eligibility": "Freshers welcome",
            "deadline": date.today().isoformat(),
            "description": "Build web applications.",
            "publish": "1",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        vacancy = get_db().execute(
            "SELECT status, moderation_status FROM vacancies ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert vacancy["status"] == "active"
        assert vacancy["moderation_status"] == "pending"


def test_closing_approved_vacancy_preserves_moderation_state(app):
    seed_employer(app)
    with app.app_context():
        db = get_db()
        employer_id = db.execute(
            "SELECT user_id FROM employer_profiles WHERE organization_name=?",
            ("Test Company",),
        ).fetchone()["user_id"]
        db.execute(
            """INSERT INTO vacancies
            (employer_id,title,vacancy_type,description,location,status,moderation_status)
            VALUES(?,?,?,?,?,?,?)""",
            (
                employer_id,
                "Approved Role",
                "Entry-level Job",
                "A valid job.",
                "Pune",
                "active",
                "approved",
            ),
        )
        db.commit()
        vacancy_id = db.execute(
            "SELECT id FROM vacancies ORDER BY id DESC LIMIT 1"
        ).fetchone()["id"]

    client = app.test_client()
    login(client, "employer", "employer@example.com", "employer-password-123")
    token = csrf(client, "/employer/vacancies")
    response = client.post(
        f"/employer/vacancies/{vacancy_id}/status",
        data={"csrf_token": token, "status": "closed"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        vacancy = get_db().execute(
            "SELECT status, moderation_status FROM vacancies WHERE id=?",
            (vacancy_id,),
        ).fetchone()
        assert vacancy["status"] == "closed"
        assert vacancy["moderation_status"] == "approved"


def test_expired_job_is_not_reachable_from_student_details(app):
    seed_student(app)
    seed_employer(app)
    with app.app_context():
        db = get_db()
        employer_id = db.execute(
            "SELECT user_id FROM employer_profiles WHERE organization_name=?",
            ("Test Company",),
        ).fetchone()["user_id"]
        db.execute(
            """INSERT INTO vacancies
            (employer_id,title,vacancy_type,description,location,deadline,status,moderation_status)
            VALUES(?,?,?,?,?,?,?,?)""",
            (
                employer_id,
                "Expired Role",
                "Entry-level Job",
                "Expired opportunity.",
                "Pune",
                "2000-01-01",
                "active",
                "approved",
            ),
        )
        db.commit()
        vacancy_id = db.execute(
            "SELECT id FROM vacancies ORDER BY id DESC LIMIT 1"
        ).fetchone()["id"]

    client = app.test_client()
    login(client, "student", "student@example.com", "student-password-123")
    response = client.get(f"/student/jobs/{vacancy_id}")
    assert response.status_code == 404
