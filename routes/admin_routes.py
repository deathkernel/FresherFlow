from datetime import datetime, timezone
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from database.database import get_db
from routes.decorators import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def log_action(db, action, target_type=None, target_id=None, details=None):
    db.execute("INSERT INTO admin_activity(admin_id,action,target_type,target_id,details) VALUES(?,?,?,?,?)", (session["user_id"], action, target_type, target_id, details))

def back(endpoint):
    return redirect(request.referrer or url_for(endpoint))

@admin_bp.get("/dashboard")
@role_required("admin")
def dashboard():
    db=get_db()
    stats={
        "students":db.execute("SELECT COUNT(*) c FROM users WHERE role='student'").fetchone()["c"],
        "employers":db.execute("SELECT COUNT(*) c FROM users WHERE role='employer'").fetchone()["c"],
        "pending_employers":db.execute("SELECT COUNT(*) c FROM employer_profiles WHERE verification_status='pending'").fetchone()["c"],
        "active_jobs":db.execute("SELECT COUNT(*) c FROM vacancies WHERE status='active' AND moderation_status='approved'").fetchone()["c"],
        "pending_jobs":db.execute("SELECT COUNT(*) c FROM vacancies WHERE moderation_status='pending'").fetchone()["c"],
        "applications":db.execute("SELECT COUNT(*) c FROM applications").fetchone()["c"]}
    employers=db.execute("""SELECT u.id,u.name,u.email,u.created_at,ep.organization_name,ep.account_status,ep.verification_status FROM users u JOIN employer_profiles ep ON ep.user_id=u.id WHERE u.role='employer' ORDER BY u.id DESC LIMIT 8""").fetchall()
    jobs=db.execute("""SELECT v.id,v.title,v.created_at,v.status,v.moderation_status,ep.organization_name FROM vacancies v JOIN employer_profiles ep ON ep.user_id=v.employer_id ORDER BY v.id DESC LIMIT 8""").fetchall()
    return render_template("admin/dashboard.html",stats=stats,recent_employers=employers,recent_jobs=jobs)

@admin_bp.get("/employers")
@role_required("admin")
def employers():
    db=get_db(); q=request.args.get("q","").strip(); status=request.args.get("status",""); verification=request.args.get("verification","")
    sql="""SELECT u.id,u.name,u.email,u.created_at,ep.organization_name,ep.organization_type,ep.location,ep.account_status,ep.verification_status,ep.verified_at FROM users u JOIN employer_profiles ep ON ep.user_id=u.id WHERE u.role='employer'"""; args=[]
    if q: sql+=" AND (u.name LIKE ? OR u.email LIKE ? OR ep.organization_name LIKE ? OR ep.location LIKE ?)"; args += [f"%{q}%"]*4
    if status in {"active","suspended"}: sql+=" AND ep.account_status=?"; args.append(status)
    if verification in {"pending","verified","rejected"}: sql+=" AND ep.verification_status=?"; args.append(verification)
    rows=db.execute(sql+" ORDER BY u.id DESC",args).fetchall()
    return render_template("admin/employers.html",employers=rows,q=q,status=status,verification=verification)

@admin_bp.get("/employers/<int:user_id>")
@role_required("admin")
def employer_detail(user_id):
    db=get_db(); employer=db.execute("""SELECT u.*,ep.organization_name,ep.organization_type,ep.website,ep.location,ep.description,ep.account_status,ep.verification_status,ep.verification_note,ep.verified_at FROM users u JOIN employer_profiles ep ON ep.user_id=u.id WHERE u.id=? AND u.role='employer'""",(user_id,)).fetchone()
    if not employer:return render_template("404.html"),404
    jobs=db.execute("SELECT * FROM vacancies WHERE employer_id=? ORDER BY id DESC",(user_id,)).fetchall()
    activity=db.execute("SELECT * FROM admin_activity WHERE target_type='employer' AND target_id=? ORDER BY id DESC LIMIT 10",(user_id,)).fetchall()
    counts={"jobs":len(jobs),"applications":db.execute("SELECT COUNT(*) c FROM applications a JOIN vacancies v ON v.id=a.vacancy_id WHERE v.employer_id=?",(user_id,)).fetchone()["c"],"selected":db.execute("SELECT COUNT(*) c FROM applications a JOIN vacancies v ON v.id=a.vacancy_id WHERE v.employer_id=? AND a.status='Selected'",(user_id,)).fetchone()["c"]}
    return render_template("admin/employer_detail.html",employer=employer,jobs=jobs,activity=activity,counts=counts)

