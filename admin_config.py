import os


def get_admin_credentials():
    """Return explicitly configured admin credentials.

    Production must never fall back to a known/default password. The application
    treats missing credentials as an unavailable admin login instead.
    """
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email or not password:
        return None, None
    return email, password
