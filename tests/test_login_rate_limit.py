import sqlite3
from types import SimpleNamespace

import security


def make_db():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute(
        """CREATE TABLE auth_attempts (
            attempt_key TEXT PRIMARY KEY,
            failed_count INTEGER NOT NULL DEFAULT 0,
            locked_until INTEGER NOT NULL DEFAULT 0,
            updated_at INTEGER NOT NULL
        )"""
    )
    return db


def test_client_login_key_ignores_spoofed_forwarded_for():
    request = SimpleNamespace(
        remote_addr="203.0.113.10",
        headers={"X-Forwarded-For": "198.51.100.99"},
    )

    key = security.client_login_key(request, "student", "  USER@Example.COM ")

    assert key == "student:203.0.113.10:user@example.com"
    assert "198.51.100.99" not in key


def test_login_locks_after_maximum_failures(monkeypatch):
    now = 1_000
    monkeypatch.setattr(security.time, "time", lambda: now)
    db = make_db()
    key = "student:203.0.113.10:user@example.com"

    for _ in range(security.LOGIN_MAX_FAILURES):
        security.record_login_failure(db, key)

    row = db.execute(
        "SELECT failed_count, locked_until FROM auth_attempts WHERE attempt_key=?",
        (key,),
    ).fetchone()
    assert row["failed_count"] == security.LOGIN_MAX_FAILURES
    assert row["locked_until"] == now + security.LOGIN_LOCK_SECONDS
    assert security.login_is_locked(db, key)


def test_login_lock_expires(monkeypatch):
    now = 1_000
    monkeypatch.setattr(security.time, "time", lambda: now)
    db = make_db()
    key = "employer:203.0.113.10:employer@example.com"

    for _ in range(security.LOGIN_MAX_FAILURES):
        security.record_login_failure(db, key)

    now += security.LOGIN_LOCK_SECONDS
    assert not security.login_is_locked(db, key)


def test_expired_login_window_is_removed(monkeypatch):
    now = 1_000
    monkeypatch.setattr(security.time, "time", lambda: now)
    db = make_db()
    key = "student:203.0.113.10:user@example.com"
    security.record_login_failure(db, key)

    now += security.LOGIN_WINDOW_SECONDS + 1
    assert not security.login_is_locked(db, key)
    assert db.execute(
        "SELECT 1 FROM auth_attempts WHERE attempt_key=?", (key,)
    ).fetchone() is None


def test_successful_login_clears_failures(monkeypatch):
    monkeypatch.setattr(security.time, "time", lambda: 1_000)
    db = make_db()
    key = "student:203.0.113.10:user@example.com"
    security.record_login_failure(db, key)

    security.clear_login_failures(db, key)

    assert db.execute(
        "SELECT 1 FROM auth_attempts WHERE attempt_key=?", (key,)
    ).fetchone() is None
