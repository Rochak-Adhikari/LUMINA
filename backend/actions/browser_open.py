"""
actions/browser_open.py — Lumina dedicated browser open tool

Opens URLs or known sites in Lumina's dedicated Brave browser instance.
This is completely separate from the user's personal Brave browser.

Lumina browser config (matches local_browser_control.py):
    Profile dir : E:\\LuminaBrowser\\profile  (env: LUMINA_BROWSER_PROFILE)
    CDP port    : 9223                         (env: LUMINA_CDP_PORT)
    Window size : 1100x700

Supported actions:
    open_url      — open an arbitrary URL in Lumina's browser
    google_search — search Google in Lumina's browser
    open_site     — open a known/named site in Lumina's browser
"""

import os
import platform
import subprocess
import urllib.parse

_OS = platform.system()

# ---------------------------------------------------------------------------
# Lumina browser config — must match local_browser_control.py constants
# ---------------------------------------------------------------------------

def _detect_brave_exe() -> str:
    candidates = [
        os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                     "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                     "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"


_BRAVE_EXE             = os.environ.get("BRAVE_EXECUTABLE_PATH", "").strip() or _detect_brave_exe()
_LUMINA_PROFILE        = os.environ.get("LUMINA_BROWSER_PROFILE",   r"E:\LuminaBrowser\profile").strip()
_LUMINA_DOWNLOADS      = os.environ.get("LUMINA_BROWSER_DOWNLOADS", r"E:\LuminaBrowser\downloads").strip()
_LUMINA_CDP_PORT       = int(os.environ.get("LUMINA_CDP_PORT", "9223"))
_LUMINA_WINDOW_W       = int(os.environ.get("LUMINA_WINDOW_W", "1100"))
_LUMINA_WINDOW_H       = int(os.environ.get("LUMINA_WINDOW_H", "700"))
_LUMINA_WINDOW_X       = int(os.environ.get("LUMINA_WINDOW_X", "100"))
_LUMINA_WINDOW_Y       = int(os.environ.get("LUMINA_WINDOW_Y", "100"))

# ── Well-known site shortcuts ─────────────────────────────────────────────────
KNOWN_SITES: dict[str, str] = {
    # Video
    "youtube":      "https://www.youtube.com",
    "twitch":       "https://www.twitch.tv",
    "vimeo":        "https://www.vimeo.com",
    "netflix":      "https://www.netflix.com",
    "soundcloud":   "https://soundcloud.com",
    # Social
    "twitter":      "https://twitter.com",
    "x":            "https://twitter.com",
    "instagram":    "https://www.instagram.com",
    "facebook":     "https://www.facebook.com",
    "reddit":       "https://www.reddit.com",
    "linkedin":     "https://www.linkedin.com",
    "tiktok":       "https://www.tiktok.com",
    "snapchat":     "https://web.snapchat.com",
    "discord":      "https://discord.com/app",
    # Messaging
    "whatsapp":     "https://web.whatsapp.com",
    "whatsapp web": "https://web.whatsapp.com",
    "telegram":     "https://web.telegram.org",
    # Productivity / Dev
    "google":       "https://www.google.com",
    "gmail":        "https://mail.google.com",
    "drive":        "https://drive.google.com",
    "docs":         "https://docs.google.com",
    "sheets":       "https://sheets.google.com",
    "slides":       "https://slides.google.com",
    "meet":         "https://meet.google.com",
    "calendar":     "https://calendar.google.com",
    "github":       "https://github.com",
    "gitlab":       "https://gitlab.com",
    "stackoverflow": "https://stackoverflow.com",
    "chatgpt":      "https://chat.openai.com",
    "claude":       "https://claude.ai",
    "gemini":       "https://gemini.google.com",
    # Shopping / News
    "amazon":       "https://www.amazon.com",
    "ebay":         "https://www.ebay.com",
    "wikipedia":    "https://www.wikipedia.org",
    "news":         "https://news.google.com",
    "bbc":          "https://www.bbc.com",
    # Misc
    "maps":         "https://maps.google.com",
    "translate":    "https://translate.google.com",
    "weather":      "https://weather.com",
}


def _ensure_lumina_dirs() -> None:
    """Create dedicated profile/downloads dirs if they don't exist."""
    for d in (_LUMINA_PROFILE, _LUMINA_DOWNLOADS):
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass


def _cdp_reachable() -> bool:
    """Check if Lumina's dedicated browser CDP port is responding."""
    import urllib.request
    try:
        r = urllib.request.urlopen(
            f"http://127.0.0.1:{_LUMINA_CDP_PORT}/json/version", timeout=2
        )
        r.close()
        return True
    except Exception:
        return False


def _open_in_lumina_browser(url: str) -> bool:
    """
    Open a URL in Lumina's dedicated Brave browser instance.

    Strategy:
    1. If Lumina's browser is already running (CDP reachable on port 9223):
       Open a new tab in it via 'brave.exe --app=<url>' targeting the
       same profile — Brave detects the running instance and opens a new tab.
    2. If not running: launch the dedicated Lumina browser with this URL.

    NEVER uses os.startfile, NEVER opens in personal Brave, NEVER uses
    the default system browser association.
    """
    if not os.path.isfile(_BRAVE_EXE):
        print(f"[BrowserOpen] Brave not found at {_BRAVE_EXE}")
        return False

    _ensure_lumina_dirs()

    try:
        if _cdp_reachable():
            # Lumina browser is already running — open URL as a new tab.
            # Brave detects the profile is already in use and opens a new tab
            # in the existing window rather than launching a second instance.
            cmd = [
                _BRAVE_EXE,
                f"--user-data-dir={_LUMINA_PROFILE}",
                "--profile-directory=Default",
                url,
            ]
        else:
            # Lumina browser not running — launch it with this URL
            cmd = [
                _BRAVE_EXE,
                f"--remote-debugging-port={_LUMINA_CDP_PORT}",
                f"--user-data-dir={_LUMINA_PROFILE}",
                "--profile-directory=Default",
                f"--default-download-directory={_LUMINA_DOWNLOADS}",
                f"--window-size={_LUMINA_WINDOW_W},{_LUMINA_WINDOW_H}",
                f"--window-position={_LUMINA_WINDOW_X},{_LUMINA_WINDOW_Y}",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--no-first-run",
                "--no-default-browser-check",
                url,
            ]

        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS if _OS == "Windows" else 0,
        )
        return True
    except Exception as e:
        print(f"[BrowserOpen] Failed to open in Lumina browser: {e}")
        return False


