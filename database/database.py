import sqlite3
from pathlib import Path
from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def migrate_student_profile(db):
    existing = {row[1] for row in db.execute("PRAGMA table_info(student_profiles)").fetchall()}
    additions = {
        "college": "TEXT",
        "graduation_year": "TEXT",
        "preferred_job_type": "TEXT",
        "preferred_location": "TEXT",
    }
    for column, definition in additions.items():
        if column not in existing:
            db.execute(f"ALTER TABLE student_profiles ADD COLUMN {column} {definition}")


def init_db(database_path):
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys = ON")
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    db.executescript(schema)
    migrate_student_profile(db)

    if db.execute("SELECT COUNT(*) FROM users WHERE role='employer'").fetchone()[0] == 0:
        db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)", (
            "TechNova Recruiting", "demo.employer@fresherflow.local", generate_password_hash("Demo@123"), "employer"))
        employer_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute("INSERT INTO employer_profiles(user_id,organization_name,organization_type,location,description) VALUES(?,?,?,?,?)", (
            employer_id, "TechNova", "Technology", "Pune, Maharashtra", "Demo employer profile for local development."))
        seed = [
            (employer_id, "Python Developer Intern", "Internship", "Build APIs and assist the backend team.", "Pune, Maharashtra", "₹15,000/mo", "Python, Flask, SQLite", "Students / freshers with Python basics", "2026-12-31"),
            (employer_id, "Frontend Developer", "Entry-level Job", "Create responsive user interfaces for client projects.", "Remote", "₹4.5 LPA", "HTML, CSS, JavaScript, Bootstrap", "Freshers with frontend project experience", "2026-12-31"),
            (employer_id, "Data Analyst Intern", "Internship", "Work with datasets and create business reports.", "Mumbai, Maharashtra", "₹18,000/mo", "Python, Excel, SQL", "Students pursuing data or computer-related courses", "2026-12-31"),
            (employer_id, "Junior Software Engineer", "Entry-level Job", "Join the engineering team and ship production features.", "Bengaluru, Karnataka", "₹6 LPA", "Python, Git, SQL", "0–1 years experience", "2026-12-31")
        ]
        db.executemany("""INSERT INTO vacancies(employer_id,title,vacancy_type,description,location,salary,skills,eligibility,deadline,status)
                          VALUES(?,?,?,?,?,?,?,?,?,?)""", [(*row, "active") for row in seed])
    db.commit()
    db.close()
