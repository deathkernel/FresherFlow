import os


# Simple local admin credentials for the college project.
# Environment variables can still override these values.
DEFAULT_ADMIN_EMAIL = "admin@fresherflow.local"
DEFAULT_ADMIN_PASSWORD_HASH = "pbkdf2:sha256:600000$44cb4d5236eb290a$6w1jNTj2Rg1GKUuR0wPSY9zzLq9Fr2rpujyFSZKrH4w="


def get_admin_credentials():
    """Return admin credentials as (email, password_hash)."""
    email = os.environ.get("ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL).strip().lower()
    password_hash = os.environ.get(
        "ADMIN_PASSWORD_HASH", DEFAULT_ADMIN_PASSWORD_HASH
    ).strip()
    return email, password_hash
