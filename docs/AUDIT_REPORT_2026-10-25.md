# FresherFlow Audit Report — 2026-10-25

## Scope and method

Reviewed the current `main` branch at the time of the audit, including Flask app/configuration, authentication and role decorators, upload validation, SQLite schema/migrations, student/employer/admin/platform/SEO routes, representative Jinja templates, browser JavaScript, dependencies, CI workflows, and existing tests. This was a source-level review through repository files; it was not a live deployment penetration test or a full browser-based accessibility run.

## Findings

### FF-AUD-001 — Production canonical URLs can fall back to the request host

- **Severity:** Medium
- **Area:** Security / SEO configuration
- **Evidence:** `templates/base.html` and `routes/seo_routes.py` use the configured `SEO_BASE_URL` when present, but otherwise fall back to `request.url_root`. Production configuration documented a canonical URL but did not enforce it at startup.
- **Risk:** If production is deployed without a canonical URL, a request with an attacker-controlled Host header may influence canonical/Open Graph links and generated robots/sitemap URLs.
- **Status:** Fixed in PR #24. Production startup now requires `SEO_BASE_URL` to be a valid HTTPS origin (no credentials, path, query, or fragment).
- **Regression coverage:** Tests reject a missing or path-bearing production canonical URL. Existing production cookie test now supplies a valid canonical origin.

### FF-AUD-002 — Public company pages linked to an authenticated job route

- **Severity:** Medium (functional defect)
- **Area:** Public UX / navigation
- **Evidence:** `templates/company.html` linked each public company vacancy to `student.job_details`, which requires a student session.
- **Impact:** Visitors browsing a public company page were redirected to login instead of being able to view the public job detail page.
- **Status:** Fixed in PR #24 by linking to `seo.public_job_detail`.
- **Regression coverage:** Added a test asserting the company page points to `/jobs/<id>`, not `/student/jobs/<id>`.

### FF-AUD-003 — Formatting and lint conventions are not enforced consistently

- **Severity:** Low
- **Area:** Maintainability
- **Evidence:** Some route modules and SEO handlers use compressed statements and inconsistent whitespace, while other modules use conventional multiline formatting. `requirements-dev.txt` currently contains pytest but no formatter/linter, and CI does not enforce formatting.
- **Impact:** Future changes can introduce inconsistent style and make review harder.
- **Recommendation:** Agree on Python formatting/lint rules (for example, Black plus Ruff), format Python in a dedicated low-risk PR, then enforce checks in CI. Adopt a formatter for HTML/Jinja/CSS/JavaScript separately; do not run blind global whitespace rewrites.

### FF-AUD-004 — Browser-level accessibility and responsive validation is not automated

- **Severity:** Low (coverage gap, not a confirmed defect)
- **Area:** UI / accessibility / regression coverage
- **Evidence:** CI runs pytest and dependency auditing but does not run a browser automation or accessibility scanner.
- **Impact:** Mobile layout regressions, keyboard/focus issues, and inaccessible controls may not be caught by the current CI suite.
- **Recommendation:** Add a small Playwright smoke suite for registration/login, public job browsing, student application, employer vacancy management, and admin moderation; add automated accessibility checks where feasible.

## Controls observed in reviewed code

- Global CSRF validation for POST requests.
- Role/session checks in protected routes, with auth-version validation for student/employer sessions and admin password-hash versioning.
- Parameterized SQL in reviewed query paths; dynamic SQL fragments inspected were limited to allow-listed sort clauses or generated placeholder counts.
- Resume and Excel upload size/signature/archive-expansion checks.
- SQLite foreign keys enabled on database connections, with schema constraints and versioned migrations.
- Security headers, non-cacheable dynamic responses, and separate CodeQL and test/dependency-audit workflows.

These controls reduce risk but are not a guarantee that the entire application is vulnerability-free.

## Validation

- PR #24 adds regression tests for FF-AUD-001 and FF-AUD-002.
- GitHub Actions test workflow passed on Python 3.11 and 3.12, including the dependency audit job on Python 3.12, for the audited PR commit.
- CodeQL result should be checked on the latest PR commit before merge.
- No live production penetration test or browser-based visual/accessibility test was performed.

## Recommended next steps

1. Finish reviewing the latest CodeQL result and merge PR #24 only after review.
2. Run a dedicated language-aware formatting/lint pass and add CI enforcement.
3. Add browser smoke/accessibility tests and validate representative pages at mobile and desktop widths.
4. Review backup/restore and migration rollback procedures for SQLite before production deployment.
