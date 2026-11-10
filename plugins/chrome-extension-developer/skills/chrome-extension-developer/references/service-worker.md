# Extension service worker

Official:
- https://developer.chrome.com/docs/extensions/develop/concepts/service-workers
- https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle
- https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/events

## Lifecycle

Install / update (store update, or reload of an unpacked extension):

1. `install` (SW event)
2. `runtime.onInstalled` (extension event; also fires when **Chrome** updates) — `details.reason` is `install`, `update`, `chrome_update`, or `shared_module_update`
3. `activate` (SW event; fires immediately, no page reload concept)

Profile start: `runtime.onStartup` fires; no SW lifecycle events.

## Termination rules

Chrome terminates the extension SW when:

- **30 s of inactivity** (events and extension API calls reset the timer);
- a single event/API call takes **> 5 minutes**;
- a `fetch()` response takes **> 30 s** to arrive.

Lifetime improvements to rely on (set `minimum_chrome_version` if you depend on them):

| Chrome | Change |
|---|---|
| 105 | `runtime.connectNative()` port keeps SW alive. |
| 109 | Messages from an offscreen document reset timers. |
| 110 | Extension API calls reset timers. |
| 114 | Sending a message over a long-lived port keeps SW alive (opening one does not). |
| 116 | Active WebSocket traffic extends lifetime; prompt-style APIs (`permissions.request`, `identity.launchWebAuthFlow`, `desktopCapture.chooseDesktopMedia`, `management.uninstall`) may exceed 5 min. |
| 118 | Active `debugger` sessions keep SW alive. |
| 120 | `alarms` minimum period is 30 s. |

**Do not** build keep-alive hacks (pinging ports, opening tabs). Design for termination instead,
and avoid keeping the SW alive indefinitely — it costs users memory and battery.

## Rules

1. **Register listeners synchronously at the top level.** Chrome wakes the SW to dispatch an
   event; if the listener is attached after an `await`, the event is lost.

   ```js
   // ❌ wrong
   const settings = await browser.storage.local.get();
   browser.action.onClicked.addListener(handle);

   // ✅ right
   const settingsReady = browser.storage.local.get();
   browser.action.onClicked.addListener(async (tab) => {
     const settings = await settingsReady;
     // ...
   });
   ```

2. **No state in globals.** Use `storage.session` (in-memory, 10 MB, cleared on restart/update),
   `storage.local` (disk, 10 MB, or unlimited with `unlimitedStorage`), IndexedDB, or CacheStorage.
   Globals are fine only as a cache that is rebuilt from storage.

3. **No DOM, no `window`, no `localStorage`, no `XMLHttpRequest`.** Use `fetch`, and an offscreen
   document for DOM-dependent work.

4. **No dynamic `import()`** in the SW. Static imports with `"type": "module"`, or `importScripts()` in classic workers (top level only).

5. **Timers**: `setTimeout`/`setInterval` die with the SW. Use `browser.alarms` for anything
   longer than a few seconds; alarms are not exact and may not persist across browser restarts —
   recreate on `onStartup`/`onInstalled` if missing.

6. **Idempotent startup.** `onInstalled` can fire for Chrome updates; make setup re-runnable
   (`contextMenus.removeAll()` then create; check alarms before creating).

7. **Long work**: chunk it, checkpoint progress in storage, and continue on the next alarm or
   event. For streaming/real-time, use WebSocket (Chrome 116+) or Web Push.

## Event routing pattern

```ts
// background/index.ts
import { handleMessage } from './messages';
import { onInstalled } from './install';
import { onAlarm } from './alarms';

browser.runtime.onInstalled.addListener(onInstalled);
browser.runtime.onMessage.addListener(handleMessage);
browser.alarms.onAlarm.addListener(onAlarm);
browser.tabs.onRemoved.addListener((tabId) => browser.storage.session.remove(`tab:${tabId}`));
```

Keep each handler in its own module; the entry file only wires listeners.

## Event filters

Filter at registration to avoid waking the SW unnecessarily:

```js
browser.webNavigation.onCompleted.addListener(onDone, {
  url: [{ hostSuffix: 'example.com', schemes: ['https'] }],
});
```

## Updates

- `runtime.onUpdateAvailable` → call `runtime.reload()` when safe (e.g., no active work) to apply the update sooner; otherwise it applies on next idle/restart.
- Write versioned, idempotent storage migrations keyed on `previousVersion`.
