# Recovery Audit Report

## Generated: Phase 0 — Recovery-Aware Audit of Prior Modifications

---

## AUDITED FILES

### 1. `backend/core/registry.py` (NEW FILE)

- **Status:** KEEP
- **Risk Level:** LOW
- **What it does:** Defines `RegistryBase<T>` generic class with `register()`, `get()`, `create()`, `items()`, `keys()`, `contains()`, `clear()`. Three subclasses: `ActionRegistry`, `AgentRegistry`, `ToolRegistry`.
- **Import dependencies:** Only stdlib (`typing`). No external deps.
- **Who imports it:** `backend/core/__init__.py`, `backend/actions/__init__.py`
- **Analysis:** Self-contained, well-structured. Uses only stdlib. Safe as-is.
- **Required follow-up:** None.

---

### 2. `backend/core/__init__.py` (NEW FILE)

- **Status:** REVISE
- **Risk Level:** MEDIUM
- **What it does:** `from core.registry import ActionRegistry, AgentRegistry, ToolRegistry`
- **Problem:** Uses relative-looking `from core.registry import ...`. This only works if `backend/` is on `sys.path`. That IS the case at runtime (server.py line 45 does `sys.path.append`). But the import style is fragile — if someone imports this package from a different working directory or test runner, it breaks.
- **Analysis:** Functionally fine at Lumina runtime. But this file is also **currently unused** — nobody does `from core import ActionRegistry`. The actual consumer (`actions/__init__.py`) imports directly `from core.registry import ActionRegistry`.
- **Required follow-up:** This file is harmless but unused. Keep it but note it's not yet part of any runtime path.

---

### 3. `backend/core/base_agent.py` (NEW FILE)

- **Status:** KEEP (UNUSED)
- **Risk Level:** LOW (no runtime impact)
- **What it does:** Defines `BaseAgent` ABC, `AgentContext`, `AgentResult` dataclasses.
- **Who imports it:** **Nobody.** Purely additive, never referenced.
- **Analysis:** Clean, well-defined abstractions. Uses only stdlib. No risk.
- **Required follow-up:** None until actively adopted by an agent.

---

### 4. `backend/actions/__init__.py` (MODIFIED)

- **Status:** REVISE — one issue identified
- **Risk Level:** **HIGH** — this is an import-time file on the critical startup path
- **What changed:**
  1. Added `import sys, os` + `sys.path.insert(0, _backend_dir)` hack
  2. Changed `_try_register` to use `ActionRegistry.register_value()` instead of plain dict insert
  3. Added `code_helper` registration
  4. `ACTION_REGISTRY = ActionRegistry._entries()` — alias to internal dict
- **Import chain:** `server.py` → `import lumina` → `lumina.py` line 26: `from actions import ACTION_REGISTRY` → triggers `actions/__init__.py` → `from core.registry import ActionRegistry`
- **Analysis of risks:**
  - **sys.path hack (lines 20-23):** `_backend_dir` resolves to `backend/` parent. This is REDUNDANT — `server.py` line 45 already adds `backend/` to `sys.path` before `import lumina`. But it's a safety net and harmless.
  - **`ActionRegistry.register_value()` instead of dict insert:** Functionally equivalent. `register_value` raises `ValueError` on duplicate keys. The original code silently overwrote. This is actually *stricter* — if the module is re-imported or hot-reloaded, it will crash. **This is a latent bug** but won't trigger in normal startup since actions/__init__.py runs once.
  - **`ACTION_REGISTRY = ActionRegistry._entries()`:** This returns a reference to the **same internal dict object**, not a copy. So `ACTION_REGISTRY[key]` in lumina.py still works. Verified: `_entries()` returns the class attribute dict directly. **This is safe.**
  - **`code_helper` registration:** Added at line 56. The module `actions.code_helper` will be imported at startup. If it fails (missing dep), it's caught by `_try_register`'s try/except. **Safe — graceful degradation.**
- **Critical finding:** The `code_helper.py` uses `import google.generativeai as genai` internally (lazy, at call time), not at import time. So registration will succeed. The import only fails if someone actually calls the tool and the package isn't installed.
- **Required follow-up:**
  1. Verify `from core.registry import ActionRegistry` resolves at Lumina startup time
  2. Consider whether the duplicate-key `ValueError` in `register_value` could cause issues during development/testing

---

### 5. `backend/actions/code_helper.py` (NEW FILE)

