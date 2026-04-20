import subprocess
import os
import time
import platform
from pathlib import Path

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_OS = platform.system()

# Windows app path shortcuts
_WIN_PATHS = [
    Path.home() / "AppData" / "Local" / "Programs",
    Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path("C:/Windows/System32"),
    Path("C:/Users/Public/Desktop"),
    Path.home() / "Desktop",
    Path.home() / "AppData" / "Local",
]

# Known user-installed apps that live under LocalAppData (not on PATH)
_LOCAL_APP_DIRS = {
    "discord":   Path.home() / "AppData" / "Local" / "Discord",
    "spotify":   Path.home() / "AppData" / "Roaming" / "Spotify",
    "telegram":  Path.home() / "AppData" / "Roaming" / "Telegram Desktop",
    "whatsapp":  Path.home() / "AppData" / "Local" / "WhatsApp",
    "zoom":      Path("C:/Program Files") / "Zoom" / "bin",
}

# Common Windows commands
_WIN_COMMANDS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe", "calc": "calc.exe",
    "paint": "mspaint.exe",
    "word": "WINWORD.EXE", "microsoft word": "WINWORD.EXE",
    "excel": "EXCEL.EXE", "microsoft excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "outlook": "OUTLOOK.EXE",
    "teams": "Teams.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe", "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "control": "control.exe", "control panel": "control.exe",
    "task manager": "taskmgr.exe",
    "settings": "ms-settings:", "windows settings": "ms-settings:",
    "snipping tool": "SnippingTool.exe", "snip": "SnippingTool.exe",
    "camera": "microsoft.windows.camera:",
    "photos": "ms-photos:",
    "xbox": "xbox:",
    "store": "ms-windows-store:",
    "chrome": "chrome.exe",
    "brave": "brave.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe", "microsoft edge": "msedge.exe",
    "vlc": "vlc.exe",
    "spotify": "Spotify.exe",
    "discord": "Discord.exe",
    "telegram": "Telegram.exe",
    "whatsapp": "WhatsApp.exe",
    "slack": "slack.exe",
    "zoom": "Zoom.exe",
    "vscode": "Code.exe", "visual studio code": "Code.exe",
    "git": "git.exe",
    "python": "python.exe",
    "obs": "obs64.exe",
    "winrar": "WinRAR.exe",
    "7zip": "7zFM.exe", "7-zip": "7zFM.exe",
    "regedit": "regedit.exe",
    "taskscheduler": "taskschd.msc",
}

# macOS app shortcuts
_MAC_APPS = {
    "safari": "Safari", "chrome": "Google Chrome", "firefox": "Firefox",
    "finder": "Finder", "terminal": "Terminal", "textedit": "TextEdit",
    "calculator": "Calculator", "calendar": "Calendar", "mail": "Mail",
    "notes": "Notes", "reminders": "Reminders", "maps": "Maps",
    "preview": "Preview", "photos": "Photos", "music": "Music",
    "facetime": "FaceTime", "messages": "Messages", "slack": "Slack",
    "xcode": "Xcode", "vscode": "Visual Studio Code",
    "activity monitor": "Activity Monitor", "system preferences": "System Preferences",
    "spotify": "Spotify", "discord": "Discord", "zoom": "zoom.us",
}


def _find_windows_executable(app_name: str) -> str | None:
    name_lower = app_name.lower().strip()

    # ── Check user-installed app dirs FIRST (Discord, Spotify, Telegram, etc.)
    # These live under AppData and are NOT on PATH, so bare exe names fail.
    for key, base_dir in _LOCAL_APP_DIRS.items():
        if key in name_lower or name_lower in key:
            if base_dir.exists():
                # Find the primary exe inside that directory (not installers/updaters)
                candidates = []
                for exe_path in base_dir.rglob("*.exe"):
                    n = exe_path.name.lower()
                    # Skip updaters and helpers
                    if any(skip in n for skip in ("update", "crash", "helper", "install", "setup")):
                        continue
                    if key in n:
                        candidates.append(exe_path)
                if candidates:
                    # Prefer shorter paths (less likely to be subdirectory helpers)
                    candidates.sort(key=lambda p: len(p.parts))
                    return str(candidates[0])

    # ── Check well-known command names (system apps, on PATH or known system paths)
    if name_lower in _WIN_COMMANDS:
        return _WIN_COMMANDS[name_lower]
    for key in _WIN_COMMANDS:
        if name_lower in key or key in name_lower:
            return _WIN_COMMANDS[key]

    # ── Search common install directories
    search_name = app_name.replace(" ", "") + ".exe"
    for base in _WIN_PATHS:
        if not base.exists():
            continue
        for path in base.rglob(f"*{app_name}*.exe"):
            return str(path)
        for path in base.rglob(search_name):
            return str(path)

    return None


