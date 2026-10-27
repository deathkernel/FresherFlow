# FresherFlow Feature & Security Audit — 2026-10-27

## Executive summary

This is a source-level audit of the current working branch `fix/bulk-ui-audit-2026-10-27`, intended to cover the product's documented features across public, student, employer, and administrator flows. It is not a claim of complete assurance: this run did not execute the application in a browser, run DAST against a live instance, or independently rerun the full test suite. A literal "100% secure / bug-free" certification is not possible from source review alone.

### Priority snapshot

| ID | Priority | Area | Finding | Status |
|---|---|---|---|---|
| FF-FEAT-001 | High | Student apply / employer verification | Apply endpoint does not enforce the same employer verification predicate used by public listing, job details, and save-job routes. | Open; fix recommended |
| FF-FEAT-002 | Medium | Employer dashboard / analytics | "Live" vacancy counts are not fully consistent with public visibility: dashboard count excludes expired jobs after the current patch, but it does not check employer verification/account status; analytics has a different count predicate and also omits deadline filtering. | Open; fix recommended |
| FF-FEAT-003 | Medium | UI / accessibility | Current CI does not run browser-level smoke tests or automated accessibility checks. Visual behavior such as the admin setup layout and responsive dashboards needs browser verification. | Coverage gap |
| FF-FEAT-004 | Medium | Auth/config test isolation | Local admin credentials previously caused three local tests to fail with `admin123`; current branch now limits local-file credential loading to development and isolates those tests, but the updated suite still needs a fresh run. | Fix pushed; retest pending |
| FF-FEAT-005 | Low | Maintainability | CI runs pytest and dependency audit, but no enforced Python formatter/linter or template/CSS/JS checks were found in the reviewed workflow. | Improvement |
| FF-FEAT-006 | Low | Runtime compatibility | CI covers Python 3.11 and 3.12; local testing was performed on Python 3.15.2. The supported runtime matrix does not yet include 3.15. | Verify / decide support |

## Scope reviewed

- Flask app factory, request lifecycle, CSRF enforcement, error handlers, security headers and trusted-proxy configuration.
- Environment/session configuration and administrator credential loading.
- Authentication, registration, logout, role decorators and session invalidation.
- Student dashboard/profile/resume upload, job search/detail, save/apply, applications and password change.
- Employer dashboard/profile, vacancy create/edit/publish/status, bulk form and Excel import, applications, resume downloads, messaging and analytics.
- Admin dashboard, vacancy moderation, application views, employer verification/suspension/removal, resume access and audit logging.
- Notifications, messages, preferences, public company/job pages, robots/sitemap, SQLite schema/migrations, tests and GitHub Actions workflows.
- Existing audit documents and current PR #32 context.

## Detailed findings

### FF-FEAT-001 — Apply endpoint has weaker visibility checks than public job discovery

**Priority:** High  
**Area:** Student workflow / business rules

The public job list, student job details and save-job endpoint require the employer to be both active and verified. The student apply endpoint checks that the vacancy is active and approved and that the employer account is active, but it does not require `ep.verification_status='verified'`.

This creates inconsistent rules: a student may submit an application directly to a vacancy that is no longer visible in public discovery because the employer's verification was moved back to pending after an organization profile change. The route should use the same publication/eligibility predicate as public discovery, including employer verification and the deadline condition.

**Recommended regression tests**
- A verified, active employer with an approved live vacancy can receive an application.
- A pending/rejected/unverified employer's vacancy cannot be applied to, even with a direct POST.
- Suspended employer, closed/rejected/pending vacancy, and expired deadline are rejected.
- Duplicate applications remain blocked.

### FF-FEAT-002 — "Live vacancies" is calculated differently across employer surfaces

**Priority:** Medium  
**Area:** Dashboard / analytics consistency

The employer dashboard now filters live jobs to active, approved and non-expired vacancies. It does not join the employer profile to require active + verified status. The employer analytics query uses a separate, looser predicate (active + approved only) and omits deadline filtering. Public discovery requires active + verified employer, active + approved vacancy, and a non-expired deadline.

As a result, dashboard/profile/analytics numbers can disagree with each other and with what students can actually see, particularly after an employer profile edit causes re-verification.

**Recommended remediation**
- Centralize the "public/live vacancy" SQL predicate or consistently apply it in each count query.
- Include active employer account, verified employer, active vacancy, approved moderation and no expired deadline.
- Add tests comparing dashboard/profile/analytics counts against the same seeded set of visible, pending, expired, rejected and suspended cases.

### FF-FEAT-003 — Browser and accessibility validation is not part of CI

**Priority:** Medium  
**Area:** UX / accessibility / regression coverage

The reviewed CI workflow runs pytest on Python 3.11 and 3.12 and runs `pip-audit` in the 3.12 job. The CodeQL workflow performs static analysis. No Playwright/browser test or automated accessibility scan was found in the reviewed workflows.

Server-side tests cannot reliably catch stylesheet load failures, broken visual layout, overflow, keyboard/focus problems, contrast regressions, or client-side JavaScript errors.

**Recommended remediation**
- Add a small Playwright smoke suite for registration/login, public job browsing, student apply/save, employer vacancy creation/moderation feedback, and admin moderation.
- Exercise desktop and mobile viewport sizes.
- Add axe-core or equivalent accessibility checks for representative pages.
- Keep manual keyboard-only and screen-reader checks as explicit release checklist items.

