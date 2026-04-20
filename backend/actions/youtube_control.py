"""
actions/youtube_control.py — Lumina YouTube control tool

Handles YouTube-specific commands by constructing and opening
YouTube URLs in the system default browser.

V2 — Tab-reuse aware.
- Tries to find and reuse an existing YouTube tab via CDP (no new tab spam).
- play_first: navigates existing YT tab to search results, then clicks first video
  via CDP for reliable playback. Falls back to os.startfile if CDP unavailable.
- All actions share the same YouTube tab when one is already open.

Supported actions:
    open_home       — open YouTube home
    search          — search YouTube for a query
    play_first      — search and play the first result
    open_channel    — open a YouTube channel by name/handle
    open_url        — open a specific youtube.com URL
    trending        — open YouTube trending
    shorts          — open YouTube Shorts feed
    music           — open YouTube Music
    subscriptions   — open YouTube Subscriptions
    library         — open YouTube Library
    history         — open YouTube History
"""

import asyncio
import os
import platform
import subprocess
import urllib.parse

_OS = platform.system()

YT_BASE   = "https://www.youtube.com"
YTM_BASE  = "https://music.youtube.com"

# CDP port — must match Lumina's dedicated browser port (9223, not 9222)
# 9222 is the personal Brave port. Lumina uses 9223.
_CDP_PORT = int(os.environ.get("LUMINA_CDP_PORT", "9223"))

# Lumina dedicated profile — matches local_browser_control.py and browser_open.py
_LUMINA_PROFILE   = os.environ.get("LUMINA_BROWSER_PROFILE",   r"E:\LuminaBrowser\profile").strip()
_LUMINA_DOWNLOADS = os.environ.get("LUMINA_BROWSER_DOWNLOADS", r"E:\LuminaBrowser\downloads").strip()
_LUMINA_WINDOW_W  = int(os.environ.get("LUMINA_WINDOW_W", "1100"))
_LUMINA_WINDOW_H  = int(os.environ.get("LUMINA_WINDOW_H", "700"))
_LUMINA_WINDOW_X  = int(os.environ.get("LUMINA_WINDOW_X", "100"))
_LUMINA_WINDOW_Y  = int(os.environ.get("LUMINA_WINDOW_Y", "100"))


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


_BRAVE_EXE = os.environ.get("BRAVE_EXECUTABLE_PATH", "").strip() or _detect_brave_exe()


# ---------------------------------------------------------------------------
# Low-level URL opener — uses Lumina's dedicated browser, never personal Brave
# ---------------------------------------------------------------------------

def _open_url_os(url: str) -> bool:
    """
    Open URL in Lumina's dedicated Brave browser.
    If already running (CDP reachable), opens as a new tab in the existing window.
    If not running, launches the dedicated instance.
    NEVER uses os.startfile / personal browser.
    """
    if not os.path.isfile(_BRAVE_EXE):
        return False

    try:
        os.makedirs(_LUMINA_PROFILE, exist_ok=True)
        os.makedirs(_LUMINA_DOWNLOADS, exist_ok=True)
    except Exception:
        pass

    try:
        if _cdp_reachable():
            # Already running — Brave will open a new tab in the existing window
            cmd = [
                _BRAVE_EXE,
                f"--user-data-dir={_LUMINA_PROFILE}",
                "--profile-directory=Default",
                url,
            ]
        else:
            # Launch the dedicated Lumina browser with this URL
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
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS if _OS == "Windows" else 0,
        )
        return True
    except Exception as e:
        print(f"[YouTube] Failed to open in Lumina browser: {e}")
        return False


def _yt_search_url(query: str) -> str:
    return f"{YT_BASE}/results?search_query={urllib.parse.quote_plus(query)}"


def _cdp_reachable() -> bool:
    """Quick check if CDP endpoint is responding."""
    import urllib.request
    try:
        req = urllib.request.urlopen(
            f"http://127.0.0.1:{_CDP_PORT}/json/version", timeout=2
        )
        req.close()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# CDP-based YouTube tab reuse
# ---------------------------------------------------------------------------

