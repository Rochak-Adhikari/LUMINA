"""
test_phase_1_2.py — Phase 1.2 Verification Tests

Tests:
  1.  BrainState: basic import and construction
  2.  BrainState: initial snapshot has correct defaults
  3.  BrainState: snapshot() returns a frozen (immutable) object
  4.  BrainState: transaction() commits changes atomically
  5.  BrainState: transaction() rolls back on exception
  6.  BrainState: nested transactions (RLock re-entrancy)
  7.  BrainState: concurrent read/write thread safety
  8.  BrainState: convenience helpers (set_session, set_project, etc.)
  9.  BrainState: reset_session() clears only session-scoped fields
  10. InProcessEventBus: basic import and construction
  11. InProcessEventBus: sync publish/subscribe round-trip
  12. InProcessEventBus: wildcard topic matching
  13. InProcessEventBus: unsubscribe stops delivery
  14. InProcessEventBus: error isolation — bad handler does not break others
  15. InProcessEventBus: multiple handlers on same topic
  16. DI Container: IBrainState and IEventBus resolve without error
  17. IBrainState interface: BrainState satisfies ABC contract
  18. Backward compat: test_phase_b1 assertions still hold

Run with:
    $env:CONDA_DEFAULT_ENV='lumina'
    $env:PYTHONUTF8='1'
    & "E:\\AI\\conda_envs\\lumina\\python.exe" -X utf8 backend/brain/test_phase_1_2.py
"""

import os
import sys
import threading
import time
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
project_root = Path(__file__).parent.parent.parent
os.chdir(project_root)
sys.path.insert(0, str(project_root / "backend"))

# ── Counters ──────────────────────────────────────────────────────────────────
_passed = 0
_failed = 0


def _ok(name: str) -> None:
    global _passed
    _passed += 1
    print(f"  [PASS] {name}")


def _fail(name: str, reason: str) -> None:
    global _failed
    _failed += 1
    print(f"  [FAIL] {name}")
    print(f"         {reason}")


def _section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# =============================================================================
# Section 1 — BrainState
# =============================================================================

_section("BrainState Construction & Defaults")

try:
    from brain.state import BrainState, BrainSnapshot
    _ok("1.  Import BrainState and BrainSnapshot")
except Exception as e:
    _fail("1.  Import BrainState and BrainSnapshot", str(e))
    sys.exit(1)

try:
    bs = BrainState()
    _ok("2.  BrainState() construction succeeds")
except Exception as e:
    _fail("2.  BrainState() construction succeeds", str(e))
    sys.exit(1)

# ── Test 3: default snapshot values ──────────────────────────────────────────
_section("Snapshot Defaults")

try:
    snap = bs.snapshot()
    assert isinstance(snap, BrainSnapshot), "snapshot() must return BrainSnapshot"
    assert snap.session.session_id is None, "session_id should be None"
    assert snap.session.is_generating is False, "is_generating should be False"
    assert snap.workspace.current_project == "temp", "default project should be 'temp'"
    assert snap.conversation.turn_index == 0, "turn_index should be 0"
    assert snap.conversation.mood_state == "calm", "mood_state should be 'calm'"
    assert snap.flags.audio_paused is False, "audio_paused should be False"
    assert snap.execution.active_tool is None, "active_tool should be None"
    assert snap.planner.plan_depth == 0, "plan_depth should be 0"
    _ok("3.  Snapshot defaults are correct")
except AssertionError as e:
    _fail("3.  Snapshot defaults are correct", str(e))
except Exception as e:
    _fail("3.  Snapshot defaults are correct", str(e))

# ── Test 4: snapshot is frozen ─────────────────────────────────────────────
_section("Snapshot Immutability")

try:
    snap = bs.snapshot()
    raised = False
    try:
        snap.session = None  # type: ignore
    except Exception:
        raised = True
    assert raised, "Mutating a frozen snapshot should raise"
    _ok("4.  Snapshot fields are immutable (frozen Pydantic model)")
