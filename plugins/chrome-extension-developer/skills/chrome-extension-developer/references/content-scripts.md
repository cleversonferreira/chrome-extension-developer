# Content scripts

Official: https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts ·
https://developer.chrome.com/docs/extensions/reference/api/scripting ·
https://developer.chrome.com/docs/extensions/develop/concepts/match-patterns

## Three ways to inject

| Method | When | Requirements |
|---|---|---|
| Static (`content_scripts` in manifest) | Always run on known sites | `matches` (grants host access, shows warning) |
| Dynamic (`scripting.registerContentScripts`) | User opts sites in/out at runtime | `scripting` + host permission (often optional) |
| Programmatic (`scripting.executeScript` / `insertCSS`) | On demand (action click, context menu, command) | `scripting` + `activeTab` or host permission |

```js
// Programmatic: on toolbar click, no install-time host warning
browser.action.onClicked.addListener(async (tab) => {
  if (!tab.id || !/^https?:/.test(tab.url ?? '')) return;
  const [{ result }] = await browser.scripting.executeScript({
    target: { tabId: tab.id },
    func: (max) => document.body.innerText.slice(0, max),   // serialized; no closures
    args: [50_000],
  });
});
```

```js
// Dynamic registration after the user grants a site
await browser.permissions.request({ origins: ['https://news.example.com/*'] });
await browser.scripting.registerContentScripts([{
  id: 'news-enhancer',
  matches: ['https://news.example.com/*'],
  js: ['content/news.js'],
  runAt: 'document_idle',
  persistAcrossSessions: true,
}]);
```

Registered scripts survive browser restarts when `persistAcrossSessions: true` (the default).
(Contrast: `userScripts` registrations are cleared on extension update and must be re-added in
`onInstalled`.) Call `getRegisteredContentScripts({ ids })` before registering to avoid
duplicate-ID errors, and use `updateContentScripts()` to change existing ones.

## Worlds

- **ISOLATED** (default): own JS globals, shares the DOM with the page, can use `runtime`, `storage`, `i18n`, messaging. The page cannot see your variables.
- **MAIN**: runs in the page's JS context — can read page variables / patch `fetch`, but **no extension APIs** and the page can tamper with everything. Use only when strictly needed.

Bridge MAIN ↔ ISOLATED with `window.postMessage` or `CustomEvent`, using a random/nonce
channel name and validating `event.source === window` and the payload shape.

```json
{ "matches": ["https://app.example.com/*"], "js": ["inject/main.js"], "world": "MAIN", "run_at": "document_start" }
```

## Timing

`run_at`: `document_start` (before DOM — good for CSS/early hooks), `document_end`
(DOM ready, subresources loading), `document_idle` (default, recommended).

## SPAs and dynamic pages

Content scripts run once per document load. For client-side routing:

- Observe DOM with a scoped `MutationObserver` (debounce; disconnect when done).
- Or listen in the SW to `webNavigation.onHistoryStateUpdated` and message the tab.
- Listen to the Navigation API (`navigation.addEventListener('navigate', …)`) in MAIN world if necessary.

## UI injected into pages

- Mount inside a **Shadow DOM** host element to isolate styles from the page (`attachShadow({ mode: 'closed' })`).
- Load assets via `runtime.getURL()` — they must be listed in `web_accessible_resources` if the *page* fetches them (e.g., `<img src>` in the page DOM).
- Never inject `<script src>` from remote origins.

## Restrictions

Cannot run on: `chrome://`, `chrome-extension://` of other extensions, the Chrome Web Store,
`view-source:`, most `about:` pages, and `file://` unless the user enables *Allow access to file URLs*.
Use `match_origin_as_fallback: true` to run in `about:blank`/`blob:`/`data:` frames created by matched origins.

## Communication & fetch

- Content scripts are subject to the **page's CORS**. Do cross-origin requests in the SW and message results back.
- Keep content scripts thin: gather DOM data → send to SW → apply results. Business logic and secrets stay in the SW.

## Cleanup on update/disable

When the extension reloads, old content scripts are orphaned (`runtime.id` becomes undefined,
messaging throws "Extension context invalidated"). Detect and tear down:

```js
function isContextValid() { try { return !!browser.runtime?.id; } catch { return false; } }
```

On `onInstalled` (`reason === 'update'`), re-inject into open tabs if the feature requires it.
