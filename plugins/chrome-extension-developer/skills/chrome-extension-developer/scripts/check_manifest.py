#!/usr/bin/env python3
"""
check_manifest.py — lint a Chrome extension manifest.json against Manifest V3 best practices.

Usage:
    python3 check_manifest.py path/to/manifest.json [--json] [--strict]

Exit codes: 0 = no errors, 1 = errors found (or warnings with --strict), 2 = could not read manifest.
No third-party dependencies (Python 3.8+).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ERROR, WARN, INFO = "error", "warning", "info"

MV2_KEYS = {
    "browser_action": "Use `action` (MV3).",
    "page_action": "Use `action` + declarativeContent / action.disable().",
}
BROAD_HOSTS = {"<all_urls>", "*://*/*", "http://*/*", "https://*/*", "*://*/"}
HIGH_RISK_PERMISSIONS = {
    "debugger": "Full page debugging access; very hard to justify in review.",
    "management": "Can manage other extensions.",
    "nativeMessaging": "Talks to native apps; requires a host installer.",
    "proxy": "Controls proxy settings.",
    "privacy": "Changes browser privacy settings.",
    "contentSettings": "Changes per-site content settings.",
    "history": "Read browsing history warning.",
    "topSites": "Read browsing history warning.",
    "webNavigation": "Read browsing history warning; consider activeTab or tabs.onUpdated.",
    "cookies": "Access to site cookies; strong privacy implications.",
    "clipboardRead": "Reads clipboard data.",
    "tabs": "Only needed to read tab url/title/favIconUrl; tabs.query/create/update work without it.",
    "webRequestBlocking": "Enterprise (policy-installed) only in MV3; use declarativeNetRequest.",
    "unlimitedStorage": "Disclose why large local storage is needed.",
    "<all_urls>": "Host pattern does not belong in `permissions`.",
}
VERSION_RE = re.compile(r"^(0|[1-9]\d{0,4})(\.(0|[1-9]\d{0,4})){0,3}$")
REMOTE_IN_CSP = re.compile(r"(https?:|wss?:|\*)\S*", re.I)


class Report:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, level: str, key: str, message: str) -> None:
        self.items.append({"level": level, "key": key, "message": message})

    def count(self, level: str) -> int:
        return sum(1 for i in self.items if i["level"] == level)


def is_host_pattern(p: str) -> bool:
    return p == "<all_urls>" or "://" in p


def check_files(root: Path, rel: str | None, key: str, r: Report) -> None:
    if rel and not rel.startswith(("http://", "https://")) and not (root / rel).exists():
        r.add(ERROR, key, f"File not found in package: {rel}")


def lint(manifest: dict, root: Path) -> Report:
    r = Report()
    m = manifest

    # --- required keys -------------------------------------------------------
    mv = m.get("manifest_version")
    if mv != 3:
        r.add(ERROR, "manifest_version", f"Must be 3 (found {mv!r}). MV2 is no longer supported by Chrome or the Web Store.")
    for k in ("name", "version"):
        if not m.get(k):
            r.add(ERROR, k, "Required key missing.")
    name = m.get("name", "")
    if isinstance(name, str) and not name.startswith("__MSG_") and len(name) > 75:
        r.add(ERROR, "name", f"Max 75 characters (found {len(name)}).")
    desc = m.get("description")
    if not desc:
        r.add(WARN, "description", "Missing description (shown in the store and chrome://extensions).")
    elif isinstance(desc, str) and not desc.startswith("__MSG_") and len(desc) > 132:
        r.add(ERROR, "description", f"Max 132 characters (found {len(desc)}).")
    version = str(m.get("version", ""))
    if version and not VERSION_RE.match(version):
        r.add(ERROR, "version", f"Invalid version {version!r}: 1–4 dot-separated integers 0–65535, no leading zeros. Use version_name for labels.")
    elif version:
        if any(int(p) > 65535 for p in version.split(".")):
            r.add(ERROR, "version", "Each version component must be ≤ 65535.")

    # --- MV2 leftovers -------------------------------------------------------
    for k, hint in MV2_KEYS.items():
        if k in m:
            r.add(ERROR, k, f"MV2-only key. {hint or ''}".strip())
    bg = m.get("background")
    if isinstance(bg, dict):
        for k in ("scripts", "page", "persistent"):
            if k in bg:
                r.add(ERROR, f"background.{k}", "MV2-only. Use background.service_worker.")
        sw = bg.get("service_worker")
        if sw:
            check_files(root, sw, "background.service_worker", r)
            if bg.get("type") != "module":
                r.add(INFO, "background.type", 'Consider "type": "module" to use ES module imports in the service worker.')
    csp = m.get("content_security_policy")
    if isinstance(csp, str):
        r.add(ERROR, "content_security_policy", "String CSP is MV2. Use { extension_pages, sandbox }.")
    elif isinstance(csp, dict):
        ep = csp.get("extension_pages", "")
        if re.search(r"'unsafe-eval'|'unsafe-inline'", ep):
            r.add(ERROR, "content_security_policy.extension_pages", "'unsafe-eval'/'unsafe-inline' are not allowed for extension pages.")
        for token in re.findall(r"script-src([^;]*)", ep):
            if REMOTE_IN_CSP.search(token):
                r.add(ERROR, "content_security_policy.extension_pages", "Remote script sources are forbidden (remotely hosted code).")
    war = m.get("web_accessible_resources")
    if isinstance(war, list) and war and all(isinstance(x, str) for x in war):
        r.add(ERROR, "web_accessible_resources", "Flat string list is MV2. Use [{ resources, matches }].")
    elif isinstance(war, list):
        for i, entry in enumerate(war):
            if isinstance(entry, dict):
                if not entry.get("matches") and not entry.get("extension_ids"):
                    r.add(WARN, f"web_accessible_resources[{i}]", "No `matches`/`extension_ids` — resources are not reachable by any page.")
                if set(entry.get("matches", [])) & BROAD_HOSTS:
                    r.add(WARN, f"web_accessible_resources[{i}]", "Exposed to all sites: enables fingerprinting. Narrow `matches` or set use_dynamic_url.")
                if any(str(res).strip() in ("*", "**/*", "/*") for res in entry.get("resources", [])):
                    r.add(WARN, f"web_accessible_resources[{i}]", "Wildcard exposes the whole package. List only needed files.")

    # --- permissions ---------------------------------------------------------
    perms = [p for p in m.get("permissions", []) if isinstance(p, str)]
    hosts = [p for p in m.get("host_permissions", []) if isinstance(p, str)]
    opt_perms = [p for p in m.get("optional_permissions", []) if isinstance(p, str)]
    for p in perms:
        if is_host_pattern(p):
            r.add(ERROR, "permissions", f"Host pattern {p!r} must be in host_permissions in MV3.")
        if p in HIGH_RISK_PERMISSIONS:
            r.add(WARN, f"permissions:{p}", HIGH_RISK_PERMISSIONS[p])
    if len(set(perms)) != len(perms):
        r.add(WARN, "permissions", "Duplicate entries.")
    broad = sorted(set(hosts) & BROAD_HOSTS)
    if broad:
        r.add(WARN, "host_permissions", f"Broad host access {broad}: strongest warning and slower review. Prefer activeTab, narrow patterns, or optional_host_permissions.")
    for cs_i, cs in enumerate(m.get("content_scripts", []) or []):
        matches = set(cs.get("matches", []))
        if matches & BROAD_HOSTS:
            r.add(WARN, f"content_scripts[{cs_i}].matches", "Runs on every site. Narrow `matches` or inject on demand with scripting + activeTab.")
        for f in cs.get("js", []) + cs.get("css", []):
            check_files(root, f, f"content_scripts[{cs_i}]", r)
        if cs.get("world") == "MAIN":
            r.add(INFO, f"content_scripts[{cs_i}].world", "MAIN world has no extension APIs and is visible to the page — validate everything crossing the bridge.")
    if "scripting" in perms and not hosts and "activeTab" not in perms and not m.get("optional_host_permissions"):
        r.add(WARN, "permissions:scripting", "scripting without host access or activeTab cannot inject anywhere.")
    if "activeTab" in perms and broad:
        r.add(INFO, "permissions:activeTab", "activeTab is redundant with broad host permissions — consider dropping the broad hosts instead.")
    if "webRequest" in perms and not hosts:
        r.add(WARN, "permissions:webRequest", "webRequest needs host_permissions to observe requests.")
    if "sidePanel" in perms and "side_panel" not in m:
        r.add(INFO, "side_panel", "sidePanel permission without side_panel.default_path; make sure setOptions({ path }) is called.")
    if "side_panel" in m and "sidePanel" not in perms:
        r.add(ERROR, "permissions", "side_panel key requires the \"sidePanel\" permission.")
    if "offscreen" in perms:
        r.add(INFO, "permissions:offscreen", "Remember: one offscreen document at a time; only runtime API inside it.")
    if "declarative_net_request" in m and not ({"declarativeNetRequest", "declarativeNetRequestWithHostAccess"} & set(perms)):
        r.add(ERROR, "permissions", "declarative_net_request requires declarativeNetRequest(WithHostAccess) permission.")
    for rr in (m.get("declarative_net_request", {}) or {}).get("rule_resources", []):
        check_files(root, rr.get("path"), "declarative_net_request.rule_resources", r)
    if "userScripts" in perms:
        r.add(INFO, "permissions:userScripts", "Users must enable 'Allow User Scripts' (Chrome 138+). Detect availability at runtime.")
    for p in opt_perms:
        if is_host_pattern(p):
            r.add(ERROR, "optional_permissions", f"Host pattern {p!r} belongs in optional_host_permissions.")

    # --- externally_connectable ---------------------------------------------
    ec = m.get("externally_connectable")
    if isinstance(ec, dict):
        if set(ec.get("matches", [])) & BROAD_HOSTS or "*" in ec.get("ids", []):
            r.add(WARN, "externally_connectable", "Open to every site/extension. Restrict to exact origins/IDs and validate senders.")

    # --- UI, icons, i18n ------------------------------------------------------
    icons = m.get("icons") or {}
    if "128" not in icons:
        r.add(WARN, "icons", "Provide a 128×128 icon (required by the Chrome Web Store). Recommended: 16, 32, 48, 128.")
    for size, path in icons.items():
        check_files(root, path, f"icons.{size}", r)
        if isinstance(path, str) and path.lower().endswith(".svg"):
            r.add(ERROR, f"icons.{size}", "SVG is not supported for manifest icons; use PNG.")
    action = m.get("action")
    if isinstance(action, dict):
        check_files(root, action.get("default_popup"), "action.default_popup", r)
    for key in ("options_page",):
        check_files(root, m.get(key), key, r)
    if isinstance(m.get("options_ui"), dict):
        check_files(root, m["options_ui"].get("page"), "options_ui.page", r)
    if isinstance(m.get("side_panel"), dict):
        check_files(root, m["side_panel"].get("default_path"), "side_panel.default_path", r)
    has_locales = (root / "_locales").is_dir()
    if has_locales and not m.get("default_locale"):
        r.add(ERROR, "default_locale", "_locales/ exists, so default_locale is required.")
    if m.get("default_locale") and not (root / "_locales" / m["default_locale"] / "messages.json").exists():
        r.add(ERROR, "default_locale", f"_locales/{m['default_locale']}/messages.json not found.")
    if has_locales and m.get("default_locale"):
        msgs_path = root / "_locales" / m["default_locale"] / "messages.json"
        try:
            msgs = json.loads(msgs_path.read_text(encoding="utf-8"))
            used = set(re.findall(r"__MSG_(\w+)__", json.dumps(m)))
            missing = sorted(k for k in used if k not in msgs and not k.startswith("@@"))
            if missing:
                r.add(ERROR, "_locales", f"Keys used in manifest but missing in default locale: {missing}")
        except (OSError, ValueError) as e:
            r.add(ERROR, "_locales", f"Cannot parse {msgs_path}: {e}")
    if not has_locales and "__MSG_" in json.dumps(m):
        r.add(ERROR, "_locales", "Manifest uses __MSG_*__ but no _locales/ folder exists.")

    # --- versions & namespaces ------------------------------------------------
    mcv = m.get("minimum_chrome_version")
    if mcv is None:
        r.add(INFO, "minimum_chrome_version", 'Not set. If you use browser.* unguarded or Promise-returning onMessage, set "148". Raising it freezes users on older Chrome.')
    else:
        try:
            if int(str(mcv).split(".")[0]) < 88:
                r.add(WARN, "minimum_chrome_version", "Below the first MV3 release (88).")
        except ValueError:
            r.add(ERROR, "minimum_chrome_version", f"Invalid value {mcv!r}.")
    if "devtools_page" in m:
        r.add(INFO, "devtools_page", "Before Chrome 152, devtools_page disables the browser namespace for the whole extension, and disables Promise-returning onMessage listeners.")
    if "key" in m:
        r.add(WARN, "key", "Dev-only ID pinning key present — remove it before uploading to the Chrome Web Store.")
    if "update_url" in m:
        r.add(INFO, "update_url", "Only for self-hosted/enterprise distribution; the Web Store ignores/rejects it.")

    return r


def scan_sources(root: Path, r: Report) -> None:
    """Grep shipped JS for MV2 APIs and risky patterns."""
    patterns = [
        (ERROR, r"chrome\.extension\.getURL", "Use runtime.getURL."),
        (ERROR, r"(chrome|browser)\.(extension|runtime)\.getBackgroundPage", "No background page in MV3; use messaging/storage."),
        (ERROR, r"(chrome|browser)\.browserAction|(chrome|browser)\.pageAction", "Use the action API."),
        (ERROR, r"(chrome|browser)\.tabs\.(executeScript|insertCSS|removeCSS)", "Use the scripting API."),
        (ERROR, r"<script[^>]+src=[\"']https?://", "Remotely hosted script — forbidden in MV3."),
        (WARN, r"\beval\s*\(|new\s+Function\s*\(", "eval/new Function — only allowed in sandboxed pages."),
        (WARN, r"\.innerHTML\s*=|insertAdjacentHTML\s*\(|document\.write\s*\(", "HTML sink — ensure data is trusted or sanitized."),
        (WARN, r"\bon(click|load|change|submit)\s*=\s*[\"']", "Inline event handler — blocked by extension CSP."),
        (WARN, r"http://(?!localhost|127\.0\.0\.1)", "Plain HTTP URL — use HTTPS."),
    ]
    skip = {"node_modules", ".git", "test", "tests", "__tests__"}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {".js", ".mjs", ".html", ".ts"}:
            continue
        if any(part in skip for part in path.relative_to(root).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(path.relative_to(root))
        for level, pat, msg in patterns:
            for match in re.finditer(pat, text):
                line = text.count("\n", 0, match.start()) + 1
                r.add(level, f"{rel}:{line}", msg)
                break  # one hit per pattern per file is enough


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    ap.add_argument("--no-source-scan", action="store_true", help="skip scanning JS/HTML files")
    args = ap.parse_args()

    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"Cannot read manifest: {e}", file=sys.stderr)
        return 2
    root = args.manifest.resolve().parent
    report = lint(manifest, root)
    if not args.no_source_scan:
        scan_sources(root, report)

    if args.json:
        print(json.dumps(report.items, indent=2, ensure_ascii=False))
    else:
        icon = {ERROR: "✖", WARN: "⚠", INFO: "ℹ"}
        order = {ERROR: 0, WARN: 1, INFO: 2}
        for item in sorted(report.items, key=lambda i: order[i["level"]]):
            print(f"{icon[item['level']]} [{item['level']}] {item['key']}: {item['message']}")
        print(f"\n{report.count(ERROR)} error(s), {report.count(WARN)} warning(s), {report.count(INFO)} info.")

    if report.count(ERROR) or (args.strict and report.count(WARN)):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
