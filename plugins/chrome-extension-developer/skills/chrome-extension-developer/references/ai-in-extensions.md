# AI in Chrome extensions

Official: https://developer.chrome.com/docs/extensions/ai · https://developer.chrome.com/docs/ai/built-in

## Built-in (on-device) AI APIs

Available to extensions (some via origin trial / Early Preview Program, check status per API):

| API | Purpose |
|---|---|
| Prompt API (`LanguageModel`) | General prompting of Gemini Nano, multimodal input where supported |
| Summarizer API | Summaries in several types/lengths/formats |
| Translator API | On-device translation |
| Language Detector API | Detect text language |
| Writer / Rewriter API | Generate / refine text (tone, length) |
| Proofreader API | Grammar and spelling corrections |

Pattern (feature-detect, check availability, create a session, handle download):

```js
if (!('Summarizer' in self)) return fallback();
const availability = await Summarizer.availability();   // 'unavailable' | 'downloadable' | 'downloading' | 'available'
if (availability === 'unavailable') return fallback();
const summarizer = await Summarizer.create({
  type: 'key-points', length: 'short', format: 'markdown',
  monitor(m) { m.addEventListener('downloadprogress', (e) => reportProgress(e.loaded)); },
});
const summary = await summarizer.summarize(pageText);
```

- Run in an extension page (side panel/popup) or offscreen document when the API needs a document context; verify where each API is exposed (window vs worker) in its doc page.
- Model **download requires user activation** for some APIs and has hardware requirements — design a graceful fallback.
- Trigger large model downloads **after install**, not on every update; model weights are data, not remotely hosted code.
- Keep input sizes within the session's quota (`measureInputUsage`/`inputQuota` where available); chunk long pages.
- Always confirm API shapes against the current doc — these APIs are evolving.

## Cloud AI (Gemini API or any provider)

- **Never ship API keys** in the package. Proxy through your server, fetch short-lived keys from your server, or let users bring their own key.
- Disclose in the privacy policy and CWS Privacy tab what user content is sent to the server.
- Call from the SW (host permission for the API domain) and stream results to the UI via a port.
- Timeouts: a `fetch()` whose response takes > 30 s to start can get the SW killed — use streaming responses or move the call to an extension page.

## Agentic AI

- **WebMCP** is a proposed standard to expose structured tools to AI agents from web pages; see https://developer.chrome.com/docs/ai/webmcp and its tool-security guidance.
- Extensions that let agents act on pages must defend against prompt injection from page content: treat page text as data, require user confirmation for side-effectful actions, scope permissions tightly.

## Building extensions with AI coding tools

Google publishes an official "chrome-extensions" skill in Modern Web Guidance:
`npx skills add GoogleChrome/modern-web-guidance --skill chrome-extensions`. It can be used
alongside this skill.
