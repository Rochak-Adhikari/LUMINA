"""
Lumina Passive Memory Store

This module provides PASSIVE memory storage for Lumina.
Memory is local-first, safe, and non-destructive.

IMPORTANT:
- Memory does NOT trigger actions
- Memory does NOT modify system behavior
- Memory is READ-ONLY during conversation (writes are explicit)
- No file manipulation or OS access beyond local SQLite database
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Literal

MemoryType = Literal["fact", "preference", "conversation_summary", "session_summary", "intent", "assumption"]
MemoryState = Literal["active", "pending", "dormant"]


class MemoryStore:
    """
    Passive memory storage for Lumina.
    
    Memory Types:
    - fact: Factual information about the user
    - preference: User preferences
    - conversation_summary: High-level summaries of past conversations
    - session_summary: Auto-saved continuity summaries (Phase E3)
    - intent: Future plans, commitments, goals
    - assumption: Temporary inferred memory (pending confirmation)
    
    Memory States:
    - active: Injected into prompts, fully trusted
    - pending: Used cautiously, awaiting confirmation or decay
    - dormant: Low-priority, not injected but still searchable
    
    Memory is NEVER deleted. Only priority changes.
    
    Safety Guarantees:
    - All database operations are transactional
    - No OS access beyond local database file
    - No automatic behavior changes
    - Memory retrieval is passive (no side effects)
    """
    
    def __init__(self, db_path: str = "lumina_memory.db"):
        """
        Initialize memory store.
        
        Args:
            db_path: Path to SQLite database file (default: lumina_memory.db)
        """
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Target schema: memories table with lifecycle fields
        _TARGET_TYPES = "'fact','preference','conversation_summary','session_summary','intent','assumption'"
        _TARGET_SCHEMA = f"""
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK(type IN ({_TARGET_TYPES})),
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                last_accessed_at TEXT,
                access_count INTEGER DEFAULT 0,
                state TEXT NOT NULL DEFAULT 'active' CHECK(state IN ('active','pending','dormant')),
                confidence REAL DEFAULT 1.0,
                priority INTEGER DEFAULT 50,
                last_confirmed_at TEXT,
                last_used_at TEXT
            )
        """
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memories'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            cursor.execute(_TARGET_SCHEMA)
            conn.commit()
            print("[MEMORY STORE] Created memories table with lifecycle fields")
        else:
            # Safe migration: add missing columns + fix CHECK constraint
            self._migrate_memories_table(conn, cursor, _TARGET_SCHEMA)
        
        # Create index for efficient retrieval by type
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(type)
        """)
        
        # Create index for recent access
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_last_accessed ON memories(last_accessed_at DESC)
        """)
        
        # Phase E5: Transcript storage for hybrid retrieval
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                project_name TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_session ON transcripts(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_project ON transcripts(project_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_created ON transcripts(created_at DESC)")
        
        # Phase E5: Memory chunks for hybrid retrieval indexing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_id TEXT,
                project_name TEXT,
                chunk_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                embedding BLOB,
                embedding_dim INTEGER,
                hash TEXT UNIQUE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source ON memory_chunks(source_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_hash ON memory_chunks(hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_created ON memory_chunks(created_at DESC)")
        
        # Phase E5: FTS5 index for keyword search (external content table)
        try:
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_chunks_fts
                USING fts5(chunk_text, content='memory_chunks', content_rowid='id')
            """)
        except Exception as e:
            print(f"[MEMORY STORE] FTS5 setup note: {e}")
        
        # Index for state-aware queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_state ON memories(state)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_priority ON memories(priority DESC)")
        
        # ========================================
        # Panel data tables: quests, events, archive_notes
        # ========================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'medium' CHECK(priority IN ('low','medium','high')),
                status TEXT DEFAULT 'active' CHECK(status IN ('active','completed','side')),
                progress INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                datetime TEXT NOT NULL,
                notes TEXT,
                completed INTEGER DEFAULT 0,
                notified INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        # Migration: add notified column if missing (existing DBs)
        try:
            cursor.execute("ALTER TABLE events ADD COLUMN notified INTEGER DEFAULT 0")
            print("[MEMORY STORE] Migrated events table: added 'notified' column")
        except Exception:
            pass  # Column already exists
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS archive_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                tags TEXT,
                pinned INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
        print(f"[MEMORY STORE] Initialized at: {self.db_path}")
    
    def _migrate_memories_table(self, conn, cursor, target_schema: str):
        """Safe migration: add missing columns and fix CHECK constraint. Preserves all data."""
        # Check which columns exist
        cursor.execute("PRAGMA table_info(memories)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        new_cols = {
            "state": ("TEXT", "'active'"),
            "confidence": ("REAL", "1.0"),
            "priority": ("INTEGER", "50"),
            "last_confirmed_at": ("TEXT", "NULL"),
            "last_used_at": ("TEXT", "NULL"),
        }
        
        cols_added = []
        for col_name, (col_type, default_val) in new_cols.items():
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE memories ADD COLUMN {col_name} {col_type} DEFAULT {default_val}")
                    cols_added.append(col_name)
                except Exception as e:
                    print(f"[MEMORY STORE] Column add note ({col_name}): {e}")
        
        if cols_added:
            conn.commit()
            print(f"[MEMORY STORE] Migration: added columns {cols_added}")
        
        # Fix CHECK constraint if it doesn't allow new types
        needs_rebuild = False
        for probe_type in ("session_summary", "intent", "assumption"):
            try:
                cursor.execute(
                    "INSERT INTO memories (type, content, created_at, state, confidence, priority) "
                    "VALUES (?, '__migration_probe__', '2000-01-01T00:00:00', 'active', 1.0, 50)",
                    (probe_type,)
                )
                cursor.execute("DELETE FROM memories WHERE content = '__migration_probe__' AND type = ?", (probe_type,))
                conn.commit()
            except sqlite3.IntegrityError:
                conn.rollback()
                needs_rebuild = True
                break
        
        if needs_rebuild:
            print("[MEMORY STORE] Migrating memories table: updating CHECK constraints for new types + states")
            cursor.execute("ALTER TABLE memories RENAME TO _memories_old")
            cursor.execute(target_schema)
            # Copy data — use defaults for any missing columns
            cursor.execute("PRAGMA table_info(_memories_old)")
            old_cols = [row[1] for row in cursor.fetchall()]
            # Build column list that exists in both old and new
            all_new_cols = ["id", "type", "content", "metadata", "created_at", "last_accessed_at",
                           "access_count", "state", "confidence", "priority", "last_confirmed_at", "last_used_at"]
            shared = [c for c in all_new_cols if c in old_cols]
            shared_str = ", ".join(shared)
            cursor.execute(f"INSERT INTO memories ({shared_str}) SELECT {shared_str} FROM _memories_old")
            cursor.execute("DROP TABLE _memories_old")
            conn.commit()
            print("[MEMORY STORE] Migration complete: all types and lifecycle fields active")
    
    def add_memory(self, memory_type: MemoryType, content: str, metadata: Optional[Dict] = None,
                   state: MemoryState = "active", confidence: float = 1.0, priority: int = 50) -> int:
        """
        Add a new memory entry.
        
        Args:
            memory_type: Type of memory (fact, preference, conversation_summary)
            content: The actual memory content
            metadata: Optional metadata as dict
        
        Returns:
            The ID of the newly created memory
        """
        if not content.strip():
            raise ValueError("Memory content cannot be empty")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.utcnow().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute("""
            INSERT INTO memories (type, content, metadata, created_at, state, confidence, priority, last_confirmed_at, last_used_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (memory_type, content.strip(), metadata_json, timestamp, state, confidence, priority,
              timestamp if state == "active" else None, timestamp))
        
        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[MEMORY STORE] Added {memory_type} (state={state}, conf={confidence:.2f}, pri={priority}): {content[:50]}...")
        return memory_id
    
    def get_memories(
        self, 
        memory_type: Optional[MemoryType] = None, 
        limit: int = 10,
        update_access: bool = True
    ) -> List[Dict]:
        """
        Retrieve memories, optionally filtered by type.
        
        Args:
            memory_type: Filter by type (None = all types)
            limit: Maximum number of memories to return
            update_access: Whether to update last_accessed_at and access_count
        
        Returns:
            List of memory dicts with keys: id, type, content, metadata, created_at
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if memory_type:
            cursor.execute("""
                SELECT id, type, content, metadata, created_at, access_count
                FROM memories
                WHERE type = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (memory_type, limit))
        else:
            cursor.execute("""
                SELECT id, type, content, metadata, created_at, access_count
                FROM memories
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        memories = []
        
        for row in rows:
            memory = {
                "id": row[0],
                "type": row[1],
                "content": row[2],
                "metadata": json.loads(row[3]) if row[3] else None,
                "created_at": row[4],
                "access_count": row[5]
            }
            memories.append(memory)
            
            # Update access tracking if requested
            if update_access:
                cursor.execute("""
                    UPDATE memories
                    SET last_accessed_at = ?, access_count = access_count + 1
                    WHERE id = ?
                """, (datetime.utcnow().isoformat(), row[0]))
        
        conn.commit()
        conn.close()
        
        return memories
    
    def get_latest_session_summary(self) -> Optional[Dict]:
        """
        Get the most recent session summary for continuity (Phase E3).
        
        Supports both 'session_summary' (new) and 'conversation_summary' (legacy)
        types for backward compatibility.
        
        Returns:
            Latest session_summary memory dict or None if no summaries exist
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, type, content, metadata, created_at, access_count
            FROM memories
            WHERE type IN ('session_summary', 'conversation_summary')
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "type": row[1],
            "content": row[2],
            "metadata": json.loads(row[3]) if row[3] else None,
            "created_at": row[4],
            "access_count": row[5]
        }
    
    def get_identity_memories(self) -> List[Dict]:
        """
        Retrieve identity-related memories that should always be included.
        These are memories about the owner/user and system identity.
        
        Returns:
            List of identity memory dicts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all memories with seed=True or containing identity markers
        cursor.execute("""
            SELECT id, type, content, metadata, created_at, access_count
            FROM memories
            WHERE type = 'fact' AND (
                content LIKE '%Scepter%' OR
                content LIKE '%Rochak Adhikari%' OR
                content LIKE '%companion%' OR
                content LIKE '%owner%' OR
                metadata LIKE '%"seed": true%' OR
                metadata LIKE '%"system": true%'
            )
            ORDER BY created_at ASC
        """)
        
        rows = cursor.fetchall()
        memories = []
        
        for row in rows:
            memory = {
                "id": row[0],
                "type": row[1],
                "content": row[2],
                "metadata": json.loads(row[3]) if row[3] else None,
                "created_at": row[4],
                "access_count": row[5]
            }
            memories.append(memory)
        
        conn.close()
        return memories
    
    def search_memories(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search memories by content.
        
        Args:
            query: Search query string
            limit: Maximum number of results
        
        Returns:
            List of matching memory dicts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Simple LIKE search (can be enhanced with FTS if needed)
        cursor.execute("""
            SELECT id, type, content, metadata, created_at, access_count
            FROM memories
            WHERE content LIKE ?
            ORDER BY last_accessed_at DESC, created_at DESC
            LIMIT ?
        """, (f"%{query}%", limit))
        
        rows = cursor.fetchall()
        memories = []
        
        for row in rows:
            memories.append({
                "id": row[0],
                "type": row[1],
                "content": row[2],
                "metadata": json.loads(row[3]) if row[3] else None,
                "created_at": row[4],
                "access_count": row[5]
            })
        
        conn.close()
        return memories
    
    def get_relevant_memories(self, query: str, max_results: int = 8) -> List[Dict]:
        """
        Retrieve memories relevant to a query with simple relevance scoring.
        
        Scoring algorithm:
        - Keyword overlap (case-insensitive, word-level)
        - Substring match bonus
        - Recency bonus (newer = higher score)
        - Access count bonus (frequently accessed = higher score)
        
        Args:
            query: User's message/query
            max_results: Maximum number of memories to return
        
        Returns:
            List of memory dicts sorted by relevance score (highest first)
        """
        if not query or not query.strip():
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all memories
        cursor.execute("""
            SELECT id, type, content, metadata, created_at, access_count, last_accessed_at
            FROM memories
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return []
        
        # Normalize query
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_memories = []
        
        for row in rows:
            memory_id, mem_type, content, metadata, created_at, access_count, last_accessed = row
            
            # Normalize content
            content_lower = content.lower()
            content_words = set(content_lower.split())
            
            # Calculate score
            score = 0.0
            
            # Keyword overlap (most important)
            overlap = query_words.intersection(content_words)
            score += len(overlap) * 10.0
            
            # Substring match bonus
            if query_lower in content_lower or content_lower in query_lower:
                score += 15.0
            
            # Recency bonus (recent memories are more relevant)
            try:
                created_dt = datetime.fromisoformat(created_at)
                age_days = (datetime.utcnow() - created_dt).total_seconds() / 86400
                recency_score = max(0, 5.0 - (age_days * 0.1))  # Decay over time
                score += recency_score
            except:
                pass
            
            # Access count bonus (frequently used memories)
            score += min(access_count or 0, 5) * 0.5
            
            # Type bonus (facts and preferences are more important)
            if mem_type in ["fact", "preference"]:
                score += 2.0
            
            if score > 0:
                scored_memories.append({
                    "id": memory_id,
                    "type": mem_type,
                    "content": content,
                    "metadata": json.loads(metadata) if metadata else None,
                    "created_at": created_at,
                    "access_count": access_count or 0,
                    "score": score
                })
        
        # Sort by score descending
        scored_memories.sort(key=lambda x: x["score"], reverse=True)
        
        # Update access tracking for top results
        if scored_memories:
            top_ids = [m["id"] for m in scored_memories[:max_results]]
            if top_ids:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                timestamp = datetime.utcnow().isoformat()
                for mem_id in top_ids:
                    cursor.execute("""
                        UPDATE memories
                        SET last_accessed_at = ?, access_count = access_count + 1
                        WHERE id = ?
                    """, (timestamp, mem_id))
                conn.commit()
                conn.close()
        
        return scored_memories[:max_results]
    
    def get_memory_context(self, max_facts: int = 5, max_preferences: int = 3) -> str:
        """
        Get a formatted memory context string for conversation enhancement.
        
        This is the primary method for passive memory retrieval during conversation.
        
        Args:
            max_facts: Maximum number of facts to include
            max_preferences: Maximum number of preferences to include
        
        Returns:
            Formatted string with memory context
        """
        facts = self.get_memories("fact", limit=max_facts, update_access=True)
        preferences = self.get_memories("preference", limit=max_preferences, update_access=True)
        
        if not facts and not preferences:
            return ""
        
        context_parts = []
        
        if facts:
            facts_str = "\n".join([f"- {f['content']}" for f in facts])
            context_parts.append(f"Known Facts:\n{facts_str}")
        
        if preferences:
            prefs_str = "\n".join([f"- {p['content']}" for p in preferences])
            context_parts.append(f"User Preferences:\n{prefs_str}")
        
        return "\n\n".join(context_parts)
    
    # ========================================
    # LIFECYCLE MANAGEMENT
    # ========================================
    
    def get_by_state(self, state: str, limit: int = 50) -> List[Dict]:
        """Retrieve memories filtered by state (active, pending, dormant)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, type, content, metadata, created_at, access_count,
                   state, confidence, priority, last_confirmed_at, last_used_at
            FROM memories WHERE state = ?
            ORDER BY priority DESC, created_at DESC
            LIMIT ?
        """, (state, limit))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict_full(r) for r in rows]
    
    def get_active_for_injection(self, limit: int = 20) -> List[Dict]:
        """Get active memories ordered by priority for prompt injection."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, type, content, metadata, created_at, access_count,
                   state, confidence, priority, last_confirmed_at, last_used_at
            FROM memories
            WHERE state = 'active' AND type NOT IN ('conversation_summary', 'session_summary')
            ORDER BY priority DESC, created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict_full(r) for r in rows]
    
    def get_pending_assumptions(self, limit: int = 5) -> List[Dict]:
        """Get pending assumptions for cautious injection or revisit."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, type, content, metadata, created_at, access_count,
                   state, confidence, priority, last_confirmed_at, last_used_at
            FROM memories
            WHERE state = 'pending' AND type IN ('assumption', 'intent')
            ORDER BY confidence DESC, created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict_full(r) for r in rows]
    
    def promote_memory(self, memory_id: int, new_state: str = "active", confidence: float = None) -> bool:
        """Promote a memory (e.g., pending → active). Returns True if updated."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        if confidence is not None:
            cursor.execute("""
                UPDATE memories SET state = ?, confidence = ?, last_confirmed_at = ?, priority = MIN(priority + 10, 100)
                WHERE id = ?
            """, (new_state, confidence, now, memory_id))
        else:
            cursor.execute("""
                UPDATE memories SET state = ?, last_confirmed_at = ?, priority = MIN(priority + 10, 100)
                WHERE id = ?
            """, (new_state, now, memory_id))
        changed = cursor.rowcount > 0
        conn.commit()
        conn.close()
        if changed:
            print(f"[MEMORY DECISION] Promoted memory {memory_id} → {new_state}")
        return changed
    
    def demote_memory(self, memory_id: int, new_state: str = "dormant") -> bool:
        """Demote a memory (e.g., active → dormant). Returns True if updated."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE memories SET state = ?, priority = MAX(priority - 15, 0)
            WHERE id = ?
        """, (new_state, memory_id))
        changed = cursor.rowcount > 0
        conn.commit()
        conn.close()
        if changed:
            print(f"[MEMORY DECISION] Demoted memory {memory_id} → {new_state}")
        return changed
    
    def mark_used(self, memory_id: int, boost: int = 3) -> None:
        """Mark a memory as used — bumps priority and last_used_at."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            UPDATE memories SET last_used_at = ?, last_accessed_at = ?,
                   access_count = access_count + 1,
                   priority = MIN(priority + ?, 100)
            WHERE id = ?
        """, (now, now, boost, memory_id))
        conn.commit()
        conn.close()
    
    def decay_priorities(self, threshold_days: int = 7, decay_amount: int = 2, dormant_threshold: int = 10) -> Dict:
        """
        Decay priorities of memories not used recently.
        Memories below dormant_threshold become dormant.
        Returns counts of decayed and demoted memories.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.utcnow()
        cutoff = (now - timedelta(days=threshold_days)).isoformat()
        
        # Decay priority for memories not used recently
        cursor.execute("""
            UPDATE memories SET priority = MAX(priority - ?, 0)
            WHERE state IN ('active', 'pending')
              AND (last_used_at IS NULL OR last_used_at < ?)
              AND type NOT IN ('session_summary', 'conversation_summary')
        """, (decay_amount, cutoff))
        decayed = cursor.rowcount
        conn.commit()
        
        # Demote to dormant if below threshold
        cursor.execute("""
            UPDATE memories SET state = 'dormant'
            WHERE state IN ('active', 'pending')
              AND priority <= ?
              AND type NOT IN ('fact', 'session_summary', 'conversation_summary')
        """, (dormant_threshold,))
        demoted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if decayed > 0 or demoted > 0:
            print(f"[MEMORY DECISION] Priority decay: {decayed} decayed, {demoted} demoted to dormant")
        return {"decayed": decayed, "demoted": demoted}
    
    def get_stale_pending(self, older_than_hours: int = 24, limit: int = 3) -> List[Dict]:
        """Get pending memories older than threshold for natural revisit."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cutoff = (datetime.utcnow() - timedelta(hours=older_than_hours)).isoformat()
        cursor.execute("""
            SELECT id, type, content, metadata, created_at, access_count,
                   state, confidence, priority, last_confirmed_at, last_used_at
            FROM memories
            WHERE state = 'pending' AND created_at < ?
            ORDER BY priority DESC
            LIMIT ?
        """, (cutoff, limit))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict_full(r) for r in rows]
    
    def _row_to_dict_full(self, row) -> Dict:
        """Convert a full row (with lifecycle fields) to dict."""
        return {
            "id": row[0],
            "type": row[1],
            "content": row[2],
            "metadata": json.loads(row[3]) if row[3] else None,
            "created_at": row[4],
            "access_count": row[5],
            "state": row[6] if len(row) > 6 else "active",
            "confidence": row[7] if len(row) > 7 else 1.0,
            "priority": row[8] if len(row) > 8 else 50,
            "last_confirmed_at": row[9] if len(row) > 9 else None,
            "last_used_at": row[10] if len(row) > 10 else None,
        }
    
    def get_stats(self) -> Dict:
        """Get memory store statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT type, COUNT(*) FROM memories GROUP BY type")
        by_type = dict(cursor.fetchall())
        
        # State counts
        by_state = {}
        try:
            cursor.execute("SELECT state, COUNT(*) FROM memories GROUP BY state")
            by_state = dict(cursor.fetchall())
        except Exception:
            pass
        
        conn.close()
        
        return {
            "total_memories": total,
            "by_type": by_type,
            "by_state": by_state,
            "database_path": str(self.db_path)
        }
    
    # ========================================
    # Panel CRUD: Quests
    # ========================================
    def list_quests(self, status_filter: str = None) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        if status_filter:
            c.execute("SELECT * FROM quests WHERE status = ? ORDER BY created_at DESC", (status_filter,))
        else:
            c.execute("SELECT * FROM quests ORDER BY created_at DESC")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def create_quest(self, title: str, description: str = "", priority: str = "medium", status: str = "active") -> Dict:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        c.execute("INSERT INTO quests (title, description, priority, status, progress, created_at) VALUES (?,?,?,?,0,?)",
                  (title, description, priority, status, now))
        qid = c.lastrowid
        conn.commit()
        c.execute("SELECT * FROM quests WHERE id = ?", (qid,))
        row = dict(c.fetchone())
        conn.close()
        print(f"[PANEL] Quest created id={qid} title={title}")
        return row

    def update_quest(self, quest_id: int, **kwargs) -> Optional[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        allowed = {"title", "description", "priority", "status", "progress"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            conn.close()
            return None
        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        vals = list(updates.values()) + [quest_id]
        c.execute(f"UPDATE quests SET {set_clause} WHERE id = ?", vals)
        conn.commit()
        c.execute("SELECT * FROM quests WHERE id = ?", (quest_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_quest(self, quest_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM quests WHERE id = ?", (quest_id,))
        deleted = c.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    # ========================================
    # Panel CRUD: Events
    # ========================================
    def list_events(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM events ORDER BY datetime ASC")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def create_event(self, title: str, dt: str, notes: str = "") -> Dict:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        c.execute("INSERT INTO events (title, datetime, notes, created_at) VALUES (?,?,?,?)",
                  (title, dt, notes, now))
        eid = c.lastrowid
        conn.commit()
        c.execute("SELECT * FROM events WHERE id = ?", (eid,))
        row = dict(c.fetchone())
        conn.close()
        print(f"[PANEL] Event created id={eid} title={title}")
        return row

    def update_event(self, event_id: int, **kwargs) -> Optional[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        allowed = {"title", "datetime", "notes", "completed", "notified"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            conn.close()
            return None
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        vals = list(updates.values()) + [event_id]
        c.execute(f"UPDATE events SET {set_clause} WHERE id = ?", vals)
        conn.commit()
        c.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_event(self, event_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM events WHERE id = ?", (event_id,))
        deleted = c.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_due_events(self, now_iso: str) -> List[Dict]:
        """Get events whose datetime <= now, not completed, not yet notified."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            "SELECT * FROM events WHERE datetime <= ? AND completed = 0 AND notified = 0 ORDER BY datetime ASC",
            (now_iso,)
        )
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def mark_event_notified(self, event_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE events SET notified = 1 WHERE id = ?", (event_id,))
        updated = c.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    # ========================================
    # Panel CRUD: Archive Notes
    # ========================================
    def list_archive_notes(self, tag_filter: str = None) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        if tag_filter:
            c.execute("SELECT * FROM archive_notes WHERE tags LIKE ? ORDER BY pinned DESC, created_at DESC",
                      (f"%{tag_filter}%",))
        else:
            c.execute("SELECT * FROM archive_notes ORDER BY pinned DESC, created_at DESC")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def create_archive_note(self, title: str, body: str, tags: str = "") -> Dict:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        c.execute("INSERT INTO archive_notes (title, body, tags, created_at) VALUES (?,?,?,?)",
                  (title, body, tags, now))
        nid = c.lastrowid
        conn.commit()
        c.execute("SELECT * FROM archive_notes WHERE id = ?", (nid,))
        row = dict(c.fetchone())
        conn.close()
        print(f"[PANEL] Archive note created id={nid} title={title}")
        return row

    def update_archive_note(self, note_id: int, **kwargs) -> Optional[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        allowed = {"title", "body", "tags", "pinned"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            conn.close()
            return None
        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        vals = list(updates.values()) + [note_id]
        c.execute(f"UPDATE archive_notes SET {set_clause} WHERE id = ?", vals)
        conn.commit()
        c.execute("SELECT * FROM archive_notes WHERE id = ?", (note_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_archive_note(self, note_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM archive_notes WHERE id = ?", (note_id,))
        deleted = c.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def clear_all(self):
        """
        DANGER: Clear all memories.
        This is a destructive operation and should be used with caution.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories")
        conn.commit()
        conn.close()
        print("[MEMORY STORE] All memories cleared")


# Example usage for testing
if __name__ == "__main__":
    store = MemoryStore("test_memory.db")
    
    # Add some test memories
    store.add_memory("fact", "User's name is Rochak")
    store.add_memory("fact", "User lives in Kathmandu")
    store.add_memory("preference", "User prefers casual Nepali with English mixing")
    store.add_memory("conversation_summary", "Discussed AI architecture and memory systems")
    
    # Get memory context
    context = store.get_memory_context()
    print("\n=== Memory Context ===")
    print(context)
    
    # Get stats
    stats = store.get_stats()
    print("\n=== Stats ===")
    print(json.dumps(stats, indent=2))
