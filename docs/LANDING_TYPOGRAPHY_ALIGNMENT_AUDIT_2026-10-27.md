# Landing page typography and alignment audit — 2026-10-27

## Scope
- Hero heading wrapping and line-height
- Section and card heading/paragraph rhythm
- Responsive widths (320, 390, 768, 1024 and 1440 CSS pixels)
- Large-text customization preference
- Horizontal overflow and heading bounds

## Changes
- Added scoped landing-page typography rules for balanced heading wrapping and readable paragraph line-height.
- Kept card and proof-strip content shrinkable to reduce overflow risk.
- Made hero and final CTA buttons wrap safely on small screens.
- Added explicit landing typography rules for `data-font-scale="large"`.
- Added Playwright checks for responsive heading bounds, horizontal overflow, section heading visibility and large-text scaling.

## Validation
Automated browser tests are configured in `.github/workflows/ui-accessibility.yml`. The results must be checked on the pull request before merge. This audit does not claim a local browser run.
