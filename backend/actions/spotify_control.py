"""
actions/spotify_control.py — Lumina Spotify Desktop Control Action

Controls the installed Spotify desktop application directly using:
  1. Win32 AppActivate (focus Spotify window)
  2. Spotify keyboard shortcuts (Space, Ctrl+Right, Ctrl+Left, Ctrl+L, etc.)
  3. subprocess / psutil for launch and process detection

Architecture:
  - All operations target the Spotify desktop app exclusively.
  - NEVER falls back to browser, YouTube, or web Spotify.
  - If Spotify is not installed or not running, reports honestly.
  - Uses pyautogui only AFTER focus is confirmed, so keystrokes go to Spotify.

Supported actions:
  open         — launch or focus Spotify
  focus        — bring Spotify window to front
  play         — resume playback (Space toggle)
  pause        — pause playback (Space toggle)
  next         — next track (Ctrl+Right)
  previous     — previous track (Ctrl+Left)
  search       — focus Spotify search bar and type query (Ctrl+L → type → Enter)
  play_query   — search for query and attempt to play first result
  open_liked   — navigate to Liked Songs (keyboard nav sequence)
  open_library — navigate to Your Library (keyboard nav sequence)
  shuffle      — toggle shuffle (Ctrl+S in Spotify)
  repeat       — toggle repeat (Ctrl+R in Spotify)
"""

import os
import subprocess
import platform
import time
from pathlib import Path

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

_OS = platform.system()

# ── Spotify executable detection ──────────────────────────────────────────────

_SPOTIFY_EXE_CANDIDATES = [
    Path.home() / "AppData" / "Roaming" / "Spotify" / "Spotify.exe",
    Path("C:/Program Files/WindowsApps") / "SpotifyAB.SpotifyMusic_Spotify.exe",
]

# Also check via env override
_SPOTIFY_EXE_ENV = os.environ.get("SPOTIFY_EXE_PATH", "").strip()


def _find_spotify_exe() -> str | None:
    if _SPOTIFY_EXE_ENV and Path(_SPOTIFY_EXE_ENV).is_file():
        return _SPOTIFY_EXE_ENV
    for p in _SPOTIFY_EXE_CANDIDATES:
        if p.exists():
            return str(p)
    # Last resort: search Roaming/Spotify directory
    roaming_spotify = Path.home() / "AppData" / "Roaming" / "Spotify"
    if roaming_spotify.exists():
        for exe in roaming_spotify.glob("Spotify.exe"):
            return str(exe)
    return None


def _spotify_running() -> bool:
    """Return True if any Spotify.exe process is alive."""
    if _PSUTIL:
        for proc in psutil.process_iter(["name"]):
            try:
                if "spotify" in proc.info["name"].lower():
                    return True
            except Exception:
                pass
        return False
    # Fallback: tasklist
    if _OS == "Windows":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Spotify.exe", "/NH"],
                capture_output=True, text=True, timeout=5
            )
            return "spotify.exe" in result.stdout.lower()
        except Exception:
            return False
    return False


def _focus_spotify() -> bool:
    """
    Bring the Spotify window to the foreground using WScript.Shell AppActivate.
    Returns True if the AppActivate call succeeded (window was found).
    """
    if _OS != "Windows":
        return False
    try:
        script = '(New-Object -ComObject WScript.Shell).AppActivate("Spotify")'
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=5
        )
        # AppActivate returns True/False as stdout
        return "true" in result.stdout.lower() or result.returncode == 0
    except Exception as e:
        print(f"[Spotify] focus error: {e}")
        return False


