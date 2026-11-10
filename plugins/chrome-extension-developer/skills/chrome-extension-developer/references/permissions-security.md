# Permissions, security and privacy

Official:
- https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions
- https://developer.chrome.com/docs/extensions/develop/concepts/permission-warnings
- https://developer.chrome.com/docs/extensions/reference/permissions-list
- https://developer.chrome.com/docs/extensions/develop/security-privacy/stay-secure
- https://developer.chrome.com/docs/extensions/develop/security-privacy/user-privacy

## Least privilege, concretely

1. Start with zero permissions; add one per feature, with a comment in the PR explaining it.
2. Replace broad host access with `activeTab` whenever access is user-initiated (action click, context menu, command, accepted omnibox suggestion). `activeTab` grants temporary access to the current tab until navigation/close, **with no install warning**.
3. Use `declarativeNetRequest` (no host warning for block/allow rules) instead of `webRequest`. `declarativeNetRequestWithHostAccess` when redirecting/modifying headers.
4. Put optional capabilities in `optional_permissions` / `optional_host_permissions` and request at use time:

```js
button.addEventListener('click', async () => {
  const granted = await browser.permissions.request({ origins: ['https://*.github.com/*'] });
  if (!granted) return showExplanation();
  // proceed
});
browser.permissions.onRemoved.addListener(({ origins }) => disableFeaturesFor(origins));
```

`permissions.request()` must be called from a user gesture in an extension page.
`permissions.contains()` to check; `permissions.remove()` to drop when no longer needed.

5. Adding a permission that triggers a **new warning** in an update **disables the extension until the user accepts**. Prefer optional permissions for new capabilities.

## Common warnings (what users see)

| Permission | Warning (approx.) |
|---|---|
| `<all_urls>` / `*://*/*` | Read and change all your data on all websites |
| specific host | Read and change your data on example.com |
| `tabs` | Read your browsing history (only needed for `url`/`title`/`favIconUrl` of tabs — **not** for `tabs.create/query/update`) |
| `history`, `topSites`, `webNavigation` | Read your browsing history |
| `bookmarks` | Read and change your bookmarks |
| `downloads` | Manage your downloads |
| `debugger` | Access the page debugger backend; read/change all data |
| `nativeMessaging` | Communicate with cooperating native applications |
| `management` | Manage your apps, extensions, and themes |
| `clipboardRead` | Read data you copy and paste |
| `geolocation` | Detect your physical location |
| `notifications` | Display notifications |
| `storage`, `alarms`, `contextMenus`, `scripting`, `activeTab`, `sidePanel`, `offscreen` | none |

Preview real warnings: pack the extension and install the `.crx`, or use the extension update testing tool.

## Threat model

- **Content scripts** share a renderer with possibly malicious pages: assume every message from them is forged; never send secrets to them; never let them trigger privileged actions with arbitrary parameters (URLs, tab IDs, script code).
- **MAIN world** scripts are fully visible to the page.
- **Web-accessible resources** enable fingerprinting and clickjacking of your pages — keep minimal; never expose privileged pages.
- **externally_connectable** exposes your API to listed origins — validate `sender.origin`.
- **Developer account** compromise = malicious update to all users → 2-step verification with a security key; least-privilege publisher roles.
- **Supply chain**: lockfile, pinned deps, `npm audit`, review bundle diffs before release; avoid unmaintained deps.

## Code-level rules

- No `eval`, `new Function`, `setTimeout(string)`, `innerHTML`/`outerHTML`/`insertAdjacentHTML`/`document.write` with untrusted data. Use `textContent`, DOM APIs, `<template>`.
- Sanitize HTML you must render (bundled DOMPurify) and consider Trusted Types in extension pages (`require-trusted-types-for 'script'` in CSP).
- HTTPS everywhere; pin API base URLs as constants, never from messages.
- Validate URLs with `new URL()` and allow-listed protocols/hosts before opening or fetching.
- Use `crypto.randomUUID()`/`crypto.getRandomValues()`, never `Math.random()`, for tokens/nonces.

## Remotely hosted code (RHC)

Forbidden in MV3 and by store policy: loading JS (or WASM) from outside the package, or
executing strings fetched at runtime. Allowed: fetching **data** (JSON, config, ML model weights)
that does not change logic in a way that bypasses review. Alternatives:
- Bundle libraries; for config-driven behavior use data + fixed interpreter code.
- `userScripts` API for user-provided scripts (user opt-in required).
- Sandboxed page (`"sandbox": { "pages": [...] }`) for `eval`-dependent templating, communicating via `postMessage`.

## API keys and secrets

Never ship secret keys in the package (it's trivially unzipped). Options:
- Proxy through your own server (preferred) with per-user auth.
- Ask the user to supply their own key; store in `storage.local`/`session`.
- Fetch short-lived tokens from your server after authentication.

## Privacy

- Collect the minimum; process locally when possible.
- Publish a privacy policy that matches reality; complete the CWS Privacy tab (single purpose, permission justifications, data-type disclosures, Limited Use certification).
- Get explicit consent before collecting personal or sensitive data, and make it revocable.
- Don't sell data or use it for unrelated purposes (Limited Use policy).
- Analytics (e.g., GA4 via Measurement Protocol from the SW): disclose, anonymize, offer opt-out.
