from config import Config, get_admin_credentials
from database.database import get_db
from routes import admin_setup_routes


def csrf(client, path):
    client.get(path)
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_admin_registration_is_local_and_one_time(tmp_path, monkeypatch):
    monkeypatch.setenv("FRESHERFLOW_ENV", "development")
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.setattr(admin_setup_routes, "INSTANCE_DIR", tmp_path)
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "registration.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))

    from app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    token = csrf(client, "/admin/register")
    response = client.post(
        "/admin/register",
        data={
            "csrf_token": token,
            "admin_id": "fresh-admin",
            "password": "correct-horse-battery",
            "confirm_password": "correct-horse-battery",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/login")
    assert get_admin_credentials()[0] == "fresh-admin"
    assert client.get("/admin/register").status_code == 302


def test_admin_registration_rejects_short_or_mismatched_passwords(tmp_path, monkeypatch):
    monkeypatch.setenv("FRESHERFLOW_ENV", "development")
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.setattr(admin_setup_routes, "INSTANCE_DIR", tmp_path)
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "registration-invalid.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))

    from app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    token = csrf(client, "/admin/register")
    response = client.post(
        "/admin/register",
        data={
            "csrf_token": token,
            "admin_id": "fresh-admin",
            "password": "1234567",
            "confirm_password": "1234567",
        },
    )

    assert response.status_code == 200
    assert not (tmp_path / "admin_credentials.json").exists()


def test_admin_registration_rejects_non_loopback_client(tmp_path, monkeypatch):
    monkeypatch.setenv("FRESHERFLOW_ENV", "development")
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.setattr(admin_setup_routes, "INSTANCE_DIR", tmp_path)
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "registration-remote.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))

    from app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    client.environ_base["REMOTE_ADDR"] = "192.0.2.10"

    response = client.get("/admin/register")
    assert response.status_code == 403
    assert not (tmp_path / "admin_credentials.json").exists()

def test_admin_registration_page_loads_auth_styles_and_centered_layout(tmp_path, monkeypatch):
    monkeypatch.setenv("FRESHERFLOW_ENV", "development")
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.setattr(admin_setup_routes, "INSTANCE_DIR", tmp_path)
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "registration-ui.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))

    from app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().get("/admin/register")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'href="/static/css/auth.css"' in html
    assert 'class="auth-simple-shell admin-auth-shell"' in html
    assert 'class="auth-simple-card admin-auth-card reveal"' in html
    assert "Create admin account" in html

    css_response = app.test_client().get("/static/css/auth.css")
    assert css_response.status_code == 200
    css = css_response.get_data(as_text=True)
    assert ".admin-auth-shell" in css
    assert ".admin-auth-card" in css
    assert "@media (max-width: 520px)" in css

def test_admin_registration_accepts_eight_character_password(tmp_path, monkeypatch):
    monkeypatch.setenv("FRESHERFLOW_ENV", "development")
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.setattr(admin_setup_routes, "INSTANCE_DIR", tmp_path)
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "registration-eight-char.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))

    from app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    token = csrf(client, "/admin/register")
    response = client.post(
        "/admin/register",
        data={
            "csrf_token": token,
            "admin_id": "fresh-admin",
            "password": "Abc123!@",
            "confirm_password": "Abc123!@",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/login")
    assert (tmp_path / "admin_credentials.json").exists()
