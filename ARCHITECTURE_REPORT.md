# Lumina Architecture Report & Feature Matrix

## Generated: Phase 2 Deep Analysis

---

## 1. ARCHITECTURE OVERVIEW

### 1.1 Lumina (Primary — Source of Truth)

**Stack:** Python (FastAPI + Socket.IO) backend → React (Vite) frontend → Electron shell

```
┌─────────────────────────────────────────────────────┐
│  Electron (main.js)                                 │
│  ├─ Spawns Python backend (server.py)               │
│  ├─ Loads Vite dev server (port 5173) or dist/      │
│  └─ IPC: window controls, shutdown                  │
├─────────────────────────────────────────────────────┤
│  Frontend (AppTest.jsx + panels + components)       │
│  ├─ Socket.IO → localhost:8000                      │
│  ├─ Panels: Home / Quests / Events / Archive / Settings │
│  ├─ Overlays: CAD viewer, Browser viewer, Printer   │
│  └─ Auth lock, Visualizer, Chat, Confirmation popup │
├─────────────────────────────────────────────────────┤
│  Backend (server.py — 3317 lines)                   │
│  ├─ FastAPI HTTP routes (health, memory REST)       │
│  ├─ Socket.IO events (~40 event handlers)           │
│  ├─ AudioLoop (lumina.py) — Gemini Live API         │
│  │   ├─ VAD + transcription streaming               │
│  │   ├─ Tool call dispatch (12+ built-in tools)     │
│  │   ├─ ACTION_REGISTRY dispatch (16 action modules)│
│  │   └─ Auto-retry with exponential backoff         │
│  ├─ Memory subsystem                                │
│  │   ├─ memory_store.py — SQLite lifecycle DB       │
│  │   ├─ memory_engine.py — Hybrid retrieval (FTS5+FAISS)│
│  │   └─ Transcript aggregation + indexing           │
│  ├─ Agents                                          │
│  │   ├─ CadAgent (OpenSCAD → STL)                   │
│  │   ├─ KasaAgent (TP-Link smart home)              │
│  │   ├─ PrinterAgent (Moonraker/OctoPrint)          │
│  │   └─ WebAgent (headless browser automation)      │
│  ├─ persona_engine.py — Behavioral engine           │
│  ├─ action_router.py — Deterministic NL→CRUD parser │
│  ├─ authenticator.py — Face auth (MediaPipe)        │
│  ├─ project_manager.py — Project file management    │
│  └─ tools/ — Gemini func declarations + browser CDP │
└─────────────────────────────────────────────────────┘
```

**Key Runtime Flow:**
1. Electron starts → spawns `server.py` → waits for `/health`
2. Frontend connects via Socket.IO → emits `start_audio` with mic device
3. Backend creates `AudioLoop` → connects to Gemini Live API
4. Audio flows: mic → VAD → Gemini → TTS → speaker
5. Text flows: user_input → memory intercept → action router → memory injection → persona context → Gemini
6. Tool calls: Gemini → permission check → confirmation gate → execute → FunctionResponse
7. Panel CRUD: Socket.IO events → memory_store.py → broadcast updates

### 1.2 Jarvis-MK37 (Feature Donor)

**Stack:** Python + Gemini Live API + PySide6 UI (standalone desktop app)

```
┌─────────────────────────┐
│  JarvisUI (PySide6)     │
│  └─ Text input + audio  │
├─────────────────────────┤
│  JarvisLive (main.py)   │
│  ├─ Gemini Live session │
│  ├─ Tool dispatch       │
│  ├─ Agent system:       │
│  │   ├─ planner.py      │
│  │   ├─ executor.py     │
│  │   ├─ error_handler.py│
│  │   └─ task_queue.py   │
│  ├─ Memory manager      │
│  └─ 16 action modules   │
├─────────────────────────┤
│  actions/               │
│  ├─ browser_control.py  │  (multi-browser CDP, 40KB)
│  ├─ computer_control.py │  (pyautogui-based)
│  ├─ game_updater.py     │  (Steam/Epic, 42KB)
│  ├─ code_helper.py      │  (write/edit/run code)
│  ├─ dev_agent.py        │  (multi-file project builder)
│  ├─ flight_finder.py    │  (Google Flights scraper)
│  ├─ youtube_video.py    │  (play/summarize/trending)
│  └─ ... (14 more)       │
└─────────────────────────┘
```

