import subprocess
import platform
import shlex
import re
from datetime import datetime, timedelta

_OS = platform.system()

# Prefix used to tag Lumina's Task Scheduler tasks (avoids collisions)
_TASK_PREFIX = "LuminaReminder_"


def _parse_natural_time(time_str: str) -> datetime | None:
    """
    Parse natural language time/date expressions.
    Examples: '5 minutes', 'tomorrow 9am', '3:30 PM', 'in 2 hours'
    """
    now = datetime.now()
    s   = time_str.lower().strip()

    # "in X minutes/hours"
    m = re.search(r'in\s+(\d+)\s+(minute|minutes|min|mins)', s)
    if m:
        return now + timedelta(minutes=int(m.group(1)))

    m = re.search(r'in\s+(\d+)\s+(hour|hours|hr|hrs)', s)
    if m:
        return now + timedelta(hours=int(m.group(1)))

    # "X minutes" (without "in")
    m = re.search(r'(\d+)\s*(minute|minutes|min|mins)', s)
    if m:
        return now + timedelta(minutes=int(m.group(1)))

    m = re.search(r'(\d+)\s*(hour|hours|hr|hrs)', s)
    if m:
        return now + timedelta(hours=int(m.group(1)))

    # "tomorrow at HH:MM"
    if "tomorrow" in s:
        base = now + timedelta(days=1)
        m    = re.search(r'(\d{1,2}):?(\d{0,2})\s*(am|pm)?', s)
        if m:
            h   = int(m.group(1))
            mn  = int(m.group(2)) if m.group(2) else 0
            ampm = m.group(3) or ""
            if ampm == "pm" and h < 12: h += 12
            if ampm == "am" and h == 12: h = 0
            return base.replace(hour=h, minute=mn, second=0, microsecond=0)
        return base.replace(hour=9, minute=0, second=0, microsecond=0)

    # "at HH:MM AM/PM" or "HH:MM"
    m = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)?', s)
    if m:
        h    = int(m.group(1))
        mn   = int(m.group(2))
        ampm = m.group(3) or ""
        if ampm == "pm" and h < 12: h += 12
        if ampm == "am" and h == 12: h = 0
        dt = now.replace(hour=h, minute=mn, second=0, microsecond=0)
        if dt <= now:
            dt += timedelta(days=1)
        return dt

    # "H am/pm" or "H pm"
    m = re.search(r'(\d{1,2})\s*(am|pm)', s)
    if m:
        h    = int(m.group(1))
        ampm = m.group(2)
        if ampm == "pm" and h < 12: h += 12
        if ampm == "am" and h == 12: h = 0
        dt = now.replace(hour=h, minute=0, second=0, microsecond=0)
        if dt <= now:
            dt += timedelta(days=1)
        return dt

    # Just a number — assume minutes
    m = re.search(r'^(\d+)$', s)
    if m:
        return now + timedelta(minutes=int(m.group(1)))

    return None


def _task_name(title: str) -> str:
    safe = re.sub(r'[^a-zA-Z0-9_]', '_', title)
    return f"{_TASK_PREFIX}{safe[:40]}"


def _create_windows_task(task_name: str, trigger_dt: datetime, message: str) -> str:
    """Creates a Windows Task Scheduler one-shot task that shows a msgbox."""
    time_str = trigger_dt.strftime("%H:%M")
    date_str = trigger_dt.strftime("%Y-%m-%d")

    ps_action = (
        f'Add-Type -AssemblyName PresentationFramework; '
        f'[System.Windows.MessageBox]::Show("{message}", '
        f'"Lumina Reminder", "OK", "Information")'
    )

    cmd = (
        f'schtasks /create /f /tn "{task_name}" '
        f'/tr "powershell -WindowStyle Hidden -Command \\"{ps_action}\\"" '
        f'/sc once /sd {date_str} /st {time_str}'
    )

    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=15
    )
    if result.returncode == 0:
        return f"Reminder scheduled for {trigger_dt.strftime('%Y-%m-%d %H:%M')}."
    else:
        return f"Scheduler error: {result.stderr.strip()[:300]}"


def _delete_windows_task(task_name: str) -> str:
    result = subprocess.run(
        f'schtasks /delete /f /tn "{task_name}"',
        shell=True, capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0:
        return f"Reminder '{task_name}' deleted."
    return f"Could not delete: {result.stderr.strip()}"


def _list_windows_tasks() -> str:
    result = subprocess.run(
        f'schtasks /query /fo csv /nh | findstr "{_TASK_PREFIX}"',
        shell=True, capture_output=True, text=True, timeout=10
    )
    tasks = [
        line.split(",")[0].strip('"').replace(_TASK_PREFIX, "")
        for line in result.stdout.strip().split("\n")
        if _TASK_PREFIX in line
    ]
    if not tasks:
        return "No Lumina reminders scheduled."
    return "Scheduled reminders:\n" + "\n".join(f"  • {t}" for t in tasks)


def _platform_not_supported(action: str) -> str:
    return (
        f"Reminder action '{action}' via Windows Task Scheduler "
        f"is only fully supported on Windows. "
        f"On {_OS}, please use Lumina's events panel for reminders."
    )


def system_reminder(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Lumina system-level reminder (Windows Task Scheduler).

    parameters:
        action  : 'set' (default) | 'delete' | 'list'
        title   : Reminder title / label
        time    : Natural language time ('in 30 minutes', 'tomorrow 9am', '3:30 PM')
        message : Message text shown in reminder popup (defaults to title)
    """
    params  = parameters or {}
    action  = params.get("action", "set").lower().strip()
    title   = params.get("title", "Reminder").strip()
    time_   = params.get("time", "").strip()
    message = params.get("message", title).strip()

    if player:
        player.write_log(f"[reminder] {action} '{title}'")

    if action == "list":
        if _OS == "Windows":
            return _list_windows_tasks()
        return _platform_not_supported("list")

    if action == "delete":
        if _OS == "Windows":
            return _delete_windows_task(_task_name(title))
        return _platform_not_supported("delete")

    # Default: set
    if not time_:
        return "Please specify a time for the reminder (e.g. 'in 30 minutes', 'tomorrow 9am')."

    trigger_dt = _parse_natural_time(time_)
    if not trigger_dt:
        return f"Couldn't parse time: '{time_}'. Try 'in 30 minutes' or 'tomorrow 9am'."

    print(f"[Reminder] ⏰ '{title}' at {trigger_dt.strftime('%Y-%m-%d %H:%M')}")

    if _OS == "Windows":
        return _create_windows_task(_task_name(title), trigger_dt, message)

    # Fallback for non-Windows: return a note
    return (
        f"Reminder '{title}' would fire at {trigger_dt.strftime('%Y-%m-%d %H:%M')}. "
        f"System reminder scheduling is only fully supported on Windows. "
        f"Consider using Lumina's Events panel instead."
    )
