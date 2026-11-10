# Testing and debugging

Official:
- https://developer.chrome.com/docs/extensions/how-to/test/unit-testing
- https://developer.chrome.com/docs/extensions/how-to/test/end-to-end-testing
- https://developer.chrome.com/docs/extensions/how-to/test/puppeteer
- https://developer.chrome.com/docs/extensions/how-to/test/test-serviceworker-termination-with-puppeteer
- https://developer.chrome.com/docs/extensions/get-started/tutorial/debug

## Strategy

1. **Unit** — pure logic (parsers, reducers, validators, rule builders). Keep extension API calls at the edges so most code needs no mocks.
2. **Integration** — handlers with a mocked `browser`/`chrome`.
3. **E2E** — real Chrome with the unpacked build loaded (Puppeteer, Playwright, Selenium, WebDriverIO).
4. **Manual smoke** — reload at `chrome://extensions`, exercise each surface, check errors panel.

## Unit tests with a mocked API (Vitest/Jest)

```ts
// test/setup.ts
import { vi } from 'vitest';
const store: Record<string, unknown> = {};
const api = {
  runtime: { id: 'test-id', sendMessage: vi.fn(), onMessage: { addListener: vi.fn() }, getURL: (p: string) => `chrome-extension://test-id/${p}` },
  storage: {
    local: {
      get: vi.fn(async (k?: string | string[]) => (k == null ? { ...store } : Object.fromEntries([k].flat().filter((x) => x in store).map((x) => [x, store[x]])))),
      set: vi.fn(async (o: Record<string, unknown>) => { Object.assign(store, o); }),
      remove: vi.fn(async (k: string | string[]) => { [k].flat().forEach((x) => delete store[x]); }),
    },
  },
};
(globalThis as any).chrome = api;
(globalThis as any).browser = api;
```

Alternatives: `jest-chrome`/`vitest-chrome`-style mock libraries, or `sinon-chrome`. Reset mocks between tests.

## E2E with Puppeteer

```js
import puppeteer from 'puppeteer';
const EXT = new URL('../dist', import.meta.url).pathname;

const browser = await puppeteer.launch({
  headless: true,                         // new headless supports extensions
  pipe: true,
  enableExtensions: [EXT],                // recent Puppeteer; older: args --load-extension / --disable-extensions-except
});
const swTarget = await browser.waitForTarget((t) => t.type() === 'service_worker' && t.url().endsWith('service-worker.js'));
const extId = new URL(swTarget.url()).host;
const worker = await swTarget.worker();

const page = await browser.newPage();
await page.goto(`chrome-extension://${extId}/popup/popup.html`);
await page.click('#increment');
const value = await worker.evaluate(async () => (await chrome.storage.local.get('settings')).settings.count);
```

- Pin the ID with a dev-only `key` if tests or servers need a fixed origin.
- Open the popup in a tab; if it depends on the active tab, accept `?tab=<id>` override.
- Playwright: `chromium.launchPersistentContext('', { args: [`--disable-extensions-except=${EXT}`, `--load-extension=${EXT}`] })`, then `context.serviceWorkers()` / `waitForEvent('serviceworker')`.
- Selenium attaches a debugger to SWs, so they **never terminate** — don't rely on it for termination tests.

## Testing service worker termination

```js
async function stopServiceWorker(browser, extId) {
  const host = `chrome-extension://${extId}`;
  const target = await browser.waitForTarget((t) => t.type() === 'service_worker' && t.url().startsWith(host));
  const worker = await target.worker();
  await worker.close();                   // terminates the SW
}
// then trigger an event (open popup, send message) and assert state survived
```

Every feature with state should have a "works after SW restart" test.

## CI

- Build → `npm test` → E2E in headless Chrome (`xvfb` not needed with new headless) → run `scripts/check_manifest.py dist/manifest.json` → zip `dist/` → optional publish via CWS API (see `publishing.md`).
- Cache the Chrome-for-Testing binary (`npx @puppeteer/browsers install chrome@stable`).

## Debugging tools

| What | Where |
|---|---|
| SW console, network, sources | `chrome://extensions` → *service worker* link (Inspect views) |
| Extension errors (with stack) | *Errors* button on the extension card |
| Popup | Right-click the popup → *Inspect*, or open its URL in a tab |
| Side panel | Right-click inside → *Inspect* |
| Content scripts | Page DevTools → *Sources › Content scripts*; console context dropdown |
| Offscreen document | `chrome://extensions` → Inspect views → offscreen page |
| Storage | DevTools → *Application › Storage › Extension storage* |
| SW status / force stop | `chrome://serviceworker-internals` |
| DNR matches | `declarativeNetRequest.onRuleMatchedDebug` (unpacked + `declarativeNetRequestFeedback`) |
| Updates flow | `chrome://extensions-internals` (ID, permissions, install state) |

Reloading: the reload icon on the card reloads the SW and pages; content scripts in open tabs become orphaned → refresh those tabs. Use `vite build --watch` (or the framework's dev server) for fast iteration.
