import os

from config import DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD_HASH, get_admin_credentials as _get_admin_credentials


def get_admin_credentials():
    return _get_admin_credentials()
