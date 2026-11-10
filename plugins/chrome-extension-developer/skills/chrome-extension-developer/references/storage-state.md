# Storage and state

Official: https://developer.chrome.com/docs/extensions/reference/api/storage ·
https://developer.chrome.com/docs/extensions/develop/concepts/storage-and-cookies

## Storage areas

| Area | Persistence | Quota | Content scripts by default | Use for |
|---|---|---|---|---|
| `storage.local` | Disk, until uninstall | 10 MB (`unlimitedStorage` removes limit) | exposed | Caches, larger data, app state |
| `storage.sync` | Synced via Chrome Sync (local if sync off) | ~100 KB total, 8 KB/item, 512 items, 120 writes/min, 1800 writes/h | exposed | User settings |
| `storage.session` | Memory; cleared on reload/update/disable/browser restart | 10 MB | **not** exposed | SW state, tokens, sensitive data |
| `storage.managed` | Read-only, from enterprise policy | — | exposed | Admin config (needs `storage.managed_schema`) |

- Values must be JSON-serializable. `get()`, `set()`, `remove()`, `clear()`, `getKeys()`, `getBytesInUse()` all return Promises.
- Restrict content-script access: `browser.storage.local.setAccessLevel({ accessLevel: 'TRUSTED_CONTEXTS' })` (call from a trusted context, e.g. on startup).
- `storage.onChanged` (all areas) / `storage.<area>.onChanged` → react to changes across contexts.
- Web Storage (`localStorage`) is unavailable in the SW, shared with the page in content scripts, and cleared with browsing data — **don't use it**. Migrate legacy data through an offscreen document (`reasons: ['LOCAL_STORAGE']`).
- `storage.sync` writes are rate-limited: debounce option inputs; batch keys into one `set()`.

## Typed wrapper with defaults and migrations

```ts
// shared/storage.ts
export interface Settings { enabled: boolean; theme: 'system' | 'light' | 'dark'; sites: string[] }
export const DEFAULTS: Settings = { enabled: true, theme: 'system', sites: [] };
const SCHEMA_VERSION = 2;

export async function getSettings(): Promise<Settings> {
  const { settings } = await browser.storage.sync.get('settings');
  return { ...DEFAULTS, ...(settings ?? {}) };
}

export async function patchSettings(patch: Partial<Settings>): Promise<Settings> {
  const next = { ...(await getSettings()), ...patch };
  await browser.storage.sync.set({ settings: next });
  return next;
}

export function onSettingsChanged(cb: (s: Settings) => void) {
  browser.storage.sync.onChanged.addListener((changes) => {
    if (changes.settings) cb({ ...DEFAULTS, ...changes.settings.newValue });
  });
}

export async function migrate(): Promise<void> {
  const { schemaVersion = 1 } = await browser.storage.local.get('schemaVersion');
  if (schemaVersion < 2) {
    // example: rename key `blocked` -> settings.sites
    const { blocked } = await browser.storage.sync.get('blocked');
    if (Array.isArray(blocked)) await patchSettings({ sites: blocked });
    await browser.storage.sync.remove('blocked');
  }
  await browser.storage.local.set({ schemaVersion: SCHEMA_VERSION });
}
```

Call `migrate()` from `runtime.onInstalled` (reason `update`). Make each step idempotent.

## SW cache pattern

```js
let cache;                                    // rebuildable cache only
async function state() {
  cache ??= browser.storage.session.get({ tabs: {} });
  return cache;
}
```

Invalidate the cache in `storage.onChanged`.

## Concurrency

`storage` has no transactions. For read-modify-write from multiple contexts, funnel writes
through the SW (single writer) or use IndexedDB transactions.

## Large / binary data

Use IndexedDB (available in SW and pages) — e.g., via a small wrapper like `idb`, bundled.
Request `unlimitedStorage` if needed and disclose it.

## Cookies

`cookies` API + host permission for the target domain to read/write site cookies. Prefer not
to touch cookies unless the single purpose demands it (strong privacy implications).

## Sensitive data

- Tokens: `storage.session` (memory only) or re-acquire via `identity`.
- Never put secrets in `storage.sync` or expose them to content scripts.
- For at-rest encryption use WebCrypto (`crypto.subtle`) with a non-extractable key stored in IndexedDB — but understand that anything the extension can decrypt, malware on the device can too.
