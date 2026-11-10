# UI surfaces

Official: https://developer.chrome.com/docs/extensions/develop/ui

All extension pages (popup, side panel, options, overrides, tabs opened with `runtime.getURL`)
have full extension API access and follow the extension CSP: **no inline scripts, no inline
event handlers** (`onclick=""`). Use `<script type="module" src="./main.js">`.

## Action (toolbar)

- `action.setBadgeText({ text, tabId })`, `setBadgeBackgroundColor`, `setIcon`, `setTitle`, `setPopup` (per tab or global).
- `action.onClicked` fires only when there is **no** popup.
- `action.openPopup()` opens the popup programmatically.
- Disable per tab with `action.disable(tabId)`, or declaratively with `declarativeContent` (no host permission needed).

## Popup

- Recommended size ≤ 800×600; it closes on blur, destroying all JS state → save input immediately to `storage`.
- Render fast: read storage once, show skeleton, then hydrate.
- Don't do long work in the popup; delegate to the SW.

## Side panel (Chrome 114+)

```json
"permissions": ["sidePanel"],
"side_panel": { "default_path": "sidepanel/index.html" }
```

```js
browser.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(console.error);

// Tab-specific panel
browser.tabs.onUpdated.addListener(async (tabId, _info, tab) => {
  if (!tab.url) return;
  const enabled = new URL(tab.url).hostname.endsWith('example.com');
  await browser.sidePanel.setOptions({ tabId, path: 'sidepanel/index.html', enabled });
});

// Open from a user gesture (context menu, command, button)
browser.contextMenus.onClicked.addListener((info, tab) => {
  browser.sidePanel.open({ windowId: tab.windowId });   // or { tabId }
});
```

Version-gated: `open()` 116+, `getLayout()` (left/right) 140+, `close()` and `onOpened` 141+, `onClosed` 142+.
Since Chrome 145, `close({ tabId })` rejects if only the global panel is open.

## Options page

```json
"options_ui": { "page": "options/index.html", "open_in_tab": false }
```

Open with `runtime.openOptionsPage()`. Persist each change immediately; listen to
`storage.onChanged` elsewhere to apply settings live.

## Context menus

Create in `runtime.onInstalled` (they persist). Use `contexts` (`selection`, `link`, `image`,
`page`, `action`…) and `documentUrlPatterns` to scope. Handle with `contextMenus.onClicked`
registered at top level. Max top-level items per extension: `contextMenus.ACTION_MENU_TOP_LEVEL_LIMIT` for the action menu.

## Commands (keyboard shortcuts)

- `_execute_action` and `_execute_side_panel` are reserved command names (no listener needed).
- Up to 4 suggested shortcuts; users change them at `chrome://extensions/shortcuts`. Don't assume your suggestion was applied — read `commands.getAll()`.

## Omnibox

`"omnibox": { "keyword": "ext" }` → `omnibox.onInputChanged` (suggest), `onInputEntered` (act).

## Notifications

`notifications.create(id, { type: 'basic', iconUrl, title, message })` — requires `notifications`.
Keep them meaningful and rare; respect user opt-out.

## Override pages

`chrome_url_overrides` for `newtab`, `history` or `bookmarks` (one per extension). New-tab
overrides must keep the user's expectations (search, speed) — the store reviews this.

## Themes

A theme is a separate manifest-only package (`"theme": { … }`) — not combined with an extension.

## Icons

- Manifest `icons` 16/32/48/128; `action.default_icon` 16/32 (Chrome scales).
- Use PNG (SVG not supported for manifest icons). Provide a dark-mode friendly design or switch at runtime with `action.setIcon` based on `matchMedia('(prefers-color-scheme: dark)')` in an extension page/offscreen document.

## Internationalization (i18n)

```
_locales/
  en/messages.json
  pt_BR/messages.json
```

```json
{ "extName": { "message": "Word Counter", "description": "Extension name" } }
```

- Manifest: `"name": "__MSG_extName__"`, `"default_locale": "en"`.
- JS: `browser.i18n.getMessage('extName')`; placeholders with `$1`/named placeholders.
- CSS: `__MSG_@@bidi_dir__` for RTL; HTML: set `dir`/`lang` at load from `i18n.getUILanguage()`.
- Use `Intl.*` for dates, numbers, plural rules.

## Accessibility

- Every interactive element reachable with Tab and operable with Enter/Space; visible focus.
- Use native elements (`<button>`, `<label for>`) before ARIA; add `aria-label` to icon buttons; `aria-live="polite"` for async status.
- Contrast ≥ 4.5:1 for text; support `prefers-color-scheme`, `prefers-reduced-motion`, zoom.
- Injected UI must not trap focus or break the host page's a11y tree; provide an Escape close.

## UX rules of thumb

- Loading, empty, and error states for every async view.
- Never surprise the user: no unrequested tabs, notifications, or new-tab hijacks.
- Onboarding page on install (`tabs.create({ url: 'welcome.html' })`) only if it's genuinely useful; never on update unless there's a meaningful change.
