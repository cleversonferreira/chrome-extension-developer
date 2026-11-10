/**
 * Shared message contract for every extension context.
 * Responses always use the envelope { ok: true, data } | { ok: false, error }.
 */

export const MSG = Object.freeze({
  COUNT_ACTIVE_TAB: 'COUNT_ACTIVE_TAB',
  GET_STATS: 'GET_STATS',
  RESET_STATS: 'RESET_STATS',
});

/**
 * Send a message to the service worker and unwrap the envelope.
 * @param {{ type: string } & Record<string, unknown>} message
 * @returns {Promise<any>}
 */
export async function send(message) {
  const res = await browser.runtime.sendMessage(message);
  if (!res?.ok) throw new Error(res?.error ?? 'No response from service worker');
  return res.data;
}

/** @param {unknown} value */
export function isMessage(value) {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (/** @type {any} */ (value).type) === 'string' &&
    Object.values(MSG).includes(/** @type {any} */ (value).type)
  );
}
