from functools import wraps

from flask import flash, redirect, session, url_for

from database.database import get_db


def role_required(*roles):
    """Require an authenticated user with one of the allowed roles.

    Accepts one role for backward compatibility and multiple roles for
    shared platform routes, e.g. @role_required("student", "employer").
    """
    if not roles:
        raise ValueError("role_required requires at least one role")

    allowed_roles = set(roles)

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                login_role = roles[0]
                if login_role == "admin":
                    return redirect(url_for("admin.login"))
                return redirect(url_for("auth.login", role=login_role))

            if session.get("role") not in allowed_roles:
                flash("You do not have access to this panel.", "error")
                return redirect(url_for("dashboard_redirect"))

            if session.get("role") == "employer":
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
