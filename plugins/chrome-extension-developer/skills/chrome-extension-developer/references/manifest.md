# manifest.json reference (Manifest V3)

Official: https://developer.chrome.com/docs/extensions/reference/manifest

`manifest.json` is the only file with a mandated name and must sit at the package root.

## Required keys

| Key | Rules |
|---|---|
| `manifest_version` | `3`. |
| `name` | ≤ 75 chars. Can be `__MSG_extName__`. |
| `version` | 1–4 dot-separated integers, each 0–65535, no leading zeros (`"1.4.12"`). Must increase on every store upload. Use `version_name` for display strings like `"1.4 beta"`. |

## Strongly recommended

| Key | Notes |
|---|---|
| `description` | ≤ 132 chars; shown in the store and `chrome://extensions`. |
| `icons` | Provide 16, 32, 48, 128 PNG. 128 is required by the store (96×96 artwork + 16 px transparent padding). |
| `action` | `default_popup`, `default_title`, `default_icon`. Omit `default_popup` to receive `action.onClicked`. |
| `default_locale` | Required iff `_locales/` exists. |
| `minimum_chrome_version` | Set deliberately. **Raising it stops updates for users on older Chrome** — they stay frozen on the version they have. Use 148 for new extensions that use `browser.*`. |

## Background

```json
"background": { "service_worker": "background/service-worker.js", "type": "module" }
```

- One file only; with `"type": "module"` you can use static `import` (no dynamic `import()` in the SW).
- No `scripts`, `page`, or `persistent` (MV2 only).

## Content scripts (static)

```json
"content_scripts": [{
  "matches": ["https://*.example.com/*"],
  "exclude_matches": ["https://admin.example.com/*"],
  "js": ["content/main.js"],
  "css": ["content/styles.css"],
  "run_at": "document_idle",
  "all_frames": false,
  "match_origin_as_fallback": false,
  "world": "ISOLATED"
}]
```

Static `matches` also grant host access for injection; Chrome shows them as host warnings.
Static content scripts are **not** injected into tabs that were already open at install time —
inject programmatically on `onInstalled` if needed.

## Permissions

```json
"permissions": ["storage", "alarms"],
"optional_permissions": ["downloads"],
"host_permissions": ["https://api.example.com/*"],
"optional_host_permissions": ["https://*/*"]
```

Host patterns live in `host_permissions` (not `permissions`) in MV3. See
`permissions-security.md` for warnings and optional flows.

## UI surfaces

```json
"side_panel": { "default_path": "sidepanel/index.html" },
"options_ui": { "page": "options/index.html", "open_in_tab": false },
"chrome_url_overrides": { "newtab": "newtab/index.html" },
"devtools_page": "devtools/devtools.html",
"omnibox": { "keyword": "ext" },
"commands": {
  "_execute_action": { "suggested_key": { "default": "Ctrl+Shift+Y", "mac": "Command+Shift+Y" } },
  "toggle-feature": { "suggested_key": { "default": "Alt+Shift+T" }, "description": "Toggle feature" }
}
```

Note: declaring `devtools_page` disables the `browser` namespace for the **entire extension**
before Chrome 152, and disables Promise-returning `onMessage` listeners.

## Content Security Policy

```json
"content_security_policy": {
  "extension_pages": "script-src 'self'; object-src 'self';",
  "sandbox": "sandbox allow-scripts; script-src 'self' 'unsafe-eval'; object-src 'self';"
}
```

- MV3 default for `extension_pages`: `script-src 'self' 'wasm-unsafe-eval'; object-src 'self';`.
- You may *tighten* it; you may not add remote script hosts or `'unsafe-eval'`/`'unsafe-inline'` for scripts in extension pages.
- Only `sandbox` pages (declared in `"sandbox": { "pages": [...] }`) may use `eval` — and they have no extension API access.

## Web-accessible resources

```json
"web_accessible_resources": [{
  "resources": ["images/badge.svg", "inject/main-world.js"],
  "matches": ["https://*.example.com/*"],
  "use_dynamic_url": true
}]
```

Everything listed is fetchable by matching pages and makes the extension detectable. Keep it
minimal; `use_dynamic_url` rotates the URL per session to reduce fingerprinting.

## Messaging & connectivity

```json
"externally_connectable": { "matches": ["https://app.example.com/*"], "ids": ["<other-extension-id>"] }
```

Without this key, any extension can message yours but no web page can. Always validate senders.

## declarativeNetRequest

```json
"declarative_net_request": {
  "rule_resources": [{ "id": "default", "enabled": true, "path": "rules/default.json" }]
}
```

## Other useful keys

| Key | Use |
|---|---|
| `key` | Public key to pin the extension ID during development (OAuth, allow-listing). **Remove before uploading** — the store assigns/keeps its own. |
| `incognito` | `"spanning"` (default), `"split"`, or `"not_allowed"`. |
| `storage.managed_schema` | JSON schema for enterprise policy (`storage.managed`). |
| `oauth2` | `client_id` + `scopes` for `identity.getAuthToken`. |
| `homepage_url`, `author` | Metadata. |
| `cross_origin_embedder_policy` / `cross_origin_opener_policy` | Opt into cross-origin isolation (`SharedArrayBuffer`). |
| `export` / `import` | Shared modules between extensions. |
| `update_url` | Only for self-hosted (enterprise/Linux) distribution. |

## Removed in MV3 (never emit)

`background.scripts`, `background.page`, `background.persistent`, `browser_action`,
`page_action`, string-valued `content_security_policy`, host patterns inside `permissions`,
`web_accessible_resources` as a flat string array, `"webRequestBlocking"` (enterprise only).
