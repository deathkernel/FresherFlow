import secrets
import time
from pathlib import Path
from urllib.parse import urlparse
from zipfile import BadZipFile, ZipFile


from flask import abort, session

CSRF_SESSION_KEY = "csrf_token"
ALLOWED_RESUME_EXTENSIONS = {"pdf", "doc", "docx"}
MAX_RESUME_BYTES = 5 * 1024 * 1024
LOGIN_MAX_FAILURES = 5
LOGIN_LOCK_SECONDS = 300
LOGIN_WINDOW_SECONDS = 900


def csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if token:
        return token

    token = secrets.token_urlsafe(32)
    session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf(token):
    expected = session.get(CSRF_SESSION_KEY)
    if not expected or not token or not secrets.compare_digest(token, expected):
        abort(400, description="Invalid form token.")


def valid_resume_upload(file_storage):
    """Validate resume size, extension and container/file signatures."""
    if not file_storage or not file_storage.filename:
        return False

    filename = Path(file_storage.filename).name
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_RESUME_EXTENSIONS:
        return False

    stream = file_storage.stream
    position = stream.tell()
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(0)
    header = stream.read(8)
    stream.seek(position)

    if size <= 0 or size > MAX_RESUME_BYTES:
        return False
    if extension == "pdf":
        return header.startswith(b"%PDF-")
    if extension == "doc":
        return header == bytes.fromhex("D0CF11E0A1B11AE1")
    if not header.startswith(b"PK\x03\x04"):
        return False

    stream.seek(0)
    try:
        with ZipFile(stream) as archive:
            names = archive.namelist()
            if not names or any(
                name.startswith(("/", "\\")) or ".." in Path(name).parts
                for name in names
            ):
                return False
            required = {"[Content_Types].xml", "word/document.xml"}
            if not required.issubset(names):
                return False
            if any(info.file_size > MAX_RESUME_BYTES for info in archive.infolist()):
                return False
    except (BadZipFile, OSError, ValueError):
        return False
    finally:
        stream.seek(position)

    return True


def login_is_locked(db, key):
    now = int(time.time())
    row = db.execute(
        "SELECT failed_count, locked_until, updated_at FROM auth_attempts WHERE attempt_key=?",
        (key,),
    ).fetchone()
    if not row:
        return False

    updated_at = int(row["updated_at"])
    locked_until = int(row["locked_until"])
    if updated_at + LOGIN_WINDOW_SECONDS < now:
        db.execute("DELETE FROM auth_attempts WHERE attempt_key=?", (key,))
        db.commit()
        return False
    return locked_until > now


def record_login_failure(db, key):
    now = int(time.time())
    row = db.execute(
        "SELECT failed_count, updated_at FROM auth_attempts WHERE attempt_key=?",
        (key,),
    ).fetchone()
    failures = 1 if not row or int(row["updated_at"]) + LOGIN_WINDOW_SECONDS < now else int(row["failed_count"]) + 1
    locked_until = now + LOGIN_LOCK_SECONDS if failures >= LOGIN_MAX_FAILURES else 0
    db.execute(
        """INSERT INTO auth_attempts(attempt_key, failed_count, locked_until, updated_at)
           VALUES(?,?,?,?)
           ON CONFLICT(attempt_key) DO UPDATE SET
             failed_count=excluded.failed_count,
             locked_until=excluded.locked_until,
             updated_at=excluded.updated_at""",
        (key, failures, locked_until, now),
    )
    db.commit()


def clear_login_failures(db, key):
    db.execute("DELETE FROM auth_attempts WHERE attempt_key=?", (key,))
    db.commit()


def client_login_key(request, scope, identity):
    """Create a bounded rate-limit key from scope, IP and supplied identity."""
    remote = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
    ip = remote.split(",", 1)[0].strip()
    normalized = (identity or "").strip().lower()
    return f"{scope}:{ip}:{normalized}"

def valid_website_url(value):
    """Return True only for absolute HTTP(S) URLs."""
    value = (value or "").strip()
    if not value:
        return True

    try:
        parsed = urlparse(value)
    except ValueError:
        return False

    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
