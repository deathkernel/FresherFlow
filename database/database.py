import os
import sqlite3
from pathlib import Path
from flask import current_app, g


def get_db():
    if "db" not in g:
        db=sqlite3.connect(current_app.config["DATABASE"]);db.row_factory=sqlite3.Row;db.execute("PRAGMA foreign_keys = ON");g.db=db
    return g.db

def close_db(_error=None):
    db=g.pop("db",None)
    if db is not None:db.close()

def migrate_student_profile(db):
    existing={row[1] for row in db.execute("PRAGMA table_info(student_profiles)").fetchall()};additions={"college":"TEXT","graduation_year":"TEXT","preferred_job_type":"TEXT","preferred_location":"TEXT"}
    for column,definition in additions.items():
        if column not in existing:db.execute(f"ALTER TABLE student_profiles ADD COLUMN {column} {definition}")

def migrate_employer_data(db):
    employer_columns={row[1] for row in db.execute("PRAGMA table_info(employer_profiles)").fetchall()};additions={"account_status":"TEXT NOT NULL DEFAULT 'active'","verification_status":"TEXT NOT NULL DEFAULT 'verified'","verification_note":"TEXT","verified_at":"TEXT"}
    for column,definition in additions.items():
        if column not in employer_columns:db.execute(f"ALTER TABLE employer_profiles ADD COLUMN {column} {definition}")
    db.execute("UPDATE employer_profiles SET account_status='active' WHERE account_status IS NULL");db.execute("UPDATE employer_profiles SET verification_status='verified' WHERE verification_status IS NULL OR verification_status='pending'")
    vacancy_columns={row[1] for row in db.execute("PRAGMA table_info(vacancies)").fetchall()};additions={"moderation_status":"TEXT NOT NULL DEFAULT 'approved'","moderation_note":"TEXT","moderated_at":"TEXT"}
    for column,definition in additions.items():
        if column not in vacancy_columns:db.execute(f"ALTER TABLE vacancies ADD COLUMN {column} {definition}")
    db.execute("UPDATE vacancies SET moderation_status='approved' WHERE moderation_status IS NULL OR moderation_status='pending'")

def init_db(database_path):
    path=Path(database_path);path.parent.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(path);db.execute("PRAGMA foreign_keys = ON");schema=Path(__file__).with_name("schema.sql").read_text(encoding="utf-8");db.executescript(schema);migrate_student_profile(db);migrate_employer_data(db)
    from .demo_seed import seed_demo_data
    password=os.environ.get("DEMO_EMPLOYER_PASSWORD") or "FresherFlowDemo@2026"
    seed_demo_data(db,password)
    db.commit();db.close()
