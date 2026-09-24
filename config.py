import os
import secrets
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)
SECRET_FILE = INSTANCE_DIR / ".secret_key"

DEFAULT_ADMIN_EMAIL = "admin@123"
DEFAULT_ADMIN_PASSWORD_HASH = "pbkdf2:sha256:600000$fresherflow$3B6BgnhYPwjlDy87Yq/x1vzwL8LNIgws2L3EigRKMgk="


def local_secret():
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text(encoding="utf-8").strip()
    value = secrets.token_hex(32)
    SECRET_FILE.write_text(value, encoding="utf-8")
    return value


def get_admin_credentials():
    """Return deterministic local credentials in development and env credentials in production."""
    if os.environ.get("FRESHERFLOW_ENV", "development").strip().lower() == "production":
        email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
        password_hash = os.environ.get("ADMIN_PASSWORD_HASH", "").strip()
        if email and password_hash:
            return email, password_hash
        return "", ""
    return DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD_HASH


class Config:
    """Application configuration with safe production defaults."""

    ENVIRONMENT = os.environ.get("FRESHERFLOW_ENV", "development").strip().lower()
    configured_secret = os.environ.get("SECRET_KEY", "").strip()
    if ENVIRONMENT == "production" and not configured_secret:
        raise RuntimeError(
            "SECRET_KEY must be configured when FRESHERFLOW_ENV=production"
        )

    SECRET_KEY = configured_secret or local_secret()
    DATABASE = str(INSTANCE_DIR / "fresherflow.db")
    UPLOAD_FOLDER = str(BASE_DIR / "uploads" / "resumes")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
