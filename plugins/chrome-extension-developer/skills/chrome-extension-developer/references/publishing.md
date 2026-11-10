# Publishing and maintaining on the Chrome Web Store

Official: https://developer.chrome.com/docs/webstore · /webstore/publish · /webstore/program-policies ·
/webstore/best-practices · /webstore/review-process · /webstore/using-api · /webstore/api

## Before the first upload

- Register a developer account (one-time fee), verify email, enable **2-Step Verification with a security key**; use a group publisher with least-privilege roles if multiple people publish.
- New publishers can have **2 published extensions** initially (limit can be raised later; themes excluded).
- Narrow **single purpose**; policies: user data, deceptive behavior, spam/repetitive content, keyword stuffing, minimum functionality, affiliate ads, RHC ban.

## Package

- Zip the **build output** with `manifest.json` at the root (not the source folder; no `node_modules`, `.git`, source maps unless intended, tests, `.env`).
- Remove the dev-only `key` field.
- Bump `version`. Max package size 2 GB.
- Run `scripts/check_manifest.py dist/manifest.json` and an E2E smoke test on the zip contents.

## Store listing

- Name/summary consistent with the manifest; detailed description that explains features and permissions in plain language.
- Store icon 128×128; at least one screenshot **1280×800** (or 640×400), up to 5; small promo tile 440×280; optional marquee 1400×560; optional YouTube video.
- Category, language(s), support URL / email, homepage, privacy policy URL.
- Localize the listing for each `_locales` language you support.

## Privacy tab

- Single-purpose description.
- **Justification for every permission** and host permission (reviewers compare with code).
- Remote code declaration ("No, I am not using remote code").
- Data usage disclosures (types collected) + certifications (no selling, no unrelated use, no creditworthiness use) — must match the privacy policy.

## Test instructions

If features need an account or specific setup, provide test credentials and steps — missing
access is a common rejection reason.

## Review

- Broad host permissions, sensitive permissions, obfuscated code, or large code changes lengthen review. Minified code is fine; **obfuscated** code is not.
- Some updates qualify to **skip review** (e.g., limited metadata changes) — see the skip-review doc.
- **Deferred publishing**: uncheck auto-publish; after approval you have **30 days** to publish before it reverts to draft.
- **Cancel review** to replace a buggy submission.

## Rollout and recovery

- **Staged rollout** (percentage deployment) for extensions with enough users; ramp gradually and watch error/uninstall metrics.
- **Rollback** to the previous version from the dashboard (or API) if something breaks.
- Raising `minimum_chrome_version` freezes users on older Chrome — decide with analytics.
- New permission warnings disable the extension for existing users until they accept — prefer optional permissions.

## Common rejection reasons → fixes

| Rejection | Fix |
|---|---|
| Purple Potassium (excessive permissions) | Remove unused permissions; switch to `activeTab`/optional. |
| Blue Argon (remote code) | Bundle all JS; remove CDN scripts/eval of fetched code. |
| Yellow Magnesium (functionality not working) | Provide test instructions/credentials; fix broken flows. |
| Red Titanium (obfuscation) | Ship readable/minified code, not obfuscated. |
| User data / privacy violations | Privacy policy, accurate disclosures, consent, HTTPS, Limited Use. |
| Yellow Zinc (metadata) | Accurate description/screenshots, no keyword stuffing, icon present. |
| Single purpose violation | Split unrelated features into separate extensions. |

(Codes evolve — always read the violation email and the troubleshooting page.)

## Publishing from CI (Chrome Web Store API v2)

Endpoints under `publishers.items` (v2): `media.upload`, `publish`, `fetchStatus`,
`cancelSubmission`, `rollback`, `setPublishedDeployPercentage`, `queryMetrics`,
`fetchReviews`, `getRatingSummary`. Auth with an OAuth client / service account authorized
for the publisher. Typical GitHub Actions flow:

1. On tag `v*`: install, test, build, zip.
2. Upload zip (`media.upload`) → poll `fetchStatus`.
3. `publish` (optionally with deferred publishing or initial deploy percentage).
4. Later: `setPublishedDeployPercentage` to ramp; `rollback` on incident.

Store credentials as encrypted CI secrets; never commit tokens. Verify exact request shapes in
the v2 REST reference before writing the workflow (v1 is legacy).

## Self-hosting / enterprise

- Off-store installs are only possible via enterprise policy (`ExtensionInstallForcelist` with `update_url`) or on Linux with external extension JSON files. See /how-to/distribute.
- Private/unlisted store visibility or domain-restricted publishing is usually simpler for internal tools.

## After launch

- Respond to reviews and support requests; keep a public changelog.
- Monitor CWS metrics (installs, uninstalls, weekly users) and optional GA4 events.
- Subscribe to the Chromium Extensions Google Group / Chrome blog and "What's new in Chrome extensions" for API changes and deprecations.
