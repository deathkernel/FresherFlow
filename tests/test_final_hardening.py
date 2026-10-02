import pytest

from config import Config
from database.database import get_db
from security import login_is_locked, record_login_failure


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
