import importlib

import pytest
from werkzeug.security import generate_password_hash


def test_admin_credentials_require_explicit_hash(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)

    import admin_config

    importlib.reload(admin_config)

    assert admin_config.get_admin_credentials() == (None, None)


def test_admin_credentials_load_hashed_password(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "Admin@Example.com")
    password_hash = generate_password_hash("a-strong-test-password")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", password_hash)

    import admin_config

    importlib.reload(admin_config)

    email, configured_hash = admin_config.get_admin_credentials()
    assert email == "admin@example.com"
    assert configured_hash == password_hash


def test_production_requires_secret_key(monkeypatch):
    monkeypatch.setenv("FRESHERFLOW_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    import config

    with pytest.raises(RuntimeError, match="SECRET_KEY must be configured"):
        importlib.reload(config)