### 1.3 OpenJarvis (Architecture Donor)

**Stack:** Python SDK + modular registry-based architecture

```
┌──────────────────────────────────────┐
│  SDK (Jarvis, JarvisSystem, Builder) │
├──────────────────────────────────────┤
│  core/                               │
│  ├─ registry.py — RegistryBase<T>    │
│  │   ├─ AgentRegistry                │
│  │   ├─ ToolRegistry                 │
│  │   ├─ MemoryRegistry               │
│  │   ├─ SkillRegistry                │
│  │   ├─ EngineRegistry               │
│  │   └─ 8 more typed registries      │
│  ├─ config.py — JarvisConfig (57KB!) │
│  ├─ events.py — EventBus             │
│  └─ types.py — Message, Role, etc.   │
├──────────────────────────────────────┤
│  agents/ (13 implementations)        │
│  ├─ orchestrator.py                  │
│  ├─ operative.py                     │
│  ├─ deep_research.py                 │
│  ├─ morning_digest.py                │
│  └─ ... ReAct, Claude Code, RLM     │
├──────────────────────────────────────┤
│  tools/ (30+ tools)                  │
│  ├─ browser.py, shell_exec.py        │
│  ├─ file_read/write, git_tool        │
│  ├─ knowledge_tools, db_query        │
│  ├─ mcp_adapter.py                   │
│  └─ ... calculator, PDF, image, TTS  │
├──────────────────────────────────────┤
│  skills/ (composable multi-tool)     │
│  ├─ SkillManager, SkillExecutor      │
│  ├─ parser, loader, importer         │
│  └─ tool_adapter, tool_translator    │
├──────────────────────────────────────┤
│  workflow/ (DAG-based)               │
│  ├─ engine.py, graph.py, builder.py  │
│  └─ types.py, loader.py             │
├──────────────────────────────────────┤
│  scheduler/                          │
│  ├─ scheduler.py, store.py, tools.py │
└──────────────────────────────────────┘
```

---

## 2. FEATURE MATRIX

