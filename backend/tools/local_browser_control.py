"""
Phase T2: Local Browser Control — Lumina's dedicated Brave browser.

Lumina owns a completely separate Brave instance that NEVER touches the
user's personal Brave profile or session.

Dedicated browser configuration:
    Profile dir  : E:\\LuminaBrowser\\profile  (env: LUMINA_BROWSER_PROFILE)
    Downloads    : E:\\LuminaBrowser\\downloads (env: LUMINA_BROWSER_DOWNLOADS)
    CDP port     : 9223                         (env: LUMINA_CDP_PORT)
    Window size  : 1100x700                     (env: LUMINA_WINDOW_W / LUMINA_WINDOW_H)
    Window pos   : 100,100                      (env: LUMINA_WINDOW_X / LUMINA_WINDOW_Y)

Rules:
    - NEVER kills all brave.exe processes
    - NEVER attaches to or inspects the user's personal Brave
    - NEVER uses the personal user-data-dir
    - Uses port 9223 (not 9222) to avoid collision with personal Brave
    - If Lumina's browser is not running, CLASS 3 auto-launches it
    - CLASS 1/2 require the dedicated browser to already be running

Single async entrypoint:
    execute_local_browser(action, params, context) -> dict

Supported actions:
    open_url, play_pause, click_selector, click_at, scroll,
    go_back, go_forward, reload, get_state,
    get_clickables, click_text, click_best, list_tabs, switch_tab,
    close_tab, screenshot, new_tab, focus_textbox, type_text,
    press_keys, wait_for_text, get_active_state, analyze_screen

Guardrails:
    - browser_confirmation_mode: strict | relaxed | off
    - Dangerous content (post, send, submit, etc.) always requires confirmation
    - submit_form, upload_file, download permanently blocked
    - Only http/https URLs allowed
    - Structured {ok, message, data} responses with mandatory logging
"""

from __future__ import annotations

import asyncio
import base64
import collections
import logging
import os
import platform
import re
import subprocess
import time
import unicodedata
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger("lumina.local_browser")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[LOCAL_BROWSER] %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Configuration (env-driven, with sensible Windows defaults)
# ---------------------------------------------------------------------------

def _detect_brave_exe() -> str:
    """Auto-detect Brave executable on Windows."""
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


# ---------------------------------------------------------------------------
# Lumina dedicated browser constants
# IMPORTANT: These are completely separate from the user's personal Brave.
# Lumina NEVER reads from or writes to the user's real Brave profile.
# ---------------------------------------------------------------------------

BRAVE_EXE = os.environ.get("BRAVE_EXECUTABLE_PATH", "").strip() or _detect_brave_exe()

# Dedicated profile and downloads dirs — isolated from user's real Brave
LUMINA_BROWSER_PROFILE   = os.environ.get("LUMINA_BROWSER_PROFILE",   r"E:\LuminaBrowser\profile").strip()
LUMINA_BROWSER_DOWNLOADS = os.environ.get("LUMINA_BROWSER_DOWNLOADS", r"E:\LuminaBrowser\downloads").strip()

# Port 9223 — deliberately different from 9222 to avoid colliding with
# any personal Brave the user may have started with --remote-debugging-port=9222
CDP_PORT = int(os.environ.get("LUMINA_CDP_PORT", "9223"))

# Window geometry — small visible rectangle, not fullscreen
LUMINA_WINDOW_W = int(os.environ.get("LUMINA_WINDOW_W", "1100"))
LUMINA_WINDOW_H = int(os.environ.get("LUMINA_WINDOW_H", "700"))
LUMINA_WINDOW_X = int(os.environ.get("LUMINA_WINDOW_X", "100"))
LUMINA_WINDOW_Y = int(os.environ.get("LUMINA_WINDOW_Y", "100"))

AUTOSTART = os.environ.get("LOCAL_BROWSER_AUTOSTART", "true").strip().lower() == "true"

# Legacy aliases — kept so any remaining references don't break
BRAVE_USER_DATA = LUMINA_BROWSER_PROFILE
BRAVE_PROFILE   = "Default"

# Disallowed URL schemes
_BLOCKED_SCHEMES = {"file", "chrome", "brave", "javascript", "data", "about"}

# ---------------------------------------------------------------------------
# Action classification
# ---------------------------------------------------------------------------

_ALWAYS_SAFE = frozenset({
    "open_url", "new_tab", "switch_tab", "list_tabs", "scroll",
    "get_clickables", "get_state", "get_active_state", "analyze_screen",
    "screenshot", "go_back", "go_forward", "reload", "wait_for_text",
    "play_pause",
})

_CONDITIONALLY_SAFE = frozenset({
    "click_text", "click_best", "click_at", "click_selector",
    "focus_textbox", "press_keys", "type_text", "close_tab",
})

_ALWAYS_BLOCKED = frozenset({"submit_form", "upload_file", "download"})

_DANGEROUS_PATTERNS = re.compile(
    r"\b(post|send|submit|comment|reply|pay|buy|checkout|order|"
    r"delete|remove|clear|login|sign\s*in|sign\s*up|register|"
    r"allow|install|grant|authorize)\b",
    re.IGNORECASE
)

_RETRYABLE_ACTIONS = frozenset({"click_text", "click_best", "focus_textbox"})
_MAX_RETRIES = 2


def _normalize_text(text: str) -> str:
    """Normalize text for matching: lowercase, collapse whitespace, strip emoji/symbols/punctuation."""
    if not text:
        return ""
    text = ''.join(c for c in text if unicodedata.category(c)[0] not in ('S',))
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = text.strip(' \t\n\r.,!?;:()[]{}"\'\u2010\u2011\u2012\u2013\u2014-')
    return text


def _needs_confirmation(action: str, params: dict, mode: str) -> Tuple[bool, str]:
    """Determine if a non-blocked action needs user confirmation.
    Returns (needs_confirm, reason).
    """
    if action in _ALWAYS_SAFE:
        return False, "always_safe"

    target_text = str(params.get("text", "") or params.get("query", "") or
                      params.get("keys", "") or "")
    is_dangerous = bool(_DANGEROUS_PATTERNS.search(target_text))

    if is_dangerous:
        return True, f"dangerous_content:'{target_text[:50]}'"

    if mode == "off":
        return False, "mode_off"
    elif mode == "relaxed":
        if action == "type_text":
            return True, "type_text_relaxed"
        return False, "relaxed_safe"
    elif mode == "strict":
        return True, "strict_mode"
    return False, "default"

# ---------------------------------------------------------------------------
# CDP connection check
# ---------------------------------------------------------------------------

def _cdp_reachable() -> bool:
    """Quick check if Lumina's dedicated CDP endpoint is responding on port CDP_PORT."""
    import urllib.request
    try:
        req = urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/version", timeout=2)
        req.close()
        return True
    except Exception:
        return False


def _lumina_browser_running_without_debug() -> bool:
    """
    Check if any Brave process is bound to Lumina's CDP port without debug enabled.
    NOTE: We check only whether Lumina's own port (CDP_PORT=9223) is unreachable
    while a brave.exe exists that we previously launched. We do NOT scan all
    brave.exe processes — the user's personal Brave is not our concern.
    """
    if platform.system() != "Windows":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq brave.exe", "/NH"],
            capture_output=True, text=True, timeout=5
        )
        has_any_brave = "brave.exe" in result.stdout.lower()
        # Only report a conflict if brave is running AND our specific port is not answering.
        # The user's personal Brave on port 9222 does NOT count as a conflict.
        return has_any_brave and not _cdp_reachable()
    except Exception:
        return False


# Keep the old name as an alias so nothing else breaks
_brave_running_without_debug = _lumina_browser_running_without_debug


# ── 3-class browser action policy ───────────────────────────────────────────
#
# CLASS 1 — SAFE_ATTACH_ONLY: Read-only inspection of the current live session.
#   - Requires CDP to be ALREADY running (Brave launched with debug port).
#   - If CDP unavailable: return clear failure. NEVER restart Brave.
#   - Never touches user navigation. Never opens/closes tabs.
_SAFE_ATTACH_ONLY_ACTIONS = frozenset({
    "analyze_screen", "screenshot", "get_state", "get_active_state",
    "list_tabs", "get_clickables",
})

