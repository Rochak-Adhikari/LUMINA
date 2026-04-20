"""
actions/send_message.py — Lumina messaging action

Opens WhatsApp Web / Telegram / Instagram and attempts to send a message.

HONESTY POLICY:
- For WhatsApp: open the pre-filled link (wa.me deep link) in the default browser.
  If pyautogui is available, attempt to press Enter to send after the page loads.
  BUT — sending only works if the user is already logged in to WhatsApp Web.
  If login is required, we report that clearly instead of pretending success.
- For Telegram / Instagram: open the appropriate page; these require active login
  and UI state we cannot reliably control, so we report honestly.
- Never claim "message sent" unless Send was actually pressed and we have no
  indication of it failing.
"""

import os
import platform
import subprocess
import time
import webbrowser
from urllib.parse import quote

_OS = platform.system()

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE    = 0.1
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

SUPPORTED_PLATFORMS = ["whatsapp", "telegram", "instagram"]


def _open_url(url: str, wait: float = 2.5) -> bool:
    """Open a URL in the default browser. Returns True on success."""
    try:
        if _OS == "Windows":
            os.startfile(url)
        elif _OS == "Darwin":
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["xdg-open", url])
        time.sleep(wait)
        return True
    except Exception:
        try:
            webbrowser.open(url)
            time.sleep(wait)
            return True
        except Exception:
            return False


def _smart_type(text: str):
    """Type text using clipboard for reliability."""
    if _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.write(text, interval=0.03)
    time.sleep(0.2)


