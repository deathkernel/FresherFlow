from werkzeug.security import generate_password_hash

from app import create_app
from config import Config
from database.database import get_db


def make_app(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "sessions.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db = get_db()
        user = db.execute(
            "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
            ("Test Recruiter", "session@example.com", generate_password_hash("old-password-123"), "employer"),
        )
        user_id = user.lastrowid
        db.execute(
            """INSERT INTO employer_profiles
               (company_id,user_id,organization_name,account_status,verification_status)
               VALUES(?,?,?,?,?)""",
            (f"FF-CMP-{user_id:06d}", user_id, "Session Company", "active", "verified"),
        )
        db.commit()
    return app


def login(client):
    client.get("/login?role=employer")
    with client.session_transaction() as session:
        token = session["csrf_token"]
    return client.post(
        "/login?role=employer",
        data={
            "csrf_token": token,
            "email": "session@example.com",
            "password": "old-password-123",
        },
    )


def test_password_change_revokes_other_sessions_but_keeps_current_one(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    first = app.test_client()
    second = app.test_client()
    assert login(first).status_code == 302
    assert login(second).status_code == 302

    first.get("/employer/password")
    with first.session_transaction() as session:
        token = session["csrf_token"]
    changed = first.post(
        "/employer/password",
        data={
            "csrf_token": token,
            "current_password": "old-password-123",
            "new_password": "new-password-456",
            "confirm_password": "new-password-456",
        },
        follow_redirects=False,
    )
    assert changed.status_code == 302
    assert first.get("/employer/profile").status_code == 200

    stale = second.get("/employer/profile", follow_redirects=False)
    assert stale.status_code == 302
    assert "/login?role=employer" in stale.headers["Location"]
    with second.session_transaction() as session:
        assert "user_id" not in session
