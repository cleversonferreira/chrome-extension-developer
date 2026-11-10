// globalThis.browser ??= chrome; // uncomment to support Chrome < 148
import { getSettings, patchSettings } from '../shared/storage.js';
import { applyI18n } from '../shared/i18n.js';

applyI18n(document);

const checkbox = /** @type {HTMLInputElement} */ (document.getElementById('includeHidden'));
const status = /** @type {HTMLElement} */ (document.getElementById('status'));

const settings = await getSettings(); // top-level await is fine in module pages
checkbox.checked = settings.includeHidden;

// Persist immediately: options/popup pages can close at any time.
checkbox.addEventListener('change', async () => {
  await patchSettings({ includeHidden: checkbox.checked });
  status.textContent = browser.i18n.getMessage('saved');
});
