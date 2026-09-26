# FresherFlow

FresherFlow is a Flask-based fresher recruitment platform with separate student, employer and admin workflows, SQLite persistence, resume uploads and vacancy moderation.

## Stack

- Python 3.11+
- Flask 3.x
- SQLite
- HTML/CSS/JavaScript
- openpyxl for Excel vacancy import

## Local setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
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

### Local admin login (development only)

- Admin ID: `admin@123`
- Password: `admin123`

These defaults are enabled only when `FRESHERFLOW_ENV=development`. For staging/production, set `ADMIN_EMAIL` and `ADMIN_PASSWORD_HASH`; otherwise admin login is disabled.

## Features

- Student registration, profile, resume and opportunity search
- Internship and entry-level job vacancies
- Employer organization profile and vacancy management; employer accounts are created by Admin
- Excel `.xlsx` bulk vacancy import
- Admin moderation and company management
- Applications and application status tracking
- Vacancy deadline validation
- CSRF protection and secure session cookies

## Tests

```bash
pytest -q
```

Runtime files such as the SQLite database, generated secret and uploaded resumes should not be committed to Git.

## Production hardening

Set `FRESHERFLOW_ENV=production` for deployment. Configure a strong `SECRET_KEY`, plus `ADMIN_EMAIL` and a Werkzeug password hash in `ADMIN_PASSWORD_HASH`. Never commit the runtime database, generated secret or uploaded resumes.
