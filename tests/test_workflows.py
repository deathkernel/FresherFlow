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
            (company_id,user_id,organization_name,account_status,verification_status,verified_at)
            VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)""",
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



def test_getting_notifications_does_not_mark_them_read(app):
    seed_student(app)
    with app.app_context():
        db = get_db()
        student_id = db.execute(
            "SELECT id FROM users WHERE email='student@example.com'"
        ).fetchone()["id"]
        db.execute(
            "INSERT INTO notifications(user_id,title,body) VALUES(?,?,?)",
            (student_id, "Test update", "Unread notification"),
        )
        db.commit()

    client = app.test_client()
    login(client, "student", "student@example.com", "student-password-123")
    response = client.get("/notifications")
    assert response.status_code == 200
    with app.app_context():
        assert get_db().execute(
            "SELECT is_read FROM notifications WHERE title='Test update'"
        ).fetchone()["is_read"] == 0

    with client.session_transaction() as session:
        token = session["csrf_token"]
    response = client.post(
        "/notifications/read-all",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        assert get_db().execute(
            "SELECT is_read FROM notifications WHERE title='Test update'"
        ).fetchone()["is_read"] == 1


def test_getting_message_thread_does_not_mark_messages_read(app):
    seed_student(app)
    seed_employer(app)
    with app.app_context():
        db = get_db()
        student_id = db.execute(
            "SELECT id FROM users WHERE email='student@example.com'"
        ).fetchone()["id"]
        employer_id = db.execute(
            "SELECT id FROM users WHERE email='employer@example.com'"
        ).fetchone()["id"]
        db.execute(
            "INSERT INTO messages(sender_id,recipient_id,body) VALUES(?,?,?)",
            (employer_id, student_id, "Unread message"),
        )
        db.commit()

    client = app.test_client()
    login(client, "student", "student@example.com", "student-password-123")
    response = client.get(f"/messages?with={employer_id}")
    assert response.status_code == 200
    with app.app_context():
        assert get_db().execute(
            "SELECT is_read FROM messages WHERE body='Unread message'"
        ).fetchone()["is_read"] == 0

    with client.session_transaction() as session:
        token = session["csrf_token"]
    response = client.post(
        "/messages/read",
        data={"csrf_token": token, "recipient_id": str(employer_id)},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        assert get_db().execute(
            "SELECT is_read FROM messages WHERE body='Unread message'"
        ).fetchone()["is_read"] == 1


def test_employer_cannot_edit_another_employers_vacancy(app):
    seed_employer(app, email="owner@example.com")
    seed_employer(app, email="other-owner@example.com")
    with app.app_context():
        db = get_db()
        other_id = db.execute(
            "SELECT id FROM users WHERE email=?", ("other-owner@example.com",)
        ).fetchone()["id"]
        db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,status,moderation_status)
               VALUES(?,?,?,?,?,?,?)""",
            (other_id, "Private Vacancy", "Entry-level Job", "Private description",
             "Pune", "active", "approved"),
        )
        db.commit()
        vacancy_id = db.execute(
            "SELECT id FROM vacancies WHERE employer_id=?", (other_id,)
        ).fetchone()["id"]

    client = app.test_client()
    login(client, "employer", "owner@example.com", "employer-password-123")
    response = client.get(f"/employer/vacancies/{vacancy_id}/edit")
    assert response.status_code == 404

    with app.app_context():
        row = get_db().execute(
            "SELECT title FROM vacancies WHERE id=?", (vacancy_id,)
        ).fetchone()
        assert row["title"] == "Private Vacancy"


