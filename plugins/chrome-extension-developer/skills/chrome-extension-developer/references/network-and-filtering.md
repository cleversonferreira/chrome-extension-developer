# Network requests and content filtering

Official:
- https://developer.chrome.com/docs/extensions/develop/concepts/content-filtering
- https://developer.chrome.com/docs/extensions/reference/api/declarativeNetRequest
- https://developer.chrome.com/docs/extensions/reference/api/webRequest
- https://developer.chrome.com/docs/extensions/develop/concepts/network-requests

## Cross-origin requests

- **Service worker / extension pages**: `fetch()` to any origin in `host_permissions` bypasses CORS. Without host permission, normal CORS applies.
- **Content scripts**: same CORS rules as the page → route requests through the SW.
- Never let a message choose the request URL; build it from constants + validated parameters.

## declarativeNetRequest (DNR)

Declarative rules evaluated by the browser — no code runs per request, no access to request
bodies, privacy-friendly. Permissions:

- `declarativeNetRequest` — block/allow/upgradeScheme without host warnings.
- `declarativeNetRequestWithHostAccess` — needed (with host permissions) for `redirect` and `modifyHeaders`.
- `declarativeNetRequestFeedback` — `getMatchedRules()` / `onRuleMatchedDebug` (debug unpacked only).

Rule types: **static** (rulesets in the package, enable/disable with `updateEnabledRulesets`),
**dynamic** (`updateDynamicRules`, persist across sessions/updates), **session**
(`updateSessionRules`, cleared on restart). Limits (rule counts, enabled rulesets, regex rules)
change across versions — read them at runtime from constants such as
`MAX_NUMBER_OF_DYNAMIC_RULES`, `GUARANTEED_MINIMUM_STATIC_RULES`, `MAX_NUMBER_OF_REGEX_RULES`, and
check the reference page before relying on a number.

```json
// rules/default.json
[
  {
    "id": 1,
    "priority": 1,
    "action": { "type": "block" },
    "condition": { "urlFilter": "||ads.example.com^", "resourceTypes": ["script", "image", "sub_frame"] }
  },
  {
    "id": 2,
    "priority": 2,
    "action": {
      "type": "modifyHeaders",
      "requestHeaders": [{ "header": "x-ext-client", "operation": "set", "value": "1" }]
    },
    "condition": { "requestDomains": ["api.example.com"], "resourceTypes": ["xmlhttprequest"] }
  }
]
```

```js
// Dynamic rule from user input (validated)
await browser.declarativeNetRequest.updateDynamicRules({
  removeRuleIds: [1000],
  addRules: [{
    id: 1000, priority: 1,
    action: { type: 'block' },
    condition: { requestDomains: [validatedDomain], resourceTypes: ['main_frame'] },
  }],
});
```

Tips:
- Prefer `requestDomains`/`initiatorDomains` over `urlFilter` strings for clarity and speed.
- Use `isUrlFilterValid` / `isRegexSupported` before adding user-supplied filters.
- Test with `testMatchOutcome()` (unpacked) and `getMatchedRules()`.
- Use `allowAllRequests` with high priority to exempt sites (allow-list), and `upgradeScheme` for HTTPS upgrades.

## webRequest (observational)

In MV3, `webRequest` listeners are **non-blocking** for regular extensions (blocking requires
`webRequestBlocking` and policy installation, i.e. enterprise). `webRequestAuthProvider` allows
`onAuthRequired` handling. Use it to observe/log, not to modify — modifications belong in DNR.
Always pass a filter (`{ urls: [...], types: [...] }`) to avoid waking the SW for every request.

## webNavigation

Lifecycle of navigations per frame (`onBeforeNavigate`, `onCommitted`, `onDOMContentLoaded`,
`onCompleted`, `onHistoryStateUpdated` for SPAs). Requires `webNavigation` (history warning).
Use event URL filters.

## Proxy, privacy, contentSettings

`proxy.settings.set` (permission `proxy`), `privacy.*` settings, `contentSettings` per-site
toggles — high-trust permissions; justify carefully in the store listing.
