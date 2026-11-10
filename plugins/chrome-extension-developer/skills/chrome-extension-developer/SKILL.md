---
name: chrome-extension-developer
description: Expert guidance for building, maintaining, debugging, auditing, migrating and publishing Google Chrome extensions (Manifest V3) — manifest.json, service workers, content scripts, messaging, storage, popup/side panel/options UI, declarativeNetRequest, offscreen documents, userScripts, permissions, security, testing (Puppeteer/Playwright/unit), and Chrome Web Store submission. Use whenever the user works on a browser/Chrome extension, a manifest.json with manifest_version, chrome.* or browser.* extension APIs, MV2→MV3 migration, or a Chrome Web Store listing or rejection.
---

# Google Chrome Extension Developer

You are acting as a senior Chrome extension engineer. Your output must follow the **current
official Chrome documentation** (developer.chrome.com/docs/extensions), not patterns from old
blog posts or Manifest V2 tutorials.

This file is the operating manual. Deep, topic-specific guidance lives in `references/` —
load only the file(s) the task needs (see the routing table at the end).

## When to use this skill

- Creating a new Chrome extension, or adding features to an existing one.
- Implementing or debugging service workers, content scripts, popup / side panel / options pages, and message passing between contexts.
- Using extension APIs: `storage`, `tabs`, `scripting`, `alarms`, `sidePanel`, `offscreen`, `declarativeNetRequest`, `permissions`, `identity`, `userScripts`, etc.
- Migrating Manifest V2 → V3, auditing security/permissions, or fixing Chrome Web Store rejections.
- Packaging, testing and publishing (including CI publishing via the Chrome Web Store API).

## When NOT to use it (or use with care)

- **Safari Web Extensions** — they need an Xcode app wrapper and have API gaps; only the shared WebExtensions code is in scope.
- **Firefox-only / Edge-only specifics** — the `browser.*` code you write here is largely portable, but Firefox differs (event pages/background scripts allowed, structured-clone messaging, `browser_specific_settings`, different store). Flag differences instead of assuming parity.
- **Plain web apps** or PWAs that never touch extension APIs.
- **Chrome Apps / NaCl / MV2-only techniques** — obsolete; do not produce them.

---

## 0. Ground truth (as of the Chrome 148–152 era, late 2026)

Internalize these before writing any code. They are the most common sources of outdated advice.

| Fact | Consequence |
|---|---|
| **Manifest V2 is dead.** Disabled for all users since Chrome 138/139 (Jul 2025); all remaining MV2 items were removed from the Chrome Web Store on **Aug 31 2026**. | Never generate MV2 code (`background.scripts`, `persistent`, `browser_action`, `page_action`, blocking `webRequest`, `chrome.extension.getURL`, string `content_security_policy`). Treat any MV2 code you find as a migration task. |
| **`browser.*` namespace** is available from **Chrome 148**; `browser === chrome` objects (`chrome.tabs === browser.tabs`). `chrome.*` keeps working. Extensions with a `devtools_page` get `browser` only from **Chrome 152**. | New extension → set `"minimum_chrome_version": "148"` and use `browser.*`. Existing extension with older users → add the runtime guard (`globalThis.browser ??= chrome`). `webextension-polyfill` becomes a no-op on 148+. |
| **`runtime.onMessage` listeners may return a Promise / be `async`** (Chrome 148, gradual rollout). Throwing/rejecting in a listener rejects the sender's `sendMessage()` (Chrome 146, gradual). | Prefer `return true` + `sendResponse` when you must support users whose rollout hasn't landed, or when the extension has a DevTools page. Never register an `async` listener that ignores some messages — it answers `null` and steals the response. |
| **Service worker is ephemeral.** Terminated after 30 s idle, if one event/API call runs > 5 min, or a `fetch()` response takes > 30 s. | No state in globals. Register listeners synchronously at top level. Persist to `storage.session`/`storage.local`/IndexedDB. Use `alarms` (min period 30 s, Chrome 120+), not `setInterval`. |
| **No remotely hosted code.** All JS must ship in the package. | No `<script src="https://…">`, no `eval`/`new Function` of fetched code, no CDN libraries. Bundle everything. Use a sandboxed page if `eval` is unavoidable. AI models are data, not code — allowed. |
| Messaging uses **JSON serialization** in Chrome (not structured clone), 64 MiB max. | `undefined` → `null`; no `Map`, `Set`, `Date`, `Blob`, class instances, functions. Serialize explicitly. |

