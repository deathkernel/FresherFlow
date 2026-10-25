import json
import os
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from config import INSTANCE_DIR
from database.database import get_db
from security import clear_login_failures, client_login_key

admin_setup_bp = Blueprint("admin_setup", __name__, url_prefix="/admin")


def _credentials_file():
    return Path(INSTANCE_DIR) / "admin_credentials.json"


def _loopback_only():
    return request.remote_addr in {"127.0.0.1", "::1"}


def _setup_available():
    if current_app.config.get("ENVIRONMENT") == "production":
        return False

    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password_hash = os.environ.get("ADMIN_PASSWORD_HASH", "").strip()
    legacy_local_placeholder = email == "admin123" and password_hash == "admin123"
    if (email or password_hash) and not legacy_local_placeholder:
        return False

    return not _credentials_file().exists()


@admin_setup_bp.route("/register", methods=["GET", "POST"])
def register():
    if not _loopback_only():
        return render_template(
            "error.html",
            status_code=403,
            title="Local setup only",
            message="Administrator registration is available only from this computer.",
        ), 403

    if not _setup_available():
        flash("Administrator registration is already closed. Please sign in.", "info")
        return redirect(url_for("admin.login"))

    if request.method == "POST":
        admin_id = request.form.get("admin_id", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not admin_id or len(admin_id) > 64 or any(ch.isspace() for ch in admin_id):
            flash("Admin ID is required and must be 1–64 characters without spaces.", "error")
        elif len(password) < 12:
            flash("Choose a password with at least 12 characters.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        else:
            path = _credentials_file()
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "admin_id": admin_id,
                "password_hash": generate_password_hash(password),
            }
            try:
                # Exclusive creation makes registration one-time even if two
                # local requests arrive at nearly the same time.
                with path.open("x", encoding="utf-8") as handle:
                    json.dump(payload, handle)
                    handle.write("\\n")
            except FileExistsError:
                flash("Administrator registration has already been completed.", "error")
                return redirect(url_for("admin.login"))

            db = get_db()
            clear_login_failures(db, client_login_key(request, "admin", admin_id))
            flash("Administrator account created. You can now sign in.", "success")
            return redirect(url_for("admin.login"))

    return render_template("admin/register.html")


def local_admin_credentials():
    """Read one-time local setup credentials; never used in production."""
    if os.environ.get("FRESHERFLOW_ENV", "development").strip().lower() == "production":
        return None
    path = _credentials_file()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        admin_id = str(payload.get("admin_id", "")).strip().lower()
        password_hash = str(payload.get("password_hash", "")).strip()
        if admin_id and password_hash:
            return admin_id, password_hash
    except (OSError, ValueError, TypeError):
        return None
    return None
