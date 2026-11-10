// Event router for the extension. Rules:
//  - every listener is registered synchronously at top level;
//  - no state in globals (the worker can be terminated after ~30 s idle);
//  - every message is validated before acting on it.

// Uncomment to support Chrome < 148 (and lower minimum_chrome_version in the manifest):
// globalThis.browser ??= chrome;

import { MSG, isMessage } from '../shared/messages.js';
import { DEFAULT_SETTINGS, DEFAULT_STATS, getSettings, getStats, setStats } from '../shared/storage.js';

const log = (...args) => console.debug('[ext:sw]', ...args);

browser.runtime.onInstalled.addListener(async ({ reason }) => {
  log('onInstalled', reason);
  if (reason === 'install') {
    await browser.storage.sync.set({ settings: DEFAULT_SETTINGS });
    await browser.storage.local.set({ stats: DEFAULT_STATS });
  }
});

browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Only accept messages from our own extension pages (popup/options).
  if (sender.id !== browser.runtime.id || !isMessage(message)) return;
  const handler = HANDLERS[message.type];
  handler(message, sender)
    .then((data) => sendResponse({ ok: true, data }))
    .catch((err) => sendResponse({ ok: false, error: err instanceof Error ? err.message : String(err) }));
  return true; // async response; works on every Chrome version
});

const HANDLERS = {
  async [MSG.COUNT_ACTIVE_TAB]() {
    const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id || !/^https?:/.test(tab.url ?? '')) {
      throw new Error(browser.i18n.getMessage('errorRestrictedPage'));
    }
    const { includeHidden } = await getSettings();
    // activeTab grants temporary access because the user opened the popup.
    const [injection] = await browser.scripting.executeScript({
      target: { tabId: tab.id },
      func: countWordsInPage,
      args: [includeHidden],
    });
    const words = Number(injection?.result ?? 0);
    const stats = await getStats();
    return setStats({
      pagesCounted: stats.pagesCounted + 1,
      totalWords: stats.totalWords + words,
      lastCount: { words, at: Date.now() },
    });
  },

  async [MSG.GET_STATS]() {
    return getStats();
  },

  async [MSG.RESET_STATS]() {
    return setStats({ ...DEFAULT_STATS });
  },
};

/**
 * Runs inside the page (isolated world). Must be self-contained: it is serialized,
 * so it cannot reference variables from this module.
 * @param {boolean} includeHidden
 */
function countWordsInPage(includeHidden) {
  const text = includeHidden ? document.body?.textContent ?? '' : document.body?.innerText ?? '';
  const words = text.trim().match(/[\p{L}\p{N}'’-]+/gu);
  return words ? words.length : 0;
}
