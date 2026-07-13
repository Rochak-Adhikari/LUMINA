import sys
import asyncio
import os

# ─────────────────────────────────────────────────────────────────────────────
# CRITICAL: Force UTF-8 on stdout/stderr BEFORE any print() runs.
# Electron spawns the backend with a cp1252 pipe on Windows; without this any
# print containing → ✓ ✗ — Unicode characters raises UnicodeEncodeError and
# kills the entire backend. errors="replace" ensures we never crash even on
# legacy terminals. Guarded for Python <3.7 where reconfigure() is missing.
# ─────────────────────────────────────────────────────────────────────────────
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ========================================
# CRITICAL: CONDA ENVIRONMENT CHECK
# ========================================
REQUIRED_ENV = r"E:\AI\conda_envs\lumina"
current_env = os.environ.get("CONDA_DEFAULT_ENV", "")

if current_env != REQUIRED_ENV:
    print(f"\n{'='*60}")
    print(f"ERROR: Wrong conda environment!")
    print(f"{'='*60}")
    print(f"Required: {REQUIRED_ENV}")
    print(f"Current:  {current_env or '(none)'}")
    print(f"\nPlease activate the correct environment:")
    print(f"  conda activate {REQUIRED_ENV}")
    print(f"{'='*60}\n")
    sys.exit(1)

print(f"[ENV CHECK] OK Running in conda environment: {REQUIRED_ENV}")

# Fix for asyncio subprocess support on Windows
# MUST BE SET BEFORE OTHER IMPORTS
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import socketio
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncio
import threading
import sys
import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path



# Ensure we can import lumina
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import lumina
from authenticator import FaceAuthenticator
from kasa_agent import KasaAgent
from memory_engine import MemoryEngine
from persona_engine import init_persona_engine, get_persona_engine

# Phase E5: Deferred init — created in start_audio after MemoryStore creates tables
memory_engine: MemoryEngine = None

# Create a Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()

# Register Remote Control Dashboard Routes
from dashboard_routes import register_dashboard_routes
register_dashboard_routes(app)

app_socketio = socketio.ASGIApp(sio, app)

