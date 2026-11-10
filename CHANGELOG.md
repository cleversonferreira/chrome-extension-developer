# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [SemVer](https://semver.org/).

## [Unreleased]

## [1.0.0] — 2026-11-10

### Added
- `SKILL.md` operating manual: ground-truth table (MV2 removal, `browser.*` in Chrome 148, Promise `onMessage` listeners, service worker termination rules, remote code ban, JSON messaging), request classification, non-negotiable rules, scaffold and maintenance workflows, building-block decision table, debugging playbook, audit checklist, scope (when to use / not use).
- References: manifest, service worker, messaging, content scripts, UI surfaces, storage & state, permissions & security, network & filtering, offscreen & platform, testing & debugging, MV2→MV3 migration, publishing, AI in extensions.
- `scripts/check_manifest.py` zero-dependency manifest and source linter.
- `templates/starter-mv3` runnable no-build starter (popup, options, i18n en/pt_BR, activeTab + scripting).
- Claude Code plugin marketplace packaging, CI workflow, issue/PR templates, English and Portuguese READMEs.
