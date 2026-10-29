import hashlib
import json
import re
import secrets
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

    if 3 not in applied:
        user_columns = {
            row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()
        }
        if "auth_version" not in user_columns:
            db.execute(
                "ALTER TABLE users ADD COLUMN auth_version TEXT NOT NULL DEFAULT ''"
            )
        db.execute(
            """CREATE TRIGGER IF NOT EXISTS users_auth_version_default
               AFTER INSERT ON users
               WHEN NEW.auth_version IS NULL OR NEW.auth_version=''
               BEGIN
                   UPDATE users SET auth_version=lower(hex(randomblob(32)))
                   WHERE id=NEW.id;
               END"""
        )
        for row in db.execute(
            "SELECT id FROM users WHERE auth_version IS NULL OR auth_version=''"
        ).fetchall():
            db.execute(
                "UPDATE users SET auth_version=? WHERE id=?",
                (secrets.token_urlsafe(32), row["id"]),
            )
        db.execute("INSERT INTO schema_migrations(version) VALUES(3)")


    if 4 not in applied:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id INTEGER PRIMARY KEY,
            theme TEXT NOT NULL DEFAULT 'light' CHECK(theme IN ('light','dark','system')),
            font_scale TEXT NOT NULL DEFAULT 'normal' CHECK(font_scale IN ('normal','large')),
            reduce_motion INTEGER NOT NULL DEFAULT 0 CHECK(reduce_motion IN (0,1)),
            notify_application INTEGER NOT NULL DEFAULT 1 CHECK(notify_application IN (0,1)),
            notify_message INTEGER NOT NULL DEFAULT 1 CHECK(notify_message IN (0,1)),
            notify_vacancy INTEGER NOT NULL DEFAULT 1 CHECK(notify_vacancy IN (0,1)),
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        DROP TRIGGER IF EXISTS notify_application_created;
        DROP TRIGGER IF EXISTS notify_application_status;
        DROP TRIGGER IF EXISTS notify_vacancy_status;
        CREATE TRIGGER notify_application_created
        AFTER INSERT ON applications
        BEGIN
            INSERT INTO notifications(user_id,title,body,kind)
            SELECT NEW.student_id,'Application submitted','Your application has been submitted successfully.','application'
            WHERE COALESCE((SELECT notify_application FROM user_preferences WHERE user_id=NEW.student_id),1)=1;
            INSERT INTO notifications(user_id,title,body,kind)
            SELECT v.employer_id,'New application','A student applied to your vacancy.','application'
            FROM vacancies v
            WHERE v.id=NEW.vacancy_id
              AND COALESCE((SELECT notify_application FROM user_preferences WHERE user_id=v.employer_id),1)=1;
        END;
        CREATE TRIGGER notify_application_status
        AFTER UPDATE OF status ON applications
        WHEN OLD.status <> NEW.status
        BEGIN
            INSERT INTO notifications(user_id,title,body,kind)
            SELECT NEW.student_id,'Application status updated','Your application is now ' || NEW.status || '.','application'
            WHERE COALESCE((SELECT notify_application FROM user_preferences WHERE user_id=NEW.student_id),1)=1;
        END;
        CREATE TRIGGER notify_vacancy_status
        AFTER UPDATE OF status ON vacancies
        WHEN OLD.status <> NEW.status
        BEGIN
            INSERT INTO notifications(user_id,title,body,kind)
            SELECT NEW.employer_id,'Vacancy status updated','Your vacancy is now ' || NEW.status || '.','vacancy'
            WHERE COALESCE((SELECT notify_vacancy FROM user_preferences WHERE user_id=NEW.employer_id),1)=1;
        END;
        """)
        db.execute("INSERT INTO schema_migrations(version) VALUES(4)")



    if 5 not in applied:
        # Cover the public job feeds and the most common dashboard sort/filter paths.
        db.executescript("""
        CREATE INDEX IF NOT EXISTS idx_vacancies_public_listing
            ON vacancies(status, moderation_status, deadline, id DESC);
        CREATE INDEX IF NOT EXISTS idx_vacancies_public_created
            ON vacancies(status, moderation_status, created_at DESC, id DESC);
        CREATE INDEX IF NOT EXISTS idx_applications_student_applied
            ON applications(student_id, applied_at DESC);
        CREATE INDEX IF NOT EXISTS idx_applications_vacancy_status
            ON applications(vacancy_id, status);
        """)
        db.execute("INSERT INTO schema_migrations(version) VALUES(5)")

    if 6 not in applied:
        # Moderation is a separate state from vacancy publication status. Notify
        # employers when an administrator approves or rejects a vacancy.
        db.executescript("""
        DROP TRIGGER IF EXISTS notify_vacancy_moderation;
        CREATE TRIGGER notify_vacancy_moderation
        AFTER UPDATE OF moderation_status ON vacancies
        WHEN OLD.moderation_status <> NEW.moderation_status
          AND NEW.moderation_status IN ('approved','rejected')
        BEGIN
            INSERT INTO notifications(user_id,title,body,kind)
            SELECT NEW.employer_id,
                   CASE NEW.moderation_status
                       WHEN 'approved' THEN 'Vacancy approved'
                       ELSE 'Vacancy rejected'
                   END,
                   CASE NEW.moderation_status
                       WHEN 'approved' THEN 'Your vacancy has been approved and can appear in student job listings.'
                       ELSE 'Your vacancy was rejected by the administrator. Review the moderation note and update the vacancy before resubmitting.'
                   END,
                   'vacancy'
            WHERE COALESCE(
                (SELECT notify_vacancy FROM user_preferences WHERE user_id=NEW.employer_id),
                1
            )=1;
        END;
        """)
        db.execute("INSERT INTO schema_migrations(version) VALUES(6)")

    if 7 not in applied:
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_sender_created_at "
            "ON messages(sender_id, created_at)"
        )
        db.execute("INSERT INTO schema_migrations(version) VALUES(7)")

    if 8 not in applied:
        vacancy_columns = {row[1] for row in db.execute("PRAGMA table_info(vacancies)").fetchall()}
        if "vacancy_code" not in vacancy_columns:
            db.execute("ALTER TABLE vacancies ADD COLUMN vacancy_code TEXT")
        if "dedupe_fingerprint" not in vacancy_columns:
            db.execute("ALTER TABLE vacancies ADD COLUMN dedupe_fingerprint TEXT")
        def normalized(value):
            return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()
        seen = {}
        for row in db.execute("SELECT * FROM vacancies ORDER BY id ASC").fetchall():
            identity = {"employer_id": row["employer_id"], "title": normalized(row["title"]), "vacancy_type": normalized(row["vacancy_type"]), "location": normalized(row["location"]), "description": normalized(row["description"])}
            fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()
            code = row["vacancy_code"] or f"FF-JOB-{secrets.token_hex(6).upper()}"
            duplicate_of = seen.get(fingerprint)
            db.execute("UPDATE vacancies SET vacancy_code=?, dedupe_fingerprint=? WHERE id=?", (code, fingerprint, row["id"]))
            if duplicate_of is None:
                seen[fingerprint] = {"id": row["id"], "code": code}
                continue
            has_history = db.execute("SELECT EXISTS(SELECT 1 FROM applications WHERE vacancy_id=?) OR EXISTS(SELECT 1 FROM saved_jobs WHERE vacancy_id=?)", (row["id"], row["id"])).fetchone()[0]
            if has_history:
                db.execute("UPDATE vacancies SET status='closed', moderation_status='rejected', moderation_note=?, moderated_at=CURRENT_TIMESTAMP WHERE id=?", (f"Duplicate of {duplicate_of['code']}; retained to preserve application history.", row["id"]))
            else:
                db.execute("DELETE FROM vacancies WHERE id=?", (row["id"],))
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_vacancies_vacancy_code ON vacancies(vacancy_code)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_vacancies_dedupe_fingerprint ON vacancies(employer_id, dedupe_fingerprint)")
        db.execute("INSERT INTO schema_migrations(version) VALUES(8)")


    if 9 not in applied:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS colleges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','suspended')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS college_verifiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            college_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','suspended')),
            auth_version TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(college_id) REFERENCES colleges(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS student_verification_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL UNIQUE,
            college_id INTEGER NOT NULL,
            enrollment_number TEXT NOT NULL,
            graduation_year TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','college_approved','college_rejected')),
            reviewer_id INTEGER,
            reviewer_note TEXT,
            submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TEXT,
            FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(college_id) REFERENCES colleges(id),
            FOREIGN KEY(reviewer_id) REFERENCES college_verifiers(id)
        );
        CREATE INDEX IF NOT EXISTS idx_college_verifiers_college ON college_verifiers(college_id, status);
        CREATE INDEX IF NOT EXISTS idx_student_verification_queue ON student_verification_requests(college_id, status, submitted_at);
        """)
        db.execute("INSERT INTO schema_migrations(version) VALUES(9)")

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