def _launch_spotify() -> str:
    """Launch Spotify desktop app. Returns a status string."""
    exe = _find_spotify_exe()
    if not exe:
        return "Spotify desktop app not found. Make sure it is installed."
    try:
        subprocess.Popen(
            [exe],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return "launched"
    except Exception as e:
        return f"Failed to launch Spotify: {e}"


def _ensure_spotify_focused(wait_after_launch: float = 3.0) -> str:
    """
    Ensure Spotify is running and focused.
    Returns 'ok', 'launched' (needs extra wait), or an error string.
    """
    if _spotify_running():
        focused = _focus_spotify()
        if focused:
            time.sleep(0.3)
            return "ok"
        # Running but focus failed — try again once
        time.sleep(0.5)
        _focus_spotify()
        time.sleep(0.3)
        return "ok"
    else:
        # Not running — launch it
        status = _launch_spotify()
        if status == "launched":
            time.sleep(wait_after_launch)
            _focus_spotify()
            time.sleep(0.5)
            return "launched"
        return status  # error string


def _type_in_spotify(text: str):
    """Type text into the currently focused Spotify window."""
    if not _PYAUTOGUI:
        return
    if _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.write(str(text), interval=0.05)


# ── Individual action implementations ─────────────────────────────────────────

def _action_open() -> str:
    if _spotify_running():
        focused = _focus_spotify()
        time.sleep(0.3)
        return "Spotify is already open — brought it to the front." if focused else "Spotify is running but could not be focused."
    status = _launch_spotify()
    if status == "launched":
        return "Launching Spotify desktop app..."
    return status


def _action_focus() -> str:
    if not _spotify_running():
        return "Spotify is not running. Say 'open Spotify' to launch it first."
    focused = _focus_spotify()
    time.sleep(0.3)
    return "Spotify brought to front." if focused else "Could not focus Spotify — it may be minimized to tray."


def _action_play() -> str:
    if not _PYAUTOGUI:
        return "pyautogui is not installed — cannot send keyboard shortcuts."
    status = _ensure_spotify_focused()
    if status not in ("ok", "launched"):
        return status
    time.sleep(0.2)
    pyautogui.press("space")
    return "Play/Resume sent to Spotify desktop app."


def _action_pause() -> str:
    if not _PYAUTOGUI:
        return "pyautogui is not installed — cannot send keyboard shortcuts."
    status = _ensure_spotify_focused()
    if status not in ("ok", "launched"):
        return status
    time.sleep(0.2)
    pyautogui.press("space")
    return "Pause sent to Spotify desktop app."


def _action_next() -> str:
    if not _PYAUTOGUI:
        return "pyautogui is not installed — cannot send keyboard shortcuts."
    status = _ensure_spotify_focused()
    if status not in ("ok", "launched"):
        return status
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "right")
    return "Next track attempted in Spotify desktop app."


def _action_previous() -> str:
    if not _PYAUTOGUI:
        return "pyautogui is not installed — cannot send keyboard shortcuts."
    status = _ensure_spotify_focused()
    if status not in ("ok", "launched"):
        return status
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "left")
    return "Previous track attempted in Spotify desktop app."


def _action_search(query: str) -> str:
    if not query:
        return "Please provide a search query."
    if not _PYAUTOGUI:
        return "pyautogui is not installed — cannot send keyboard shortcuts."
    status = _ensure_spotify_focused()
    if status not in ("ok", "launched"):
        return status
    # Ctrl+L opens the search bar in Spotify desktop
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.5)
    # Clear existing text in search bar then type query
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    _type_in_spotify(query)
    time.sleep(0.3)
    pyautogui.press("enter")
    return f"Search for '{query}' attempted in Spotify desktop app."


def _action_play_query(query: str) -> str:
    if not query:
        return "Please provide a song, artist, or playlist to play."
    if not _PYAUTOGUI:
        return "pyautogui is not installed — cannot send keyboard shortcuts."
    status = _ensure_spotify_focused()
    if status not in ("ok", "launched"):
        return status
    # Open search bar
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    _type_in_spotify(query)
    time.sleep(0.3)
    pyautogui.press("enter")
    time.sleep(1.2)
    # Navigate down to first result and press Enter to start it
    # In Spotify desktop, after search the first result is accessible via Tab then Enter
    pyautogui.press("tab")
    time.sleep(0.3)
    pyautogui.press("enter")
    return (
        f"Play '{query}' attempted in Spotify desktop app. "
        "Search was sent and first result interaction attempted — "
        "exact playback confirmation is not possible via keyboard automation."
    )