### FF-FEAT-004 — Local admin credential test isolation

**Priority:** Medium  
**Area:** Configuration / test reliability

The user reported three failing tests where `get_admin_credentials()` unexpectedly returned `admin123` despite the test clearing `ADMIN_EMAIL` and `ADMIN_PASSWORD_HASH`. The branch changes now restrict local credentials-file loading to the development environment and mock the local credential provider in tests that explicitly assert "no credentials configured."

The intended behavior is safer and more deterministic, but the latest complete test run after these changes has not been independently observed during this audit. Do not mark the fix verified until the full suite and CI pass.

### FF-FEAT-005 — Static quality gates are incomplete

**Priority:** Low  
**Area:** Maintainability / CI

The reviewed workflows cover automated tests, dependency auditing and CodeQL. No enforced Python formatter/linter or HTML/Jinja/CSS/JavaScript lint step was found in the reviewed workflow files.

**Recommended remediation**
- Introduce Ruff (and optionally Black) with a dedicated, reviewed cleanup rather than a blind repository-wide rewrite.
- Add suitable template/CSS/JavaScript checks if they fit the project stack.
- Fail CI on new violations after existing findings are resolved or baselined.

### FF-FEAT-006 — Runtime support matrix excludes the locally used Python version

**Priority:** Low  
**Area:** Compatibility

The README and CI define Python 3.11+ / test matrix 3.11 and 3.12, while the user's local environment is Python 3.15.2. The reported prior suite passed 86 tests on 3.15 before subsequent changes, but the current branch has not been freshly validated end-to-end on that interpreter.

**Recommended remediation**
- Keep 3.11 and 3.12 as declared supported CI versions unless project requirements change.
- Consider adding Python 3.13/3.14/3.15 to a non-blocking compatibility matrix only after dependencies and deployment runtime are verified.

## Feature coverage matrix

| Feature area | Source-reviewed | Automated tests observed in repository | Remaining validation |
|---|---|---|---|
| Public landing, job search/details, company pages, SEO metadata, robots and sitemap | Yes | SEO tests present | Browser navigation and metadata validation |
| Student registration/login/logout | Yes | Workflow/auth tests present | Browser form validation and error states |
| Student profile, resume upload/replacement/download | Yes | Workflow/security coverage exists | More malformed-file and lifecycle checks |
| Job search/filter/sort, save/unsave, apply, application history | Yes | Workflow tests present | Add verification-state apply test (FF-FEAT-001) |
| Employer profile and re-verification | Yes | Partial workflow coverage | Verify previously approved listings become non-public immediately |
| Vacancy create/edit/draft/publish/status and moderation | Yes | Workflow tests present | Cross-surface live-count parity tests (FF-FEAT-002) |
| Excel bulk vacancy import | Yes | Source-reviewed; targeted test coverage should be confirmed in full suite | Large/invalid workbook boundary tests |
| Employer applications, applicant resumes and candidate status | Yes | Workflow/hardening coverage exists | Explicit cross-employer IDOR matrix |
| Notifications and preferences | Yes | Customization/workflow tests present | Check each notification category and disabled preference |
| Student-employer messaging | Yes | Message read/access tests present | Role-pair, rate-limit and long-message browser checks |
| Admin login, one-time local setup, moderation, employer lifecycle, audit log | Yes | Admin/security/workflow tests present | Full admin journey and updated credential regression run |
| Password change/session invalidation | Yes | Customization/hardening tests present | Verify both roles, all old sessions and password boundary cases |
| Security controls (CSRF, sessions, headers, upload validation, rate limiting) | Source-reviewed | Security/hardening tests and CodeQL workflow exist | Authorized staging DAST / penetration test remains unperformed |
| Responsive UI/accessibility | Partial source review | No browser/accessibility CI found | Playwright + axe and manual keyboard/mobile verification |
| Database migration and recovery | Schema/migrations reviewed | Existing tests cover fresh DB behavior | Upgrade tests from real prior schema snapshots and backup/restore drill |
| Production deployment | Config/docs reviewed | Production config tests present | TLS/reverse-proxy, secrets, WSGI, permissions and deployment smoke test |

## Validation status and limits

- A previous user-provided local run reported **86 passed, 3 failed** before the latest configuration/test-isolation changes were pulled.
- The latest reported source changes include the live-vacancy regression test and admin credential test isolation; this audit did not execute a new local test run.
- GitHub Actions status for the latest commit must be checked before merge.
- No live production target was tested; no destructive tests were run.
- This document is a source-level feature audit, not a guarantee that every possible defect has been found.

## Recommended fix order

1. Fix FF-FEAT-001 so the apply route enforces the same employer verification/public visibility rules as the listing.
2. Fix FF-FEAT-002 by aligning dashboard, profile and analytics live counts.
3. Pull the branch in the correct worktree and run the complete pytest suite; resolve every failure before merging.
4. Verify CI, dependency audit and CodeQL on the latest PR commit.
5. Add browser smoke/accessibility tests and manually inspect Student, Employer and Admin pages at desktop/mobile widths.
6. Run authorized staging security checks and test database upgrade/backup recovery before any production deployment.