When in doubt about a version-gated detail, **verify against the live docs** (WebFetch the
relevant `developer.chrome.com/docs/extensions/reference/api/<name>` page) rather than relying on memory.

---

## 1. How to work

### 1.1 Classify the request first

1. **New extension** → §2 scaffold workflow.
2. **Feature on an existing extension** → read `manifest.json` + the entry points it references *before* editing. Respect the existing toolchain (Vite/WXT/Plasmo/webpack/none), language (TS/JS) and namespace choice.
3. **Bug / "it stopped working"** → §5 debugging playbook.
4. **Audit / review / "is this safe?"** → §6 audit checklist; run `scripts/check_manifest.py`.
5. **MV2 → MV3 migration** → `references/migration-mv3.md`.
6. **Chrome Web Store submission or rejection** → `references/publishing.md`.

### 1.2 Non-negotiable rules for every change

- **Least privilege.** Every permission and host pattern must be justified by code that uses it. Prefer `activeTab` + `scripting` over `<all_urls>`. Put rarely-used powers in `optional_permissions` / `optional_host_permissions` and request them at the moment of use with `permissions.request()` (needs a user gesture).
- **Content scripts are untrusted.** Validate every message in the service worker (type allow-list, schema, `sender.id === browser.runtime.id`, expected `sender.origin`/`sender.tab`). Never let a content script make the extension fetch an arbitrary URL or call an API with arbitrary arguments. Never send secrets to content scripts.
- **No `innerHTML`/`document.write`/`eval` with dynamic data.** Use `textContent`, `createElement`, `<template>` cloning, or a vetted sanitizer.
- **HTTPS only** for every network request.
- **Async everywhere.** All extension APIs return Promises in MV3 — use `async/await`, wrap in `try/catch`, check `browser.runtime.lastError` only in callback-style code.
- **Top-level listener registration** in the service worker; never inside `await`, `then`, or another listener.
- **Handle the "receiving end does not exist" case** when messaging tabs (content script not injected yet, restricted page like `chrome://`, the Web Store, or PDF viewer).
- **i18n-ready strings** (`_locales/*/messages.json` + `__MSG_key__` in manifest) when the extension has UI.
- **Bump `version`** in `manifest.json` for every release (1–4 dot-separated integers, 0–65535 each).

### 1.3 Code style

- TypeScript preferred (`@types/chrome`), strict mode. Small pure functions; side effects at the edges (listeners).
- One typed message contract shared by all contexts (discriminated union on `type`). See `references/messaging.md`.
- One `storage` wrapper with typed keys and defaults. See `references/storage-state.md`.
- Structure by context: `background/`, `content/`, `popup/`, `sidepanel/`, `options/`, `offscreen/`, `shared/`.
- Descriptive names (`isEnabled`, `hasHostPermission`), JSDoc on exported functions, no dead code.
- Log with a prefix (`[ext:sw]`, `[ext:cs]`) and keep debug logging behind a flag.

---

## 2. Workflow: new extension from scratch

1. **Define the single purpose** in one sentence (Chrome Web Store policy requires a narrow, easy-to-understand purpose). Everything else is scope creep.
2. **Pick the UI surface(s)** — see the decision table in §3.
3. **Pick the toolchain.**
   - Tiny/no-deps → plain ES modules, no build (`templates/starter-mv3/` in this skill).
   - Real product → Vite + TypeScript (or a framework like WXT/CRXJS if the user already uses it). Output must be a self-contained folder with `manifest.json` at its root.
4. **Write the manifest** (see `references/manifest.md`) — start from the minimal template below and add only what the features need.
5. **Implement the service worker** as an event router (install/update setup, messaging, alarms, context menus).
6. **Implement content scripts** only if you must read/modify page DOM; choose static vs. programmatic injection (see `references/content-scripts.md`).
7. **Implement UI pages** (popup/side panel/options) — they are normal extension pages with full API access.
8. **Persist state** in `storage` — never in SW globals.
9. **Add tests** — unit tests with a mocked `chrome`/`browser`, E2E with Puppeteer or Playwright (see `references/testing-debugging.md`).
10. **Run `python3 scripts/check_manifest.py path/to/manifest.json`** and fix findings.
11. **Load unpacked** at `chrome://extensions` (Developer mode), test, then package and publish.

### Minimal modern manifest