def _send_whatsapp(contact: str, message: str) -> str:
    """
    Open WhatsApp Web with a pre-filled message link.

    WhatsApp supports wa.me deep-links with phone numbers:
      https://wa.me/<phone>?text=<encoded_message>

    If the contact looks like a phone number (digits + + - spaces),
    use the deep link. Otherwise, open WhatsApp Web and note that
    contact lookup by name requires manual selection.

    If pyautogui is available, press Enter after the page is loaded
    to attempt to send the pre-filled message (works only if already logged in).
    """
    # Clean up contact
    digits = "".join(c for c in contact if c.isdigit() or c == "+")
    is_phone = len(digits) >= 7

    if is_phone:
        # Strip non-digits except leading +
        phone = contact.replace(" ", "").replace("-", "")
        url = f"https://wa.me/{phone}?text={quote(message)}"
        print(f"[SendMessage] WhatsApp deep link → {url[:80]}")
    else:
        # Name-based: open WhatsApp Web search
        url = f"https://web.whatsapp.com/send?text={quote(message)}"
        print(f"[SendMessage] WhatsApp Web (name search) → contact: {contact}")

    if not _open_url(url, wait=4.0):
        return "Could not open WhatsApp Web. Check your browser and internet connection."

    if not _PYAUTOGUI:
        return (
            f"Opened WhatsApp Web with your message pre-filled for {contact}. "
            "Please press Enter in the browser to send "
            "(pyautogui not installed for auto-send)."
        )

    # Give the page extra time to load + login state to be recognized
    time.sleep(2.5)

    # Try to press Enter to send the pre-filled message.
    # This works reliably ONLY if the user is already logged in to WhatsApp Web.
    # If the login screen appears, Enter will do nothing and we can't detect that.
    try:
        # Click in the approximate area of the message input box (bottom center)
        # then press Enter. This is best-effort — no login state verification.
        import pyautogui as _pg
        screen_w, screen_h = _pg.size()
        # WhatsApp Web message box is roughly at 50% width, 90% height
        _pg.click(screen_w // 2, int(screen_h * 0.90))
        time.sleep(0.4)
        _pg.press("enter")
        time.sleep(0.3)
        return (
            f"Attempted to send message to {contact} via WhatsApp Web. "
            "This succeeds only if you are already logged in. "
            "Please verify the message was sent in your browser."
        )
    except Exception as e:
        return (
            f"Opened WhatsApp Web for {contact}. "
            f"Auto-send failed ({e}). Please press Enter manually to send."
        )


def _send_telegram(contact: str, message: str) -> str:
    """
    Open Telegram Web and attempt to navigate to a contact.

    Telegram does not support pre-filled deep-links for contacts by name.
    For @username style contacts, we can attempt t.me/<username> links.
    """
    if contact.startswith("@"):
        # Username — direct t.me link
        username = contact.lstrip("@")
        url = f"https://t.me/{username}"
    elif contact.replace("@", "").isidentifier():
        url = f"https://t.me/{contact.lstrip('@')}"
    else:
        url = "https://web.telegram.org"

    print(f"[SendMessage] Telegram → {url}")
    if not _open_url(url, wait=3.5):
        return "Could not open Telegram."

    if not _PYAUTOGUI:
        return (
            f"Opened Telegram for {contact}. "
            "Please type your message and send it manually "
            "(pyautogui not installed for auto-send)."
        )

    # If we opened a t.me link, a "Send Message" button appears.
    # Click it, wait for chat to load, then type and press Enter.
    if contact.startswith("@") or url.startswith("https://t.me/"):
        time.sleep(2.5)
        try:
            # Tab to the "Send Message" button and click
            pyautogui.press("tab")
            time.sleep(0.3)
            pyautogui.press("enter")
            time.sleep(2.0)
            # Now the message box should be focused in the chat
            _smart_type(message)
            time.sleep(0.4)
            pyautogui.press("enter")
            time.sleep(0.3)
            return (
                f"Attempted to send message to {contact} via Telegram. "
                "Please verify it was sent in your browser."
            )
        except Exception as e:
            return (
                f"Opened Telegram for {contact}. "
                f"Auto-send failed ({e}). Please send manually."
            )

    return (
        f"Opened Telegram Web. To message {contact}, search for them manually "
        "and send your message."
    )


def _send_instagram(contact: str, message: str) -> str:
    """
    Open Instagram DMs.

    Instagram does not support pre-filled DM deep-links for arbitrary users.
    We open the new DM compose URL and report honestly.
    """
    url = "https://www.instagram.com/direct/new/"
    print(f"[SendMessage] Instagram DM compose → {contact}")

    if not _open_url(url, wait=4.0):
        return "Could not open Instagram."

    if not _PYAUTOGUI:
        return (
            f"Opened Instagram DM for {contact}. "
            "Please search for the contact and send your message manually."
        )

    # Instagram DM flow requires login, search UI interaction,
    # and confirmation steps that are too fragile to script reliably.
    # We do a best-effort attempt but are transparent about limitations.
    time.sleep(2.0)
    try:
        # Type contact name in the search box
        _smart_type(contact)
        time.sleep(1.5)
        pyautogui.press("enter")
        time.sleep(1.2)
        # Tab to "Next" button
        pyautogui.press("tab")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(1.5)
        # Type message
        _smart_type(message)
        time.sleep(0.4)
        pyautogui.press("enter")
        time.sleep(0.3)
        return (
            f"Attempted Instagram DM to {contact}. "
            "Instagram's login/UI state affects reliability — "
            "please verify the message was sent."
        )
    except Exception as e:
        return (
            f"Opened Instagram DM. Auto-send failed ({e}). "
            "Please search for {contact} and send manually."
        )


def send_message(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Lumina messaging action. Opens WhatsApp/Telegram/Instagram and sends a message.

    IMPORTANT: This tool requires the user to be logged in to the
    messaging platform in their browser. Lumina does NOT store credentials.
    Results are always reported honestly — "attempted" not "confirmed sent".

    parameters:
        platform  : 'whatsapp' | 'telegram' | 'instagram' (default: 'whatsapp')
        contact   : Contact name, @username, or phone number (e.g. '+1234567890')
        message   : Message text to send
    """
    params    = parameters or {}
    platform_ = (params.get("platform") or "whatsapp").lower().strip()
    contact   = (params.get("contact") or "").strip()
    message   = (params.get("message") or "").strip()

    if not contact:
        return "Please specify a contact name, @username, or phone number."
    if not message:
        return "Please specify a message to send."
    if platform_ not in SUPPORTED_PLATFORMS:
        return f"Unsupported platform: '{platform_}'. Supported: {', '.join(SUPPORTED_PLATFORMS)}"

    if player:
        player.write_log(f"[msg] {platform_} → {contact[:30]}")

    print(f"[SendMessage] Platform: {platform_}  Contact: {contact}  Msg: {message[:50]}")

    if platform_ == "whatsapp":
        return _send_whatsapp(contact, message)
    elif platform_ == "telegram":
        return _send_telegram(contact, message)
    elif platform_ == "instagram":
        return _send_instagram(contact, message)

    return "Could not send message."
