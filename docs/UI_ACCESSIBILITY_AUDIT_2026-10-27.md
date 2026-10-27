# FresherFlow UI / Accessibility Audit — 2026-10-27

## Scope

This change adds a browser-based regression layer for public-facing pages. It intentionally does not redesign existing screens or change authentication, job discovery, or form submission behavior.

## Source-verified starting point

- `templates/base.html` includes a skip link targeting `#main-content`.
- `templates/index.html` provides the public landing page and responsive navigation.
- `static/css/ui-audit-fixes.css` includes focus-visible styling, reduced-motion rules, and mobile layout rules.
- `templates/settings.html` exposes theme, text-size, and reduce-motion preferences.
- The existing test workflow covers pytest, Ruff, and dependency auditing; browser and accessibility automation were not previously configured in the reviewed workflow.

## Changes in this PR

- Add a separate GitHub Actions workflow for browser-level UI and accessibility checks.
- Use Playwright with Chromium to smoke-test the landing page, login, registration, and public job listing routes.
- Verify the landing page skip link is the first keyboard focus target and points to the main content.
- Check the landing page for horizontal overflow at a 390px viewport width.
- Run axe-core against WCAG 2.0/2.1 A and AA tags on representative public pages. The workflow fails on serious or critical violations and prints all detected violations for review.

## Validation status

The checks are executable in GitHub Actions; their pass/fail status must be read from the workflow run for the PR commit. No claim is made here that browser tests or axe scans passed before CI executes.

## Follow-up

- Review all axe findings, including moderate/minor findings, and remediate reproducible issues in focused changes.
- Extend browser coverage to authenticated student, employer, and admin flows using isolated test data and test-only accounts.
- Keep manual keyboard-only, screen-reader, zoom, contrast, and forced-colors checks in the release checklist.