async def _cdp_navigate_youtube(target_url: str) -> dict:
    """
    Navigate an existing YouTube tab (or create one) to target_url via CDP.

    Strategy:
    1. Connect to running Brave via CDP (no restart, safe attach only).
    2. Find an existing tab whose URL contains youtube.com / youtu.be.
    3. If found, navigate that tab to target_url (reuse).
    4. If not found, open a new tab with target_url.
    5. Return {success, method, url}.

    IMPORTANT: Uses browser.disconnect() NOT browser.close().
    In CDP-connect mode, close() kills the real browser process.
    disconnect() only tears down the Playwright wrapper — tabs stay alive.
    """
    if not _cdp_reachable():
        return {"success": False, "reason": "cdp_unavailable"}

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.connect_over_cdp(
                f"http://127.0.0.1:{_CDP_PORT}"
            )
            contexts = browser.contexts
            if not contexts:
                await browser.close()
                return {"success": False, "reason": "no_context"}

            ctx = contexts[0]
            pages = ctx.pages

            # Find an existing YouTube tab
            yt_page = None
            for page in pages:
                try:
                    url = page.url
                    if "youtube.com" in url or "youtu.be" in url:
                        yt_page = page
                        break
                except Exception:
                    continue

            if yt_page:
                # Reuse existing YouTube tab
                await yt_page.bring_to_front()
                await yt_page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
                method = "reuse"
            else:
                # No YouTube tab found — open a new one
                yt_page = await ctx.new_page()
                await yt_page.bring_to_front()
                await yt_page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
                method = "new_tab"

            final_url = yt_page.url
            # In CDP-connect mode, close() only tears down the Playwright channel
            # (_should_close_connection_on_close=False). The real browser stays alive.
            await browser.close()
            return {"success": True, "method": method, "url": final_url}

    except Exception as e:
        return {"success": False, "reason": str(e)}


async def _cdp_play_first_result(query: str) -> dict:
    """
    Navigate YouTube search results for `query` in an existing/new YouTube tab,
    then navigate directly to the first video URL and start playback.

    Strategy:
    1. Navigate YT tab to search URL.
    2. Wait for ytd-video-renderer to appear.
    3. PRIMARY: Extract first /watch?v= href from DOM and goto it directly
       (more reliable than .click() on YouTube SPA).
    4. FALLBACK: Try .click() on the first video-title anchor.
    5. After landing on video page, JS-unmute and press 'k' to ensure playback.
    6. CRITICAL: Uses browser.disconnect() NOT browser.close().

    Returns {success, method, url, played} or {success: False, reason}.
    """
    if not _cdp_reachable():
        return {"success": False, "reason": "cdp_unavailable"}

    search_url = _yt_search_url(query)

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.connect_over_cdp(
                f"http://127.0.0.1:{_CDP_PORT}"
            )
            contexts = browser.contexts
            if not contexts:
                await browser.close()
                return {"success": False, "reason": "no_context"}

            ctx = contexts[0]
            pages = ctx.pages

            # Find or create a YouTube tab
            yt_page = None
            for page in pages:
                try:
                    if "youtube.com" in page.url or "youtu.be" in page.url:
                        yt_page = page
                        break
                except Exception:
                    continue

            method_prefix = "reuse" if yt_page else "new_tab"
            if not yt_page:
                yt_page = await ctx.new_page()

            await yt_page.bring_to_front()
            await yt_page.goto(search_url, wait_until="domcontentloaded", timeout=20000)

            # Wait for search results to load
            try:
                await yt_page.wait_for_selector(
                    "ytd-video-renderer, ytd-rich-item-renderer",
                    timeout=8000
                )
            except Exception:
                await asyncio.sleep(2)

            navigated = False
            video_url = None

            # PRIMARY: Extract first /watch?v= href from DOM and navigate directly.
            # This is more reliable than .click() on YouTube's SPA (which may not
            # trigger the router if the element is off-screen or not in focus).
            try:
                watch_href = await yt_page.evaluate("""
                    () => {
                        // Prefer links inside a video renderer container
                        const containers = document.querySelectorAll(
                            'ytd-video-renderer, ytd-rich-item-renderer');
                        for (const c of containers) {
                            const a = c.querySelector('a#video-title, a.yt-simple-endpoint');
                            if (a) {
                                const h = a.getAttribute('href');
                                if (h && h.startsWith('/watch?v=')) return h;
                            }
                        }
                        // Fallback: any /watch?v= link on the page
                        for (const a of document.querySelectorAll('a[href]')) {
                            const h = a.getAttribute('href');
                            if (h && h.startsWith('/watch?v=')) return h;
                        }
                        return null;
                    }
                """)
                if watch_href:
                    video_url = f"https://www.youtube.com{watch_href}"
                    await yt_page.goto(video_url, wait_until="domcontentloaded", timeout=20000)
                    navigated = True
            except Exception:
                pass

            # FALLBACK: .click() on first video-title anchor
            if not navigated:
                _SELECTORS = [
                    "ytd-video-renderer a#video-title",
                    "ytd-video-renderer a.yt-simple-endpoint",
                    "ytd-rich-item-renderer a#video-title",
                    "a#video-title",
                ]
                for sel in _SELECTORS:
                    try:
                        el = await yt_page.query_selector(sel)
                        if el:
                            href = await el.get_attribute("href")
                            if href and "/watch" in href:
                                await el.click()
                                await asyncio.sleep(1.5)
                                navigated = True
                                video_url = yt_page.url
                                break
                    except Exception:
                        continue

            played = False
            if navigated:
                # Wait for video element and start playback
                await asyncio.sleep(1.5)
                try:
                    play_result = await yt_page.evaluate("""
                        () => {
                            const v = document.querySelector('video');
                            if (!v) return {found: false};
                            v.muted = false;
                            if (v.volume < 0.1) v.volume = 0.8;
                            const was_paused = v.paused;
                            if (v.paused) v.play().catch(() => {});
                            return {found: true, was_paused: was_paused,
                                    paused: v.paused, volume: v.volume};
                        }
                    """)
                    played = play_result.get("found", False)
                except Exception:
                    pass
                # Keyboard nudge as backup
                if not played:
                    try:
                        await yt_page.keyboard.press("k")
                        played = True
                    except Exception:
                        pass

            final_url = yt_page.url
            # In CDP-connect mode, close() only tears down the Playwright channel.
            # The real browser and all its tabs stay alive.
            await browser.close()

            if navigated and played:
                return {"success": True, "played": True,
                        "method": method_prefix + "+goto", "url": final_url}
            elif navigated and not played:
                return {"success": True, "played": False,
                        "method": method_prefix + "+goto_no_play", "url": final_url}
            else:
                return {"success": False, "reason": "no_video_link_found",
                        "url": final_url}

    except Exception as e:
        return {"success": False, "reason": str(e)}