# CLASS 2 — LIVE_SESSION_ONLY: DOM interaction on the current live browser.
#   - Requires an already-attached CDP session.
#   - If CDP unavailable (no debug port running): return clear failure.
#   - NEVER restart Brave just to get a click target. The user's session
#     would be destroyed and replaced with a blank automation tab.
_LIVE_SESSION_ONLY_ACTIONS = frozenset({
    "click_text", "click_best", "click_at", "click_selector",
    "focus_textbox", "type_text", "press_keys", "play_pause",
    "scroll", "wait_for_text", "switch_tab", "close_tab",
    "go_back", "go_forward", "reload",
})

# CLASS 3 — AUTOMATION_ACTIONS: May legitimately restart/launch a dedicated
#   Brave session if the user has explicitly requested an automation task
#   that requires a fresh controlled browser (e.g. open_url in a new tab,
#   form fill flows). AUTOSTART applies only here.
#   NOTE: This set is intentionally small. Most actions belong in CLASS 1/2.
_AUTOMATION_ACTIONS = frozenset({
    "open_url", "new_tab",
})

# Legacy alias kept for any remaining internal references
_INTERACTION_ACTIONS = _LIVE_SESSION_ONLY_ACTIONS

# ---------------------------------------------------------------------------
# Lumina browser launcher
# ---------------------------------------------------------------------------

def _ensure_lumina_dirs() -> None:
    """Create dedicated profile and downloads dirs if they don't exist."""
    for d in (LUMINA_BROWSER_PROFILE, LUMINA_BROWSER_DOWNLOADS):
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create dir {d}: {e}")


def _launch_brave() -> subprocess.Popen:
    """
    Launch Lumina's dedicated Brave instance.

    Key properties:
    - Uses LUMINA_BROWSER_PROFILE (E:\\LuminaBrowser\\profile) — NOT the user's real Brave profile.
    - Uses CDP port 9223 — NOT 9222, so it never collides with personal Brave.
    - Opens as a small 1100x700 window at position (100, 100).
    - NEVER kills other brave.exe processes.
    - No --disable-gpu-compositing / --disable-software-rasterizer (those whiten the UI).
    """
    _ensure_lumina_dirs()
    cmd = [
        BRAVE_EXE,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={LUMINA_BROWSER_PROFILE}",
        "--profile-directory=Default",
        # Dedicated download directory
        f"--default-download-directory={LUMINA_BROWSER_DOWNLOADS}",
        # Small visible window — not fullscreen, not maximized
        f"--window-size={LUMINA_WINDOW_W},{LUMINA_WINDOW_H}",
        f"--window-position={LUMINA_WINDOW_X},{LUMINA_WINDOW_Y}",
        # Keep background-throttling disabled so automation tabs stay active.
        # DO NOT add --disable-gpu-compositing or --disable-software-rasterizer:
        # those flags destroy the GPU compositor path on Windows, turning the
        # entire browser UI white/invisible until a repaint is forced (e.g. F12).
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        # Open a new window (don't reuse existing session from a different profile)
        "--new-window",
        # Start on a blank page — don't restore previous session from personal profile
        "--no-first-run",
        "--no-default-browser-check",
    ]
    logger.info(f"[LUMINA BROWSER] Launching dedicated Brave: port={CDP_PORT} "
                f"profile={LUMINA_BROWSER_PROFILE} size={LUMINA_WINDOW_W}x{LUMINA_WINDOW_H}")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.DETACHED_PROCESS if platform.system() == "Windows" else 0,
    )
    return proc


# ---------------------------------------------------------------------------
# LocalBrowserController
# ---------------------------------------------------------------------------

