// globalThis.browser ??= chrome; // uncomment to support Chrome < 148
import { MSG, send } from '../shared/messages.js';
import { applyI18n } from '../shared/i18n.js';

const $ = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const numberFormat = new Intl.NumberFormat(browser.i18n.getUILanguage());

applyI18n(document);

function render(stats) {
  $('pages').textContent = numberFormat.format(stats.pagesCounted);
  $('words').textContent = numberFormat.format(stats.totalWords);
}

function setStatus(text, isError = false) {
  const el = $('status');
  el.textContent = text; // textContent, never innerHTML
  el.classList.toggle('error', isError);
}

$('count').addEventListener('click', async () => {
  const button = /** @type {HTMLButtonElement} */ ($('count'));
  button.disabled = true;
  setStatus(browser.i18n.getMessage('counting'));
  try {
    const stats = await send({ type: MSG.COUNT_ACTIVE_TAB });
    render(stats);
    setStatus(browser.i18n.getMessage('countResult', [numberFormat.format(stats.lastCount.words)]));
  } catch (err) {
    setStatus(err instanceof Error ? err.message : String(err), true);
  } finally {
    button.disabled = false;
  }
});

$('reset').addEventListener('click', async () => render(await send({ type: MSG.RESET_STATS })));
$('options').addEventListener('click', () => browser.runtime.openOptionsPage());

send({ type: MSG.GET_STATS }).then(render).catch((e) => setStatus(String(e), true));