@admin_bp.post("/employers/<int:user_id>/verification")
@role_required("admin")
def employer_verification(user_id):
    action=request.form.get("action"); note=request.form.get("note","").strip() or None
    if action not in {"verify","reject"}:return back("admin.employers")
    db=get_db(); exists=db.execute("SELECT 1 FROM users WHERE id=? AND role='employer'",(user_id,)).fetchone()
    if not exists:return render_template("404.html"),404
    status="verified" if action=="verify" else "rejected"; verified=datetime.now(timezone.utc).isoformat() if action=="verify" else None
    db.execute("UPDATE employer_profiles SET verification_status=?,verification_note=?,verified_at=? WHERE user_id=?",(status,note,verified,user_id)); log_action(db,f"Employer {action}d","employer",user_id,note); db.commit(); flash(f"Employer {action}d.","success")
    return back("admin.employers")

@admin_bp.post("/employers/<int:user_id>/status")
@role_required("admin")
def employer_status(user_id):
    status=request.form.get("status")
    if status not in {"active","suspended"}:return back("admin.employers")
    db=get_db(); db.execute("UPDATE employer_profiles SET account_status=? WHERE user_id=?",(status,user_id)); log_action(db,f"Employer account {status}","employer",user_id); db.commit(); flash(f"Employer account {status}.","success"); return back("admin.employers")

@admin_bp.get("/jobs")
@role_required("admin")
def jobs():
    db=get_db(); q=request.args.get("q","").strip(); moderation=request.args.get("moderation","")
    sql="""SELECT v.*,u.name employer_name,u.email employer_email,ep.organization_name,ep.verification_status,ep.account_status FROM vacancies v JOIN users u ON u.id=v.employer_id JOIN employer_profiles ep ON ep.user_id=u.id WHERE 1=1"""; args=[]
    if q:sql+=" AND (v.title LIKE ? OR ep.organization_name LIKE ? OR u.email LIKE ?)";args += [f"%{q}%"]*3
    if moderation in {"pending","approved","rejected"}:sql+=" AND v.moderation_status=?";args.append(moderation)
    rows=db.execute(sql+" ORDER BY v.id DESC",args).fetchall();return render_template("admin/jobs.html",jobs=rows,q=q,moderation=moderation)

@admin_bp.post("/jobs/<int:vacancy_id>/moderation")
@role_required("admin")
def job_moderation(vacancy_id):
    action=request.form.get("action");note=request.form.get("note","").strip() or None
    if action not in {"approve","reject","remove"}:return back("admin.jobs")
    db=get_db();job=db.execute("SELECT id FROM vacancies WHERE id=?",(vacancy_id,)).fetchone()
    if not job:return render_template("404.html"),404
    now=datetime.now(timezone.utc).isoformat()
    if action=="approve":db.execute("UPDATE vacancies SET moderation_status='approved',moderation_note=?,moderated_at=? WHERE id=?",(note,now,vacancy_id));message="Job approved."
    else:db.execute("UPDATE vacancies SET moderation_status='rejected',moderation_note=?,moderated_at=?,status='closed' WHERE id=?",(note or ("Removed by admin" if action=="remove" else "Rejected by admin"),now,vacancy_id));message="Job removed from the platform." if action=="remove" else "Job rejected."
    log_action(db,f"Job {action}d","job",vacancy_id,note);db.commit();flash(message,"success");return back("admin.jobs")

@admin_bp.get("/activity")
@role_required("admin")
def activity():
    rows=get_db().execute("SELECT aa.*,au.name admin_name FROM admin_activity aa JOIN admin_users au ON au.id=aa.admin_id ORDER BY aa.id DESC LIMIT 100").fetchall();return render_template("admin/activity.html",activity=rows)

@admin_bp.get("/settings")
@role_required("admin")
def settings():return render_template("admin/settings.html")
