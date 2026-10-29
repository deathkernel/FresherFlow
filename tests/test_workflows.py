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
    assert response.status_code == 403
    assert b"Student accounts are created by your college." in response.data
    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM users WHERE email=?",
            ("blocked@example.com",),
        ).fetchone()[0] == 0


def test_public_student_registration_is_disabled(app):
    client = app.test_client()
    token = csrf(client, "/register")
    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "role": "student",
            "name": "Self Registered Student",
            "email": "self-register@example.edu",
            "password": "student-password-123",
            "confirm_password": "student-password-123",
        },
    )
    assert response.status_code == 403
    assert b"Student accounts are created by your college." in response.data
    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM users WHERE email=?",
            ("self-register@example.edu",),
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

def test_vacancy_moderation_change_notifies_employer(app):
    seed_employer(app)
    with app.app_context():
        db = get_db()
        employer_id = db.execute(
            "SELECT id FROM users WHERE email='employer@example.com'"
        ).fetchone()["id"]
        db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,status,moderation_status)
               VALUES(?,?,?,?,?,'active','pending')""",
            (employer_id, "Notification Role", "Entry-level Job", "A test role.", "Pune"),
        )
        vacancy_id = db.execute(
            "SELECT id FROM vacancies WHERE title='Notification Role'"
        ).fetchone()["id"]
        db.commit()

        db.execute(
            "UPDATE vacancies SET moderation_status='approved', status='active' WHERE id=?",
            (vacancy_id,),
        )
        db.commit()
        notice = db.execute(
            "SELECT title,body,kind FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (employer_id,),
        ).fetchone()
        assert notice is not None
        assert notice["title"] == "Vacancy approved"
        assert "approved" in notice["body"].lower()
        assert notice["kind"] == "vacancy"


def test_employer_can_download_only_resume_of_own_applicant(app, tmp_path):
    seed_student(app)
    seed_employer(app)
    seed_employer(app, email="other-employer@example.com")
    resume_content = b"Test resume content"
    resume_path = tmp_path / "uploads" / "test-resume.pdf"
    resume_path.parent.mkdir(parents=True, exist_ok=True)
    resume_path.write_bytes(resume_content)

    with app.app_context():
        db = get_db()
        student_id = db.execute(
            "SELECT id FROM users WHERE email='student@example.com'"
        ).fetchone()["id"]
        employer_id = db.execute(
            "SELECT id FROM users WHERE email='employer@example.com'"
        ).fetchone()["id"]
        other_employer_id = db.execute(
            "SELECT id FROM users WHERE email='other-employer@example.com'"
        ).fetchone()["id"]
        db.execute(
            "UPDATE student_profiles SET resume_filename='test-resume.pdf' WHERE user_id=?",
            (student_id,),
        )
        cur = db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,status,moderation_status)
               VALUES(?,?,?,?,?,'active','approved')""",
            (employer_id, "Applicant Role", "Entry-level Job", "A test role.", "Pune"),
        )
        application_id = db.execute(
            "INSERT INTO applications(vacancy_id,student_id) VALUES(?,?)",
            (cur.lastrowid, student_id),
        ).lastrowid
        db.commit()

    own_client = app.test_client()
    login(own_client, "employer", "employer@example.com", "employer-password-123")
    response = own_client.get(f"/employer/applications/{application_id}/resume")
    assert response.status_code == 200
    assert response.data == resume_content
    assert response.headers["Cache-Control"] == "private, no-store"

    other_client = app.test_client()
    login(other_client, "employer", "other-employer@example.com", "employer-password-123")
    response = other_client.get(f"/employer/applications/{application_id}/resume")
    assert response.status_code == 404