| Feature | Lumina | Jarvis-MK37 | OpenJarvis | Action |
|---|---|---|---|---|
| **Voice I/O (Gemini Live)** | ✅ Full (VAD, mic gate, transcription streaming) | ✅ Basic (sounddevice) | ❌ Text-only SDK | Keep Lumina |
| **Persona Engine** | ✅ Rich (emotion, debate, idle mind, jealousy, singing) | ❌ Static prompt | ❌ None | Keep Lumina |
| **Memory Store (lifecycle)** | ✅ Full (pending/active/dormant, FTS, FAISS hybrid) | ⚠️ Basic JSON (category/key/value) | ✅ Pluggable backends (SQLite, chunking) | Keep Lumina, adapt OJ patterns |
| **Panel CRUD (Quests/Events/Archive)** | ✅ Full with NL action router | ❌ None | ❌ None | Keep Lumina |
| **CAD Generation** | ✅ CadAgent (OpenSCAD→STL, iterate) | ❌ None | ❌ None | Keep Lumina |
| **3D Printer Control** | ✅ PrinterAgent (Moonraker/OctoPrint, slicing) | ❌ None | ❌ None | Keep Lumina |
| **Smart Home (Kasa)** | ✅ KasaAgent (discover, on/off, color, brightness) | ❌ None | ❌ None | Keep Lumina |
| **Local Browser Control (CDP)** | ✅ 81KB (Brave, CDP, type/click/scroll/tabs) | ✅ 40KB (multi-browser CDP) | ✅ browser.py (CDP, axtree) | Keep Lumina, import MK37 multi-browser |
| **Face Authentication** | ✅ MediaPipe | ❌ None | ❌ None | Keep Lumina |
| **Project Management** | ✅ project_manager.py | ❌ None | ❌ None | Keep Lumina |
| **Tool Permission Gating** | ✅ Full (env var clamp + per-tool) | ❌ None | ❌ None | Keep Lumina |
| **Tool Confirmation UI** | ✅ Full (popup + gated actions) | ❌ None | ❌ None | Keep Lumina |
| **Electron Desktop App** | ✅ Full | ✅ PySide6 (different) | ❌ CLI/SDK | Keep Lumina |
| **React UI + Panels** | ✅ Full (Sidebar, 5 panels) | ❌ PySide6 | ❌ None | Keep Lumina |
| **open_app** | ✅ Via ACTION_REGISTRY | ✅ Original | ❌ | Already imported |
| **web_search** | ✅ Via ACTION_REGISTRY | ✅ Original | ✅ web_search.py | Already imported |
| **weather_report** | ✅ Via ACTION_REGISTRY | ✅ Original | ❌ | Already imported |
| **send_message** | ✅ Via ACTION_REGISTRY | ✅ Original | ❌ | Already imported |
| **computer_control** | ✅ Via ACTION_REGISTRY | ✅ Original (richer) | ❌ | Already imported |
| **computer_settings** | ✅ Via ACTION_REGISTRY | ✅ Original | ❌ | Already imported |
| **desktop_control** | ✅ Via ACTION_REGISTRY | ✅ Original | ❌ | Already imported |
| **file_controller** | ✅ Via ACTION_REGISTRY | ✅ Original | ✅ file_read/write | Already imported |
| **screen_processor** | ✅ Via ACTION_REGISTRY | ✅ Original | ❌ | Already imported |
| **cmd_control** | ✅ Via ACTION_REGISTRY | ❌ (via computer_control) | ❌ | Lumina-original |
| **spotify_control** | ✅ Via ACTION_REGISTRY | ❌ | ❌ | Lumina-original |
| **youtube_control** | ✅ Via ACTION_REGISTRY | ✅ youtube_video.py | ❌ | Already imported |
| **browser_open** | ✅ Via ACTION_REGISTRY | ❌ (via browser_control) | ❌ | Lumina-original |
| **reminder** | ✅ Via ACTION_REGISTRY | ✅ Task Scheduler | ❌ | Already imported |
| **code_helper** | ❌ Not in Lumina | ✅ Write/edit/run code | ✅ code_interpreter | **IMPORT from MK37** |
| **dev_agent** | ❌ Not in Lumina | ✅ Multi-file project builder | ❌ | **IMPORT from MK37** |
| **game_updater** | ❌ Not in Lumina | ✅ Steam/Epic (42KB) | ❌ | **IMPORT from MK37** |
| **flight_finder** | ❌ Not in Lumina | ✅ Google Flights scraper | ❌ | **IMPORT from MK37** |
| **Agent Planner** | ❌ | ✅ Multi-step planning | ✅ Orchestrator | **IMPORT MK37 planner, adapt OJ orchestrator** |
| **Agent Executor** | ❌ | ✅ Code generation + error recovery | ✅ executor.py | **IMPORT from MK37** |
| **Agent Task Queue** | ❌ | ✅ Priority queue | ❌ | **IMPORT from MK37** |
| **Registry Pattern** | ⚠️ ad-hoc ACTION_REGISTRY dict | ❌ | ✅ RegistryBase<T> (elegant) | **ADAPT from OpenJarvis** |
| **Skill System** | ❌ | ❌ | ✅ Full (parse, load, execute, compose) | **Future import** |
| **Workflow Engine** | ❌ | ❌ | ✅ DAG-based workflow engine | **Future import** |
| **Scheduler** | ❌ | ❌ | ✅ Cron-like scheduler | **Future import** |
| **EventBus** | ❌ (uses Socket.IO directly) | ❌ | ✅ Internal event bus | **Future import** |
| **MCP Adapter** | ❌ | ❌ | ✅ mcp_adapter.py | **Future import** |
| **Deep Research Agent** | ❌ | ❌ | ✅ deep_research.py | **Future import** |
| **Morning Digest** | ❌ | ❌ | ✅ morning_digest.py | **Future import** |
| **Git Tool** | ❌ | ❌ | ✅ git_tool.py | **Future import** |
| **DB Query Tool** | ❌ | ❌ | ✅ db_query.py | **Future import** |
| **PDF Tool** | ❌ | ❌ | ✅ pdf_tool.py | **Future import** |
| **Image Tool** | ❌ | ❌ | ✅ image_tool.py | **Future import** |
| **TTS Tool** | ❌ (uses Gemini native) | ❌ | ✅ text_to_speech.py | N/A (Lumina uses Gemini TTS) |

