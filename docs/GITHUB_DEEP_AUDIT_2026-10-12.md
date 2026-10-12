# GitHub Deep Audit — deathkernel / FresherFlow
**Audit date:** 2026-10-12  
**Repository:** https://github.com/deathkernel/FresherFlow  
**Scope:** Repository rules, CI/CD, source security review, dependency controls, tests, issues/PRs, branch hygiene, documentation and release readiness.

## Executive summary
FresherFlow has a strong baseline for a small Flask application: CSRF protection, role guards, password hashing, login throttling, upload validation, security response headers, session revocation, audit logging, tests on Python 3.11/3.12, CodeQL and weekly Dependabot updates are present.

The highest-priority repository-level gap is that the active main-branch ruleset requires a pull request but has **zero required approving reviews and an empty required-status-checks list**. Thus CI and CodeQL exist but are not enforced as merge gates by this ruleset. Current default-branch test and CodeQL runs were successful at audit time.

A recent failed test run revealed an unresolved merge-conflict marker in app.py at that historical commit. The current main version of app.py has no conflict marker and latest test run passes; classify this as a resolved historical incident, not a current main-branch bug.

This is a remote repository/source audit, not an executed production penetration test. The GitHub integration could not inspect certain security-alert and branch-protection endpoints, so those are marked unverified below.

## Findings (priority ordered)

### P0 — Enforce successful CI before merging
**Evidence:** Active ruleset `Protect main branch` applies to `refs/heads/main`, blocks deletion and non-fast-forward updates, and requires a pull request. However, `required_status_checks` is empty and `required_approving_review_count` is 0.
**Impact:** A future PR could be merged without requiring the tests or CodeQL workflow to pass.
**Recommendation:** Add required checks after confirming the exact displayed check names in GitHub's ruleset UI. Require the Python 3.11 test, Python 3.12 test (which also runs pip-audit), and CodeQL analysis. For solo maintenance, keeping approval count at 0 can be a deliberate trade-off; required CI checks should still be enforced.
**Link:** https://github.com/deathkernel/FresherFlow/rules/24940063

### P1 — Improve admin login throttling coverage
**Evidence:** Admin login checks and records lockout attempts, but `client_login_key` uses the configured client address plus the attempted identity. Verify the deployment proxy setup and ensure lockout cannot be cheaply bypassed with forwarded-address spoofing; the core helper explicitly avoids trusting X-Forwarded-For without `ProxyFix`.
**Impact:** Misconfigured reverse-proxy handling can weaken brute-force throttling or rate-limit many real users behind shared IPs.
**Recommendation:** Keep `TRUSTED_PROXY_HOPS=0` unless the service is behind a known trusted proxy; when enabled, use the exact hop count. Add a test for forged forwarded headers and the deployed proxy path.
**Links:** https://github.com/deathkernel/FresherFlow/blob/main/security.py and https://github.com/deathkernel/FresherFlow/blob/main/app.py

### P1 — Validate authorization boundaries with adversarial tests
**Evidence:** Role guards validate the user's role and authentication version, employer status is checked, and message/notification queries mostly scope records by the current user. The codebase handles sensitive student profile/resume and employer application data.
**Impact:** Any missed ownership check could expose resumes, applications, message content or allow cross-employer status changes.
**Recommendation:** Add/retain negative tests for cross-user and cross-employer IDOR attempts on student resumes, application status updates, message threads, employer vacancy changes and admin-only actions. A source scan is not proof those paths are safe end-to-end.
**Links:** https://github.com/deathkernel/FresherFlow/blob/main/routes/decorators.py and https://github.com/deathkernel/FresherFlow/blob/main/routes/platform_routes.py