def _open_windows(app_name: str) -> str:
    exe = _find_windows_executable(app_name)
    if exe:
        try:
            if exe.startswith("ms-"):
                os.startfile(exe)
            else:
                subprocess.Popen(exe, shell=True)
            return f"Opening {app_name}..."
        except Exception as e:
            return f"Found {app_name} but failed to open: {e}"

    # Generic fallback: let Windows shell resolve it
    try:
        subprocess.Popen(app_name, shell=True)
        return f"Attempting to open: {app_name}"
    except Exception as e:
        return f"Could not open {app_name}: {e}"


def _open_mac(app_name: str) -> str:
    app = _MAC_APPS.get(app_name.lower(), app_name)
    try:
        result = subprocess.run(
            ["open", "-a", app], capture_output=True, text=True
        )
        if result.returncode == 0:
            return f"Opened {app} on macOS."
        return f"Could not open {app}: {result.stderr.strip()}"
    except Exception as e:
        return f"Open failed: {e}"


def _open_linux(app_name: str) -> str:
    name = app_name.lower().replace(" ", "")
    try:
        result = subprocess.Popen(
            [name],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return f"Opened {app_name} on Linux."
    except FileNotFoundError:
        try:
            subprocess.Popen(
                ["xdg-open", app_name],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return f"Opened with xdg-open: {app_name}"
        except Exception as e:
            return f"Could not open {app_name}: {e}"


def _is_running(app_name: str) -> bool:
    if not _PSUTIL:
        return False
    name_lower = app_name.lower()
    for proc in psutil.process_iter(["name"]):
        try:
            if name_lower in proc.info["name"].lower():
                return True
        except Exception:
            pass
    return False


def _focus_or_open(app_name: str) -> str:
    if _OS == "Windows":
        try:
            script = f'(New-Object -ComObject WScript.Shell).AppActivate("{app_name}")'
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True, timeout=3
            )
            if result.returncode == 0:
                return f"Brought {app_name} to front."
        except Exception:
            pass
    return open_app({"app": app_name})


def open_app(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Lumina application launcher action.

    parameters:
        app     : App name (e.g. 'notepad', 'spotify', 'chrome')
        action  : 'open' (default) | 'close' | 'focus' | 'check'
    """
    params     = parameters or {}
    app_name   = params.get("app", "").strip()
    action     = params.get("action", "open").lower()

    if not app_name:
        return "Please specify an app name."

    if player:
        player.write_log(f"[app] {action} {app_name}")

    print(f"[OpenApp] ▶️ {action}: {app_name}")

    if action == "check":
        running = _is_running(app_name)
        return f"{app_name} is {'running' if running else 'not running'}."

    if action == "close":
        if _OS == "Windows":
            subprocess.run(["taskkill", "/IM", app_name + ".exe", "/F"],
                           capture_output=True)
            return f"Closed {app_name}."
        elif _OS == "Darwin":
            subprocess.run(["pkill", "-x", app_name], capture_output=True)
            return f"Closed {app_name}."
        else:
            subprocess.run(["pkill", "-f", app_name], capture_output=True)
            return f"Closed {app_name}."

    if action == "focus":
        return _focus_or_open(app_name)

    # Default: open
    if _OS == "Windows":
        return _open_windows(app_name)
    elif _OS == "Darwin":
        return _open_mac(app_name)
    else:
        return _open_linux(app_name)