def test_employer_cannot_change_another_employers_application_status(app):
    seed_student(app)
    seed_employer(app, email="owner@example.com")
    seed_employer(app, email="other-owner@example.com")
    with app.app_context():
        db = get_db()
        student_id = db.execute(
            "SELECT id FROM users WHERE email=?", ("student@example.com",)
        ).fetchone()["id"]
        other_id = db.execute(
            "SELECT id FROM users WHERE email=?", ("other-owner@example.com",)
        ).fetchone()["id"]
        cursor = db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,status,moderation_status)
               VALUES(?,?,?,?,?,?,?)""",
            (other_id, "Other Company's Role", "Entry-level Job", "Description",
             "Pune", "active", "approved"),
        )
        db.execute(
            "INSERT INTO applications(vacancy_id,student_id,status) VALUES(?,?,?)",
            (cursor.lastrowid, student_id, "Applied"),
        )
        db.commit()
        application_id = db.execute(
            "SELECT id FROM applications WHERE vacancy_id=?", (cursor.lastrowid,)
        ).fetchone()["id"]

    client = app.test_client()
    login(client, "employer", "owner@example.com", "employer-password-123")
    token = csrf(client, "/employer/applications")
    response = client.post(
        f"/employer/applications/{application_id}/status",
        data={"csrf_token": token, "status": "Selected"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        row = get_db().execute(
            "SELECT status FROM applications WHERE id=?", (application_id,)
        ).fetchone()
        assert row["status"] == "Applied"


def test_student_cannot_access_employer_dashboard(app):
    seed_student(app)
    client = app.test_client()
    login(client, "student", "student@example.com", "student-password-123")

    response = client.get("/employer/dashboard", follow_redirects=False)

    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]

def test_message_sender_is_rate_limited_to_reduce_spam(app):
    seed_student(app)
    seed_employer(app)
    with app.app_context():
        db = get_db()
        student_id = db.execute(
            "SELECT id FROM users WHERE email=?", ("student@example.com",)
        ).fetchone()["id"]
        employer_id = db.execute(
            "SELECT id FROM users WHERE email=?", ("employer@example.com",)
        ).fetchone()["id"]
        db.executemany(
            "INSERT INTO messages(sender_id,recipient_id,body) VALUES(?,?,?)",
            [
                (student_id, employer_id, f"Existing message {index}")
                for index in range(20)
            ],
        )
        db.commit()

    client = app.test_client()
    login(client, "student", "student@example.com", "student-password-123")
    token = csrf(client, f"/messages?with={employer_id}")
    response = client.post(
        "/messages",
        data={
            "csrf_token": token,
            "recipient_id": str(employer_id),
            "body": "This message should be rate limited.",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"too many messages" in response.data.lower()

    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM messages WHERE sender_id=?", (student_id,)
        ).fetchone()[0] == 20

def seed_application_relationship(
    app,
    student_email="student@example.com",
    employer_email="employer@example.com",
):
    with app.app_context():
        db = get_db()
        student_id = db.execute(
            "SELECT id FROM users WHERE email=?", (student_email,)
        ).fetchone()["id"]
        employer_id = db.execute(
            "SELECT id FROM users WHERE email=?", (employer_email,)
        ).fetchone()["id"]
        cursor = db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,status,moderation_status)
               VALUES(?,?,?,?,?,?,?)""",
            (
                employer_id,
                "Applicant Contact Role",
                "Entry-level Job",
                "A role for messaging authorization tests.",
                "Pune",
                "active",
                "approved",
            ),
        )
        db.execute(
            "INSERT INTO applications(vacancy_id,student_id,status) VALUES(?,?,?)",
            (cursor.lastrowid, student_id, "Applied"),
        )
        db.commit()


def test_user_cannot_start_message_conversation_without_application(app):
    seed_student(app)
    seed_employer(app)
    client = app.test_client()
    login(client, "student", "student@example.com", "student-password-123")
    with app.app_context():
        employer_id = get_db().execute(
            "SELECT id FROM users WHERE email=?", ("employer@example.com",)
        ).fetchone()["id"]
    token = csrf(client, "/notifications")
    response = client.post(
        "/messages",
        data={
            "csrf_token": token,
            "recipient_id": str(employer_id),
            "body": "Hello, please contact me.",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"after applying to one of their jobs" in response.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0


def test_student_can_start_message_after_applying_to_verified_employer(app):
    seed_student(app)
    seed_employer(app)
    seed_application_relationship(app)
    client = app.test_client()
    login(client, "student", "student@example.com", "student-password-123")
    with app.app_context():
        employer_id = get_db().execute(
            "SELECT id FROM users WHERE email=?", ("employer@example.com",)
        ).fetchone()["id"]
    token = csrf(client, "/notifications")
    response = client.post(
        "/messages",
        data={
            "csrf_token": token,
            "recipient_id": str(employer_id),
            "body": "Hello, I applied for your role.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        row = get_db().execute(
            "SELECT sender_id, recipient_id, body FROM messages"
        ).fetchone()
        assert row["body"] == "Hello, I applied for your role."
        assert row["recipient_id"] == employer_id


def test_employer_can_message_student_who_applied_to_its_job(app):
    seed_student(app)
    seed_employer(app)
    seed_application_relationship(app)
    client = app.test_client()
    login(client, "employer", "employer@example.com", "employer-password-123")
    with app.app_context():
        student_id = get_db().execute(
            "SELECT id FROM users WHERE email=?", ("student@example.com",)
        ).fetchone()["id"]
    token = csrf(client, "/notifications")
    response = client.post(
        "/messages",
        data={
            "csrf_token": token,
            "recipient_id": str(student_id),
            "body": "Thanks for applying. We will review your profile.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        row = get_db().execute(
            "SELECT sender_id, recipient_id, body FROM messages"
        ).fetchone()
        assert row["body"] == "Thanks for applying. We will review your profile."
        assert row["sender_id"] != row["recipient_id"]

