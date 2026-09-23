import os


# Simple local admin credentials for the college project.
DEFAULT_ADMIN_EMAIL = "admin@123"
DEFAULT_ADMIN_PASSWORD_HASH = "pbkdf2:sha256:600000$fresherflow$3B6BgnhYPwjlDy87Yq/x1vzwL8LNIgws2L3EigRKMgk="


def get_admin_credentials():
    """Return admin credentials as (email, password_hash)."""
    email = os.environ.get("ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL).strip().lower()
    password_hash = os.environ.get(
        "ADMIN_PASSWORD_HASH", DEFAULT_ADMIN_PASSWORD_HASH
    ).strip()
    return email, password_hash
