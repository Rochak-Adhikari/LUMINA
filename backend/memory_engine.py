"""
Lumina Memory Engine v2 — Hybrid Retrieval (Keyword + Vector)

Inspired by OpenClaw hybrid retrieval design; implemented independently.

Provides:
- Transcript storage (user + assistant messages)
- Chunking + dedup indexing
- Keyword search via SQLite FTS5
- Vector search via FAISS (primary) or NumPy cosine similarity (fallback)
- Hybrid merge (0.6 vector + 0.4 keyword) with recency + type boosts
- Returns top_k=8 memory excerpts with metadata

Phase E5 for Project Lumina.
"""

import asyncio
import hashlib
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# --- Optional: FAISS ---
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

# --- Optional: Google Gemini Embeddings ---
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# ========================================
# CONSTANTS
# ========================================
EMBEDDING_DIM = 768           # text-embedding-004 default
MAX_CHUNKS_INJECT = 8         # hard cap on injected excerpts
MAX_CHUNK_DISPLAY = 240       # truncate each excerpt in prompt prefix
CHUNK_MAX_CHARS = 800         # chunking window
CHUNK_OVERLAP = 120           # overlap between chunks
EMBED_BATCH_SIZE = 20         # batch size for embedding API calls
EMBED_BATCH_DELAY = 0.25      # seconds between batches (rate-limit safety)


# ========================================
# UTILITY FUNCTIONS
# ========================================

