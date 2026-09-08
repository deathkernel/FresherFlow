import os
import sqlite3
from pathlib import Path
from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db=sqlite3.connect(current_app.config["DATABASE"]);g.db.row_factory=sqlite3.Row;g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(_error=None):
    db=g.pop("db",None)
    if db is not None:db.close()

def migrate_student_profile(db):
    existing={row[1] for row in db.execute("PRAGMA table_info(student_profiles)").fetchall()};additions={"college":"TEXT","graduation_year":"TEXT","preferred_job_type":"TEXT","preferred_location":"TEXT"}
    for column,definition in additions.items():
        if column not in existing:db.execute(f"ALTER TABLE student_profiles ADD COLUMN {column} {definition}")

def migrate_role_and_moderation(db):
    db.execute("""CREATE TABLE IF NOT EXISTS admin_users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
    employer_columns={row[1] for row in db.execute("PRAGMA table_info(employer_profiles)").fetchall()};added_verification=False
    additions={"account_status":"TEXT NOT NULL DEFAULT 'active'","verification_status":"TEXT NOT NULL DEFAULT 'pending'","verification_note":"TEXT","verified_at":"TEXT"}
    for column,definition in additions.items():
        if column not in employer_columns:
            db.execute(f"ALTER TABLE employer_profiles ADD COLUMN {column} {definition}")
            if column=="verification_status":added_verification=True
    if added_verification:db.execute("UPDATE employer_profiles SET verification_status='verified' WHERE verification_status='pending'")
    vacancy_columns={row[1] for row in db.execute("PRAGMA table_info(vacancies)").fetchall()};additions={"moderation_status":"TEXT NOT NULL DEFAULT 'approved'","moderation_note":"TEXT","moderated_at":"TEXT"}
    for column,definition in additions.items():
        if column not in vacancy_columns:db.execute(f"ALTER TABLE vacancies ADD COLUMN {column} {definition}")
    db.execute("""CREATE TABLE IF NOT EXISTS admin_activity(id INTEGER PRIMARY KEY AUTOINCREMENT,admin_id INTEGER NOT NULL,action TEXT NOT NULL,target_type TEXT,target_id INTEGER,details TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(admin_id) REFERENCES admin_users(id) ON DELETE CASCADE)""")

def ensure_env_admin(db):
    email=os.environ.get("FRESHERFLOW_ADMIN_EMAIL","admin@123").strip().lower()
    password=os.environ.get("FRESHERFLOW_ADMIN_PASSWORD","admin@123")
    name=os.environ.get("FRESHERFLOW_ADMIN_NAME","FresherFlow Admin").strip() or "FresherFlow Admin"
    if not email or not password:return
    from werkzeug.security import generate_password_hash
    existing=db.execute("SELECT id FROM admin_users WHERE email=?",(email,)).fetchone()
    if not existing:
        db.execute("INSERT INTO admin_users(name,email,password_hash) VALUES(?,?,?)",(name,email,generate_password_hash(password)))

def init_db(database_path):
    path=Path(database_path);path.parent.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(path);db.execute("PRAGMA foreign_keys = ON");schema=Path(__file__).with_name("schema.sql").read_text(encoding="utf-8");db.executescript(schema);migrate_student_profile(db);migrate_role_and_moderation(db);ensure_env_admin(db)
    if os.environ.get("FRESHERFLOW_DEMO")=="1":
        from werkzeug.security import generate_password_hash
        if db.execute("SELECT COUNT(*) FROM users WHERE role='employer'").fetchone()[0]==0:
            password=os.environ.get("DEMO_EMPLOYER_PASSWORD")
            if password:
                db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",("TechNova Recruiting","demo.employer@fresherflow.local",generate_password_hash(password),"employer"));employer_id=db.execute("SELECT last_insert_rowid()").fetchone()[0]
                db.execute("INSERT INTO employer_profiles(user_id,organization_name,organization_type,location,description,account_status,verification_status) VALUES(?,?,?,?,?,?,?)",(employer_id,"TechNova","Technology","Pune, Maharashtra","Demo employer profile for local development.","active","verified"))
                seed=[("Python Developer Intern","Internship","Build APIs and assist the backend team.","Pune, Maharashtra","₹15,000/mo","Python, Flask, SQLite","Students / freshers with Python basics","2026-12-31"),("Frontend Developer","Entry-level Job","Create responsive user interfaces for client projects.","Remote","₹4.5 LPA","HTML, CSS, JavaScript, Bootstrap","Freshers with frontend project experience","2026-12-31"),("Data Analyst Intern","Internship","Work with datasets and create business reports.","Mumbai, Maharashtra","₹18,000/mo","Python, Excel, SQL","Students pursuing data or computer-related courses","2026-12-31"),("Junior Software Engineer","Entry-level Job","Join the engineering team and ship production features.","Bengaluru, Karnataka","₹6 LPA","Python, Git, SQL","0–1 years experience","2026-12-31")]
                db.executemany("INSERT INTO vacancies(employer_id,title,vacancy_type,description,location,salary,skills,eligibility,deadline,status,moderation_status) VALUES(?,?,?,?,?,?,?,?,?,?,?)",[(employer_id,*row,"active","approved") for row in seed])
    db.commit();db.close()
