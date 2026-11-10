# Migrating Manifest V2 → V3 (and modernizing old MV3 code)

Official: https://developer.chrome.com/docs/extensions/develop/migrate ·
/develop/migrate/checklist · /develop/migrate/mv2-deprecation-timeline · /develop/migrate/known-issues

## Status (late 2026)

MV2 is disabled in all Chrome channels (Chrome 138; enterprise policy removed in 139), and on
**Aug 31 2026** all remaining MV2 items were removed from the Chrome Web Store. An MV2
extension today can only be rescued by a full MV3 rewrite and a new (or restored) listing.

## Grep list — outdated APIs and patterns

| Search for | Replace with |
|---|---|
| `"manifest_version": 2` | `3` |
| `"background": { "scripts"` / `"page"` / `"persistent"` | `"service_worker"` (+ `"type": "module"`) |
| `browser_action`, `page_action`, `chrome.browserAction`, `chrome.pageAction` | `action`, `chrome.action` (use `declarativeContent` or `action.disable/enable` for page-action behavior) |
| host patterns in `permissions` | `host_permissions` / `optional_host_permissions` |
| `"content_security_policy": "..."` (string) | object `{ "extension_pages": "...", "sandbox": "..." }` |
| `web_accessible_resources: ["a.png"]` | `[{ "resources": [...], "matches": [...] }]` |
| `chrome.extension.getURL` | `runtime.getURL` |
| `chrome.extension.getBackgroundPage`, `runtime.getBackgroundPage` | messaging / `storage` (no background page exists) |
| `chrome.extension.sendRequest/onRequest` | `runtime.sendMessage/onMessage` |
| `chrome.tabs.executeScript`, `tabs.insertCSS`, `tabs.removeCSS` | `scripting.executeScript`, `scripting.insertCSS`, `scripting.removeCSS` (+ `scripting` permission) |
| `code: "..."` string injection | `func` + `args`, or `files` |
| `webRequestBlocking` / `{ blocking: true }` | `declarativeNetRequest` rules |
| `localStorage` / `window` / `document` in background | `storage.*`, offscreen document |
| `XMLHttpRequest` in background | `fetch` |
| `setInterval` / long `setTimeout` in background | `alarms` |
| `eval`, `new Function`, remote `<script src>` | bundled code, sandboxed page, `userScripts` |
| `chrome.runtime.lastError` checks everywhere | `try/catch` around awaited Promises |
| `webextension-polyfill` | native `browser.*` (Chrome 148+) — remove once users are on 148+ |
| `chrome.identity` with MV2 OAuth tricks | `getAuthToken` / `launchWebAuthFlow` |

## Migration steps

1. **Manifest** — convert keys per the table; run `scripts/check_manifest.py`.
2. **Background → service worker** — remove DOM use; move state to storage; register listeners at top level; replace timers with alarms; move DOM work to an offscreen document.
3. **API calls** — swap renamed APIs; convert callbacks to Promises.
4. **Blocking webRequest → DNR** — express logic as static rulesets + dynamic rules; complex per-request logic may need redesign (DNR has no access to bodies).
5. **Security** — remove remote code; tighten CSP; scope WAR with `matches`.
6. **Test** — every feature, including SW termination and update from the previous version (storage migration).
7. **Publish** — the update must keep permission warnings as stable as possible; new warnings disable the extension until the user re-approves.

## Modernizing "old MV3" (2021–2024 era) code

- Replace callback APIs with `await`.
- Adopt `browser.*` (with guard or `minimum_chrome_version: "148"`).
- Use `storage.session` instead of in-memory globals.
- Replace keep-alive hacks (port pinging, `chrome.runtime.getPlatformInfo` loops, offscreen keep-alive) with alarms, WebSocket, or push.
- Use `sidePanel` instead of injected iframes for companion UIs.
- Use `runtime.getContexts()` instead of `clients.matchAll()` / `getViews()`.
- Remove `webextension-polyfill` once users are on Chrome 148+.
