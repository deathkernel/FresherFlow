import os
import secrets
from datetime import timedelta
from pathlib import Path

from werkzeug.security import generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
SECRET_FILE = INSTANCE_DIR / ".secret_key"
_LOCAL_DEMO_ADMIN_PASSWORD_HASH = generate_password_hash("admin123")

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
    environment = os.environ.get("FRESHERFLOW_ENV", "development").strip().lower()

    # Legacy local placeholder values are not real credentials. Ignore them
    # outside production so first-time local registration can take precedence.
    legacy_local_placeholder = (
        environment != "production"
        and email == "admin123"
        and password_hash == "admin123"
    )

    if email and password_hash and not legacy_local_placeholder:
        return email, password_hash
    if (email or password_hash) and not legacy_local_placeholder:
        return "", ""

    if environment != "production":
        # A locally registered account takes precedence over the demo fallback.
        try:
            from routes.admin_setup_routes import local_admin_credentials

            registered = local_admin_credentials()
            if registered:
                return registered
        except (ImportError, OSError, ValueError):
            pass
        # Local development convenience only. Never enable in production.
        return "admin123", _LOCAL_DEMO_ADMIN_PASSWORD_HASH

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
    # Bound in-memory form parsing as well as the total request body. The part
    # count stays high enough for the supported 100-vacancy bulk form workflow.
    MAX_FORM_MEMORY_SIZE = 500_000
    MAX_FORM_PARTS = 1000

    SEND_FILE_MAX_AGE_DEFAULT = 3600

    # The __Host- prefix requires Secure, Path=/ and no Domain attribute.
    # It prevents sibling subdomains from setting an overriding session cookie.
    SESSION_COOKIE_NAME = "__Host-fresherflow_session" if ENVIRONMENT == "production" else "session"
    SESSION_COOKIE_PATH = "/"
    SESSION_COOKIE_DOMAIN = None
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (
        ENVIRONMENT == "production"
        or os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    )
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
