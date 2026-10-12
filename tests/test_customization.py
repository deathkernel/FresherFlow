import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from config import Config
from database.database import get_db


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "fresherflow.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    application = create_app()
    application.config.update(TESTING=True)
    return application


def token_for(client, path):
    client.get(path)
    with client.session_transaction() as session:
        return session["csrf_token"]


def seed_student(app):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
            ("Test Student", "student@example.com",
             generate_password_hash("student-password-123"), "student"),
        )
        user_id = db.execute(
            "SELECT id FROM users WHERE email=?", ("student@example.com",)
        ).fetchone()["id"]
        db.execute(
            "INSERT INTO student_profiles(user_id,education,college) VALUES(?,?,?)",
            (user_id, "BCA", "Test College"),
        )
        db.commit()


def login_student(client):
    token = token_for(client, "/login?role=student")
    return client.post("/login?role=student", data={
        "csrf_token": token,
        "email": "student@example.com",
        "password": "student-password-123",
    })


def test_settings_preferences_persist(app):
    seed_student(app)
    client = app.test_client()
    login_student(client)
    token = token_for(client, "/settings")
    response = client.post("/settings", data={
        "csrf_token": token, "theme": "dark", "font_scale": "large",
        "reduce_motion": "on", "notify_application": "on",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Your preferences have been saved." in response.data
    assert b'data-theme="dark"' in response.data
    assert b'data-font-scale="large"' in response.data
    with app.app_context():
        row = get_db().execute(
            "SELECT theme,font_scale,reduce_motion,notify_application,notify_message "
            "FROM user_preferences WHERE user_id=(SELECT id FROM users WHERE email=?)",
            ("student@example.com",),
        ).fetchone()
        assert tuple(row) == ("dark", "large", 1, 1, 0)


def test_settings_requires_authentication(app):
    response = app.test_client().get("/settings")
    assert response.status_code == 302


def test_student_can_change_password_and_invalidates_old_sessions(app):
    seed_student(app)
    client = app.test_client()
    login_student(client)
    token = token_for(client, "/student/change-password")
    response = client.post("/student/change-password", data={
        "csrf_token": token,
        "current_password": "student-password-123",
        "new_password": "new-student-password-456",
        "confirm_password": "new-student-password-456",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Password changed successfully." in response.data
    with app.app_context():
        row = get_db().execute(
            "SELECT password_hash FROM users WHERE email=?",
            ("student@example.com",),
        ).fetchone()
        from werkzeug.security import check_password_hash
        assert check_password_hash(row["password_hash"], "new-student-password-456")


def test_application_notifications_respect_preferences(app):
    seed_student(app)
    with app.app_context():
        db = get_db()
        employer_id = db.execute(
            "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
            ("Test Employer", "employer@example.com",
             generate_password_hash("employer-password-123"), "employer"),
        ).lastrowid
        db.execute(
            """INSERT INTO employer_profiles
               (company_id,user_id,organization_name,account_status,verification_status)
               VALUES(?,?,?,?,?)""",
            (f"FF-CMP-{employer_id:06d}", employer_id, "Test Company", "active", "verified"),
        )
        student_id = db.execute(
            "SELECT id FROM users WHERE email=?", ("student@example.com",)
        ).fetchone()["id"]
        db.execute(
            "INSERT INTO user_preferences(user_id,notify_application) VALUES(?,0)",
            (student_id,),
        )
        db.execute(
            "INSERT INTO user_preferences(user_id,notify_application) VALUES(?,0)",
            (employer_id,),
        )
        vacancy_id = db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,status,moderation_status)
               VALUES(?,?,?,?,?,'active','approved')""",
            (employer_id, "Junior Developer", "Entry-level Job",
             "A test vacancy", "Remote"),
        ).lastrowid
        db.execute(
            "INSERT INTO applications(vacancy_id,student_id) VALUES(?,?)",
            (vacancy_id, student_id),
        )
        db.commit()
        count = db.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id IN (?,?)",
            (student_id, employer_id),
        ).fetchone()[0]
        assert count == 0
