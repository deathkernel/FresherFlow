# Simple local admin credentials for the college project.
# Environment overrides are intentionally not used here so the demo login
# remains consistent on a fresh local setup.
DEFAULT_ADMIN_EMAIL = "admin@123"
DEFAULT_ADMIN_PASSWORD_HASH = "pbkdf2:sha256:600000$fresherflow$3B6BgnhYPwjlDy87Yq/x1vzwL8LNIgws2L3EigRKMgk="


def get_admin_credentials():
    """Return the default local admin credentials as (email, password_hash)."""
    return DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD_HASH
