# Lumina File-by-File Merge Plan

## Guiding Principles
- Lumina is the primary source of truth and product identity
- Never break existing startup or features
- Import only what's missing or demonstrably better
- Adapt architecture patterns, don't copy-paste codebases
- Incremental changes with verification at each step

---

## PHASE 3: Bug Fixes & Stabilization (Do First)

### Bug 1: Indentation error in tool confirmation (`lumina.py:1111-1114`)
- **File:** `backend/lumina.py`
- **Lines:** ~1111-1156
- **Problem:** `print(f"...")` and `future = asyncio.Future()` etc. are outside the `if self.on_tool_confirmation:` block. If callback is None, `request_id` is undefined → NameError at runtime.
- **Fix:** Indent lines 1114-1131 into the `if` block. Add else branch that auto-confirms (no UI → proceed).
- **Risk:** Low — only affects edge case where confirmation callback isn't set.

### Bug 2: Duplicate denial check (`lumina.py:1134-1156`)
- **File:** `backend/lumina.py`
- **Lines:** ~1134-1156
- **Problem:** `if not confirmed:` block appears twice in sequence (exact duplicate).
- **Fix:** Remove the second duplicate block (lines ~1146-1156).
- **Risk:** None — dead code removal.

### Bug 3: save_memory writes empty file (`server.py:2296-2300`)
- **File:** `backend/server.py`
- **Lines:** ~2296-2300
- **Problem:** Loop iterates messages but never calls `f.write()`.
- **Fix:** Add `f.write(f"[{sender}]: {text}\n")` inside the loop.
- **Risk:** None — fixing a broken feature.

### Bug 4: macOS-only video capture (`lumina.py:1714`)
- **File:** `backend/lumina.py`
- **Line:** ~1714
- **Problem:** `cv2.CAP_AVFOUNDATION` is macOS-only. Windows needs `cv2.CAP_DSHOW` or default `0`.
- **Fix:** Use platform detection: `cv2.CAP_DSHOW if sys.platform == 'win32' else cv2.CAP_AVFOUNDATION`
- **Risk:** Low — video mode is rarely used but should work on Windows.

### Bug 5: Mid-file imports (`server.py:2254-2258`)
- **File:** `backend/server.py`
- **Lines:** ~2254-2258
- **Problem:** `import json`, `from datetime import datetime`, `from pathlib import Path` appear at line 2254. These are already imported at top of file.
- **Fix:** Remove the duplicate mid-file imports.
- **Risk:** None — they're redundant.

---

## PHASE 4: Registry & Agent Architecture

### Step 4.1: Create `backend/core/registry.py`
- **Source:** Adapt from OpenJarvis `core/registry.py`
- **What to take:** `RegistryBase<T>` generic class with `register()`, `get()`, `create()`, `items()`, `keys()`, `contains()`, `clear()`
- **What to adapt:** Simplify — Lumina only needs `ToolRegistry`, `AgentRegistry`, `ActionRegistry` initially. Skip Model/Engine/Benchmark/Channel/Learning/Speech/Compression/TTS/Connector registries.
- **New file:** `backend/core/__init__.py`, `backend/core/registry.py`
- **Risk:** None — additive, no existing code changes.

### Step 4.2: Migrate ACTION_REGISTRY to new registry
- **File:** `backend/actions/__init__.py`
- **Change:** Replace flat dict with `ActionRegistry.register()` decorators on each action module.
- **Backward compat:** Keep `ACTION_REGISTRY` as a property of `ActionRegistry._entries()` or alias.
- **Risk:** Low — existing dispatch in `lumina.py` uses `ACTION_REGISTRY` dict, alias preserves it.

### Step 4.3: Create `backend/core/base_agent.py`
- **Source:** Inspired by OpenJarvis `agents/_stubs.py`
- **What to define:** `BaseAgent` ABC with `async execute(context) -> AgentResult`, `name`, `description`, `required_tools`.
- **What NOT to do:** Don't force-refactor CadAgent/KasaAgent/PrinterAgent/WebAgent yet — wrap them later.
- **Risk:** None — additive.

### Step 4.4: Create tool registry for Gemini function declarations
- **File:** `backend/tools/__init__.py`
- **Change:** Each tool declaration becomes a registered entry instead of a list. The list is built from registry at AudioLoop init time.
- **Benefit:** New tools auto-register, permissions can filter by registry key.
- **Risk:** Low — must ensure Gemini config still gets the same list.

---

## PHASE 5: Feature Import