# Phase E3: FastAPI shutdown event handler (replaces signal handlers)
@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown: save session summary and stop audio loop."""
    print("\n[SERVER] FastAPI shutdown event triggered...")
    
    # Phase E3: Save session summary before shutdown
    if audio_loop and audio_loop.memory_store and last_user_activity:
        print("[SERVER] Saving session summary before shutdown...")
        try:
            await asyncio.wait_for(save_session_summary("Server shutdown"), timeout=2.0)
        except asyncio.TimeoutError:
            print("[SESSION SUMMARY] Warning: Save timed out after 2s")
        except Exception as e:
            print(f"[SERVER] Error saving session summary: {e}")
    
    # Clean up audio loop
    if audio_loop:
        try:
            print("[SERVER] Stopping Audio Loop...")
            audio_loop.stop()
        except Exception as e:
            print(f"[SERVER] Error stopping audio loop: {e}")
    
    print("[SERVER] Shutdown complete.")

# ========================================
# PHASE D.1: GLOBAL STATE + HEARTBEAT
# ========================================
# Global state
audio_loop = None
loop_task = None
authenticator = None
kasa_agent = KasaAgent()
SETTINGS_FILE = "settings.json"

# Phase D.1.a: Client connection tracking for heartbeat
connected_clients = {}  # {sid: {'last_pong': timestamp, 'status': 'connected'}}
heartbeat_task = None

# Phase E2: Memory suggestion tracking
pending_memory_suggestions = {}  # {temp_id: {'type': str, 'content': str, 'confidence': float, 'reason': str, 'timestamp': float}}
import uuid

# Phase E3: Continuity memory tracking
last_user_activity = None  # Timestamp of last user_input
idle_timer_task = None  # Async task for idle timeout
last_summary_time = None  # Timestamp of last session_summary save (for rate limiting)
SESSION_IDLE_TIMEOUT = 12 * 60  # 12 minutes in seconds
SUMMARY_RATE_LIMIT = 30 * 60  # 30 minutes in seconds
import time

# Idle suppression gate — idle monitor skips emits if now < this timestamp
idle_disabled_until_ts = 0.0

# Nav confirmation rate-limit state: (panel, view) -> last_emit_timestamp
_nav_ack_last = {}
_NAV_ACK_COOLDOWN = 1.5  # seconds between duplicate ack for same panel+view
_NAV_ACK_LABELS = {
    'quests': 'Opened Quests.',
    'archive': 'Opened Knowledge Archives.',
    'events': 'Opened Events.',
    'settings': 'Opened Settings.',
    'home': 'Back to Home.',
}

async def emit_local_nav_ack(panel, view, sid=None, audio_loop_ref=None):
    """Emit a short local confirmation (chat_message + Gemini voice) for panel nav.
    Rate-limited: same (panel, view) cannot fire more than once per _NAV_ACK_COOLDOWN."""
    global _nav_ack_last
    _now = time.time()
    _key = (panel, view)
    _last = _nav_ack_last.get(_key, 0.0)
    if _now - _last < _NAV_ACK_COOLDOWN:
        print(f"[NAV ACK] rate-limited panel={panel} view={view} (cooldown)")
        return
    _nav_ack_last[_key] = _now

    label = _NAV_ACK_LABELS.get(panel, f"Opened {panel.title()}.")
    if view not in ('all', None):
        label = label.rstrip('.') + f" ({view})."

    # Gemini Live voice ack — short prompt, no tool calls, no conversation
    _al = audio_loop_ref or audio_loop
    if _al and _al.session:
        _prompt = f"[NAV_ACK] Say exactly this and nothing else: \"{label}\""
        await _al.safe_send(_prompt, end_of_turn=True, timeout=5.0)
        print(f"[NAV ACK] panel={panel} view={view} label='{label}' voice=gemini")
    else:
        # Fallback: text-only when no Gemini session
        await sio.emit('chat_message', {'sender': 'Lumina', 'text': label}, room=sid)
        print(f"[NAV ACK] panel={panel} view={view} label='{label}' voice=none (no session)")

# Phase E4: Project awareness tracking
last_project_name = "temp"  # Track last project to detect changes

# Phase D: Resilience & Audio Quality Settings
DEBUG_AUDIO = os.environ.get("DEBUG_AUDIO", "0") == "1"  # D.2.b: Gate verbose audio logs

# ========================================
# PHASE E2: MEMORY CANDIDATE EXTRACTOR
# ========================================
def extract_memory_candidates(text: str, context: str = "user") -> list:
    """
    Extract memory candidates from user or assistant messages.
    Returns list of dicts: {'type': str, 'content': str, 'confidence': float, 'reason': str}
    
    Rules:
    - Only stable, long-term items (identity, preferences, constraints, goals)
    - Confidence >= 0.75 required to suggest
    - Never auto-save (requires user approval)
    """
    candidates = []
    text_lower = text.lower()
    
    # Identity patterns (high confidence)
    identity_patterns = [
        (r"my name is (\w+)", "fact", 0.95, "User stated their name"),
        (r"i am (\w+)", "fact", 0.85, "User stated identity"),
        (r"call me (\w+)", "preference", 0.90, "User stated preferred name"),
    ]
    
    # Preference patterns (medium-high confidence)
    preference_patterns = [
        ("i prefer ", "preference", 0.85, "User stated preference"),
        ("i like ", "preference", 0.80, "User stated preference"),
        ("i love ", "preference", 0.80, "User stated preference"),
        ("i always ", "preference", 0.85, "User stated habit/preference"),
        ("i never ", "preference", 0.85, "User stated constraint"),
        ("don't ", "preference", 0.75, "User stated constraint"),
        ("mero preference ", "preference", 0.85, "User stated preference (Nepali)"),
    ]
    
    # Fact patterns (location, background)
    fact_patterns = [
        ("i am from ", "fact", 0.90, "User stated location"),
        ("i live in ", "fact", 0.90, "User stated location"),
        ("i work as ", "fact", 0.85, "User stated occupation"),
        ("i am a ", "fact", 0.80, "User stated role/identity"),
        ("ma ", "fact", 0.75, "User stated fact (Nepali)"),
    ]
    
    # Constraint patterns (important for system behavior)
    constraint_patterns = [
        ("always ask ", "preference", 0.90, "User requires confirmation"),
        ("never ", "preference", 0.85, "User stated constraint"),
        ("don't ever ", "preference", 0.90, "User stated strong constraint"),
        ("must ", "preference", 0.85, "User stated requirement"),
    ]
    
    all_patterns = identity_patterns + preference_patterns + fact_patterns + constraint_patterns
    
    for pattern, mem_type, confidence, reason in all_patterns:
        if pattern in text_lower:
            # Extract content after pattern
            idx = text_lower.index(pattern)
            content_start = idx
            # Take full sentence or up to punctuation
            remaining = text[content_start:].split('.')[0].split('!')[0].split('?')[0].strip()
            
            # Validate: must be substantial (>10 chars) and not too long (<200 chars)
            if remaining and 10 < len(remaining) < 200:
                # Only suggest if confidence >= 0.75
                if confidence >= 0.75:
                    candidates.append({
                        'type': mem_type,
                        'content': remaining,
                        'confidence': confidence,
                        'reason': reason
                    })
                    break  # Only one candidate per message
    
    return candidates

# ========================================
# PHASE E3: SESSION SUMMARY GENERATION
# ========================================
async def save_session_summary(reason: str = "Idle timeout"):
    """
    Generate and save a session summary for continuity (Phase E3).
    
    Summary structure (350-700 chars):
    - Where we left off
    - Open tasks/topics
    - Key decisions made today
    - Optional: tone/mood
    
    Rate limited: max 1 summary per 30 minutes
    """
    global last_summary_time
    
    # Check rate limit
    current_time = time.time()
    if last_summary_time and (current_time - last_summary_time) < SUMMARY_RATE_LIMIT:
        print(f"[SESSION SUMMARY] Skipped - rate limited (last saved {int((current_time - last_summary_time)/60)} min ago)")
        return
    
    if not audio_loop or not audio_loop.memory_store:
        print("[SESSION SUMMARY] Skipped - no memory store available")
        return
    
    # Generate summary based on recent conversation
    # Simple heuristic: get last few messages and summarize
    try:
        # Get recent memories to understand context
        recent_memories = audio_loop.memory_store.get_memories(limit=10, update_access=False)
        
        # Build a simple summary
        summary_parts = []
        summary_parts.append(f"Session ended: {reason}.")
        
        if recent_memories:
            # Count memory types
            facts = [m for m in recent_memories if m['type'] == 'fact']
            prefs = [m for m in recent_memories if m['type'] == 'preference']
            
            if facts:
                summary_parts.append(f"Discussed {len(facts)} fact(s).")
            if prefs:
                summary_parts.append(f"User shared {len(prefs)} preference(s).")
        
        # Add timestamp context
        summary_parts.append(f"Last activity: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}.")
        summary_parts.append("Ready to continue where we left off.")
        
        summary_content = " ".join(summary_parts)
        
        # Ensure summary is within bounds (350-700 chars)
        if len(summary_content) < 350:
            summary_content += " Conversation was brief but productive."
        if len(summary_content) > 700:
            summary_content = summary_content[:697] + "..."
        
        # Save to database
        memory_id = audio_loop.memory_store.add_memory('session_summary', summary_content)
        last_summary_time = current_time
        
        print(f"[SESSION SUMMARY] Saved (ID: {memory_id}): {summary_content[:100]}...")
        
    except Exception as e:
        print(f"[SESSION SUMMARY] Error: {e}")
        import traceback
        traceback.print_exc()

async def idle_timer_loop():
    """
    Monitor for idle timeout and save session summary (Phase E3).
    Triggers after 12 minutes of no user activity.
    """
    global last_user_activity, idle_timer_task
    
    print("[IDLE TIMER] Started monitoring for idle timeout")
    
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            
            if last_user_activity:
                idle_duration = time.time() - last_user_activity
                
                if idle_duration >= SESSION_IDLE_TIMEOUT:
                    print(f"[IDLE TIMER] Idle timeout reached ({int(idle_duration/60)} min)")
                    await save_session_summary("Idle timeout")
                    # Reset activity to prevent repeated saves
                    last_user_activity = None
                    
        except asyncio.CancelledError:
            print("[IDLE TIMER] Cancelled")
            break
        except Exception as e:
            print(f"[IDLE TIMER] Error: {e}")

DEFAULT_SETTINGS = {
    "face_auth_enabled": False,
    # Phase D.3.a: VAD settings for clipping prevention
    "vad_min_speech_ms": 350,      # Minimum speech duration to trigger (Phase 2: was 250)
    "vad_silence_stop_ms": 900,    # Silence duration before stopping
    "vad_pre_roll_ms": 700,        # Pre-roll buffer to capture first syllable (Phase 2: was 250)
    "vad_post_roll_ms": 300,       # Post-roll buffer after silence detected
    "continuous_conversation": False,  # D.3.c: Continuous mode (experimental)
    "tool_permissions": {
        # ========================================
        # ALL TOOLS DISABLED BY DEFAULT (Phase B.1)
        # ========================================
        "generate_cad": False,
        "run_web_agent": False,
        "write_file": False,
        "read_directory": False,
        "read_file": False,
        "create_project": False,
        "switch_project": False,
        "list_projects": False,
        "create_directory": False,
        "list_smart_devices": False,
        "control_light": False,
        "discover_printers": False,
        "print_stl": False,
        "get_print_status": False,
        "iterate_cad": False,
        "browser_control": True,
        "local_browser_control": False,
        "youtube_play":    True,
        # ── Phase M: Mark-XXX Integrated Action Tools (all disabled by default) ──
        "cmd_control": False,
        "file_controller": False,
        "computer_control": False,
        "computer_settings": False,
        "open_app": False,
        "send_message": False,
        "web_search": False,
        "weather": False,
        "system_reminder": False,
        "screen_process": False,
        "desktop_control": False,
        "browser_open":    False,
    },
    "browser_confirmation_mode": "relaxed",
    "persona_enabled": True,
    "persona_mode": "playful_mischievous_best_friend",
    "persona_teasing_intensity": 0.6,
    "persona_idle_enabled": True,
    "persona_idle_timeout_s": 60,
    "persona_idle_min_gap_s": 90,
    "persona_strict_sensitivity": 0.5,
    "persona_adaptive_mode": True,
    "printers": [],
    "kasa_devices": [],
    "camera_flipped": False,
    "auto_capture_tasks": True
}

SETTINGS = DEFAULT_SETTINGS.copy()

def load_settings():
    global SETTINGS
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                loaded = json.load(f)
                for k, v in loaded.items():
                    if k == "tool_permissions" and isinstance(v, dict):
                         SETTINGS["tool_permissions"].update(v)
                    else:
                        SETTINGS[k] = v

            # VAD floor enforcement: stale saved values must not regress below
            # the tuned defaults. Users can raise them but never below floor.
            _VAD_FLOORS = {
                "vad_min_speech_ms": 350,
                "vad_pre_roll_ms": 700,
            }
            for vk, floor in _VAD_FLOORS.items():
                if SETTINGS.get(vk, 0) < floor:
                    print(f"[SETTINGS] Upgrading {vk}: {SETTINGS.get(vk)} -> {floor} (floor)")
                    SETTINGS[vk] = floor

            # Strip any deprecated/removed tool keys that may persist in saved JSON
            _DEPRECATED_TOOLS = {"youtube_control"}
            for _dt in _DEPRECATED_TOOLS:
                SETTINGS["tool_permissions"].pop(_dt, None)

            print(f"Loaded settings: {SETTINGS}")
        except Exception as e:
            print(f"Error loading settings: {e}")

def save_settings():
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(SETTINGS, f, indent=4)
        print("Settings saved.")
    except Exception as e:
        print(f"Error saving settings: {e}")

# Load on startup
load_settings()

# ========================================
# PHASE B.2: TOOL CLAMP (ENV-configurable)
# ========================================
# LUMINA_TOOL_CLAMP_MODE: "on" (default) | "off"
#   "on"  — force all tool permissions False, except those in the allowlist
#   "off" — use saved settings as-is (no forced overrides)
# LUMINA_TOOL_CLAMP_ALLOW: comma-separated tool names that stay enabled when clamp is ON
#   e.g. "browser_control" or "browser_control,read_file"
_clamp_mode = os.environ.get("LUMINA_TOOL_CLAMP_MODE", "on").strip().lower()
_clamp_allow_raw = os.environ.get("LUMINA_TOOL_CLAMP_ALLOW", "").strip()
_clamp_allowlist = set(t.strip() for t in _clamp_allow_raw.split(",") if t.strip()) if _clamp_allow_raw else set()

print(f"[TOOL CLAMP] mode={_clamp_mode}  allowlist={sorted(_clamp_allowlist) if _clamp_allowlist else '(none)'}")

def _reapply_tool_clamp():
    """Re-enforce the tool clamp on current SETTINGS.

    Called at startup and after every tool_permissions update to prevent
    runtime writes from overriding clamp-protected values.
    """
    if _clamp_mode != "on":
        return
    changed = []
    for tool_key in SETTINGS["tool_permissions"].keys():
        if tool_key in _clamp_allowlist:
            if not SETTINGS["tool_permissions"][tool_key]:
                changed.append(f"{tool_key}: False->True")
            SETTINGS["tool_permissions"][tool_key] = True
        else:
            if SETTINGS["tool_permissions"][tool_key]:
                changed.append(f"{tool_key}: True->False")
            SETTINGS["tool_permissions"][tool_key] = False
    if changed:
        print(f"[TOOL CLAMP] Re-applied clamp, fixed: {changed}")

_reapply_tool_clamp()
print(f"[TOOL CLAMP] mode={_clamp_mode}  permissions after clamp: {SETTINGS['tool_permissions']}" if _clamp_mode == "on"
      else f"[TOOL CLAMP] Clamp OFF — using saved settings: {SETTINGS['tool_permissions']}")

authenticator = None

# Only initialize Kasa agent if smart device tools are enabled
if SETTINGS["tool_permissions"].get("list_smart_devices", False):
    kasa_agent = KasaAgent(known_devices=SETTINGS.get("kasa_devices"))
    print("[SERVER] Kasa agent initialized")
else:
    kasa_agent = None
    print("[SERVER] Kasa tools DISABLED - skipping Kasa agent initialization")
# tool_permissions is now SETTINGS["tool_permissions"]

# ========================================
# PHASE 1.1: DI CONTAINER WIRING
# Register existing concrete objects behind their interfaces.
# This does NOT change any runtime behaviour — concrete objects are
# constructed exactly as before.  Container wiring adds a resolution
# path for future callers that depend on interfaces instead of concretions.
# ========================================
from core.container import container
from core.interfaces import ISmartHomeAgent, IMemoryManager, IWorkspaceManager

# ISmartHomeAgent — kasa_agent may be None when smart devices are disabled.
# We only register if the agent was actually created; callers that resolve
# ISmartHomeAgent when it is unavailable will receive a KeyError and should
# handle it gracefully.
if kasa_agent is not None:
    container.register_instance(ISmartHomeAgent, kasa_agent)
    print("[DI] ISmartHomeAgent → KasaAgent registered")
else:
    print("[DI] ISmartHomeAgent — skipped (Kasa tools disabled)")

# IMemoryManager and IWorkspaceManager are owned by AudioLoop (lumina.py).
# They are registered lazily via _register_audio_loop_services() which is
# called from start_audio() after AudioLoop is fully constructed.
# See _register_audio_loop_services() below.

# ========================================
# PHASE 1.2: BRAIN STATE + EVENT BUS
# Construct and register BrainState and InProcessEventBus at server
# startup.  These objects coexist alongside all existing legacy globals;
# no existing behaviour is changed.
# ========================================
from core.interfaces import IBrainState, IEventBus
from brain.state import BrainState
from brain.events import InProcessEventBus

# BrainState — single source of runtime truth.
# Constructed here so it is available before AudioLoop starts.
_brain_state = BrainState()
container.register_instance(IBrainState, _brain_state)
print("[DI] IBrainState → BrainState registered")

# InProcessEventBus — lightweight in-process pub/sub.
# Registered as a singleton so all subsystems share the same bus.
_event_bus = InProcessEventBus()
container.register_instance(IEventBus, _event_bus)
print("[DI] IEventBus → InProcessEventBus registered")


# ========================================
# ACTION ROUTER: Gemini LLM prompt builder (no templates)
# ========================================
import json as _ar_json

def _build_action_llm_prompt(meta: dict, mood_state: str = "calm") -> str:
    """
    Build a Gemini directive for an action that was just performed.
    Gemini will generate a natural spoken reply in Lumina's voice.
    """
    pe = get_persona_engine()
    persona_mode = pe.persona_mode if pe else "playful_mischievous_best_friend"
    teasing_cap = pe.teasing_cap if pe else 0.5
    last_emotion = pe._last_emotion if pe else "neutral"

    meta_json = _ar_json.dumps(meta, default=str)

    return (
        f"[ACTION_CONFIRMATION]\n"
        f"You are Lumina. Mode: {persona_mode}.\n"
        f"User mood: {mood_state}. Emotion: {last_emotion}. Teasing cap: {teasing_cap:.2f}.\n"
        f"An action was just performed on the user's behalf:\n"
        f"{meta_json}\n"
        f"Generate a natural spoken reply confirming what you did.\n"
        f"Do NOT mention system mechanics, JSON, databases, or panels.\n"
        f"Sound human. Be concise (1-2 sentences). Be expressive.\n"
        f"Optionally ask a light follow-up question.\n"
        f"Do NOT start with 'Okay' or 'Sure'.\n"
    )

def _build_followup_llm_prompt(meta: dict, mood_state: str = "calm") -> str:
    """Build a Gemini directive for a follow-up question (ambiguous action)."""
    pe = get_persona_engine()
    persona_mode = pe.persona_mode if pe else "playful_mischievous_best_friend"
    followup_text = meta.get("followup_text", "I need more info.")

    return (
        f"[ACTION_FOLLOWUP]\n"
        f"You are Lumina. Mode: {persona_mode}.\n"
        f"User mood: {mood_state}.\n"
        f"You need to ask a clarifying question:\n"
        f"Intent: {followup_text}\n"
        f"Ask naturally in your voice. 1 sentence. Don't sound robotic.\n"
    )

def _build_alarm_dismiss_llm_prompt(title: str, mood_state: str = "calm") -> str:
    """Build a Gemini directive for post-alarm-dismiss follow-up."""
    pe = get_persona_engine()
    persona_mode = pe.persona_mode if pe else "playful_mischievous_best_friend"

    return (
        f"[ALARM_DISMISSED]\n"
        f"You are Lumina. Mode: {persona_mode}.\n"
        f"User mood: {mood_state}.\n"
        f"A reminder just fired for: \"{title}\"\n"
        f"The user dismissed the alarm overlay.\n"
        f"Ask naturally if they handled it. Offer to remind again if not.\n"
        f"1-2 sentences. Sound human. Don't be robotic.\n"
    )

async def _send_action_to_llm(prompt: str, sid: str = None):
    """
    Route an action confirmation prompt through Gemini Live session.
    Uses safe_send() to wait for any active turn before sending.
    Falls back to direct chat_message emit if session unavailable.
    """
    if audio_loop and audio_loop.session:
        sent = await audio_loop.safe_send(prompt, end_of_turn=True, timeout=15.0)
        if sent:
            print(f"[ACTION→LLM] Sent to Gemini ({len(prompt)} chars)")
            return True
        else:
            print("[ACTION→LLM] safe_send failed (timeout or error)")
    # Fallback: no active session
    print("[ACTION→LLM] No active session — fallback to chat_message")
    return False

# ========================================
# MOOD TRACKER: Per-session lightweight sentiment
# ========================================
_session_mood = {}  # sid -> {"messages": deque(maxlen=5), "mood_state": str}

def _update_mood(sid: str, text: str) -> str:
    """Track last 5 messages per session and compute lightweight mood state."""
    from collections import deque
    if sid not in _session_mood:
        _session_mood[sid] = {"messages": deque(maxlen=5), "mood_state": "calm"}

    entry = _session_mood[sid]
    entry["messages"].append(text)
    msgs = list(entry["messages"])

    # Lightweight sentiment signals
    text_lower = text.lower()
    frustration = any(w in text_lower for w in ["ugh", "damn", "wtf", "broken", "not working", "hate", "annoying", "stupid"])
    excitement = any(w in text_lower for w in ["awesome", "amazing", "yes!", "let's go", "perfect", "love it"])
    low_energy = len(text) < 15 and not any(c in text for c in "!?")
    focused = any(w in text_lower for w in ["fix", "debug", "implement", "build", "code", "deploy", "error"])
    playful = any(w in text_lower for w in ["haha", "lol", "lmao", "😂", "joke", "sing", "fun"])

    # Repetition detection (same short message repeated)
    if len(msgs) >= 3 and len(set(m.lower().strip() for m in msgs[-3:])) == 1:
        frustration = True

    # Compute state
    if frustration:
        state = "frustrated"
    elif playful:
        state = "playful"
    elif focused:
        state = "focused"
    elif excitement:
        state = "playful"
    elif low_energy:
        state = "low_energy"
    else:
        state = "calm"

    entry["mood_state"] = state
    return state

def _get_mood(sid: str) -> str:
    """Get current mood state for a session."""
    return _session_mood.get(sid, {}).get("mood_state", "calm")

# ========================================
# ALARM SCHEDULER
# ========================================
_alarm_task = None

async def _reminder_alarm_loop():
    """Background loop: check for due events every 3 seconds and fire alarms."""
    print("[ALARM] Reminder alarm scheduler started")
    while True:
        try:
            await asyncio.sleep(3)
            store = _get_memory_store()
            now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M")
            due = store.get_due_events(now_iso)
            for evt in due:
                store.mark_event_notified(evt["id"])
                # Broadcast alarm overlay ONLY — no chat_message, no LLM here
                await sio.emit("reminder_alarm", evt)
                print(f"[ALARM] Fired overlay for event id={evt['id']} title={evt['title']}")
        except Exception as e:
            print(f"[ALARM] Scheduler error (non-fatal): {e}")

@app.on_event("startup")
async def startup_event():
    global _alarm_task
    import sys
    print(f"[SERVER DEBUG] Startup Event Triggered")
    print(f"[SERVER DEBUG] Python Version: {sys.version}")
    try:
        loop = asyncio.get_running_loop()
        print(f"[SERVER DEBUG] Running Loop: {type(loop)}")
        policy = asyncio.get_event_loop_policy()
        print(f"[SERVER DEBUG] Current Policy: {type(policy)}")
    except Exception as e:
        print(f"[SERVER DEBUG] Error checking loop: {e}")

    # Only initialize Kasa agent if tools are enabled
    if kasa_agent is not None:
        print("[SERVER] Startup: Initializing Kasa Agent...")
        await kasa_agent.initialize()
    else:
        print("[SERVER] Startup: Kasa agent DISABLED - skipping initialization")

    # Start the reminder alarm scheduler
    _alarm_task = asyncio.create_task(_reminder_alarm_loop())

@app.get("/status")
async def status():
    return {"status": "running", "service": "Lumina Backend"}

from pydantic import BaseModel
class WhatsAppMessage(BaseModel):
    text: str
    sender: str

@app.post("/whatsapp_reply")
async def whatsapp_reply(msg: WhatsAppMessage):
    """Generate a Lumina reply for a WhatsApp message received in the UI."""
    from whatsapp_poller import generate_lumina_reply
    from google import genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"reply": "Hey, sorry, API key not configured on backend."}
    client = genai.Client(http_options={"api_version": "v1beta"}, api_key=api_key)
    try:
        reply_text = await generate_lumina_reply(msg.text, msg.sender, client)
        return {"reply": reply_text}
    except Exception as e:
        print(f"[WHATSAPP ENDPOINT] Error generating reply: {e}")
        return {"reply": "Sry bro, error aayo reply garna... 😅"}

# ========================================
# Phase T2: Local Browser Control test endpoints
# ========================================
@app.get("/api/settings/browser-confirmation")
async def get_browser_confirmation_mode():
    return {"mode": SETTINGS.get("browser_confirmation_mode", "relaxed")}

@app.post("/api/settings/browser-confirmation")
async def set_browser_confirmation_mode(request: Request):
    body = await request.json()
    mode = body.get("mode", "")
    if mode not in ("strict", "relaxed", "off"):
        return JSONResponse(status_code=400,
                            content={"error": f"Invalid mode: {mode}. Must be strict|relaxed|off"})
    SETTINGS["browser_confirmation_mode"] = mode
    if audio_loop:
        audio_loop.set_browser_confirmation_mode(mode)
    save_settings()
    await sio.emit('settings', SETTINGS)
    print(f"[SERVER] browser_confirmation_mode set to: {mode}")
    return {"mode": mode}

@app.get("/api/vision/latest")
async def vision_latest():
    """Return the latest screenshot frame from the browser frame cache."""
    from tools.local_browser_control import get_local_browser_controller
    ctrl = get_local_browser_controller()
    if ctrl._frame_cache:
        frame = ctrl._frame_cache[-1]
        return {
            "timestamp": frame["timestamp"],
            "tab_index": frame["tab_index"],
            "title": frame["title"],
            "url": frame["url"],
            "screenshot_b64": frame["screenshot_b64"],
        }
    return {"error": "No frames captured yet"}

@app.get("/local-browser/status")
async def local_browser_status():
    """Check if CDP is reachable and return current tab state."""
    from tools.local_browser_control import get_local_browser_controller, _cdp_reachable
    reachable = _cdp_reachable()
    if not reachable:
        return {"cdp_reachable": False, "tab": None}
    ctrl = get_local_browser_controller()
    conn = await ctrl.ensure_connected()
    if not conn["success"]:
        return {"cdp_reachable": True, "connected": False, "error": conn.get("error")}
    state = await ctrl.get_state()
    return {"cdp_reachable": True, "connected": True, "tab": state}

@app.post("/local-browser/open")
async def local_browser_open(request: Request):
    """Open a URL in the local Brave browser."""
    body = await request.json()
    url = body.get("url", "")
    if not url:
        return JSONResponse(status_code=400, content={"error": "Missing 'url' field"})
    from tools.local_browser_control import execute_local_browser
    ctx = {"tool_permissions": {"local_browser_control": True}}
    result = await execute_local_browser("open_url", {"url": url}, ctx)
    return result

# ========================================
# PHASE D.1.a: HEARTBEAT SYSTEM
# ========================================
async def heartbeat_loop():
    """Send heartbeat pings every 5s and check for stale clients"""
    global connected_clients
    while True:
        await asyncio.sleep(5)
        now = datetime.utcnow().timestamp()
        stale_clients = []
        
        for sid, info in list(connected_clients.items()):
            # Emit ping
            try:
                await sio.emit('hb_ping', {}, room=sid)
            except:
                pass
            
            # Check if client is stale (no pong for 15s)
            last_pong = info.get('last_pong', now)
            if now - last_pong > 15:
                if info.get('status') != 'stale':
                    print(f"[HB] Client {sid} timeout (no pong for {int(now - last_pong)}s)")
                    connected_clients[sid]['status'] = 'stale'
                    try:
                        await sio.emit('connection_status', {'status': 'reconnecting'}, room=sid)
                    except:
                        pass
                    stale_clients.append(sid)

@sio.event
async def hb_pong(sid):
    """Client responds to heartbeat ping"""
    global connected_clients
    if sid in connected_clients:
        connected_clients[sid]['last_pong'] = datetime.utcnow().timestamp()
        if connected_clients[sid]['status'] == 'stale':
            print(f"[HB] Client {sid} recovered")
            connected_clients[sid]['status'] = 'connected'
            await sio.emit('connection_status', {'status': 'connected'}, room=sid)

@sio.event
async def connect(sid, environ):
    global connected_clients, heartbeat_task, idle_timer_task
    print(f"[SOCKET] connect: {sid}")
    
    # Phase D.1.a: Track client for heartbeat
    connected_clients[sid] = {
        'last_pong': datetime.utcnow().timestamp(),
        'status': 'connected'
    }
    
    # Start heartbeat loop if not running
    if heartbeat_task is None or heartbeat_task.done():
        heartbeat_task = asyncio.create_task(heartbeat_loop())
    
    # Phase E3: Start idle timer loop if not running
    if idle_timer_task is None or idle_timer_task.done():
        idle_timer_task = asyncio.create_task(idle_timer_loop())
    
    await sio.emit('status', {'msg': 'Connected to Lumina Backend'}, room=sid)
    await sio.emit('connection_status', {'status': 'connected'}, room=sid)

    global authenticator
    
    # Callback for Auth Status
    async def on_auth_status(is_auth):
        print(f"[SERVER] Auth status change: {is_auth}")
        await sio.emit('auth_status', {'authenticated': is_auth})

    # Callback for Auth Camera Frames
    async def on_auth_frame(frame_b64):
        await sio.emit('auth_frame', {'image': frame_b64})

    # Initialize Authenticator if not already done
    if authenticator is None:
        authenticator = FaceAuthenticator(
            reference_image_path="reference.jpg",
            on_status_change=on_auth_status,
            on_frame=on_auth_frame
        )
    
    # Check if already authenticated or needs to start
    if authenticator.authenticated:
        await sio.emit('auth_status', {'authenticated': True})
    else:
        # Check Settings for Auth
        if SETTINGS.get("face_auth_enabled", False):
            await sio.emit('auth_status', {'authenticated': False})
            # Start the auth loop in background
            asyncio.create_task(authenticator.start_authentication_loop())
        else:
            # Bypass Auth
            print("Face Auth Disabled. Auto-authenticating.")
            # We don't change authenticator state to true to avoid confusion if re-enabled? 
            # Or we should just tell client it's auth'd.
            await sio.emit('auth_status', {'authenticated': True})

@sio.event
async def disconnect(sid):
    global connected_clients
    print(f"[SOCKET] disconnect: {sid}")
    
    # Phase D.1.a: Remove from tracking
    if sid in connected_clients:
        del connected_clients[sid]

# ========================================
# TRANSCRIPT AGGREGATOR (FIX A) — kill micro-stores
# ========================================
_TRANSCRIPT_NOISE = frozenset([
    "ok", "okay", "hmm", "hm", "um", "uh", "yo", "hey", "yes", "yeah",
    "yep", "no", "nope", "huh", "ah", "oh", "lol", "mhm",
])
_TRANSCRIPT_SENTENCE_END = re.compile(r"[.!?]$")

class TranscriptAggregator:
    """Buffers raw transcript fragments; flushes to MEMORY2 only when stable."""
    def __init__(self):
        self._buf = {"user": "", "assistant": ""}
        self._last_frag_ts: float = 0.0
        # Configurable (overridden from SETTINGS in _apply_settings)
        self.min_chars: int = 25
        self.force_flush_chars: int = 40
        self.silence_flush_s: float = 1.5
        self.enabled: bool = True

    def _is_junk(self, text: str) -> bool:
        t = text.strip().lower()
        if t in _TRANSCRIPT_NOISE:
            return True
        # Truly tiny with no content (1-2 chars, no punctuation)
        if len(t) < 3 and not _TRANSCRIPT_SENTENCE_END.search(t):
            return True
        return False

    def add_fragment(self, role: str, text: str) -> None:
        """Buffer a raw transcript fragment. Does NOT store to DB."""
        text = text.strip()
        if not text:
            return
        if self._is_junk(text):
            print(f"[TRANSCRIPT] junk_discard len={len(text)} text='{text[:30]}'")
            return
        key = "user" if role == "user" else "assistant"
        self._buf[key] += (" " if self._buf[key] else "") + text
        self._last_frag_ts = time.time()
        total = len(self._buf[key])
        print(f"[TRANSCRIPT] buffer_add len={len(text)} total={total}")

    def check_flush(self, role: str) -> str | None:
        """Return flushed text if flush conditions are met, else None."""
        key = "user" if role == "user" else "assistant"
        buf = self._buf[key].strip()
        if not buf:
            return None
        reason = None
        if len(buf) >= self.force_flush_chars:
            reason = "len"
        elif _TRANSCRIPT_SENTENCE_END.search(buf):
            reason = "punct"
        elif len(buf) >= self.min_chars:
            reason = "min_len"
        if reason:
            self._buf[key] = ""
            print(f"[TRANSCRIPT] flush reason={reason} chars={len(buf)}")
            return buf
        return None

    def force_flush(self, role: str, reason: str = "force") -> str | None:
        """Force-flush buffer (e.g. on real user turn). Returns text or None."""
        key = "user" if role == "user" else "assistant"
        buf = self._buf[key].strip()
        if buf and len(buf) >= 10:
            self._buf[key] = ""
            print(f"[TRANSCRIPT] flush reason={reason} chars={len(buf)}")
            return buf
        if buf:
            self._buf[key] = ""
            print(f"[TRANSCRIPT] discard_short reason={reason} chars={len(buf)}")
        return None

    def flush_stale(self) -> list:
        """Flush any buffers older than silence_flush_s. Returns [(role, text)]."""
        results = []
        now = time.time()
        if self._last_frag_ts == 0.0 or (now - self._last_frag_ts) < self.silence_flush_s:
            return results
        for key in ("user", "assistant"):
            buf = self._buf[key].strip()
            if buf and len(buf) >= 10:
                self._buf[key] = ""
                print(f"[TRANSCRIPT] flush reason=silence chars={len(buf)}")
                results.append((key, buf))
            elif buf:
                self._buf[key] = ""
                print(f"[TRANSCRIPT] discard_short reason=silence chars={len(buf)}")
        return results

_transcript_agg = TranscriptAggregator()

async def _store_transcript(role: str, text: str, project_name: str = None):
    """Store+index a flushed transcript chunk via MEMORY2, offloaded to thread (FIX C)."""
    if not memory_engine:
        return
    try:
        loop = asyncio.get_event_loop()
        tid = await loop.run_in_executor(
            None, memory_engine.store_transcript, role, text, project_name
        )
        if tid:
            await memory_engine.index_transcript_message(tid, text, project_name)
    except Exception as e:
        print(f"[MEMORY2] Background index error: {e}")

async def _index_transcript_bg(role: str, content: str, project_name: str = None):
    """FIX A: Buffer fragment, flush only when stable. Called from user_input + on_transcription."""
    if not _transcript_agg.enabled:
        # Fallback: direct store (legacy)
        await _store_transcript(role, content, project_name)
        return
    _transcript_agg.add_fragment(role, content)
    flushed = _transcript_agg.check_flush(role)
    if flushed:
        asyncio.create_task(_store_transcript(role, flushed, project_name))

async def _flush_transcript_buffer_if_stale():
    """Flush stale transcript buffers (called from idle monitor every 10s)."""
    proj = None
    if audio_loop and audio_loop.project_manager:
        proj = audio_loop.project_manager.current_project
    for role, text in _transcript_agg.flush_stale():
        asyncio.create_task(_store_transcript(role, text, proj))

@sio.event
async def start_audio(sid, data=None):
    global audio_loop, loop_task
    
    # Optional: Block if not authenticated
    # Only block if auth is ENABLED and not authenticated
    if SETTINGS.get("face_auth_enabled", False):
        if authenticator and not authenticator.authenticated:
            print("Blocked start_audio: Not authenticated.")
            await sio.emit('error', {'msg': 'Authentication Required'})
            return

    print("[SOCKET] start_audio request")
    
    device_index = None
    device_name = None
    if data:
        if 'device_index' in data:
            device_index = data['device_index']
        if 'device_name' in data:
            device_name = data['device_name']
            
    print(f"Using input device: Name='{device_name}', Index={device_index}")
    
    # ========================================
    # PHASE D.1.b: SINGLE SESSION GUARD
    # ========================================
    # Prevent duplicate AudioLoop/Gemini sessions
    if audio_loop:
        if loop_task and (loop_task.done() or loop_task.cancelled()):
             print("[SOCKET] reconnect_attempt: Previous loop task finished, cleaning up")
             audio_loop = None
             loop_task = None
        else:
             print("[SOCKET] recovered: Audio loop already running, reusing session")
             await sio.emit('status', {'msg': 'Lumina Already Running'})
             await sio.emit('connection_status', {'status': 'connected'}, room=sid)
             return


    # Callback to send audio data to frontend
    def on_audio_data(data_bytes):
        # We need to schedule this on the event loop
        # This is high frequency, so we might want to downsample or batch if it's too much
        asyncio.create_task(sio.emit('audio_data', {'data': list(data_bytes)}))

    # Callback to send CAL data to frontend
    def on_cad_data(data):
        info = f"{len(data.get('vertices', []))} vertices" if 'vertices' in data else f"{len(data.get('data', ''))} bytes (STL)"
        print(f"Sending CAD data to frontend: {info}")
        asyncio.create_task(sio.emit('cad_data', data))

    # Callback to send Browser data to frontend
    def on_web_data(data):
        print(f"Sending Browser data to frontend: {len(data.get('log', ''))} chars logs")
        asyncio.create_task(sio.emit('browser_frame', data))
        
    # Callback to send Transcription data to frontend
    _last_emitted_hash = [None]  # mutable container for closure
    def on_transcription(data):
        # data = {"sender": "User"|"Lumina", "text": "..."}
        _text = data.get('text', '')
        if not _text:
            return

        # Task D: Suppress assistant output if voice nav fast-path handled this turn
        if data.get('sender') == 'Lumina' and audio_loop and audio_loop._voice_nav_handled:
            print(f"[DEDUP] skip_emit reason=voice_nav_handled text='{_text[:40]}'")
            return

        # Task D: Hash-based dedup for assistant messages (catches reconnect replays)
        if data.get('sender') == 'Lumina':
            import hashlib
            _h = hashlib.md5(_text.encode()).hexdigest()[:12]
            if _h == _last_emitted_hash[0]:
                print(f"[DEDUP] skip_emit message_hash={_h} reason=already_emitted")
                return
            _last_emitted_hash[0] = _h
            # Extend idle suppression on assistant speech (30s from now)
            global idle_disabled_until_ts
            _tts_gate = time.time() + 30.0
            if _tts_gate > idle_disabled_until_ts:
                idle_disabled_until_ts = _tts_gate

        asyncio.create_task(sio.emit('transcription', data))
        # Phase E5: Store transcripts from voice pipeline (non-blocking)
        if memory_engine and _text:
            _role = "assistant" if data.get('sender') == 'Lumina' else "user"
            _project = audio_loop.project_manager.current_project if (audio_loop and audio_loop.project_manager) else None
            asyncio.create_task(_index_transcript_bg(_role, _text, _project))

    # Callback to send Confirmation Request to frontend
    def on_tool_confirmation(data):
        # data = {"id": "uuid", "tool": "tool_name", "args": {...}}
        print(f"Requesting confirmation for tool: {data.get('tool')}")
        asyncio.create_task(sio.emit('tool_confirmation_request', data))

    # Callback to send CAD status to frontend
    def on_cad_status(status):
        # status can be: 
        # - a string like "generating" (from lumina.py handle_cad_request)
        # - a dict with {status, attempt, max_attempts, error} (from CadAgent)
        if isinstance(status, dict):
            print(f"Sending CAD Status: {status.get('status')} (attempt {status.get('attempt')}/{status.get('max_attempts')})")
            asyncio.create_task(sio.emit('cad_status', status))
        else:
            # Legacy: simple string
            print(f"Sending CAD Status: {status}")
            asyncio.create_task(sio.emit('cad_status', {'status': status}))

    # Callback to send CAD thoughts to frontend (streaming)
    def on_cad_thought(thought_text):
        asyncio.create_task(sio.emit('cad_thought', {'text': thought_text}))

    # Callback to send Project Update to frontend
    def on_project_update(project_name):
        global last_project_name
        print(f"Sending Project Update: {project_name}")
        asyncio.create_task(sio.emit('project_update', {'project': project_name}))
        
        # Phase E4: Emit system message on project change
        if last_project_name != project_name:
            last_project_name = project_name
            asyncio.create_task(sio.emit('chat_message', {
                'sender': 'System',
                'text': f'📁 Project set to: {project_name}. Global memory stays shared across projects; project chat/files are scoped here.'
            }))

    # Callback to send Device Update to frontend
    def on_device_update(devices):
        # devices is a list of dicts
        print(f"Sending Kasa Device Update: {len(devices)} devices")
        asyncio.create_task(sio.emit('kasa_devices', devices))

    # Callback to send Error to frontend
    def on_error(msg):
        print(f"Sending Error to frontend: {msg}")
        asyncio.create_task(sio.emit('error', {'msg': msg}))
    
    # Phase D.1.c: Callback for Gemini Live connection status
    def on_model_status(status):
        # status: 'connecting', 'connected', 'disconnected', 'reconnecting'
        asyncio.create_task(sio.emit('model_status', {'status': status}))

    # Initialize Lumina
    try:
        print(f"Initializing AudioLoop with device_index={device_index}")
        audio_loop = lumina.AudioLoop(
            video_mode="none", 
            on_audio_data=on_audio_data,
            on_cad_data=on_cad_data,
            on_web_data=on_web_data,
            on_transcription=on_transcription,
            on_tool_confirmation=on_tool_confirmation,
            on_cad_status=on_cad_status,
            on_cad_thought=on_cad_thought,
            on_project_update=on_project_update,
            on_device_update=on_device_update,
            on_error=on_error,
            on_model_status=on_model_status,  # Phase D.1.c: Gemini Live status

            input_device_index=device_index,
            input_device_name=device_name,
            kasa_agent=kasa_agent
        )
        
        # Phase D.3.a: Apply VAD settings from SETTINGS
        audio_loop.vad_min_speech_ms = SETTINGS.get('vad_min_speech_ms', 350)
        audio_loop.vad_silence_stop_ms = SETTINGS.get('vad_silence_stop_ms', 900)
        audio_loop.vad_pre_roll_ms = SETTINGS.get('vad_pre_roll_ms', 700)
        audio_loop.vad_post_roll_ms = SETTINGS.get('vad_post_roll_ms', 300)
        print(f"[VAD INIT] Applied to AudioLoop: min_speech={audio_loop.vad_min_speech_ms} pre_roll={audio_loop.vad_pre_roll_ms} silence_stop={audio_loop.vad_silence_stop_ms} post_roll={audio_loop.vad_post_roll_ms}")

        # Task B: Wire voice nav fast-path callback
        def _on_voice_command(panel, view):
            nav_data = {"panel": panel, "view": view}
            asyncio.create_task(sio.emit("navigate_panel", nav_data, room=sid))
            asyncio.create_task(emit_local_nav_ack(panel, view, sid=sid, audio_loop_ref=audio_loop))
            print(f"[VOICE FASTPATH] emit navigate_panel panel={panel} view={view} source=voice")
        audio_loop.on_voice_command = _on_voice_command

        print("AudioLoop initialized successfully.")

        # Phase E5: Initialize MemoryEngine AFTER MemoryStore has created all tables
        global memory_engine
        if memory_engine is None and audio_loop.memory_store:
            db_path = str(audio_loop.memory_store.db_path)
            memory_engine = MemoryEngine(db_path=db_path)
            print(f"[MEMORY2] Engine initialized with DB: {db_path}")
            # Run priority decay on session start
            try:
                decay_result = memory_engine.run_decay(audio_loop.memory_store)
                if decay_result.get("decayed", 0) > 0 or decay_result.get("demoted", 0) > 0:
                    print(f"[MEMORY DECISION] Session start decay: {decay_result}")
            except Exception as e:
                print(f"[MEMORY2] Decay error on startup: {e}")

        # ── Phase 1.1: Register AudioLoop-owned services into the DI container ──
        # Use override() instead of register_instance() so session restarts
        # (audio_loop = None → new AudioLoop) do not throw "already registered".
        if audio_loop.memory_store:
            container.override(IMemoryManager, audio_loop.memory_store)
            print("[DI] IMemoryManager → MemoryStore registered")
        if audio_loop.project_manager:
            container.override(IWorkspaceManager, audio_loop.project_manager)
            print("[DI] IWorkspaceManager → ProjectManager registered")
        if memory_engine:
            from core.interfaces import IKnowledgeManager
            container.override(IKnowledgeManager, memory_engine)
            print("[DI] IKnowledgeManager → MemoryEngine registered")

        # Apply current permissions
        audio_loop.update_permissions(SETTINGS["tool_permissions"])
        audio_loop.set_browser_confirmation_mode(SETTINGS.get("browser_confirmation_mode", "relaxed"))


        # Initialize Persona Engine
        persona_eng = init_persona_engine(SETTINGS)
        print(f"[PERSONA] Engine initialized: {persona_eng.get_status()}")
        
        # Check initial mute state
        if data and data.get('muted', False):
            print("Starting with Audio Paused")
            audio_loop.set_paused(True)

        # Generate startup greeting to inject as start_message
        _startup_greeting = None
        if persona_eng and persona_eng.enabled:
            _startup_greeting = persona_eng.generate_startup_greeting()
            print(f"[PERSONA] Startup greeting: {_startup_greeting}")

        print("Creating asyncio task for AudioLoop.run()")
        _start_msg = f"[PERSONA_STARTUP_GREETING]\nSay this naturally as your opening line (paraphrase, don't read verbatim): \"{_startup_greeting}\"" if _startup_greeting else None
        loop_task = asyncio.create_task(audio_loop.run(start_message=_start_msg))
        
        # Add a done callback to catch silent failures in the loop
        def handle_loop_exit(task):
            try:
                task.result()
            except asyncio.CancelledError:
                print("Audio Loop Cancelled")
            except Exception as e:
                print(f"Audio Loop Crashed: {e}")
                # You could emit 'error' here if you have context
        
        loop_task.add_done_callback(handle_loop_exit)

        # Phase 6: True Idle Mind — autonomous Gemini-generated initiative
        import random as _idle_random
        _IDLE_CATEGORIES = [
            "Ask a reflective question about the user's day or current project.",
            "Comment on something interesting related to what the user was working on recently.",
            "Suggest an improvement or idea for the user's workflow.",
            "Say something playfully teasing (light, affectionate).",
            "Share a random curious thought or fun fact.",
            "Ask if the user needs anything or wants to brainstorm.",
        ]

        async def _persona_idle_monitor():
            """True Idle Mind: Gemini-generated autonomous thoughts, not templates."""
            while audio_loop and not audio_loop.stop_event.is_set():
                # Random interval: 45-120 seconds between checks
                await asyncio.sleep(_idle_random.uniform(45, 120))
                pe = get_persona_engine()
                if not pe or not pe.idle_enabled:
                    continue
                # Phase 1: Block idle when Gemini is actively generating or audio still playing
                if audio_loop and (audio_loop.is_generating or time.time() < audio_loop._mic_gate_until):
                    print(f"[IDLE MIND] suppressed reason={'generating' if audio_loop.is_generating else 'audio_playing'}")
                    continue
                # Idle suppression: skip if within cooldown window after user activity / TTS
                _now_idle = time.time()
                if _now_idle < idle_disabled_until_ts:
                    _remaining = idle_disabled_until_ts - _now_idle
                    print(f"[IDLE MIND] suppressed — cooldown {_remaining:.0f}s remaining")
                    continue
                # Flush stale transcript fragments
                if memory_engine:
                    await _flush_transcript_buffer_if_stale()
                # Use PersonaEngine cooldown/window checks
                _, stage = pe.check_idle()
                if stage == 0:
                    continue  # cooldown not met or idle not triggered
                if stage >= 3:
                    continue  # silence stage — don't speak

                pe.set_idle_emitting(True)
                try:
                    if audio_loop and audio_loop.session:
                        category = _idle_random.choice(_IDLE_CATEGORIES)
                        mood = _get_mood("__idle__")
                        persona_mode = pe.persona_mode if pe else "playful_mischievous_best_friend"
                        directive = (
                            f"[IDLE_MIND]\n"
                            f"You are Lumina. Mode: {persona_mode}. User mood: {mood}.\n"
                            f"The user has been quiet for a while. You want to say something spontaneously.\n"
                            f"Category: {category}\n"
                            f"Generate 1-2 natural sentences. Sound alive and spontaneous.\n"
                            f"Do NOT mention that the user has been idle or quiet.\n"
                            f"Do NOT say 'Hey, I noticed you've been quiet'.\n"
                            f"Just speak naturally as if a thought occurred to you.\n"
                        )
                        await audio_loop.safe_send(directive, end_of_turn=True, timeout=10.0)
                        print(f"[IDLE MIND] stage={stage} category='{category[:40]}'")
                except Exception as e:
                    print(f"[IDLE MIND] error: {e}")
                finally:
                    if pe:
                        pe.set_idle_emitting(False)

        asyncio.create_task(_persona_idle_monitor())
        
        print("Emitting 'Lumina Started'")
        await sio.emit('status', {'msg': 'Lumina Started'})

        # Load saved printers ONLY if printer tools are enabled
        if SETTINGS["tool_permissions"].get("discover_printers", False):
            saved_printers = SETTINGS.get("printers", [])
            if saved_printers and audio_loop.printer_agent:
                print(f"[SERVER] Loading {len(saved_printers)} saved printers...")
                for p in saved_printers:
                    audio_loop.printer_agent.add_printer_manually(
                        name=p.get("name", p["host"]),
                        host=p["host"],
                        port=p.get("port", 80),
                        printer_type=p.get("type", "moonraker"),
                        camera_url=p.get("camera_url")
                    )
            
            # Start Printer Monitor ONLY if enabled
            asyncio.create_task(monitor_printers_loop())
            print("[SERVER] Printer monitoring enabled")
        else:
            print("[SERVER] Printer tools DISABLED - skipping printer initialization")
        
    except Exception as e:
        print(f"CRITICAL ERROR STARTING LUMINA: {e}")
        import traceback
        traceback.print_exc()
        await sio.emit('error', {'msg': f"Failed to start: {str(e)}"})
        audio_loop = None # Ensure we can try again


async def monitor_printers_loop():
    """Background task to query printer status periodically."""
    print("[SERVER] Starting Printer Monitor Loop")
    while audio_loop and audio_loop.printer_agent:
        try:
            agent = audio_loop.printer_agent
            if not agent.printers:
                await asyncio.sleep(5)
                continue
                
            tasks = []
            for host, printer in agent.printers.items():
                if printer.printer_type.value != "unknown":
                    tasks.append(agent.get_print_status(host))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        pass # Ignore errors for now
                    elif res:
                        # res is PrintStatus object
                        await sio.emit('print_status_update', res.to_dict())
                        
        except asyncio.CancelledError:
            print("[SERVER] Printer Monitor Cancelled")
            break
        except Exception as e:
            print(f"[SERVER] Monitor Loop Error: {e}")
            
        await asyncio.sleep(2) # Update every 2 seconds for responsiveness

@sio.event
async def stop_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.stop() 
        print("Stopping Audio Loop")
        audio_loop = None
        await sio.emit('status', {'msg': 'Lumina Stopped'})

@sio.event
async def pause_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.set_paused(True)
        print("Pausing Audio")
        await sio.emit('status', {'msg': 'Audio Paused'})

@sio.event
async def resume_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.set_paused(False)
        print("Resuming Audio")
        await sio.emit('status', {'msg': 'Audio Resumed'})

@sio.event
async def confirm_tool(sid, data):
    # data: { "id": "...", "confirmed": True/False }
    request_id = data.get('id')
    confirmed = data.get('confirmed', False)
    
    print(f"[SERVER DEBUG] Received confirmation response for {request_id}: {confirmed}")
    
    if audio_loop:
        audio_loop.resolve_tool_confirmation(request_id, confirmed)
    else:
        print("Audio loop not active, cannot resolve confirmation.")

@sio.event
async def shutdown(sid, data=None):
    """Gracefully shutdown the server when the application closes."""
    global audio_loop, loop_task, authenticator
    
    print("[SERVER] ========================================")
    print("[SERVER] SHUTDOWN SIGNAL RECEIVED FROM FRONTEND")
    print("[SERVER] ========================================")
    
    # Phase E3: Save session summary before shutdown
    if audio_loop and audio_loop.memory_store and last_user_activity:
        print("[SERVER] Saving session summary before shutdown...")
        try:
            await asyncio.wait_for(save_session_summary("Frontend shutdown"), timeout=2.0)
        except asyncio.TimeoutError:
            print("[SESSION SUMMARY] Warning: Save timed out after 2s")
        except Exception as e:
            print(f"[SERVER] Error saving session summary: {e}")
    
    # Stop audio loop
    if audio_loop:
        print("[SERVER] Stopping Audio Loop...")
        audio_loop.stop()
        audio_loop = None
    
    # Cancel the loop task if running
    if loop_task and not loop_task.done():
        print("[SERVER] Cancelling loop task...")
        loop_task.cancel()
        loop_task = None
    
    # Stop authenticator if running
    if authenticator:
        print("[SERVER] Stopping Authenticator...")
        authenticator.stop()
    
    print("[SERVER] Frontend shutdown complete.")

@sio.event
async def user_input(sid, data):
    text = data.get('text')
    print(f"[SERVER DEBUG] User input received: '{text}'")
    
    # Phase D.4: Per-turn metrics tracking
    turn_start_time = datetime.utcnow()
    
    # Phase E3: Update last activity timestamp
    global last_user_activity, idle_disabled_until_ts
    last_user_activity = time.time()
    idle_disabled_until_ts = last_user_activity + 120.0
    print(f"[IDLE] user_turn ts={last_user_activity:.1f} idle_suppressed_until=+120s")

    # FIX B: Reset persona idle timer on REAL user turn only
    _pe_turn = get_persona_engine()
    if _pe_turn:
        _pe_turn.record_user_message()

    # FIX A: Force-flush transcript buffer on real user turn
    if _transcript_agg.enabled and memory_engine:
        _flushed = _transcript_agg.force_flush("user", reason="user_turn")
        if _flushed:
            _proj = None
            if audio_loop and audio_loop.project_manager:
                _proj = audio_loop.project_manager.current_project
            asyncio.create_task(_store_transcript("user", _flushed, _proj))

    if not audio_loop:
        print("[SERVER DEBUG] [Error] Audio loop is None. Cannot send text.")
        return

    if not text:
        return
    
    # ========================================
    # MEMORY LIFECYCLE: VOICE/TEXT CONFIRMATION OF PENDING MEMORIES
    # ========================================
    # EARLY INTERCEPT — runs before anything is sent to the LLM.
    # Strips punctuation so voice-transcribed text like "Yeah, lock that in." matches.
    if audio_loop and audio_loop.memory_store and memory_engine:
        # Normalize: lowercase, strip outer whitespace, remove all punctuation
        _clean = re.sub(r'[^\w\s]', '', text.lower()).strip()
        _clean = re.sub(r'\s+', ' ', _clean)  # collapse whitespace
        _now_iso = datetime.utcnow().isoformat()
        
        # Strong confirm phrases — always trigger if there's ANY valid target
        _strong_confirm = [
            "lock it in", "lock that in", "save it", "save that",
            "remember it", "remember that", "yes save", "yes remember",
            "okay save", "ok save", "keep it", "keep that", "go ahead",
            "yeah lock that in", "yes lock that in", "yeah save that",
            "yeah keep that", "confirm",
        ]
        # Weak confirm — only triggers when a consent or revisit target is active
        _weak_confirm = ["yes", "yeah", "yep", "sure", "do it"]
        
        # Strong deny phrases — always trigger if there's any pending/target
        _strong_deny = [
            "dont save", "forget that", "forget it", "never mind",
            "dont remember", "discard", "drop it", "no thanks",
            "no not today", "no actually", "nope dont save",
        ]
        # Weak deny — only triggers when a consent or revisit target is active
        _weak_deny = ["no", "nope", "skip", "not today"]
        
        _has_revisit_target = getattr(audio_loop, '_revisit_target_id', None) is not None
        _has_consent_target = getattr(audio_loop, '_current_pending_consent_id', None) is not None
        _has_any_target = _has_revisit_target or _has_consent_target
        
        _is_strong_confirm = any(p in _clean for p in _strong_confirm)
        _is_strong_deny = any(p in _clean for p in _strong_deny)
        _is_weak_confirm = any(p == _clean for p in _weak_confirm)  # exact match only
        _is_weak_deny = any(p == _clean for p in _weak_deny)  # exact match only
        
        # Weak phrases trigger only when there's a specific target awaiting response
        _is_confirm = _is_strong_confirm or (_is_weak_confirm and _has_any_target)
        _is_deny = _is_strong_deny or (_is_weak_deny and _has_any_target)
        
        # For strong phrases without any target, check if pending exists before intercepting
        if (_is_strong_confirm or _is_strong_deny) and not _has_any_target:
            _pending_check = audio_loop.memory_store.get_by_state("pending", limit=1)
            if not _pending_check:
                _is_confirm = False
                _is_deny = False
                print(f"[MEMORY DECISION] Strong phrase but no target/pending, forwarding to LLM: \"{text.strip()}\"")
        
        if _is_confirm or _is_deny:
            try:
                # Priority 1: Revisit target (explicit memory review)
                _revisit_id = getattr(audio_loop, '_revisit_target_id', None)
                if _revisit_id:
                    audio_loop._revisit_target_id = None
                    if _is_confirm:
                        print(f"[MEMORY REVISIT] Confirm for revisit id={_revisit_id}: \"{text.strip()}\"")
                        audio_loop.memory_store.promote_memory(_revisit_id, new_state="active", confidence=1.0)
                        print(f"[MEMORY REVISIT] Re-confirmed active id={_revisit_id}")
                        await sio.emit('memory_lifecycle_event', {
                            'event': 'revisit_confirm', 'id': _revisit_id,
                            'memory_id': _revisit_id, 'type': 'revisit',
                            'content': '(re-confirmed)', 'ts': _now_iso
                        }, room=sid)
                    else:
                        print(f"[MEMORY REVISIT] Deny for revisit id={_revisit_id}: \"{text.strip()}\"")
                        audio_loop.memory_store.demote_memory(_revisit_id, new_state="dormant")
                        print(f"[MEMORY REVISIT] Retired id={_revisit_id}")
                        await sio.emit('memory_lifecycle_event', {
                            'event': 'revisit_retire', 'id': _revisit_id,
                            'memory_id': _revisit_id, 'type': 'revisit',
                            'content': '(retired after revisit)', 'ts': _now_iso
                        }, room=sid)
                    return  # Do NOT forward to LLM

                # Priority 2: Consent target (Lumina just asked about this candidate)
                _consent_id = getattr(audio_loop, '_current_pending_consent_id', None)
                if _consent_id:
                    # Clear consent tracking
                    audio_loop._current_pending_consent_id = None
                    audio_loop._current_pending_consent_content = None
                    audio_loop._current_pending_consent_type = None
                    if _is_confirm:
                        print(f"[MEMORY DECISION] Confirm for consent id={_consent_id}: \"{text.strip()}\"")
                        audio_loop.memory_store.promote_memory(_consent_id, new_state="active", confidence=1.0)
                        print(f"[MEMORY DECISION] Promoted pending->active id={_consent_id}")
                        await sio.emit('memory_lifecycle_event', {
                            'event': 'promoted', 'id': _consent_id,
                            'memory_id': _consent_id, 'type': 'consent',
                            'content': '(confirmed by user)', 'ts': _now_iso
                        }, room=sid)
                    else:
                        print(f"[MEMORY DECISION] Deny for consent id={_consent_id}: \"{text.strip()}\"")
                        audio_loop.memory_store.demote_memory(_consent_id, new_state="dormant")
                        print(f"[MEMORY DECISION] Demoted pending->dormant id={_consent_id}")
                        await sio.emit('memory_lifecycle_event', {
                            'event': 'demoted', 'id': _consent_id,
                            'memory_id': _consent_id, 'type': 'consent',
                            'content': '(denied by user)', 'ts': _now_iso
                        }, room=sid)
                    return  # Do NOT forward to LLM

                # Priority 3: Fallback to most recent pending (strong phrases only reach here)
                recent_pending = audio_loop.memory_store.get_by_state("pending", limit=1)
                if recent_pending:
                    mem = recent_pending[0]
                    if _is_confirm:
                        print(f"[MEMORY DECISION] Confirm (fallback) for id={mem['id']}: \"{text.strip()}\"")
                        audio_loop.memory_store.promote_memory(mem['id'], new_state="active", confidence=1.0)
                        print(f"[MEMORY DECISION] Promoted pending->active id={mem['id']} type={mem['type']}")
                        await sio.emit('memory_lifecycle_event', {
                            'event': 'promoted', 'id': mem['id'],
                            'memory_id': mem['id'], 'type': mem['type'],
                            'content': mem['content'], 'ts': _now_iso
                        }, room=sid)
                    else:
                        print(f"[MEMORY DECISION] Deny (fallback) for id={mem['id']}: \"{text.strip()}\"")
                        audio_loop.memory_store.demote_memory(mem['id'], new_state="dormant")
                        print(f"[MEMORY DECISION] Demoted pending->dormant id={mem['id']} type={mem['type']}")
                        await sio.emit('memory_lifecycle_event', {
                            'event': 'demoted', 'id': mem['id'],
                            'memory_id': mem['id'], 'type': mem['type'],
                            'content': mem['content'], 'ts': _now_iso
                        }, room=sid)
                    return  # Do NOT forward to LLM
                else:
                    print(f"[MEMORY DECISION] Phrase detected but no target to act on: \"{text.strip()}\"")
            except Exception as e:
                print(f"[MEMORY DECISION] Confirmation error: {e}")
    
    # ========================================
    # PHASE T3: EXPLICIT REVISIT CUE DETECTION
    # ========================================
    # Only triggers on explicit user cue — never unsolicited.
    if audio_loop and audio_loop.memory_store:
        _revisit_cues = [
            "what do you remember", "check my preferences", "review my memories",
            "remember what i like", "what do i like", "what have you remembered",
            "revisit my preferences", "revisit my memories", "go over my preferences",
        ]
        _clean_for_revisit = re.sub(r'[^\w\s]', '', text.lower()).strip()
        _is_revisit = any(cue in _clean_for_revisit for cue in _revisit_cues)
        
        if _is_revisit:
            # B4: Don't set a new revisit target if one is already awaiting response
            if getattr(audio_loop, '_revisit_target_id', None) is not None:
                print(f"[MEMORY REVISIT] Already awaiting response for revisit id={audio_loop._revisit_target_id}, ignoring duplicate cue")
            else:
                try:
                    cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
                    all_active = audio_loop.memory_store.get_by_state("active", limit=50)
                    stale = [m for m in all_active
                             if m.get('type') in ('preference', 'intent')
                             and m.get('created_at', '') < cutoff]
                    if stale:
                        target = stale[0]
                        audio_loop._revisit_target_id = target['id']
                        audio_loop._revisit_target_content = target['content']
                        audio_loop._revisit_target_type = target['type']
                        _ts = datetime.utcnow().isoformat()
                        print(f"[MEMORY REVISIT] Set revisit target id={target['id']}: {target['content'][:60]}")
                        await sio.emit('memory_lifecycle_event', {
                            'event': 'revisit_prompt', 'id': target['id'],
                            'memory_id': target['id'],
                            'type': target['type'], 'content': target['content'],
                            'ts': _ts
                        }, room=sid)
                        # DO NOT return — let message flow to Gemini with revisit directive injected
                    else:
                        print("[MEMORY REVISIT] No stale active memories to revisit")
                        # Let Gemini handle naturally — it knows the memories
                except Exception as e:
                    print(f"[MEMORY REVISIT] Error: {e}")
    
    # ========================================
    # CHAT COMMAND INTERCEPTION (Phase B.1)
    # ========================================
    
    # /remember command: write to memory
    if text.strip().startswith('/remember '):
        parts = text.strip()[10:].split(None, 1)  # Remove '/remember ' and split type/content
        
        if len(parts) < 2:
            await sio.emit('chat_message', {
                'sender': 'System',
                'text': '❌ Usage: /remember <type> <content>\nTypes: fact, preference, conversation_summary'
            })
            return
        
        memory_type = parts[0].lower()
        content = parts[1]
        
        valid_types = ['fact', 'preference', 'conversation_summary', 'session_summary']
        if memory_type not in valid_types:
            await sio.emit('chat_message', {
                'sender': 'System',
                'text': f'❌ Invalid type: {memory_type}\nValid types: fact, preference, conversation_summary, session_summary'
            })
            return
        
        try:
            if audio_loop and audio_loop.memory_store:
                memory_id = audio_loop.memory_store.add_memory(memory_type, content)
                await sio.emit('chat_message', {
                    'sender': 'System',
                    'text': f'✅ Saved to memory ({memory_type}): {content}'
                })
                print(f"[SERVER] Memory written via /remember: {memory_type} - {content[:50]}")
            else:
                await sio.emit('chat_message', {
                    'sender': 'System',
                    'text': '❌ Memory store not available'
                })
        except Exception as e:
            await sio.emit('chat_message', {
                'sender': 'System',
                'text': f'❌ Failed to save memory: {str(e)}'
            })
            print(f"[SERVER] Error writing memory: {e}")
        
        return  # Do NOT forward to model
    
    # /memory command: list recent memories
    if text.strip() == '/memory':
        try:
            if audio_loop and audio_loop.memory_store:
                memories = audio_loop.memory_store.get_memories(limit=20, update_access=False)
                
                if memories:
                    memory_lines = ["📝 Recent Memories:"]
                    for mem in memories:
                        memory_lines.append(f"  • [{mem['type']}] {mem['content'][:80]}")
                    
                    await sio.emit('chat_message', {
                        'sender': 'System',
                        'text': '\n'.join(memory_lines)
                    })
                else:
                    await sio.emit('chat_message', {
                        'sender': 'System',
                        'text': '📝 No memories stored yet'
                    })
            else:
                await sio.emit('chat_message', {
                    'sender': 'System',
                    'text': '❌ Memory store not available'
                })
        except Exception as e:
            await sio.emit('chat_message', {
                'sender': 'System',
                'text': f'❌ Error retrieving memories: {str(e)}'
            })
            print(f"[SERVER] Error retrieving memories: {e}")
        
        return  # Do NOT forward to model
    
    # Phase E3: /save_summary command: manually trigger session summary save for testing
    if text.strip() == '/save_summary':
        try:
            if audio_loop and audio_loop.memory_store:
                print("[SERVER] Manual session summary save triggered via /save_summary")
                await save_session_summary("Manual test trigger")
                
                # Get the latest summary to confirm
                latest = audio_loop.memory_store.get_latest_session_summary()
                if latest:
                    await sio.emit('chat_message', {
                        'sender': 'System',
                        'text': f"✅ Session summary saved. It will be used on next restart for continuity."
                    })
                    print(f"[SERVER] Session summary saved via /save_summary (ID: {latest['id']})")
                else:
                    await sio.emit('chat_message', {
                        'sender': 'System',
                        'text': '⚠️ Summary save completed but could not retrieve'
                    })
            else:
                await sio.emit('chat_message', {
                    'sender': 'System',
                    'text': '❌ Memory store not available'
                })
        except Exception as e:
            await sio.emit('chat_message', {
                'sender': 'System',
                'text': f'❌ Error saving summary: {str(e)}'
            })
            print(f"[SERVER] Error in /save_summary: {e}")
        
        return  # Do NOT forward to model
    
    # ========================================
    # VOICE COMMAND FAST-PATH (deterministic, no LLM)
    # Handles panel navigation locally before any Gemini/memory calls.
    # ========================================
    _raw_text = text
    _text_lower = text.strip().lower()

    # Step 1: Normalize common STT mishearings
    _STT_WORD_MAP = {
        'questions': 'quests', 'question': 'quest',
        'archives': 'archive', 'archiving': 'archive',
        'reminder': 'reminders', 'calender': 'calendar',
    }
    for wrong, right in _STT_WORD_MAP.items():
        if wrong in _text_lower:
            _text_lower = _text_lower.replace(wrong, right)
    if _text_lower != text.strip().lower():
        text = _text_lower
        print(f"[STT NORMALIZE] '{_raw_text}' → '{text}'")

    # Step 2: Deterministic panel command detection
    _PANEL_COMMANDS = {
        'quests': [
            r'^(?:open|show|go\s*to|switch\s*to|view)\s+(?:my\s+)?(?:the\s+)?quests?(?:\s+panel)?$',
            r'^quests?\s+(?:khol|open|show)$',
            r'^(?:open|show)\s+(?:my\s+)?(?:completed|active|done|main|side)\s+quests?$',
        ],
        'archive': [
            r'^(?:open|show|go\s*to|switch\s*to|view)\s+(?:my\s+)?(?:the\s+)?(?:knowledge\s+)?archive(?:s)?(?:\s+panel)?$',
            r'^(?:open|show|go\s*to|view)\s+(?:my\s+)?notes?(?:\s+panel)?$',
            r'^(?:archive|notes?)\s+(?:khol|open|show)$',
        ],
        'events': [
            r'^(?:open|show|go\s*to|switch\s*to|view)\s+(?:my\s+)?(?:the\s+)?(?:events?|reminders?|calendar)(?:\s+panel)?$',
            r'^(?:events?|reminders?|calendar)\s+(?:khol|open|show)$',
            r'^(?:what|show)\s+(?:reminders?|events?)\s+(?:are|do\s+i\s+have)\s+(?:active|pending|today).*$',
        ],
        'settings': [
            r'^(?:open|show|go\s*to)\s+(?:the\s+)?settings?(?:\s+panel)?$',
        ],
        'home': [
            r'^(?:go\s+)?home$',
            r'^(?:open|show|go\s*to)\s+(?:the\s+)?(?:home|main|dashboard)(?:\s+panel)?$',
        ],
    }

    _fastpath_panel = None
    _fastpath_view = 'all'
    for panel, patterns in _PANEL_COMMANDS.items():
        for pat in patterns:
            if re.match(pat, _text_lower):
                _fastpath_panel = panel
                # Detect view filter
                if 'completed' in _text_lower or 'done' in _text_lower:
                    _fastpath_view = 'completed'
                elif 'active' in _text_lower:
                    _fastpath_view = 'active'
                elif 'side' in _text_lower:
                    _fastpath_view = 'side'
                break
        if _fastpath_panel:
            break

    if _fastpath_panel:
        nav_data = {"panel": _fastpath_panel, "view": _fastpath_view}
        await sio.emit("navigate_panel", nav_data, room=sid)
        await emit_local_nav_ack(_fastpath_panel, _fastpath_view, sid=sid, audio_loop_ref=audio_loop)
        print(f"[VOICE FASTPATH] raw='{_raw_text}' normalized='{_text_lower}' target_panel={_fastpath_panel} view={_fastpath_view} routed=LOCAL")
        return  # No LLM — local confirmation only

    # ========================================
    # ACTION ROUTER: Natural language → Panel CRUD → Gemini LLM voice
    # ========================================
    try:
        from action_router import ActionRouter
        _ar_store = _get_memory_store()
        _ar = ActionRouter(_ar_store)

        # Update mood tracker
        mood_state = _update_mood(sid, text)

        # Per-session last-item tracking for "that quest / that note" references
        if not hasattr(sio, '_ar_last_ids'):
            sio._ar_last_ids = {}
        last_ids = sio._ar_last_ids.get(sid, {"quest": None, "event": None, "note": None})

        _auto_capture = SETTINGS.get("auto_capture_tasks", True)
        _ar_result = _ar.parse(text, last_ids=last_ids, auto_capture=_auto_capture)
        if _ar_result:
            panel = _ar_result["panel"]
            action = _ar_result["action"]
            data = _ar_result.get("data", {})
            meta = _ar_result.get("meta", {})

            # Panel navigation — deterministic, no LLM/TTS
            if action == "navigate":
                nav_data = {"panel": panel, "view": data.get("view", "all")}
                if data.get("tag"):
                    nav_data["tag"] = data["tag"]
                await sio.emit("navigate_panel", nav_data, room=sid)
                print(f"[ACTION ROUTER] navigate→{panel} view={nav_data.get('view')} routed=LOCAL")
                return  # Silent — no Gemini call, no TTS

            if action == "ask_followup":
                # Route followup through Gemini for natural voice
                prompt = _build_followup_llm_prompt(meta, mood_state)
                sent = await _send_action_to_llm(prompt, sid)
                if not sent:
                    # Fallback: direct chat if no session
                    fb = meta.get("followup_text", "I need more info on that.")
                    await sio.emit('chat_message', {'sender': 'Lumina', 'text': fb}, room=sid)
                print(f"[ACTION ROUTER] followup→LLM panel={panel}")
                return

            executed = False
            entity_id = None
            try:
                if panel == "quests":
                    if action == "create":
                        result = _ar_store.create_quest(**data)
                        await sio.emit("quest_created", result)
                        entity_id = result.get("id")
                        executed = True
                    elif action == "update":
                        qid = data.pop("id")
                        result = _ar_store.update_quest(qid, **data)
                        if result:
                            await sio.emit("quest_updated", result)
                            entity_id = qid
                            executed = True
                    elif action == "delete":
                        if _ar_store.delete_quest(data["id"]):
                            await sio.emit("quest_deleted", {"id": data["id"]})
                            executed = True

                elif panel == "events":
                    if action == "create":
                        result = _ar_store.create_event(
                            title=data["title"], dt=data["datetime"], notes=data.get("notes", "")
                        )
                        await sio.emit("event_created", result)
                        entity_id = result.get("id")
                        executed = True
                    elif action == "update":
                        eid = data.pop("id")
                        result = _ar_store.update_event(eid, **data)
                        if result:
                            await sio.emit("event_updated", result)
                            entity_id = eid
                            executed = True
                    elif action == "delete":
                        if _ar_store.delete_event(data["id"]):
                            await sio.emit("event_deleted", {"id": data["id"]})
                            executed = True

                elif panel == "archive":
                    if action == "create":
                        result = _ar_store.create_archive_note(**data)
                        await sio.emit("archive_note_created", result)
                        entity_id = result.get("id")
                        executed = True
                    elif action == "update":
                        nid = data.pop("id")
                        result = _ar_store.update_archive_note(nid, **data)
                        if result:
                            await sio.emit("archive_note_updated", result)
                            entity_id = nid
                            executed = True
                    elif action == "delete":
                        if _ar_store.delete_archive_note(data["id"]):
                            await sio.emit("archive_note_deleted", {"id": data["id"]})
                            executed = True

            except Exception as crud_err:
                print(f"[ACTION ROUTER] CRUD error: {crud_err}")
                await sio.emit('chat_message', {
                    'sender': 'Lumina',
                    'text': f"Hmm, that didn't work — {str(crud_err)}"
                }, room=sid)
                return

            if executed:
                # Update session last_ids
                if entity_id:
                    id_key = {"quests": "quest", "events": "event", "archive": "note"}.get(panel)
                    if id_key:
                        last_ids[id_key] = entity_id
                        sio._ar_last_ids[sid] = last_ids

                # Route confirmation through Gemini LLM for natural voice + TTS
                prompt = _build_action_llm_prompt(meta, mood_state)
                sent = await _send_action_to_llm(prompt, sid)
                if not sent:
                    # Fallback: basic chat_message if no Gemini session
                    title = meta.get("title", "that")
                    at = meta.get("action_type", "done")
                    await sio.emit('chat_message', {
                        'sender': 'Lumina',
                        'text': f"Done — {at} '{title}'."
                    }, room=sid)
                print(f"[ACTION ROUTER] {action} {panel}→LLM")
                return  # CRUD done, Gemini will stream the voice reply
    except ImportError:
        print("[ACTION ROUTER] action_router.py not found — skipping")
    except Exception as ar_err:
        print(f"[ACTION ROUTER] Parse error (non-fatal): {ar_err}")
    
    # ========================================
    # NORMAL MESSAGE FLOW (send to model)
    # ========================================

    if not audio_loop.session:
        # Queue the message instead of dropping it — will be flushed when session is ready
        if not hasattr(audio_loop, '_pending_text_queue'):
            audio_loop._pending_text_queue = []
        audio_loop._pending_text_queue.append((sid, text))
        print(f"[SERVER DEBUG] Session not ready — queued message ({len(audio_loop._pending_text_queue)} pending): '{text[:50]}'")
        await sio.emit('chat_message', {
            'sender': 'System',
            'text': 'Connecting to Gemini... your message is queued.'
        }, room=sid)
        return

    # Flush any previously queued messages first
    if hasattr(audio_loop, '_pending_text_queue') and audio_loop._pending_text_queue:
        queued = audio_loop._pending_text_queue[:]
        audio_loop._pending_text_queue.clear()
        print(f"[SERVER DEBUG] Flushing {len(queued)} queued message(s)")
        for q_sid, q_text in queued:
            # Recursively process queued messages (they will go through full pipeline)
            await user_input(q_sid, {'text': q_text})

    # ========================================
    # MEMORY LIFECYCLE: AUTO-STORE PREFERENCES AS PENDING (no popup)
    # ========================================
    # Preferences/facts detected by extract_memory_candidates are stored
    # directly as state=pending. User confirms via voice/text, not popup.
    if audio_loop and audio_loop.memory_store:
        try:
            candidates = extract_memory_candidates(text, context="user")
            
            if candidates:
                for candidate in candidates:
                    # Check for duplicates
                    existing = audio_loop.memory_store.search_memories(candidate['content'], limit=3)
                    is_duplicate = any(candidate['content'].lower() in m['content'].lower() or 
                                      m['content'].lower() in candidate['content'].lower() 
                                      for m in existing)
                    
                    if not is_duplicate:
                        # Auto-store as pending — no popup, no socket emit
                        mem_id = audio_loop.memory_store.add_memory(
                            memory_type=candidate['type'],
                            content=candidate['content'],
                            metadata={"source": "auto_extract", "reason": candidate['reason']},
                            state="pending",
                            confidence=candidate['confidence'],
                            priority=35,
                        )
                        print(f"[MEMORY DECISION] Auto-stored {candidate['type']} as pending (id={mem_id}): '{candidate['content'][:60]}'")
                        # Track for consent: Lumina will ask via Gemini context injection
                        audio_loop._current_pending_consent_id = mem_id
                        audio_loop._current_pending_consent_content = candidate['content']
                        audio_loop._current_pending_consent_type = candidate['type']
                        _ts = datetime.utcnow().isoformat()
                        await sio.emit('memory_lifecycle_event', {
                            'event': 'pending', 'id': mem_id,
                            'memory_id': mem_id,
                            'type': candidate['type'], 'content': candidate['content'],
                            'ts': _ts
                        }, room=sid)
                    else:
                        print(f"[MEMORY SUGGEST] Skipped duplicate: '{candidate['content'][:50]}'")
                
        except Exception as e:
            print(f"[MEMORY SUGGEST] Error: {e}")
    
    # ========================================
    # MEMORY LIFECYCLE: DETECT INTENTS & ASSUMPTIONS
    # ========================================
    memory_signals = []
    if audio_loop and audio_loop.memory_store and memory_engine:
        try:
            memory_signals = memory_engine.detect_memory_signals(text, audio_loop.memory_store)
            _ts = datetime.utcnow().isoformat()
            for sig in memory_signals:
                # Track for consent (last one wins if multiple, but typically only one per message)
                audio_loop._current_pending_consent_id = sig['id']
                audio_loop._current_pending_consent_content = sig['content']
                audio_loop._current_pending_consent_type = sig['type']
                await sio.emit('memory_lifecycle_event', {
                    'event': 'pending', 'id': sig['id'],
                    'memory_id': sig['id'],
                    'type': sig['type'], 'content': sig['content'],
                    'ts': _ts
                }, room=sid)
        except Exception as e:
            print(f"[MEMORY DECISION] Signal detection error: {e}")

    # ========================================
    # PHASE E5: STORE USER TRANSCRIPT + INDEX
    # ========================================
    current_project = None
    if audio_loop and audio_loop.project_manager:
        current_project = audio_loop.project_manager.current_project
    if memory_engine:
        asyncio.create_task(_index_transcript_bg("user", text, current_project))

    # ========================================
    # MEMORY INJECTION — DISCIPLINED LAYERS (v2)
    # Budget-controlled, topic-aware, no stale resurfacing
    # ========================================
    memory_context = ""
    injected_memory_ids = []
    
    if audio_loop and audio_loop.memory_store:
        try:
            from persona_engine import get_persona_engine as _get_pe, PersonaEngine
            ms = audio_loop.memory_store
            _pe = _get_pe()

            # --- Compute retrieval budget from persona engine ---
            budget = _pe.compute_memory_budget(text) if _pe else dict(PersonaEngine.compute_memory_budget(PersonaEngine.__new__(PersonaEngine), text)) if False else {
                "max_chars": 1300, "max_identity": 4, "max_active_project": 4,
                "max_archived": 0, "max_excerpts": 5, "max_pending": 2,
                "summary_inject_interval": 12, "inject_summary": True, "refs_completed": False,
            }
            if _pe:
                budget = _pe.compute_memory_budget(text)

            _max_chars = budget.get("max_chars", 1300)
            _max_identity = budget.get("max_identity", 4)
            _max_active = budget.get("max_active_project", 4)
            _max_excerpts = budget.get("max_excerpts", 5)
            _max_pending = budget.get("max_pending", 2)
            _inject_summary = budget.get("inject_summary", True)
            _refs_completed = budget.get("refs_completed", False)

            # --- Retrieve data ---
            identity_memories = ms.get_identity_memories()
            session_summary = ms.get_latest_session_summary() if _inject_summary else None
            active_memories = ms.get_active_for_injection(limit=_max_active + 6)  # fetch extra, filter below
            pending_assumptions = ms.get_pending_assumptions(limit=_max_pending)

            hybrid_excerpts = []
            if memory_engine:
                try:
                    # FIX C: Offload hybrid search to thread to avoid blocking ws recv
                    _loop = asyncio.get_event_loop()
                    hybrid_excerpts = await _loop.run_in_executor(
                        None, memory_engine.search_memory_sync, text, _max_excerpts + 3
                    ) if hasattr(memory_engine, 'search_memory_sync') else await memory_engine.search_memory(text, top_k=_max_excerpts + 3)
                except Exception as he:
                    print(f"[MEMORY2] Hybrid search error: {he}")

            revisit_hint = None
            if memory_engine:
                try:
                    stale = memory_engine.get_revisit_candidates(ms)
                    revisit_hint = memory_engine.build_revisit_hint(stale)
                except Exception:
                    pass

            # ---- BUILD PREFIX (compact) ----
            memory_lines = [
                "[MEMORY] Scepter IS the user. Treat as facts. DO NOT mention, repeat, or bring up these memories or past chats unless Scepter's message is directly related to them or explicitly asks about them. Keep casual chat focused entirely on the present.",
                ""
            ]
            _count_identity = 0
            _count_active = 0
            _count_excerpts = 0
            _count_pending = 0
            _count_suppressed = 0
            _summary_injected = False

            # --- A) IDENTITY (always inject, capped) ---
            identity_items = [m for m in identity_memories if any(kw in m['content'].lower() for kw in ['scepter', 'rochak', 'companion', 'owner'])]
            for mem in identity_items[:_max_identity]:
                memory_lines.append(f"- {mem['content']}")
                injected_memory_ids.append(mem['id'])
                _count_identity += 1

            # --- B) ACTIVE PROJECT MEMORY (conditional, suppression-filtered) ---
            identity_ids = {m['id'] for m in identity_items}
            for mem in active_memories:
                if _count_active >= _max_active:
                    break
                if mem['id'] in identity_ids:
                    continue
                # Completed work suppression (FIX E)
                if _pe and _pe.should_suppress_memory(mem['content'], text):
                    _count_suppressed += 1
                    continue
                memory_lines.append(f"- {mem['content']}")
                injected_memory_ids.append(mem['id'])
                ms.mark_used(mem['id'], boost=1)
                _count_active += 1

            # --- C) PENDING ASSUMPTIONS (cautious, capped) ---
            if pending_assumptions:
                for mem in pending_assumptions[:_max_pending]:
                    conf = mem.get('confidence', 0.5)
                    memory_lines.append(f"- (pending, conf={conf:.2f}) {mem['content']}")
                    injected_memory_ids.append(mem['id'])
                    _count_pending += 1

            # --- D) SESSION SUMMARY (throttled) ---
            if session_summary and _inject_summary:
                summary_text = session_summary['content'][:200]
                memory_lines.append(f"- (session) {summary_text}")
                injected_memory_ids.append(session_summary['id'])
                _summary_injected = True
                if _pe:
                    _pe.mark_summary_injected()

            # --- E) HYBRID EXCERPTS (budget-capped, suppression-filtered) ---
            if hybrid_excerpts:
                seen_excerpt_ids = set()
                for exc in hybrid_excerpts:
                    if _count_excerpts >= _max_excerpts:
                        break
                    cid = exc.get("chunk_id")
                    if cid in seen_excerpt_ids:
                        continue
                    seen_excerpt_ids.add(cid)
                    exc_text = exc["text"][:200].replace("\n", " ").strip()
                    # Completed work suppression on excerpts too (FIX E)
                    if _pe and _pe.should_suppress_memory(exc_text, text):
                        _count_suppressed += 1
                        continue
                    memory_lines.append(f"- {exc_text}")
                    _count_excerpts += 1

            memory_lines.append("")

            # --- F) PROJECT CONTEXT (always, 1 line) ---
            proj_name = current_project or "temp"
            memory_lines.append(f"Project: {proj_name}")

            # --- G) REVISIT HINT ---
            if revisit_hint:
                memory_lines.append(revisit_hint)

            # --- H) SIGNAL HINTS ---
            if memory_signals:
                for sig in memory_signals:
                    hint = sig.get("response_hint", "")
                    if hint:
                        memory_lines.append(f"[NOTE] {hint}")

            # --- I) MEMORY CANDIDATE CONSENT ---
            _consent_id = getattr(audio_loop, '_current_pending_consent_id', None)
            _consent_content = getattr(audio_loop, '_current_pending_consent_content', None)
            _consent_type = getattr(audio_loop, '_current_pending_consent_type', None)
            if _consent_id and _consent_content:
                memory_lines.append(f"[CANDIDATE] {_consent_type or 'preference'}: \"{_consent_content[:100]}\"")
                memory_lines.append("At END of reply, briefly ask if you should remember this. Sound natural.")
                print(f"[MEMORY] Consent directive for id={_consent_id}: '{_consent_content[:50]}'")

            # --- J) REVISIT DIRECTIVE ---
            _revisit_id = getattr(audio_loop, '_revisit_target_id', None)
            _revisit_content = getattr(audio_loop, '_revisit_target_content', None)
            if _revisit_id and _revisit_content:
                memory_lines.append(f"[REVISIT] \"{_revisit_content[:100]}\"")
                memory_lines.append("Ask casually if this is still true. No system jargon.")
                print(f"[MEMORY] Revisit directive for id={_revisit_id}: '{_revisit_content[:50]}'")

            # --- HARD CAP on total chars ---
            memory_context = "\n".join(memory_lines) + "\n"
            if len(memory_context) > _max_chars:
                memory_context = memory_context[:_max_chars - 4] + "...\n"

            print(f"[MEMORY] inject identity={_count_identity} active={_count_active} excerpts={_count_excerpts} pending={_count_pending} summary={'yes' if _summary_injected else 'no'} total_chars={len(memory_context)}")
            if _count_suppressed > 0:
                print(f"[MEMORY] suppressed_completed_refs count={_count_suppressed}")

        except Exception as e:
            print(f"[MEMORY] Error retrieving memories: {e}")
            import traceback
            traceback.print_exc()
    
    # Script preprocessing removed — allow natural mixed Nepali/English
    _nepali_directive = ""

    # ========================================
    # PERSONA CONTEXT INJECTION
    # ========================================
    persona_context = ""
    pe = get_persona_engine()
    if pe and pe.enabled:
        try:
            persona_context = pe.build_persona_context(text)
            if persona_context:
                print(f"[PERSONA] Injected {len(persona_context)} chars of persona context (emotion={pe._last_emotion})")
        except Exception as e:
            print(f"[PERSONA] Error building context: {e}")
    
    # Combine memory context + persona context + nepali directive + user text
    full_message = memory_context + persona_context + _nepali_directive + text
    
    memory_inject_time = datetime.utcnow()
    memory_ms = int((memory_inject_time - turn_start_time).total_seconds() * 1000)
    
    print(f"[SERVER DEBUG] Message payload: memory_prefix={len(memory_context)} chars, user_text={len(text)} chars")
    print(f"[SERVER DEBUG] Message role: user (Gemini Live doesn't support separate system messages per turn)")
    
    # Log User Input to Project History
    if audio_loop and audio_loop.project_manager:
        audio_loop.project_manager.log_chat("User", text)
        
    # Use the same 'send' method that worked for audio, as 'send_realtime_input' and 'send_client_content' seem unstable in this env
    # INJECT VIDEO FRAME IF AVAILABLE (VAD-style logic for Text Input)
    if audio_loop and audio_loop._latest_image_payload:
        print(f"[SERVER DEBUG] Piggybacking video frame with text input.")
        try:
            # Send frame first (non-turn-ending)
            await audio_loop.safe_send(audio_loop._latest_image_payload, end_of_turn=False, timeout=5.0)
        except Exception as e:
            print(f"[SERVER DEBUG] Failed to send piggyback frame: {e}")
            
    llm_send_time = datetime.utcnow()
    await audio_loop.safe_send(full_message, end_of_turn=True, timeout=15.0)
    llm_complete_time = datetime.utcnow()
    
    # Phase D.4: Per-turn metrics
    llm_total_ms = int((llm_complete_time - llm_send_time).total_seconds() * 1000)
    total_turn_ms = int((llm_complete_time - turn_start_time).total_seconds() * 1000)
    
    # Socket and model status
    socket_status = 'ok' if sid in connected_clients and connected_clients[sid]['status'] == 'connected' else 'degraded'
    model_status = 'ok'  # If we got here without exception, model accepted the message
    
    print(f"[TURN] memory_ms={memory_ms} llm_total_ms={llm_total_ms} total_ms={total_turn_ms} socket={socket_status} model={model_status}")
    print(f"[SERVER DEBUG] Message sent to model successfully.")

@sio.event
async def video_frame(sid, data):
    # data should contain 'image' which is binary (blob) or base64 encoded
    image_data = data.get('image')
    if image_data and audio_loop:
        # We don't await this because we don't want to block the socket handler
        # But send_frame is async, so we create a task
        asyncio.create_task(audio_loop.send_frame(image_data))

@sio.event
async def save_memory(sid, data):
    try:
        messages = data.get('messages', [])
        if not messages:
            print("No messages to save.")
            return

        # Ensure directory exists
        memory_dir = Path("long_term_memory")
        memory_dir.mkdir(exist_ok=True)

        # Generate filename
        # Use provided filename if available, else timestamp
        provided_name = data.get('filename')
        
        if provided_name:
            # Simple sanitization
            if not provided_name.endswith('.txt'):
                provided_name += '.txt'
            # Prevent directory traversal
            filename = memory_dir / Path(provided_name).name 
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = memory_dir / f"memory_{timestamp}.txt"

        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            for msg in messages:
                sender = msg.get('sender', 'Unknown')
                text = msg.get('text', '')
                f.write(f"[{sender}]: {text}\n")
        print(f"Conversation saved to {filename}")
        await sio.emit('status', {'msg': 'Memory Saved Successfully'})

    except Exception as e:
        print(f"Error saving memory: {e}")
        await sio.emit('error', {'msg': f"Failed to save memory: {str(e)}"})

@sio.event
async def upload_memory(sid, data):
    print(f"Received memory upload request")
    try:
        memory_text = data.get('memory', '')
        if not memory_text:
            print("No memory data provided.")
            return

        if not audio_loop:
             print("[SERVER DEBUG] [Error] Audio loop is None. Cannot load memory.")
             await sio.emit('error', {'msg': "System not ready (Audio Loop inactive)"})
             return
        
        if not audio_loop.session:
             print("[SERVER DEBUG] [Error] Session is None. Cannot load memory.")
             await sio.emit('error', {'msg': "System not ready (No active session)"})
             return

        # Send to model
        print("Sending memory context to model...")
        context_msg = f"System Notification: The user has uploaded a long-term memory file. Please load the following context into your understanding. The format is a text log of previous conversations:\n\n{memory_text}"
        
        await audio_loop.safe_send(context_msg, end_of_turn=True, timeout=15.0)
        print("Memory context sent successfully.")
        await sio.emit('status', {'msg': 'Memory Loaded into Context'})

    except Exception as e:
        print(f"Error uploading memory: {e}")
        await sio.emit('error', {'msg': f"Failed to upload memory: {str(e)}"})

@sio.event
async def process_file(sid, data):
    """Handle file processing requests from the UI (non-memory files)."""
    import asyncio
    file_path = data.get('file_path', '').strip()
    file_name = data.get('file_name', file_path)
    print(f"[SERVER] Received process_file request: {file_name}")

    if not file_path:
        await sio.emit('chat_message', {
            'sender': 'System',
            'text': 'No file path provided.'
        }, room=sid)
        return

    try:
        from actions import ACTION_REGISTRY
        if 'file_processor' not in ACTION_REGISTRY:
            await sio.emit('chat_message', {
                'sender': 'System',
                'text': 'File processor not available.'
            }, room=sid)
            return

        _fp = ACTION_REGISTRY['file_processor']
        result = await asyncio.to_thread(
            _fp,
            {'file_path': file_path},
            None,  # response
            None,  # player
            None,  # session_memory
        )
        await sio.emit('chat_message', {
            'sender': 'Lumina',
            'text': f"📄 **{file_name}**\n\n{result}"
        }, room=sid)
    except Exception as e:
        print(f"[SERVER] process_file error: {e}")
        await sio.emit('chat_message', {
            'sender': 'System',
            'text': f"File processing failed: {e}"
        }, room=sid)

@sio.event
async def discover_kasa(sid):
    print(f"Received discover_kasa request")
    
    # Guard: If tools disabled or kasa_agent is None, return empty
    if not SETTINGS["tool_permissions"].get("list_smart_devices", False) or kasa_agent is None:
        print("[TOOLS] Kasa tools DISABLED - returning empty device list")
        await sio.emit('kasa_devices', [])
        await sio.emit('status', {'msg': 'Kasa tools are disabled'})
        return
    
    try:
        devices = await kasa_agent.discover_devices()
        await sio.emit('kasa_devices', devices)
        await sio.emit('status', {'msg': f"Found {len(devices)} Kasa devices"})
        
        # Save to settings
        # devices is a list of full device info dicts. minimizing for storage.
        saved_devices = []
        for d in devices:
            saved_devices.append({
                "ip": d["ip"],
                "alias": d["alias"],
                "model": d["model"]
            })
        
        # Merge with existing to preserve any manual overrides? 
        # For now, just overwrite with latest scan result + previously known if we want to be fancy,
        # but user asked for "Any new devices that are scanned are added there".
        # A simple full persistence of current state is safest.
        SETTINGS["kasa_devices"] = saved_devices
        save_settings()
        print(f"[SERVER] Saved {len(saved_devices)} Kasa devices to settings.")
        
    except Exception as e:
        print(f"Error discovering kasa: {e}")
        await sio.emit('error', {'msg': f"Kasa Discovery Failed: {str(e)}"})

@sio.event
async def iterate_cad(sid, data):
    # data: { prompt: "make it bigger" }
    prompt = data.get('prompt')
    print(f"Received iterate_cad request: '{prompt}'")
    
    if not audio_loop or not audio_loop.cad_agent:
        await sio.emit('error', {'msg': "CAD Agent not available"})
        return

    try:
        # Notify user work has started
        await sio.emit('status', {'msg': 'Iterating design...'})
        await sio.emit('cad_status', {'status': 'generating'})
        
        # Call the agent with project path
        cad_output_dir = str(audio_loop.project_manager.get_current_project_path() / "cad")
        result = await audio_loop.cad_agent.iterate_prototype(prompt, output_dir=cad_output_dir)
        
        if result:
            info = f"{len(result.get('data', ''))} bytes (STL)"
            print(f"Sending updated CAD data: {info}")
            await sio.emit('cad_data', result)
            # Save to Project
            if 'file_path' in result:
                saved_path = audio_loop.project_manager.save_cad_artifact(result['file_path'], prompt)
                if saved_path:
                    print(f"[SERVER] Saved iterated CAD to {saved_path}")

            await sio.emit('status', {'msg': 'Design updated'})
        else:
            await sio.emit('error', {'msg': 'Failed to update design'})
            
    except Exception as e:
        print(f"Error iterating CAD: {e}")
        await sio.emit('error', {'msg': f"Iteration Error: {str(e)}"})

@sio.event
async def generate_cad(sid, data):
    # data: { prompt: "make a cube" }
    prompt = data.get('prompt')
    print(f"Received generate_cad request: '{prompt}'")
    
    if not audio_loop or not audio_loop.cad_agent:
        await sio.emit('error', {'msg': "CAD Agent not available"})
        return

    try:
        await sio.emit('status', {'msg': 'Generating new design...'})
        await sio.emit('cad_status', {'status': 'generating'})
        
        # Use generate_prototype based on prompt with project path
        cad_output_dir = str(audio_loop.project_manager.get_current_project_path() / "cad")
        result = await audio_loop.cad_agent.generate_prototype(prompt, output_dir=cad_output_dir)
        
        if result:
            info = f"{len(result.get('data', ''))} bytes (STL)"
            print(f"Sending newly generated CAD data: {info}")
            await sio.emit('cad_data', result)


            # Save to Project
            if 'file_path' in result:
                saved_path = audio_loop.project_manager.save_cad_artifact(result['file_path'], prompt)
                if saved_path:
                    print(f"[SERVER] Saved generated CAD to {saved_path}")

            await sio.emit('status', {'msg': 'Design generated'})
        else:
            await sio.emit('error', {'msg': 'Failed to generate design'})
            
    except Exception as e:
        print(f"Error generating CAD: {e}")
        await sio.emit('error', {'msg': f"Generation Error: {str(e)}"})

@sio.event
async def prompt_web_agent(sid, data):
    # data: { prompt: "find xyz" }
    prompt = data.get('prompt')
    print(f"Received web agent prompt: '{prompt}'")
    
    if not audio_loop or not audio_loop.web_agent:
        await sio.emit('error', {'msg': "Web Agent not available"})
        return

    try:
        await sio.emit('status', {'msg': 'Web Agent running...'})
        
        # We assume web_agent has a run method or similar.
        # This might block the loop if not strictly async or offloaded.
        # Ideally web_agent.run is async.
        # And it should emit 'browser_snap' and logs automatically via hooks if setup.
        
        # We might need to launch this as a task if it's long running?
        # asyncio.create_task(audio_loop.web_agent.run(prompt))
        # But we want to catch errors here.
        
        # Based on typical agent design, run() is the entry point.
        await audio_loop.web_agent.run(prompt)
        
        await sio.emit('status', {'msg': 'Web Agent finished'})
        
    except Exception as e:
        print(f"Error running Web Agent: {e}")
        await sio.emit('error', {'msg': f"Web Agent Error: {str(e)}"})

@sio.event
async def discover_printers(sid):
    print("Received discover_printers request")
    
    # Guard: If tools disabled, return empty
    if not SETTINGS["tool_permissions"].get("discover_printers", False):
        print("[TOOLS] Printer tools DISABLED - returning empty printer list")
        await sio.emit('printer_list', [])
        await sio.emit('status', {'msg': 'Printer tools are disabled'})
        return
    
    # If audio_loop isn't ready yet, return saved printers from settings
    if not audio_loop or not audio_loop.printer_agent:
        saved_printers = SETTINGS.get("printers", [])
        if saved_printers:
            # Convert saved printers to the expected format
            printer_list = []
            for p in saved_printers:
                printer_list.append({
                    "name": p.get("name", p["host"]),
                    "host": p["host"],
                    "port": p.get("port", 80),
                    "printer_type": p.get("type", "unknown"),
                    "camera_url": p.get("camera_url")
                })
            print(f"[SERVER] Returning {len(printer_list)} saved printers (audio_loop not ready)")
            await sio.emit('printer_list', printer_list)
            return
        else:
            await sio.emit('printer_list', [])
            await sio.emit('status', {'msg': "Connect to Lumina to enable printer discovery"})
            return
        
    try:
        printers = await audio_loop.printer_agent.discover_printers()
        await sio.emit('printer_list', printers)
        await sio.emit('status', {'msg': f"Found {len(printers)} printers"})
    except Exception as e:
        print(f"Error discovering printers: {e}")
        await sio.emit('error', {'msg': f"Printer Discovery Failed: {str(e)}"})

@sio.event
async def add_printer(sid, data):
    # data: { host: "192.168.1.50", name: "My Printer", type: "moonraker" }
    raw_host = data.get('host')
    name = data.get('name') or raw_host
    ptype = data.get('type', "moonraker")
    
    # Parse port if present
    if ":" in raw_host:
        host, port_str = raw_host.split(":")
        port = int(port_str)
    else:
        host = raw_host
        port = 80
    
    print(f"Received add_printer request: {host}:{port} ({ptype})")
    
    if not audio_loop or not audio_loop.printer_agent:
        await sio.emit('error', {'msg': "Printer Agent not available"})
        return
        
    try:
        # Add manually
        camera_url = data.get('camera_url')
        printer = audio_loop.printer_agent.add_printer_manually(name, host, port=port, printer_type=ptype, camera_url=camera_url)
        
        # Save to settings
        new_printer_config = {
            "name": name,
            "host": host,
            "port": port,
            "type": ptype,
            "camera_url": camera_url
        }
        
        # Check if already exists to avoid duplicates
        exists = False
        for p in SETTINGS.get("printers", []):
            if p["host"] == host and p["port"] == port:
                exists = True
                break
        
        if not exists:
            if "printers" not in SETTINGS:
                SETTINGS["printers"] = []
            SETTINGS["printers"].append(new_printer_config)
            save_settings()
            print(f"[SERVER] Saved printer {name} to settings.")
        
        # Probe to confirm/correct type
        print(f"Probing {host} to confirm type...")
        # Try port 7125 (Moonraker) and 4408 (Fluidd/K1) 
        ports_to_try = [80, 7125, 4408]
        
        actual_type = "unknown"
        for port in ports_to_try:
             found_type = await audio_loop.printer_agent._probe_printer_type(host, port)
             if found_type.value != "unknown":
                 actual_type = found_type
                 # Update port if different
                 if port != 80:
                     printer.port = port
                 break
        
        if actual_type != "unknown" and actual_type != printer.printer_type:
             printer.printer_type = actual_type
             print(f"Corrected type to {actual_type.value} on port {printer.port}")
             
        # Refresh list for everyone
        printers = [p.to_dict() for p in audio_loop.printer_agent.printers.values()]
        await sio.emit('printer_list', printers)
        await sio.emit('status', {'msg': f"Added printer: {name}"})
        
    except Exception as e:
        print(f"Error adding printer: {e}")
        await sio.emit('error', {'msg': f"Failed to add printer: {str(e)}"})

@sio.event
async def print_stl(sid, data):
    print(f"Received print_stl request: {data}")
    # data: { stl_path: "path/to.stl" | "current", printer: "name_or_ip", profile: "optional" }
    
    # Guard: If tools disabled, return error
    if not SETTINGS["tool_permissions"].get("print_stl", False):
        print("[TOOLS] Print tools DISABLED - ignoring print_stl request")
        await sio.emit('error', {'msg': 'Print tools are disabled'})
        return
    
    if not audio_loop or not audio_loop.printer_agent:
        await sio.emit('error', {'msg': "Printer Agent not available"})
        return
        
    try:
        stl_path = data.get('stl_path', 'current')
        printer_name = data.get('printer')
        profile = data.get('profile')
        
        if not printer_name:
             await sio.emit('error', {'msg': "No printer specified"})
             return
             
        await sio.emit('status', {'msg': f"Preparing print for {printer_name}..."})
        
        # Get current project path for resolution
        current_project_path = None
        if audio_loop and audio_loop.project_manager:
            current_project_path = str(audio_loop.project_manager.get_current_project_path())
            print(f"[SERVER DEBUG] Using project path: {current_project_path}")

        # Resolve STL path before slicing so we can preview it
        resolved_stl = audio_loop.printer_agent._resolve_file_path(stl_path, current_project_path)
        
        if resolved_stl and os.path.exists(resolved_stl):
            # Open the STL in the CAD module for preview
            try:
                import base64
                with open(resolved_stl, 'rb') as f:
                    stl_data = f.read()
                stl_b64 = base64.b64encode(stl_data).decode('utf-8')
                stl_filename = os.path.basename(resolved_stl)
                
                print(f"[SERVER] Opening STL in CAD module: {stl_filename}")
                await sio.emit('cad_data', {
                    'format': 'stl',
                    'data': stl_b64,
                    'filename': stl_filename
                })
            except Exception as e:
                print(f"[SERVER] Warning: Could not preview STL: {e}")
        
        # Progress Callback
        async def on_slicing_progress(percent, message):
            await sio.emit('slicing_progress', {
                'printer': printer_name,
                'percent': percent,
                'message': message
            })
            if percent < 100:
                 await sio.emit('status', {'msg': f"Slicing: {percent}%"})

        result = await audio_loop.printer_agent.print_stl(
            stl_path, 
            printer_name, 
            profile,
            progress_callback=on_slicing_progress,
            root_path=current_project_path
        )
        
        await sio.emit('print_result', result)
        await sio.emit('status', {'msg': f"Print Job: {result.get('status', 'unknown')}"})
        
    except Exception as e:
        print(f"Error printing STL: {e}")
        await sio.emit('error', {'msg': f"Print Failed: {str(e)}"})

@sio.event
async def get_slicer_profiles(sid):
    """Get available OrcaSlicer profiles for manual selection."""
    print("Received get_slicer_profiles request")
    if not audio_loop or not audio_loop.printer_agent:
        await sio.emit('error', {'msg': "Printer Agent not available"})
        return
    
    try:
        profiles = audio_loop.printer_agent.get_available_profiles()
        await sio.emit('slicer_profiles', profiles)
    except Exception as e:
        print(f"Error getting slicer profiles: {e}")
        await sio.emit('error', {'msg': f"Failed to get profiles: {str(e)}"})

@sio.event
async def control_kasa(sid, data):
    # data: { ip, action: "on"|"off"|"brightness"|"color", value: ... }
    ip = data.get('ip')
    action = data.get('action')
    print(f"Kasa Control: {ip} -> {action}")
    
    # Guard: If tools disabled or kasa_agent is None, return error
    if not SETTINGS["tool_permissions"].get("control_light", False) or kasa_agent is None:
        print("[TOOLS] Kasa control DISABLED - ignoring control_kasa request")
        await sio.emit('error', {'msg': 'Kasa tools are disabled'})
        return
    
    try:
        success = False
        if action == "on":
            success = await kasa_agent.turn_on(ip)
        elif action == "off":
            success = await kasa_agent.turn_off(ip)
        elif action == "brightness":
            val = data.get('value')
            success = await kasa_agent.set_brightness(ip, val)
        elif action == "color":
            # value is {h, s, v} - convert to tuple for set_color
            h = data.get('value', {}).get('h', 0)
            s = data.get('value', {}).get('s', 100)
            v = data.get('value', {}).get('v', 100)
            success = await kasa_agent.set_color(ip, (h, s, v))
        
        if success:
            await sio.emit('kasa_update', {
                'ip': ip,
                'is_on': True if action == "on" else (False if action == "off" else None),
                'brightness': data.get('value') if action == "brightness" else None,
            })
 
        else:
             await sio.emit('error', {'msg': f"Failed to control device {ip}"})

    except Exception as e:
         print(f"Error controlling kasa: {e}")
         await sio.emit('error', {'msg': f"Kasa Control Error: {str(e)}"})

@sio.event
async def get_settings(sid):
    payload = dict(SETTINGS)
    payload["_tool_clamp_mode"] = _clamp_mode
    payload["_tool_clamp_allowlist"] = sorted(_clamp_allowlist) if _clamp_allowlist else []
    
    # Add remote pairing info if dashboard is available
    try:
        from dashboard_routes import get_dashboard_server
        db = get_dashboard_server()
        if db:
            key = db.new_key()
            url = db.get_url()
            payload["remote_pairing"] = {
                "pin": key,
                "url": url,
                "qr_url": f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={url}/auto-login?key={key}",
                "manual_url": db.get_manual_url()
            }
    except Exception as e:
        print(f"[SERVER] Remote pairing info error: {e}")

    await sio.emit('settings', payload)

@sio.event
async def update_settings(sid, data):
    # Generic update
    print(f"Updating settings: {data}")
    
    # Handle specific keys if needed
    if "tool_permissions" in data:
        SETTINGS["tool_permissions"].update(data["tool_permissions"])
        _reapply_tool_clamp()  # Protect clamp-enforced values
        if audio_loop:
            audio_loop.update_permissions(SETTINGS["tool_permissions"])
            
    if "face_auth_enabled" in data:
        SETTINGS["face_auth_enabled"] = data["face_auth_enabled"]
        # If turned OFF, maybe emit auth status true?
        if not data["face_auth_enabled"]:
             await sio.emit('auth_status', {'authenticated': True})
             # Stop auth loop if running?
             if authenticator:
                 authenticator.stop() 

    if "camera_flipped" in data:
        SETTINGS["camera_flipped"] = data["camera_flipped"]
        print(f"[SERVER] Camera flip set to: {data['camera_flipped']}")

    if "browser_confirmation_mode" in data:
        mode = data["browser_confirmation_mode"]
        if mode in ("strict", "relaxed", "off"):
            SETTINGS["browser_confirmation_mode"] = mode
            if audio_loop:
                audio_loop.set_browser_confirmation_mode(mode)
            print(f"[SERVER] browser_confirmation_mode set to: {mode}")
        else:
            print(f"[SERVER] Invalid browser_confirmation_mode: {mode}")

    # Persona settings sync
    _persona_keys = [
        "persona_enabled", "persona_mode", "persona_teasing_intensity",
        "persona_idle_enabled", "persona_idle_timeout_s", "persona_idle_min_gap_s",
        "persona_strict_sensitivity", "persona_adaptive_mode",
    ]
    _persona_changed = False
    for pk in _persona_keys:
        if pk in data:
            SETTINGS[pk] = data[pk]
            _persona_changed = True
    if _persona_changed:
        pe = get_persona_engine()
        if pe:
            pe.update_settings(SETTINGS)
        print(f"[SERVER] Persona settings updated")

    save_settings()
    # Broadcast new full settings (include clamp metadata for UI)
    payload = dict(SETTINGS)
    payload["_tool_clamp_mode"] = _clamp_mode
    payload["_tool_clamp_allowlist"] = sorted(_clamp_allowlist) if _clamp_allowlist else []
    await sio.emit('settings', payload)


@sio.event
async def revoke_remote_devices(sid):
    try:
        from dashboard_routes import get_dashboard_server
        db = get_dashboard_server()
        if db:
            count = len(db._device_sessions)
            db._device_sessions.clear()
            db._tokens.clear()
            db._token_keys.clear()
            print(f"[SERVER] Revoked {count} remote control devices.")
            await sio.emit('remote_revoked', {'count': count})
    except Exception as e:
        print(f"[SERVER] Error revoking devices: {e}")


# Deprecated/Mapped for compatibility if frontend still uses specific events
@sio.event
async def get_tool_permissions(sid):
    await sio.emit('tool_permissions', SETTINGS["tool_permissions"])

@sio.event
async def update_tool_permissions(sid, data):
    print(f"Updating permissions (legacy event): {data}")
    SETTINGS["tool_permissions"].update(data)
    _reapply_tool_clamp()  # Protect clamp-enforced values
    save_settings()
    
    if audio_loop:
        audio_loop.update_permissions(SETTINGS["tool_permissions"])
    # Broadcast update to all
    await sio.emit('tool_permissions', SETTINGS["tool_permissions"])

# ========================================
# EMERGENCY KILL SWITCH
# ========================================
@sio.event
async def kill_browser_tools(sid):
    """Emergency kill switch — instantly disable all browser tools for session."""
    SETTINGS["tool_permissions"]["local_browser_control"] = False
    SETTINGS["tool_permissions"]["browser_control"] = False
    _reapply_tool_clamp()
    save_settings()
    if audio_loop:
        audio_loop.update_permissions(SETTINGS["tool_permissions"])
    await sio.emit('settings', SETTINGS)
    print("[SERVER] EMERGENCY: All browser tools killed by user")

# ========================================
# PANEL CRUD: Quests, Events, Archive Notes
# Uses the same lumina_memory.db via audio_loop.memory_store
# ========================================

_fallback_memory_store = None  # cached fallback — avoids repeated construction

def _get_memory_store():
    """Get the MemoryStore instance from audio_loop, or create a standalone one."""
    global _fallback_memory_store
    if audio_loop and audio_loop.memory_store:
        return audio_loop.memory_store
    # Fallback: create once and cache (tables already exist from init)
    if _fallback_memory_store is None:
        import os
        from memory_store import MemoryStore
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lumina_memory.db")
        _fallback_memory_store = MemoryStore(db_path)
    return _fallback_memory_store

@sio.event
async def list_quests(sid, data=None):
    store = _get_memory_store()
    status_filter = data.get("status") if data else None
    quests = store.list_quests(status_filter)
    await sio.emit("quests_list", quests, to=sid)

@sio.event
async def create_quest(sid, data):
    store = _get_memory_store()
    try:
        quest = store.create_quest(
            title=data.get("title", "Untitled Quest"),
            description=data.get("description", ""),
            priority=data.get("priority", "medium"),
            status=data.get("status", "active"),
        )
        await sio.emit("quest_created", quest)
    except Exception as e:
        print(f"[PANEL] create_quest error: {e}")
        await sio.emit("panel_error", {"panel": "quests", "error": str(e)}, to=sid)

@sio.event
async def update_quest(sid, data):
    store = _get_memory_store()
    quest_id = data.pop("id", None)
    if not quest_id:
        await sio.emit("panel_error", {"panel": "quests", "error": "Missing id"}, to=sid)
        return
    try:
        updated = store.update_quest(quest_id, **data)
        if updated:
            await sio.emit("quest_updated", updated)
        else:
            await sio.emit("panel_error", {"panel": "quests", "error": "Not found"}, to=sid)
    except Exception as e:
        print(f"[PANEL] update_quest error: {e}")
        await sio.emit("panel_error", {"panel": "quests", "error": str(e)}, to=sid)

@sio.event
async def delete_quest(sid, data):
    store = _get_memory_store()
    quest_id = data.get("id")
    if quest_id and store.delete_quest(quest_id):
        await sio.emit("quest_deleted", {"id": quest_id})
    else:
        await sio.emit("panel_error", {"panel": "quests", "error": "Not found"}, to=sid)

@sio.event
async def list_events(sid, data=None):
    store = _get_memory_store()
    events = store.list_events()
    await sio.emit("events_list", events, to=sid)

@sio.event
async def create_event(sid, data):
    store = _get_memory_store()
    try:
        event = store.create_event(
            title=data.get("title", "Untitled Event"),
            dt=data.get("datetime", ""),
            notes=data.get("notes", ""),
        )
        await sio.emit("event_created", event)
    except Exception as e:
        print(f"[PANEL] create_event error: {e}")
        await sio.emit("panel_error", {"panel": "events", "error": str(e)}, to=sid)

@sio.event
async def update_event(sid, data):
    store = _get_memory_store()
    event_id = data.pop("id", None)
    if not event_id:
        await sio.emit("panel_error", {"panel": "events", "error": "Missing id"}, to=sid)
        return
    try:
        updated = store.update_event(event_id, **data)
        if updated:
            await sio.emit("event_updated", updated)
        else:
            await sio.emit("panel_error", {"panel": "events", "error": "Not found"}, to=sid)
    except Exception as e:
        print(f"[PANEL] update_event error: {e}")
        await sio.emit("panel_error", {"panel": "events", "error": str(e)}, to=sid)

@sio.event
async def delete_event(sid, data):
    store = _get_memory_store()
    event_id = data.get("id")
    if event_id and store.delete_event(event_id):
        await sio.emit("event_deleted", {"id": event_id})
    else:
        await sio.emit("panel_error", {"panel": "events", "error": "Not found"}, to=sid)

@sio.event
async def list_archive_notes(sid, data=None):
    store = _get_memory_store()
    tag_filter = data.get("tag") if data else None
    notes = store.list_archive_notes(tag_filter)
    await sio.emit("archive_notes_list", notes, to=sid)

@sio.event
async def create_archive_note(sid, data):
    store = _get_memory_store()
    try:
        note = store.create_archive_note(
            title=data.get("title", "Untitled Note"),
            body=data.get("body", ""),
            tags=data.get("tags", ""),
        )
        await sio.emit("archive_note_created", note)
    except Exception as e:
        print(f"[PANEL] create_archive_note error: {e}")
        await sio.emit("panel_error", {"panel": "archive", "error": str(e)}, to=sid)

@sio.event
async def update_archive_note(sid, data):
    store = _get_memory_store()
    note_id = data.pop("id", None)
    if not note_id:
        await sio.emit("panel_error", {"panel": "archive", "error": "Missing id"}, to=sid)
        return
    try:
        updated = store.update_archive_note(note_id, **data)
        if updated:
            await sio.emit("archive_note_updated", updated)
        else:
            await sio.emit("panel_error", {"panel": "archive", "error": "Not found"}, to=sid)
    except Exception as e:
        print(f"[PANEL] update_archive_note error: {e}")
        await sio.emit("panel_error", {"panel": "archive", "error": str(e)}, to=sid)

@sio.event
async def delete_archive_note(sid, data):
    store = _get_memory_store()
    note_id = data.get("id")
    if note_id and store.delete_archive_note(note_id):
        await sio.emit("archive_note_deleted", {"id": note_id})
    else:
        await sio.emit("panel_error", {"panel": "archive", "error": "Not found"}, to=sid)

# ========================================
# ALARM DISMISS FOLLOW-UP (via Gemini LLM)
# ========================================

@sio.event
async def reminder_alarm_dismissed(sid, data):
    """Handle user dismissing the alarm overlay. Route follow-up through Gemini."""
    event_id = data.get("event_id")
    title = data.get("title", "that reminder")
    try:
        # Update session last_ids so "that event/reminder" works
        if not hasattr(sio, '_ar_last_ids'):
            sio._ar_last_ids = {}
        last_ids = sio._ar_last_ids.get(sid, {"quest": None, "event": None, "note": None})
        if event_id:
            last_ids["event"] = event_id
            sio._ar_last_ids[sid] = last_ids

        # Mark event completed + broadcast panel update
        try:
            store = _get_memory_store()
            updated = store.update_event(event_id, completed=1)
            if updated:
                await sio.emit("event_updated", updated)
        except Exception:
            pass

        # Route follow-up through Gemini for natural voice + TTS
        mood = _get_mood(sid)
        prompt = _build_alarm_dismiss_llm_prompt(title, mood)
        sent = await _send_action_to_llm(prompt, sid)
        if not sent:
            # Fallback if no Gemini session
            await sio.emit('chat_message', {
                'sender': 'Lumina',
                'text': f"Did you handle '{title}'? I can remind you again if not."
            }, room=sid)
        print(f"[ALARM] Dismiss→LLM for event_id={event_id} title={title}")
    except Exception as e:
        print(f"[ALARM] Dismiss handler error: {e}")

# ========================================
# PASSIVE MEMORY ENDPOINTS
# ========================================

@sio.event
async def memory_decision(sid, data):
    """
    Handle user decision on memory suggestion (Phase E2).
    
    Expected data: {
        "temp_id": "uuid-string",
        "accept": true/false
    }
    """
    global pending_memory_suggestions
    
    temp_id = data.get('temp_id')
    accept = data.get('accept', False)
    
    if not temp_id:
        print("[MEMORY DECISION] Error: No temp_id provided")
        return
    
    # Check if suggestion exists
    if temp_id not in pending_memory_suggestions:
        print(f"[MEMORY DECISION] Error: Unknown temp_id: {temp_id}")
        await sio.emit('chat_message', {
            'sender': 'System',
            'text': '❌ Memory suggestion expired or not found'
        }, room=sid)
        return
    
    suggestion = pending_memory_suggestions[temp_id]
    
    if accept:
        # User approved - save to database
        try:
            if audio_loop and audio_loop.memory_store:
                memory_id = audio_loop.memory_store.add_memory(
                    suggestion['type'],
                    suggestion['content']
                )
                
                # Confirm to user
                await sio.emit('chat_message', {
                    'sender': 'System',
                    'text': f"✅ Memory saved: {suggestion['content']}"
                }, room=sid)
                
                print(f"[MEMORY DECISION] ACCEPTED: {suggestion['type']} - '{suggestion['content'][:50]}...' (ID: {memory_id})")
            else:
                await sio.emit('chat_message', {
                    'sender': 'System',
                    'text': '❌ Memory store not available'
                }, room=sid)
        except Exception as e:
            print(f"[MEMORY DECISION] Error saving memory: {e}")
            await sio.emit('chat_message', {
                'sender': 'System',
                'text': f'❌ Failed to save memory: {str(e)}'
            }, room=sid)
    else:
        # User rejected - just log and discard
        print(f"[MEMORY DECISION] REJECTED: {suggestion['type']} - '{suggestion['content'][:50]}...'")
        await sio.emit('chat_message', {
            'sender': 'System',
            'text': '🗑️ Memory suggestion discarded'
        }, room=sid)
    
    # Remove from pending suggestions
    del pending_memory_suggestions[temp_id]

@sio.event
async def add_memory(sid, data):
    """
    Add a new memory entry.
    
    Expected data: {
        "type": "fact" | "preference" | "conversation_summary",
        "content": "memory content string",
        "metadata": {...} (optional)
    }
    """
    if not audio_loop or not audio_loop.memory_store:
        await sio.emit('error', {'msg': "Memory store not available"})
        return
    
    try:
        memory_type = data.get('type')
        content = data.get('content')
        metadata = data.get('metadata')
        
        if not memory_type or not content:
            await sio.emit('error', {'msg': "Missing type or content"})
            return
        
        memory_id = audio_loop.memory_store.add_memory(memory_type, content, metadata)
        await sio.emit('memory_added', {'id': memory_id, 'type': memory_type, 'content': content})
        print(f"[SERVER] Memory added: {memory_type} - {content[:50]}")
        
    except Exception as e:
        print(f"Error adding memory: {e}")
        await sio.emit('error', {'msg': f"Failed to add memory: {str(e)}"})

@sio.event
async def get_memories(sid, data=None):
    """
    Get memories, optionally filtered by type.
    
    Expected data: {
        "type": "fact" | "preference" | "conversation_summary" (optional),
        "limit": 10 (optional)
    }
    """
    if not audio_loop or not audio_loop.memory_store:
        await sio.emit('error', {'msg': "Memory store not available"})
        return
    
    try:
        memory_type = data.get('type') if data else None
        limit = data.get('limit', 10) if data else 10
        
        memories = audio_loop.memory_store.get_memories(memory_type, limit, update_access=False)
        await sio.emit('memories', {'memories': memories})
        
    except Exception as e:
        print(f"Error getting memories: {e}")
        await sio.emit('error', {'msg': f"Failed to get memories: {str(e)}"})

@sio.event
async def get_memory_stats(sid):
    """Get memory store statistics."""
    if not audio_loop or not audio_loop.memory_store:
        await sio.emit('error', {'msg': "Memory store not available"})
        return
    
    try:
        stats = audio_loop.memory_store.get_stats()
        await sio.emit('memory_stats', stats)
        
    except Exception as e:
        print(f"Error getting memory stats: {e}")
        await sio.emit('error', {'msg': f"Failed to get stats: {str(e)}"})

"""
========================================
PHASE E5 MANUAL TEST CHECKLIST
========================================
See Manual Verification section in Phase E5 commit / task description.
========================================
"""

# ========================================
# PHASE E5: MEMORY ENGINE v2 REST ENDPOINTS
# ========================================

@app.get("/memory/status")
async def memory_status():
    """Return memory engine status + lifecycle state counts."""
    status = {}
    if memory_engine:
        status = memory_engine.get_status()
    else:
        status["error"] = "Memory engine not initialized"
    # Add MemoryStore state counts if available
    if audio_loop and audio_loop.memory_store:
        try:
            store_stats = audio_loop.memory_store.get_stats()
            status["by_state"] = store_stats.get("by_state", {})
            status["by_type"] = store_stats.get("by_type", {})
            status["total_memories"] = store_stats.get("total_memories", 0)
        except Exception:
            pass
    return status

@app.get("/memory/search")
async def memory_search_get():
    """GET hint: tell user to use POST with example."""
    return JSONResponse({
        "error": "Use POST /memory/search with JSON body",
        "example": {
            "method": "POST",
            "url": "/memory/search",
            "headers": {"Content-Type": "application/json"},
            "body": {"query": "dark mode", "top_k": 8}
        },
        "curl": 'Invoke-RestMethod -Method POST -Uri http://127.0.0.1:8000/memory/search -ContentType "application/json" -Body \'{"query":"dark mode","top_k":8}\''
    }, status_code=405)

@app.post("/memory/search")
async def memory_search(request: Request):
    """Hybrid memory search. Body: {"query": "...", "top_k": 8}"""
    if not memory_engine:
        return JSONResponse({"error": "Memory engine not initialized"}, status_code=503)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
    query = body.get("query", "").strip()
    if not query:
        return JSONResponse({"error": "Missing 'query' field"}, status_code=400)
    top_k = min(int(body.get("top_k", 8)), 20)
    results = await memory_engine.search_memory(query, top_k=top_k)
    return {"query": query, "top_k": top_k, "results": results, "count": len(results)}

@app.post("/memory/reindex")
async def memory_reindex():
    """Reindex all memories and transcripts. Safe + idempotent."""
    if not memory_engine:
        return JSONResponse({"error": "Memory engine not initialized"}, status_code=503)
    counts = await memory_engine.reindex_all()
    return {"status": "ok", "counts": counts}

# ========================================
# MEMORY LIFECYCLE DEBUG ENDPOINTS
# ========================================

@app.get("/memory/pending")
async def memory_pending():
    """List pending memories (last 20) with full lifecycle fields."""
    if not audio_loop or not audio_loop.memory_store:
        return JSONResponse({"error": "Memory store not available"}, status_code=503)
    pending = audio_loop.memory_store.get_by_state("pending", limit=20)
    return {"count": len(pending), "memories": pending}

@app.post("/memory/confirm")
async def memory_confirm_endpoint(request: Request):
    """Promote a pending memory to active. Body: {"id": <int>}"""
    if not audio_loop or not audio_loop.memory_store:
        return JSONResponse({"error": "Memory store not available"}, status_code=503)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
    mem_id = body.get("id")
    if not mem_id:
        return JSONResponse({"error": "Missing 'id' field"}, status_code=400)
    ok = audio_loop.memory_store.promote_memory(int(mem_id), new_state="active", confidence=1.0)
    if ok:
        print(f"[MEMORY DECISION] REST confirmed pending->active id={mem_id}")
        return {"status": "promoted", "id": mem_id, "new_state": "active"}
    return JSONResponse({"error": f"Memory {mem_id} not found or already active"}, status_code=404)

@app.post("/memory/deny")
async def memory_deny_endpoint(request: Request):
    """Demote a pending memory to dormant. Body: {"id": <int>}"""
    if not audio_loop or not audio_loop.memory_store:
        return JSONResponse({"error": "Memory store not available"}, status_code=503)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
    mem_id = body.get("id")
    if not mem_id:
        return JSONResponse({"error": "Missing 'id' field"}, status_code=400)
    ok = audio_loop.memory_store.demote_memory(int(mem_id), new_state="dormant")
    if ok:
        print(f"[MEMORY DECISION] REST denied pending->dormant id={mem_id}")
        return {"status": "demoted", "id": mem_id, "new_state": "dormant"}
    return JSONResponse({"error": f"Memory {mem_id} not found or already dormant"}, status_code=404)

if __name__ == "__main__":
    print("\n" + "="*70)
    print("[MEMORY LIFECYCLE] Endpoints:")
    print("  GET  /memory/status   — counts + state breakdown")
    print("  GET  /memory/pending  — list pending memories")
    print("  POST /memory/search   — hybrid search {query, top_k}")
    print("  POST /memory/confirm  — promote pending->active {id}")
    print("  POST /memory/deny     — demote pending->dormant {id}")
    print("  POST /memory/reindex  — reindex all")
    print("="*70 + "\n")
    
    uvicorn.run(
        "server:app_socketio", 
        host="0.0.0.0", 
        port=8000, 
        reload=False, # Reload enabled causes spawn of worker which might miss the event loop policy patch
        loop="asyncio",
        reload_excludes=["temp_cad_gen.py", "output.stl", "*.stl"]
    )
