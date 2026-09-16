import os

DEFAULT_ADMIN_EMAIL = "admin@fresherflow.local"
DEFAULT_ADMIN_PASSWORD = "Admin@12345"


def get_admin_credentials():
    email = os.environ.get("ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL).strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
    return email, password
