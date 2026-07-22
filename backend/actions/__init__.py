"""
actions/__init__.py — Lumina Actions Package

Ported action capabilities from Mark-XXX. Each action follows:

    action_func(parameters: dict, response=None, player=None, session_memory=None) -> str

All successfully imported actions are registered via ActionRegistry.
The legacy ACTION_REGISTRY dict is kept as a backward-compatible view
so existing code (lumina.py tool dispatch, server.py) continues to work.

Actions whose optional dependencies are missing at import time are skipped
gracefully — they will simply be absent from the registry and Lumina will
return a helpful error if the model calls them.
"""

import sys
import os

# Ensure backend/ is on sys.path so `core.registry` resolves
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from core.registry import ActionRegistry

main_loop = None
# Socket.IO server handle, injected by server.py at startup. Lets thread-run
# action tools push events to the Electron renderer (e.g. route normal browsing
# to the embedded browser panel instead of the external dedicated Brave).
sio = None

def run_coroutine(coro):
    """Run a coroutine on the main thread event loop (threadsafe)."""
    import asyncio
    global main_loop
    if main_loop is not None:
        try:
            future = asyncio.run_coroutine_threadsafe(coro, main_loop)
            return future.result()
        except Exception as e:
            print(f"[ACTIONS] run_coroutine_threadsafe failed: {e}")
    return asyncio.run(coro)


def emit_workspace_browser(url: str) -> bool:
    """
    Ask the Electron renderer to open *url* in the embedded browser workspace.

    Thread-safe: schedules ``sio.emit('workspace_open', {...})`` onto the main
    event loop. Returns True only when the emit was dispatched (frontend bridge
    available), so callers can fall back to the external browser when the UI is
    not reachable (e.g. headless / no active socket). Never raises.
    """
    global sio, main_loop
    if sio is None or main_loop is None:
        return False
    try:
        import asyncio
        fut = asyncio.run_coroutine_threadsafe(
            sio.emit('workspace_open', {'type': 'browser', 'url': url}),
            main_loop,
        )
        fut.result(timeout=3)
        return True
    except Exception as e:
        print(f"[ACTIONS] emit_workspace_browser failed: {e}")
        return False


def _try_register(name: str, module_path: str, func_name: str) -> None:
    """Import an action function and register it, logging any import failures."""
    try:
        import importlib
        mod = importlib.import_module(module_path)
        fn  = getattr(mod, func_name)
        ActionRegistry.register_value(name, fn)
        print(f"[ACTIONS] Registered: {name}")
    except ImportError as e:
        print(f"[ACTIONS] Skipped '{name}' — missing dependency: {e}")
    except Exception as e:
        print(f"[ACTIONS] Skipped '{name}' — import error: {e}")

# ── Register each action ─────────────────────────────────────────────────────
_try_register("cmd_control",       "actions.cmd_control",       "cmd_control")
_try_register("file_controller",   "actions.file_controller",   "file_controller")
_try_register("computer_control",  "actions.computer_control",  "computer_control")
_try_register("computer_settings", "actions.computer_settings", "computer_settings")
_try_register("open_app",          "actions.open_app",          "open_app")
_try_register("send_message",      "actions.send_message",      "send_message")
_try_register("web_search",        "actions.web_search",        "web_search")
_try_register("weather",           "actions.weather_report",    "weather_report")
_try_register("system_reminder",   "actions.reminder",          "system_reminder")
_try_register("screen_process",    "actions.screen_processor",  "screen_process")
_try_register("desktop_control",   "actions.desktop_control",   "desktop_control")
_try_register("browser_open",      "actions.browser_open",      "browser_open")
_try_register("spotify_control",   "actions.spotify_control",   "spotify_control")
_try_register("code_helper",      "actions.code_helper",       "code_helper")
_try_register("file_processor",   "actions.file_processor",    "file_processor")
_try_register("dev_agent",        "actions.dev_agent",         "dev_agent")
_try_register("flight_finder",    "actions.flight_finder",     "flight_finder")
_try_register("game_updater",     "actions.game_updater",      "game_updater")
_try_register("youtube_play",     "actions.youtube_control",   "youtube_play")

# Backward-compatible alias: existing code uses ACTION_REGISTRY as a dict
# ActionRegistry._entries() returns the same dict used internally
ACTION_REGISTRY = ActionRegistry._entries()

__all__ = ["ACTION_REGISTRY", "ActionRegistry"]
