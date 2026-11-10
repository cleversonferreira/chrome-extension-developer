# Messaging

Official: https://developer.chrome.com/docs/extensions/develop/concepts/messaging

## APIs

| From → To | One-time | Long-lived |
|---|---|---|
| Content script / extension page → extension (SW, pages) | `runtime.sendMessage(msg)` | `runtime.connect({ name })` |
| Extension → content script in a tab | `tabs.sendMessage(tabId, msg, { frameId?, documentId? })` | `tabs.connect(tabId, { name })` |
| Another extension / allowed web page → you | `runtime.sendMessage(extId, msg)` → `runtime.onMessageExternal` | `runtime.onConnectExternal` |
| User script → extension | `runtime.sendMessage` → `runtime.onUserScriptMessage` (needs `userScripts.configureWorld({ messaging: true })`) | `runtime.onUserScriptConnect` |
| Extension ↔ native app | `runtime.sendNativeMessage` | `runtime.connectNative` |

Extensions **cannot** initiate messages to web pages (use a content script + `window.postMessage`).

## Serialization & limits

- Chrome uses **JSON serialization** (Firefox/Safari use structured clone). `undefined` → `null`; `Date` → string; `Map`/`Set`/class instances lose meaning; functions throw. Max **64 MiB**.
- Send binary data as base64 or via `storage`/IndexedDB, or use an offscreen document + Blob URLs.

## Responding asynchronously

Three ways, in order of compatibility:

```js
// 1) Universal: return literal true and call sendResponse later
browser.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type !== 'GET_STATUS') return;           // ignore → other listeners may answer
  fetchStatus().then(sendResponse, (e) => sendResponse({ error: e.message }));
  return true;                                       // must be the literal `true`
});

// 2) Chrome 148+ (gradual rollout): return a Promise
browser.runtime.onMessage.addListener((msg) => {
  if (msg?.type !== 'GET_STATUS') return;            // return undefined for messages you don't handle
  return fetchStatus();                              // resolved value is the response
});

// 3) Chrome 148+: async listener — ONLY if it handles every message type it receives
browser.runtime.onMessage.addListener(async (msg) => { /* ... */ });
```

Pitfalls:

- An `async` listener **always** returns a Promise; if it resolves to `undefined`, the sender
  receives `null` and later listeners' responses are ignored. Use a sync wrapper that returns
  `undefined` for foreign messages and a Promise for owned ones.
- Promise returns are **disabled** in extensions that declare a `devtools_page`.
- Since Chrome 146 (gradual), a thrown error or rejected Promise in a listener rejects the
  sender's `sendMessage()` with the error message (reject with an `Error` instance, otherwise
  the sender gets a generic message). Non-serializable responses also reject.
- Only the **first** listener to respond/reject/throw affects the sender.

Recommended: always respond with an envelope, which is robust across versions:

```ts
type Ok<T> = { ok: true; data: T };
type Err = { ok: false; error: string };
type Result<T> = Ok<T> | Err;
```

## Typed message contract (TypeScript)

```ts
// shared/messages.ts
export type Message =
  | { type: 'GET_SETTINGS' }
  | { type: 'SAVE_SETTINGS'; settings: Settings }
  | { type: 'ANALYZE_PAGE'; url: string; text: string };

export type ResponseMap = {
  GET_SETTINGS: Settings;
  SAVE_SETTINGS: void;
  ANALYZE_PAGE: AnalysisResult;
};

export async function send<M extends Message>(msg: M): Promise<ResponseMap[M['type']]> {
  const res = (await browser.runtime.sendMessage(msg)) as Result<ResponseMap[M['type']]>;
  if (!res?.ok) throw new Error(res?.error ?? 'No response');
  return res.data;
}
```

```ts
// background/messages.ts
const handlers: { [K in Message['type']]: (m: Extract<Message, { type: K }>, s: chrome.runtime.MessageSender) => Promise<ResponseMap[K]> } = {
  GET_SETTINGS: async () => getSettings(),
  SAVE_SETTINGS: async (m) => saveSettings(validateSettings(m.settings)),
  ANALYZE_PAGE: async (m, sender) => {
    if (!sender.tab?.id) throw new Error('Must come from a tab');
    return analyze(String(m.text).slice(0, 100_000));
  },
};

export function handleMessage(msg: unknown, sender: chrome.runtime.MessageSender, sendResponse: (r: unknown) => void) {
  if (sender.id !== browser.runtime.id) return;
  if (!isMessage(msg)) return;
  const handler = handlers[msg.type] as (m: Message, s: typeof sender) => Promise<unknown>;
  handler(msg, sender)
    .then((data) => sendResponse({ ok: true, data }))
    .catch((e) => sendResponse({ ok: false, error: e instanceof Error ? e.message : String(e) }));
  return true;
}
```

Write `isMessage()` as a runtime validator (hand-written or with a schema library such as zod/valibot bundled into the extension).

## Messaging a tab safely

```js
async function sendToTab(tabId, message) {
  try {
    return await browser.tabs.sendMessage(tabId, message);
  } catch (err) {
    // "Receiving end does not exist" → inject, then retry once
    await browser.scripting.executeScript({ target: { tabId }, files: ['content/main.js'] });
    return browser.tabs.sendMessage(tabId, message);
  }
}
```

Requires `scripting` + host access (or `activeTab` after a user gesture). Make the content
script idempotent (`if (window.__extLoaded) return; window.__extLoaded = true;`).

## Ports

- `onDisconnect` fires when the other end disconnects, the frame/tab unloads, or no `onConnect` listener exists. A port can have multiple receivers (one per frame) — `onDisconnect` can fire multiple times.
- Sending over a port keeps the SW alive (Chrome 114+), but ports die when the SW terminates; reconnect from the client on `onDisconnect`.
- Name ports (`{ name: 'stream' }`) and check `port.name`/`port.sender` in `onConnect`.

## Security

- Content scripts run in the page's renderer — treat their messages as attacker-controlled.
- Check `sender.id`, `sender.origin`, `sender.url`, `sender.tab`, `sender.frameId`, `sender.documentId`.
- Never `eval` or `innerHTML` a response; parse with `JSON.parse`, render with `textContent`.
- Externally: validate `sender.id` against an allow-list (`onMessageExternal`) or `sender.origin` for web pages; register `onMessageExternal` only if you need it.