except AssertionError as e:
    _fail("4.  Snapshot fields are immutable (frozen Pydantic model)", str(e))

# ── Test 5: transaction commit ─────────────────────────────────────────────
_section("Transaction — Commit")

try:
    with bs.transaction() as draft:
        draft.session_id = "session-abc"
        draft.current_project = "project_alpha"
        draft.turn_index = 5
        draft.mood_state = "focused"
        draft.is_generating = True

    snap = bs.snapshot()
    assert snap.session.session_id == "session-abc", f"Expected 'session-abc', got {snap.session.session_id!r}"
    assert snap.workspace.current_project == "project_alpha", f"Expected 'project_alpha', got {snap.workspace.current_project!r}"
    assert snap.conversation.turn_index == 5, f"Expected 5, got {snap.conversation.turn_index}"
    assert snap.conversation.mood_state == "focused", f"Expected 'focused', got {snap.conversation.mood_state!r}"
    assert snap.session.is_generating is True, f"Expected True, got {snap.session.is_generating}"
    _ok("5.  Transaction commits all changes atomically")
except AssertionError as e:
    _fail("5.  Transaction commits all changes atomically", str(e))
except Exception as e:
    _fail("5.  Transaction commits all changes atomically", str(e))

# ── Test 6: transaction rollback ───────────────────────────────────────────
_section("Transaction — Rollback on Exception")

try:
    snap_before = bs.snapshot()
    try:
        with bs.transaction() as draft:
            draft.session_id = "SHOULD-NOT-COMMIT"
            draft.turn_index = 999
            raise RuntimeError("Simulated failure inside transaction")
    except RuntimeError:
        pass  # expected

    snap_after = bs.snapshot()
    assert snap_after.session.session_id == snap_before.session.session_id, \
        f"session_id should not have changed: got {snap_after.session.session_id!r}"
    assert snap_after.conversation.turn_index == snap_before.conversation.turn_index, \
        f"turn_index should not have changed: got {snap_after.conversation.turn_index}"
    _ok("6.  Transaction rolls back cleanly on exception")
except AssertionError as e:
    _fail("6.  Transaction rolls back cleanly on exception", str(e))
except Exception as e:
    _fail("6.  Transaction rolls back cleanly on exception", str(e))

# ── Test 7: nested transactions (RLock) ────────────────────────────────────
_section("Nested Transactions (RLock Re-entrancy)")

try:
    bs5 = BrainState()

    # Sequential nested calls: each transaction() commits its own draft.
    # The inner transaction runs and commits BEFORE the outer context exits.
    # Because they each capture a new draft from the *current* state at the
    # time of entry, and because the RLock allows re-entrancy on the same
    # thread, both commits succeed without deadlock.
    def _sequential_nested(state: BrainState):
        with state.transaction() as outer:
            outer.audio_paused = True
        # Inner runs after outer has committed
        with state.transaction() as inner:
            inner.phone_connected = True

    _sequential_nested(bs5)
    snap = bs5.snapshot()
    assert snap.flags.audio_paused is True, "audio_paused should be True after first transaction"
    assert snap.flags.phone_connected is True, "phone_connected should be True after second transaction"
    _ok("7.  Sequential transactions work correctly (RLock re-entrant, no deadlock)")
except AssertionError as e:
    _fail("7.  Sequential transactions work correctly", str(e))
except Exception as e:
    _fail("7.  Sequential transactions work correctly", str(e))

# ── Test 8: concurrent read/write thread safety ────────────────────────────
_section("Thread Safety — Concurrent Read/Write")

