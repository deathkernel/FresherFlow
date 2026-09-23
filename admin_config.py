import os

DEFAULT_ADMIN_EMAIL = "admin@123"
DEFAULT_ADMIN_PASSWORD_HASH = "pbkdf2:sha256:600000$fresherflow$3B6BgnhYPwjlDy87Yq/x1vzwL8LNIgws2L3EigRKMgk="


def get_admin_credentials():
    """Return explicitly configured credentials, or the local project defaults."""
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password_hash = os.environ.get("ADMIN_PASSWORD_HASH", "").strip()
    if email and password_hash:
        return email, password_hash
    return DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD_HASH
