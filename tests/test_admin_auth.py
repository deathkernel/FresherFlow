from werkzeug.security import generate_password_hash

from admin_config import get_admin_credentials
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


def test_admin_auth_is_disabled_without_credentials(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)

    assert not admin_credentials_valid("admin@example.com", "anything")
