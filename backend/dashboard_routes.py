import asyncio
import base64
import hashlib
import re
import secrets
import socket
import string
import time
import os
import sys
import platform
import subprocess
import threading
import collections
from pathlib import Path
from typing import Optional, Dict, Set, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
PORT = 8000
MAX_UPLOAD_MB = 500

def _make_uploads_dir() -> Path:
    """Return (and create) the cross-platform uploads folder."""
    for candidate in [
        Path.home() / "Downloads" / "Lumina Uploads",
        Path.home() / "Documents" / "Lumina Uploads",
        BASE_DIR / "uploads",
    ]:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except Exception:
            pass
    return BASE_DIR / "uploads"

UPLOADS_DIR = _make_uploads_dir()

_KEY_CHARS = [c for c in (string.ascii_uppercase + string.digits)
              if c not in ('O', 'I', 'L', '0', '1')]

# ── AES-256-CBC ───────────────────────────────────────────────────────────────
_AES_SALT = b'JARVIS-DASHBOARD-v1'

def _derive_key(session_key: str) -> bytes:
    """SHA-256(sessionKey‖salt) → 32-byte AES-256 key."""
    return hashlib.sha256(session_key.encode('utf-8') + _AES_SALT).digest()

def _decrypt_cbc(aes_key: bytes, enc_b64: str) -> str:
    """Decrypt base64(IV[16] ‖ ciphertext) with AES-256-CBC + PKCS7."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as sym_pad
    raw      = base64.b64decode(enc_b64)
    iv, ct   = raw[:16], raw[16:]
    dec      = Cipher(algorithms.AES(aes_key), modes.CBC(iv)).decryptor()
    padded   = dec.update(ct) + dec.finalize()
    unpadder = sym_pad.PKCS7(128).unpadder()
    return (unpadder.update(padded) + unpadder.finalize()).decode('utf-8')

# ── Firewall access setup ───────────────────────────────────────────────────
def _ensure_network_access(port: int) -> None:
    """Cross-platform, best-effort: open port in the OS firewall for LAN access."""
    if platform.system() == "Windows":
        import ctypes
        port_rule = f"Lumina Dashboard Port {port}"
        prog_rule  = "Lumina Dashboard Python"
        py_exe     = sys.executable

        def _netsh_rule_exists(name: str) -> bool:
            try:
                r = subprocess.run(
                    ["netsh", "advfirewall", "firewall", "show", "rule", f"name={name}"],
                    capture_output=True, text=True, timeout=5,
                )
                return r.returncode == 0 and "No rules match" not in r.stdout
            except Exception:
                return False

        def _network_is_public() -> bool:
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                     "(Get-NetConnectionProfile | "
                     "Where-Object {$_.NetworkCategory -eq 'Public'} | "
                     "Measure-Object).Count"],
                     capture_output=True, text=True, timeout=6,
                )
                return r.stdout.strip() not in ("", "0")
            except Exception:
                return False

        need_port    = not _netsh_rule_exists(port_rule)
        need_prog    = not _netsh_rule_exists(prog_rule)
        need_private = _network_is_public()

        if not need_port and not need_prog and not need_private:
            return  # already fully configured

        # Build a .bat file to configure firewall
        bat_lines = ["@echo off"]
        if need_private:
            bat_lines.append(
                'powershell -NoProfile -NonInteractive -Command "'
                'Get-NetConnectionProfile | '
                "Where-Object {$_.NetworkCategory -eq 'Public'} | "
                'Set-NetConnectionProfile -NetworkCategory Private"'
            )
        if need_port:
            bat_lines.append(
                f'netsh advfirewall firewall add rule '
                f'name="{port_rule}" protocol=TCP dir=in '
                f'localport={port} action=allow'
            )
        if need_prog:
            bat_lines.append(
                f'netsh advfirewall firewall add rule '
                f'name="{prog_rule}" dir=in action=allow '
                f'program="{py_exe}" enable=yes'
            )

        bat_body = "\r\n".join(bat_lines) + "\r\n"
        import tempfile
        fd, bat_path = tempfile.mkstemp(suffix=".bat", prefix="lumina_fw_")
        try:
            os.write(fd, bat_body.encode("mbcs"))
            os.close(fd)
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            return

        try:
            r = subprocess.run(
                [bat_path], capture_output=True, timeout=8, shell=True
            )
            if r.returncode == 0:
                print(f"[Dashboard] Firewall configured for port {port}.")
                try:
                    os.unlink(bat_path)
                except Exception:
                    pass
                return
        except Exception:
            pass

        # ShellExecuteW: native UAC elevation
        print("[Dashboard] One-time network setup required.")
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", bat_path, None, None, 0
            )
            if int(ret) > 32:
                time.sleep(2)
                print(f"[Dashboard] Network setup complete — port {port} is open.")
        except Exception as e:
            print(f"[Dashboard] Firewall setup error: {e}")
        finally:
            def _cleanup(path: str) -> None:
                time.sleep(5)
                try:
                    os.unlink(path)
                except Exception:
                    pass
            threading.Thread(target=_cleanup, args=(bat_path,), daemon=True).start()

def _local_ip() -> str:
    """Return the best LAN-facing IPv4 address, no internet required."""
    for probe in ("8.8.8.8", "1.1.1.1", "192.168.1.1"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect((probe, 80))
            ip = s.getsockname()[0]
            s.close()
            if not ip.startswith("127."):
                return ip
        except Exception:
            pass
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return "127.0.0.1"

def _read_static(name: str) -> str:
    try:
        return (STATIC_DIR / name).read_text(encoding="utf-8")
    except Exception as e:
        print(f"[Dashboard] Error reading static file {name}: {e}")
        return ""

class DashboardServer:
    def __init__(self):
        self._ip                          = _local_ip()
        self._tokens: Set[str]            = set()
        self._token_keys: Dict[str, str]  = {}   # auth_token → session_key
        self._aes_cache:  Dict[str, bytes]= {}   # session_key → AES bytes
        self._clients: Set[WebSocket]     = set()
        self._history: list[Dict[str, Any]] = []
        self._command_queue               = asyncio.Queue()
        self._wake_callback               = None
        self._connect_callback            = None
        self._pending_keys: Dict[str, float] = {}
        self._device_sessions: Dict[str, Dict[str, Any]] = {}  # device_token → {session_key}
        self._phone_audio_queue           = asyncio.Queue(maxsize=200)
        self._uploads_dir                 = UPLOADS_DIR

    def new_key(self, expiry_secs: int = 600) -> str:
        now = time.time()
        self._pending_keys = {k: v for k, v in self._pending_keys.items() if v > now}
        key = ''.join(secrets.choice(_KEY_CHARS) for _ in range(6))
        self._pending_keys[key] = now + expiry_secs
        return key

    def get_url(self) -> str:
        return f"http://{self._ip}:{PORT}"

    def get_manual_url(self) -> str:
        return f"{self._ip}:{PORT}"

    def _aes_key(self, session_key: str) -> bytes:
        if session_key not in self._aes_cache:
            self._aes_cache[session_key] = _derive_key(session_key)
        return self._aes_cache[session_key]

    def _decrypt(self, token: str, enc_b64: str) -> Optional[str]:
        sk = self._token_keys.get(token)
        if not sk:
            return None
        try:
            return _decrypt_cbc(self._aes_key(sk), enc_b64)
        except Exception:
            return None

    def set_wake_callback(self, fn) -> None:
        self._wake_callback = fn

    def set_connect_callback(self, fn) -> None:
        self._connect_callback = fn

    async def broadcast(self, msg: Dict[str, Any]) -> None:
        self._history.append(msg)
        if len(self._history) > 300:
            self._history = self._history[-300:]
        dead: Set[WebSocket] = set()
        for ws in list(self._clients):
            try:
                await ws.send_json(msg)
            except Exception:
                dead.add(ws)
        self._clients -= dead

# ── Singleton Instance ────────────────────────────────────────────────────────
_dashboard: Optional[DashboardServer] = None

def get_dashboard_server() -> DashboardServer:
    global _dashboard
    if _dashboard is None:
        _dashboard = DashboardServer()
    return _dashboard

def register_dashboard_routes(app: FastAPI) -> None:
    """Register all Lumina remote control dashboard routes on the FastAPI app."""
    dashboard = get_dashboard_server()

    # Trigger firewall setup in background thread
    asyncio.get_event_loop().run_in_executor(None, _ensure_network_access, PORT)

    def _auth(req: Request) -> bool:
        tok = req.headers.get("authorization", "").removeprefix("Bearer ").strip()
        return bool(tok) and tok in dashboard._tokens

    @app.get("/static/crypto.js")
    async def serve_crypto():
        js_file = STATIC_DIR / "crypto-js.min.js"
        if js_file.exists():
            return FileResponse(str(js_file), media_type="application/javascript")
        # Failover to cdn redirect
        from fastapi.responses import RedirectResponse
        return RedirectResponse("https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.2.0/crypto-js.min.js")

    @app.get("/login", response_class=HTMLResponse)
    async def login_page():
        return HTMLResponse(_read_static("login.html"))

    @app.get("/", response_class=HTMLResponse)
    async def index():
        html = _read_static("app.html")
        html = html.replace("__IP__", dashboard._ip).replace("__PORT__", str(PORT))
        return HTMLResponse(html)

    @app.post("/login")
    async def login(req: Request):
        body    = await req.json()
        entered = str(body.get("pin", "")).strip().upper()
        now     = time.time()
        if entered in dashboard._pending_keys and dashboard._pending_keys[entered] > now:
            del dashboard._pending_keys[entered]          # one-time use
            tok = secrets.token_urlsafe(32)
            dashboard._tokens.add(tok)
            dashboard._token_keys[tok] = entered
            dashboard._aes_key(entered)                   # pre-derive & cache
            if dashboard._connect_callback:
                try:
                    dashboard._connect_callback()
                except Exception as e:
                    print(f"[Dashboard] Connect callback error: {e}")
            asyncio.create_task(dashboard.broadcast(
                {"type": "sys", "text": "Remote connection established."}
            ))
            return JSONResponse({"ok": True, "token": tok})
        return JSONResponse({"ok": False, "error": "Invalid or expired key"}, status_code=401)

    @app.get("/auto-login")
    async def auto_login(key: str = ""):
        """QR code target — validates key, sets local storage values, redirects phone."""
        now = time.time()
        if not key or key not in dashboard._pending_keys or dashboard._pending_keys[key] <= now:
            return HTMLResponse("""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width">
