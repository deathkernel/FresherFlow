import os
import secrets
from datetime import timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
SECRET_FILE = INSTANCE_DIR / ".secret_key"

INSTANCE_DIR.mkdir(exist_ok=True)


def local_secret():
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text(encoding="utf-8").strip()

    value = secrets.token_hex(32)
    SECRET_FILE.write_text(value, encoding="utf-8")
    return value


def get_admin_credentials():
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password_hash = os.environ.get("ADMIN_PASSWORD_HASH", "").strip()

    if email and password_hash:
        return email, password_hash

    # Never ship or silently enable a default administrator account.
    return "", ""


class Config:
    ENVIRONMENT = os.environ.get("FRESHERFLOW_ENV", "development").strip().lower()
    configured_secret = os.environ.get("SECRET_KEY", "").strip()

    if ENVIRONMENT == "production" and not configured_secret:
        raise RuntimeError(
            "SECRET_KEY must be configured when FRESHERFLOW_ENV=production"
        )
    if ENVIRONMENT == "production" and len(configured_secret) < 32:
        raise RuntimeError(
            "SECRET_KEY must be at least 32 characters in production"
        )

    SECRET_KEY = configured_secret or local_secret()
    DATABASE = str(INSTANCE_DIR / "fresherflow.db")
    SEO_BASE_URL = os.environ.get("SEO_BASE_URL", "").strip().rstrip("/")
    UPLOAD_FOLDER = str(BASE_DIR / "uploads" / "resumes")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    # Assets are not fingerprinted; keep cache short to limit stale deployments.
    SEND_FILE_MAX_AGE_DEFAULT = 3600

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Production cookies must always be HTTPS-only; an env override must not
    # silently weaken this setting.
    SESSION_COOKIE_SECURE = (
        ENVIRONMENT == "production"
        or os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    )
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
