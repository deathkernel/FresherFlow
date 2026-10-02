# FresherFlow

FresherFlow is a Flask-based fresher recruitment platform with separate student, employer and admin workflows, SQLite persistence, resume uploads, vacancy moderation and application tracking.

## Stack

- Python 3.11+
- Flask 3.x
- SQLite
- HTML/CSS/JavaScript
- openpyxl for Excel vacancy import

## Architecture

The application is intentionally small and role-oriented:

- `app.py` — application setup, CSRF enforcement, security headers and error handlers
- `config.py` — runtime configuration, sessions and secrets
- `security.py` — CSRF, upload validation, URL validation and login throttling
- `database/` — SQLite schema, indexes and migrations
- `routes/auth_routes.py` — student/employer authentication
- `routes/student_routes.py` — profiles, opportunities, applications and saved jobs
- `routes/employer_routes.py` — employer profiles, vacancies and candidate workflow
- `routes/admin_routes.py` — moderation, employer management and audit logging
- `templates/` — Jinja UI
- `static/` — CSS and JavaScript
- `tests/` — automated security and workflow tests

## Local setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

## Run

```bash
python app.py
```

The application creates its SQLite database under `instance/` on first start. Runtime databases, generated secrets and uploaded resumes are ignored by Git.

### Panels

- Student / Employer: `http://127.0.0.1:5000/login`
- Admin: `http://127.0.0.1:5000/admin`

## Configuration

### Development

Development can use the generated local secret and the documented development-only admin credentials.

### Production

Set:

```text
FRESHERFLOW_ENV=production
SECRET_KEY=<long-random-secret>
ADMIN_EMAIL=<admin-email>
ADMIN_PASSWORD_HASH=<Werkzeug-password-hash>
SESSION_COOKIE_SECURE=1
```

Do not use the development admin credentials in production.

Generate a Werkzeug password hash with:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('replace-this-password'))"
```

## Security model

FresherFlow currently includes:

- CSRF validation for all POST requests
- HttpOnly and SameSite session cookies
- Secure cookies in production
- production SECRET_KEY enforcement
- security response headers and CSP
- password hashing with Werkzeug
- login throttling after repeated failures
- resume size, extension and file-signature validation
- DOCX container validation without extracting uploaded archives
- sanitized server-side resume filenames
- private resume downloads
- role-based route protection
- employer suspension checks
- vacancy moderation before public visibility
- database foreign keys and indexes
- admin audit logging

Uploaded resumes should remain outside the executable/static directory and should never be committed to Git.

## Database

SQLite is used for local development and the current project scope.

The database layer creates a `schema_migrations` table and applies idempotent migrations during startup. New databases receive safe moderation defaults:

- employer verification: `pending`
- vacancy moderation: `pending`

Existing databases retain their historical moderation decisions while compatibility triggers prevent legacy implicit inserts from silently bypassing moderation.

For a larger deployment, PostgreSQL or another server database should be considered.

## Workflows

### Student

```text
Register
  ↓
Profile + resume
  ↓
Discover approved opportunities
  ↓
Save / Apply
  ↓
Track application status
```

### Employer

```text
Admin creates employer account
  ↓
Create vacancy / import Excel
  ↓
Submit for moderation
  ↓
Admin approval
  ↓
Applications
  ↓
Update candidate status
```

### Admin

```text
Review vacancies
  ↓
Approve / reject
  ↓
Manage employer accounts
  ↓
Inspect applications
  ↓
Audit sensitive actions
```

## Features

- Student registration and profile management
- Resume upload and replacement
- Internship and entry-level job vacancies
- Opportunity search and filters
- Saved jobs and duplicate-application protection
- Employer organization profile
- Single and Excel bulk vacancy import
- Admin vacancy moderation
- Employer activation/suspension
- Candidate/application status tracking
- Pagination for growing lists
- CSRF protection and secure sessions
- Security-focused automated tests

## Tests

```bash
pytest -q
```

CI runs the test suite on Python 3.11 and 3.12.

## Production notes

Do not use Flask's development server as the production web server. Put FresherFlow behind a production WSGI server and HTTPS, keep uploads private, back up the database, and rotate credentials if they are ever exposed.

Runtime files such as the SQLite database, generated secret and uploaded resumes should not be committed to Git.
