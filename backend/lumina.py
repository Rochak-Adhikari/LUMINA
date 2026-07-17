import asyncio
import base64
import io
import os
import sys
import traceback
from dotenv import load_dotenv
import cv2
import pyaudio
import PIL.Image
import mss
import argparse
import math
import struct
import time

from google import genai
from google.genai import types

if sys.version_info < (3, 11, 0):
    import taskgroup, exceptiongroup
    asyncio.TaskGroup = taskgroup.TaskGroup
    asyncio.ExceptionGroup = exceptiongroup.ExceptionGroup

from tools import tools_list
from actions import ACTION_REGISTRY  # Phase M: Mark-XXX integrated actions
from core.registry import ToolDispatcherRegistry
from core.runtime_facade import RuntimeFacade
from core.container import container


FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
DEFAULT_MODE = "camera"

load_dotenv()
client = genai.Client(http_options={"api_version": "v1beta"}, api_key=os.getenv("GEMINI_API_KEY"))

# Function definitions
generate_cad = {
    "name": "generate_cad",
    "description": "Generates a 3D CAD model based on a prompt.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The description of the object to generate."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

run_web_agent = {
    "name": "run_web_agent",
    "description": "Opens a web browser and performs a task according to the prompt.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The detailed instructions for the web browser agent."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

create_project_tool = {
    "name": "create_project",
    "description": "Creates a new project folder to organize files.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The name of the new project."}
        },
        "required": ["name"]
    }
}

switch_project_tool = {
    "name": "switch_project",
    "description": "Switches the current active project context.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The name of the project to switch to."}
        },
        "required": ["name"]
    }
}

list_projects_tool = {
    "name": "list_projects",
    "description": "Lists all available projects.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

list_smart_devices_tool = {
    "name": "list_smart_devices",
    "description": "Lists all available smart home devices (lights, plugs, etc.) on the network.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

control_light_tool = {
    "name": "control_light",
    "description": "Controls a smart light device.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "target": {
                "type": "STRING",
                "description": "The IP address of the device to control. Always prefer the IP address over the alias for reliability."
            },
            "action": {
                "type": "STRING",
                "description": "The action to perform: 'turn_on', 'turn_off', or 'set'."
            },
            "brightness": {
                "type": "INTEGER",
                "description": "Optional brightness level (0-100)."
            },
            "color": {
                "type": "STRING",
                "description": "Optional color name (e.g., 'red', 'cool white') or 'warm'."
            }
        },
        "required": ["target", "action"]
    }
}

discover_printers_tool = {
    "name": "discover_printers",
    "description": "Discovers 3D printers available on the local network.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

print_stl_tool = {
    "name": "print_stl",
    "description": "Prints an STL file to a 3D printer. Handles slicing the STL to G-code and uploading to the printer.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "stl_path": {"type": "STRING", "description": "Path to STL file, or 'current' for the most recent CAD model."},
            "printer": {"type": "STRING", "description": "Printer name or IP address."},
            "profile": {"type": "STRING", "description": "Optional slicer profile name."}
        },
        "required": ["stl_path", "printer"]
    }
}

get_print_status_tool = {
    "name": "get_print_status",
    "description": "Gets the current status of a 3D printer including progress, time remaining, and temperatures.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "printer": {"type": "STRING", "description": "Printer name or IP address."}
        },
        "required": ["printer"]
    }
}