<style>
  body{background:#07090f;color:#dde3ed;font-family:sans-serif;
       display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}
  h2{color:#f87171;margin-bottom:12px}p{color:#5e6a7e;font-size:14px}
</style></head>
<body><div><h2>Link Expired</h2>
<p>Open settings in Lumina UI to get a new pairing QR code.</p>
</div></body></html>""")

        del dashboard._pending_keys[key]
        tok     = secrets.token_urlsafe(32)
        dev_tok = secrets.token_urlsafe(32)
        dashboard._tokens.add(tok)
        dashboard._token_keys[tok] = key
        dashboard._aes_key(key)
        dashboard._device_sessions[dev_tok] = {"session_key": key}

        if dashboard._connect_callback:
            try:
                dashboard._connect_callback()
            except Exception as e:
                print(f"[Dashboard] Connect callback error: {e}")
        asyncio.create_task(dashboard.broadcast(
            {"type": "sys", "text": "Remote connection established via QR code."}
        ))

        return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width">
<style>
  body{{background:#07090f;color:#dde3ed;font-family:sans-serif;
       display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}}
  p{{color:#5e6a7e;font-size:14px}}
</style></head>
<body>
<script>
  sessionStorage.setItem('jarvis_token','{tok}');
  sessionStorage.setItem('jarvis_key','{key}');
  localStorage.setItem('jarvis_device_token','{dev_tok}');
  setTimeout(function(){{location.replace('/')}},400);
</script>
<p>Connecting to Lumina…</p>
</body></html>""")

    @app.post("/api/device-login")
    async def device_login_ep(req: Request):
        try:
            body = await req.json()
        except Exception:
            return JSONResponse({"ok": False}, status_code=400)
        dev_tok = (body.get("device_token") or "").strip()
        if not dev_tok or dev_tok not in dashboard._device_sessions:
            return JSONResponse({"ok": False}, status_code=401)
        session_key = dashboard._device_sessions[dev_tok]["session_key"]
        tok = secrets.token_urlsafe(32)
        dashboard._tokens.add(tok)
        dashboard._token_keys[tok] = session_key
        dashboard._aes_key(session_key)
        if dashboard._connect_callback:
            try:
                dashboard._connect_callback()
            except Exception as e:
                print(f"[Dashboard] Connect callback error: {e}")
        asyncio.create_task(dashboard.broadcast(
            {"type": "sys", "text": "Known device reconnected automatically."}
        ))
        return JSONResponse({"ok": True, "token": tok, "key": session_key})

    @app.post("/api/revoke-devices")
    async def revoke_devices(req: Request):
        if not _auth(req):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        count = len(dashboard._device_sessions)
        dashboard._device_sessions.clear()
        return JSONResponse({"ok": True, "revoked": count})

    @app.post("/api/command")
    async def command(req: Request):
        if not _auth(req):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        body  = await req.json()
        token = req.headers.get("authorization", "").removeprefix("Bearer ").strip()
        enc   = body.get("enc", "")
        if enc:
            text = dashboard._decrypt(token, enc)
            if text is None:
                return JSONResponse({"error": "Decryption failed"}, status_code=400)
        else:
            text = (body.get("text") or "").strip()
        if text:
            await dashboard._command_queue.put(text)
            if dashboard._wake_callback:
                try:
                    dashboard._wake_callback()
                except Exception as e:
                    print(f"[Dashboard] Wake callback error: {e}")
        return JSONResponse({"ok": True})

    @app.post("/api/wake")
    async def wake_ep(req: Request):
        if not _auth(req):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if dashboard._wake_callback:
            try:
                dashboard._wake_callback()
            except Exception as e:
                print(f"[Dashboard] Wake callback error: {e}")
        return JSONResponse({"ok": True})

    # ── Phone mic streaming ───────────────────────────────────────────
    @app.websocket("/ws/phone-audio")
    async def phone_audio_ws(websocket: WebSocket, token: str = ""):
        tok = token.strip()
        if not tok or tok not in dashboard._tokens:
            await websocket.close(code=4001)
            return
        await websocket.accept()
        asyncio.create_task(dashboard.broadcast(
            {"type": "sys", "text": "Phone microphone live."}
        ))
        try:
            while True:
                data = await websocket.receive_bytes()
                try:
                    dashboard._phone_audio_queue.put_nowait(
                        {"data": data, "mime_type": "audio/pcm"}
                    )
                except asyncio.QueueFull:
                    pass
        except WebSocketDisconnect:
            pass
        finally:
            asyncio.create_task(dashboard.broadcast(
                {"type": "sys", "text": "Phone microphone stopped."}
            ))

    # ── File sharing ──────────────────────────────────────────────────
    def _safe_filename(raw: str) -> str:
        name = Path(raw).name
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(". ")
        return name or "upload"

    @app.post("/api/upload")
    async def upload_file(req: Request, file: UploadFile = File(...)):
        if not _auth(req):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        safe = _safe_filename(file.filename or "upload")
        dest = dashboard._uploads_dir / safe
        stem, suffix = Path(safe).stem, Path(safe).suffix
        counter = 1
        while dest.exists():
            dest = dashboard._uploads_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        size = 0
        max_bytes = MAX_UPLOAD_MB * 1024 * 1024
        try:
            with open(dest, "wb") as fout:
                while True:
                    chunk = await file.read(65536)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        fout.close()
                        dest.unlink(missing_ok=True)
                        return JSONResponse(
                            {"error": f"File too large (max {MAX_UPLOAD_MB} MB)"},
                            status_code=413,
                        )
                    fout.write(chunk)
        except Exception as exc:
            try:
                dest.unlink(missing_ok=True)
            except Exception:
                pass
            return JSONResponse({"error": str(exc)}, status_code=500)

        # Drop file notification to all dashboard clients and logs
        asyncio.create_task(dashboard.broadcast({
            "type": "file_received",
            "name": dest.name,
            "size": size,
            "saved_to": str(dashboard._uploads_dir),
        }))
        return JSONResponse({"ok": True, "name": dest.name, "size": size})

    @app.get("/api/files")
    async def list_files(req: Request):
        if not _auth(req):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        files = []
        try:
            for f in sorted(
                (p for p in dashboard._uploads_dir.iterdir() if p.is_file()),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            ):
                files.append({"name": f.name, "size": f.stat().st_size})
        except Exception:
            pass
        return JSONResponse({"files": files})

    @app.get("/uploads/{filename}")
    async def download_file(filename: str, token: str = ""):
        tok = token.strip()
        if not tok or tok not in dashboard._tokens:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        safe = re.sub(r'[/\\]', '', filename)
        path = dashboard._uploads_dir / safe
        if not path.exists() or not path.is_file():
            return JSONResponse({"error": "Not found"}, status_code=404)
        return FileResponse(str(path), filename=safe)

    # ── WebSocket command sync ──────────────────────────────────────────
    @app.websocket("/ws/dashboard")
    async def ws_ep(websocket: WebSocket, token: str = ""):
        tok = token.strip()
        if not tok or tok not in dashboard._tokens:
            await websocket.close(code=4001)
            return
        await websocket.accept()
        dashboard._clients.add(websocket)
        for entry in dashboard._history[-50:]:
            try:
                await websocket.send_json(entry)
            except Exception:
                break
        try:
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "command":
                    enc = data.get("enc", "")
                    t   = dashboard._decrypt(tok, enc) if enc else (data.get("text") or "").strip()
                    if t:
                        await dashboard._command_queue.put(t)
                        if dashboard._wake_callback:
                            try:
                                dashboard._wake_callback()
                            except Exception as e:
                                print(f"[Dashboard] Wake callback error: {e}")
        except WebSocketDisconnect:
            pass
        finally:
            dashboard._clients.discard(websocket)
