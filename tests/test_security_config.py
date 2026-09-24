import importlib

import pytest
from werkzeug.security import generate_password_hash


def test_admin_credentials_use_local_defaults(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)

    import config

    importlib.reload(config)

    email, password_hash = config.get_admin_credentials()
    assert email == "admin@123"
    assert password_hash


def test_admin_credentials_load_hashed_password(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "Admin@Example.com")
    password_hash = generate_password_hash("a-strong-test-password")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", password_hash)

    import config

    importlib.reload(config)

    email, configured_hash = config.get_admin_credentials()
    assert email == "admin@example.com"
    assert configured_hash == password_hash


def test_production_requires_secret_key(monkeypatch):
    monkeypatch.setenv("FRESHERFLOW_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    import config

    with pytest.raises(RuntimeError, match="SECRET_KEY must be configured"):
        importlib.reload(config)
