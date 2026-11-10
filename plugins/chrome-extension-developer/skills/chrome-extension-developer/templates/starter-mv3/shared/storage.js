/** Typed-ish storage helpers with defaults. All state lives here, never in SW globals. */

export const DEFAULT_SETTINGS = Object.freeze({ includeHidden: false });
export const DEFAULT_STATS = Object.freeze({ pagesCounted: 0, totalWords: 0, lastCount: null });

/** @returns {Promise<typeof DEFAULT_SETTINGS>} */
export async function getSettings() {
  const { settings } = await browser.storage.sync.get('settings');
  return { ...DEFAULT_SETTINGS, ...(settings ?? {}) };
}

/** @param {Partial<typeof DEFAULT_SETTINGS>} patch */
export async function patchSettings(patch) {
  const next = { ...(await getSettings()), ...patch };
  await browser.storage.sync.set({ settings: next });
  return next;
}

/** @returns {Promise<typeof DEFAULT_STATS>} */
export async function getStats() {
  const { stats } = await browser.storage.local.get('stats');
  return { ...DEFAULT_STATS, ...(stats ?? {}) };
}

/** @param {typeof DEFAULT_STATS} stats */
export async function setStats(stats) {
  await browser.storage.local.set({ stats });
  return stats;
}