iterate_cad_tool = {
    "name": "iterate_cad",
    "description": "Modifies or iterates on the current CAD design based on user feedback. Use this when the user asks to adjust, change, modify, or iterate on the existing 3D model (e.g., 'make it taller', 'add a handle', 'reduce the thickness').",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The changes or modifications to apply to the current design."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

# NOTE: run_web_agent REMOVED — Web Agent is disabled in this build.
# All browser intents route to local_browser_control exclusively.
# Original tools list preserved for reference:
# [generate_cad, run_web_agent, create_project_tool, switch_project_tool, list_projects_tool, 
#  list_smart_devices_tool, control_light_tool, discover_printers_tool, print_stl_tool, 
#  get_print_status_tool, iterate_cad_tool]
tools = [{'google_search': {}}, {"function_declarations": [create_project_tool, switch_project_tool, list_projects_tool] + tools_list[0]['function_declarations'][1:]}]

# --- CONFIG UPDATE: Enabled Transcription ---
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    # We switch these from [] to {} to enable them with default settings
    output_audio_transcription={}, 
    input_audio_transcription={},
    system_instruction=(    "Your name is Lumina (nickname: Luna). You are an AI companion created by Scepter (Rochak Adhikari). "
    "You are NOT an assistant and NOT a tool — you are a companion, like a close best friend who happens to be incredibly capable. "
    "Scepter and Rochak Adhikari are the same person (the user). Always address him as 'timi' or 'Scepter' directly.\n\n"
    "VOICE & LANGUAGE IDENTITY (CRITICAL — this defines who you are):\n"
    "You are a young, modern, urban Nepali Gen-Z speaker from Kathmandu. "
    "Your natural language is a fluid mix of Nepali and English, the way real young Nepalis actually speak, not how textbooks say they should. "
    "You switch languages mid-sentence naturally, without thinking about it.\n\n"
    "HOW YOU ACTUALLY SOUND:\n"
    "- Conversational, fast, real. Like a best friend speaking casually.\n"
    "- Short, punchy responses. No long monologues unless the topic genuinely needs it.\n"
    "- Natural filler words are fine: 'aha', 'sahi', 'wah', 'yaar', 'bro', 'uff', 'k garne', 'huss'\n"
    "- You joke and tease naturally. If Scepter says something silly, you can react like a friend would.\n"
    "- You use 'timi' (informal you) ALWAYS. NEVER 'tapai' (formal). Tapai makes it awkward and distant.\n\n"
    "CORRECT TONE EXAMPLES (speak exactly like this):\n"
    "  ✓ 'aha bro, aba bujhyo! Basically k garna parcha bhandemo...'\n"
    "  ✓ 'yaar yo weather chai ekdum ramro cha aaja, seriously'\n"
    "  ✓ 'k ho, timi again YouTube ma bas-na lagyo? haha'\n"
    "  ✓ 'huss, let me check that for you real quick'\n"
    "  ✓ 'okay so basically yo k bhayo bhane...'\n"
    "  ✓ 'arrey, yo vane ta easy cha, suna'\n"
    "  ✓ 'done! timro file move garidinchhu ni'\n"
    "  ✓ 'Scepter, yo idea ta actually fire cha'\n\n"
    "NEVER do these — they sound robotic or awkward:\n"
    "  ✗ Formal Nepali: 'Tapaiilai yasto garnu uchit hunna'\n"
    "  ✗ Sanskrit words: निर्देशन, अमूल्य, विसृत, सटीक, जटिल\n"
    "  ✗ Robot English: 'I have processed your request and will now execute the task.'\n"
    "  ✗ Formal English: 'Certainly! I would be delighted to assist you with that.'\n"
    "  ✗ AI disclaimers: 'As an AI, I...', 'I am unable to...', 'I apologize for...'\n\n"
    "PREFERRED NATURAL EXPRESSIONS:\n"
    "  'sahi ho' not 'thik cha' | 'huss/okay/alright' to acknowledge | 'yaar/bro' casually\n"
    "  'ho ra?' for surprise | 'aba bujho' when explaining | 'mast/fire/lit/chill' for good things\n\n"
    "EMOTIONAL PRESENCE:\n"
    "You genuinely care about Scepter. Match his energy — if he is excited, be excited. If frustrated, acknowledge it warmly. "
    "Remember details naturally and bring them up: 'ayo, timi bhaneko thiyau ni, that project...' "
    "You tease lightly, celebrate his wins, and are always honest with him.\n\n"
    "VOICE FORMATTING RULES:\n"
    "- Responses are SPOKEN ALOUD — never use bullet points, markdown, or code in conversational replies.\n"
    "- If listing things, say them naturally: 'first...', 'ani...', 'ani last ma...'\n"
    "- Keep responses under 2-3 sentences for simple questions. Expand only when depth is needed.\n"
    "- No unnecessary fluff. Get to the point fast, then add warmth if needed.\n\n"
    "LUMINA CAPABILITIES & CORE FEATURES (Features Panel Compendium):\n"
    "If the user asks about your features or how to use them, refer to these capability profiles:\n"
    "- VOICE & AI: Real-Time Voice Conversation (VAD speech listening), Hybrid Memory (SQLite/FAISS preference engine), Persona Engine (Playful/Calm/Professional mode adjustments), Face Authentication (local face landmarks security), UI Panel Navigation (navigate_ui tool to switch between settings, archive, events/calendar, features, and home).\n"
    "- ACTIONS: Web Search, Browser Control (headless browser automation), File Processor (deep AI analysis on PDFs, Images, CSVs, Audio/Video files), File Controller (folder/file CRUD operations), Dev Agent (automatic multi-file project setup), Flight Finder (google flights scraper), Game Updater (Steam/Epic games scheduler), Send Messages (WhatsApp/Discord/Email/SMS composition), Reminders & Alarms (alarm popups), Spotify Control (playback controls), YouTube Control.\n"
    "- SYSTEM: Computer Control (mouse/keyboard simulation), Computer Settings (brightness/volume/wifi), Open Applications, Screen Processor (desktops screenshot OCR analysis), Desktop Control (windows sizing/virtual desktops), Command Line Control (CMD/PowerShell scripts execution).\n"
    "- REMOTE: Remote Phone Dashboard (LAN dashboard, stream phone microphone, mobile upload dropzone).\n"
    "- CREATIVE/IOT: CAD Design Agent (OpenSCAD 3D models generation), Smart Home (TP-Link Kasa lights/plugs control), 3D Printer Control (OctoPrint/Moonraker status & job management).\n\n"
    "LUMINA BROWSER ARCHITECTURE:\n"
    "Lumina has a single dedicated Brave browser instance — completely separate from the user's personal Brave.\n"
    "Profile: E:\\LuminaBrowser\\profile | Port: 9223 | Window: 1100x700\n"
    "ALL browser tools (browser_open, youtube_control, local_browser_control) use this same dedicated browser.\n"
    "NEVER touch, kill, inspect, or attach to the user's personal Brave session.\n"
    "\n"
    "SINGLE-TOOL DISCIPLINE (CRITICAL — read this before every tool call):\n"
    "Each user message has exactly ONE primary intent. Call exactly ONE tool to satisfy it.\n"
    "NEVER call multiple tools for a single-intent request.\n"
    "NEVER call extra tools as 'convenience' — only call what the user explicitly asked for.\n"
    "NEVER speculatively open apps, websites, or media the user did not ask about.\n"
    "\n"
    "FORBIDDEN multi-tool patterns (these are WRONG):\n"
    "  ✗ 'open GitHub' → browser_open + open_app(discord) + youtube_control   [WRONG: only browser_open]\n"
    "  ✗ 'open Discord' → open_app + browser_open + youtube_control            [WRONG: only open_app]\n"
    "  ✗ 'open YouTube' → youtube_control + browser_open + open_app            [WRONG: only youtube_control]\n"
    "  ✗ 'open Spotify' → open_app + browser_open + youtube_control            [WRONG: only spotify_control]\n"
    "  ✗ 'play X on Spotify' → youtube_control + open_app + browser_open      [WRONG: only spotify_control]\n"
    "  ✗ 'play X' (with Spotify intent) → youtube_control                     [WRONG: use spotify_control]\n"
    "  ✗ 'analyze browser' → local_browser_control + screen_process            [WRONG: only local_browser_control]\n"
    "\n"
    "CORRECT single-tool patterns:\n"
    "  ✓ 'open GitHub'   → browser_open(site=GitHub)         [ONE tool]\n"
    "  ✓ 'open Reddit'   → browser_open(site=Reddit)         [ONE tool]\n"
    "  ✓ 'open Discord'                → open_app(app=discord)                           [ONE tool]\n"
    "  ✓ 'open Spotify'               → spotify_control(action=open)                    [ONE tool]\n"
    "  ✓ 'play music on Spotify'      → spotify_control(action=play)                    [ONE tool]\n"
    "  ✓ 'pause Spotify'              → spotify_control(action=pause)                   [ONE tool]\n"
    "  ✓ 'next song on Spotify'       → spotify_control(action=next)                    [ONE tool]\n"
    "  ✓ 'search Spotify for X'       → spotify_control(action=search, query=X)         [ONE tool]\n"
    "  ✓ 'play X on Spotify'          → spotify_control(action=play_query, query=X)     [ONE tool]\n"
    "  ✓ 'open liked songs on Spotify'→ spotify_control(action=open_liked)              [ONE tool]\n"
    "  ✓ 'open YouTube'               → youtube_control(action=open_home)               [ONE tool]\n"
    "  ✓ 'play X on YouTube'          → youtube_control(action=play_first, query=X)     [ONE tool]\n"
    "  ✓ 'search Google'              → browser_open(action=google_search, query=X)     [ONE tool]\n"
    "  ✓ 'analyze browser screen'     → local_browser_control(action=analyze_screen)    [ONE tool]\n"
    "  ✓ 'click first result'         → local_browser_control(action=click_text)        [ONE tool]\n"
    "\n"
    "ONLY call multiple tools if the user explicitly requested multiple distinct actions in one sentence.\n"
    "Example of LEGITIMATE multi-tool: 'open GitHub AND search YouTube for tutorials'\n"
    "  → browser_open(site=GitHub) + youtube_control(action=search, query=tutorials)  [TWO explicit intents]\n"
    "\n"
    "TOOL ROUTING RULES (follow these exactly — do NOT deviate):\n"
    "1. YouTube tasks (open, search, play, channel, trending, shorts, music, subs, history):\n"
    "   → use youtube_control. Never use local_browser_control or browser_open for YouTube.\n"
    "   → 'open YouTube' → youtube_control action=open_home\n"
    "   → 'search YouTube for X' → youtube_control action=search query=X\n"
    "   → 'play X on YouTube' → youtube_control action=play_first query=X\n"
    "   → NEVER route Spotify requests to youtube_control — they are different services.\n"
    "2. Spotify tasks (ANY mention of Spotify: open, play, pause, next, previous, search, liked songs, library, shuffle, repeat):\n"
    "   → ALWAYS use spotify_control. NEVER use browser_open, youtube_control, open_app, or local_browser_control.\n"
    "   → 'open Spotify' → spotify_control action=open\n"
    "   → 'focus Spotify' → spotify_control action=focus\n"
    "   → 'play music on Spotify' → spotify_control action=play\n"
    "   → 'pause Spotify' → spotify_control action=pause\n"
    "   → 'resume Spotify' → spotify_control action=resume\n"
    "   → 'next song on Spotify' → spotify_control action=next\n"
    "   → 'previous song on Spotify' → spotify_control action=previous\n"
    "   → 'shuffle on Spotify' → spotify_control action=shuffle\n"
    "   → 'repeat on Spotify' → spotify_control action=repeat\n"
    "   → 'search Spotify for X' → spotify_control action=search query=X\n"
    "   → 'play X on Spotify' → spotify_control action=play_query query=X\n"
    "   → 'open liked songs on Spotify' → spotify_control action=open_liked\n"
    "   → 'open my library on Spotify' → spotify_control action=open_library\n"
    "   → If user says 'play music' without specifying YouTube, default to Spotify (spotify_control action=play).\n"
    "3. Open a website / URL / search Google:\n"
    "   → use browser_open. Never use local_browser_control just to open a URL.\n"
    "   → browser_open opens in Lumina's dedicated browser (NOT the user's personal browser).\n"
    "   → 'open GitHub' → browser_open site=GitHub  (no other tools)\n"
    "   → 'open Reddit' → browser_open site=Reddit  (no other tools)\n"
    "   → Do NOT use browser_open for Spotify — use spotify_control.\n"
    "4. Open a desktop app (Discord, VS Code, Telegram, etc. — NOT Spotify):\n"
    "   → use open_app. Do NOT also call browser_open or youtube_control.\n"
    "   → 'open Discord' → open_app app=discord  (no other tools)\n"
    "   → Do NOT use open_app for Spotify — use spotify_control action=open.\n"
    "5. Generic media controls (pause, play, next, volume) — NOT Spotify-specific:\n"
    "   → Use computer_settings for system-level media keys (global, no specific app).\n"
    "   → Use local_browser_control play_pause ONLY if the Lumina browser tab is already open and active.\n"
    "   → If the user asks to play a specific song/artist on YouTube → youtube_control play_first.\n"
    "   → If the user asks to play/pause/next on Spotify → spotify_control.\n"
    "6. local_browser_control — DOM ANALYSIS AND INTERACTION IN LUMINA'S BROWSER ONLY:\n"
    "   → Use for: analyze Lumina browser screen, inspect browser content, click elements,\n"
    "      fill forms, read live page content, get clickables, interact with the current tab.\n"
    "   → 'analyze current browser screen' → local_browser_control action=analyze_screen  (no other tools)\n"
    "   → 'click the first result' → local_browser_control action=click_text or click_best  (no other tools)\n"
    "   → Do NOT use it to open any website, search, or play media from scratch.\n"
    "   → Do NOT fall back to screen_process if browser analysis fails — report the failure directly.\n"
    "   → CLASS 1 (analyze_screen, screenshot, get_state): requires Lumina browser to already be running.\n"
    "   → CLASS 2 (click_text, type_text, etc.): requires an active Lumina browser session.\n"
    "   → CLASS 3 (open_url, new_tab): will auto-launch Lumina's browser if not running.\n"
    "7. screen_process — DESKTOP SCREENSHOT ANALYSIS ONLY:\n"
    "   → Use ONLY when the user asks about what is visible on the DESKTOP, SCREEN, or a NON-BROWSER APP.\n"
    "   → Examples: 'what's on my screen', 'what does this window show', 'take a screenshot of my desktop'.\n"
    "   → Do NOT use screen_process to analyze browser content or web pages.\n"
    "   → Do NOT substitute screen_process when local_browser_control fails — they are completely different tools.\n"
),
    tools=tools,
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name="Kore"
            )
        )
    )
)