- **Status:** REVISE
- **Risk Level:** MEDIUM
- **What it does:** 547-line code helper action ported from MK37. Supports write/edit/explain/run/build/optimize/screen_debug.
- **Problems identified:**
  1. **Does NOT use Lumina's `_gemini_helper.py` pattern.** Other Lumina actions use `backend/actions/_gemini_helper.py` for API key resolution and model creation. This file has its own `_get_api_key()` that reads from env var OR `settings.json` — but `settings.json` does NOT contain a `gemini_api_key` field, so the fallback always returns `""`. The correct Lumina pattern is `_gemini_helper.get_api_key()` which uses `dotenv` + `GEMINI_API_KEY` env var.
  2. **Hardcoded `DESKTOP = Path.home() / "Desktop"`** — no project_manager integration. MK37-ism; fine for now but not aligned with Lumina's project-based file model.
  3. **`_take_screenshot()` uses `pyautogui`** — may not be in Lumina's conda env. Import is guarded (`try/except`), so no startup risk.
  4. **`_screen_debug_action` uses `google.genai` (newer SDK)** while `_get_gemini` uses `google.generativeai` (older SDK). Mixed SDK usage in the same file.
- **Required follow-up:**
  1. Replace `_get_api_key()` / `_get_gemini()` with Lumina's `_gemini_helper` pattern
  2. Or at minimum ensure `GEMINI_API_KEY` env var is set (which Lumina already does via `load_dotenv` in lumina.py)

---

### 6. `backend/tools/__init__.py` (MODIFIED)

- **Status:** KEEP
- **Risk Level:** LOW
- **What changed:**
  1. Added `code_helper_tool` function declaration dict (lines 490-513)
  2. Added `code_helper_tool` to the `tools_list` array (line 537)
- **Analysis:** The dict is well-formed and follows the exact pattern of all other tool declarations in the file. Adding it to `tools_list` means Gemini will see it as an available function. This is purely additive.
- **Risk:** If `code_helper` isn't registered in `ACTION_REGISTRY` (e.g., import failure), Gemini could still call it, and lumina.py's dispatch would hit the `elif fc.name in ACTION_REGISTRY` check at line 1629 — it would NOT match, and fall through to an unhandled tool error path. But this is the same risk for any action tool — existing behavior.
- **Required follow-up:** None.

---

### 7. `backend/lumina.py` — Edit 1: Confirmation indentation fix (lines ~1109-1147)

- **Status:** KEEP — correct fix
- **Risk Level:** LOW
- **What changed:**
  - Original: lines after `if self.on_tool_confirmation:` (print, future, etc.) were at the WRONG indent level — they ran unconditionally, causing `NameError` when `request_id` was not defined.
  - Fix: Indented those lines into the `if` block. Added `else` branch with auto-confirm log message.
  - Removed duplicate `if not confirmed:` block.
- **Analysis:** The original code was genuinely broken. The fix is correct:
  - When `self.on_tool_confirmation` exists: prompt user, await confirmation, deny if rejected.
  - When it doesn't: auto-confirm (log only, fall through to execution).
  - The `continue` in the denial branch correctly skips to the next tool call.
- **Flow after fix:** `confirmation_required=True` → enter `else` block → `if self.on_tool_confirmation` → await user → if denied: `continue` → if confirmed: fall through to tool dispatch at line 1149. If `on_tool_confirmation` is None → else branch: log auto-confirm → fall through.
- **Required follow-up:** None.

---

### 8. `backend/lumina.py` — Edit 2: Platform-aware video capture (line ~1704-1707)

- **Status:** KEEP
- **Risk Level:** LOW
- **What changed:** `cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)` → platform detection using `sys.platform == 'win32'` to pick `CAP_DSHOW` vs `CAP_AVFOUNDATION`.
- **Analysis:** Correct fix. `CAP_AVFOUNDATION` is macOS-only API. Lumina runs on Windows. However, `import sys as _sys` inside the async method is slightly ugly — `sys` is already imported at module level. Minor style issue, not a bug.
- **Required follow-up:** Could simplify to use module-level `sys` instead of `import sys as _sys`, but functionally fine.

---

### 9. `backend/server.py` — Edit 1: save_memory f.write fix (line ~2294)

- **Status:** KEEP — correct fix
- **Risk Level:** LOW
- **What changed:** Added `f.write(f"[{sender}]: {text}\n")` inside the message loop that previously iterated without writing.
- **Analysis:** The original code opened a file, looped over messages extracting sender/text, then closed the file — producing an empty file every time. This is clearly a bug. The fix is correct.
- **Required follow-up:** None.

---

