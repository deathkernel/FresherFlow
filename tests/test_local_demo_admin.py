from werkzeug.security import generate_password_hash

from app import create_app
from config import Config
from database.database import get_db


def csrf(client, path):
    client.get(path)
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_local_demo_admin_login_works_from_loopback(tmp_path, monkeypatch):
    monkeypatch.setenv("FRESHERFLOW_ENV", "development")
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "local-demo.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    token = csrf(client, "/admin/login")
    response = client.post(
        "/admin/login",
        data={"csrf_token": token, "email": "admin123", "password": "admin123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/")


def test_local_demo_admin_login_is_rejected_from_non_loopback(tmp_path, monkeypatch):
    monkeypatch.setenv("FRESHERFLOW_ENV", "development")
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "remote-demo.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    client.environ_base["REMOTE_ADDR"] = "192.0.2.10"

    token = csrf(client, "/admin/login")
    response = client.post(
        "/admin/login",
        data={"csrf_token": token, "email": "admin123", "password": "admin123"},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"Invalid admin credentials." in response.data


def test_production_does_not_fall_back_to_demo_admin(monkeypatch):
    monkeypatch.setenv("FRESHERFLOW_ENV", "production")
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)

    from config import get_admin_credentials

    assert get_admin_credentials() == ("", "")
