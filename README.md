# FresherFlow

FresherFlow is a Flask-based fresher recruitment platform with separate student, employer and admin workflows, SQLite persistence, resume uploads, vacancy moderation and public-job synchronization.

## Stack

- Python 3.12+
- Flask 3.x
- SQLite
- HTML/CSS/JavaScript
- GitHub Actions, CodeQL and pip-audit

## Local setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Copy `.env.example` to `.env` and configure the variables in your shell/deployment environment. The application does not load `.env` automatically.

### Admin credentials

`ADMIN_PASSWORD_HASH` must contain a Werkzeug password hash. Generate one locally without putting the plaintext password in the repository:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('CHANGE-ME'))"
```

Then set:

```text
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD_HASH=<generated-hash>
```

### Run

```bash
python app.py
```

The application creates its SQLite database under `instance/` on first start. Runtime databases, generated secrets and uploaded resumes are ignored by Git.

## Security notes

- All application POST forms use CSRF protection.
- Sessions use HttpOnly and SameSite cookie settings; enable `SESSION_COOKIE_SECURE=1` behind HTTPS.
- Resume uploads are limited to 5 MB and checked by file signature as well as extension.
- Admin authentication requires an explicitly configured password hash; there is no default admin password.
- Public-job synchronization uses a dedicated token.
- Do not commit `.env`, `instance/`, database files or uploaded resumes.

## Tests and security checks

Run the tests with:

```bash
pytest -q
```

GitHub Actions also runs tests, CodeQL, dependency auditing and dependency review for pull requests.

## Public job sync

The scheduled workflow can call the deployed endpoint with `PUBLIC_JOB_SYNC_TOKEN`. If deployment secrets are not configured, the workflow runs the local sync script as a smoke test instead.
