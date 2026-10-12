import pytest
from flask import Flask, request

from config import Config
from database.database import get_db
from security import client_login_key, login_is_locked, record_login_failure


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "fresherflow.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    from app import create_app
    app = create_app()
    app.config.update(TESTING=True)
    return app


def test_database_defaults_are_safe(app):
    with app.app_context():
        db = get_db()
        employer_sql = db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='employer_profiles'"
        ).fetchone()["sql"]
        vacancy_sql = db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='vacancies'"
        ).fetchone()["sql"]
        assert "DEFAULT 'pending'" in employer_sql
        assert "DEFAULT 'pending'" in vacancy_sql


def test_login_attempts_lock_after_repeated_failures(app):
    with app.app_context():
        db = get_db()
        key = "test:127.0.0.1:user@example.com"
        for _ in range(4):
            record_login_failure(db, key)
            assert not login_is_locked(db, key)
        record_login_failure(db, key)
        assert login_is_locked(db, key)


def test_login_rate_limit_ignores_untrusted_forwarded_for():
    flask_app = Flask(__name__)
    with flask_app.test_request_context(
        "/login",
        environ_base={"REMOTE_ADDR": "198.51.100.25"},
        headers={"X-Forwarded-For": "203.0.113.77"},
    ):
        key = client_login_key(request, "user", "USER@example.com")

    assert key == "user:198.51.100.25:user@example.com"


def test_login_rate_limit_uses_direct_peer_without_forwarded_header():
    flask_app = Flask(__name__)
    with flask_app.test_request_context(
        "/login", environ_base={"REMOTE_ADDR": "198.51.100.25"}
    ):
        key = client_login_key(request, "admin", "admin@example.com")

    assert key == "admin:198.51.100.25:admin@example.com"


def test_security_headers_are_present(app):
    response = app.test_client().get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers


def test_audit_log_table_exists(app):
    with app.app_context():
        row = get_db().execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'"
        ).fetchone()
        assert row is not None
