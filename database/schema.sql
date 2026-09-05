CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('student','employer')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS student_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    phone TEXT,
    education TEXT,
    college TEXT,
    graduation_year TEXT,
    skills TEXT,
    certifications TEXT,
    preferred_job_type TEXT,
    preferred_location TEXT,
    resume_filename TEXT,
    profile_strength INTEGER NOT NULL DEFAULT 20,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS employer_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    organization_name TEXT NOT NULL,
    organization_type TEXT,
    website TEXT,
    location TEXT,
    description TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vacancies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employer_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    vacancy_type TEXT NOT NULL CHECK(vacancy_type IN ('Internship','Entry-level Job')),
    description TEXT NOT NULL,
    location TEXT NOT NULL,
    salary TEXT,
    skills TEXT,
    eligibility TEXT,
    deadline TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','active','closed')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(employer_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vacancy_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'Applied' CHECK(status IN ('Applied','Shortlisted','Selected','Rejected')),
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(vacancy_id, student_id),
    FOREIGN KEY(vacancy_id) REFERENCES vacancies(id) ON DELETE CASCADE,
    FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS saved_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vacancy_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(vacancy_id, student_id),
    FOREIGN KEY(vacancy_id) REFERENCES vacancies(id) ON DELETE CASCADE,
    FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE
);
