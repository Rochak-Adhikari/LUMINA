# Phase B.2.2 Hotfix Summary

> **Date**: February 1, 2026  
> **Status**: Complete  
> **Objective**: Guard tool socket handlers + seed owner identity fact

---

## CRITICAL: Must Run in `lumina` Conda Environment

**ALL commands MUST be run with**:
```bash
conda activate lumina
```

**Before running ANY test or starting the server, verify environment**:
```bash
# Check current environment
conda info --envs | grep "*"

# Should show: lumina * (active environment)
```

---

## Changes Made

### 1. Tool Socket Handler Guards

**Problem**: When tools disabled and `kasa_agent = None`, socket events still called methods on None, causing crashes.

**Solution**: Added guards to all tool handlers to NO-OP safely when tools disabled.

---

#### Handler: `discover_kasa`

**File**: `backend/server.py` (Lines 789-797)

```python
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
        # ... rest of handler
```

**Expected Log** (when disabled):
```
Received discover_kasa request
[TOOLS] Kasa tools DISABLED - returning empty device list
```

---

#### Handler: `discover_printers`

**File**: `backend/server.py` (Lines 933-941)

```python
@sio.event
async def discover_printers(sid):
    print("Received discover_printers request")
    
    # Guard: If tools disabled, return empty
    if not SETTINGS["tool_permissions"].get("discover_printers", False):
        print("[TOOLS] Printer tools DISABLED - returning empty printer list")
        await sio.emit('printer_list', [])
        await sio.emit('status', {'msg': 'Printer tools are disabled'})
        return
    
    # ... rest of handler
```

**Expected Log** (when disabled):
```
Received discover_printers request
[TOOLS] Printer tools DISABLED - returning empty printer list
```

---

#### Handler: `print_stl`

**File**: `backend/server.py` (Lines 1051-1059)

```python
@sio.event
async def print_stl(sid, data):
    print(f"Received print_stl request: {data}")
    
    # Guard: If tools disabled, return error
    if not SETTINGS["tool_permissions"].get("print_stl", False):
        print("[TOOLS] Print tools DISABLED - ignoring print_stl request")
        await sio.emit('error', {'msg': 'Print tools are disabled'})
        return
    
    # ... rest of handler
```

**Expected Log** (when disabled):
```
Received print_stl request: {...}
[TOOLS] Print tools DISABLED - ignoring print_stl request
```

---

#### Handler: `control_kasa`

**File**: `backend/server.py` (Lines 1144-1154)

```python
@sio.event
async def control_kasa(sid, data):
    ip = data.get('ip')
    action = data.get('action')
    print(f"Kasa Control: {ip} -> {action}")
    
    # Guard: If tools disabled or kasa_agent is None, return error
    if not SETTINGS["tool_permissions"].get("control_light", False) or kasa_agent is None:
        print("[TOOLS] Kasa control DISABLED - ignoring control_kasa request")
        await sio.emit('error', {'msg': 'Kasa tools are disabled'})
        return
    
    # ... rest of handler
```

**Expected Log** (when disabled):
```
Kasa Control: 192.168.1.100 -> on
[TOOLS] Kasa control DISABLED - ignoring control_kasa request
```

---

### 2. Owner Identity Memory Seed

**Problem**: Memory DB works but doesn't contain core identity facts.

**Solution**: Auto-seed owner identity fact on startup (idempotent).

---

#### Implementation

**File**: `backend/lumina.py` (Lines 311-344)

```python
# In AudioLoop.__init__():
# Seed core identity fact (idempotent - only if not already present)
self._seed_owner_identity()

def _seed_owner_identity(self):
    """
    Seed core identity fact about owner.
    Idempotent - only adds if not already present.
    """
    owner_fact = "Lumina is a private companion made only for Scepter (Rochak Adhikari)."
    
    try:
        # Check if already exists
        existing = self.memory_store.search_memories("Scepter", limit=5)
        for mem in existing:
            if "Rochak Adhikari" in mem['content'] or "private companion" in mem['content']:
                print(f"[MEMORY SEED] Owner identity fact already exists (ID: {mem['id']})")
                return
        
        # Add the seed fact
        memory_id = self.memory_store.add_memory(
            memory_type="fact",
            content=owner_fact,
            metadata={"seed": True, "system": True}
        )
        print(f"[MEMORY SEED] Added owner identity fact (ID: {memory_id})")
    except Exception as e:
        print(f"[MEMORY SEED] Error seeding owner identity: {e}")
```

**Expected Logs**:

**First startup** (seed added):
```
[LUMINA] Passive Memory Store initialized
[MEMORY SEED] Added owner identity fact (ID: 4)
```

**Subsequent startups** (already exists):
```
[LUMINA] Passive Memory Store initialized
[MEMORY SEED] Owner identity fact already exists (ID: 4)
```

---

## Files Changed

| File | Lines | Change |
|------|-------|--------|
| `backend/server.py` | 789-797 | Guard `discover_kasa` handler |
| `backend/server.py` | 933-941 | Guard `discover_printers` handler |
| `backend/server.py` | 1051-1059 | Guard `print_stl` handler |
| `backend/server.py` | 1144-1154 | Guard `control_kasa` handler |
| `backend/lumina.py` | 311-344 | Add `_seed_owner_identity()` method |

---

## Testing Instructions

### STEP 1: Activate Lumina Environment

**CRITICAL**: Do this FIRST before ANY commands:

```bash
conda activate lumina
```

**Verify**:
```bash
conda info --envs | grep "*"
# Should show: lumina * 
```

---

### STEP 2: Start Server

