# FresherFlow — Security and Release-Readiness Audit

**Audit date:** 2026-10-25  
**Repository:** https://github.com/deathkernel/FresherFlow  
**Review basis:** source review of Flask routes, session/CSRF handling, SQLite schema and migrations, uploads, public SEO routes, templates, tests, and GitHub Actions.  
**Status:** code-level audit and regression fixes are in the audit PR; final CI results and live-browser checks must be confirmed separately.

## Executive summary

The inspected code has several good baseline controls: global CSRF validation for POST requests, parameterized SQL, role guards, per-user ownership predicates in employer vacancy/application operations, session-version revocation, password hashing, login throttling, bounded resume uploads, private resume downloads, security headers, and dependency/CodeQL workflows.

The audit found and addressed the public-visibility and deployment URL issues below, added outbound message throttling, and expanded regression tests around tenant/role boundaries. This is a source-code audit, **not** a production penetration test or a certification of WCAG compliance.

## Findings fixed in this PR

### High — Public vacancy/company visibility did not consistently require employer verification
**Risk:** Pending or unverified employers could be discoverable through public/student-facing routes or sitemap/company pages if a route checked only active account state.  
**Fix:** Public vacancy details/listings, student-facing job visibility, company pages, and sitemap entries require active and verified employer status.  
**Regression coverage:** Verified/unverified employer visibility cases in tests/test_seo.py and related tests.

### Medium — Company-page job links used a student-authenticated route
**Risk:** Public visitors could be sent to a route that requires a student login rather than the public vacancy page.  
**Fix:** Company job cards use the public job-detail endpoint.  
**Regression coverage:** Company-page link target test.

### Medium — Production canonical URLs depended on deployment configuration without strict origin validation
**Risk:** Incorrect or unsafe SEO base URL configuration could generate bad canonical/OG URLs.  
**Fix:** Production requires a valid HTTPS origin for SEO_BASE_URL; malformed values, credentials, paths, query strings, and fragments are rejected.  
**Regression coverage:** Production configuration tests.

### Medium — Outbound messaging had no sender-level volume guard
**Risk:** An authenticated account could generate unbounded messages and message notifications in a short period.  
**Fix:** Limit a sender to 20 messages per 10-minute window, with user-facing feedback when the limit is reached. The existing messages index supports the sender/time lookup.  
**Regression coverage:** Test verifies the 21st message is rejected and no extra message is persisted.

### Regression coverage — Cross-employer access boundaries
Added tests that one employer cannot edit another employer's vacancy or change the status of an application belonging to another employer, and that a student cannot enter the employer dashboard.

## Existing controls reviewed

- Global CSRF validation for POST requests.
- Role guards, per-user session-version checks, and admin session invalidation when the configured password hash changes.
- Login attempt throttling and cleanup of stale attempts.
- Parameterized database queries in inspected routes.
- Employer ownership predicates for vacancy editing/status changes and application-status changes.
- Student-scoped notifications, saved jobs, applications, and resume access.
- Resume extension/signature/size checks and XLSX archive expansion limits.
- SQLite foreign-key enforcement and schema migrations.
- Production secret/admin credential requirements, secure cookies, CSP and other security headers.
- GitHub Actions test matrix, dependency audit, and CodeQL.

These are source-review observations; they do not imply every possible input or deployment configuration has been dynamically tested.

## Validation

- Existing CI workflow runs pytest on Python 3.11 and 3.12 and audits dependencies.
- CodeQL security analysis runs on pull requests.
- New/updated tests are included in the audit PR; final pass/fail status must be checked on the latest PR head after CI completes.
- No live deployment URL was provided to this repository integration, so production DAST, Lighthouse, axe/WAVE, screen-reader testing, and responsive browser testing were not executed.

## Remaining validation before calling the release audit fully closed

1. Confirm the latest PR CI test matrix, dependency audit, and CodeQL are green.
2. Run fresh-install and upgrade-path migration tests against representative older database snapshots; exercise backup/restore and interrupted migration recovery.
3. Run browser end-to-end journeys for registration/login, profile/resume upload, job search/apply/save, employer job creation/editing, moderation, and messaging.
4. Run manual keyboard/screen-reader checks plus axe/WAVE; verify focus order, form errors, heading structure, contrast, zoom, and touch targets.
5. Measure Lighthouse mobile/desktop and inspect real deployment TLS/proxy/HSTS behavior. Do not claim performance scores without measurements.

## Scope limitations

This audit did not include a live production penetration test, third-party account access, real-user analytics/CRO measurement, or browser automation against a deployed instance. Those items require a staging/deployed environment and should remain explicitly unverified until run.
