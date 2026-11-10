/**
 * Fill every element that has data-i18n="messageKey" with the localized string.
 * Uses textContent so translations can never inject HTML.
 * @param {ParentNode} root
 */
export function applyI18n(root) {
  for (const el of root.querySelectorAll('[data-i18n]')) {
    const key = el.getAttribute('data-i18n');
    if (key) el.textContent = browser.i18n.getMessage(key) || key;
  }
  document.documentElement.lang = browser.i18n.getUILanguage();
  document.documentElement.dir = browser.i18n.getMessage('@@bidi_dir') || 'ltr';
}
