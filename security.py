import secrets
from pathlib import Path
from urllib.parse import urlparse

from flask import abort, session

CSRF_SESSION_KEY = "csrf_token"
ALLOWED_RESUME_EXTENSIONS = {"pdf", "doc", "docx"}
MAX_RESUME_BYTES = 5 * 1024 * 1024


def csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf(token):
    expected = session.get(CSRF_SESSION_KEY)
    if not expected or not token or not secrets.compare_digest(token, expected):
        abort(400, description="Invalid form token.")


def valid_resume_upload(file_storage):
    """Validate resume extension, size and common file signatures."""
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
    if extension == "docx":
        return header.startswith(b"PK\x03\x04")

    return header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")


def valid_website_url(value):
    """Allow only absolute HTTP(S) website URLs."""
    value = (value or "").strip()
    if not value:
        return True
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
