import pytest
from flask import Flask, request

from config import Config
from database.database import get_db
from security import client_login_ip_key, client_login_key, login_is_locked, record_login_failure


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



def test_stale_login_attempts_are_cleaned_during_failure_recording(app):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO auth_attempts(attempt_key,failed_count,locked_until,updated_at) VALUES(?,?,?,?)",
            ("stale:entry", 5, 1, 1),
        )
        db.commit()
        record_login_failure(db, "fresh:entry")
        stale = db.execute(
            "SELECT 1 FROM auth_attempts WHERE attempt_key='stale:entry'"
        ).fetchone()
        assert stale is None


def test_production_forces_secure_session_cookies(app, monkeypatch):
    from werkzeug.security import generate_password_hash
    from app import create_app

    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", generate_password_hash("test-admin-password"))
    monkeypatch.setattr(Config, "ENVIRONMENT", "production")
    monkeypatch.setattr(Config, "SESSION_COOKIE_SECURE", False)
    production_app = create_app()
    assert production_app.config["SESSION_COOKIE_SECURE"] is True


def test_dynamic_responses_are_not_cacheable(app):
    response = app.test_client().get("/")
    assert response.headers["Cache-Control"] == "no-store"



def test_trusted_proxy_hops_enable_client_ip_and_https_detection(app, monkeypatch):
    from app import create_app

    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
    proxy_app = create_app()
    proxy_app.config.update(TESTING=True)

    @proxy_app.get("/_proxy-audit-test")
    def proxy_audit_test():
        return f"{request.remote_addr}|{request.is_secure}|{request.host}"

    response = proxy_app.test_client().get(
        "/_proxy-audit-test",
        environ_base={"REMOTE_ADDR": "10.0.0.5"},
        headers={
            "X-Forwarded-For": "198.51.100.42",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "attacker.example",
        },
    )
    assert response.data == b"198.51.100.42|True|localhost"
    assert response.headers["Strict-Transport-Security"].startswith("max-age=")


def test_per_ip_login_throttle_counts_failures_across_identities(app):
    from flask import Flask, request

    flask_app = Flask(__name__)
    with flask_app.test_request_context(
        "/login", environ_base={"REMOTE_ADDR": "198.51.100.25"}
    ):
        ip_key = client_login_ip_key(request, "user")

    with app.app_context():
        db = get_db()
        for _ in range(19):
            record_login_failure(db, ip_key, max_failures=20)
            assert not login_is_locked(db, ip_key)
        record_login_failure(db, ip_key, max_failures=20)
        assert login_is_locked(db, ip_key)
