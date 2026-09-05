from functools import wraps
from flask import session, redirect, url_for, flash


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("auth.login"))
            if session.get("role") != role:
                flash("You do not have access to this panel.", "error")
                return redirect(url_for("dashboard_redirect"))
            return view(*args, **kwargs)
        return wrapped
    return decorator
