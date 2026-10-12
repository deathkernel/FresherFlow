from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from database.database import get_db
from routes.decorators import role_required

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings", methods=["GET", "POST"])
@role_required("student", "employer")
def preferences():
    db = get_db()
    user_id = session["user_id"]
    db.execute(
        "INSERT OR IGNORE INTO user_preferences(user_id) VALUES(?)", (user_id,)
    )
    db.commit()

    if request.method == "POST":
        theme = request.form.get("theme", "light")
        font_scale = request.form.get("font_scale", "normal")
        if theme not in {"light", "dark", "system"}:
            theme = "light"
        if font_scale not in {"normal", "large"}:
            font_scale = "normal"
        reduce_motion = int(request.form.get("reduce_motion") == "on")
        notify_application = int(request.form.get("notify_application") == "on")
        notify_message = int(request.form.get("notify_message") == "on")
        notify_vacancy = int(request.form.get("notify_vacancy") == "on")
        db.execute(
            """UPDATE user_preferences SET theme=?, font_scale=?, reduce_motion=?,
               notify_application=?, notify_message=?, notify_vacancy=?,
               updated_at=CURRENT_TIMESTAMP WHERE user_id=?""",
            (theme, font_scale, reduce_motion, notify_application,
             notify_message, notify_vacancy, user_id),
        )
        db.commit()
        flash("Your preferences have been saved.", "success")
        return redirect(url_for("settings.preferences"))

    preferences = db.execute(
        "SELECT * FROM user_preferences WHERE user_id=?", (user_id,)
    ).fetchone()
    return render_template("settings.html", preferences=preferences)


@settings_bp.app_context_processor
def user_preferences_context():
    defaults = {
        "theme": "light", "font_scale": "normal", "reduce_motion": 0,
        "notify_application": 1, "notify_message": 1, "notify_vacancy": 1,
    }
    user_id = session.get("user_id")
    if not user_id:
        return {"user_preferences": defaults}
    row = get_db().execute(
        "SELECT theme, font_scale, reduce_motion, notify_application, "
        "notify_message, notify_vacancy FROM user_preferences WHERE user_id=?",
        (user_id,),
    ).fetchone()
    if not row:
        return {"user_preferences": defaults}
    return {"user_preferences": dict(row)}