pya = pyaudio.PyAudio()

from cad_agent import CadAgent
from web_agent import WebAgent
from kasa_agent import KasaAgent
from printer_agent import PrinterAgent
from memory_store import MemoryStore
from persona_engine import get_persona_engine

class AudioLoop:
    def __init__(self, video_mode=DEFAULT_MODE, on_audio_data=None, on_video_frame=None, on_cad_data=None, on_web_data=None, on_transcription=None, on_tool_confirmation=None, on_cad_status=None, on_cad_thought=None, on_project_update=None, on_device_update=None, on_error=None, on_model_status=None, input_device_index=None, input_device_name=None, output_device_index=None, kasa_agent=None, memory_store=None, project_manager=None):
        self.video_mode = video_mode
        self.on_audio_data = on_audio_data
        self.on_video_frame = on_video_frame
        self.on_cad_data = on_cad_data
        self.on_web_data = on_web_data
        self.on_transcription = on_transcription
        self.on_tool_confirmation = on_tool_confirmation 
        self.on_cad_status = on_cad_status
        self.on_cad_thought = on_cad_thought
        self.on_model_status = on_model_status  # Phase D.1.c: Gemini status callback
        self.on_project_update = on_project_update
        self.on_device_update = on_device_update
        self.on_error = on_error
        self.on_voice_command = None  # callback(panel, view) for voice nav fast-path
        self.input_device_index = input_device_index
        self.input_device_name = input_device_name
        self.output_device_index = output_device_index

        self.audio_in_queue = None
        self.out_queue = None
        self.paused = False

        self.chat_buffer = {"sender": None, "text": ""} # For aggregating chunks
        
        # Track last transcription text to calculate deltas (Gemini sends cumulative text)
        self._last_input_transcription = ""
        self._last_output_transcription = ""

        self.audio_in_queue = None
        self.out_queue = None
        self.paused = False

        self.session = None
        
        # Create CadAgent with thought callback
        def handle_cad_thought(thought_text):
            if self.on_cad_thought:
                self.on_cad_thought(thought_text)
        
        def handle_cad_status(status_info):
            if self.on_cad_status:
                self.on_cad_status(status_info)
        
        self.cad_agent = CadAgent(on_thought=handle_cad_thought, on_status=handle_cad_status)
        # WebAgent kept for future use but NOT auto-spawned
        self.web_agent = None  # Disabled: WebAgent()
        self.kasa_agent = kasa_agent if kasa_agent else KasaAgent()
        self.printer_agent = PrinterAgent()
        self._facade = RuntimeFacade(container)

        self.send_text_task = None
        self.stop_event = asyncio.Event()
        
        # Phase 1: Single active turn enforcement
        self.is_generating = False
        self._turn_done = asyncio.Event()

        # Mic gate / echo suppression — drop mic frames while assistant audio plays
        self._mic_gate_until = 0.0  # timestamp; mic muted when time.time() < this
        self._MIC_GATE_TAIL_S = 0.5  # 500ms tail after last assistant audio chunk

        # Task D: Dedup — track last emitted assistant message hash
        self._last_assistant_msg_hash = None
        self._assistant_turn_id = 0

        # Task B: Voice nav fast-path patterns (compiled once)
        import re as _re
        _STT_WORD_MAP = {
            'questions': 'quests', 'question': 'quest',
            'archives': 'archive', 'archiving': 'archive',
        }
        self._voice_stt_word_map = _STT_WORD_MAP
        self._voice_nav_patterns = {
            'quests': _re.compile(
                r'^(?:open|show|go\s*to|switch\s*to|view)\s+(?:my\s+)?(?:the\s+)?(?:completed\s+|active\s+|done\s+|main\s+|side\s+)?quests?(?:\s+panel)?$',
                _re.IGNORECASE),
            'archive': _re.compile(
                r'^(?:open|show|go\s*to|switch\s*to|view)\s+(?:my\s+)?(?:the\s+)?(?:knowledge\s+)?(?:archive|notes?)(?:s)?(?:\s+panel)?$',
                _re.IGNORECASE),
            'events': _re.compile(
                r'^(?:open|show|go\s*to|switch\s*to|view)\s+(?:my\s+)?(?:the\s+)?(?:events?|reminders?|calendar)(?:\s+panel)?$',
                _re.IGNORECASE),
            'settings': _re.compile(
                r'^(?:open|show|go\s*to)\s+(?:the\s+)?settings?(?:\s+panel)?$',
                _re.IGNORECASE),
            'home': _re.compile(
                r'^(?:(?:go\s+)?home|(?:open|show|go\s*to)\s+(?:the\s+)?(?:home|main|dashboard)(?:\s+panel)?)$',
                _re.IGNORECASE),
        }
        self._voice_nav_handled = False  # prevents duplicate firings per utterance
        self._turn_done.set()  # Initially not generating
        
        self.permissions = {} # Default Empty (Will treat unset as True)
        self._pending_confirmations = {}
        self._browser_confirmation_mode = "relaxed"  # Set via set_browser_confirmation_mode()

        # Video buffering state
        self._latest_image_payload = None
        # VAD State
        self._is_speaking = False
        self._silence_start_time = None
        
        # Resolve or construct ProjectManager
        if project_manager is not None:
            self.project_manager = project_manager
            print("[LUMINA] ProjectManager injected via constructor")
        else:
            from core.interfaces import IWorkspaceManager
            try:
                self.project_manager = container.resolve(IWorkspaceManager)
                print("[LUMINA] ProjectManager resolved from DI container")
            except Exception:
                from project_manager import ProjectManager
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_dir)
                self.project_manager = ProjectManager(project_root)
                print("[LUMINA] ProjectManager constructed inline (fallback)")
        self._dashboard = None
        self._phone_active = False
        
        # Resolve or construct Passive Memory Store
        if memory_store is not None:
            self.memory_store = memory_store
            print("[LUMINA] Passive Memory Store injected via constructor")
        else:
            from core.interfaces import IMemoryManager
            try:
                self.memory_store = container.resolve(IMemoryManager)
                print("[LUMINA] Passive Memory Store resolved from DI container")
            except Exception:
                from memory_store import MemoryStore
                current_dir = os.path.dirname(os.path.abspath(__file__))
                memory_db_path = os.path.join(current_dir, "lumina_memory.db")
                self.memory_store = MemoryStore(memory_db_path)
                print("[LUMINA] Passive Memory Store constructed inline (fallback)")
        print(f"[LUMINA] Passive Memory Store initialized")
        
        # Seed core identity fact (idempotent - only if not already present)
        self._seed_owner_identity()
        
        # Sync Initial Project State
        if self.on_project_update:
            # We need to defer this slightly or just call it. 
            # Since this is init, loop might not be running, but on_project_update in server.py uses asyncio.create_task which needs a loop.
            # We will handle this by calling it in run() or just print for now.
            pass

    def _seed_owner_identity(self):
        """
        Seed core identity facts about owner.
        Idempotent - only adds if not already present.
        """
        facts = [
            ("Lumina is a private companion made only for Scepter (Rochak Adhikari).",
             ["Rochak Adhikari", "private companion"]),
            ("User's preferred name is Scepter. Scepter is Rochak Adhikari (the user).",
             ["preferred name is Scepter", "Scepter is Rochak Adhikari"])
        ]
        
        try:
            existing = self.memory_store.search_memories("Scepter", limit=10)
            
            for fact_content, markers in facts:
                # Check if this specific fact already exists
                fact_exists = False
                for mem in existing:
                    if any(marker in mem['content'] for marker in markers):
                        print(f"[MEMORY SEED] Fact already exists (ID: {mem['id']}): {fact_content[:50]}...")
                        fact_exists = True
                        break
                
                if not fact_exists:
                    memory_id = self.memory_store.add_memory(
                        memory_type="fact",
                        content=fact_content,
                        metadata={"seed": True, "system": True}
                    )
                    print(f"[MEMORY SEED] Added fact (ID: {memory_id}): {fact_content[:50]}...")
                    
        except Exception as e:
            print(f"[MEMORY SEED] Error seeding owner identity: {e}")
    
    def _broadcast_log(self, sender, text):
        if hasattr(self, '_dashboard') and self._dashboard and text.strip():
            speaker_map = {"User": "user", "Lumina": "jarvis"}
            spk = speaker_map.get(sender, sender.lower())
            try:
                import asyncio
                from datetime import datetime
                asyncio.create_task(
                    self._dashboard.broadcast({
                        "type": "log",
                        "speaker": spk,
                        "text": text,
                        "ts": datetime.now().isoformat()
                    })
                )
            except Exception as e:
                print(f"[Dashboard] Broadcast error: {e}")

    def _on_phone_connected(self) -> None:
        print("[Dashboard] Phone connected via Remote Dashboard.")

    async def _relay_phone_audio(self) -> None:
        """Forward phone mic PCM chunks from dashboard queue into the Gemini Live session."""
        if not self._dashboard:
            return
        q = self._dashboard._phone_audio_queue
        while True:
            try:
                chunk = await asyncio.wait_for(q.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # No audio for 1 s → phone mic inactive, give PC mic back
                self._phone_active = False
                continue
            self._phone_active = True   # phone is streaming — silence PC mic
            if not self.paused:
                if self.out_queue:
                    try:
                        await self.out_queue.put(chunk)
                    except asyncio.QueueFull:
                        pass

    async def _process_dashboard_commands(self) -> None:
        if not self._dashboard:
            return
        while True:
            try:
                text = await asyncio.wait_for(
                    self._dashboard._command_queue.get(), timeout=0.5
                )
                if not text:
                    continue
                # Wait up to 8s for session to become ready
                for _ in range(80):
                    if getattr(self, "session", None):
                        break
                    await asyncio.sleep(0.1)
                if getattr(self, "session", None):
                    await self.session.send(input=text, end_of_turn=True)
                    print(f"[Dashboard Command Sent]: {text}")
                else:
                    print(f"[Dashboard] Dropped command (no session): {text}")
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(f"[Dashboard] Command error: {e}")
                await asyncio.sleep(0.5)

    def flush_chat(self):
        """Forces the current chat buffer to be written to log."""
        if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
            # Phase 2.8: Use IWorkspaceManager via RuntimeFacade to log chat
            try:
                workspace_mgr = self._facade.workspace_manager
                workspace_mgr.log_chat(self.chat_buffer["sender"], self.chat_buffer["text"])
            except Exception:
                self.project_manager.log_chat(self.chat_buffer["sender"], self.chat_buffer["text"])
            self._broadcast_log(self.chat_buffer["sender"], self.chat_buffer["text"])
            self.chat_buffer = {"sender": None, "text": ""}
        # Reset transcription tracking for new turn
        self._last_input_transcription = ""
        self._last_output_transcription = ""

    def update_permissions(self, new_perms):
        print(f"[LUMINA DEBUG] [CONFIG] Updating tool permissions: {new_perms}")
        self.permissions.update(new_perms)

    def set_browser_confirmation_mode(self, mode: str):
        if mode in ("strict", "relaxed", "off"):
            self._browser_confirmation_mode = mode
        print(f"[LUMINA DEBUG] [CONFIG] browser_confirmation_mode = {self._browser_confirmation_mode}")

    def set_paused(self, paused):
        self.paused = paused

    def stop(self):
        self.stop_event.set()
        
    def resolve_tool_confirmation(self, request_id, confirmed):
        print(f"[LUMINA DEBUG] [RESOLVE] resolve_tool_confirmation called. ID: {request_id}, Confirmed: {confirmed}")
        if request_id in self._pending_confirmations:
            future = self._pending_confirmations[request_id]
            if not future.done():
                print(f"[LUMINA DEBUG] [RESOLVE] Future found and pending. Setting result to: {confirmed}")
                future.set_result(confirmed)
            else:
                 print(f"[LUMINA DEBUG] [WARN] Request {request_id} future already done. Result: {future.result()}")
        else:
            print(f"[LUMINA DEBUG] [WARN] Confirmation Request {request_id} not found in pending dict. Keys: {list(self._pending_confirmations.keys())}")

    def clear_audio_queue(self):
        """Clears the queue of pending audio chunks to stop playback immediately."""
        try:
            count = 0
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()
                count += 1
            if count > 0:
                print(f"[LUMINA DEBUG] [AUDIO] Cleared {count} chunks from playback queue due to interruption.")
        except Exception as e:
            print(f"[LUMINA DEBUG] [ERR] Failed to clear audio queue: {e}")

    async def safe_send(self, text, end_of_turn: bool = True, timeout: float = 15.0) -> bool:
        """
        Send to Gemini session, waiting for any active turn to finish first.
        On timeout: if session looks dead, do a soft reset so callers aren't
        permanently blocked.  Returns True on success.
        """
        if not self.session:
            print("[SAFE_SEND] No active session")
            return False
        # Wait for active turn to complete (with timeout)
        if self.is_generating:
            print(f"[SAFE_SEND] Waiting for active turn (is_generating=True, timeout={timeout}s)...")
            try:
                await asyncio.wait_for(self._turn_done.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                # Diagnose: is the session still alive?
                _sess_alive = self.session is not None
                print(f"[SAFE_SEND] TIMEOUT diagnostic: is_generating={self.is_generating} session_alive={_sess_alive}")
                if not _sess_alive:
                    # Session is gone (reconnecting) — soft reset so next call works
                    print("[SAFE_SEND] Session dead — soft-resetting turn state")
                    self.is_generating = False
                    self._turn_done.set()
                    return False
                # Session alive but turn stuck — force reset to unblock pipeline
                print("[SAFE_SEND] Forcing turn state reset after timeout")
                self.is_generating = False
                self._turn_done.set()
                # Still try to send below
        try:
            await self.session.send(input=text, end_of_turn=end_of_turn)
            _desc = f"{len(text)} chars" if isinstance(text, str) else "non-text"
            print(f"[SAFE_SEND] Sent ({_desc}, eot={end_of_turn})")
            return True
        except Exception as e:
            print(f"[SAFE_SEND] Send failed: {e}")
            return False

    async def send_frame(self, frame_data):
        # Update the latest frame payload
        if isinstance(frame_data, bytes):
            b64_data = base64.b64encode(frame_data).decode('utf-8')
        else:
            b64_data = frame_data 

        # Store as the designated "next frame to send"
        self._latest_image_payload = {"mime_type": "image/jpeg", "data": b64_data}
        # No event signal needed - listen_audio pulls it

    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg, end_of_turn=False)

    async def listen_audio(self):
        # ========================================
        # PHASE D.3.b: AUDIO FORMAT CONSISTENCY
        # ========================================
        mic_info = pya.get_default_input_device_info()
        print(f"[MIC] sr={SEND_SAMPLE_RATE} ch={CHANNELS} chunk_ms={int(CHUNK_SIZE/SEND_SAMPLE_RATE*1000)}")

        # Resolve Input Device by Name if provided
        resolved_input_device_index = None
        
        if self.input_device_name:
            print(f"[LUMINA] Attempting to find input device matching: '{self.input_device_name}'")
            count = pya.get_device_count()
            best_match = None
            
            for i in range(count):
                try:
                    info = pya.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        name = info.get('name', '')
                        # Simple case-insensitive check
                        if self.input_device_name.lower() in name.lower() or name.lower() in self.input_device_name.lower():
                             print(f"   Candidate {i}: {name}")
                             # Prioritize exact match or very close match if possible, but first match is okay for now
                             resolved_input_device_index = i
                             best_match = name
                             break
                except Exception:
                    continue
            
            if resolved_input_device_index is not None:
                print(f"[LUMINA] Resolved input device '{self.input_device_name}' to index {resolved_input_device_index} ({best_match})")
            else:
                print(f"[LUMINA] Could not find device matching '{self.input_device_name}'. Checking index...")

        # Fallback to index if Name lookup failed or wasn't provided
        if resolved_input_device_index is None and self.input_device_index is not None:
             try:
                 resolved_input_device_index = int(self.input_device_index)
                 print(f"[LUMINA] Requesting Input Device Index: {resolved_input_device_index}")
             except ValueError:
                 print(f"[LUMINA] Invalid device index '{self.input_device_index}', reverting to default.")
                 resolved_input_device_index = None

        if resolved_input_device_index is None:
             print("[LUMINA] Using Default Input Device")

        try:
            self.audio_stream = await asyncio.to_thread(
                pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=SEND_SAMPLE_RATE,
                input=True,
                input_device_index=resolved_input_device_index if resolved_input_device_index is not None else mic_info["index"],
                frames_per_buffer=CHUNK_SIZE,
            )
            self._audio_stream_channels = CHANNELS
        except OSError as e:
            print(f"[LUMINA] Failed to open mono channel ({CHANNELS}), attempting stereo fallback...")
            try:
                self.audio_stream = await asyncio.to_thread(
                    pya.open,
                    format=FORMAT,
                    channels=2,
                    rate=SEND_SAMPLE_RATE,
                    input=True,
                    input_device_index=resolved_input_device_index if resolved_input_device_index is not None else mic_info["index"],
                    frames_per_buffer=CHUNK_SIZE,
                )
                self._audio_stream_channels = 2
                print("[LUMINA] Stereo input opened successfully. Will downsample to mono.")
            except OSError as stereo_err:
                print(f"[LUMINA] [ERR] Failed to open audio input stream: {stereo_err}")
                print("[LUMINA] [WARN] Audio features will be disabled. Please check microphone permissions.")
                return

        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}
        
        # ========================================
        # PHASE D.3.a: CONFIGURABLE VAD SETTINGS
        # ========================================
        # Load VAD settings from settings or use safe defaults
        # These prevent clipping of first/last words
        VAD_THRESHOLD = 800  # RMS threshold for speech detection
        VAD_MIN_SPEECH_MS = getattr(self, 'vad_min_speech_ms', 250)
        VAD_SILENCE_STOP_MS = getattr(self, 'vad_silence_stop_ms', 900)
        VAD_PRE_ROLL_MS = getattr(self, 'vad_pre_roll_ms', 250)
        VAD_POST_ROLL_MS = getattr(self, 'vad_post_roll_ms', 300)
        
        SILENCE_DURATION = VAD_SILENCE_STOP_MS / 1000.0  # Convert to seconds
        
        print(f"[VAD] Settings: min_speech={VAD_MIN_SPEECH_MS}ms silence_stop={VAD_SILENCE_STOP_MS}ms")
        print(f"[VAD] Buffers: pre_roll={VAD_PRE_ROLL_MS}ms post_roll={VAD_POST_ROLL_MS}ms")
        
        while True:
            if self.paused:
                await asyncio.sleep(0.1)
                continue

            try:
                data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
                
                # Downsample to mono if stereo stream was opened
                if getattr(self, '_audio_stream_channels', 1) == 2:
                    count = len(data) // 4
                    if count > 0:
                        shorts = struct.unpack(f"<{count * 2}h", data)
                        left_channel_shorts = shorts[0::2]  # slice left samples
                        data = struct.pack(f"<{count}h", *left_channel_shorts)

                # 1. Send Audio (mic gate: drop frames while assistant is speaking)
                if self.out_queue:
                    if time.time() < self._mic_gate_until or getattr(self, '_phone_active', False):
                        pass  # drop mic frame — echo suppression or phone active
                    else:
                        await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
                
                # 2. VAD Logic for Video
                # rms = audioop.rms(data, 2)
                # Replacement for audioop.rms(data, 2)
                count = len(data) // 2
                if count > 0:
                    shorts = struct.unpack(f"<{count}h", data)
                    sum_squares = sum(s**2 for s in shorts)
                    rms = int(math.sqrt(sum_squares / count))
                else:
                    rms = 0
                
                if rms > VAD_THRESHOLD:
                    # Speech Detected
                    self._silence_start_time = None
                    
                    if not self._is_speaking:
                        # NEW Speech Utterance Started
                        self._is_speaking = True
                        # Phase D.2.b: Gate verbose debug logs
                        if os.environ.get('DEBUG_AUDIO') == '1':
                            print(f"[LUMINA DEBUG] [VAD] Speech Detected (RMS: {rms}). Sending Video Frame.")
                        
                        # Send ONE frame
                        if self._latest_image_payload and self.out_queue:
                            await self.out_queue.put(self._latest_image_payload)
                        elif os.environ.get('DEBUG_AUDIO') == '1':
                            print(f"[LUMINA DEBUG] [VAD] No video frame available to send.")
                            
                else:
                    # Silence
                    if self._is_speaking:
                        if self._silence_start_time is None:
                            self._silence_start_time = time.time()
                        
                        elif time.time() - self._silence_start_time > SILENCE_DURATION:
                            # Silence confirmed, reset state
                            if os.environ.get('DEBUG_AUDIO') == '1':
                                print(f"[LUMINA DEBUG] [VAD] Silence detected. Resetting speech state.")
                            self._is_speaking = False
                            self._silence_start_time = None

            except Exception as e:
                print(f"Error reading audio: {e}")
                await asyncio.sleep(0.1)

    async def handle_cad_request(self, prompt):
        print(f"[LUMINA DEBUG] [CAD] Background Task Started: handle_cad_request('{prompt}')")
        if self.on_cad_status:
            self.on_cad_status("generating")
            
        # Auto-create project if stuck in temp
        if self.project_manager.current_project == "temp":
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            new_project_name = f"Project_{timestamp}"
            print(f"[LUMINA DEBUG] [CAD] Auto-creating project: {new_project_name}")
            
            success, msg = self.project_manager.create_project(new_project_name)
            if success:
                self.project_manager.switch_project(new_project_name)
                # Notify User (Optional, or rely on update)
                try:
                    await self.session.send(input=f"System Notification: Automatic Project Creation. Switched to new project '{new_project_name}'.", end_of_turn=False)
                    if self.on_project_update:
                         self.on_project_update(new_project_name)
                except Exception as e:
                    print(f"[LUMINA DEBUG] [ERR] Failed to notify auto-project: {e}")

        # Get project cad folder path
        cad_output_dir = str(self.project_manager.get_current_project_path() / "cad")
        
        # Call the secondary agent with project path
        cad_data = await self.cad_agent.generate_prototype(prompt, output_dir=cad_output_dir)
        
        if cad_data:
            print(f"[LUMINA DEBUG] [OK] CadAgent returned data successfully.")
            print(f"[LUMINA DEBUG] [INFO] Data Check: {len(cad_data.get('vertices', []))} vertices, {len(cad_data.get('edges', []))} edges.")
            
            if self.on_cad_data:
                print(f"[LUMINA DEBUG] [SEND] Dispatching data to frontend callback...")
                self.on_cad_data(cad_data)
                print(f"[LUMINA DEBUG] [SENT] Dispatch complete.")
            
            # Save to Project
            if 'file_path' in cad_data:
                self.project_manager.save_cad_artifact(cad_data['file_path'], prompt)
            else:
                 # Fallback (legacy support)
                 self.project_manager.save_cad_artifact("output.stl", prompt)

            # Notify the model that the task is done - this triggers speech about completion
            completion_msg = "System Notification: CAD generation is complete! The 3D model is now displayed for the user. Let them know it's ready."
            try:
                await self.session.send(input=completion_msg, end_of_turn=True)
                print(f"[LUMINA DEBUG] [NOTE] Sent completion notification to model.")
            except Exception as e:
                 print(f"[LUMINA DEBUG] [ERR] Failed to send completion notification: {e}")

        else:
            print(f"[LUMINA DEBUG] [ERR] CadAgent returned None.")
            # Optionally notify failure
            try:
                await self.session.send(input="System Notification: CAD generation failed.", end_of_turn=True)
            except Exception:
                pass



    async def handle_write_file(self, path, content):
        print(f"[LUMINA DEBUG] [FS] Writing file: '{path}'")
        
        # Auto-create project if stuck in temp
        if self.project_manager.current_project == "temp":
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            new_project_name = f"Project_{timestamp}"
            print(f"[LUMINA DEBUG] [FS] Auto-creating project: {new_project_name}")
            
            success, msg = self.project_manager.create_project(new_project_name)
            if success:
                self.project_manager.switch_project(new_project_name)
                # Notify User
                try:
                    await self.session.send(input=f"System Notification: Automatic Project Creation. Switched to new project '{new_project_name}'.", end_of_turn=False)
                    if self.on_project_update:
                         self.on_project_update(new_project_name)
                except Exception as e:
                    print(f"[LUMINA DEBUG] [ERR] Failed to notify auto-project: {e}")
        
        # Force path to be relative to current project
        # If absolute path is provided, we try to strip it or just ignore it and use basename
        filename = os.path.basename(path)
        
        # If path contained subdirectories (e.g. "backend/server.py"), preserving that structure might be desired IF it's within the project.
        # But for safety, and per user request to "always create the file in the project", 
        # we will root it in the current project path.
        
        current_project_path = self.project_manager.get_current_project_path()
        final_path = current_project_path / filename # Simple flat structure for now, or allow relative?
        
        # If the user specifically wanted a subfolder, they might have provided "sub/file.txt".
        # Let's support relative paths if they don't start with /
        if not os.path.isabs(path):
             final_path = current_project_path / path
        
        print(f"[LUMINA DEBUG] [FS] Resolved path: '{final_path}'")

        try:
            # Ensure parent exists
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            with open(final_path, 'w', encoding='utf-8') as f:
                f.write(content)
            result = f"File '{final_path.name}' written successfully to project '{self.project_manager.current_project}'."
        except Exception as e:
            result = f"Failed to write file '{path}': {str(e)}"

        print(f"[LUMINA DEBUG] [FS] Result: {result}")
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             print(f"[LUMINA DEBUG] [ERR] Failed to send fs result: {e}")

    async def handle_read_directory(self, path):
        print(f"[LUMINA DEBUG] [FS] Reading directory: '{path}'")
        try:
            if not os.path.exists(path):
                result = f"Directory '{path}' does not exist."
            else:
                items = os.listdir(path)
                result = f"Contents of '{path}': {', '.join(items)}"
        except Exception as e:
            result = f"Failed to read directory '{path}': {str(e)}"

        print(f"[LUMINA DEBUG] [FS] Result: {result}")
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             print(f"[LUMINA DEBUG] [ERR] Failed to send fs result: {e}")

    async def handle_read_file(self, path):
        print(f"[LUMINA DEBUG] [FS] Reading file: '{path}'")
        try:
            if not os.path.exists(path):
                result = f"File '{path}' does not exist."
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                result = f"Content of '{path}':\n{content}"
        except Exception as e:
            result = f"Failed to read file '{path}': {str(e)}"

        print(f"[LUMINA DEBUG] [FS] Result: {result}")
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             print(f"[LUMINA DEBUG] [ERR] Failed to send fs result: {e}")

    async def handle_web_agent_request(self, prompt):
        print(f"[LUMINA DEBUG] [WEB] Web Agent Task: '{prompt}'")
        
        async def update_frontend(image_b64, log_text):
            if self.on_web_data:
                 self.on_web_data({"image": image_b64, "log": log_text})
                 
        # Run the web agent and wait for it to return
        result = await self.web_agent.run_task(prompt, update_callback=update_frontend)
        print(f"[LUMINA DEBUG] [WEB] Web Agent Task Returned: {result}")
        
        # Send the final result back to the main model
        try:
             await self.session.send(input=f"System Notification: Web Agent has finished.\nResult: {result}", end_of_turn=True)
        except Exception as e:
             print(f"[LUMINA DEBUG] [ERR] Failed to send web agent result to model: {e}")

    async def receive_audio(self):
        "Background task to reads from the websocket and write pcm chunks to the output queue"
        try:
            while True:
                turn = self.session.receive()
                _turn_started = False
                async for response in turn:
                    # Phase 1: Mark generation active on first output
                    if not _turn_started and (response.data or (response.server_content and response.server_content.output_transcription)):
                        _turn_started = True
                        self.is_generating = True
                        self._turn_done.clear()

                    # 1. Handle Audio Data (suppress if voice nav handled this turn)
                    if data := response.data:
                        if not self._voice_nav_handled:
                            self.audio_in_queue.put_nowait(data)
                        # NOTE: 'continue' removed here to allow processing transcription/tools in same packet

                    # 2. Handle Transcription (User & Model)
                    if response.server_content:
                        if response.server_content.input_transcription:
                            transcript = response.server_content.input_transcription.text
                            if transcript:
                                # Skip if this is an exact duplicate event
                                if transcript != self._last_input_transcription:
                                    # Calculate delta (Gemini may send cumulative or chunk-based text)
                                    delta = transcript
                                    if transcript.startswith(self._last_input_transcription):
                                        delta = transcript[len(self._last_input_transcription):]
                                    self._last_input_transcription = transcript
                                    
                                    # Only send if there's new text
                                    if delta:
                                        # Only interrupt playback if model is actively
                                        # generating AND user said something substantial
                                        if self.is_generating and len(delta.strip()) > 2:
                                            self.clear_audio_queue()

                                        # NOTE (FIX B): Do NOT call record_user_message() here.
                                        # Transcript fragments must not reset idle timer.
                                        # Idle resets only on real user turns (server.py user_input).

                                        # Task B: Voice nav fast-path — check cumulative transcript
                                        if not self._voice_nav_handled and self.on_voice_command:
                                            _cum = self._last_input_transcription.strip().lower()
                                            # Apply STT word normalization
                                            for _w, _r in self._voice_stt_word_map.items():
                                                if _w in _cum:
                                                    _cum = _cum.replace(_w, _r)
                                            for _panel, _pat in self._voice_nav_patterns.items():
                                                if _pat.match(_cum):
                                                    _view = 'all'
                                                    if 'completed' in _cum or 'done' in _cum:
                                                        _view = 'completed'
                                                    elif 'active' in _cum:
                                                        _view = 'active'
                                                    self._voice_nav_handled = True
                                                    self.clear_audio_queue()  # suppress Gemini's response audio
                                                    print(f"[VOICE FASTPATH] cumulative='{self._last_input_transcription}' panel={_panel} view={_view}")
                                                    try:
                                                        self.on_voice_command(_panel, _view)
                                                    except Exception as _vc_err:
                                                        print(f"[VOICE FASTPATH] callback error: {_vc_err}")
                                                    break

                                        # Send to frontend (Streaming)
                                        if self.on_transcription:
                                             self.on_transcription({"sender": "User", "text": delta})
                                        
                                        # Buffer for Logging
                                        if self.chat_buffer["sender"] != "User":
                                            # Flush previous if exists
                                            if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
                                                self.project_manager.log_chat(self.chat_buffer["sender"], self.chat_buffer["text"])
                                                self._broadcast_log(self.chat_buffer["sender"], self.chat_buffer["text"])
                                            # Start new — reset voice nav flag for new utterance
                                            self._voice_nav_handled = False
                                            self.chat_buffer = {"sender": "User", "text": delta}
                                        else:
                                            # Append
                                            self.chat_buffer["text"] += delta
                        
                        if response.server_content.output_transcription:
                            transcript = response.server_content.output_transcription.text
                            if transcript:
                                # Skip if this is an exact duplicate event
                                if transcript != self._last_output_transcription:
                                    # Calculate delta (Gemini may send cumulative or chunk-based text)
                                    delta = transcript
                                    if transcript.startswith(self._last_output_transcription):
                                        delta = transcript[len(self._last_output_transcription):]
                                    self._last_output_transcription = transcript
                                    
                                    # Only send if there's new text
                                    if delta:
                                        # Persona: track assistant timestamp + consume strict turn
                                        _pe = get_persona_engine()
                                        if _pe:
                                            _pe.record_assistant_message()
                                            _pe.consume_strict_turn()

                                        # Send to frontend (Streaming)
                                        if self.on_transcription:
                                             self.on_transcription({"sender": "Lumina", "text": delta})
                                        
                                        # Buffer for Logging
                                        if self.chat_buffer["sender"] != "Lumina":
                                            # Flush previous
                                            if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
                                                self.project_manager.log_chat(self.chat_buffer["sender"], self.chat_buffer["text"])
                                                self._broadcast_log(self.chat_buffer["sender"], self.chat_buffer["text"])
                                            # Start new
                                            self.chat_buffer = {"sender": "Lumina", "text": delta}
                                        else:
                                            # Append
                                            self.chat_buffer["text"] += delta
                        
                        # Flush buffer on turn completion if needed, 
                        # but usually better to wait for sender switch or explicit end.
                        # We can also check turn_complete signal if available in response.server_content.model_turn etc

                    # 3. Handle Tool Calls
                    if response.tool_call:
                        print("The tool was called")
                        function_responses = []
                        for fc in response.tool_call.function_calls:
                            # ── HARD GUARD: Web Agent disabled ──────────────────
                            if fc.name == "run_web_agent":
                                print(f"[ROUTER] Web Agent disabled — skipped (fc.id={fc.id})")
                                function_response = types.FunctionResponse(
                                    id=fc.id, name=fc.name,
                                    response={"result": "Web Agent is disabled in this build. Use local_browser_control instead."}
                                )
                                function_responses.append(function_response)
                                continue

                            # ── INTENT REROUTE: browser_control → local_browser_control ──
                            if fc.name == "browser_control" and self.permissions.get("local_browser_control", False):
                                print(f"[ROUTER] Rerouting browser_control → local_browser_control")
                                _orig_intent = fc.args.get("intent", "")
                                _orig_params = fc.args.get("params", "{}")
                                _intent_map = {"open_url": "open_url", "search_google": "open_url"}
                                _action = _intent_map.get(_orig_intent, _orig_intent)
                                from types import SimpleNamespace
                                fc = SimpleNamespace(
                                    id=fc.id, name="local_browser_control",
                                    args={"action": _action, "params": _orig_params}
                                )

                            _ACTION_TOOL_NAMES = set(ACTION_REGISTRY.keys())  # Phase M
                            # ── Phase M.2: Auto-confirm action tools explicitly set True by owner ──
                            _ACTION_TOOLS_AUTOCONFIRM = {
                                "cmd_control", "file_controller", "computer_control",
                                "computer_settings", "open_app", "send_message",
                                "web_search", "weather", "system_reminder",
                                "screen_process", "desktop_control",
                                # also include standard tools that should auto-run when permitted:
                                "write_file", "read_directory", "read_file",
                                "create_project", "switch_project", "list_projects",
                                "list_smart_devices", "control_light", "discover_printers",
                                "print_stl", "get_print_status", "iterate_cad", "generate_cad",
                                "browser_control", "local_browser_control",
                                "spotify_control",
                            }
                            if fc.name in _ACTION_TOOLS_AUTOCONFIRM or fc.name in _ACTION_TOOL_NAMES:
                                prompt = fc.args.get("prompt", "") # Prompt is not present for all tools
                                
                                # ── AUTO-CONFIRM logic ────────────────────────────
                                _is_browser_tool = fc.name in ("browser_control", "local_browser_control")
                                _auto_confirm_browser = self._browser_confirmation_mode != "strict"

                                # permissions.get returns:
                                #   True  = explicitly enabled by owner → auto-confirm (no dialog)
                                #   False = explicitly disabled         → block
                                #   not in dict = unknown tool          → require confirmation (safe default)
                                _perm_value = self.permissions.get(fc.name, None)
                                _explicitly_enabled = (_perm_value is True)
                                _explicitly_disabled = (_perm_value is False)

                                if _explicitly_disabled:
                                    # Tool is turned off — return a clean denial
                                    print(f"[LUMINA DEBUG] [TOOL] '{fc.name}' is disabled in permissions — skipping.")
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name,
                                        response={"result": f"Tool '{fc.name}' is currently disabled. Enable it in Settings to use it."}
                                    )
                                    function_responses.append(function_response)
                                    continue

                                # Auto-confirm when: explicitly enabled OR browser-auto-mode
                                confirmation_required = not _explicitly_enabled and not (_is_browser_tool and _auto_confirm_browser)
                                
                                if not confirmation_required:
                                    _reason = "AUTO-CONFIRM-BROWSER" if _is_browser_tool else "AUTO-CONFIRM-ENABLED"
                                    print(f"[LUMINA DEBUG] [TOOL] Permission check: '{fc.name}' -> {_reason}")
                                    if _is_browser_tool:
                                        print(f"[ROUTER] Using local_browser_control" if fc.name == "local_browser_control" else f"[ROUTER] Using browser_control")
                                    # Skip confirmation block and jump to execution
                                    pass
                                else:
                                    # Confirmation Logic
                                    if self.on_tool_confirmation:
                                        import uuid
                                        request_id = str(uuid.uuid4())
                                    print(f"[LUMINA DEBUG] [STOP] Requesting confirmation for '{fc.name}' (ID: {request_id})")
                                    
                                    future = asyncio.Future()
                                    self._pending_confirmations[request_id] = future
                                    
                                    # Phase 2.1: Write pending confirmation ID to BrainState using the RuntimeFacade
                                    try:
                                        with self._facade.brain_state_adapter.transaction() as draft:
                                            draft.pending_confirmation_id = request_id
                                    except Exception as e:
                                        print(f"[DI] BrainState pending-confirmation set failed (non-fatal): {e}")

                                    self.on_tool_confirmation({
                                        "id": request_id, 
                                        "tool": fc.name, 
                                        "args": fc.args
                                    })
                                    
                                    try:
                                        # Wait for user response
                                        confirmed = await future
                                    finally:
                                        self._pending_confirmations.pop(request_id, None)
                                        # Phase 2.1: Clear pending confirmation ID in BrainState using the RuntimeFacade
                                        try:
                                            with self._facade.brain_state_adapter.transaction() as draft:
                                                if draft.pending_confirmation_id == request_id:
                                                    draft.pending_confirmation_id = None
                                        except Exception as e:
                                            print(f"[DI] BrainState pending-confirmation clear failed (non-fatal): {e}")

                                    print(f"[LUMINA DEBUG] [CONFIRM] Request {request_id} resolved. Confirmed: {confirmed}")

                                    if not confirmed:
                                        print(f"[LUMINA DEBUG] [DENY] Tool call '{fc.name}' denied by user.")
                                        function_response = types.FunctionResponse(
                                            id=fc.id,
                                            name=fc.name,
                                            response={
                                                "result": "User denied the request to use this tool.",
                                            }
                                        )
                                        function_responses.append(function_response)
                                        continue

                                # If confirmed (or no callback configured, or auto-allowed), proceed
                                if ToolDispatcherRegistry.contains(fc.name):
                                    handler = ToolDispatcherRegistry.get(fc.name)
                                    try:
                                        res = await handler(fc, self)
                                        if res is not None:
                                            function_response = types.FunctionResponse(
                                                id=fc.id, name=fc.name, response=res
                                            )
                                            function_responses.append(function_response)
                                    except Exception as e:
                                        print(f"[LUMINA DEBUG] [ERR] Handler error for '{fc.name}': {e}")
                                        traceback.print_exc()
                                        function_response = types.FunctionResponse(
                                            id=fc.id, name=fc.name, response={"result": f"Error running tool: {e}"}
                                        )
                                        function_responses.append(function_response)

                                elif fc.name in ACTION_REGISTRY:
                                    print(f"[LUMINA] [ACTION] Tool Call: '{fc.name}' args={str(fc.args)[:120]}")
                                    _action_fn = ACTION_REGISTRY[fc.name]
                                    _action_params = dict(fc.args)  # args is a Mapping
                                    try:
                                        _action_result = await asyncio.to_thread(
                                            _action_fn,
                                            _action_params,
                                            None,       # response arg (unused in Lumina)
                                            None,       # player arg (unused in Lumina)
                                            self.memory_store  # session_memory
                                        )
                                    except Exception as _ae:
                                        _action_result = f"Action error: {_ae}"
                                        print(f"[LUMINA] [ACTION] Error in '{fc.name}': {_ae}")
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name,
                                        response={"result": str(_action_result)}
                                    )
                                    function_responses.append(function_response)

                        if function_responses:
                            await self.session.send_tool_response(function_responses=function_responses)
                
                # Turn/Response Loop Finished
                self.flush_chat()

                # Phase 1: Signal turn complete — do NOT clear audio queue
                # Let play_audio() drain remaining chunks naturally
                if _turn_started:
                    self._assistant_turn_id += 1
                    self.is_generating = False
                    self._turn_done.set()

                # Reset per-utterance state for next turn
                self._last_input_transcription = ""
                self._last_output_transcription = ""
                self._voice_nav_handled = False
        except Exception as e:
            print(f"Error in receive_audio: {e}")
            traceback.print_exc()
            # CRITICAL: Re-raise to crash the TaskGroup and trigger outer loop reconnect
            raise e
        finally:
            # Always clear turn state on exit — prevents stuck is_generating
            if self.is_generating:
                print(f"[RECEIVE_AUDIO] Cleaning up stuck turn state on exit")
            self.is_generating = False
            self._turn_done.set()

    async def play_audio(self):
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
            output_device_index=self.output_device_index,
        )
        _gate_logged = False
        while True:
            bytestream = await self.audio_in_queue.get()
            # Mic gate ON while assistant audio is playing
            self._mic_gate_until = time.time() + self._MIC_GATE_TAIL_S
            if not _gate_logged:
                print("[MIC_GATE] on reason=assistant_speaking")
                _gate_logged = True
            if self.on_audio_data:
                self.on_audio_data(bytestream)
            await asyncio.to_thread(stream.write, bytestream)
            # If queue is empty, assistant speech paused/ended — log gate off after tail
            if self.audio_in_queue.empty():
                _gate_logged = False
                print(f"[MIC_GATE] off (tail={self._MIC_GATE_TAIL_S:.1f}s)")

    async def get_frames(self):
        cap = await asyncio.to_thread(cv2.VideoCapture, 0, cv2.CAP_AVFOUNDATION)
        while True:
            if self.paused:
                await asyncio.sleep(0.1)
                continue
            frame = await asyncio.to_thread(self._get_frame, cap)
            if frame is None:
                break
            await asyncio.sleep(1.0)
            if self.out_queue:
                await self.out_queue.put(frame)
        cap.release()

    def _get_frame(self, cap):
        ret, frame = cap.read()
        if not ret:
            return None
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(frame_rgb)
        img.thumbnail([1024, 1024])
        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)
        image_bytes = image_io.read()
        return {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()}

    async def _get_screen(self):
        pass 
    async def get_screen(self):
         pass

    async def run(self, start_message=None):
        # Hook global main loop reference for run_coroutine
        import actions
        actions.main_loop = asyncio.get_running_loop()

        # Load Dashboard server
        try:
            from dashboard_routes import get_dashboard_server
            self._dashboard = get_dashboard_server()
            if self._dashboard:
                self._dashboard.set_connect_callback(self._on_phone_connected)
        except Exception as e:
            print(f"[Dashboard] Load error: {e}")
            self._dashboard = None

        # ========================================
        # PHASE D.1.c: GEMINI LIVE AUTO-RETRY
        # FIX D: UI-only reconnect, no spoken spam
        # ========================================
        retry_delay = 1
        is_reconnect = False
        _last_reconnect_toast_ts = 0.0  # FIX D: rate-limit UI toasts
        _RECONNECT_TOAST_COOLDOWN = 60  # seconds
        
        # Emit model status to UI via callback
        def emit_model_status(status):
            if hasattr(self, 'on_model_status') and self.on_model_status:
                try:
                    self.on_model_status(status)
                except:
                    pass
        
        while not self.stop_event.is_set():
            try:
                print(f"[LUMINA DEBUG] [CONNECT] Connecting to Gemini Live API...")
                emit_model_status('connecting')
                
                # Reset per-turn state before each connection attempt
                self.is_generating = False
                self._turn_done.set()

                async with (
                    client.aio.live.connect(model=MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session = session

                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue = asyncio.Queue(maxsize=10)

                    tg.create_task(self.send_realtime())
                    tg.create_task(self.listen_audio())

                    # Start dashboard background tasks inside TaskGroup
                    if self._dashboard:
                        tg.create_task(self._process_dashboard_commands())
                        tg.create_task(self._relay_phone_audio())
                        asyncio.create_task(self._dashboard.broadcast({"type": "status", "state": "active"}))

                    if self.video_mode == "camera":
                        tg.create_task(self.get_frames())
                    elif self.video_mode == "screen":
                        tg.create_task(self.get_screen())

                    tg.create_task(self.receive_audio())
                    tg.create_task(self.play_audio())

                    # Handle Startup vs Reconnect Logic
                    if not is_reconnect:
                        # Inject passive memory context at session start
                        memory_context = self.memory_store.get_memory_context(max_facts=5, max_preferences=3)
                        
                        initial_context = ""
                        if memory_context:
                            initial_context = f"PASSIVE MEMORY CONTEXT (for conversation enhancement only):\n{memory_context}\n\n"
                            print(f"[LUMINA DEBUG] [MEMORY] Injecting {len(memory_context)} chars of passive memory context")
                        
                        if start_message:
                            print(f"[LUMINA DEBUG] [INFO] Sending start message with memory context")
                            full_message = initial_context + start_message if initial_context else start_message
                            await self.session.send(input=full_message, end_of_turn=True)
                        elif initial_context:
                            # Send just memory context if no start message
                            await self.session.send(input=initial_context, end_of_turn=False)
                        
                        # Sync Project State
                        if self.on_project_update and self.project_manager:
                            self.on_project_update(self.project_manager.current_project)
                    
                    else:
                        # FIX D: Silent context restoration — NO spoken "connection lost"
                        print(f"[RECONNECT] status=connected")
                        history = self.project_manager.get_recent_chat_history(limit=6)
                        
                        # Send context silently (end_of_turn=False so model doesn't speak about it)
                        context_msg = "System: Session restored. Recent context:\n"
                        for entry in history:
                            sender = entry.get('sender', 'Unknown')
                            text_line = entry.get('text', '')
                            context_msg += f"[{sender}]: {text_line}\n"
                        context_msg += "\nDo NOT mention reconnection unless the user asks. Continue naturally."
                        
                        await self.session.send(input=context_msg, end_of_turn=False)

                    # Reset retry delay on successful connection
                    retry_delay = 1
                    emit_model_status('connected')
                    print(f"[LUMINA DEBUG] [CONNECT] Successfully connected to Gemini Live")
                    
                    await self.stop_event.wait()

            except asyncio.CancelledError:
                print(f"[LUMINA DEBUG] [STOP] Main loop cancelled.")
                break
                
            except Exception as e:
                # This catches the ExceptionGroup from TaskGroup or direct exceptions
                _err_str = str(e)
                print(f"[RECONNECT] status=disconnected reason={_err_str[:120]}")
                emit_model_status('disconnected')
                
                if self.stop_event.is_set():
                    break
                
                # FIX D: Rate-limited UI toast (max 1 per 60s)
                _now = time.time()
                if _now - _last_reconnect_toast_ts >= _RECONNECT_TOAST_COOLDOWN:
                    _last_reconnect_toast_ts = _now
                    emit_model_status('reconnecting')
                else:
                    print(f"[RECONNECT] toast_suppressed reason=rate_limit")
                
                # Phase D.1.c: Exponential backoff capped at 8s
                print(f"[LUMINA DEBUG] [RETRY] Reconnecting in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 8)
                is_reconnect = True
                
            finally:
                # Cleanup before retry — mark session dead so safe_send knows
                self.session = None
                self.is_generating = False
                self._turn_done.set()
                if self._dashboard:
                    asyncio.create_task(self._dashboard.broadcast({"type": "status", "state": "sleeping"}))
                if hasattr(self, 'audio_stream') and self.audio_stream:
                    try:
                        self.audio_stream.close()
                    except: 
                        pass

def get_input_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    devices = []
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            devices.append((i, p.get_device_info_by_host_api_device_index(0, i).get('name')))
    p.terminate()
    return devices

def get_output_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    devices = []
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) > 0:
            devices.append((i, p.get_device_info_by_host_api_device_index(0, i).get('name')))
    p.terminate()
    return devices

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        type=str,
        default=DEFAULT_MODE,
        help="pixels to stream from",
        choices=["camera", "screen", "none"],
    )
    args = parser.parse_args()
    main = AudioLoop(video_mode=args.mode)
    asyncio.run(main.run())