def browser_open(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Open URLs or known sites in Lumina's dedicated Brave browser.
    NEVER uses the user's personal Brave or system default browser.

    parameters:
        action  : 'open_url' | 'google_search' | 'open_site' (default: auto-detect)
        url     : Full URL to open (for open_url)
        query   : Search query (for google_search)
        site    : Site name or partial URL (for open_site)
    """
    params = parameters or {}
    action = params.get("action", "").strip().lower()
    url    = params.get("url", "").strip()
    query  = params.get("query", "").strip()
    site   = params.get("site", "").strip()

    # ── Auto-detect action from provided params ───────────────────────────────
    if not action:
        if url:
            action = "open_url"
        elif query:
            action = "google_search"
        elif site:
            action = "open_site"
        else:
            return "Please provide a URL, site name, or search query."

    # ── open_url ──────────────────────────────────────────────────────────────
    if action == "open_url":
        if not url:
            return "Please provide a URL to open."
        if not url.startswith(("http://", "https://", "file://", "ftp://")):
            url = "https://" + url
        print(f"[BrowserOpen] Opening URL in Lumina browser: {url}")
        if _open_in_lumina_browser(url):
            return f"Opened {url} in Lumina's browser."
        return f"Could not open {url} in Lumina's browser."

    # ── google_search ─────────────────────────────────────────────────────────
    if action == "google_search":
        if not query:
            query = site or url
        if not query:
            return "Please provide a search query."
        encoded = urllib.parse.quote_plus(query)
        search_url = f"https://www.google.com/search?q={encoded}"
        print(f"[BrowserOpen] Google search in Lumina browser: {query!r}")
        if _open_in_lumina_browser(search_url):
            return f"Searching Google for: {query}"
        return f"Could not open Google search for '{query}'."

    # ── open_site ─────────────────────────────────────────────────────────────
    if action == "open_site":
        if not site:
            site = url or query
        if not site:
            return "Please provide a site name or URL."

        site_lower = site.lower().strip()

        # Direct lookup in known sites
        target_url = KNOWN_SITES.get(site_lower)

        # Fuzzy lookup — partial key match
        if not target_url:
            for key, val in KNOWN_SITES.items():
                if key in site_lower or site_lower in key:
                    target_url = val
                    break

        # If still not found: check if looks like a domain
        if not target_url:
            if "." in site and " " not in site:
                target_url = f"https://{site}" if not site.startswith("http") else site
            else:
                # Fall back to Google search for the site name
                encoded = urllib.parse.quote_plus(site)
                target_url = f"https://www.google.com/search?q={encoded}"
                print(f"[BrowserOpen] Site not in known list, falling back to search: {site!r}")
                if _open_in_lumina_browser(target_url):
                    return f"Couldn't find a direct URL for '{site}', searching Google instead."
                return f"Could not open or search for '{site}'."

        print(f"[BrowserOpen] Opening site '{site}' -> {target_url} in Lumina browser")
        if _open_in_lumina_browser(target_url):
            return f"Opening {site.title()} in Lumina's browser."
        return f"Could not open {site}."

    return f"Unknown action '{action}'. Use: open_url, google_search, or open_site."
