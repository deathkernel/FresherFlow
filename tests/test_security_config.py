import importlib

import pytest
from werkzeug.security import generate_password_hash


def test_admin_credentials_are_not_defaulted_in_development(monkeypatch):
    monkeypatch.setenv("FRESHERFLOW_ENV", "development")
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)

    import config
    importlib.reload(config)

    assert config.get_admin_credentials() == ("", "")

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


def test_admin_credentials_are_disabled_outside_development(monkeypatch):
    monkeypatch.setenv("FRESHERFLOW_ENV", "staging")
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)

    import config
    importlib.reload(config)
    assert config.get_admin_credentials() == ("", "")



def test_production_rejects_short_secret_key():
    import os
    import subprocess
    import sys

    environment = os.environ.copy()
    environment["FRESHERFLOW_ENV"] = "production"
    environment["SECRET_KEY"] = "too-short"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, "-c", "import config"],
        env=environment,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode != 0
    assert "at least 32 characters" in result.stderr