def _navigate_youtube(target_url: str) -> str:
    """
    Synchronous wrapper: try CDP tab reuse first, fall back to os.startfile.
    Returns a human-readable status string.
    """
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_cdp_navigate_youtube(target_url))
        loop.close()
    except Exception as e:
        result = {"success": False, "reason": str(e)}

    if result.get("success"):
        method = result.get("method", "")
        if method == "reuse":
            return "reuse"
        return "new_tab_cdp"
    else:
        # CDP unavailable or failed — fall back to OS open (may create new tab)
        _open_url_os(target_url)
        return "os_open"


# ---------------------------------------------------------------------------
# Public tool entry point
# ---------------------------------------------------------------------------

def youtube_control(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Lumina YouTube control tool.

    parameters:
        action  : Action to perform (see supported list above)
        query   : Search query (for search / play_first)
        channel : Channel name or @handle (for open_channel)
        url     : Specific YouTube URL (for open_url)
    """
    params  = parameters or {}
    action  = params.get("action", "open_home").strip().lower().replace(" ", "_")
    query   = params.get("query", "").strip()
    channel = params.get("channel", "").strip()
    url     = params.get("url", "").strip()

    # ── open_home ─────────────────────────────────────────────────────────────
    if action in ("open_home", "open", "home"):
        print("[YouTube] Opening Home")
        method = _navigate_youtube(YT_BASE)
        if method == "reuse":
            return "Navigated existing YouTube tab to YouTube home."
        return "Opening YouTube home."

    # ── search ────────────────────────────────────────────────────────────────
    if action == "search":
        if not query:
            return "Please provide a search query for YouTube."
        target = _yt_search_url(query)
        print(f"[YouTube] Searching: {query!r}")
        method = _navigate_youtube(target)
        if method == "reuse":
            return f"Searching YouTube for: {query} (reused existing tab)"
        return f"Searching YouTube for: {query}"

    # ── play_first ────────────────────────────────────────────────────────────
    if action == "play_first":
        if not query:
            return "Please provide a query to play on YouTube."
        print(f"[YouTube] play_first via CDP: {query!r}")

        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(_cdp_play_first_result(query))
            loop.close()
        except Exception as e:
            result = {"success": False, "reason": str(e)}

        if result.get("success"):
            tab_note = "(reused existing YouTube tab)" if "reuse" in result.get("method", "") else "(new YouTube tab)"
            if result.get("played"):
                return f"Now playing first YouTube result for: {query} {tab_note}"
            else:
                # Navigated to video page but playback may not have started
                return (
                    f"Opened first YouTube result for: {query} {tab_note}. "
                    "Video page loaded — playback should start automatically, "
                    "or press play if it did not."
                )
        else:
            reason = result.get("reason", "unknown")
            print(f"[YouTube] play_first CDP failed ({reason}), falling back to search page")
            if reason == "cdp_unavailable":
                # No CDP — open search page via OS, tell user honestly
                _open_url_os(_yt_search_url(query))
                return (
                    f"Opened YouTube search for '{query}'. "
                    "Auto-play is not available (browser remote debugging is off). "
                    "Please click the first result to start playback."
                )
            else:
                # CDP available but click/navigation failed
                search_url = _yt_search_url(query)
                method = _navigate_youtube(search_url)
                tab_note = "(reused existing tab)" if method == "reuse" else ""
                return (
                    f"Opened YouTube search for '{query}' {tab_note}. "
                    f"Could not auto-click the first result ({reason}). "
                    "Please click it to start playback."
                )

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
            print(f"[YouTube] Channel has spaces, searching: {channel!r}")
            method = _navigate_youtube(target)
            return f"Searching YouTube for channel: {channel}"

        print(f"[YouTube] Opening channel: {target}")
        method = _navigate_youtube(target)
        if method == "reuse":
            return f"Navigated to YouTube channel: {channel} (reused existing tab)"
        return f"Opening YouTube channel: {channel}"

    # ── open_url ──────────────────────────────────────────────────────────────
    if action == "open_url":
        if not url:
            return "Please provide a YouTube URL to open."
        if url.startswith("/"):
            url = YT_BASE + url
        elif not url.startswith("http"):
            url = f"{YT_BASE}/{url}"
        print(f"[YouTube] Opening URL: {url}")
        method = _navigate_youtube(url)
        return f"Opening YouTube: {url}"

    # ── trending ──────────────────────────────────────────────────────────────
    if action in ("trending", "explore"):
        target = f"{YT_BASE}/feed/trending"
        print("[YouTube] Opening Trending")
        _navigate_youtube(target)
        return "Opening YouTube Trending."

    # ── shorts ────────────────────────────────────────────────────────────────
    if action == "shorts":
        target = f"{YT_BASE}/shorts"
        print("[YouTube] Opening Shorts")
        _navigate_youtube(target)
        return "Opening YouTube Shorts."

    # ── music ─────────────────────────────────────────────────────────────────
    if action in ("music", "youtube_music"):
        target = YTM_BASE if not query else (
            f"{YTM_BASE}/search?q={urllib.parse.quote_plus(query)}"
        )
        print(f"[YouTube] Opening Music: {target}")
        _navigate_youtube(target)
        return "Opening YouTube Music." if not query else f"Searching YouTube Music for: {query}"

    # ── subscriptions / library / history ─────────────────────────────────────
    if action in ("subscriptions", "subs"):
        _navigate_youtube(f"{YT_BASE}/feed/subscriptions")
        return "Opening YouTube Subscriptions."

    if action in ("library", "history"):
        target = f"{YT_BASE}/feed/library" if action == "library" else f"{YT_BASE}/feed/history"
        _navigate_youtube(target)
        return f"Opening YouTube {action.title()}."

    # ── Fallback: treat unknown action as search query ─────────────────────────
    fallback_query = query or action.replace("_", " ")
    print(f"[YouTube] Unknown action '{action}', falling back to search: {fallback_query!r}")
    target = _yt_search_url(fallback_query)
    _navigate_youtube(target)
    return f"Searching YouTube for: {fallback_query}"
