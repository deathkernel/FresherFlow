from functools import wraps
from flask import session, redirect, url_for, flash

from database.database import get_db


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                target = "admin.login" if role == "admin" else "auth.login"
                if role != "admin":
                    return redirect(url_for(target, role=role))
                return redirect(url_for(target))
            if session.get("role") != role:
                flash("You do not have access to this panel.", "error")
                return redirect(url_for("dashboard_redirect"))
            if role == "employer":
                profile = get_db().execute(
                    "SELECT account_status FROM employer_profiles WHERE user_id=?",
                    (session["user_id"],),
                ).fetchone()
                if not profile or profile["account_status"] != "active":
                    session.clear()
                    flash("This employer account is no longer active.", "error")
                    return redirect(url_for("auth.login", role="employer"))
            return view(*args, **kwargs)

        return wrapped

    return decorator