---

## 3. CONFLICT MAP

### 3.1 Direct Conflicts (Must Resolve)

| Area | Lumina | MK37 | Resolution |
|---|---|---|---|
| **Browser control** | `local_browser_control.py` (Brave CDP, 81KB) | `browser_control.py` (multi-browser CDP, 40KB) | Merge: keep Lumina's local_browser_control as primary, import MK37's multi-browser selection logic |
| **Memory format** | SQLite lifecycle DB (state machine) | JSON flat file (category/key/value) | Keep Lumina's (far superior) |
| **Tool dispatch** | `lumina.py` inline if/elif chain (~600 lines) | `main.py` inline if/elif chain (~350 lines) | Refactor both → registry-based dispatch |
| **System prompt** | In-code config dict + persona_engine | `core/prompt.txt` file | Keep Lumina's dynamic system, allow file-based overrides |
| **Audio I/O** | PyAudio + custom VAD | sounddevice | Keep Lumina's (more mature VAD) |

### 3.2 Naming Conflicts

| Lumina name | MK37 name | Note |
|---|---|---|
| `browser_control` (tool) | `browser_control` (action) | Different implementations. Lumina's is headless, MK37's is CDP. Already coexist. |
| `youtube_control.py` | `youtube_video.py` | Same feature, different names. Lumina already has a port. |
| `reminder` (action) | `reminder` (action) | Same function, already imported. |

### 3.3 Architecture Gaps

1. **No registry pattern** — Lumina uses a flat dict `ACTION_REGISTRY` and inline tool dispatch. OpenJarvis has elegant `RegistryBase<T>` with typed subclasses.
2. **No agent abstraction** — Lumina's agents (CadAgent, KasaAgent, etc.) are domain-specific classes with no shared interface. OpenJarvis has `BaseAgent`, `ToolUsingAgent`, `AgentContext`, `AgentResult`.
3. **No skill/workflow system** — Lumina has no concept of composable multi-tool operations.
4. **No scheduler** — Events panel is UI-only, no backend cron-like execution.
5. **God file problem** — `server.py` is 3317 lines, `lumina.py` is 1907 lines. Both need decomposition.

---

## 4. DETECTED BUGS & ISSUES

### 4.1 Code Bugs

1. **Indentation bug in confirmation logic** (`lumina.py:1111-1114`):
   ```python
   if self.on_tool_confirmation:
       import uuid
       request_id = str(uuid.uuid4())
   print(f"...")  # <-- This line runs even when on_tool_confirmation is None!
   ```
   The `print` and subsequent lines are outside the `if` block. If `on_tool_confirmation` is None, `request_id` is undefined → `NameError`.

2. **Duplicate denial check** (`lumina.py:1134-1156`): The `if not confirmed` block is duplicated — same check appears twice in sequence.

3. **save_memory handler writes nothing** (`server.py:2296-2300`):
   ```python
   with open(filename, 'w', encoding='utf-8') as f:
       for msg in messages:
           sender = msg.get('sender', 'Unknown')
           text = msg.get('text', '')
   # <-- No f.write() call! File is created empty.
   ```

