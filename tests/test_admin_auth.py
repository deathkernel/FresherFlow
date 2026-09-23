from werkzeug.security import generate_password_hash

from admin_config import DEFAULT_ADMIN_EMAIL, get_admin_credentials
from routes.admin_routes import admin_credentials_valid


def test_admin_auth_uses_hash(monkeypatch):
    password = "a-strong-test-password"
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", generate_password_hash(password))

    email, password_hash = get_admin_credentials()
    assert email == "admin@example.com"
    assert password_hash
    assert admin_credentials_valid("admin@example.com", password)
    assert not admin_credentials_valid("admin@example.com", "wrong-password")


def test_admin_auth_uses_local_defaults_without_env(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)

    email, password_hash = get_admin_credentials()
    assert email == DEFAULT_ADMIN_EMAIL
    assert password_hash
    assert admin_credentials_valid(DEFAULT_ADMIN_EMAIL, "admin123")
    assert not admin_credentials_valid(DEFAULT_ADMIN_EMAIL, "wrong-password")