class LocalBrowserController:
    """Manages a CDP connection to Lumina's dedicated Brave browser instance."""

    def __init__(self):
        self._playwright = None
        self._browser = None      # Playwright Browser (CDP-connected)
        self._context = None      # Default browser context
        self._page = None         # Active page/tab
        self._brave_proc = None   # Popen handle if we started Brave
        self._connected = False
        self._lumina_pages = set()  # Pages created by Lumina (tab safety)
        self._frame_cache = collections.deque(maxlen=10)
        self._last_frame_time = 0.0

    # -- lifecycle -----------------------------------------------------------

    async def ensure_connected(self, action: str = "") -> Dict[str, Any]:
        """Ensure Brave is running with CDP and we are connected.

        Args:
            action: the action that triggered this call. Used to decide whether
                    Brave auto-restart is appropriate.
        Returns {success, error} dict.
        """
        # Already connected — verify page is still alive
        if self._connected and self._page:
            try:
                await self._page.title()
                return {"success": True}
            except Exception:
                logger.info("Stale CDP connection, reconnecting...")
                self._connected = False
                self._lumina_pages.clear()
                self._frame_cache.clear()

        # ── 3-class policy enforcement ──────────────────────────────────────
        # Determine which class this action belongs to.
        _is_safe_attach   = action in _SAFE_ATTACH_ONLY_ACTIONS   # CLASS 1
        _is_live_session  = action in _LIVE_SESSION_ONLY_ACTIONS   # CLASS 2
        _is_automation    = action in _AUTOMATION_ACTIONS           # CLASS 3
        # Unknown actions default to live-session (no restart)
        if not (_is_safe_attach or _is_live_session or _is_automation):
            _is_live_session = True

        # Check if Lumina's dedicated CDP port is unreachable despite some Brave running.
        # NOTE: We NEVER kill the user's personal Brave. We only launch/manage our own
        # dedicated instance on port CDP_PORT (9223), which uses a completely separate profile.
        if _lumina_browser_running_without_debug():
            if _is_safe_attach:
                # CLASS 1: inspection — requires dedicated browser to be running with CDP
                msg = (
                    f"Lumina's dedicated browser is not reachable on port {CDP_PORT}. "
                    f"'{action}' requires the Lumina browser to be running. "
                    f"Ask Lumina to open a URL or new tab to launch the dedicated browser first."
                )
                logger.info(f"[BROWSER] CLASS1 {action}: Lumina browser not on CDP port — graceful failure")
                return {"success": False, "error": msg}

            elif _is_live_session:
                # CLASS 2: DOM interaction — requires already-attached dedicated browser
                msg = (
                    f"Lumina's dedicated browser is not reachable on port {CDP_PORT}. "
                    f"'{action}' requires an active Lumina browser session. "
                    f"Use 'open URL' first to launch the Lumina browser, then retry."
                )
                logger.info(f"[BROWSER] CLASS2 {action}: Lumina browser not on CDP port — graceful failure")
                return {"success": False, "error": msg}

            else:
                # CLASS 3: automation — launch Lumina's OWN dedicated browser.
                # NEVER kill all brave.exe. We only launch a new instance with our profile.
                logger.info(f"[BROWSER] CLASS3 {action}: launching Lumina's dedicated browser on port {CDP_PORT}")
                if AUTOSTART:
                    if os.path.isfile(BRAVE_EXE):
                        self._brave_proc = _launch_brave()
                        for _ in range(30):
                            await asyncio.sleep(0.5)
                            if _cdp_reachable():
                                break
                        else:
                            return {"success": False, "error": f"Lumina browser launched but CDP port {CDP_PORT} not ready after 15s."}
                    else:
                        return {"success": False, "error": f"Brave executable not found at: {BRAVE_EXE}."}
                else:
                    return {
                        "success": False,
                        "error": (
                            f"Lumina's dedicated browser is not running on port {CDP_PORT} and "
                            "LOCAL_BROWSER_AUTOSTART is disabled. Start the Lumina browser manually: "
                            f'brave.exe --remote-debugging-port={CDP_PORT} --user-data-dir="{LUMINA_BROWSER_PROFILE}"'
                        )
                    }

        # Lumina's dedicated browser is not running at all — decide by class
        if not _cdp_reachable():
            # CLASS 1: inspection requires the dedicated browser to already be running
            if _is_safe_attach:
                msg = (
                    f"Lumina's dedicated browser is not running (port {CDP_PORT} unreachable). "
                    f"'{action}' requires the Lumina browser. Ask Lumina to open a URL first."
                )
                logger.info(f"[BROWSER] CLASS1 {action}: Lumina browser not running — no launch")
                return {"success": False, "error": msg}

            # CLASS 2: same — DOM interaction needs an existing session
            if _is_live_session:
                msg = (
                    f"Lumina's dedicated browser is not running (port {CDP_PORT} unreachable). "
                    f"'{action}' requires an active Lumina browser session. "
                    "Use 'open URL' or 'open YouTube' first."
                )
                logger.info(f"[BROWSER] CLASS2 {action}: Lumina browser not running — no launch")
                return {"success": False, "error": msg}

            # CLASS 3: auto-launch Lumina's dedicated browser
            if not AUTOSTART:
                return {
                    "success": False,
                    "error": (
                        "Lumina's dedicated browser is not running and LOCAL_BROWSER_AUTOSTART is disabled. "
                        f"Start it with: brave.exe --remote-debugging-port={CDP_PORT} "
                        f'--user-data-dir="{LUMINA_BROWSER_PROFILE}"'
                    )
                }
            if not os.path.isfile(BRAVE_EXE):
                return {
                    "success": False,
                    "error": f"Brave executable not found at: {BRAVE_EXE}. Set BRAVE_EXECUTABLE_PATH."
                }
            self._brave_proc = _launch_brave()
            for _ in range(30):  # up to 15 seconds
                await asyncio.sleep(0.5)
                if _cdp_reachable():
                    break
            else:
                return {
                    "success": False,
                    "error": f"Lumina browser started but CDP not reachable on port {CDP_PORT} after 15s."
                }
            logger.info(f"[LUMINA BROWSER] Dedicated browser running on port {CDP_PORT}.")

        # Connect via Playwright CDP
        try:
            from playwright.async_api import async_playwright

            # Always tear down any stale playwright/browser handles before
            # connecting. If Brave was relaunched, the old playwright instance's
            # internal CDP WebSocket is dead — reusing it causes connect_over_cdp
            # to fail or attach to a broken context.
            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None
                self._context = None
                self._page = None

            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.connect_over_cdp(
                f"http://127.0.0.1:{CDP_PORT}"
            )
            # Get existing context (the user's real profile)
            contexts = self._browser.contexts
            if contexts:
                self._context = contexts[0]
            else:
                self._context = await self._browser.new_context()

            # Reuse existing page or create one
            pages = self._context.pages
            if pages:
                self._page = pages[-1]  # use most recent tab
            else:
                self._page = await self._context.new_page()

            self._connected = True
            title = await self._page.title()
            url = self._page.url
            logger.info(f"Connected via CDP. Active tab: {title} ({url})")
            return {"success": True}

        except Exception as e:
            logger.error(f"CDP connect failed: {e}")
            return {"success": False, "error": f"CDP connect failed: {e}"}

    async def disconnect(self):
        """Cleanly disconnect (does NOT close Brave)."""
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass
        self._browser = None
        self._context = None
        self._page = None
        self._connected = False
        self._lumina_pages.clear()
        self._frame_cache.clear()
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        logger.info("Disconnected from CDP.")

    # -- state ---------------------------------------------------------------

    async def get_state(self) -> Dict[str, Any]:
        """Return current tab state."""
        if not self._connected or not self._page:
            return {"url": None, "title": None}
        try:
            return {
                "url": self._page.url,
                "title": await self._page.title(),
            }
        except Exception:
            return {"url": None, "title": None}

    # -- actions -------------------------------------------------------------

    async def open_url(self, url: str) -> Dict[str, Any]:
        """Navigate the active tab to a URL."""
        parsed = urlparse(url)
        if parsed.scheme.lower() in _BLOCKED_SCHEMES or not parsed.scheme:
            return {"success": False, "error": f"Blocked URL scheme: {parsed.scheme or 'none'}. Only http/https allowed."}

        # Ensure scheme
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=20000)
            state = await self.get_state()
            logger.info(f"open_url ok -> {state['url']}")
            return {"success": True, "state": state}
        except Exception as e:
            return {"success": False, "error": str(e), "state": await self.get_state()}

    async def play_pause(self) -> Dict[str, Any]:
        """Toggle HTML5 video/audio playback. On YouTube, press 'k'. Generic fallback."""
        try:
            url = self._page.url
            is_youtube = "youtube.com" in url or "youtu.be" in url

            if is_youtube:
                # YouTube: press 'k' to toggle play/pause, then unmute
                await self._page.keyboard.press("k")
                await asyncio.sleep(0.3)
                # Unmute and set volume via JS
                unmute_result = await self._page.evaluate("""
                    (() => {
                        const v = document.querySelector('video');
                        if (!v) return {found: false};
                        v.muted = false;
                        if (v.volume < 0.3) v.volume = 0.8;
                        return {found: true, paused: v.paused, muted: v.muted, volume: v.volume};
                    })()
                """)
                logger.info(f"play_pause (YouTube 'k') -> {unmute_result}")
                return {"success": True, "state": await self.get_state(), "media": unmute_result}
            else:
                # Generic: find first video/audio and toggle
                result = await self._page.evaluate("""
                    (() => {
                        const v = document.querySelector('video') || document.querySelector('audio');
                        if (!v) return {found: false, error: 'No video or audio element found'};
                        v.muted = false;
                        if (v.volume < 0.3) v.volume = 0.8;
                        if (v.paused) { v.play(); } else { v.pause(); }
                        return {found: true, paused: v.paused, muted: v.muted, volume: v.volume};
                    })()
                """)
                logger.info(f"play_pause (generic) -> {result}")
                return {"success": True, "state": await self.get_state(), "media": result}

        except Exception as e:
            return {"success": False, "error": str(e), "state": await self.get_state()}

    async def click_selector(self, selector: str) -> Dict[str, Any]:
        """Click an element by CSS selector."""
        try:
            await self._page.click(selector, timeout=5000)
            await asyncio.sleep(0.3)
            logger.info(f"click_selector ok: {selector}")
            return {"success": True, "state": await self.get_state()}
        except Exception as e:
            return {"success": False, "error": str(e), "state": await self.get_state()}

    async def click_at(self, x: int, y: int) -> Dict[str, Any]:
        """Click at viewport coordinates."""
        try:
            await self._page.mouse.click(x, y)
            await asyncio.sleep(0.3)
            logger.info(f"click_at ok: ({x}, {y})")
            return {"success": True, "state": await self.get_state()}
        except Exception as e:
            return {"success": False, "error": str(e), "state": await self.get_state()}

    async def scroll(self, delta_y: int = 300) -> Dict[str, Any]:
        """Scroll the page vertically."""
        try:
            await self._page.mouse.wheel(0, delta_y)
            await asyncio.sleep(0.2)
            logger.info(f"scroll ok: deltaY={delta_y}")
            return {"success": True, "state": await self.get_state()}
        except Exception as e:
            return {"success": False, "error": str(e), "state": await self.get_state()}

    async def go_back(self) -> Dict[str, Any]:
        """Navigate back."""
        try:
            await self._page.go_back(timeout=10000)
            logger.info("go_back ok")
            return {"success": True, "state": await self.get_state()}
        except Exception as e:
            return {"success": False, "error": str(e), "state": await self.get_state()}

    async def go_forward(self) -> Dict[str, Any]:
        """Navigate forward."""
        try:
            await self._page.go_forward(timeout=10000)
            logger.info("go_forward ok")
            return {"success": True, "state": await self.get_state()}
        except Exception as e:
            return {"success": False, "error": str(e), "state": await self.get_state()}

    async def reload(self) -> Dict[str, Any]:
        """Reload current page."""
        try:
            await self._page.reload(timeout=15000)
            logger.info("reload ok")
            return {"success": True, "state": await self.get_state()}
        except Exception as e:
            return {"success": False, "error": str(e), "state": await self.get_state()}

    # -- page health & tab safety --------------------------------------------

    _CHECK_HEALTH_JS = """
    () => {
        const text = (document.body && document.body.innerText || '').trim();
        return {
            text_length: text.length,
            child_count: document.body ? document.body.childElementCount : 0,
            ready_state: document.readyState,
            url: location.href
        };
    }
    """

    async def _check_page_health(self) -> Dict[str, Any]:
        """Check if the current page is rendering properly (not white/blank)."""
        try:
            health = await self._page.evaluate(self._CHECK_HEALTH_JS)
            url = health.get("url", "")
            is_blank = (
                health["text_length"] < 5
                and health["ready_state"] == "complete"
                and url not in ("about:blank", "chrome://newtab/", "brave://newtab/")
                and url.startswith("http")
            )
            health["is_blank"] = is_blank
            return health
        except Exception:
            return {"is_blank": True, "error": "page unresponsive"}

    async def _recover_page(self) -> Dict[str, Any]:
        """Attempt to recover a blank/white page. Returns {recovered, method}."""
        url = self._page.url
        logger.warning(f"Blank page detected at {url}, attempting recovery...")

        # Step 1: Reload
        try:
            await self._page.reload(timeout=10000)
            await asyncio.sleep(1.5)
            health = await self._check_page_health()
            if not health.get("is_blank"):
                logger.info("Page recovered after reload")
                return {"recovered": True, "method": "reload"}
        except Exception as e:
            logger.warning(f"Reload recovery failed: {e}")

        # Step 2: Recreate the tab with the same URL
        try:
            if url and url.startswith("http"):
                old_page = self._page
                self._lumina_pages.discard(old_page)
                new_page = await self._context.new_page()
                self._lumina_pages.add(new_page)
                self._page = new_page
                await new_page.goto(url, wait_until="domcontentloaded", timeout=20000)
                try:
                    await old_page.close()
                except Exception:
                    pass
                await asyncio.sleep(1)
                health = await self._check_page_health()
                if not health.get("is_blank"):
                    logger.info("Page recovered after tab recreation")
                    return {"recovered": True, "method": "recreate_tab"}
        except Exception as e:
            logger.warning(f"Tab recreation recovery failed: {e}")

        return {"recovered": False, "method": "exhausted"}

    async def _ensure_lumina_tab(self) -> None:
        """Ensure we're operating in a Lumina-owned tab. Creates one if needed."""
        # Prune dead references
        if self._context:
            live_pages = set(self._context.pages)
            self._lumina_pages &= live_pages

        if self._page in self._lumina_pages:
            return  # Already in a Lumina tab

        page = await self._context.new_page()
        self._lumina_pages.add(page)
        self._page = page
        await page.bring_to_front()
        logger.info("Created Lumina-owned tab (tab safety)")

    # -- new primitive actions -----------------------------------------------

    async def new_tab(self, url: str = None) -> Dict[str, Any]:
        """Open a new browser tab, optionally navigating to a URL."""
        try:
            page = await self._context.new_page()
            self._lumina_pages.add(page)
            self._page = page
            await page.bring_to_front()

            if url:
                parsed = urlparse(url)
                if parsed.scheme.lower() in _BLOCKED_SCHEMES:
                    return {"success": False, "error": f"Blocked URL scheme: {parsed.scheme}"}
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)

            idx = list(self._context.pages).index(page)
            state = await self.get_state()
            logger.info(f"new_tab [{idx}] -> {state.get('url', 'about:blank')}")
            return {"success": True, "tab_index": idx, "state": state}
        except Exception as e:
            return {"success": False, "error": str(e)}

    _FIND_TEXTBOX_JS = """
    (hint) => {
        const MIN_SIZE = 15;
        const inputs = document.querySelectorAll(
            'input[type="text"], input[type="search"], input[type="email"], '
            + 'input[type="url"], input[type="tel"], input[type="number"], '
            + 'input:not([type]), textarea, [contenteditable="true"], '
            + '[role="textbox"], [role="searchbox"]'
        );
        let best = null;
        let bestScore = -1;
        const hintLower = (hint || '').toLowerCase();

        for (const el of inputs) {
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') continue;
            if (el.disabled || el.readOnly) continue;

            const rect = el.getBoundingClientRect();
            if (rect.width < MIN_SIZE || rect.height < MIN_SIZE) continue;
            if (rect.bottom < 0 || rect.top > window.innerHeight) continue;
            if (rect.right < 0 || rect.left > window.innerWidth) continue;

            let score = 10;
            const placeholder = (el.placeholder || '').toLowerCase();
            const aria = (el.getAttribute('aria-label') || '').toLowerCase();
            const name = (el.name || '').toLowerCase();
            const elId = (el.id || '').toLowerCase();

            if (hintLower) {
                for (const attr of [placeholder, aria, name, elId]) {
                    if (attr && (attr.includes(hintLower) || hintLower.includes(attr))) {
                        score += 50;
                    }
                }
            }

            if (el.type === 'search' || aria.includes('search') ||
                placeholder.includes('search')) score += 20;
            if (rect.width > 200) score += 10;
            score -= rect.top / 100;

            if (score > bestScore) {
                bestScore = score;
                best = {
                    tag: el.tagName.toLowerCase(),
                    type: el.type || '',
                    placeholder: el.placeholder || '',
                    aria_label: el.getAttribute('aria-label') || '',
                    bounding_box: {
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        width: Math.round(rect.width), height: Math.round(rect.height)
                    },
                    score: Math.round(score)
                };
            }
        }
        return best;
    }
    """

    async def focus_textbox(self, hint: str = "") -> Dict[str, Any]:
        """Find the most relevant visible text input and focus it."""
        try:
            result = await self._page.evaluate(self._FIND_TEXTBOX_JS, hint)
            if not result:
                return {"success": False, "error": "No visible text input found on page.",
                        "state": await self.get_state()}

            bb = result["bounding_box"]
            cx = bb["x"] + bb["width"] // 2
            cy = bb["y"] + bb["height"] // 2
            await self._page.mouse.click(cx, cy)
            await asyncio.sleep(0.2)

            logger.info(f"focus_textbox -> <{result['tag']}> "
                        f"placeholder='{result.get('placeholder', '')[:30]}' at ({cx},{cy})")
            return {"success": True, "focused": result, "state": await self.get_state()}
        except Exception as e:
            return {"success": False, "error": str(e), "state": await self.get_state()}

    async def type_text(self, text: str, mode: str = "append") -> Dict[str, Any]:
        """Type text into the currently focused element.
        mode='replace' selects all first; mode='append' types at cursor.
        """
        try:
            if mode == "replace":
                await self._page.keyboard.press("Control+a")
                await asyncio.sleep(0.1)

            await self._page.keyboard.type(text, delay=35)

            logger.info(f"type_text ok: '{text[:40]}...' (mode={mode})")
            return {"success": True, "typed": text[:80], "mode": mode,
                    "state": await self.get_state()}
        except Exception as e:
            return {"success": False, "error": str(e), "state": await self.get_state()}

    _KEY_MAP = {
        "ctrl+l": "Control+l", "ctrl+a": "Control+a",
        "ctrl+c": "Control+c", "ctrl+v": "Control+v",
        "ctrl+t": "Control+t", "ctrl+w": "Control+w",
        "ctrl+shift+t": "Control+Shift+t",
        "ctrl+enter": "Control+Enter",
        "enter": "Enter", "tab": "Tab", "escape": "Escape",
        "backspace": "Backspace", "delete": "Delete",
        "arrowup": "ArrowUp", "arrowdown": "ArrowDown",
        "arrowleft": "ArrowLeft", "arrowright": "ArrowRight",
        "space": " ", "home": "Home", "end": "End",
        "pageup": "PageUp", "pagedown": "PageDown",
    }

    async def press_keys(self, keys: str) -> Dict[str, Any]:
        """Send keyboard key presses (Enter, Tab, Ctrl+L, etc.)."""
        try:
            normalized = self._KEY_MAP.get(keys.lower().strip(), keys)
            await self._page.keyboard.press(normalized)
            await asyncio.sleep(0.2)

            logger.info(f"press_keys ok: '{normalized}'")
            return {"success": True, "keys": normalized, "state": await self.get_state()}
        except Exception as e:
            return {"success": False, "error": str(e), "state": await self.get_state()}

    async def wait_for_text(self, text: str, timeout_ms: int = 5000) -> Dict[str, Any]:
        """Wait until the specified text appears visibly on the page."""
        try:
            deadline = asyncio.get_event_loop().time() + timeout_ms / 1000
            while asyncio.get_event_loop().time() < deadline:
                found = await self._page.evaluate(
                    "(t) => document.body && document.body.innerText.includes(t)", text
                )
                if found:
                    logger.info(f"wait_for_text '{text[:30]}' found")
                    return {"success": True, "found": True, "state": await self.get_state()}
                await asyncio.sleep(0.3)

            logger.info(f"wait_for_text '{text[:30]}' timed out after {timeout_ms}ms")
            return {"success": True, "found": False, "timed_out": True,
                    "state": await self.get_state()}
        except Exception as e:
            return {"success": False, "error": str(e), "found": False}

    async def get_active_state(self) -> Dict[str, Any]:
        """Return comprehensive state of the active tab."""
        try:
            if not self._connected or not self._page:
                return {"success": False, "error": "Not connected."}

            page_info = await self._page.evaluate("""
            () => ({
                ready_state: document.readyState,
                viewport: { width: window.innerWidth, height: window.innerHeight },
                scroll_y: window.scrollY,
                scroll_height: document.body ? document.body.scrollHeight : 0
            })
            """)

            active_idx = -1
            if self._context:
                for i, p in enumerate(self._context.pages):
                    if p == self._page:
                        active_idx = i
                        break

            return {
                "success": True,
                "active_tab_index": active_idx,
                "url": self._page.url,
                "title": await self._page.title(),
                "is_loading": page_info["ready_state"] != "complete",
                "viewport": page_info["viewport"],
                "scroll_y": page_info["scroll_y"],
                "scroll_height": page_info["scroll_height"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # -- frame capture -------------------------------------------------------

    async def _capture_frame(self) -> Dict[str, Any]:
        """Capture a screenshot frame with metadata. Throttled to max 2 FPS."""
        now = time.time()
        if now - self._last_frame_time < 0.5:
            return {}
        try:
            buf = await asyncio.wait_for(
                self._page.screenshot(type="png", full_page=False),
                timeout=5.0
            )
            b64 = base64.b64encode(buf).decode("ascii")
            tab_idx = -1
            if self._context:
                for i, p in enumerate(self._context.pages):
                    if p == self._page:
                        tab_idx = i
                        break
            frame = {
                "timestamp": now,
                "tab_index": tab_idx,
                "title": await self._page.title(),
                "url": self._page.url,
                "screenshot_b64": b64,
            }
            self._frame_cache.append(frame)
            self._last_frame_time = now
            return frame
        except (asyncio.TimeoutError, asyncio.CancelledError):
            logger.debug("_capture_frame: screenshot timed out or cancelled (shutdown?)")
            return {}
        except Exception:
            return {}

    # -- close_tab -----------------------------------------------------------

    async def close_tab(self, index: int = None) -> Dict[str, Any]:
        """Close a tab by index or the active tab. Prevents closing the last tab."""
        try:
            if not self._context:
                return {"success": False, "error": "No browser context."}
            pages = list(self._context.pages)
            if len(pages) <= 1:
                return {"success": False, "error": "Cannot close last remaining tab."}

            if index is not None:
                if index < 0 or index >= len(pages):
                    return {"success": False,
                            "error": f"Tab index {index} out of range (0-{len(pages)-1})."}
                target = pages[index]
            else:
                target = self._page

            self._lumina_pages.discard(target)
            was_active = (target == self._page)
            await target.close()

            if was_active:
                remaining = list(self._context.pages)
                if remaining:
                    self._page = remaining[-1]
                    await self._page.bring_to_front()

            remaining_count = len(list(self._context.pages))
            logger.info(f"close_tab: closed tab{' (active)' if was_active else ''}, "
                        f"{remaining_count} remaining")
            return {"success": True, "remaining_tabs": remaining_count,
                    "state": await self.get_state()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # -- click_best ----------------------------------------------------------

    async def click_best(self, query: str, prefer: List[str] = None,
                         area: str = None) -> Dict[str, Any]:
        """Click the best matching element with strict scoring (>=85) and filtering."""
        try:
            items = await self._page.evaluate(self._GET_CLICKABLES_JS)
            if not items:
                return {"success": False, "error": "No clickable elements found.",
                        "state": await self.get_state()}

            target = _normalize_text(query)
            prefer_tags = [t.lower() for t in (prefer or ["button", "a", "input"])]

            vh = await self._page.evaluate("() => window.innerHeight")

            def _score_best(item):
                candidates = [
                    _normalize_text(item.get("text", "") or ""),
                    _normalize_text(item.get("aria_label", "") or ""),
                ]
                best = 0
                for c in candidates:
                    if not c:
                        continue
                    if target == c:
                        best = max(best, 100)
                    elif c.startswith(target) or target.startswith(c):
                        overlap = min(len(target), len(c))
                        best = max(best, 50 + int(45 * overlap / max(len(target), len(c))))
                    elif target in c or c in target:
                        overlap = len(target) if target in c else len(c)
                        best = max(best, 40 + int(45 * overlap / max(len(target), len(c))))
                    else:
                        t_words = set(target.split())
                        c_words = set(c.split())
                        common = t_words & c_words
                        if common:
                            best = max(best, int(60 * len(common) / len(t_words)))
                tag = item.get("tag", "")
                for idx, ptag in enumerate(prefer_tags):
                    if tag == ptag:
                        best = min(100, best + 5 - idx)
                        break
                if item.get("role") == "button" and "button" not in prefer_tags:
                    best = min(100, best + 1)
                return best

            filtered = items
            if area:
                third = vh / 3
                if area == "top":
                    filtered = [i for i in items if i["bounding_box"]["y"] < third]
                elif area == "center":
                    filtered = [i for i in items
                                if third <= i["bounding_box"]["y"] < 2 * third]
                elif area == "bottom":
                    filtered = [i for i in items if i["bounding_box"]["y"] >= 2 * third]
            if not filtered:
                filtered = items

            scored = [(item, _score_best(item)) for item in filtered]
            scored.sort(key=lambda x: -x[1])

            best_item, best_score = scored[0]
            if best_score < 85:
                top3 = [{"text": s[0].get("text", "")[:60], "score": s[1]}
                        for s in scored[:3]]
                return {"success": False,
                        "error": f"No element scored >=85 for '{query}' (best={best_score}).",
                        "closest": top3, "state": await self.get_state()}

            bb = best_item["bounding_box"]
            cx = bb["x"] + bb["width"] // 2
            cy = bb["y"] + bb["height"] // 2
            await self._page.mouse.click(cx, cy)
            await asyncio.sleep(0.4)

            logger.info(f"click_best '{query}' -> '{best_item.get('text','')[:40]}' "
                        f"(score={best_score}, tag={best_item['tag']}) at ({cx},{cy})")

            return {"success": True, "clicked": True,
                    "text": best_item.get("text", "")[:80],
                    "tag": best_item["tag"],
                    "score": best_score,
                    "bbox": [bb["x"], bb["y"], bb["width"], bb["height"]],
                    "state": await self.get_state()}

        except Exception as e:
            return {"success": False, "error": str(e), "state": await self.get_state()}

    # -- analyze_screen ------------------------------------------------------

    _ANALYZE_SCREEN_JS = """
    () => {
        const result = {
            clickables: [], inputs: [], headings: [], errors: [],
            focused_element: null
        };

        const interactive = document.querySelectorAll(
            'a, button, [role="button"], [role="link"], [role="menuitem"], '
            + '[onclick], input[type="submit"], input[type="button"]'
        );
        for (const el of interactive) {
            const rect = el.getBoundingClientRect();
            if (rect.width < 5 || rect.height < 5) continue;
            if (rect.bottom < 0 || rect.top > window.innerHeight) continue;
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') continue;
            result.clickables.push({
                text: (el.innerText || '').trim().substring(0, 80),
                tag: el.tagName.toLowerCase(),
                bbox: [Math.round(rect.x), Math.round(rect.y),
                       Math.round(rect.width), Math.round(rect.height)]
            });
            if (result.clickables.length >= 50) break;
        }

        const fields = document.querySelectorAll(
            'input[type="text"], input[type="search"], input[type="email"], '
            + 'input[type="password"], input:not([type]), textarea, '
            + '[contenteditable="true"], [role="textbox"]'
        );
        for (const el of fields) {
            const rect = el.getBoundingClientRect();
            if (rect.width < 5 || rect.height < 5) continue;
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') continue;
            result.inputs.push({
                placeholder: el.placeholder || '',
                type: el.type || 'text',
                bbox: [Math.round(rect.x), Math.round(rect.y),
                       Math.round(rect.width), Math.round(rect.height)]
            });
        }

        for (const h of document.querySelectorAll('h1, h2, h3')) {
            const t = (h.innerText || '').trim();
            if (t) result.headings.push(t.substring(0, 100));
        }

        const errSel = '[class*="error"], [class*="alert"], [role="alert"]';
        for (const el of document.querySelectorAll(errSel)) {
            const t = (el.innerText || '').trim();
            if (t && t.length < 200) result.errors.push(t);
        }

        const focused = document.activeElement;
        if (focused && focused !== document.body) {
            const rect = focused.getBoundingClientRect();
            result.focused_element = {
                tag: focused.tagName.toLowerCase(),
                type: focused.type || '',
                placeholder: focused.placeholder || '',
                bbox: [Math.round(rect.x), Math.round(rect.y),
                       Math.round(rect.width), Math.round(rect.height)]
            };
        }

        return result;
    }
    """

    # Blank/newtab URL patterns — analyzing these is meaningless
    _BLANK_URLS = frozenset({
        "about:blank", "chrome://newtab/", "brave://newtab/",
        "edge://newtab/", "chrome-error://chromewebdata/",
    })

    async def analyze_screen(self) -> Dict[str, Any]:
        """Return structured DOM state: clickables, inputs, headings, errors, focused_element.

        Guards:
        - Returns a clean failure if the active page is a blank tab or new-tab page.
          This prevents fake success after an unwanted browser relaunch.
        - Never triggers Brave restart (analyze_screen is NOT in _INTERACTION_ACTIONS).
        """
        try:
            current_url = self._page.url
            # Guard: refuse to analyze blank/newtab pages — those are meaningless
            if current_url in self._BLANK_URLS or not current_url.startswith("http"):
                logger.warning(f"analyze_screen: refusing to analyze blank/newtab page ({current_url})")
                return {
                    "success": False,
                    "error": (
                        f"Cannot analyze browser screen: the active tab shows a blank or new-tab page "
                        f"({current_url}). No meaningful content to inspect. "
                        "Please navigate to a real webpage first."
                    ),
                    "clickables": [], "inputs": [], "headings": [],
                    "errors": [], "focused_element": None,
                }

            data = await asyncio.wait_for(
                self._page.evaluate(self._ANALYZE_SCREEN_JS),
                timeout=8.0
            )
            state = await self.get_state()

            # Secondary guard: if the page returned zero content AND body text is tiny,
            # it may be a white/broken page that rendered after a bad relaunch.
            if (not data.get("clickables") and not data.get("headings")
                    and not data.get("inputs")):
                health = await self._check_page_health()
                if health.get("text_length", 0) < 50:
                    logger.warning("analyze_screen: page appears blank/empty after DOM scan")
                    return {
                        "success": False,
                        "error": (
                            "analyze_screen: the current browser tab appears empty or not fully loaded. "
                            f"URL: {current_url} — no clickables, headings, or inputs found. "
                            "Try navigating to the page you want to analyze first."
                        ),
                        "clickables": [], "inputs": [], "headings": [],
                        "errors": [], "focused_element": None,
                        "state": state,
                    }

            logger.info(f"analyze_screen: {len(data.get('clickables',[]))} clickables, "
                        f"{len(data.get('inputs',[]))} inputs, "
                        f"{len(data.get('headings',[]))} headings")
            return {"success": True, **data, "state": state}
        except asyncio.TimeoutError:
            logger.warning("analyze_screen timed out after 8s — page may be frozen or too complex")
            return {"success": False, "error": "analyze_screen timed out (8s)",
                    "clickables": [], "inputs": [], "headings": [],
                    "errors": [], "focused_element": None}
        except Exception as e:
            return {"success": False, "error": str(e),
                    "clickables": [], "inputs": [], "headings": [],
                    "errors": [], "focused_element": None}


    # -- DOM intelligence ----------------------------------------------------

    _GET_CLICKABLES_JS = """
    () => {
        const MAX = 100;
        const MIN_SIZE = 10;
        const results = [];
        const seen = new Set();

        const INTERACTIVE = 'a, button, [role="button"], [role="link"], [role="menuitem"], '
            + '[role="tab"], [role="option"], [onclick], [tabindex], input[type="submit"], '
            + 'input[type="button"], summary, label[for], [contenteditable="true"]';

        for (const el of document.querySelectorAll(INTERACTIVE)) {
            if (results.length >= MAX) break;

            // visibility checks
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden' ||
                parseFloat(style.opacity) < 0.1) continue;
            if (el.disabled) continue;

            const rect = el.getBoundingClientRect();
            if (rect.width < MIN_SIZE || rect.height < MIN_SIZE) continue;
            // must be within viewport
            if (rect.bottom < 0 || rect.top > window.innerHeight ||
                rect.right < 0 || rect.left > window.innerWidth) continue;

            const text = (el.innerText || '').trim().substring(0, 120);
            const aria = el.getAttribute('aria-label') || '';
            const role = el.getAttribute('role') || '';
            const tag = el.tagName.toLowerCase();

            // de-duplicate by position + text
            const key = `${Math.round(rect.x)},${Math.round(rect.y)},${text.substring(0,30)}`;
            if (seen.has(key)) continue;
            seen.add(key);

            // confidence heuristic
            let confidence = 0.5;
            if (tag === 'button' || tag === 'a') confidence += 0.2;
            if (role === 'button' || role === 'link') confidence += 0.15;
            if (text.length > 0) confidence += 0.1;
            if (aria.length > 0) confidence += 0.05;
            confidence = Math.min(confidence, 1.0);

            results.push({
                text: text,
                aria_label: aria,
                role: role,
                tag: tag,
                bounding_box: {
                    x: Math.round(rect.x),
                    y: Math.round(rect.y),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height)
                },
                confidence: Math.round(confidence * 100) / 100
            });
        }
        // Sort by confidence descending
        results.sort((a, b) => b.confidence - a.confidence);
        return results;
    }
    """

    async def get_clickables(self) -> Dict[str, Any]:
        """Return all visible interactive elements on the page."""
        try:
            items = await self._page.evaluate(self._GET_CLICKABLES_JS)
            logger.info(f"get_clickables: found {len(items)} elements")
            return {"success": True, "clickables": items, "state": await self.get_state()}
        except Exception as e:
            return {"success": False, "error": str(e), "clickables": []}

    async def click_text(self, text: str) -> Dict[str, Any]:
        """Fuzzy-match visible text/aria_label and click the best candidate."""
        try:
            items = await self._page.evaluate(self._GET_CLICKABLES_JS)
            if not items:
                return {"success": False, "error": "No clickable elements found on page.",
                        "state": await self.get_state()}

            target = _normalize_text(text)

            def _score(item):
                """Score 0-100 for how well this item matches the target text."""
                candidates = [
                    _normalize_text(item.get("text", "") or ""),
                    _normalize_text(item.get("aria_label", "") or ""),
                    _normalize_text(item.get("role", "") or ""),
                ]
                best = 0
                for c in candidates:
                    if not c:
                        continue
                    if target == c:
                        best = max(best, 100)
                    elif c.startswith(target) or target.startswith(c):
                        overlap = min(len(target), len(c))
                        best = max(best, 50 + int(45 * overlap / max(len(target), len(c))))
                    elif target in c or c in target:
                        overlap = len(target) if target in c else len(c)
                        best = max(best, 40 + int(45 * overlap / max(len(target), len(c))))
                    else:
                        t_words = set(target.split())
                        c_words = set(c.split())
                        common = t_words & c_words
                        if common:
                            best = max(best, int(60 * len(common) / len(t_words)))
                tag = item.get("tag", "")
                if tag == "button":
                    best = min(100, best + 5)
                elif tag == "a":
                    best = min(100, best + 3)
                elif tag == "input":
                    best = min(100, best + 2)
                elif item.get("role") == "button":
                    best = min(100, best + 1)
                return best

            scored = [(item, _score(item)) for item in items]
            scored.sort(key=lambda x: -x[1])

            best_item, best_score = scored[0]
            if best_score < 15:
                # No reasonable match
                top3 = [{"text": s[0].get("text","")[:60],
                          "aria_label": s[0].get("aria_label","")[:60],
                          "score": s[1]} for s in scored[:3]]
                return {"success": False,
                        "error": f"No element matched '{text}' (best score {best_score}/100).",
                        "closest": top3, "state": await self.get_state()}

            # Click center of bounding box
            bb = best_item["bounding_box"]
            cx = bb["x"] + bb["width"] // 2
            cy = bb["y"] + bb["height"] // 2

            await self._page.mouse.click(cx, cy)
            await asyncio.sleep(0.4)

            logger.info(f"click_text '{text}' -> matched '{best_item.get('text','')[:40]}' "
                        f"(score={best_score}, tag={best_item['tag']}) at ({cx},{cy})")

            return {"success": True,
                    "matched": {"text": best_item.get("text","")[:80],
                                "aria_label": best_item.get("aria_label",""),
                                "tag": best_item["tag"],
                                "score": best_score,
                                "clicked_at": {"x": cx, "y": cy}},
                    "state": await self.get_state()}

        except Exception as e:
            return {"success": False, "error": str(e), "state": await self.get_state()}

    # -- tab management ------------------------------------------------------

    async def list_tabs(self) -> Dict[str, Any]:
        """Return info about all open tabs."""
        try:
            if not self._context:
                return {"success": False, "error": "No browser context.", "tabs": []}
            tabs = []
            pages = self._context.pages
            for i, page in enumerate(pages):
                try:
                    title = await page.title()
                except Exception:
                    title = "(unresponsive)"
                tabs.append({
                    "index": i,
                    "title": title,
                    "url": page.url,
                    "active": page == self._page,
                })
            logger.info(f"list_tabs: {len(tabs)} tabs")
            return {"success": True, "tabs": tabs}
        except Exception as e:
            return {"success": False, "error": str(e), "tabs": []}

    async def switch_tab(self, index: int) -> Dict[str, Any]:
        """Switch the active tab by index."""
        try:
            if not self._context:
                return {"success": False, "error": "No browser context."}
            pages = self._context.pages
            if index < 0 or index >= len(pages):
                return {"success": False,
                        "error": f"Tab index {index} out of range (0-{len(pages)-1})."}
            self._page = pages[index]
            await self._page.bring_to_front()
            state = await self.get_state()
            logger.info(f"switch_tab -> [{index}] {state.get('title','')}")
            return {"success": True, "state": state}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # -- screenshot ----------------------------------------------------------

    async def screenshot(self) -> Dict[str, Any]:
        """Take a screenshot of the active tab, return as base64 PNG."""
        try:
            buf = await self._page.screenshot(type="png", full_page=False)
            b64 = base64.b64encode(buf).decode("ascii")
            logger.info(f"screenshot ok ({len(buf)} bytes)")
            return {"success": True, "screenshot_b64": b64, "state": await self.get_state()}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_controller: Optional[LocalBrowserController] = None


def get_local_browser_controller() -> LocalBrowserController:
    global _controller
    if _controller is None:
        _controller = LocalBrowserController()
    return _controller


# ---------------------------------------------------------------------------
# Public entrypoint (called from lumina.py dispatcher)
# ---------------------------------------------------------------------------

async def execute_local_browser(action: str, params: Dict[str, Any],
                                context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a local browser action.

    Args:
        action:  one of the supported action names
        params:  action-specific parameters
        context: must contain {"tool_permissions": {...}}

    Returns:
        {"ok": bool, "message": str, "data": {...}}
    """
    # -- block permanently disallowed actions ----------------------------------
    if action in _ALWAYS_BLOCKED:
        msg = f"Action '{action}' is permanently blocked. Use manual control."
        logger.warning(f"[TOOL] action={action} gated=blocked mode=n/a reason=always_blocked")
        return {"ok": False, "message": msg, "data": {}}

    # -- confirmation gating (mode-aware) ------------------------------------
    mode = context.get("confirmation_mode", "relaxed")
    should_confirm, reason = _needs_confirmation(action, params, mode)
    logger.info(f"[TOOL] action={action} gated={'yes' if should_confirm else 'no'} "
                f"mode={mode} reason={reason}")

    if should_confirm and not context.get("confirmed"):
        detail = params.get("text", params.get("query", params.get("keys", "")))
        detail = str(detail or "")[:100]
        msg = (f"Action '{action}' requires confirmation (mode={mode}, reason={reason}). "
               f"Details: {detail!r}")
        return {"ok": False, "needs_confirmation": True, "message": msg,
                "data": {"action": action, "params": params}}

    ctrl = get_local_browser_controller()

    # -- ensure connection ---------------------------------------------------
    conn = await ctrl.ensure_connected(action)
    if not conn["success"]:
        return {"ok": False, "message": conn["error"], "data": {}}

    # -- dispatch action -----------------------------------------------------
    try:
        # Frame capture: before action
        await ctrl._capture_frame()

        if action == "open_url":
            url = params.get("url", "")
            if not url:
                return {"ok": False, "message": "Missing 'url' parameter.", "data": {}}
            await ctrl._ensure_lumina_tab()
            result = await ctrl.open_url(url)

        elif action == "play_pause":
            result = await ctrl.play_pause()

        elif action == "click_selector":
            selector = params.get("selector", "")
            if not selector:
                return {"ok": False, "message": "Missing 'selector' parameter.", "data": {}}
            result = await ctrl.click_selector(selector)

        elif action == "click_at":
            x = int(params.get("x", 0))
            y = int(params.get("y", 0))
            result = await ctrl.click_at(x, y)

        elif action == "scroll":
            direction = params.get("direction", None)
            amount = params.get("amount", None)
            if direction:
                px = int(amount) if amount else 500
                delta = -abs(px) if direction == "up" else abs(px)
            else:
                delta = int(params.get("delta_y", params.get("deltaY", 300)))
            result = await ctrl.scroll(delta)

        elif action == "go_back":
            result = await ctrl.go_back()

        elif action == "go_forward":
            result = await ctrl.go_forward()

        elif action == "reload":
            result = await ctrl.reload()

        elif action == "get_state":
            state = await ctrl.get_state()
            result = {"success": True, "state": state}

        elif action == "get_clickables":
            result = await ctrl.get_clickables()
            # Return clickables list in data for the LLM
            clickables = result.get("clickables", [])
            state = result.get("state", {})
            ok = result.get("success", False)
            summary = f"Found {len(clickables)} clickable elements."
            if clickables:
                top5 = [f"  [{i}] <{c['tag']}> \"{c['text'][:50]}\" "
                        f"(aria=\"{c['aria_label'][:30]}\", conf={c['confidence']})"
                        for i, c in enumerate(clickables[:10])]
                summary += "\nTop elements:\n" + "\n".join(top5)
            return {"ok": ok, "message": summary,
                    "data": {**state, "clickables": clickables}}

        elif action == "click_text":
            text_target = params.get("text", "")
            if not text_target:
                return {"ok": False, "message": "Missing 'text' parameter.", "data": {}}
            for _attempt in range(_MAX_RETRIES + 1):
                result = await ctrl.click_text(text_target)
                if result.get("success") or _attempt >= _MAX_RETRIES:
                    break
                logger.info(f"[TOOL] Retry {_attempt+1}/{_MAX_RETRIES} for click_text")
                await asyncio.sleep(0.3)
            # Build rich response
            ok = result.get("success", False)
            state = result.get("state", {})
            matched = result.get("matched", {})
            error = result.get("error", "")
            closest = result.get("closest", [])
            if ok:
                msg = (f"Clicked '{matched.get('text','')[:60]}' "
                       f"(tag={matched.get('tag','')}, score={matched.get('score',0)}) "
                       f"at ({matched.get('clicked_at',{}).get('x',0)},{matched.get('clicked_at',{}).get('y',0)})")
            else:
                msg = f"click_text failed: {error}"
                if closest:
                    msg += "\nClosest candidates: " + "; ".join(
                        f"\"{c['text'][:40]}\" (score={c['score']})" for c in closest)
            return {"ok": ok, "message": msg,
                    "data": {**state, "matched": matched, "closest": closest}}

        elif action == "list_tabs":
            result = await ctrl.list_tabs()
            tabs = result.get("tabs", [])
            ok = result.get("success", False)
            lines = [f"  [{t['index']}] {'*' if t['active'] else ' '} {t['title'][:60]} — {t['url'][:80]}"
                     for t in tabs]
            msg = f"{len(tabs)} tabs open:\n" + "\n".join(lines)
            return {"ok": ok, "message": msg, "data": {"tabs": tabs}}

        elif action == "switch_tab":
            idx = int(params.get("index", 0))
            result = await ctrl.switch_tab(idx)
            ok = result.get("success", False)
            state = result.get("state", {})
            error = result.get("error", "")
            msg = f"Switched to tab [{idx}]" if ok else f"switch_tab failed: {error}"
            if state.get("title"):
                msg += f" — {state['title']}"
            return {"ok": ok, "message": msg, "data": state}

        elif action == "screenshot":
            result = await ctrl.screenshot()
            ok = result.get("success", False)
            state = result.get("state", {})
            b64 = result.get("screenshot_b64", "")
            error = result.get("error", "")
            msg = f"Screenshot captured ({len(b64)} chars base64)" if ok else f"screenshot failed: {error}"
            return {"ok": ok, "message": msg,
                    "data": {**state, "screenshot_b64": b64[:100] + "..." if len(b64) > 100 else b64}}

        elif action == "new_tab":
            url = params.get("url", None)
            result = await ctrl.new_tab(url)
            ok = result.get("success", False)
            state = result.get("state", {})
            tab_idx = result.get("tab_index", -1)
            error = result.get("error", "")
            msg = f"New tab [{tab_idx}] opened" if ok else f"new_tab failed: {error}"
            if state.get("url"):
                msg += f" \u2014 {state['url']}"
            if ok and url:
                health = await ctrl._check_page_health()
                if health.get("is_blank"):
                    recovery = await ctrl._recover_page()
                    state = await ctrl.get_state()
            return {"ok": ok, "message": msg, "data": {**state, "tab_index": tab_idx}}

        elif action == "focus_textbox":
            hint = params.get("hint", params.get("text", ""))
            for _attempt in range(_MAX_RETRIES + 1):
                result = await ctrl.focus_textbox(hint)
                if result.get("success") or _attempt >= _MAX_RETRIES:
                    break
                logger.info(f"[TOOL] Retry {_attempt+1}/{_MAX_RETRIES} for focus_textbox")
                await asyncio.sleep(0.3)
            ok = result.get("success", False)
            state = result.get("state", {})
            focused = result.get("focused", {})
            error = result.get("error", "")
            if ok:
                bb = focused.get("bounding_box", {})
                msg = (f"Focused <{focused.get('tag','')}> "
                       f"placeholder='{focused.get('placeholder','')[:40]}' "
                       f"at ({bb.get('x',0)},{bb.get('y',0)})")
            else:
                msg = f"focus_textbox failed: {error}"
            return {"ok": ok, "message": msg, "data": {**state, "focused": focused}}

        elif action == "type_text":
            text_val = params.get("text", "")
            mode = params.get("mode", "append")
            if not text_val:
                return {"ok": False, "message": "Missing 'text' parameter.", "data": {}}
            result = await ctrl.type_text(text_val, mode)
            ok = result.get("success", False)
            state = result.get("state", {})
            error = result.get("error", "")
            msg = f"Typed '{text_val[:40]}' (mode={mode})" if ok else f"type_text failed: {error}"
            return {"ok": ok, "message": msg, "data": state}

        elif action == "press_keys":
            keys = params.get("keys", "")
            if not keys:
                return {"ok": False, "message": "Missing 'keys' parameter.", "data": {}}
            result = await ctrl.press_keys(keys)
            ok = result.get("success", False)
            state = result.get("state", {})
            error = result.get("error", "")
            msg = f"Pressed '{keys}'" if ok else f"press_keys failed: {error}"
            return {"ok": ok, "message": msg, "data": state}

        elif action == "wait_for_text":
            text_val = params.get("text", "")
            timeout = int(params.get("timeout_ms", 5000))
            if not text_val:
                return {"ok": False, "message": "Missing 'text' parameter.", "data": {}}
            result = await ctrl.wait_for_text(text_val, timeout)
            ok = result.get("success", False)
            found = result.get("found", False)
            timed_out = result.get("timed_out", False)
            state = result.get("state", {})
            if found:
                msg = f"Text '{text_val[:40]}' found on page"
            elif timed_out:
                msg = f"Text '{text_val[:40]}' not found after {timeout}ms"
            else:
                msg = f"wait_for_text failed: {result.get('error', '')}"
            return {"ok": ok, "message": msg,
                    "data": {**state, "found": found, "timed_out": timed_out}}

        elif action == "get_active_state":
            result = await ctrl.get_active_state()
            ok = result.get("success", False)
            error = result.get("error", "")
            if ok:
                msg = (f"Tab [{result['active_tab_index']}] "
                       f"{'loading' if result['is_loading'] else 'ready'} "
                       f"\u2014 {result.get('title', '')[:50]} "
                       f"({result.get('viewport', {}).get('width', 0)}x"
                       f"{result.get('viewport', {}).get('height', 0)})")
            else:
                msg = f"get_active_state failed: {error}"
            return {"ok": ok, "message": msg, "data": result}

        elif action == "click_best":
            query = params.get("query", "")
            if not query:
                return {"ok": False, "message": "Missing 'query' parameter.", "data": {}}
            prefer = params.get("prefer", ["button", "a", "input"])
            area = params.get("area", None)
            for _attempt in range(_MAX_RETRIES + 1):
                result = await ctrl.click_best(query, prefer, area)
                if result.get("success") or _attempt >= _MAX_RETRIES:
                    break
                logger.info(f"[TOOL] Retry {_attempt+1}/{_MAX_RETRIES} for click_best")
                await asyncio.sleep(0.3)
            ok = result.get("success", False)
            state = result.get("state", {})
            error = result.get("error", "")
            if ok:
                msg = (f"Clicked '{result.get('text','')[:50]}' "
                       f"(tag={result.get('tag','')}, score={result.get('score',0)})")
            else:
                msg = f"click_best failed: {error}"
                closest = result.get("closest", [])
                if closest:
                    msg += "\nClosest: " + "; ".join(
                        f"'{c['text'][:30]}' ({c['score']})" for c in closest)
            return {"ok": ok, "message": msg,
                    "data": {**state, "clicked": result.get("clicked", False),
                             "text": result.get("text", ""),
                             "tag": result.get("tag", ""),
                             "score": result.get("score", 0),
                             "bbox": result.get("bbox", [])}}

        elif action == "close_tab":
            idx = params.get("index", None)
            if idx is not None:
                idx = int(idx)
            result = await ctrl.close_tab(idx)
            ok = result.get("success", False)
            state = result.get("state", {})
            error = result.get("error", "")
            remaining = result.get("remaining_tabs", 0)
            msg = f"Tab closed, {remaining} remaining" if ok else f"close_tab failed: {error}"
            return {"ok": ok, "message": msg,
                    "data": {**state, "remaining_tabs": remaining}}

        elif action == "analyze_screen":
            result = await ctrl.analyze_screen()
            ok = result.get("success", False)
            error = result.get("error", "")
            state = result.get("state", {})
            data = {
                "clickables": result.get("clickables", []),
                "inputs": result.get("inputs", []),
                "headings": result.get("headings", []),
                "errors": result.get("errors", []),
                "focused_element": result.get("focused_element"),
            }
            cl_count = len(data["clickables"])
            in_count = len(data["inputs"])
            msg = (f"Screen analysis: {cl_count} clickables, {in_count} inputs"
                   if ok else f"analyze_screen failed: {error}")
            return {"ok": ok, "message": msg, "data": {**state, **data}}

        else:
            return {"ok": False, "message": f"Unknown action: '{action}'", "data": {}}

        # Frame capture: after action
        await ctrl._capture_frame()

        # -- post-navigation health check --------------------------------------
        if action in ("open_url", "reload", "go_back", "go_forward") and result.get("success"):
            health = await ctrl._check_page_health()
            if health.get("is_blank"):
                recovery = await ctrl._recover_page()
                result["state"] = await ctrl.get_state()
                result["recovery"] = recovery

        # -- build response --------------------------------------------------
        ok = result.get("success", False)
        state = result.get("state", {})
        media = result.get("media", {})
        error = result.get("error", "")

        msg = f"Action '{action}' {'succeeded' if ok else 'failed'}."
        if state.get("url"):
            msg += f" URL: {state['url']}"
        if state.get("title"):
            msg += f" Title: {state['title']}"
        if media:
            msg += f" Media: {media}"
        if error:
            msg += f" Error: {error}"

        return {"ok": ok, "message": msg, "data": {**state, "media": media}}

    except Exception as e:
        logger.error(f"execute_local_browser error: {e}")
        return {"ok": False, "message": f"Internal error: {e}", "data": {}}
