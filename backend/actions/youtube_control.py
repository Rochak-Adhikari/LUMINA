"""
actions/youtube_control.py — DEPRECATED

youtube_control has been removed as an active execution path.
YouTube requests are now routed through browser_open (browser_open action=open_url).

This file is kept as a dormant shim. It is NOT registered in ACTION_REGISTRY
and NOT exposed in tools_list. The model cannot call it.

If somehow invoked directly, it logs a deprecation warning and opens the
YouTube search page via subprocess (same as _open_url in v3).
"""

import os
import platform
import subprocess
import urllib.parse

_OS = platform.system()

YT_BASE  = "https://www.youtube.com"
YTM_BASE = "https://music.youtube.com"

# ---------------------------------------------------------------------------
# Configuration — env-driven, mirrors local_browser_control.py defaults
# ---------------------------------------------------------------------------

_CDP_PORT         = int(os.environ.get("LUMINA_CDP_PORT",      "9223"))
_LUMINA_PROFILE   = os.environ.get("LUMINA_BROWSER_PROFILE",   r"E:\LuminaBrowser\profile").strip()
_LUMINA_DOWNLOADS = os.environ.get("LUMINA_BROWSER_DOWNLOADS", r"E:\LuminaBrowser\downloads").strip()
_LUMINA_WINDOW_W  = int(os.environ.get("LUMINA_WINDOW_W", "1100"))
_LUMINA_WINDOW_H  = int(os.environ.get("LUMINA_WINDOW_H", "700"))
_LUMINA_WINDOW_X  = int(os.environ.get("LUMINA_WINDOW_X", "100"))
_LUMINA_WINDOW_Y  = int(os.environ.get("LUMINA_WINDOW_Y", "100"))


