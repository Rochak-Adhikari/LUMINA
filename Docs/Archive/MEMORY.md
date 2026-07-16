# Lumina Passive Memory System

> **Phase B Implementation**  
> **Status**: Active  
> **Database**: SQLite (local-first)

---

## Overview

Lumina's memory system is **passive** and **safe**. It stores information to enhance conversations without triggering actions or modifying system behavior.

### Key Principles

| Principle | Description |
|-----------|-------------|
| **Passive** | Memory is read-only during conversation; no automatic actions |
| **Local-First** | All data stored locally in SQLite (`backend/lumina_memory.db`) |
| **Non-Destructive** | Memory never modifies files, OS, or system behavior |
| **Optional** | System works fully without any memories |
| **Explicit Writes** | Memory is only written when explicitly requested |

---

## Memory Schema

### Database Structure

```sql
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('fact', 'preference', 'conversation_summary')),
    content TEXT NOT NULL,
    metadata TEXT,  -- JSON string
    created_at TEXT NOT NULL,
    last_accessed_at TEXT,
    access_count INTEGER DEFAULT 0
)
```

### Memory Types

| Type | Purpose | Example |
|------|---------|---------|
| **fact** | Factual information about user | "User lives in Kathmandu" |
| **preference** | User preferences | "User prefers casual Nepali" |
| **conversation_summary** | High-level conversation summaries | "Discussed AI architecture on Feb 1" |

---

## Memory Flow

### 1. Session Start (Passive Injection)

```
User connects
    ↓
MemoryStore.get_memory_context()
    ↓
Retrieve top 5 facts + 3 preferences
    ↓
Inject as system context (read-only)
    ↓
Lumina uses context to enhance responses
```

**Important**: Memory context is injected **once** at session start. Lumina does not actively query memory during conversation.

### 2. Memory Write (Explicit Only)

Memory is **never** written automatically. All writes must be:
- Explicitly requested via Socket.IO event
- Validated for type and content
- Transactional (atomic)

```
Frontend sends 'add_memory' event
    ↓
Server validates data
    ↓
MemoryStore.add_memory(type, content, metadata)
    ↓
Database transaction (atomic)
    ↓
Confirm to frontend
```

---

## API Reference

### Socket.IO Events

#### `add_memory`
**Direction**: Client → Server  
**Purpose**: Add a new memory entry

**Request**:
```json
{
  "type": "fact" | "preference" | "conversation_summary",
  "content": "memory content string",
  "metadata": {} // optional
}
```

**Response**:
```json
{
  "id": 123,
  "type": "fact",
  "content": "User lives in Kathmandu"
}
```

---

#### `get_memories`
**Direction**: Client → Server  
**Purpose**: Retrieve memories (for UI display)

**Request**:
```json
{
  "type": "fact", // optional filter
  "limit": 10     // optional, default 10
}
```

**Response**:
```json
{
  "memories": [
    {
      "id": 1,
      "type": "fact",
      "content": "User lives in Kathmandu",
      "metadata": null,
      "created_at": "2026-02-01T12:30:00",
      "access_count": 5
    }
  ]
}
```

---

#### `get_memory_stats`
**Direction**: Client → Server  
**Purpose**: Get memory store statistics

**Response**:
```json
{
  "total_memories": 15,
  "by_type": {
    "fact": 8,
    "preference": 5,
    "conversation_summary": 2
  },
  "database_path": "D:/PROJECT/Luna/backend/lumina_memory.db"
}
```

---

## Safety Guarantees

### What Memory DOES

✅ Store user facts and preferences locally  
✅ Enhance conversation relevance  
✅ Track access patterns (for future optimization)  
✅ Provide context at session start  

### What Memory DOES NOT

❌ Execute actions or commands  
❌ Modify files or OS  
❌ Control devices  
❌ Trigger autonomous behavior  
❌ Access network resources  
❌ Override system_instruction or persona  

---

## Implementation Details

### File Structure

```
backend/
├── memory_store.py       # MemoryStore class
├── lumina.py            # Passive memory integration (session start)
├── server.py            # Socket.IO endpoints
└── lumina_memory.db     # SQLite database (gitignored)
```

### Integration Points

**`lumina.py` (AudioLoop.run)**:
- Line ~1230: Inject memory context at session start
- Context is passive (read-only)
- No real-time memory queries during conversation

**`server.py`**:
- Lines 1011-1081: Memory management endpoints
- All operations validated and transactional

---

## Usage Example

### Adding Memory (via Socket.IO)

```javascript
// Frontend (React)
socket.emit('add_memory', {
  type: 'fact',
  content: 'User is building an AI companion system',
  metadata: { category: 'project' }
});

socket.on('memory_added', (data) => {
  console.log('Memory saved:', data);
});
```

### Python API (Backend)

```python
from memory_store import MemoryStore

store = MemoryStore("lumina_memory.db")

# Add memory
store.add_memory("fact", "User's name is Rochak")
store.add_memory("preference", "Prefers casual Nepali with English mixing")

# Get context for conversation
context = store.get_memory_context(max_facts=5, max_preferences=3)
print(context)
# Output:
# Known Facts:
# - User's name is Rochak
# 
# User Preferences:
# - Prefers casual Nepali with English mixing
```

---

## Testing

### Manual Test

```bash
# Activate environment
conda activate lumina

# Run test script
cd backend
python memory_store.py

# Expected output:
# [MEMORY STORE] Initialized at: test_memory.db
# [MEMORY STORE] Added fact: User's name is Rochak...
# === Memory Context ===
# Known Facts:
# - User's name is Rochak
# ...
```

---

## Future Enhancements (NOT in Phase B)

- Full-text search (SQLite FTS)
- Memory clustering/categorization
- Auto-summary of conversations
- Memory importance scoring
- UI for memory management

---

## Compliance with Phase B Requirements

| Requirement | Status |
|-------------|--------|
| Passive memory only | ✅ Read-only during conversation |
| Local-first | ✅ SQLite, no external dependencies |
| Safe | ✅ No OS access, no file manipulation |
| Optional | ✅ Works without any memories |
| Non-destructive | ✅ No automatic behavior changes |
| Explicit writes | ✅ All writes via Socket.IO events |
| No tools | ✅ Memory is not a tool |
| No agents | ✅ No agent orchestration |
| No autonomy | ✅ No automatic actions |

---

*Lumina's memory enhances conversation without compromising safety or control.*
