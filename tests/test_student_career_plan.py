from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from config import Config
from database.database import get_db


def csrf(client, path):
    client.get(path)
    with client.session_transaction() as session:
        return session["csrf_token"]


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


def student_client(app, email, password):
    client = app.test_client()
    token = csrf(client, "/login?role=student")
    response = client.post(
        "/login?role=student",
        data={"csrf_token": token, "email": email, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 302
    return client


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


def test_student_career_checklist_task_lifecycle_and_ownership(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    student_id = add_student(app, "First Student", "first@example.edu", "student-password-123")
    add_student(app, "Other Student", "other@example.edu", "other-password-123")
    client = student_client(app, "first@example.edu", "student-password-123")
    other_client = student_client(app, "other@example.edu", "other-password-123")

    page = client.get("/student/career-plan")
    assert page.status_code == 200
    assert b"My career checklist" in page.data

    token = csrf(client, "/student/career-plan")
    invalid = client.post(
        "/student/career-plan",
        data={"csrf_token": token, "title": "Invalid date", "target_date": "not-a-date"},
        follow_redirects=False,
    )
    assert invalid.status_code == 302
    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM career_tasks WHERE student_id=?", (student_id,)
        ).fetchone()[0] == 0

    target_date = (date.today() + timedelta(days=7)).isoformat()
    token = csrf(client, "/student/career-plan")
    response = client.post(
        "/student/career-plan",
        data={
            "csrf_token": token,
            "title": "Practise Python questions",
            "notes": "Revise loops, functions and exceptions",
            "target_date": target_date,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        task = get_db().execute(
            "SELECT * FROM career_tasks WHERE student_id=?", (student_id,)
        ).fetchone()
        assert task["title"] == "Practise Python questions"
        assert task["target_date"] == target_date
        task_id = task["id"]

    token = csrf(other_client, "/student/career-plan")
    assert other_client.post(
        f"/student/career-plan/{task_id}/toggle",
        data={"csrf_token": token},
        follow_redirects=False,
    ).status_code == 404
    assert other_client.post(
        f"/student/career-plan/{task_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    ).status_code == 404

    token = csrf(client, "/student/career-plan")
    response = client.post(
        f"/student/career-plan/{task_id}/toggle",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        task = get_db().execute(
            "SELECT is_completed, completed_at FROM career_tasks WHERE id=? AND student_id=?",
            (task_id, student_id),
        ).fetchone()
        assert task["is_completed"] == 1
        assert task["completed_at"]

    assert b"Completed" in client.get("/student/career-plan").data
    token = csrf(client, "/student/career-plan")
    response = client.post(
        f"/student/career-plan/{task_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM career_tasks WHERE id=?", (task_id,)
        ).fetchone()[0] == 0


def test_career_checklist_requires_student_login(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    response = app.test_client().get("/student/career-plan", follow_redirects=False)
    assert response.status_code == 302