4. **Late import at module level** (`server.py:2254-2258`):
   ```python
   import json
   from datetime import datetime
   from pathlib import Path
   # ... (imports)
   ```
   These imports appear at line 2254 (mid-file), after 2200+ lines of code. While Python allows this, it's a code smell and breaks convention.

5. **`cv2.CAP_AVFOUNDATION`** used in `lumina.py:1714` — this is macOS-only. On Windows, should use `cv2.CAP_DSHOW` or just `0`.

### 4.2 Architecture Issues

1. **server.py is a god file** — 3317 lines with ~40 socket handlers, memory lifecycle logic, action routing, idle monitoring, all interleaved.
2. **Tool dispatch in lumina.py is a 600-line if/elif chain** — unmaintainable, hard to add new tools.
3. **No error boundaries** — Many `asyncio.create_task()` calls without error handlers (fire-and-forget).
4. **Global mutable state** — `audio_loop`, `memory_engine`, `authenticator`, etc. are module-level globals mutated from multiple async contexts.
5. **Race condition risk** — `_pending_text_queue` checked and cleared without locking in `user_input`.

---

## 5. ACTIVE vs LEGACY FILES

### Active (in runtime path):
- `backend/server.py` ✅
- `backend/lumina.py` ✅
- `backend/action_router.py` ✅
- `backend/memory_store.py` ✅
- `backend/memory_engine.py` ✅
- `backend/persona_engine.py` ✅
- `backend/cad_agent.py` ✅
- `backend/printer_agent.py` ✅
- `backend/kasa_agent.py` ✅
- `backend/web_agent.py` ✅
- `backend/project_manager.py` ✅
- `backend/authenticator.py` ✅
- `backend/actions/*.py` ✅ (all 16)
- `backend/tools/__init__.py` ✅
- `backend/tools/browser_control.py` ✅
- `backend/tools/local_browser_control.py` ✅
- `src/Ui_TEST/AppTest.jsx` ✅ (actual UI)
- `src/Ui_TEST/panels/*.jsx` ✅
- `src/components/*.jsx` ✅ (imported by AppTest)
- `electron/main.js` ✅

### Legacy / Test only:
- `src/App.jsx` — just re-exports AppTest
- `backend/capture_face.py` — standalone face capture utility
- `backend/temp_cad_gen.py` — temporary CAD test
- `backend/verify_cad.py` — test utility
- `backend/verify_iteration_mock.py` — test utility
- `backend/test_*.py` — test files (4 files)
- `backend/.memory/` — empty
- `src/Ui_TEST/main_test.jsx` — standalone test entry

### Source references (not in runtime):
- `sources/Jarvis-MK37-main/` — feature donor
- `sources/OpenJarvis-main/` — architecture donor

---

## 6. PRIORITY IMPORT LIST (from MK37 & OpenJarvis)

### Priority 1 — High Value, Low Risk
1. **code_helper.py** from MK37 → new action module
2. **dev_agent.py** from MK37 → new action module
3. **game_updater.py** from MK37 → new action module
4. **flight_finder.py** from MK37 → new action module
5. **Agent planner/executor/task_queue** from MK37 → `backend/agent/`
6. **RegistryBase pattern** from OpenJarvis → `backend/core/registry.py`

### Priority 2 — Medium Value, Needs Adaptation
7. **Multi-browser support** from MK37's browser_control → merge into local_browser_control
8. **Agent error_handler** from MK37 → adapt for Lumina's async context
9. **Skill system concepts** from OpenJarvis → future phase
10. **EventBus** from OpenJarvis → future phase

### Priority 3 — Future / Research
11. Workflow engine from OpenJarvis
12. Scheduler from OpenJarvis
13. MCP adapter from OpenJarvis
14. Deep research agent from OpenJarvis
15. Morning digest from OpenJarvis