def _detect_brave_exe() -> str:
    candidates = [
        os.path.join(os.environ.get("PROGRAMFILES",      r"C:\Program Files"),
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


_BRAVE_EXE = os.environ.get("BRAVE_EXECUTABLE_PATH", "").strip() or _detect_brave_exe()


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def _yt_search_url(query: str) -> str:
    return f"{YT_BASE}/results?search_query={urllib.parse.quote_plus(query)}"


# ---------------------------------------------------------------------------
# Browser launcher — delegates to Lumina's dedicated Brave instance
# ---------------------------------------------------------------------------

def _open_url(url: str) -> bool:
    """
    Open *url* in Lumina's dedicated Brave browser.

    Uses the same profile and flags as local_browser_control.py so both
    subsystems share one browser window. Brave's single-instance model
    handles the rest: if the browser is already running, this opens the
    URL as a new tab in the existing window.

    No CDP check. No Playwright. Pure subprocess.
    """
    # Prefer the embedded browser workspace (Electron renderer) — same routing
    # as browser_open, so YouTube opens in-app instead of an external window.
    try:
        from actions import emit_workspace_browser
        if emit_workspace_browser(url):
            print(f"[YouTube] Routed to embedded browser panel: {url}")
            return True
    except Exception as e:
        print(f"[YouTube] Embedded routing unavailable ({e}); falling back")

    if not os.path.isfile(_BRAVE_EXE):
        print(f"[YouTube] Brave not found at: {_BRAVE_EXE}")
        return False

    try:
        os.makedirs(_LUMINA_PROFILE,   exist_ok=True)
        os.makedirs(_LUMINA_DOWNLOADS, exist_ok=True)
    except Exception:
        pass

    cmd = [
        _BRAVE_EXE,
        f"--remote-debugging-port={_CDP_PORT}",
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

    print(f"[YouTube] Delegating to Lumina browser: {url}")

    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS if _OS == "Windows" else 0,
        )
        print(f"[YouTube] Browser launch OK")
        return True
    except Exception as e:
        print(f"[YouTube] Browser launch FAILED: {e}")
        return False


# ---------------------------------------------------------------------------
# Public tool entry point
# ---------------------------------------------------------------------------

def youtube_control(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """DEPRECATED — YouTube requests now route through browser_open."""
    print("[YOUTUBE ROUTE] youtube_control deprecated/removed — redirecting to browser automation")
    params  = parameters or {}
    action  = params.get("action", "open_home").strip().lower().replace(" ", "_")
    query   = params.get("query", "").strip()
    channel = params.get("channel", "").strip()
    url     = params.get("url", "").strip()

    # ── open_home ─────────────────────────────────────────────────────────────
    if action in ("open_home", "open", "home"):
        print("[YouTube] Action: open_home")
        _open_url(YT_BASE)
        return "Opening YouTube."

    # ── search ────────────────────────────────────────────────────────────────
    if action == "search":
        if not query:
            return "Please provide a search query for YouTube."
        target = _yt_search_url(query)
        print(f"[YouTube] Action: search — query={query!r} url={target}")
        _open_url(target)
        return f"Searching YouTube for: {query}"

    # ── play_first ────────────────────────────────────────────────────────────
    if action == "play_first":
        if not query:
            return "Please provide a query to play on YouTube."
        target = _yt_search_url(query)
        print(f"[YouTube] Action: play_first — query={query!r} url={target}")
        ok = _open_url(target)
        if ok:
            return (
                f"Opened YouTube search results for '{query}'. "
                "Click the first video to start playback."
            )
        return f"Could not open browser for YouTube search: {query}"

    # ── open_channel ──────────────────────────────────────────────────────────
    if action == "open_channel":
        if not channel:
            channel = query
        if not channel:
            return "Please provide a channel name or @handle."

        ch = channel.strip()
        if " " not in ch:
            handle = ch if ch.startswith("@") else f"@{ch}"
            target = f"{YT_BASE}/{urllib.parse.quote(handle)}"
        else:
            target = _yt_search_url(f"{channel} youtube channel")

        print(f"[YouTube] Action: open_channel — channel={channel!r} url={target}")
        _open_url(target)
        return f"Opening YouTube channel: {channel}"

    # ── open_url ──────────────────────────────────────────────────────────────
    if action == "open_url":
        if not url:
            return "Please provide a YouTube URL to open."
        if url.startswith("/"):
            url = YT_BASE + url
        elif not url.startswith("http"):
            url = f"{YT_BASE}/{url}"
        print(f"[YouTube] Action: open_url — url={url}")
        _open_url(url)
        return f"Opening YouTube: {url}"

    # ── trending ──────────────────────────────────────────────────────────────
    if action in ("trending", "explore"):
        target = f"{YT_BASE}/feed/trending"
        print("[YouTube] Action: trending")
        _open_url(target)
        return "Opening YouTube Trending."

    # ── shorts ────────────────────────────────────────────────────────────────
    if action == "shorts":
        target = f"{YT_BASE}/shorts"
        print("[YouTube] Action: shorts")
        _open_url(target)
        return "Opening YouTube Shorts."

    # ── music ─────────────────────────────────────────────────────────────────
    if action in ("music", "youtube_music"):
        target = YTM_BASE if not query else (
            f"{YTM_BASE}/search?q={urllib.parse.quote_plus(query)}"
        )
        print(f"[YouTube] Action: music — target={target}")
        _open_url(target)
        return "Opening YouTube Music." if not query else f"Searching YouTube Music for: {query}"

    # ── subscriptions / library / history ─────────────────────────────────────
    if action in ("subscriptions", "subs"):
        print("[YouTube] Action: subscriptions")
        _open_url(f"{YT_BASE}/feed/subscriptions")
        return "Opening YouTube Subscriptions."

    if action in ("library", "history"):
        target = f"{YT_BASE}/feed/library" if action == "library" else f"{YT_BASE}/feed/history"
        print(f"[YouTube] Action: {action}")
        _open_url(target)
        return f"Opening YouTube {action.title()}."

    # ── Fallback: treat unknown action as search query ─────────────────────────
    fallback_query = query or action.replace("_", " ")
    print(f"[YouTube] Unknown action '{action}' — falling back to search: {fallback_query!r}")
    _open_url(_yt_search_url(fallback_query))
    return f"Searching YouTube for: {fallback_query}"


def youtube_play(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Advertised tool `youtube_play` — play/search a video on YouTube.

    The tool schema (tools/__init__.py::youtube_play_tool) is `{query}`.
    This adapter maps it onto the existing youtube_control(play_first) logic so
    the advertised tool has a real, registered handler (fixes "Unknown tool").
    """
    params = parameters or {}
    query = (params.get("query") or params.get("q") or "").strip()
    if not query:
        return "Please provide something to play on YouTube."
    return youtube_control(
        {"action": "play_first", "query": query},
        response, player, session_memory,
    )