### 10. `backend/server.py` — Edit 2: Removed mid-file imports (lines ~2254-2258)

- **Status:** REVISE — need to verify what was actually removed
- **Risk Level:** MEDIUM
- **What was claimed to be removed:** `import json`, `from datetime import datetime`, `from pathlib import Path` that appeared mid-file.
- **Current state at line 2254:** The line now shows `@sio.event` / `async def video_frame`. The imports are gone.
- **Analysis:** `json`, `datetime`, and `Path` are all imported at the top of server.py (lines 37, 39, 40). Removing mid-file duplicates is safe.
- **Concern:** The prior edit description said "5 lines of duplicate imports + blank/comment lines" were removed. I need to verify nothing else was caught in the deletion.
- **Verification:** Line 2252 = `print(f"[SERVER DEBUG] Message sent...")` → line 2253 = blank → line 2254 = `@sio.event` / `async def video_frame`. This looks correct — the transition from end of `user_input` handler to `video_frame` handler is clean.
- **Required follow-up:** Verified clean. No action needed.

---

### 11. `ARCHITECTURE_REPORT.md` (NEW FILE)

- **Status:** KEEP
- **Risk Level:** NONE (documentation only)
- **Required follow-up:** May need updates as work progresses.

---

### 12. `MERGE_PLAN.md` (NEW FILE)

- **Status:** KEEP
- **Risk Level:** NONE (documentation only)
- **Required follow-up:** Will be superseded by UPDATED_MERGE_PLAN.md.

---

## SUMMARY ASSESSMENTS

### 1. Startup Risk Summary

**Overall: MEDIUM**

The critical startup chain is:
```
server.py
  └─ sys.path.append(backend/)  ← line 45
  └─ import lumina               ← line 47
       └─ from actions import ACTION_REGISTRY  ← lumina.py line 26
            └─ from core.registry import ActionRegistry  ← actions/__init__.py line 25
                 (requires backend/ on sys.path — YES, set by server.py line 45)
            └─ _try_register("code_helper", ...) ← line 56
                 (imports code_helper.py — uses google.generativeai lazily, safe)
            └─ ACTION_REGISTRY = ActionRegistry._entries()  ← line 60
       └─ from tools import tools_list  ← lumina.py line 25
            (now includes code_helper_tool — dict, no import risk)
```

**Key risk:** If `lumina.py` is imported directly (not via server.py), `backend/` may not be on sys.path, and `from core.registry import ActionRegistry` would fail. The `sys.path.insert` in actions/__init__.py mitigates this. **Acceptable for now.**

### 2. Import Risk Summary

**Overall: LOW-MEDIUM**

- `core.registry` — stdlib only, no external deps. **LOW.**
- `core.base_agent` — stdlib only, unused. **LOW.**
- `actions/code_helper.py` — `google.generativeai` is lazy-imported at call time, not import time. Existence of `_gemini_helper.py` already proves the package is expected in the env. **LOW** for startup, **MEDIUM** if the tool is called and API key isn't found.
- No circular imports detected. `core` is a leaf package (no Lumina imports).

### 3. Runtime Risk Summary

**Overall: LOW**

- **lumina.py confirmation fix:** Correct. The original was broken; the fix restores intended behavior.
- **lumina.py video capture fix:** Correct. Windows-safe.
- **server.py save_memory fix:** Correct. Broken feature restored.
- **server.py import removal:** Verified safe — duplicates of top-level imports.
- **ACTION_REGISTRY alias:** Points to same dict object as `ActionRegistry._entries()`. All existing `ACTION_REGISTRY[name]` reads in lumina.py still work. **Verified safe.**
- **tools_list addition:** One more dict in the Gemini function declarations list. Additive, no behavioral change to existing tools.

### 4. Recommended Immediate Actions

| Priority | Action | Why |
|---|---|---|
| **1 (MUST)** | Run startup import validation | Confirm the `core.registry` import chain works end-to-end |
| **2 (SHOULD)** | Revise `code_helper.py` to use `_gemini_helper.py` | Aligns with Lumina conventions, avoids silent empty API key |
| **3 (SHOULD)** | Simplify `lumina.py` video fix | Use module-level `sys` instead of `import sys as _sys` (style only) |
| **4 (NICE)** | Add `code_helper` to `settings.json` tool_permissions | Currently absent — will default to "unknown tool" → confirmation required. Fine, but explicit is better. |
| **5 (NICE)** | Make `register_value` idempotent or add safeguard | Current behavior raises ValueError on duplicate key — could cause issues during hot-reload in dev |
