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


# URL substrings that strongly indicate active media playback. Used by the
# tab-reuse guard to avoid clobbering a tab the user is currently listening to
# or watching. Conservative on purpose: only well-known media URLs.
_MEDIA_URL_SUBSTRINGS = (
    "youtube.com/watch",        # YT video page
    "music.youtube.com",        # YT Music (any path; usually has playback)
    "open.spotify.com/track/",  # Spotify track
    "open.spotify.com/episode/",
    "open.spotify.com/album/",
    "open.spotify.com/playlist/",
    "netflix.com/watch",
    "primevideo.com/detail",
    "soundcloud.com/",          # SoundCloud (broad; rare false positives)
)


def _is_likely_media_tab(url: str) -> bool:
    """Heuristic: does this URL indicate the tab is likely playing media?

    URL-only check by design — fast (no extra CDP roundtrip) and stable.
    False positives only cost an extra new tab; false negatives interrupt
    playback, so the substring list is restricted to clear-cut media pages.
    """
    if not url:
        return False
    u = url.lower()
    return any(p in u for p in _MEDIA_URL_SUBSTRINGS)


def _try_navigate_active_tab(url: str) -> bool:
    """
    Navigate a reusable Lumina browser tab in-place via raw CDP WebSocket.

    Reuse-first policy with media-state guard:
      1. If the most-recently-active page is NOT playing media → navigate it.
      2. If it IS likely playing media → skip it and try the next non-media,
         non-devtools page.
      3. If every reusable page is a media tab → return False so the caller
         opens the URL in a new tab, preserving playback.

    Uses only Python stdlib — no external WebSocket libraries required.

    Media detection is URL-based (see `_is_likely_media_tab`). True playback
    state via the Media Session API would require an extra CDP round-trip
    per page; the URL heuristic covers the common cases (YouTube, Spotify,
    Netflix) with negligible overhead.
    """
    import json as _json, base64, socket, struct, os as _os

    try:
        r = urllib.request.urlopen(
            f"http://127.0.0.1:{_LUMINA_CDP_PORT}/json", timeout=2
        )
        pages = _json.loads(r.read())
        r.close()
    except Exception:
        return False

    # Candidates: real page tabs only (no devtools, no service workers).
    reusable = [
        p for p in pages
        if p.get("type") == "page"
        and "devtools" not in p.get("url", "").lower()
    ]
    if not reusable:
        return False

    # Prefer the first non-media page; fall through to None if every tab
    # appears to be a media tab (caller will open a fresh tab).
    target = next(
        (p for p in reusable if not _is_likely_media_tab(p.get("url", ""))),
        None,
    )
    if not target:
        print(f"[BrowserOpen] All reusable tabs are media tabs — opening new tab to preserve playback")
        return False

    ws_url = target.get("webSocketDebuggerUrl", "")
    if not ws_url:
        return False

    # Parse  ws://host:port/path
    ws_path = ws_url.replace("ws://", "").replace("wss://", "")
    slash = ws_path.find("/")
    hostport = ws_path[:slash] if slash >= 0 else ws_path
    path = ws_path[slash:] if slash >= 0 else "/"
    host, _, port_str = hostport.partition(":")
    port = int(port_str) if port_str else 80

    ws_key = base64.b64encode(_os.urandom(16)).decode()
    handshake = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {hostport}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {ws_key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )

    try:
        s = socket.create_connection((host, port), timeout=5)
        s.sendall(handshake.encode())

        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = s.recv(512)
            if not chunk:
                break
            buf += chunk

        if b"101" not in buf:
            s.close()
            return False

        payload = _json.dumps(
            {"id": 1, "method": "Page.navigate", "params": {"url": url}}
        ).encode("utf-8")
        mask = _os.urandom(4)
        length = len(payload)
        if length < 126:
            header = bytes([0x81, 0x80 | length])
        else:
            header = bytes([0x81, 0xFE]) + struct.pack(">H", length)
        frame = header + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        s.sendall(frame)

        s.settimeout(2)
        try:
            s.recv(512)
        except Exception:
            pass
        s.close()
        print(f"[BrowserOpen] Reused active tab -> {url}")
        return True
    except Exception as e:
        print(f"[BrowserOpen] Tab reuse via CDP failed: {e}")
        return False


def _open_in_lumina_browser(url: str) -> bool:
    """
    Open a URL for normal browsing.

    Primary path (desired UX): route to the EMBEDDED browser panel in the
    Electron renderer via a `workspace_open` event. No external window appears.

    Fallback (frontend unreachable — headless, no socket): use Lumina's
    dedicated Brave browser (reuse-first via CDP, else launch). The dedicated
    Brave remains the automation browser; this fallback only covers the case
    where the embedded panel can't receive the URL.

    NEVER uses os.startfile, NEVER opens in personal Brave.
    """
    # 1. Prefer the embedded browser workspace (Electron renderer).
    try:
        from actions import emit_workspace_browser
        if emit_workspace_browser(url):
            print(f"[BrowserOpen] Routed to embedded browser panel: {url}")
            return True
    except Exception as e:
        print(f"[BrowserOpen] Embedded routing unavailable ({e}); falling back")

    # 2. Fallback — dedicated Brave (frontend not reachable).
    if not os.path.isfile(_BRAVE_EXE):
        print(f"[BrowserOpen] Brave not found at {_BRAVE_EXE}")
        return False

    _ensure_lumina_dirs()

    try:
        if _cdp_reachable():
            # Prefer in-place navigation — reuse the active tab
            if _try_navigate_active_tab(url):
                return True
            # CDP navigation failed — fall back to new tab in existing window
            print(f"[BrowserOpen] Tab reuse unavailable, opening new tab")
            cmd = [
                _BRAVE_EXE,
                f"--user-data-dir={_LUMINA_PROFILE}",
                "--profile-directory=Default",
                url,
            ]
        else:
            # Lumina browser not running — launch it fresh with this URL
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
