import base64
import io
import time
import platform

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import mss
    _MSS = True
except ImportError:
    _MSS = False

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False

try:
    import PIL.Image
    _PIL = True
except ImportError:
    _PIL = False

# Module-level chat session (reused across calls)
_chat_session = None


def _take_screenshot_b64() -> str | None:
    """Capture the screen and return as base64-encoded JPEG."""
    try:
        if _MSS:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                img     = sct.grab(monitor)
                if _PIL:
                    pil_img = PIL.Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
                    buf = io.BytesIO()
                    pil_img.save(buf, format="JPEG", quality=85)
                    return base64.b64encode(buf.getvalue()).decode()
        elif _PYAUTOGUI:
            img = pyautogui.screenshot()
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        print(f"[ScreenProcessor] ⚠️ Screenshot failed: {e}")
    return None


def _take_camera_frame_b64() -> str | None:
    """Capture a frame from the default camera and return as base64-encoded JPEG."""
    if not _CV2:
        return None
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        time.sleep(0.3)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return None
        ret2, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret2:
            return None
        return base64.b64encode(buf.tobytes()).decode()
    except Exception as e:
        print(f"[ScreenProcessor] ⚠️ Camera capture failed: {e}")
    return None


def _get_or_create_session():
    global _chat_session
    if _chat_session is not None:
        return _chat_session
    try:
        import google.generativeai as genai
        from actions._gemini_helper import get_api_key
        genai.configure(api_key=get_api_key())
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=(
                "You are Lumina, an AI companion. You are analyzing visual content "
                "(screenshots or camera frames) and describing what you see in clear, "
                "natural language. Be concise, accurate, and helpful. "
                "When given a specific question about the screen or camera, answer directly. "
                "Do not mention being an AI unless directly asked."
            )
        )
        _chat_session = model.start_chat(history=[])
        print("[ScreenProcessor] ✅ Chat session initialized")
    except Exception as e:
        print(f"[ScreenProcessor] ❌ Session init failed: {e}")
        _chat_session = None
    return _chat_session


def _analyze_image_b64(b64_image: str, prompt: str) -> str:
    try:
        import google.generativeai as genai
        from actions._gemini_helper import get_api_key
        genai.configure(api_key=get_api_key())

        model = genai.GenerativeModel("gemini-2.5-flash")
        image_part = {
            "mime_type": "image/jpeg",
            "data": b64_image
        }
        response = model.generate_content([image_part, prompt])
        return response.text.strip()
    except Exception as e:
        return f"Vision analysis failed: {e}"


def analyze_screenshot(prompt: str = "Describe what you see on screen.") -> str:
    b64 = _take_screenshot_b64()
    if not b64:
        return "Could not capture screenshot. Make sure mss or pyautogui is installed."
    return _analyze_image_b64(b64, prompt)


def analyze_camera(prompt: str = "Describe what you see.") -> str:
    b64 = _take_camera_frame_b64()
    if not b64:
        return "Could not capture camera frame. Make sure cv2 is installed and a camera is connected."
    return _analyze_image_b64(b64, prompt)


def chat_about_screen(message: str) -> str:
    session = _get_or_create_session()
    if not session:
        return "Could not initialize screen chat session."

    b64 = _take_screenshot_b64()
    if b64:
        image_part = {"mime_type": "image/jpeg", "data": b64}
        try:
            response = session.send_message([image_part, message])
            return response.text.strip()
        except Exception as e:
            return f"Chat failed: {e}"
    else:
        # No screenshot — text only
        try:
            response = session.send_message(message)
            return response.text.strip()
        except Exception as e:
            return f"Chat failed: {e}"


def reset_session():
    global _chat_session
    _chat_session = None
    print("[ScreenProcessor] 🔄 Session reset")
    return "Screen chat session reset."


def screen_process(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Lumina screen / vision processor action.

    parameters:
        action  : 'screenshot' (default) | 'camera' | 'chat' | 'reset'
        prompt  : What to ask/describe about the captured image
    """
    params  = parameters or {}
    action  = params.get("action", "screenshot").lower().strip()
    prompt  = params.get("prompt", "").strip()

    if player:
        player.write_log(f"[screen] {action}")

    print(f"[ScreenProcessor] 📸 Action: {action}")

    if action == "reset":
        return reset_session()

    if action == "camera":
        q = prompt or "Describe what you see through the camera."
        return analyze_camera(q)

    if action == "chat":
        if not prompt:
            return "Please provide a message/question about the screen."
        return chat_about_screen(prompt)

    # Default: screenshot analysis
    q = prompt or "What do you see on this screen? Summarize the main content."
    return analyze_screenshot(q)
