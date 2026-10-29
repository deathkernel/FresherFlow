from werkzeug.security import generate_password_hash

from app import create_app
from config import Config
from database.database import get_db


def csrf(client, path):
    client.get(path)
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_college_approval_workflow_and_login(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "fresherflow.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    admin_password = "admin-test-password-123"
    college_password = "college-test-password-123"
    student_password = "student-test-password-123"
    monkeypatch.setenv("FRESHERFLOW_ENV", "development")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", generate_password_hash(admin_password))

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    # The platform admin provisions the college verifier account.
    token = csrf(client, "/admin/login")
    response = client.post(
        "/admin/login",
        data={"csrf_token": token, "email": "admin@example.com", "password": admin_password},
        follow_redirects=False,
    )
    assert response.status_code == 302

    token = csrf(client, "/admin/colleges/")
    response = client.post(
        "/admin/colleges/",
        data={
            "csrf_token": token,
            "college_name": "Example Technical College",
            "verifier_name": "College Reviewer",
            "email": "reviewer@example.edu",
            "password": college_password,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    # Create a student using the same schema and authentication rules as the app.
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'student')",
            ("Test Student", "student@example.com", generate_password_hash(student_password)),
        )
        student_id = db.execute(
            "SELECT id FROM users WHERE email='student@example.com'"
        ).fetchone()["id"]
        db.execute(
            "INSERT INTO student_profiles(user_id,college,education) VALUES(?,?,?)",
            (student_id, "Example Technical College", "B.Tech"),
        )
        db.commit()

    token = csrf(client, "/login?role=student")
    response = client.post(
        "/login?role=student",
        data={"csrf_token": token, "email": "student@example.com", "password": student_password},
        follow_redirects=False,
    )
    assert response.status_code == 302

    token = csrf(client, "/student/verification")
    response = client.post(
        "/student/verification",
        data={
            "csrf_token": token,
            "college_id": "1",
            "enrollment_number": "ETC-2024-101",
            "graduation_year": "2027",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    # The college login can see and approve its own queue.
    client.get("/college/logout")  # GET is harmless; authentication is cleared by next login below only if posted.
    client.post(
        "/auth/logout",
        data={"csrf_token": csrf(client, "/login?role=student")},
        follow_redirects=False,
    )
    token = csrf(client, "/college/login")
    response = client.post(
        "/college/login",
        data={"csrf_token": token, "email": "reviewer@example.edu", "password": college_password},
        follow_redirects=False,
    )
    assert response.status_code == 302

    dashboard = client.get("/college/")
    assert dashboard.status_code == 200
    assert b"ETC-2024-101" in dashboard.data

    token = csrf(client, "/college/requests/1")
    response = client.post(
        "/college/requests/1/decision",
        data={
            "csrf_token": token,
            "decision": "college_approved",
            "note": "Enrollment confirmed in college records.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        request_row = get_db().execute(
            "SELECT status, reviewer_note FROM student_verification_requests WHERE student_id=?",
            (student_id,),
        ).fetchone()
        assert request_row["status"] == "college_approved"
        assert request_row["reviewer_note"] == "Enrollment confirmed in college records."


def test_college_panel_does_not_allow_unauthenticated_queue_access(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "fresherflow.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().get("/college/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/college/login")