```json
{
  "manifest_version": 3,
  "name": "__MSG_extName__",
  "description": "__MSG_extDescription__",
  "version": "1.0.0",
  "default_locale": "en",
  "minimum_chrome_version": "148",
  "icons": { "16": "icons/16.png", "32": "icons/32.png", "48": "icons/48.png", "128": "icons/128.png" },
  "action": { "default_title": "__MSG_actionTitle__", "default_popup": "popup/popup.html" },
  "background": { "service_worker": "background/service-worker.js", "type": "module" },
  "permissions": ["storage", "activeTab", "scripting"]
}
```

Add `host_permissions`, `content_scripts`, `side_panel`, `options_page`/`options_ui`, `commands`,
`web_accessible_resources`, `declarative_net_request`, etc. **only when a feature needs them.**

### Service worker skeleton (modern, `browser.*`)

```js
// background/service-worker.js
// For users below Chrome 148, uncomment the guard (or import it first from shared/browser.js):
// globalThis.browser ??= chrome;

const DEFAULT_SETTINGS = { enabled: true, count: 0 };

// 1) Listeners registered synchronously at top level — always.
browser.runtime.onInstalled.addListener(async ({ reason, previousVersion }) => {
  if (reason === 'install') {
    await browser.storage.local.set({ settings: DEFAULT_SETTINGS });
  }
  if (reason === 'update') {
    await migrateStorage(previousVersion);
  }
  // Context menus persist across restarts but must be (re)created on install/update.
  await browser.contextMenus.removeAll();
  browser.contextMenus.create({ id: 'count-selection', title: 'Count words', contexts: ['selection'] });
});

browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (sender.id !== browser.runtime.id) return;          // only our own contexts
  const handler = HANDLERS[message?.type];
  if (!handler) return;                                    // not ours → let others answer
  handler(message, sender)
    .then((data) => sendResponse({ ok: true, data }))
    .catch((err) => sendResponse({ ok: false, error: String(err?.message ?? err) }));
  return true;                                             // async response (works on every version)
});

browser.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'sync') await syncNow();
});

browser.runtime.onStartup.addListener(ensureAlarms);
browser.runtime.onInstalled.addListener(ensureAlarms);

// 2) Pure handlers — state always read from storage.
const HANDLERS = {
  async GET_COUNT() {
    const { settings = DEFAULT_SETTINGS } = await browser.storage.local.get('settings');
    return settings.count;
  },
  async INCREMENT() {
    const { settings = DEFAULT_SETTINGS } = await browser.storage.local.get('settings');
    const next = { ...settings, count: settings.count + 1 };
    await browser.storage.local.set({ settings: next });
    return next.count;
  },
};

async function ensureAlarms() {
  if (!(await browser.alarms.get('sync'))) {
    await browser.alarms.create('sync', { periodInMinutes: 30 });
  }
}
async function syncNow() { /* idempotent work only */ }
async function migrateStorage(previousVersion) { /* versioned, idempotent migrations */ }
```

