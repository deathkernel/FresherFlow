from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from config import Config
from database.database import get_db


def csrf(client, path):
    client.get(path)
    with client.session_transaction() as session:
        return session["csrf_token"]


def make_app(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "fresherflow.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setattr(
        Config, "VERIFICATION_UPLOAD_FOLDER", str(tmp_path / "verification-documents")
    )
    monkeypatch.setenv("FRESHERFLOW_ENV", "development")
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    app = create_app()
    app.config.update(TESTING=True)
    return app


def add_student(app, name, email, password):
    with app.app_context():
        db = get_db()
        user_id = db.execute(
            "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'student')",
            (name, email, generate_password_hash(password)),
        ).lastrowid
        db.execute("INSERT INTO student_profiles(user_id) VALUES(?)", (user_id,))
        db.commit()
    return user_id


def add_employer(app, name, email, password, company_id):
    with app.app_context():
        db = get_db()
        user_id = db.execute(
            "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'employer')",
            (name, email, generate_password_hash(password)),
        ).lastrowid
        db.execute(
            """INSERT INTO employer_profiles
               (user_id,company_id,organization_name,account_status,verification_status,verified_at)
               VALUES(?,?,?,'active','verified',CURRENT_TIMESTAMP)""",
            (user_id, company_id, name),
        )
        db.commit()
    return user_id


def login(client, role, email, password):
    token = csrf(client, f"/login?role={role}")
    response = client.post(
        f"/login?role={role}",
        data={"csrf_token": token, "email": email, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 302


def test_employer_schedules_reschedules_and_cancels_interview(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    student_id = add_student(app, "Interview Candidate", "candidate@example.edu", "student-password-123")
    employer_id = add_employer(app, "Example Employer", "employer@example.com", "employer-password-123", "FF-CMP-INTERVIEW1")
    add_employer(app, "Other Employer", "other-employer@example.com", "other-password-123", "FF-CMP-INTERVIEW2")
    with app.app_context():
        db = get_db()
        vacancy_id = db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,status,moderation_status)
               VALUES(?,?,?,?,?,'active','approved')""",
            (employer_id, "Junior Developer", "Entry-level Job", "Interview test", "Pune"),
        ).lastrowid
        application_id = db.execute(
            "INSERT INTO applications(vacancy_id,student_id,status) VALUES(?,?,'Applied')",
            (vacancy_id, student_id),
        ).lastrowid
        db.commit()

    employer = app.test_client()
    login(employer, "employer", "employer@example.com", "employer-password-123")
    page = employer.get(f"/employer/applications/{application_id}/interview")
    assert page.status_code == 200
    assert b"Schedule interview" in page.data

    past = (datetime.now() - timedelta(days=1)).replace(second=0, microsecond=0).isoformat(timespec="minutes")
    token = csrf(employer, f"/employer/applications/{application_id}/interview")
    invalid = employer.post(
        f"/employer/applications/{application_id}/interview",
        data={"csrf_token": token, "scheduled_at": past, "mode": "Online", "meeting_url": "https://meet.example.com/room"},
        follow_redirects=False,
    )
    assert invalid.status_code == 302
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM interviews").fetchone()[0] == 0

    scheduled = (datetime.now() + timedelta(days=1)).replace(second=0, microsecond=0).isoformat(timespec="minutes")
    token = csrf(employer, f"/employer/applications/{application_id}/interview")
    response = employer.post(
        f"/employer/applications/{application_id}/interview",
        data={
            "csrf_token": token,
            "scheduled_at": scheduled,
            "mode": "Online",
            "meeting_url": "https://meet.example.com/room",
            "notes": "Prepare a short code walkthrough.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        interview = get_db().execute(
            "SELECT * FROM interviews WHERE application_id=?", (application_id,)
        ).fetchone()
        assert interview["status"] == "scheduled"
        assert interview["mode"] == "Online"
        assert interview["meeting_url"] == "https://meet.example.com/room"
        assert get_db().execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND kind='interview'",
            (student_id,),
        ).fetchone()[0] == 1

    other = app.test_client()
    login(other, "employer", "other-employer@example.com", "other-password-123")
    assert other.get(
        f"/employer/applications/{application_id}/interview", follow_redirects=False
    ).status_code == 404

    rescheduled = (datetime.now() + timedelta(days=2)).replace(second=0, microsecond=0).isoformat(timespec="minutes")
    token = csrf(employer, f"/employer/applications/{application_id}/interview")
    response = employer.post(
        f"/employer/applications/{application_id}/interview",
        data={
            "csrf_token": token,
            "scheduled_at": rescheduled,
            "mode": "In-person",
            "location": "Pune office, reception desk",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM interviews WHERE application_id=?", (application_id,)
        ).fetchone()[0] == 1
        assert get_db().execute(
            "SELECT scheduled_at, mode FROM interviews WHERE application_id=?",
            (application_id,),
        ).fetchone()["mode"] == "In-person"

    token = csrf(employer, f"/employer/applications/{application_id}/interview")
    response = employer.post(
        f"/employer/applications/{application_id}/interview/cancel",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        assert get_db().execute(
            "SELECT status FROM interviews WHERE application_id=?", (application_id,)
        ).fetchone()["status"] == "cancelled"
        assert get_db().execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND kind='interview'",
            (student_id,),
        ).fetchone()[0] == 3

    student = app.test_client()
    login(student, "student", "candidate@example.edu", "student-password-123")
    student_page = student.get("/student/interviews")
    assert student_page.status_code == 200
    assert b"Junior Developer" in student_page.data
    assert b"Cancelled" in student_page.data


def test_interview_schedule_requires_employer_login(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    response = app.test_client().get("/employer/applications/1/interview", follow_redirects=False)
    assert response.status_code == 302