### Step 5.1: Import `code_helper.py` from MK37
- **Source:** `sources/Jarvis-MK37-main/actions/code_helper.py` (19KB)
- **Target:** `backend/actions/code_helper.py`
- **Adaptations needed:**
  - Replace `_get_api_key()` with Lumina's settings/env approach
  - Add `ACTION_REGISTRY` registration
  - Add Gemini function declaration to `backend/tools/__init__.py`
  - Add to permission system in `settings.json`
- **Dependencies:** `google.generativeai` (already available in Lumina env)
- **Risk:** Low — self-contained action.

### Step 5.2: Import `dev_agent.py` from MK37
- **Source:** `sources/Jarvis-MK37-main/actions/dev_agent.py` (20KB)
- **Target:** `backend/actions/dev_agent.py`
- **Adaptations:** Same as code_helper + integrate with project_manager for output directory.
- **Dependencies:** Same as code_helper
- **Risk:** Low-Medium — multi-file generation needs sandboxing review.

### Step 5.3: Import `game_updater.py` from MK37
- **Source:** `sources/Jarvis-MK37-main/actions/game_updater.py` (42KB)
- **Target:** `backend/actions/game_updater.py`
- **Adaptations:** Replace API key loading, add registration, add function declaration, add permission toggle.
- **Dependencies:** Steam/Epic CLI tools (optional — graceful fallback)
- **Risk:** Medium — large file, Windows-specific, needs testing.

### Step 5.4: Import `flight_finder.py` from MK37
- **Source:** `sources/Jarvis-MK37-main/actions/flight_finder.py` (12KB)
- **Target:** `backend/actions/flight_finder.py`
- **Adaptations:** Same pattern as above.
- **Dependencies:** Web scraping libraries
- **Risk:** Low — self-contained.

### Step 5.5: Import Agent Planner/Executor from MK37
- **Source:** `sources/Jarvis-MK37-main/agent/` (planner.py, executor.py, error_handler.py, task_queue.py)
- **Target:** `backend/agent/` (new directory)
- **Adaptations:**
  - Replace `_get_api_key()` with Lumina's config
  - Adapt planner tool list to match Lumina's ACTION_REGISTRY
  - Wire executor into lumina.py's tool dispatch for `agent_task` tool
  - Add `agent_task` function declaration to tools/__init__.py
- **Dependencies:** google.generativeai
- **Risk:** Medium — needs careful integration with async AudioLoop context.

### Step 5.6: Merge MK37 multi-browser into local_browser_control
- **Source:** `sources/Jarvis-MK37-main/actions/browser_control.py` (40KB)
- **Target:** Enhance `backend/tools/local_browser_control.py`
- **What to take:** Multi-browser detection logic (Chrome, Edge, Firefox, Opera, Brave, Vivaldi), browser-specific CDP port finding, incognito mode support.
- **What NOT to take:** Lumina's existing CDP action system, confirmation gating, and tab management are superior — keep those.
- **Risk:** Medium — browser control is complex, needs careful merge.

---

## PHASE 6: Decomposition (Reduce God Files)

### Step 6.1: Extract socket handlers from `server.py`
- **Current:** All ~40 socket event handlers in one file.
- **Plan:** Create `backend/api/socket_handlers/`:
  - `audio.py` — start_audio, stop_audio, pause_audio, resume_audio
  - `memory.py` — save_memory, upload_memory, add_memory, get_memories, memory_decision
  - `panel_crud.py` — list_quests, create_quest, etc. (all panel CRUD)
  - `devices.py` — discover_kasa, control_kasa, discover_printers, add_printer, print_stl
  - `cad.py` — generate_cad, iterate_cad
  - `settings.py` — get_settings, update_settings, update_tool_permissions
- **Each file:** Receives `sio`, `app`, globals as parameters or via a context object.
- **Risk:** Medium — requires careful dependency management. Do incrementally.

### Step 6.2: Extract tool dispatch from `lumina.py`
- **Current:** ~600 lines of if/elif in `receive_audio()`.
- **Plan:** Create `backend/tool_dispatcher.py` with a `dispatch_tool(fc, context) -> FunctionResponse` function. Use registry lookup instead of if/elif.
- **Risk:** Medium — must maintain exact same behavior for each tool.

---

## EXECUTION ORDER

```
Phase 3 (Bugs):     Bug1 → Bug2 → Bug3 → Bug4 → Bug5        [~30 min]
Phase 4 (Registry):  4.1 → 4.2 → 4.3 → 4.4                  [~2 hours]
Phase 5 (Import):    5.1 → 5.2 → 5.4 → 5.3 → 5.5 → 5.6     [~4 hours]
Phase 6 (Decompose): 6.1 → 6.2                                [~3 hours]
```

Each step: implement → verify startup → verify affected feature → commit.
