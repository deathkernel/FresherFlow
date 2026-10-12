import hmac
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

            session_role = session.get("role")
            if session_role not in allowed_roles:
                flash("You do not have access to this panel.", "error")
                return redirect(url_for("dashboard_redirect"))

            # Random per-user versions revoke other browser sessions after password changes.
            if session_role in {"student", "employer"}:
                user = get_db().execute(
                    "SELECT role, auth_version FROM users WHERE id=?",
                    (session.get("user_id"),),
                ).fetchone()
                current_version = str(user["auth_version"] or "") if user else ""
                session_version = str(session.get("auth_version") or "")
                if (
                    not user
                    or user["role"] != session_role
                    or not current_version
                    or not hmac.compare_digest(current_version, session_version)
                ):
                    session.clear()
                    flash("Your session is no longer valid. Please sign in again.", "error")
                    return redirect(url_for("auth.login", role=session_role))

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
