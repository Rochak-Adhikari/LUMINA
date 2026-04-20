"""
actions/__init__.py — Lumina Actions Package

Ported action capabilities from Mark-XXX. Each action follows:

    action_func(parameters: dict, response=None, player=None, session_memory=None) -> str

All successfully imported actions are registered in ACTION_REGISTRY.
Actions whose optional dependencies are missing at import time are skipped
gracefully — they will simply be absent from the registry and Lumina will
return a helpful error if the model calls them.
"""

ACTION_REGISTRY: dict = {}

def _try_register(name: str, module_path: str, func_name: str) -> None:
    """Import an action function and register it, logging any import failures."""
    try:
        import importlib
        mod = importlib.import_module(module_path)
        fn  = getattr(mod, func_name)
        ACTION_REGISTRY[name] = fn
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
_try_register("youtube_control",   "actions.youtube_control",   "youtube_control")
_try_register("spotify_control",   "actions.spotify_control",   "spotify_control")

__all__ = ["ACTION_REGISTRY"]
