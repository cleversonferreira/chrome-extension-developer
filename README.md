# chrome-extension-developer

> A [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) skill that turns Claude into a senior **Google Chrome extension** engineer — for building, maintaining, debugging, auditing, migrating and publishing **Manifest V3** extensions, grounded in the official Chrome documentation.

[![CI](https://github.com/cleversonferreira/chrome-extension-developer/actions/workflows/ci.yml/badge.svg)](https://github.com/cleversonferreira/chrome-extension-developer/actions/workflows/ci.yml)
![Manifest V3](https://img.shields.io/badge/Manifest-V3-1a73e8)
![Chrome 148+](https://img.shields.io/badge/browser.*-Chrome%20148%2B-34a853)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## Why this skill?

Most extension advice on the web (and in model training data) is **outdated**: Manifest V2 background pages, `chrome.extension.getURL`, blocking `webRequest`, callback-style APIs, keep-alive hacks. Since **August 31, 2026** every MV2 item has been removed from the Chrome Web Store, and the platform keeps moving (`browser.*` namespace in Chrome 148, Promise-returning `onMessage` listeners, side panel events, `userScripts` toggle…).

This skill gives Claude a current, opinionated playbook so the code it writes is:

- **Modern** — MV3 only, `async/await`, `browser.*` namespace with a compatibility guard, version-gated features flagged with the minimum Chrome version.
- **Robust** — service workers designed for termination (no global state, top-level listeners, alarms instead of timers).
- **Secure** — least-privilege permissions, validated messaging, no remote code, no `innerHTML` sinks.
- **Shippable** — Chrome Web Store listing, privacy fields, review pitfalls, staged rollout, rollback and CI publishing.

## What's inside

```
.
├── .claude-plugin/marketplace.json        # lets Claude Code install this repo as a plugin marketplace
└── plugins/chrome-extension-developer/
    ├── .claude-plugin/plugin.json
    └── skills/chrome-extension-developer/
        ├── SKILL.md                       # the operating manual Claude loads
        ├── references/                    # deep dives, loaded on demand
        │   ├── manifest.md                # every relevant manifest key, CSP, WAR, versioning
        │   ├── service-worker.md          # lifecycle, termination rules, alarms, events
        │   ├── messaging.md               # one-time, ports, external, typed contracts, Chrome 146/148 changes
        │   ├── content-scripts.md         # static/dynamic/programmatic, worlds, SPAs, Shadow DOM
        │   ├── ui-surfaces.md             # popup, side panel, options, menus, commands, i18n, a11y
        │   ├── storage-state.md           # storage areas & quotas, typed wrapper, migrations
        │   ├── permissions-security.md    # warnings, optional permissions, threat model, privacy
        │   ├── network-and-filtering.md   # declarativeNetRequest, webRequest, CORS
        │   ├── offscreen-and-platform.md  # offscreen, userScripts, OAuth, push, native messaging, DevTools
        │   ├── testing-debugging.md       # unit, Puppeteer/Playwright E2E, SW termination tests, CI
        │   ├── migration-mv3.md           # MV2→MV3 grep list and checklist
        │   ├── publishing.md              # Chrome Web Store, review, rollout, API v2
        │   └── ai-in-extensions.md        # built-in AI APIs, cloud AI, API keys, WebMCP
        ├── scripts/check_manifest.py      # zero-dependency manifest + source linter
        └── templates/starter-mv3/         # runnable, no-build starter (popup, options, i18n, activeTab)
```

## Installation

### Option A — as a Claude Code plugin (recommended)

```bash
claude plugin marketplace add cleversonferreira/chrome-extension-developer
claude plugin install chrome-extension-developer@chrome-extension-developer
```

Or inside a session: `/plugin marketplace add cleversonferreira/chrome-extension-developer`, then `/plugin` to install. Updates arrive through the marketplace.

### Option B — as a personal skill (all your projects)

```bash
git clone https://github.com/cleversonferreira/chrome-extension-developer.git
mkdir -p ~/.claude/skills
cp -r chrome-extension-developer/plugins/chrome-extension-developer/skills/chrome-extension-developer ~/.claude/skills/
```

### Option C — as a project skill (shared with your team via git)

```bash
mkdir -p .claude/skills
cp -r /path/to/chrome-extension-developer/plugins/chrome-extension-developer/skills/chrome-extension-developer .claude/skills/
git add .claude/skills/chrome-extension-developer
```

## Usage

Claude loads the skill automatically when your request is about Chrome extensions (a `manifest.json` with `manifest_version`, `chrome.*`/`browser.*` APIs, the Web Store…). You can also invoke it explicitly — `/chrome-extension-developer` as a personal/project skill, or `/chrome-extension-developer:chrome-extension-developer` when installed as a plugin.

Example prompts:

- _"Create a Chrome extension that summarizes the current page in a side panel using the built-in Summarizer API."_
- _"Audit this extension for security and permission issues before I submit it to the Web Store."_
- _"Migrate this MV2 extension to Manifest V3."_
- _"My service worker loses state after a while — fix it."_
- _"Our extension was rejected for 'Purple Potassium'. What do we change?"_
- _"Set up Puppeteer E2E tests, including a service-worker-termination test, and a GitHub Actions workflow."_

### Use the linter directly

```bash
python3 plugins/chrome-extension-developer/skills/chrome-extension-developer/scripts/check_manifest.py path/to/manifest.json
# --json for machine-readable output, --strict to fail on warnings, --no-source-scan to skip JS/HTML scanning
```

It flags MV2 leftovers, broad or risky permissions, unsafe CSP, missing files/icons/locale keys, unscoped web-accessible resources, a leftover dev `key`, and (in shipped JS/HTML) outdated APIs, remote scripts, `eval`, HTML sinks, inline handlers and plain-HTTP URLs.

### Try the starter template

1. Copy `templates/starter-mv3/` somewhere.
2. Open `chrome://extensions`, enable **Developer mode**, click **Load unpacked**, select the folder.
3. Open any web page and click the toolbar icon (or press `Alt+Shift+W`).

It demonstrates `activeTab` + `scripting` (no install-time host warning), a validated message contract, `storage.sync`/`local`, i18n (`en`, `pt_BR`), dark mode and accessible markup. It targets Chrome 148+ (`browser.*`); comment-in the guard and lower `minimum_chrome_version` to support older versions.

## Sources

The guidance is distilled from the official documentation, which always wins in case of conflict:

- [Chrome Extensions docs](https://developer.chrome.com/docs/extensions) — [Get started](https://developer.chrome.com/docs/extensions/get-started), [Develop](https://developer.chrome.com/docs/extensions/develop), [How to](https://developer.chrome.com/docs/extensions/how-to), [Reference](https://developer.chrome.com/docs/extensions/reference), [AI](https://developer.chrome.com/docs/extensions/ai)
- [Chrome Web Store docs](https://developer.chrome.com/docs/webstore) and [Program Policies](https://developer.chrome.com/docs/webstore/program-policies)
- [GoogleChrome/chrome-extensions-samples](https://github.com/GoogleChrome/chrome-extensions-samples)

## Keeping it current

The Chrome platform changes every ~4 weeks. Each reference file links the official pages it is based on. If you spot guidance that no longer matches the docs, please open an **Outdated guidance** issue with the doc link and its "Last updated" date — that is the most valuable contribution you can make.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow, style rules and the review checklist. In short:

1. Fork and create a branch (`docs/messaging-promise-listeners`, `feat/dnr-recipes`…).
2. Keep `SKILL.md` concise; put depth in `references/`.
3. Back every factual claim with an official source; state minimum Chrome versions.
4. Run the checks locally (see CONTRIBUTING) and update `CHANGELOG.md`.
5. Open a pull request.

## Author

Created and maintained by **Cleverson Franco**, with contributions from the community (see the contributors list on GitHub).

## Disclaimer

This is a community project. It is **not affiliated with, endorsed by, or sponsored by Google or Anthropic**. "Chrome" and "Google Chrome" are trademarks of Google LLC; "Claude" is a trademark of Anthropic.

## License

[MIT](LICENSE). Code samples adapted from the Chrome documentation are © Google, licensed under Apache 2.0; documentation text is summarized, not copied, and the original is licensed under CC BY 4.0.