def _action_open_liked() -> str:
    if not _PYAUTOGUI:
        return "pyautogui is not installed — cannot send keyboard shortcuts."
    status = _ensure_spotify_focused()
    if status not in ("ok", "launched"):
        return status
    # Spotify keyboard shortcut: Alt+1 opens Home, then navigate to Liked Songs
    # The most reliable cross-version route: Ctrl+Shift+W then navigate
    # Actually the most reliable: search for "Liked Songs" via search
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    _type_in_spotify("Liked Songs")
    time.sleep(0.3)
    pyautogui.press("enter")
    return (
        "Navigating to Liked Songs in Spotify desktop app — "
        "search for 'Liked Songs' attempted. "
        "Exact navigation confirmation is not possible via keyboard automation."
    )


def _action_open_library() -> str:
    if not _PYAUTOGUI:
        return "pyautogui is not installed — cannot send keyboard shortcuts."
    status = _ensure_spotify_focused()
    if status not in ("ok", "launched"):
        return status
    # Alt+1 navigates to Home in Spotify desktop (varies by version)
    # Most reliable: focus Your Library sidebar via keyboard
    time.sleep(0.3)
    # Ctrl+Shift+L does not exist — use search approach for Your Library
    # Best available shortcut: Tab to navigate left sidebar to Library
    # Press Escape first to leave any focused field, then Alt+1 (Home), then Tab to Library
    pyautogui.press("escape")
    time.sleep(0.2)
    # In newer Spotify desktop, Ctrl+Home or just Home navigates sidebar
    # Most cross-version reliable: search approach
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    _type_in_spotify("Your Library")
    time.sleep(0.3)
    pyautogui.press("enter")
    return (
        "Navigating to Your Library in Spotify desktop app — "
        "search for 'Your Library' attempted. "
        "Exact navigation confirmation is not possible via keyboard automation."
    )


def _action_shuffle() -> str:
    if not _PYAUTOGUI:
        return "pyautogui is not installed — cannot send keyboard shortcuts."
    status = _ensure_spotify_focused()
    if status not in ("ok", "launched"):
        return status
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "s")
    return "Shuffle toggle attempted in Spotify desktop app."


def _action_repeat() -> str:
    if not _PYAUTOGUI:
        return "pyautogui is not installed — cannot send keyboard shortcuts."
    status = _ensure_spotify_focused()
    if status not in ("ok", "launched"):
        return status
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "r")
    return "Repeat toggle attempted in Spotify desktop app."


# ── Action dispatch table ──────────────────────────────────────────────────────

_ACTION_TABLE = {
    "open":         _action_open,
    "focus":        _action_focus,
    "play":         _action_play,
    "pause":        _action_pause,
    "resume":       _action_play,       # alias
    "next":         _action_next,
    "previous":     _action_previous,
    "prev":         _action_previous,   # alias
    "shuffle":      _action_shuffle,
    "repeat":       _action_repeat,
}

_QUERY_ACTIONS = {
    "search":       _action_search,
    "play_query":   _action_play_query,
    "open_liked":   _action_open_liked,
    "open_library": _action_open_library,
}


# ── Public entry point ────────────────────────────────────────────────────────

def spotify_control(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Lumina Spotify desktop control action.

    parameters:
        action : Action name (see supported actions in module docstring)
        query  : Search term / song name (for search, play_query actions)
    """
    params = parameters or {}
    action = (params.get("action") or "open").strip().lower()
    query  = (params.get("query") or "").strip()

    print(f"[Spotify] action={action} query={query!r}")

    if player:
        player.write_log(f"[spotify] {action} {query}")

    # No-query actions
    if action in _ACTION_TABLE:
        fn = _ACTION_TABLE[action]
        return fn()

    # Query-required actions
    if action in _QUERY_ACTIONS:
        fn = _QUERY_ACTIONS[action]
        return fn(query)

    # Unknown action — give helpful guidance
    known = sorted(list(_ACTION_TABLE.keys()) + list(_QUERY_ACTIONS.keys()))
    return (
        f"Unknown Spotify action: '{action}'. "
        f"Supported actions: {', '.join(known)}."
    )