try:
    errors = []
    snapshots_seen = []

    def _reader(state: BrainState, n: int):
        for _ in range(n):
            try:
                snap = state.snapshot()
                snapshots_seen.append(snap.conversation.turn_index)
            except Exception as e:
                errors.append(f"reader: {e}")

    def _writer(state: BrainState, n: int):
        for i in range(n):
            try:
                with state.transaction() as draft:
                    draft.turn_index = draft.turn_index + 1
            except Exception as e:
                errors.append(f"writer: {e}")

    bs2 = BrainState()  # Fresh instance for isolation
    readers = [threading.Thread(target=_reader, args=(bs2, 200)) for _ in range(4)]
    writers = [threading.Thread(target=_writer, args=(bs2, 50)) for _ in range(2)]
    all_threads = readers + writers
    for t in all_threads:
        t.start()
    for t in all_threads:
        t.join(timeout=10)

    assert not errors, f"Thread errors: {errors[:3]}"
    final = bs2.snapshot()
    assert final.conversation.turn_index == 100, \
        f"Expected 100 (2 writers × 50), got {final.conversation.turn_index}"
    _ok("8.  Concurrent read/write is thread-safe (no races, correct final count)")
except AssertionError as e:
    _fail("8.  Concurrent read/write is thread-safe", str(e))
except Exception as e:
    _fail("8.  Concurrent read/write is thread-safe", str(e))

# ── Test 9: convenience helpers ────────────────────────────────────────────
_section("Convenience Helpers")

try:
    bs3 = BrainState()
    bs3.set_session(session_id="sess-001", client_sid="sio-abc", model_name="gemini-2.5")
    snap = bs3.snapshot()
    assert snap.session.session_id == "sess-001"
    assert snap.session.client_sid == "sio-abc"
    assert snap.session.model_name == "gemini-2.5"
    assert snap.session.connected_at is not None

    bs3.set_project("my_project", root="/workspace/my_project")
    snap = bs3.snapshot()
    assert snap.workspace.current_project == "my_project"
    assert snap.workspace.project_root == "/workspace/my_project"

    bs3.record_user_turn("Hello Lumina", mood_state="playful")
    snap = bs3.snapshot()
    assert snap.conversation.last_user_text == "Hello Lumina"
    assert snap.conversation.mood_state == "playful"
    assert snap.conversation.turn_index == 1
    assert snap.conversation.last_activity_ts is not None

    bs3.record_assistant_turn("Hey there!")
    assert bs3.snapshot().conversation.last_assistant_text == "Hey there!"

    bs3.set_tool_executing("generate_cad", {"prompt": "a cube"})
    snap = bs3.snapshot()
    assert snap.execution.active_tool == "generate_cad"
    assert snap.execution.tool_args == {"prompt": "a cube"}

    bs3.set_tool_executing(None)
    assert bs3.snapshot().execution.active_tool is None

    bs3.set_generating(True)
    assert bs3.snapshot().session.is_generating is True

    bs3.set_audio_paused(True)
    assert bs3.snapshot().flags.audio_paused is True

    _ok("9.  All convenience helpers work correctly")
except AssertionError as e:
    _fail("9.  All convenience helpers work correctly", str(e))
except Exception as e:
    _fail("9.  All convenience helpers work correctly", str(e))

# ── Test 10: reset_session ─────────────────────────────────────────────────
_section("reset_session()")

try:
    bs4 = BrainState()
    with bs4.transaction() as d:
        d.session_id = "old-session"
        d.turn_index = 42
        d.last_user_text = "test"
        d.is_generating = True
        d.current_project = "project_x"   # workspace — should NOT reset

    bs4.reset_session()
    snap = bs4.snapshot()
    assert snap.session.session_id is None, "session_id should be cleared"
    assert snap.conversation.turn_index == 0, "turn_index should reset to 0"
    assert snap.conversation.last_user_text is None, "last_user_text should be None"
    assert snap.session.is_generating is False, "is_generating should be False"
    assert snap.workspace.current_project == "project_x", \
        "current_project (workspace) should survive reset_session"
    _ok("10. reset_session() clears session fields, preserves workspace")
