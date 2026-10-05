import sqlite3
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from database.database import get_db
from routes.decorators import role_required

platform_bp = Blueprint("platform", __name__)


@platform_bp.get("/notifications")
@role_required("student", "employer")
def notifications():
    rows = get_db().execute(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
        (session["user_id"],),
    ).fetchall()
    get_db().execute(
        "UPDATE notifications SET is_read=1 WHERE user_id=?", (session["user_id"],)
    )
    get_db().commit()
    return render_template("notifications.html", notifications=rows)


@platform_bp.post("/notifications/<int:notification_id>/read")
@role_required("student", "employer")
def notification_read(notification_id):
    db = get_db()
    db.execute(
        "UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?",
        (notification_id, session["user_id"]),
    )
    db.commit()
    return redirect(url_for("platform.notifications"))


@platform_bp.get("/messages")
@role_required("student", "employer")
def messages():
    db = get_db()
    uid = session["user_id"]
    conversations = db.execute(
        """
        SELECT other.id AS other_id, other.name AS other_name,
               MAX(m.created_at) AS last_at,
               (SELECT body FROM messages m2
                WHERE ((m2.sender_id=? AND m2.recipient_id=other.id)
                    OR (m2.sender_id=other.id AND m2.recipient_id=?))
                ORDER BY m2.created_at DESC LIMIT 1) AS last_message
        FROM messages m
        JOIN users other ON other.id=CASE WHEN m.sender_id=? THEN m.recipient_id ELSE m.sender_id END
        WHERE m.sender_id=? OR m.recipient_id=?
        GROUP BY other.id, other.name
        ORDER BY last_at DESC
        """,
        (uid, uid, uid, uid, uid),
    ).fetchall()
    selected = request.args.get("with", type=int)
    thread = []
    recipient = None
    if selected:
        recipient = db.execute(
            "SELECT id,name,role FROM users WHERE id=?", (selected,)
        ).fetchone()
        if recipient:
            thread = db.execute(
                """
                SELECT m.*, u.name AS sender_name
                FROM messages m JOIN users u ON u.id=m.sender_id
                WHERE (m.sender_id=? AND m.recipient_id=?)
                   OR (m.sender_id=? AND m.recipient_id=?)
                ORDER BY m.created_at ASC
                """,
                (uid, selected, selected, uid),
            ).fetchall()
            db.execute(
                "UPDATE messages SET is_read=1 WHERE sender_id=? AND recipient_id=?",
                (selected, uid),
            )
            db.commit()
    return render_template(
        "messages.html", conversations=conversations, thread=thread,
        recipient=recipient,
    )


@platform_bp.post("/messages")
@role_required("student", "employer")
def send_message():
    recipient_id = request.form.get("recipient_id", type=int)
    body = request.form.get("body", "").strip()
    db = get_db()
    recipient = db.execute(
        "SELECT id, role FROM users WHERE id=?", (recipient_id,)
    ).fetchone() if recipient_id else None
    if not recipient or recipient["id"] == session["user_id"] or recipient["role"] == session.get("role"):
        flash("Messages can only be sent to the other user role.", "error")
        return redirect(url_for("platform.messages"))
    if not body or len(body) > 2000:
        flash("Message must contain 1–2000 characters.", "error")
        return redirect(url_for("platform.messages", **{"with": recipient_id}))
    db.execute(
        "INSERT INTO messages(sender_id,recipient_id,body) VALUES(?,?,?)",
        (session["user_id"], recipient_id, body),
    )
    db.execute(
        "INSERT INTO notifications(user_id,title,body,kind) VALUES(?,?,?,?)",
        (recipient_id, "New message", "You received a new FresherFlow message.", "message"),
    )
    db.commit()
    return redirect(url_for("platform.messages", **{"with": recipient_id}))


@platform_bp.get("/company/<int:employer_id>")
def company(employer_id):
    db = get_db()
    company = db.execute(
        "SELECT ep.*, u.name FROM employer_profiles ep JOIN users u ON u.id=ep.user_id "
        "WHERE ep.user_id=? AND ep.account_status='active'", (employer_id,)
    ).fetchone()
    if not company:
        return render_template("404.html"), 404
    jobs = db.execute(
        "SELECT id,title,vacancy_type,location,salary,skills,deadline FROM vacancies "
        "WHERE employer_id=? AND status='active' AND moderation_status='approved' "
        "AND (deadline IS NULL OR deadline>=date('now','localtime')) ORDER BY id DESC",
        (employer_id,),
    ).fetchall()
    return render_template("company.html", company=company, jobs=jobs)


@platform_bp.get("/employer/analytics")
@role_required("employer")
def analytics():
    db = get_db()
    uid = session["user_id"]
    counts = db.execute(
        """
        SELECT
          COUNT(*) AS total,
          SUM(CASE WHEN a.status='Applied' THEN 1 ELSE 0 END) AS applied,
          SUM(CASE WHEN a.status='Shortlisted' THEN 1 ELSE 0 END) AS shortlisted,
          SUM(CASE WHEN a.status='Selected' THEN 1 ELSE 0 END) AS selected,
          SUM(CASE WHEN a.status='Rejected' THEN 1 ELSE 0 END) AS rejected
        FROM applications a JOIN vacancies v ON v.id=a.vacancy_id
        WHERE v.employer_id=?
        """, (uid,)
    ).fetchone()
    jobs = db.execute(
        "SELECT COUNT(*) total, SUM(status='active' AND moderation_status='approved') live, "
        "SUM(status='draft') drafts FROM vacancies WHERE employer_id=?", (uid,)
    ).fetchone()
    return render_template("employer/analytics.html", counts=counts, jobs=jobs)


def match_score(job_skills):
    """Return a student's percentage match against a job's required skills."""
    if not session.get("user_id") or session.get("role") != "student":
        return None
    profile = get_db().execute(
        "SELECT skills FROM student_profiles WHERE user_id=?", (session["user_id"],)
    ).fetchone()
    student_skills = {
        s.strip().lower()
        for s in (profile["skills"] if profile else "").split(",")
        if s.strip()
    }
    required = {
        s.strip().lower()
        for s in (job_skills or "").split(",")
        if s.strip()
    }
    if not required:
        return None
    return round((len(student_skills & required) / len(required)) * 100)


@platform_bp.context_processor
def platform_context():
    if not session.get("user_id"):
        return {"match_score": match_score}
    row = get_db().execute(
        "SELECT COUNT(*) AS c FROM notifications WHERE user_id=? AND is_read=0",
        (session["user_id"],),
    ).fetchone()
    return {"unread_notifications": row["c"] if row else 0, "match_score": match_score}