### P1 — Continue strict upload testing and deployment isolation
**Evidence:** Resume validation checks file extension, signature, size and DOCX ZIP expansion/entry bounds. Upload paths are stored outside static files, and resume downloads use authenticated routes.
**Impact:** Upload pipelines remain a common attack surface; signature checks don't prove a document is benign.
**Recommendation:** Keep uploads non-executable/private, test malformed/corrupt OOXML, duplicate ZIP entries, path traversal variants and archive expansion limits, and consider malware scanning/quarantine before real production use.
**Link:** https://github.com/deathkernel/FresherFlow/blob/main/security.py

### P1 — Verify branch and workflow hygiene
**Evidence:** The repository has a set of feature/fix branches, with main protected and several non-main branches reported unprotected. No open PRs were returned in the audit snapshot.
**Impact:** Stale branches are not automatically a vulnerability, but can create drift and make it harder to tell which fixes are in main.
**Recommendation:** Compare each branch against main; archive/delete only after confirming merged or obsolete state. Do not bulk-delete by name alone.
**Link:** https://github.com/deathkernel/FresherFlow/branches

### P2 — Release and project metadata
**Evidence:** Repository API returned no published releases; repository description is empty, license field is unset, and topics are empty.
**Impact:** Contributors and adopters have less context about project status and reuse rights.
**Recommendation:** Add a concise repository description and relevant topics. Add a LICENSE only after deliberately choosing the project's intended terms. Create versioned releases/tags when deployment and versioning are stable; avoid a release workflow purely for appearance.

### P2 — Public vs private data hygiene
**Evidence:** Current recursive file tree contained 106 entries and no filename patterns matching common secrets, private keys, local DB files, resume files or exported documents. `.gitignore` excludes `.env`, the instance DB/secret, uploads/resumes and local personal/project artifacts.
**Limit:** A filename scan and `.gitignore` do not detect secrets embedded in source, prior commits, image files or unusual names.
**Recommendation:** Enable/confirm secret scanning and push protection in GitHub settings where available, audit history if secret exposure is suspected, and rotate any leaked credentials immediately.

### P2 — Product verification beyond source audit
The existing product audit doc explicitly states Lighthouse, axe/accessibility automation, deployed smoke checks and conversion analytics were not run by the repo integration. Don't claim these as completed. Run browser-based checks once a staging/deployed URL is available, including keyboard/screen-reader paths, responsive sizes, registration, resume upload, applying, vacancy creation/moderation and application status changes.
**Link:** https://github.com/deathkernel/FresherFlow/blob/main/docs/COMBINED_AUDIT_2026-10-12.md

## Verified strengths
- `SECURITY.md` contains vulnerability-reporting and production deployment advice.
- `README.md` documents architecture, setup, production secrets, database behavior and core security controls.
- `.github/workflows/tests.yml` runs pytest on Python 3.11 and 3.12; pip-audit runs in the Python 3.12 matrix leg.
- `.github/workflows/security.yml` runs CodeQL on pushes, PRs and a weekly schedule using security-extended queries.
- `.github/dependabot.yml` updates pip and GitHub Actions weekly.
- Latest default-branch test run succeeded for both Python versions; latest pip-audit step succeeded; latest CodeQL analysis job succeeded.
- The current main `app.py` is clean of merge-conflict markers.

## Unverified / limitations
- The GitHub integration denied the classic branch-protection endpoint; active ruleset details were inspected instead.
- The integration did not permit read access to Dependabot alert and code-scanning alert endpoints, so alert count/severity is unknown.
- Runtime tests were not executed locally by this audit; CI evidence is reported from GitHub Actions.
- No live deployment URL was verified, so TLS/proxy configuration, real HTTP headers, app availability, Lighthouse, axe or DAST results are unverified.
- No claim of complete penetration testing or overall vulnerability-free status is made.

## Recommended next actions
1. Set required main-branch CI checks and confirm a test-only PR cannot merge when checks fail.
2. Add adversarial IDOR tests and proxy/login-throttle tests.
3. Review non-main branches against main before cleanup.
4. Confirm secret scanning/push protection and inspect alert status via GitHub Security UI.
5. Run staging end-to-end, accessibility, performance and deployment checks before calling FresherFlow production-ready.