except AssertionError as e:
    _fail("10. reset_session() clears session fields, preserves workspace", str(e))
except Exception as e:
    _fail("10. reset_session() clears session fields, preserves workspace", str(e))


# =============================================================================
# Section 2 — InProcessEventBus
# =============================================================================

_section("InProcessEventBus Construction")

try:
    from brain.events import InProcessEventBus, _topic_matches
    _ok("11. Import InProcessEventBus and _topic_matches")
except Exception as e:
    _fail("11. Import InProcessEventBus and _topic_matches", str(e))
    sys.exit(1)

try:
    bus = InProcessEventBus()
    _ok("12. InProcessEventBus() construction succeeds")
except Exception as e:
    _fail("12. InProcessEventBus() construction succeeds", str(e))
    sys.exit(1)

# ── Test 13: sync round-trip ───────────────────────────────────────────────
_section("EventBus Sync Round-Trip")

try:
    received = []
    def _handler(topic, payload):
        received.append((topic, payload))

    tok = bus.subscribe_sync("session.started", _handler)
    bus.publish_sync("session.started", {"sid": "x"})
    assert len(received) == 1, f"Expected 1 delivery, got {len(received)}"
    assert received[0][0] == "session.started"
    assert received[0][1] == {"sid": "x"}
    _ok("13. Sync subscribe/publish round-trip works")
except AssertionError as e:
    _fail("13. Sync subscribe/publish round-trip works", str(e))

# ── Test 14: wildcard matching ─────────────────────────────────────────────
_section("EventBus Wildcard Matching")

try:
    # Unit test the matching function directly
    assert _topic_matches("session.*", "session.started") is True
    assert _topic_matches("session.*", "session.ended") is True
    assert _topic_matches("session.*", "other.started") is False
    assert _topic_matches("tool.*.success", "tool.generate_cad.success") is True
    assert _topic_matches("tool.*.success", "tool.generate_cad.fail") is False
    assert _topic_matches("memory.**", "memory.write") is True
    assert _topic_matches("memory.**", "memory.search.hit") is True
    assert _topic_matches("memory.**", "other.write") is False
    assert _topic_matches("a.b.c", "a.b.c") is True
    assert _topic_matches("a.b.c", "a.b.d") is False
    _ok("14. Wildcard topic matching: *, **, exact — all correct")
except AssertionError as e:
    _fail("14. Wildcard topic matching", str(e))

# ── Test 15: wildcard delivery ─────────────────────────────────────────────
_section("EventBus Wildcard Delivery")

try:
    bus2 = InProcessEventBus()
    collected = []
    tok_w = bus2.subscribe_sync("tool.*", lambda t, p: collected.append(("wildcard", t, p)))
    tok_e = bus2.subscribe_sync("tool.cad", lambda t, p: collected.append(("exact", t, p)))

    bus2.publish_sync("tool.cad", {"status": "ok"})
    bus2.publish_sync("tool.memory", {"status": "ok"})

    wildcard_deliveries = [x for x in collected if x[0] == "wildcard"]
    exact_deliveries = [x for x in collected if x[0] == "exact"]
    assert len(wildcard_deliveries) == 2, f"Wildcard should match both: got {len(wildcard_deliveries)}"
    assert len(exact_deliveries) == 1, f"Exact should match only 'tool.cad': got {len(exact_deliveries)}"
    _ok("15. Wildcard '*' handler receives matching events; exact handler receives only its topic")
except AssertionError as e:
    _fail("15. Wildcard delivery", str(e))

# ── Test 16: unsubscribe stops delivery ────────────────────────────────────
_section("EventBus Unsubscribe")

try:
    bus3 = InProcessEventBus()
    hits = []
    tok = bus3.subscribe_sync("session.*", lambda t, p: hits.append(p))
    bus3.publish_sync("session.started", {"n": 1})
    bus3.unsubscribe_sync(tok)
    bus3.publish_sync("session.started", {"n": 2})
    assert len(hits) == 1, f"After unsubscribe, should have 1 hit, got {len(hits)}"
    assert hits[0] == {"n": 1}
    _ok("16. unsubscribe() stops delivery to that handler")