```bash
cd backend
python server.py
```

**Expected Startup Logs**:
```
[ENV CHECK] ✓ Running in conda environment: lumina
Loaded settings: {'tool_permissions': {...}}
[TOOL CLAMP] Forcing all tool permissions to False (Phase B.2)
[TOOL CLAMP] Tool permissions after clamp: {'generate_cad': False, ...}
[SERVER] Kasa tools DISABLED - skipping Kasa agent initialization
INFO:     Started server process [xxxx]
INFO:     Waiting for application startup.
[SERVER DEBUG] Startup Event Triggered
[SERVER] Startup: Kasa agent DISABLED - skipping initialization
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Verify NO errors** - server should reach "Application startup complete"

---

### STEP 3: Connect Frontend and Start Audio Loop

**In separate terminal** (also in lumina env):
```bash
conda activate lumina
npm run dev
```

**In browser**: Connect to Lumina

**Expected Server Logs**:
```
[SERVER] Starting Lumina Audio Loop...
[LUMINA] Passive Memory Store initialized
[MEMORY SEED] Added owner identity fact (ID: 4)
AudioLoop initialized successfully.
[SERVER] Printer tools DISABLED - skipping printer initialization
```

---

### STEP 4: Test Handler Guards

**Test A: discover_kasa**

Trigger: Frontend clicks "Discover Kasa Devices" (if UI exists)

**Expected Server Log**:
```
Received discover_kasa request
[TOOLS] Kasa tools DISABLED - returning empty device list
```

**Expected Frontend**: Empty device list, message "Kasa tools are disabled"

---

**Test B: discover_printers**

Trigger: Frontend clicks "Discover Printers"

**Expected Server Log**:
```
Received discover_printers request
[TOOLS] Printer tools DISABLED - returning empty printer list
```

**Expected Frontend**: Empty printer list, message "Printer tools are disabled"

---

### STEP 5: Verify Memory Seed

**In lumina environment**:
```bash
cd backend
python -c "import sqlite3; c=sqlite3.connect('lumina_memory.db'); print(c.execute('select id,type,content from memories order by id desc limit 5').fetchall()); c.close()"
```

**Expected Output** (includes owner fact):
```
[(4, 'fact', 'Lumina is a private companion made only for Scepter (Rochak Adhikari).'), 
 (3, 'preference', 'I like bright crimson and neon purple'), 
 (2, 'fact', 'User is building an AI system'), 
 (1, 'fact', 'User is from Nepal')]
```

---

### STEP 6: Test Memory Recall with Owner Fact

**In chat, type**: `/memory`

**Expected Response**:
```
📝 Recent Memories:
  [fact] Lumina is a private companion made only for Scepter (Rochak Adhikari).
  [preference] I like bright crimson and neon purple
  [fact] User is from Nepal
```

---

**In chat, ask**: "who are you?"

**Expected Server Logs**:
```
[SERVER DEBUG] User input received: 'who are you?'
[AUTO-CAPTURE] No obvious patterns detected in: 'who are you?'
[MEMORY] Injected 1 memories (IDs: [4])
[MEMORY] Scores: [25.0]
[SERVER DEBUG] Sending message to model: 'who are you?' (with 1 memories)
```

**Message sent to LLM**:
```
[MEMORY CONTEXT - Retrieved from long-term memory]
- [fact] Lumina is a private companion made only for Scepter (Rochak Adhikari).

who are you?
```

**Expected LLM Response**: Should reference being Scepter's companion

---

## Database Path Note

**When running SQLite commands from different directories**:

**From project root** (`Luna/`):
```bash
python -c "import sqlite3; c=sqlite3.connect('backend/lumina_memory.db'); ..."
```

**From backend folder** (`Luna/backend/`):
```bash
python -c "import sqlite3; c=sqlite3.connect('lumina_memory.db'); ..."
```

**The database file is always**: `Luna/backend/lumina_memory.db`

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'PIL'"

**Cause**: Running in `base` environment instead of `lumina`

**Solution**:
```bash
conda activate lumina
# Then retry command
```

---

### Issue: "Wrong conda environment! Required: lumina, Current: base"

**Cause**: Server enforces lumina environment check

**Solution**:
```bash
conda activate lumina
cd backend
python server.py
```

---

### Issue: Handlers still crash with AttributeError

**Cause**: Old code without guards still running

**Solution**:
1. Stop server (Ctrl+C)
2. Verify code changes saved
3. Run `python -m py_compile backend/server.py` (in lumina env)
4. Restart server

---

### Issue: Memory seed not appearing

**Cause**: Memory store not initialized (audio loop not started)

**Solution**: Connect frontend and start audio loop first

---

## Confirmation Checklist

After completing all tests, verify:

- ✅ Server starts successfully in `lumina` environment
- ✅ No Kasa agent initialization when tools disabled
- ✅ No printer initialization when tools disabled
- ✅ `discover_kasa` returns empty list without errors
- ✅ `discover_printers` returns empty list without errors
- ✅ `print_stl` returns error message without crash
- ✅ `control_kasa` returns error message without crash
- ✅ Owner identity fact seeded to database
- ✅ Owner fact appears in `/memory` command
- ✅ Owner fact injected when asking "who are you?"

---

## Summary

**Phase B.2.2 Hotfix Complete**:
- All tool socket handlers guarded against None access
- Owner identity fact auto-seeded (idempotent)
- All handlers return safe responses when tools disabled
- No breaking changes to STT/LLM/TTS pipeline

**All execution MUST occur inside `lumina` conda environment.**

---

*Phase B.2.2 hotfix complete.*