def test_messages_require_an_application_relationship(app):
    seed_student(app)
    seed_employer(app)
    client = app.test_client()
    login(client, "student", "student@example.com", "student-password-123")
    with app.app_context():
        employer_id = get_db().execute(
            "SELECT id FROM users WHERE email='employer@example.com'"
        ).fetchone()["id"]
    token = "test-csrf-token"
    with client.session_transaction() as session:
        session["csrf_token"] = token
    response = client.post(
        "/messages",
        data={"csrf_token": token, "recipient_id": employer_id, "body": "Hello"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0


def test_editing_verified_employer_profile_resets_verification(app):
    seed_employer(app)
    client = app.test_client()
    login(client, "employer", "employer@example.com", "employer-password-123")
    token = csrf(client, "/employer/profile")
    response = client.post(
        "/employer/profile",
        data={
            "csrf_token": token,
            "organization_name": "Changed Company Name",
            "organization_type": "Company",
            "website": "",
            "location": "Pune",
            "description": "Updated company details",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        profile = get_db().execute(
            "SELECT verification_status, verification_note, verified_at "
            "FROM employer_profiles WHERE organization_name='Changed Company Name'"
        ).fetchone()
        assert profile is not None
        assert profile["verification_status"] == "pending"
        assert profile["verified_at"] is None
        assert "re-verification" in profile["verification_note"]


def test_unverified_employer_jobs_are_hidden_from_student_dashboard(app):
    seed_student(app)
    seed_employer(app)
    with app.app_context():
        db = get_db()
        employer_id = db.execute(
            "SELECT id FROM users WHERE email='employer@example.com'"
        ).fetchone()["id"]
        db.execute(
            "UPDATE employer_profiles SET verification_status='pending', verified_at=NULL WHERE user_id=?",
            (employer_id,),
        )
        db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,status,moderation_status)
               VALUES(?,?,?,?,?,'active','approved')""",
            (employer_id, "Unverified Dashboard Role", "Entry-level Job", "A hidden role", "Pune"),
        )
        db.commit()
    client = app.test_client()
    login(client, "student", "student@example.com", "student-password-123")
    response = client.get("/student/dashboard")
    assert response.status_code == 200
    assert b"Unverified Dashboard Role" not in response.data

def test_employer_dashboard_shows_live_vacancy_count_and_excludes_expired_jobs(app):
    seed_employer(app)
    with app.app_context():
        db = get_db()
        employer_id = db.execute(
            "SELECT id FROM users WHERE email='employer@example.com'"
        ).fetchone()["id"]
        db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,deadline,status,moderation_status)
               VALUES(?,?,?,?,?,?,?,?)""",
            (employer_id, "Live Role", "Entry-level Job", "Current opening.", "Pune",
             date.today().isoformat(), "active", "approved"),
        )
        db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,deadline,status,moderation_status)
               VALUES(?,?,?,?,?,?,?,?)""",
            (employer_id, "Expired Role", "Entry-level Job", "Old opening.", "Pune",
             "2000-01-01", "active", "approved"),
        )
        db.commit()

    client = app.test_client()
    login(client, "employer", "employer@example.com", "employer-password-123")
    response = client.get("/employer/dashboard")

    assert response.status_code == 200
    assert b'<span>Live vacancies</span><strong>1</strong>' in response.data

def test_unverified_employer_cannot_receive_direct_job_application(app):
    seed_student(app)
    seed_employer(app)
    with app.app_context():
        db = get_db()
        employer_id = db.execute(
            "SELECT id FROM users WHERE email='employer@example.com'"
        ).fetchone()["id"]
        student_id = db.execute(
            "SELECT id FROM users WHERE email='student@example.com'"
        ).fetchone()["id"]
        cur = db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,deadline,status,moderation_status)
               VALUES(?,?,?,?,?,?,?,?)""",
            (employer_id, "Hidden Role", "Entry-level Job", "Not publicly visible.",
             "Pune", date.today().isoformat(), "active", "approved"),
        )
        vacancy_id = cur.lastrowid
        db.execute(
            "UPDATE employer_profiles SET verification_status='pending', verified_at=NULL WHERE user_id=?",
            (employer_id,),
        )
        db.commit()

    client = app.test_client()
    login(client, "student", "student@example.com", "student-password-123")
    token = csrf(client, "/student/jobs")
    response = client.post(
        f"/student/jobs/{vacancy_id}/apply",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM applications WHERE vacancy_id=? AND student_id=?",
            (vacancy_id, student_id),
        ).fetchone()[0] == 0


def test_live_vacancy_count_matches_dashboard_and_analytics_visibility(app):
    seed_employer(app)
    with app.app_context():
        db = get_db()
        employer_id = db.execute(
            "SELECT id FROM users WHERE email='employer@example.com'"
        ).fetchone()["id"]
        for title, deadline in (
            ("Visible Role", date.today().isoformat()),
            ("Expired Role", "2000-01-01"),
        ):
            db.execute(
                """INSERT INTO vacancies
                   (employer_id,title,vacancy_type,description,location,deadline,status,moderation_status)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (employer_id, title, "Entry-level Job", "Test vacancy.", "Pune",
                 deadline, "active", "approved"),
            )
        db.commit()

    client = app.test_client()
    login(client, "employer", "employer@example.com", "employer-password-123")
    dashboard = client.get("/employer/dashboard")
    analytics = client.get("/employer/analytics")
    assert dashboard.status_code == analytics.status_code == 200
    assert b'<span>Live vacancies</span><strong>1</strong>' in dashboard.data
    assert b'<span>Live vacancies</span><strong>1</strong>' in analytics.data

    with app.app_context():
        db = get_db()
        employer_id = db.execute(
            "SELECT id FROM users WHERE email='employer@example.com'"
        ).fetchone()["id"]
        db.execute(
            "UPDATE employer_profiles SET verification_status='pending', verified_at=NULL WHERE user_id=?",
            (employer_id,),
        )
        db.commit()
    dashboard = client.get("/employer/dashboard")
    analytics = client.get("/employer/analytics")
    assert b'<span>Live vacancies</span><strong>0</strong>' in dashboard.data
    assert b'<span>Live vacancies</span><strong>0</strong>' in analytics.data
