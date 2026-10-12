# Security Policy

## Supported versions

Security fixes target the current default branch.

## Reporting a vulnerability

Please do not publish exploitable details in a public issue. Use GitHub's private vulnerability reporting feature for this repository when available, or contact the repository maintainer privately.

Include the affected route or component, impact, reproduction steps, and suggested mitigation. Do not include real student records, resumes, credentials, or other personal data.

## Deployment checklist

- Set `FRESHERFLOW_ENV=production`.
- Set a unique random `SECRET_KEY` of at least 32 characters, `ADMIN_EMAIL`, and `ADMIN_PASSWORD_HASH` through a secret manager.
- Serve only behind HTTPS with a production WSGI server.
- Keep uploaded resumes outside public/static directories and restrict filesystem permissions.
- Configure trusted-proxy middleware only when the exact trusted proxy hop count is known.
- Keep dependencies updated and review Dependabot, CodeQL, and dependency-audit findings.
- Bulk vacancy imports are capped at 100 rows; avoid raising limits without reviewing request and archive expansion bounds.
- Back up the database securely and restrict access to backups.
- Rotate `SECRET_KEY` and administrator credentials after suspected exposure.
- Protect `main` with required CI checks and pull-request review in repository settings.