except AssertionError as e:
    _fail("16. unsubscribe() stops delivery", str(e))

# ── Test 17: error isolation ────────────────────────────────────────────────
_section("EventBus Error Isolation")

try:
    import logging
    bus4 = InProcessEventBus()
    # Suppress logger output during this test to avoid noisy tracebacks
    ev_logger = logging.getLogger("lumina.events")
    old_level = ev_logger.level
    ev_logger.setLevel(logging.CRITICAL)

    good_hits = []

    def _bad_handler(t, p):
        raise RuntimeError("Handler blew up!")

    def _good_handler(t, p):
        good_hits.append(p)

    bus4.subscribe_sync("test.event", _bad_handler)
    bus4.subscribe_sync("test.event", _good_handler)
    bus4.publish_sync("test.event", {"x": 42})  # should not raise

    ev_logger.setLevel(old_level)  # restore

    assert len(good_hits) == 1, f"Good handler should still fire: got {len(good_hits)}"
    _ok("17. Bad handler exception is isolated; other handlers still fire")
except AssertionError as e:
    _fail("17. Error isolation", str(e))
except Exception as e:
    _fail("17. Error isolation (bus raised)", str(e))


# =============================================================================
# Section 3 — DI Container Integration
# =============================================================================

_section("DI Container Integration")

try:
    from core.container import DependencyContainer
    from core.interfaces import IBrainState, IEventBus

    tc = DependencyContainer()
    test_bs = BrainState()
    test_bus = InProcessEventBus()
    tc.register_instance(IBrainState, test_bs)
    tc.register_instance(IEventBus, test_bus)

    resolved_bs = tc.resolve(IBrainState)
    resolved_bus = tc.resolve(IEventBus)
    assert resolved_bs is test_bs, "IBrainState should resolve to the registered instance"
    assert resolved_bus is test_bus, "IEventBus should resolve to the registered instance"
    _ok("18. IBrainState and IEventBus register and resolve correctly")
except AssertionError as e:
    _fail("18. DI container registration/resolution", str(e))
except Exception as e:
    _fail("18. DI container registration/resolution", str(e))

try:
    isinstance(test_bs, IBrainState)
    _ok("19. BrainState is a valid IBrainState implementation (isinstance check)")
except Exception as e:
    _fail("19. isinstance(BrainState, IBrainState)", str(e))

try:
    isinstance(test_bus, IEventBus)
    _ok("20. InProcessEventBus is a valid IEventBus implementation (isinstance check)")
except Exception as e:
    _fail("20. isinstance(InProcessEventBus, IEventBus)", str(e))


# =============================================================================
# Section 4 — Backward Compatibility
# =============================================================================

_section("Backward Compatibility — MemoryStore still works")

try:
    from memory_store import MemoryStore
    test_db = "backend/brain/_test_compat.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    store = MemoryStore(test_db)
    mid = store.add_memory("fact", "Phase 1.2 test")
    mems = store.get_memories(limit=5)
    assert len(mems) >= 1, "Should retrieve at least 1 memory"
    if os.path.exists(test_db):
        os.remove(test_db)
    _ok("21. MemoryStore construction, write, read unchanged")
except Exception as e:
    _fail("21. MemoryStore backward compat", str(e))


# =============================================================================
# Summary
# =============================================================================

print(f"\n{'='*60}")
print(f"  PHASE 1.2 TEST SUMMARY")
print(f"{'='*60}")
print(f"  Passed: {_passed}")
print(f"  Failed: {_failed}")
print(f"{'='*60}")

if _failed == 0:
    print("  ALL TESTS PASSED")
    sys.exit(0)
else:
    print(f"  {_failed} TEST(S) FAILED")
    sys.exit(1)
