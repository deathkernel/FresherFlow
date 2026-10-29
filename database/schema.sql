CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('student','employer')),
    auth_version TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS student_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL UNIQUE, phone TEXT, education TEXT,
    college TEXT, graduation_year TEXT, skills TEXT, certifications TEXT, preferred_job_type TEXT,
    preferred_location TEXT, resume_filename TEXT, profile_strength INTEGER NOT NULL DEFAULT 20,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS employer_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL UNIQUE, company_id TEXT NOT NULL UNIQUE,
    organization_name TEXT NOT NULL, organization_type TEXT, website TEXT, location TEXT, description TEXT,
    account_status TEXT NOT NULL DEFAULT 'active' CHECK(account_status IN ('active','suspended')),
    verification_status TEXT NOT NULL DEFAULT 'pending' CHECK(verification_status IN ('pending','verified','rejected')),
    verification_note TEXT, verified_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS vacancies (
    id INTEGER PRIMARY KEY AUTOINCREMENT, employer_id INTEGER NOT NULL, title TEXT NOT NULL,
    vacancy_type TEXT NOT NULL CHECK(vacancy_type IN ('Internship','Entry-level Job')), description TEXT NOT NULL,
    location TEXT NOT NULL, salary TEXT, skills TEXT, eligibility TEXT, deadline TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','active','closed')),
    moderation_status TEXT NOT NULL DEFAULT 'pending' CHECK(moderation_status IN ('pending','approved','rejected')),
    moderation_note TEXT, moderated_at TEXT, vacancy_code TEXT, dedupe_fingerprint TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(employer_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT, vacancy_id INTEGER NOT NULL, student_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'Applied' CHECK(status IN ('Applied','Shortlisted','Selected','Rejected')),
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(vacancy_id, student_id),
    FOREIGN KEY(vacancy_id) REFERENCES vacancies(id) ON DELETE CASCADE, FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS saved_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, vacancy_id INTEGER NOT NULL, student_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(vacancy_id, student_id),
    FOREIGN KEY(vacancy_id) REFERENCES vacancies(id) ON DELETE CASCADE, FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS auth_attempts (
    attempt_key TEXT PRIMARY KEY, failed_count INTEGER NOT NULL DEFAULT 0, locked_until INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_auth_attempts_updated_at ON auth_attempts(updated_at);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, actor_type TEXT NOT NULL, actor_id TEXT, action TEXT NOT NULL,
    target_type TEXT, target_id TEXT, details TEXT, ip_address TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'system', is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER NOT NULL, recipient_id INTEGER NOT NULL,
    body TEXT NOT NULL, is_read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY(recipient_id) REFERENCES users(id) ON DELETE CASCADE
);
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
CREATE INDEX IF NOT EXISTS idx_vacancies_employer_id ON vacancies(employer_id);
CREATE INDEX IF NOT EXISTS idx_vacancies_moderation_status ON vacancies(moderation_status);
CREATE INDEX IF NOT EXISTS idx_vacancies_status_deadline ON vacancies(status, deadline);
CREATE INDEX IF NOT EXISTS idx_applications_student_id ON applications(student_id);
CREATE INDEX IF NOT EXISTS idx_applications_vacancy_id ON applications(vacancy_id);
CREATE INDEX IF NOT EXISTS idx_saved_jobs_student_id ON saved_jobs(student_id);
CREATE INDEX IF NOT EXISTS idx_saved_jobs_vacancy_id ON saved_jobs(vacancy_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_employer_account_status ON employer_profiles(account_status);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_users ON messages(sender_id, recipient_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_sender_created_at ON messages(sender_id, created_at);


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
    supporting_document_filename TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','college_approved','college_rejected')),
    reviewer_id INTEGER,
    reviewer_note TEXT,
    submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TEXT,
    admin_status TEXT NOT NULL DEFAULT 'pending' CHECK(admin_status IN ('pending','verified','rejected')),
    expires_at TEXT,
    admin_review_note TEXT,
    admin_reviewed_at TEXT,
    FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(college_id) REFERENCES colleges(id),
    FOREIGN KEY(reviewer_id) REFERENCES college_verifiers(id)
);
CREATE INDEX IF NOT EXISTS idx_college_verifiers_college ON college_verifiers(college_id, status);
CREATE INDEX IF NOT EXISTS idx_student_verification_queue ON student_verification_requests(college_id, status, submitted_at);


CREATE TABLE IF NOT EXISTS career_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    title TEXT NOT NULL CHECK(length(trim(title)) > 0),
    notes TEXT,
    target_date TEXT,
    is_completed INTEGER NOT NULL DEFAULT 0 CHECK(is_completed IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_career_tasks_student_due
    ON career_tasks(student_id, is_completed, target_date, id);
