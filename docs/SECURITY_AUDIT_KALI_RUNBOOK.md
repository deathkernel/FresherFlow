# FresherFlow — Kali Linux Full Audit Runbook

**Scope:** authorized testing of the local FresherFlow instance only. Covers source review, dependency/static analysis, and Student, Employer, and Admin workflows.  
**Repository:** https://github.com/deathkernel/FresherFlow  
**Status:** source-only preliminary review; runtime/DAST results must be recorded after running the checklist below.

## Safety and test isolation

- Use a disposable copy of the SQLite database and synthetic student/employer records. Do not test with real resumes or personal data.
- Keep the Windows host and Kali VM on a **Host-only** virtual network when possible. Do not port-forward the Flask development server to the internet.
- Active scans can submit forms, create records, and trigger lockouts. Run them only against the disposable test instance.
- The app's Flask development server is for local testing only, not production.

## 1. Establish a clean baseline on Windows

From the FresherFlow project directory in PowerShell:

```powershell
git status --short
git switch main
git pull
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Save the complete test output. If the working tree contains changes, do not discard them; commit/stash them safely before switching branches.

## 2. Prepare a safe network path for Kali

1. In VMware, configure the Kali VM's network adapter as **Host-only** (or use a dedicated private lab network). Avoid Bridged mode for this audit.
2. On Windows, identify the host-only adapter's IPv4 address with `ipconfig`. Do not use the public/Wi-Fi IP if a host-only address is available.
3. Start FresherFlow from PowerShell in the project directory:

```powershell
$env:HOST = "0.0.0.0"
$env:PORT = "5000"
$env:FLASK_DEBUG = "0"
python app.py
```

4. Allow inbound TCP 5000 only on the **Private** firewall profile and scope the rule to the Kali VM's host-only IP. Do not create a Public-profile or router port-forward rule. Remove the temporary firewall rule when finished.
5. From Kali, verify reachability using the host-only IP:

```bash
curl -sS -D - -o /dev/null http://<WINDOWS_HOST_ONLY_IP>:5000/
```

If this fails, check the adapter subnet, Windows firewall rule, and Flask listener before scanning. Do not disable Windows Firewall globally.

## 3. Static and dependency checks

Run these in the Windows virtual environment first; the same source can also be checked from Kali after cloning the audit branch.

```bash
python -m pytest -q
python -m pip install bandit pip-audit
bandit -r app.py config.py admin_config.py security.py routes database -ll
pip-audit -r requirements-dev.txt
```

Record tool versions, exit codes, complete output, and the commit SHA. A scanner alert is a candidate finding until manually verified. Do not suppress findings without recording the rationale.

## 4. Web security checks from Kali

Install/launch OWASP ZAP from its official package/source. First run a **passive** scan against the disposable local instance. Review alerts and manually validate them. Use an active scan only after taking a database backup and confirming the target is the host-only test address.

Target:
`http://<WINDOWS_HOST_ONLY_IP>:5000`

Recommended first pass:
- Crawl the public landing page, login pages, registration, and public job pages.
- Use authenticated ZAP contexts separately for Student, Employer, and Admin. Do not share cookies between roles.
- Review response headers, cookie attributes, CSP, caching, error responses, mixed content, and exposed debug traces.
- Re-run with a clean database after any active scan.

## 5. Role-by-role manual test matrix

For every request, record: role/session, route, method, expected result, actual status/result, evidence, severity, and commit SHA. Use only synthetic records.

### Unauthenticated
- Open `/`, `/login`, `/register`, and `/admin/login`.
- Request each dashboard and sensitive route directly; confirm redirect/denial and no data leakage.
- POST without a CSRF token to each state-changing form; expect rejection.
- Confirm no stack trace, secret, filesystem path, or database content is returned by invalid requests.

### Student panel
- Register with valid and invalid input; verify password length, duplicate-email handling, and server-side role restrictions.
- Attempt to change another student's profile/application by changing object IDs; expect denial or no cross-user data.
- Apply to a vacancy, apply twice, save/unsave a vacancy, and inspect application status visibility.
- Upload valid and invalid PDF/DOC/DOCX files, oversized files, extension/signature mismatches, and malformed DOCX archives.
- Confirm resume downloads are private and cannot be fetched by guessing another user's filename/ID.

### Employer panel
- Confirm a student cannot access employer routes and an employer cannot access student/admin routes.
- Create/edit vacancies; confirm new vacancies remain pending until approved.
- Try to read or update applications for vacancies owned by a different employer; expect denial/no disclosure.
- Test employer suspension and session invalidation.
- Test Excel imports with malformed files, formula-like text, more than 100 rows, and oversized archives using a disposable database.

### Admin panel
- Confirm only configured admin credentials can authenticate; no built-in default account works.
- Test repeated failed logins in the lab and verify throttling without making the production account unavailable.
- Verify moderation, employer activation/suspension, and audit-log writes.
- Confirm admin actions reject missing/invalid CSRF tokens and normal roles cannot call admin endpoints.
- Check filtered pagination boundaries and ensure IDs/filters cannot expose records beyond intended admin access.

### Cross-cutting
- Test XSS payloads as harmless text in profile, vacancy, organization, and application fields; confirm output is escaped.
- Check SQL injection-like input in search/filter fields; confirm parameterized behavior and no database errors.
- Verify logout clears the session; password/auth-version changes revoke old sessions.
- Check response cache headers and CSP. Confirm external assets are limited to expected origins.
- Confirm website URL fields reject non-HTTP(S) schemes and unexpected URL formats.

## 6. Finding severity and verification

- **Critical/High:** demonstrated authentication bypass, cross-role data access, arbitrary code execution, or exposure of sensitive personal data.
- **Medium:** meaningful authorization weakness, stored/reflected XSS with a credible impact, or significant security-control bypass.
- **Low/Informational:** hardening gaps without a demonstrated exploit path.

For each finding, include a minimal reproducible test, impact, affected file/route, evidence with secrets and personal data redacted, and a regression test. Reproduce on a clean test database before calling it confirmed.

## 7. Fix and retest workflow

1. Create a focused branch from the current `main`.
2. Add a regression test that fails before the fix.
3. Apply the smallest safe code change; preserve the existing role workflows and UI.
4. Run `pytest -q`, Bandit, pip-audit, and the relevant manual/ZAP checks.
5. Re-run the exact exploit reproduction and confirm it no longer succeeds.
6. Open a pull request with the finding, test evidence, risk, and remaining limitations. Do not merge a speculative fix that has not been tested.

## Preliminary source review (not a penetration-test result)

The inspected default-branch files already implement global POST CSRF validation, password hashing, role guards, login throttling, secure session-cookie settings, production secret/admin credential requirements, response security headers, resume signature/size checks, and a pytest suite. These controls still require runtime verification. A source-only review cannot certify that IDOR, XSS, authorization, or upload bypasses are absent, and no exploitable issue should be labelled confirmed without a reproducible test.
