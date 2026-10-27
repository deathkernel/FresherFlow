from database.database import init_db
from database.vacancy_deduplication import find_duplicate_vacancy, new_vacancy_code, vacancy_fingerprint

def test_vacancy_codes_are_unique_and_have_expected_prefix():
    codes = {new_vacancy_code() for _ in range(500)}
    assert len(codes) == 500
    assert all(code.startswith("FF-JOB-") for code in codes)

def test_fingerprint_normalizes_punctuation_case_and_whitespace():
    first = {"title": "Python Developer!", "vacancy_type": "Entry-level Job", "location": "Pune, India", "description": "Build APIs and services."}
    second = {"title": " PYTHON developer ", "vacancy_type": "Entry-level Job", "location": "PUNE India", "description": "Build APIs and services"}
    assert vacancy_fingerprint(7, first) == vacancy_fingerprint(7, second)
    assert vacancy_fingerprint(7, first) != vacancy_fingerprint(8, first)

def test_duplicate_lookup_is_scoped_to_employer_and_supports_exclusion(tmp_path):
    import sqlite3
    path = tmp_path / "duplicates.db"
    init_db(path)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    data = {"title": "Python Developer", "vacancy_type": "Entry-level Job", "location": "Pune", "description": "Build APIs"}
    db.execute("INSERT INTO users(name,email,password_hash,role) VALUES('A','a@example.com','x','employer')")
    db.execute("INSERT INTO vacancies(employer_id,title,vacancy_type,description,location,status,moderation_status,vacancy_code,dedupe_fingerprint) VALUES(1,?,?,?,?, 'active','pending',?,?)", (data["title"], data["vacancy_type"], data["description"], data["location"], new_vacancy_code(), vacancy_fingerprint(1, data)))
    db.commit()
    assert find_duplicate_vacancy(db, 1, data)["title"] == "Python Developer"
    assert find_duplicate_vacancy(db, 1, data, exclude_id=1) is None
    assert find_duplicate_vacancy(db, 2, data) is None
    db.close()

def test_startup_migration_assigns_codes_and_deduplicates_legacy_rows(tmp_path):
    import sqlite3
    path = tmp_path / "legacy.db"
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password_hash TEXT, role TEXT);
        CREATE TABLE employer_profiles (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, company_id TEXT UNIQUE, organization_name TEXT);
        CREATE TABLE vacancies (
            id INTEGER PRIMARY KEY AUTOINCREMENT, employer_id INTEGER NOT NULL, title TEXT NOT NULL,
            vacancy_type TEXT NOT NULL, description TEXT NOT NULL, location TEXT NOT NULL, salary TEXT,
            skills TEXT, eligibility TEXT, deadline TEXT, status TEXT NOT NULL DEFAULT 'draft',
            moderation_status TEXT NOT NULL DEFAULT 'pending', moderation_note TEXT, moderated_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE applications (id INTEGER PRIMARY KEY, vacancy_id INTEGER, student_id INTEGER);
        CREATE TABLE saved_jobs (id INTEGER PRIMARY KEY, vacancy_id INTEGER, student_id INTEGER);
        INSERT INTO users VALUES(1,'A','a@example.com','x','employer');
        INSERT INTO vacancies(employer_id,title,vacancy_type,description,location) VALUES
            (1,'Python Developer','Entry-level Job','Build APIs','Pune'),
            (1,'Python Developer','Entry-level Job','Build APIs','Pune');
    """)
    db.commit()
    db.close()
    init_db(path)
    db = sqlite3.connect(path)
    rows = db.execute("SELECT id,vacancy_code,dedupe_fingerprint FROM vacancies ORDER BY id").fetchall()
    assert len(rows) == 1
    assert rows[0][1].startswith("FF-JOB-")
    assert len(rows[0][2]) == 64
    db.close()