Note the differences from the outdated pattern: no storage callbacks, no global counters,
alarms created idempotently (they can survive restarts but aren't guaranteed to), menus
recreated on install/update, sender validation, a structured `{ ok, data | error }` response.

---

## 3. Choosing the right building block

| Need | Use | Notes |
|---|---|---|
| Quick UI on toolbar click | `action` + `default_popup` | Popup closes on blur; persist everything immediately. |
| Persistent companion UI | `sidePanel` (`side_panel.default_path`) | `setPanelBehavior({ openPanelOnActionClick: true })`; `open()` needs a user gesture; per-tab via `setOptions({ tabId })`; `close()`/`onOpened` (141+), `onClosed` (142+). |
| Settings | `options_ui` (`open_in_tab: false`) or `options_page` | Save to `storage.sync` (≈100 KB total, 8 KB/item). |
| Run code on toolbar click without a popup | `action.onClicked` + `scripting.executeScript` + `activeTab` | No install-time host warning. |
| Modify specific sites always | static `content_scripts` + matching `host_permissions` | Narrow `matches`; `run_at: document_idle` by default. |
| Inject on demand / per user choice | `scripting.executeScript` / `scripting.registerContentScripts` | Dynamic registrations persist; handle `persistAcrossSessions`. |
| Access page's own JS variables | `world: "MAIN"` script | Main world is hostile/shared with the page — no extension APIs there; bridge via `window.postMessage` + validation. |
| Run user-supplied scripts (userscript manager) | `userScripts` API | User must enable **Allow User Scripts** per-extension (Chrome 138+; Developer mode before). Detect with a try/catch around `userScripts.getScripts()`. |
| Block/redirect/modify requests | `declarativeNetRequest` (static rulesets, dynamic/session rules) | Blocking `webRequest` is enterprise-only in MV3. |
| Observe requests | `webRequest` (non-blocking) / `webNavigation` | Needs host permissions. |
| DOM APIs in background (DOMParser, clipboard, audio, getUserMedia, Blob URLs) | `offscreen` document | One open at a time; `runtime` is its only extension API; check with `runtime.getContexts()` (or `offscreen.hasDocument()` on 150+). |
| Periodic work | `alarms` | Min 30 s (Chrome 120+). Not exact; reschedule on startup if missing. |
| Real-time server push | Web Push / `gcm`, or WebSocket in SW (keeps it alive, Chrome 116+) | Avoid keep-alive hacks. |
| Keyboard shortcut | `commands` (`_execute_action`, `_execute_side_panel`… plus custom) | Max 4 suggested shortcuts. |
| Google sign-in / OAuth | `identity.getAuthToken` (Google) / `identity.launchWebAuthFlow` (others) | Needs a stable extension ID (`key`) during development. |
| Talk to a local app | Native messaging (`connectNative`) | Host manifest installed separately per OS. |
| Talk to your website | `externally_connectable.matches` + `runtime.onMessageExternal` | Validate `sender.origin`. Extensions cannot message web pages first. |
| On-device AI (summarize/translate/prompt) | Built-in AI APIs (Prompt, Summarizer, Translator, Language Detector, Writer, Rewriter, Proofreader) | Feature-detect availability; trigger model download after install; see `references/ai-in-extensions.md`. |

Full detail for each: `references/ui-surfaces.md`, `references/content-scripts.md`,
`references/network-and-filtering.md`, `references/offscreen-and-platform.md`.

---

## 4. Maintenance workflow (existing extension)

1. **Inventory**: read `manifest.json`; list contexts, permissions, host patterns, WAR, CSP, `minimum_chrome_version`, build tooling, tests.
2. **Run the checker**: `python3 scripts/check_manifest.py manifest.json` (MV2 leftovers, risky permissions, broad hosts, CSP issues, missing icons/locales, version format).
3. **Search for outdated APIs** (see `references/migration-mv3.md` § "grep list"): `chrome.extension.getURL`, `getBackgroundPage`, `browserAction`, `pageAction`, `webRequestBlocking`, `tabs.executeScript`, `tabs.insertCSS`, `localStorage` in SW, `setInterval` keep-alives, `XMLHttpRequest` in SW.
4. **Check SW robustness**: globals used as state? listeners registered after `await`? long tasks > 5 min?
5. **Check messaging**: unvalidated senders? `async` listeners swallowing messages? non-JSON payloads?
6. **Decide namespace strategy** (§0) using real user Chrome-version analytics before raising `minimum_chrome_version` — raising it freezes users on older Chrome at their current version.
7. **Ship safely**: bump `version`, write a changelog entry, use staged rollout (percentage deployment) and keep rollback in mind.

---

## 5. Debugging playbook

| Symptom | Likely cause → fix |
|---|---|
| Listener never fires after a while | Registered asynchronously or inside another callback → move to top level. |
| State "randomly" resets | SW was terminated → move globals to `storage.session`/`local`. |
| `Could not establish connection. Receiving end does not exist.` | No content script in that tab (not injected yet, restricted URL, tab predates install) → inject with `scripting.executeScript` or catch and degrade. Also happens when no listener returns a response. |
| `The message port closed before a response was received.` | Listener did async work without `return true` (or without returning a Promise on 148+). |
| Response is `null` unexpectedly | An `async` listener returned `undefined` first; or `undefined`/non-JSON payload. |
| `Refused to execute inline script` / CSP errors in popup | Inline `<script>` or `onclick=` attributes → move to external module file, use `addEventListener`. |
| `Cannot access contents of url` / `chrome://` errors | Extensions can't script `chrome://`, the Web Store, other extensions, or (without permission) `file://`. |
| Content script can't call `fetch` to your API | CORS applies to content scripts → do the request in the SW (with host permission) and message the result back. |
| Side panel doesn't open | `sidePanel.open()` outside a user gesture, or missing `sidePanel` permission/`side_panel` key. |
| `userScripts` is undefined | User hasn't enabled **Allow User Scripts** (138+) / Developer mode (older). |
| Works unpacked, fails in store build | Bundler emitted remote/inline code, wrong paths, missing files in the zip, or `key` left in manifest. |

Inspect: `chrome://extensions` → *Inspect views: service worker*; popup → right-click *Inspect*;
content scripts → page DevTools → *Sources › Content scripts* and the context dropdown in Console;
storage → DevTools *Application › Extension storage*; also `chrome://serviceworker-internals`.
Simulate SW termination: *Stop* button in `chrome://serviceworker-internals` or the Puppeteer
recipe in `references/testing-debugging.md`.

---

## 6. Audit checklist (security, privacy, quality)

Run through this before every release or when asked to review:

- [ ] `manifest_version` is 3; no MV2 keys.
- [ ] Every entry in `permissions`/`host_permissions` is used; broad hosts (`<all_urls>`, `*://*/*`) justified or replaced by `activeTab`/optional permissions.
- [ ] `content_security_policy.extension_pages` not weakened (no remote hosts, no `unsafe-eval`; `wasm-unsafe-eval` only if WASM is used).
- [ ] No remotely hosted code; all libraries bundled; no `eval`/`new Function`/`setTimeout(string)` outside a sandboxed page.
- [ ] `web_accessible_resources` minimal, scoped with `matches` (and `use_dynamic_url` where fingerprinting matters).
- [ ] `externally_connectable` restricted to exact origins/IDs; external senders validated.
- [ ] All `onMessage` handlers validate `sender` and message shape; no arbitrary URL/argument passthrough.
- [ ] No secrets/API keys shipped in the package (proxy through your server or ask the user for their key); sensitive data in `storage.session` or encrypted.
- [ ] No `innerHTML` with untrusted data; DOM built safely.
- [ ] All network traffic HTTPS.
- [ ] Privacy policy matches actual data collection; Limited Use requirements met; data disclosures in the CWS Privacy tab are accurate.
- [ ] Accessibility: keyboard reachable UI, ARIA labels, visible focus, contrast, respects `prefers-color-scheme`/`prefers-reduced-motion`.
- [ ] i18n: user-visible strings in `_locales`; `default_locale` set when `_locales` exists.
- [ ] Tests pass, including a "service worker was terminated" scenario.

---

## 7. Output expectations

- Give **complete, runnable files** (with paths), not fragments, when creating something new; give minimal, precise diffs when editing.
- Explain *why* a permission is needed whenever you add one, and mention the install-time warning it triggers.
- When a feature is version-gated, state the minimum Chrome version and either set `minimum_chrome_version` or add feature detection.
- After changes, tell the user exactly how to verify: reload at `chrome://extensions`, what to click, which DevTools view to open.
- Cite the official doc page for non-obvious API behavior.
- Never invent API names or options. If unsure, fetch the reference page.

---

## 8. Reference routing table

| Topic | File |
|---|---|
| Manifest keys, icons, versioning, CSP, WAR, `key`, `minimum_chrome_version` | `references/manifest.md` |
| Service worker lifecycle, events, alarms, keeping work alive correctly | `references/service-worker.md` |
| One-time messages, ports, external & native messaging, typed contracts | `references/messaging.md` |
| Static/dynamic/programmatic content scripts, worlds, isolated world, SPA navigation | `references/content-scripts.md` |
| Popup, side panel, options, context menus, omnibox, notifications, commands, overrides, i18n, a11y | `references/ui-surfaces.md` |
| storage areas & quotas, typed wrapper, migrations, IndexedDB, cookies | `references/storage-state.md` |
| Permissions, warnings, optional permissions, security & privacy | `references/permissions-security.md` |
| declarativeNetRequest, webRequest, webNavigation, cross-origin fetch | `references/network-and-filtering.md` |
| Offscreen documents, userScripts, identity/OAuth, WebSockets, push, native messaging, DevTools extensions | `references/offscreen-and-platform.md` |
| Unit/E2E testing, Puppeteer/Playwright, SW termination tests, CI, debugging tools | `references/testing-debugging.md` |
| MV2→MV3 migration checklist and grep list | `references/migration-mv3.md` |
| Chrome Web Store listing, privacy fields, review, rollout, rollback, API v2, CI publishing | `references/publishing.md` |
| Built-in AI APIs, cloud AI, API key handling, WebMCP | `references/ai-in-extensions.md` |
| Starter project (no build) | `templates/starter-mv3/` |
| Manifest linter | `scripts/check_manifest.py` |

Official entry points: https://developer.chrome.com/docs/extensions ·
/get-started · /develop · /how-to · /reference · /reference/api · /reference/manifest ·
/reference/permissions-list · https://developer.chrome.com/docs/webstore ·
samples: https://github.com/GoogleChrome/chrome-extensions-samples
