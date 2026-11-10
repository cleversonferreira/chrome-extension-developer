# Contributing

Thanks for helping keep Claude's Chrome extension guidance accurate! Contributions in English
or Portuguese are welcome (skill files are written in English so they work for everyone).

## Ways to contribute

- **Report drift** — the Chrome docs changed and the skill didn't. Open an *Outdated guidance* issue with the official link and its "Last updated" date.
- **Improve a reference** — clearer explanations, missing pitfalls, better recipes.
- **Add recipes/templates** — e.g. a Vite + TypeScript starter, a side-panel starter, DNR recipes.
- **Improve the linter** — new checks in `scripts/check_manifest.py` (with a test case).
- **Share failing prompts** — a prompt where Claude did the wrong thing even with the skill loaded.

## Ground rules

1. **Official sources first.** Every factual claim must be traceable to developer.chrome.com (or the Chrome Web Store docs, Chromium blog, or W3C WebExtensions CG). Link it in the PR.
2. **State versions.** Anything introduced or changed after Chrome 120 must name its minimum Chrome version.
3. **No MV2.** Never add MV2 patterns except in `migration-mv3.md` as "replace X with Y".
4. **Secure samples.** No `innerHTML`/`eval` with untrusted data, no remote code, validated messages, least privilege.
5. **Progressive disclosure.** `SKILL.md` is loaded into context on every use — keep it short and route to `references/`. Each reference should stand on its own.
6. **Don't copy docs verbatim.** Summarize in your own words and link the source (docs text is CC BY 4.0; samples Apache 2.0 — keep attribution when adapting code).
7. **Namespace.** Use `browser.*` in samples; use `chrome.*` only where a feature requires it (e.g. `devtools_page` before Chrome 152) and say why.

## Local checks

```bash
SKILL=plugins/chrome-extension-developer/skills/chrome-extension-developer
python3 $SKILL/scripts/check_manifest.py $SKILL/templates/starter-mv3/manifest.json --strict
find $SKILL/templates -name '*.js' -print0 | xargs -0 -n1 node --check
claude plugin validate .                                   # marketplace
claude plugin validate ./plugins/chrome-extension-developer # plugin
```

Manual test: load `templates/starter-mv3` unpacked in Chrome and exercise the popup and options page.

Testing the skill itself: install it locally (`claude plugin marketplace add ./` from the repo root, or copy the skill folder to `~/.claude/skills/`), then run a few representative prompts from the README and check the output follows the rules in `SKILL.md`.

## Workflow

1. Fork, then branch: `docs/…`, `feat/…`, `fix/…`.
2. Make focused commits ([Conventional Commits](https://www.conventionalcommits.org/) appreciated: `docs(messaging): document Chrome 148 promise listeners`).
3. Update `CHANGELOG.md` under *Unreleased*.
4. Open a PR using the template; CI must pass.
5. A maintainer reviews against the checklist; we may ask for an official source.

## Releases

Maintainers bump `version` in `plugins/chrome-extension-developer/.claude-plugin/plugin.json`,
move *Unreleased* entries to a dated version in `CHANGELOG.md`, and tag `vX.Y.Z`.
Semantic versioning: major = restructuring/renamed paths, minor = new guidance/templates, patch = corrections.

## Code of conduct

Be kind, assume good faith, and keep discussions technical. Harassment of any kind is not tolerated.
