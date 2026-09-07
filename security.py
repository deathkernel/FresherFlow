import secrets

from flask import abort, session

CSRF_SESSION_KEY = "csrf_token"


def csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf(token):
    expected = session.get(CSRF_SESSION_KEY)
    if not expected or not token or not secrets.compare_digest(token, expected):
        abort(400, description="Invalid form token.")