def chunk_text(text: str, max_chars: int = CHUNK_MAX_CHARS, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into chunks with overlap. Deterministic, char-based."""
    if not text or not text.strip():
        return []
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def hash_chunk(text: str) -> str:
    """SHA-256 hash for dedup."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def sanitize_fts_query(query: str) -> str:
    """Strip non-alphanumeric chars for safe FTS5 MATCH queries."""
    words = re.findall(r"[a-zA-Z0-9]+", query.lower())
    if not words:
        return ""
    # FTS5 implicit AND: just space-separate tokens
    return " ".join(words[:12])  # cap at 12 tokens


# ========================================
# EMBEDDING PROVIDER
# ========================================

class EmbeddingProvider:
    """Text embedding via Google Gemini (primary) or deterministic hash fallback."""

    def __init__(self):
        self._client = None
        self._available = False
        self._dim = EMBEDDING_DIM
        self._init_provider()

    def _init_provider(self):
        if not GEMINI_AVAILABLE:
            print("[MEMORY2] google-genai not installed — using fallback embeddings")
            return
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("[MEMORY2] GEMINI_API_KEY not set — using fallback embeddings")
            return
        # Try v1 first (text-embedding-004 not available on v1beta)
        for api_ver in ("v1", "v1beta", None):
            try:
                opts = {"api_version": api_ver} if api_ver else {}
                client = genai.Client(api_key=api_key, http_options=opts) if opts else genai.Client(api_key=api_key)
                # Probe: send a tiny embedding request to verify the model works
                probe = client.models.embed_content(
                    model="text-embedding-004",
                    contents=["probe"],
                )
                if probe.embeddings:
                    self._client = client
                    self._available = True
                    ver_label = api_ver or "default"
                    print(f"[MEMORY2] Embedding provider: Google text-embedding-004 (api={ver_label})")
                    return
            except Exception as e:
                ver_label = api_ver or "default"
                print(f"[MEMORY2] Probe failed (api={ver_label}): {e}")
        print("[MEMORY2] All Gemini embedding probes failed — using fallback embeddings")

    @property
    def is_real(self) -> bool:
        return self._available

    # --- public API ---

    async def embed(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """Embed a list of texts. Returns list of numpy float32 arrays (or None on per-item failure)."""
        if not texts:
            return []
        if self._available:
            try:
                return await self._embed_gemini_batched(texts)
            except Exception as e:
                print(f"[MEMORY2] Gemini embedding error, using fallback: {e}")
        return self._embed_fallback(texts)

    # --- Gemini implementation ---

    async def _embed_gemini_batched(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        all_embeddings: List[Optional[np.ndarray]] = []
        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[i : i + EMBED_BATCH_SIZE]
            batch_result = await asyncio.to_thread(self._embed_gemini_sync, batch)
            all_embeddings.extend(batch_result)
            if i + EMBED_BATCH_SIZE < len(texts):
                await asyncio.sleep(EMBED_BATCH_DELAY)
        return all_embeddings

    def _embed_gemini_sync(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        try:
            result = self._client.models.embed_content(
                model="text-embedding-004",
                contents=texts,
            )
            embeddings = []
            for emb in result.embeddings:
                vec = np.array(emb.values, dtype=np.float32)
                if self._dim is None:
                    self._dim = len(vec)
                embeddings.append(vec)
            return embeddings
        except Exception as e:
            print(f"[MEMORY2] Gemini embed failed, disabling real embeddings: {e}")
            self._available = False
            return [None] * len(texts)

    # --- fallback: deterministic bag-of-words hash ---

    def _embed_fallback(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        embeddings = []
        for text in texts:
            words = text.lower().split()
            vec = np.zeros(self._dim, dtype=np.float32)
            for i, word in enumerate(words):
                h = int(hashlib.md5(word.encode()).hexdigest(), 16)
                for j in range(4):
                    idx = (h >> (j * 8)) % self._dim
                    vec[idx] += 1.0 / (1 + i * 0.01)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            embeddings.append(vec)
        return embeddings


# ========================================
# VECTOR STORE (FAISS primary, NumPy fallback)
# ========================================

class VectorStore:
    """Nearest-neighbour search over chunk embeddings."""

    def __init__(self, db_path: str, persist_dir: str):
        self._db_path = db_path
        self._persist_dir = persist_dir
        self._faiss_path = os.path.join(persist_dir, "faiss.index")
        self._ids_path = self._faiss_path + ".ids"
        self._use_faiss = FAISS_AVAILABLE
        self._index = None
        self._id_map: List[int] = []

        os.makedirs(persist_dir, exist_ok=True)

        if self._use_faiss:
            self._load_faiss()
            print(f"[MEMORY2] Vector store: FAISS (dim={EMBEDDING_DIM})")
        else:
            print(f"[MEMORY2] Vector store: NumPy cosine fallback (dim={EMBEDDING_DIM})")

    @property
    def is_faiss(self) -> bool:
        return self._use_faiss

    # --- FAISS helpers ---

    def _load_faiss(self):
        if os.path.exists(self._faiss_path):
            try:
                self._index = faiss.read_index(self._faiss_path)
                if os.path.exists(self._ids_path):
                    with open(self._ids_path, "r") as f:
                        self._id_map = json.load(f)
                print(f"[MEMORY2] Loaded FAISS index: {self._index.ntotal} vectors")
                return
            except Exception as e:
                print(f"[MEMORY2] FAISS load failed, recreating: {e}")
        self._index = faiss.IndexFlatIP(EMBEDDING_DIM)
        self._id_map = []

    def _save_faiss(self):
        if self._use_faiss and self._index:
            faiss.write_index(self._index, self._faiss_path)
            with open(self._ids_path, "w") as f:
                json.dump(self._id_map, f)

    # --- public API ---

    def add(self, chunk_ids: List[int], embeddings: List[np.ndarray]):
        if not chunk_ids or not embeddings:
            return
        if self._use_faiss:
            vecs = np.vstack(embeddings).astype(np.float32)
            faiss.normalize_L2(vecs)
            self._index.add(vecs)
            self._id_map.extend(chunk_ids)
            self._save_faiss()
        # NumPy fallback stores embeddings in SQLite BLOBs (handled by MemoryEngine)

    def search(self, query_embedding: np.ndarray, k: int = 24) -> List[Tuple[int, float]]:
        if self._use_faiss:
            return self._search_faiss(query_embedding, k)
        return self._search_numpy(query_embedding, k)

    def clear(self):
        if self._use_faiss:
            self._index = faiss.IndexFlatIP(EMBEDDING_DIM)
            self._id_map = []
            self._save_faiss()

    # --- search implementations ---

    def _search_faiss(self, query_embedding: np.ndarray, k: int) -> List[Tuple[int, float]]:
        if not self._index or self._index.ntotal == 0:
            return []
        q = query_embedding.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(q)
        actual_k = min(k, self._index.ntotal)
        distances, indices = self._index.search(q, actual_k)
        results = []
        for i in range(actual_k):
            idx = int(indices[0][i])
            score = float(distances[0][i])
            if 0 <= idx < len(self._id_map):
                results.append((self._id_map[idx], score))
        return results

    def _search_numpy(self, query_embedding: np.ndarray, k: int) -> List[Tuple[int, float]]:
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute("SELECT id, embedding FROM memory_chunks WHERE embedding IS NOT NULL")
        rows = c.fetchall()
        conn.close()
        if not rows:
            return []
        q = query_embedding.astype(np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm > 0:
            q = q / q_norm
        scored = []
        for chunk_id, emb_blob in rows:
            vec = np.frombuffer(emb_blob, dtype=np.float32)
            if len(vec) != EMBEDDING_DIM:
                continue
            v_norm = np.linalg.norm(vec)
            if v_norm > 0:
                vec = vec / v_norm
            score = float(np.dot(q, vec))
            scored.append((chunk_id, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]


# ========================================
# MEMORY ENGINE
# ========================================

class MemoryEngine:
    """
    Memory Engine v2: hybrid retrieval with transcript indexing.

    Usage:
        engine = MemoryEngine("lumina_memory.db")
        engine.store_transcript("user", "hello world", project_name="myproject")
        await engine.index_text("transcript", "1", "hello world")
        results = await engine.search_memory("hello")
    """

    def __init__(self, db_path: str = "lumina_memory.db"):
        self.db_path = db_path
        self._persist_dir = os.path.join(os.path.dirname(os.path.abspath(db_path)) or ".", ".memory")
        self._embedding = EmbeddingProvider()
        self._vector_store = VectorStore(db_path, self._persist_dir)
        self._fts_available = self._check_fts()

        stats = self.get_status()
        print(
            f"[MEMORY2] Engine ready: chunks={stats['memory_chunks']} "
            f"transcripts={stats['transcripts']} faiss={stats['faiss_enabled']} "
            f"real_embed={stats['real_embeddings']} fts={self._fts_available}"
        )

    def _check_fts(self) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("SELECT * FROM memory_chunks_fts LIMIT 0")
            conn.close()
            return True
        except Exception as e:
            print(f"[MEMORY2] FTS5 not available: {e}")
            return False

    # ============================
    # Transcript Storage
    # ============================

    def store_transcript(
        self, role: str, content: str, project_name: str = None, session_id: str = None
    ) -> Optional[int]:
        if not content or not content.strip():
            return None
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        c.execute(
            "INSERT INTO transcripts (session_id, project_name, role, content, created_at) VALUES (?,?,?,?,?)",
            (session_id, project_name, role, content.strip(), now),
        )
        tid = c.lastrowid
        conn.commit()
        conn.close()
        print(f"[MEMORY2] transcript stored id={tid} role={role} len={len(content)}")
        return tid

    # ============================
    # Indexing
    # ============================

    async def index_text(
        self, source_type: str, source_id: str, text: str, project_name: str = None
    ) -> int:
        """Chunk, dedup, embed, and index text. Returns count of new chunks added."""
        chunks = chunk_text(text)
        if not chunks:
            return 0

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        new_chunks = []
        new_hashes = []
        for chunk in chunks:
            h = hash_chunk(chunk)
            c.execute("SELECT id FROM memory_chunks WHERE hash = ?", (h,))
            if c.fetchone():
                continue
            new_chunks.append(chunk)
            new_hashes.append(h)

        if not new_chunks:
            conn.close()
            return 0

        # Embed new chunks
        try:
            embeddings = await self._embedding.embed(new_chunks)
        except Exception as e:
            print(f"[MEMORY2] Embedding error during indexing: {e}")
            embeddings = [None] * len(new_chunks)

        now = datetime.utcnow().isoformat()
        new_ids = []
        valid_embeds = []

        for i, (chunk, h) in enumerate(zip(new_chunks, new_hashes)):
            emb = embeddings[i] if i < len(embeddings) else None
            emb_blob = emb.tobytes() if emb is not None else None
            emb_dim = EMBEDDING_DIM if emb is not None else None
            try:
                c.execute(
                    """INSERT OR IGNORE INTO memory_chunks
                       (source_type, source_id, project_name, chunk_text, created_at, embedding, embedding_dim, hash)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (source_type, str(source_id), project_name, chunk, now, emb_blob, emb_dim, h),
                )
                row_id = c.lastrowid
                if row_id:
                    new_ids.append(row_id)
                    if emb is not None:
                        valid_embeds.append((row_id, emb))
                    # Sync FTS
                    if self._fts_available:
                        try:
                            c.execute(
                                "INSERT INTO memory_chunks_fts(rowid, chunk_text) VALUES (?,?)",
                                (row_id, chunk),
                            )
                        except Exception:
                            pass
            except sqlite3.IntegrityError:
                pass  # dedup collision

        conn.commit()
        conn.close()

        # Add to vector store
        if valid_embeds:
            ids, vecs = zip(*valid_embeds)
            self._vector_store.add(list(ids), list(vecs))

        if new_ids:
            print(f"[MEMORY2] indexed chunks={len(new_ids)} source={source_type} id={source_id}")
        return len(new_ids)

    async def index_memory_item(
        self, memory_id: int, mem_type: str, content: str, project_name: str = None
    ) -> int:
        return await self.index_text(mem_type, str(memory_id), content, project_name)

    async def index_transcript_message(
        self, transcript_id: int, content: str, project_name: str = None
    ) -> int:
        return await self.index_text("transcript", str(transcript_id), content, project_name)

    async def reindex_all(self) -> Dict:
        """Clear and rebuild all indexes from source tables. Safe + idempotent."""
        print("[MEMORY2] reindex_all: clearing indexes...")

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM memory_chunks")
        if self._fts_available:
            try:
                c.execute("DELETE FROM memory_chunks_fts")
            except Exception:
                pass
        conn.commit()
        conn.close()

        self._vector_store.clear()

        counts = {"memories": 0, "summaries": 0, "transcripts": 0, "total_chunks": 0}

        # Re-index memories table
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("SELECT id, type, content FROM memories")
            rows = c.fetchall()
        except Exception:
            rows = []
        conn.close()

        for mem_id, mem_type, content in rows:
            n = await self.index_text(mem_type, str(mem_id), content)
            counts["total_chunks"] += n
            if mem_type in ("session_summary", "conversation_summary"):
                counts["summaries"] += 1
            else:
                counts["memories"] += 1

        # Re-index transcripts table
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("SELECT id, content, project_name FROM transcripts")
            rows = c.fetchall()
        except Exception:
            rows = []
        conn.close()

        for tid, content, project in rows:
            n = await self.index_text("transcript", str(tid), content, project)
            counts["total_chunks"] += n
            counts["transcripts"] += 1

        # Rebuild FTS from content table (belt-and-suspenders)
        if self._fts_available:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute("INSERT INTO memory_chunks_fts(memory_chunks_fts) VALUES('rebuild')")
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[MEMORY2] FTS rebuild note: {e}")

        print(f"[MEMORY2] reindex_all done: {counts}")
        return counts

    # ============================
    # Search / Retrieval
    # ============================

    def _fts_search(self, query: str, k: int = 24) -> List[Tuple[int, float]]:
        safe_q = sanitize_fts_query(query)
        if not safe_q:
            return self._like_search(query, k)
        if not self._fts_available:
            return self._like_search(query, k)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute(
                """SELECT mc.id, fts.rank
                   FROM memory_chunks_fts fts
                   JOIN memory_chunks mc ON mc.id = fts.rowid
                   WHERE memory_chunks_fts MATCH ?
                   ORDER BY fts.rank
                   LIMIT ?""",
                (safe_q, k),
            )
            results = [(row[0], -row[1]) for row in c.fetchall()]  # rank is negative
            conn.close()
            return results
        except Exception as e:
            conn.close()
            print(f"[MEMORY2] FTS search error ({e}), falling back to LIKE")
            return self._like_search(query, k)

    def _like_search(self, query: str, k: int = 24) -> List[Tuple[int, float]]:
        words = re.findall(r"[a-zA-Z0-9]+", query.lower())[:6]
        if not words:
            return []
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        conditions = " OR ".join(["chunk_text LIKE ?"] * len(words))
        params = [f"%{w}%" for w in words]
        c.execute(
            f"SELECT id, chunk_text FROM memory_chunks WHERE {conditions} ORDER BY created_at DESC LIMIT ?",
            params + [k],
        )
        results = []
        for row in c.fetchall():
            score = sum(1.0 for w in words if w in row[1].lower())
            results.append((row[0], score))
        conn.close()
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

    async def _vector_search(self, query: str, k: int = 24) -> List[Tuple[int, float]]:
        try:
            embeddings = await self._embedding.embed([query])
            if not embeddings or embeddings[0] is None:
                return []
            return self._vector_store.search(embeddings[0], k)
        except Exception as e:
            print(f"[MEMORY2] Vector search error: {e}")
            return []

    @staticmethod
    def _normalize_scores(results: List[Tuple[int, float]]) -> List[Tuple[int, float]]:
        if not results:
            return []
        scores = [s for _, s in results]
        min_s, max_s = min(scores), max(scores)
        if max_s <= min_s:
            return [(cid, 1.0) for cid, _ in results]
        spread = max_s - min_s
        return [(cid, (s - min_s) / spread) for cid, s in results]

    def _get_chunk_metadata(self, chunk_ids: List[int]) -> Dict[int, Dict]:
        if not chunk_ids:
            return {}
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        placeholders = ",".join("?" * len(chunk_ids))
        c.execute(
            f"""SELECT id, source_type, source_id, project_name, chunk_text, created_at
                FROM memory_chunks WHERE id IN ({placeholders})""",
            chunk_ids,
        )
        meta = {}
        for row in c.fetchall():
            meta[row[0]] = {
                "id": row[0],
                "source_type": row[1],
                "source_id": row[2],
                "project_name": row[3],
                "chunk_text": row[4],
                "created_at": row[5],
            }
        conn.close()
        return meta

    async def search_memory(self, query: str, top_k: int = MAX_CHUNKS_INJECT) -> List[Dict]:
        """
        Hybrid search: 0.6*vector + 0.4*keyword, with recency and type boosts.
        Returns at most top_k results, deduped.
        """
        if not query or not query.strip():
            return []

        fetch_k = top_k * 3

        # Run keyword + vector search
        keyword_results = self._fts_search(query, fetch_k)
        vector_results = await self._vector_search(query, fetch_k)

        # Normalize to 0..1
        keyword_norm = self._normalize_scores(keyword_results)
        vector_norm = self._normalize_scores(vector_results)

        # Merge scores
        scores: Dict[int, float] = {}
        for cid, score in vector_norm:
            scores[cid] = scores.get(cid, 0) + 0.6 * score
        for cid, score in keyword_norm:
            scores[cid] = scores.get(cid, 0) + 0.4 * score

        if not scores:
            print(f"[MEMORY2] search query='{query[:40]}' keyword_n=0 vector_n=0 merged_n=0")
            return []

        # Fetch metadata for all candidates
        all_ids = list(scores.keys())
        metadata = self._get_chunk_metadata(all_ids)

        # Apply boosts
        now = datetime.utcnow()
        query_lower = query.lower()
        identity_kw = {"my", "i", "me", "prefer", "name", "who", "am", "about"}
        is_identity_query = bool(set(query_lower.split()) & identity_kw)

        for cid in list(scores.keys()):
            meta = metadata.get(cid)
            if not meta:
                continue
            # Recency boost
            try:
                created = datetime.fromisoformat(meta["created_at"])
                age_days = (now - created).total_seconds() / 86400
                if age_days < 7:
                    scores[cid] += 0.05
                elif age_days < 30:
                    scores[cid] += 0.02
            except Exception:
                pass
            # Type boost for identity-adjacent queries
            if is_identity_query and meta["source_type"] in ("fact", "preference"):
                scores[cid] += 0.08

        # Rank, dedup, cap
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        seen_texts = set()

        for cid, score in ranked:
            if len(results) >= top_k:
                break
            meta = metadata.get(cid)
            if not meta:
                continue
            # Dedup by first 100 chars
            text_key = meta["chunk_text"][:100].lower().strip()
            if text_key in seen_texts:
                continue
            seen_texts.add(text_key)

            results.append({
                "chunk_id": cid,
                "source_type": meta["source_type"],
                "source_id": meta["source_id"],
                "project_name": meta["project_name"],
                "text": meta["chunk_text"],
                "created_at": meta["created_at"],
                "score": round(score, 4),
            })

        kw_n = len(keyword_results)
        vec_n = len(vector_results)
        print(f"[MEMORY2] search query='{query[:40]}' keyword_n={kw_n} vector_n={vec_n} merged_n={len(results)}")
        return results

    # ============================
    # Status
    # ============================

    def get_status(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        def _count(table):
            try:
                c.execute(f"SELECT COUNT(*) FROM {table}")
                return c.fetchone()[0]
            except Exception:
                return 0

        status = {
            "memories": _count("memories"),
            "transcripts": _count("transcripts"),
            "memory_chunks": _count("memory_chunks"),
            "embedded_chunks": 0,
            "faiss_enabled": self._vector_store.is_faiss,
            "real_embeddings": self._embedding.is_real,
            "fts_available": self._fts_available,
            "embedding_dim": EMBEDDING_DIM,
        }
        try:
            c.execute("SELECT COUNT(*) FROM memory_chunks WHERE embedding IS NOT NULL")
            status["embedded_chunks"] = c.fetchone()[0]
        except Exception:
            pass
        # State counts
        try:
            c.execute("SELECT state, COUNT(*) FROM memories GROUP BY state")
            status["by_state"] = dict(c.fetchall())
        except Exception:
            status["by_state"] = {}
        conn.close()
        return status

    # ============================
    # ASSUMPTION & INTENT DETECTION
    # ============================

    # Patterns that indicate future intent / plans / commitments
    _INTENT_PATTERNS = [
        (r"\b(?:i(?:'ll| will| am going to| plan to| want to| intend to|'m going to))\b(.{10,120})", "intent", 0.70),
        (r"\b(?:we(?:'ll| will| are going to| plan to| should| need to))\b(.{10,120})", "intent", 0.65),
        (r"\b(?:let(?:'s| us))\b(.{10,100})", "intent", 0.60),
        (r"\b(?:tomorrow|next week|next month|tonight|this weekend|by friday|by monday)\b", "intent", 0.60),
        (r"\b(?:deadline|due date|ship|release|launch|deploy|finish|complete)\b(.{5,100})", "intent", 0.65),
    ]

    # Patterns that indicate assumptions / beliefs / preferences stated as facts
    _ASSUMPTION_PATTERNS = [
        (r"\b(?:i think|i believe|i guess|probably|maybe|i assume|i figure)\b(.{10,150})", "assumption", 0.55),
        (r"\b(?:it seems like|it looks like|apparently|i heard that)\b(.{10,150})", "assumption", 0.50),
        (r"\b(?:i(?:'m| am) (?:pretty |fairly )?sure)\b(.{10,150})", "assumption", 0.65),
    ]

    def detect_memory_signals(self, text: str, memory_store) -> List[Dict]:
        """
        Detect intent and assumption signals in user text.
        Creates memories with appropriate state and confidence.
        Returns list of created memory dicts with 'response_hint' for Lumina to say.
        
        This is the core "assume first, explain, allow correction" logic.
        """
        if not text or len(text.strip()) < 12:
            return []

        text_lower = text.lower().strip()
        created = []

        # Check intent patterns
        for pattern, mem_type, base_conf in self._INTENT_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                # Extract the full sentence containing the match
                content = self._extract_sentence(text, match.start())
                if content and len(content) > 12:
                    # Check for duplicates
                    if self._is_duplicate_memory(memory_store, content):
                        continue
                    confidence = min(base_conf + 0.1 * self._specificity_bonus(content), 0.95)
                    mid = memory_store.add_memory(
                        memory_type="intent",
                        content=content,
                        metadata={"source": "auto_detect", "pattern": pattern[:30]},
                        state="pending",
                        confidence=round(confidence, 2),
                        priority=40,
                    )
                    created.append({
                        "id": mid, "type": "intent", "content": content,
                        "confidence": confidence, "state": "pending",
                        "response_hint": f"I'll treat that as the current plan and adjust if needed.",
                    })
                    print(f"[MEMORY DECISION] Auto-detected intent (id={mid}, conf={confidence:.2f}): {content[:60]}")
                    break  # One detection per message

        # Check assumption patterns (only if no intent was found)
        if not created:
            for pattern, mem_type, base_conf in self._ASSUMPTION_PATTERNS:
                match = re.search(pattern, text_lower)
                if match:
                    content = self._extract_sentence(text, match.start())
                    if content and len(content) > 12:
                        if self._is_duplicate_memory(memory_store, content):
                            continue
                        confidence = min(base_conf + 0.05 * self._specificity_bonus(content), 0.85)
                        mid = memory_store.add_memory(
                            memory_type="assumption",
                            content=content,
                            metadata={"source": "auto_detect", "pattern": pattern[:30]},
                            state="pending",
                            confidence=round(confidence, 2),
                            priority=30,
                        )
                        created.append({
                            "id": mid, "type": "assumption", "content": content,
                            "confidence": confidence, "state": "pending",
                            "response_hint": f"Noted — I'm keeping that as tentative for now.",
                        })
                        print(f"[MEMORY DECISION] Auto-detected assumption (id={mid}, conf={confidence:.2f}): {content[:60]}")
                        break

        return created

    @staticmethod
    def _extract_sentence(text: str, match_start: int) -> str:
        """Extract the sentence containing the match position."""
        # Walk backward to sentence start
        start = match_start
        while start > 0 and text[start - 1] not in '.!?\n':
            start -= 1
        # Walk forward to sentence end
        end = match_start
        while end < len(text) and text[end] not in '.!?\n':
            end += 1
        sentence = text[start:end].strip().rstrip('.!?').strip()
        # Cap length
        if len(sentence) > 200:
            sentence = sentence[:200].rsplit(' ', 1)[0]
        return sentence

    @staticmethod
    def _specificity_bonus(content: str) -> float:
        """Higher score for specific content (numbers, dates, proper nouns)."""
        bonus = 0.0
        if re.search(r'\d', content):
            bonus += 1.0
        if re.search(r'[A-Z][a-z]', content):
            bonus += 0.5
        if len(content.split()) > 6:
            bonus += 0.5
        return bonus

    @staticmethod
    def _is_duplicate_memory(memory_store, content: str, threshold: int = 3) -> bool:
        """Check if similar memory already exists."""
        try:
            existing = memory_store.search_memories(content[:50], limit=threshold)
            content_lower = content.lower()
            for mem in existing:
                if mem['content'].lower() in content_lower or content_lower in mem['content'].lower():
                    return True
        except Exception:
            pass
        return False

    # ============================
    # PRIORITY DECAY & REVISIT
    # ============================

    def run_decay(self, memory_store) -> Dict:
        """Run priority decay. Call this periodically (e.g., on session start or idle timer)."""
        return memory_store.decay_priorities(threshold_days=7, decay_amount=2, dormant_threshold=10)

    def get_revisit_candidates(self, memory_store) -> List[Dict]:
        """
        Get pending memories that are old enough to revisit naturally.
        Lumina should weave these into conversation, not force-ask.
        """
        return memory_store.get_stale_pending(older_than_hours=24, limit=2)

    def handle_confirmation(self, memory_store, memory_id: int, confirmed: bool) -> str:
        """
        Handle user confirmation/denial of a pending memory.
        Returns a response hint for Lumina.
        """
        if confirmed:
            memory_store.promote_memory(memory_id, new_state="active", confidence=1.0)
            return "Got it — locked that in."
        else:
            memory_store.demote_memory(memory_id, new_state="dormant")
            return "No problem — I've set that aside."

    def build_revisit_hint(self, stale_memories: List[Dict]) -> Optional[str]:
        """
        Build a natural revisit prompt for Lumina to weave into conversation.
        Returns None if nothing to revisit.
        """
        if not stale_memories:
            return None
        mem = stale_memories[0]  # Revisit one at a time
        content = mem['content'][:120]
        if mem['type'] == 'intent':
            return f"[REVISIT] Earlier you mentioned: \"{content}\" — still the plan?"
        elif mem['type'] == 'assumption':
            return f"[REVISIT] I had noted: \"{content}\" — is that still accurate?"
        return None
