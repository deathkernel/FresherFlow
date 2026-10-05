import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db():
    if "db" in g:
        return g.db
    db = sqlite3.connect(current_app.config["DATABASE"])
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    g.db = db
    return db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def migrate_student_profile(db):
    existing = {row[1] for row in db.execute("PRAGMA table_info(student_profiles)").fetchall()}
    additions = {
        "college": "TEXT", "graduation_year": "TEXT",
        "preferred_job_type": "TEXT", "preferred_location": "TEXT",
    }
    for column, definition in additions.items():
        if column not in existing:
            db.execute(f"ALTER TABLE student_profiles ADD COLUMN {column} {definition}")


def migrate_employer_data(db):
    employer_columns = {row[1] for row in db.execute("PRAGMA table_info(employer_profiles)").fetchall()}
    additions = {
        "company_id": "TEXT", "account_status": "TEXT NOT NULL DEFAULT 'active'",
        "verification_status": "TEXT NOT NULL DEFAULT 'pending'",
        "verification_note": "TEXT", "verified_at": "TEXT",
    }
    for column, definition in additions.items():
        if column not in employer_columns:
            db.execute(f"ALTER TABLE employer_profiles ADD COLUMN {column} {definition}")
    db.execute("UPDATE employer_profiles SET company_id='FF-CMP-' || printf('%06d', user_id) WHERE company_id IS NULL OR company_id=''")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_employer_profiles_company_id ON employer_profiles(company_id)")
    db.execute("UPDATE employer_profiles SET account_status='active' WHERE account_status IS NULL")

    vacancy_columns = {row[1] for row in db.execute("PRAGMA table_info(vacancies)").fetchall()}
    vacancy_additions = {
        "moderation_status": "TEXT NOT NULL DEFAULT 'pending'",
        "moderation_note": "TEXT", "moderated_at": "TEXT",
    }
    for column, definition in vacancy_additions.items():
        if column not in vacancy_columns:
            db.execute(f"ALTER TABLE vacancies ADD COLUMN {column} {definition}")


def apply_migrations(db):
    db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    applied = {row["version"] for row in db.execute("SELECT version FROM schema_migrations").fetchall()}

    if 1 not in applied:
        db.execute("""CREATE TRIGGER IF NOT EXISTS vacancies_pending_default
        AFTER INSERT ON vacancies
        WHEN NEW.status='draft' AND NEW.moderation_status='approved'
        BEGIN UPDATE vacancies SET moderation_status='pending' WHERE id=NEW.id; END""")
        db.execute("""CREATE TRIGGER IF NOT EXISTS employer_verification_pending_default
        AFTER INSERT ON employer_profiles
        WHEN NEW.verification_status='verified' AND NEW.verified_at IS NULL
        BEGIN UPDATE employer_profiles SET verification_status='pending' WHERE id=NEW.id; END""")
        db.execute("INSERT INTO schema_migrations(version) VALUES(1)")

    if 2 not in applied:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'system',
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            recipient_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(recipient_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read, created_at);
        CREATE INDEX IF NOT EXISTS idx_messages_users ON messages(sender_id, recipient_id, created_at);
        CREATE TRIGGER IF NOT EXISTS notify_application_created
        AFTER INSERT ON applications
        BEGIN
            INSERT INTO notifications(user_id,title,body,kind)
            SELECT NEW.student_id,'Application submitted','Your application has been submitted successfully.','application';
            INSERT INTO notifications(user_id,title,body,kind)
            SELECT v.employer_id,'New application','A student applied to your vacancy.','application'
            FROM vacancies v WHERE v.id=NEW.vacancy_id;
        END;
        CREATE TRIGGER IF NOT EXISTS notify_application_status
        AFTER UPDATE OF status ON applications
        WHEN OLD.status <> NEW.status
        BEGIN
            INSERT INTO notifications(user_id,title,body,kind)
            VALUES(NEW.student_id,'Application status updated','Your application is now ' || NEW.status || '.','application');
        END;
        CREATE TRIGGER IF NOT EXISTS notify_vacancy_status
        AFTER UPDATE OF status ON vacancies
        WHEN OLD.status <> NEW.status
        BEGIN
            INSERT INTO notifications(user_id,title,body,kind)
            VALUES(NEW.employer_id,'Vacancy status updated','Your vacancy is now ' || NEW.status || '.','vacancy');
        END;
        """)
        db.execute("INSERT INTO schema_migrations(version) VALUES(2)")


def init_db(database_path):
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys = ON")
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        db.executescript(schema)
        migrate_student_profile(db)
        migrate_employer_data(db)
        apply_migrations(db)
        db.commit()
    finally:
        db.close()
