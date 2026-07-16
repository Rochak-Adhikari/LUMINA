"""
test_runtime_stability.py — Simulates runtime scenarios for FIX A/B/E.
Run: conda activate lumina; python test_runtime_stability.py
"""
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# TEST 1: TranscriptAggregator — micro-fragment batching
# ============================================================
print("=" * 60)
print("TEST 1: TranscriptAggregator — no micro-stores")
print("=" * 60)

# Import after path fix
from server import TranscriptAggregator, _TRANSCRIPT_NOISE

agg = TranscriptAggregator()

# Simulate junk fragments
for junk in ["ok", "hmm", "yo", "yes", "ah"]:
    agg.add_fragment("user", junk)
assert agg._buf["user"] == "", "FAIL: junk fragments should be discarded"
print("[PASS] Junk fragments discarded")

# Simulate short fragments that accumulate
agg.add_fragment("user", "hey what")
assert agg._buf["user"].strip() != "", "FAIL: non-junk should buffer"
result = agg.check_flush("user")
assert result is None, "FAIL: 8 chars should not flush (min=25)"
print("[PASS] Short fragment buffered, not flushed")

# Add more to cross min_chars threshold
agg.add_fragment("user", "about that server deployment")
result = agg.check_flush("user")
assert result is not None, "FAIL: should flush at >= 25 chars"
assert len(result) >= 25, f"FAIL: flushed text too short: {len(result)}"
print(f"[PASS] Flushed at {len(result)} chars (>= 25)")

# Sentence-end flush
agg.add_fragment("user", "sounds good.")
result = agg.check_flush("user")
assert result is not None, "FAIL: sentence-end punctuation should flush"
assert result.endswith("."), "FAIL: should end with period"
print(f"[PASS] Sentence-end flush: '{result}'")

# Force flush on real user turn
agg.add_fragment("user", "partial thought about")
forced = agg.force_flush("user", reason="user_turn")
assert forced is not None, "FAIL: force_flush should return text >= 10 chars"
print(f"[PASS] Force flush on user_turn: '{forced}'")

# Force flush with tiny leftover (should discard)
agg.add_fragment("user", "hi")  # This is junk, discarded by _is_junk
forced2 = agg.force_flush("user", reason="user_turn")
assert forced2 is None, "FAIL: force_flush should return None for empty buffer"
print("[PASS] Force flush with empty buffer returns None")

# Silence flush
agg.add_fragment("user", "something interesting here")
agg._last_frag_ts = time.time() - 3  # simulate 3s ago
stale = agg.flush_stale()
assert len(stale) >= 1, "FAIL: should flush stale buffer"
print(f"[PASS] Silence flush: {len(stale)} items")

print()

# ============================================================
# TEST 2: Idle timer — real user turns only
# ============================================================
print("=" * 60)
print("TEST 2: Idle timer — fragments do NOT reset idle")
print("=" * 60)

from persona_engine import PersonaEngine

pe = PersonaEngine()
pe.idle_timeout_s = 5  # speed up for test
pe.idle_min_gap_s = 2

# Set last user turn to 10s ago
pe._last_user_ts = time.time() - 10

# Simulate transcript fragments (should NOT reset idle)
# In production, record_user_message() is no longer called from transcript handler
# So _last_user_ts stays at 10s ago

msg, stage = pe.check_idle()
assert msg is not None, "FAIL: idle should trigger (10s > 5s timeout)"
assert stage == 1, f"FAIL: expected stage 1, got {stage}"
print(f"[PASS] Idle stage 1 triggered after 10s silence (timeout=5s)")

# Now simulate real user turn
pe.record_user_message()
pe._last_idle_ts = time.time() - 10  # reset cooldown for test
msg2, stage2 = pe.check_idle()
assert msg2 is None, "FAIL: idle should NOT trigger right after real user turn"
print("[PASS] Idle suppressed after record_user_message()")

print()

# ============================================================
# TEST 3: Completed work suppression (FIX E)
# ============================================================
print("=" * 60)
print("TEST 3: Completed work suppression")
print("=" * 60)

# E6 content, user NOT asking about E6
assert PersonaEngine.should_suppress_memory(
    "Phase E6 browser hardening complete", "suggest some music"
) == True, "FAIL: should suppress E6 when user asks about music"
print("[PASS] E6 suppressed when user asks about music")

# E6 content, user IS asking about E6
assert PersonaEngine.should_suppress_memory(
    "Phase E6 browser hardening complete", "what was E6 about"
) == False, "FAIL: should NOT suppress when user explicitly asks about E6"
print("[PASS] E6 NOT suppressed when user asks about E6")

# E7 content, unrelated
assert PersonaEngine.should_suppress_memory(
    "E7 memory budget implemented", "help me with docker"
) == True, "FAIL: should suppress E7 for unrelated query"
print("[PASS] E7 suppressed for unrelated query")

# Non-phase content, never suppress
assert PersonaEngine.should_suppress_memory(
    "User prefers dark mode", "what are my preferences"
) == False, "FAIL: non-phase content should never be suppressed"
print("[PASS] Non-phase content passes through")

# Phase content with 'summarize E6/E7' (explicit ask)
assert PersonaEngine.should_suppress_memory(
    "Phase E6 complete, Phase E7 started", "summarize E6 and E7"
) == False, "FAIL: should NOT suppress when user asks to summarize"
print("[PASS] Phase content passes when user asks to summarize")

print()
print("=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)
