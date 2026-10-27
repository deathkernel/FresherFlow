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
- Verify the landing page skip link is the first keyboard focus target, points to the main content, and moves focus to that target when activated with Enter.
- Check the landing page for horizontal overflow at a 390px viewport width.
- Run axe-core against WCAG 2.0/2.1 A and AA tags on representative public pages. The workflow fails on serious or critical violations and prints all detected violations for review, including a dedicated dark-theme landing-page scan.
- The first browser run identified low-contrast secondary text and a landing-page brand accessible-name mismatch. Targeted contrast overrides now respect Light, Dark, and System appearance settings, and the brand link uses its visible text as its accessible name.
- Disable persisted checkout credentials in the browser workflow because the job does not require authenticated Git operations.

## Validation status

The checks are executable in GitHub Actions. The current PR head is being revalidated after the latest theme, keyboard, and workflow-hardening fixes; use the latest commit's workflow results as the source of truth.

## Follow-up

- Review all axe findings, including moderate/minor findings, and remediate reproducible issues in focused changes.
- Extend browser coverage to authenticated student, employer, and admin flows using isolated test data and test-only accounts.
- Keep manual keyboard-only, screen-reader, zoom, contrast, and forced-colors checks in the release checklist.
