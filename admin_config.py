import os


def get_admin_credentials():
    """Return explicitly configured admin credentials as (email, password_hash).

    The admin password must be supplied as a Werkzeug password hash. There is
    deliberately no default credential and no plaintext-password fallback.
    """
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password_hash = os.environ.get("ADMIN_PASSWORD_HASH", "").strip()
    if not email or not password_hash:
        return None, None
    return email, password_hash
