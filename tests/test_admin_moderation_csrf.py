from werkzeug.security import generate_password_hash

from app import create_app
from config import Config
from database.database import get_db


def csrf(client, path):
    client.get(path)
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_repeat_moderation_recovers_from_stale_csrf_form(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "fresherflow.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setenv("FRESHERFLOW_ENV", "development")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv(
        "ADMIN_PASSWORD_HASH",
        generate_password_hash("admin-moderation-password-123"),
    )

    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db = get_db()
        employer_id = db.execute(
            "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
            (
                "Test Recruiter",
                "employer@example.com",
                generate_password_hash("employer-password-123"),
                "employer",
            ),
        ).lastrowid
        db.execute(
            """INSERT INTO employer_profiles
               (company_id,user_id,organization_name,account_status,verification_status)
               VALUES(?,?,?,?,?)""",
            (
                f"FF-CMP-{employer_id:06d}",
                employer_id,
                "Test Company",
                "active",
                "verified",
            ),
        )
        vacancy_id = db.execute(
            """INSERT INTO vacancies
               (employer_id,title,vacancy_type,description,location,status,moderation_status)
               VALUES(?,?,?,?,?,'active','approved')""",
            (
                employer_id,
                "Previously Approved Role",
                "Entry-level Job",
                "A test vacancy.",
                "Pune",
            ),
        ).lastrowid
        db.commit()

    client = app.test_client()
    token = csrf(client, "/admin/login")
    login_response = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "email": "admin@example.com",
            "password": "admin-moderation-password-123",
        },
        follow_redirects=False,
    )
    assert login_response.status_code == 302

    detail_path = f"/admin/jobs/{vacancy_id}"
    client.get(detail_path)
    stale_response = client.post(
        f"/admin/vacancies/{vacancy_id}/moderate",
        data={"csrf_token": "stale-token", "decision": "rejected"},
        follow_redirects=False,
    )
    assert stale_response.status_code == 302
    assert stale_response.headers["Location"].endswith(detail_path)

    token = csrf(client, detail_path)
    response = client.post(
        f"/admin/vacancies/{vacancy_id}/moderate",
        data={
            "csrf_token": token,
            "decision": "rejected",
            "note": "Updated after re-review",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        vacancy = get_db().execute(
            "SELECT moderation_status, status, moderation_note "
            "FROM vacancies WHERE id=?",
            (vacancy_id,),
        ).fetchone()
        assert vacancy["moderation_status"] == "rejected"
        assert vacancy["status"] == "closed"
        assert vacancy["moderation_note"] == "Updated after re-review"
