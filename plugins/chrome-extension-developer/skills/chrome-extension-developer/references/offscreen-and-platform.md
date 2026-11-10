# Offscreen documents, userScripts and platform integrations

## Offscreen documents (Chrome 109+)

Official: https://developer.chrome.com/docs/extensions/reference/api/offscreen

Hidden extension page that gives the SW access to DOM APIs.

- Permission: `offscreen`. URL must be a bundled static HTML file.
- `runtime` is the **only** extension API available inside it → talk via messaging.
- **One** offscreen document open at a time per profile (split incognito: one per profile).
- `reasons` (≥1) + `justification` required: `AUDIO_PLAYBACK` (auto-closes after 30 s of silence), `CLIPBOARD`, `DOM_PARSER`, `DOM_SCRAPING`, `IFRAME_SCRIPTING`, `BLOBS`, `USER_MEDIA`, `DISPLAY_MEDIA`, `WEB_RTC`, `LOCAL_STORAGE`, `WORKERS`, `BATTERY_STATUS`, `MATCH_MEDIA`, `GEOLOCATION`, `TESTING`.
- Check existence with `runtime.getContexts({ contextTypes: ['OFFSCREEN_DOCUMENT'] })` (116+) or `offscreen.hasDocument()` (150+).

```js
let creating;
async function ensureOffscreen(path = 'offscreen/offscreen.html') {
  const url = browser.runtime.getURL(path);
  const existing = await browser.runtime.getContexts({ contextTypes: ['OFFSCREEN_DOCUMENT'], documentUrls: [url] });
  if (existing.length) return;
  creating ??= browser.offscreen.createDocument({ url: path, reasons: ['DOM_PARSER'], justification: 'Parse HTML returned by the API' })
    .finally(() => { creating = undefined; });
  await creating;
}
```

Address messages to it explicitly (`{ target: 'offscreen', ... }`) and have other listeners ignore them. Close it when done (`offscreen.closeDocument()`).

## userScripts (Chrome 120+)

Official: https://developer.chrome.com/docs/extensions/reference/api/userScripts

For userscript managers — running code the **user** provides. Requires `userScripts` permission,
host permissions, **and** the user enabling **Allow User Scripts** on the extension's details page
(Chrome 138+; before that, Developer mode). When disabled, `browser.userScripts` is undefined.

```js
function isUserScriptsAvailable() {
  try { browser.userScripts.getScripts(); return true; } catch { return false; }
}
await browser.userScripts.configureWorld({ csp: "script-src 'self'", messaging: true });
await browser.userScripts.register([{ id: 'u1', matches: ['https://example.com/*'], js: [{ code: userCode }] }]);
```

- Worlds: `USER_SCRIPT` (default, exempt from page CSP) or `MAIN`; multiple worlds via `worldId` (133+).
- One-shot injection: `userScripts.execute()` (135+).
- Messages arrive on `runtime.onUserScriptMessage` / `onUserScriptConnect` (less trusted — validate).
- Registrations are **cleared on extension update** → re-register in `onInstalled` (`reason === 'update'`).
- Not a loophole for remote code in non-userscript extensions — store policy still applies.

## identity / OAuth

Official: https://developer.chrome.com/docs/extensions/how-to/integrate/oauth

- Google accounts: `identity.getAuthToken({ interactive: true })` with `oauth2.client_id` (type "Chrome extension") + `scopes` in the manifest. Pin the ID with `key` during development so the OAuth client matches.
- Other providers / non-Chrome-signed-in users: `identity.launchWebAuthFlow({ url, interactive: true })`, redirect URI `https://<extension-id>.chromiumapp.org/`. Use PKCE; keep client secrets on your server.
- Cache tokens in `storage.session`; handle revocation (`removeCachedAuthToken`).

## Real-time updates

Official: https://developer.chrome.com/docs/extensions/develop/concepts/real-time

- **Web Push** (`self.registration.pushManager.subscribe`, `userVisibleOnly: false` allowed for extensions) or `gcm` / FCM — wakes the SW without keep-alives.
- **WebSockets** in the SW (Chrome 116+) keep it alive while traffic flows; send a heartbeat < 30 s and reconnect on close.
- Polling: `alarms` (≥ 30 s).

## Native messaging

Official: https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging

- Permission `nativeMessaging`; host manifest JSON registered per OS (registry on Windows, `NativeMessagingHosts` dirs on macOS/Linux) with `allowed_origins: ["chrome-extension://<id>/"]`.
- Messages are length-prefixed JSON over stdio (1 MB from host, 64 MiB to host).
- `connectNative` port keeps the SW alive; reconnect in `onDisconnect`.

## DevTools extensions

Official: https://developer.chrome.com/docs/extensions/how-to/devtools/extend-devtools

- `devtools_page` creates panels/sidebars (`devtools.panels`), inspects the page (`devtools.inspectedWindow.eval`), network (`devtools.network`), recorder plugins.
- Declaring `devtools_page` disables the `browser` namespace for the whole extension until Chrome 152 and disables Promise-returning `onMessage` listeners — use `chrome.*` + `return true` there.

## Other web platform features

- Screen/tab capture: `tabCapture.getMediaStreamId` + offscreen `getUserMedia`, or `desktopCapture`.
- Geolocation: `geolocation` permission; from the SW use an offscreen document.
- WebHID/WebUSB: request device in an extension page (user gesture), then use it from the SW.
- Origin trials: add the token to the manifest `trial_tokens` key.
- `chrome.debugger` (CDP): extremely powerful — only with strong justification.
