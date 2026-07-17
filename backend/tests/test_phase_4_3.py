"""
tests/test_phase_4_3.py — Milestone 4.3 regression tests

Verifies SessionManager ownership of the runtime session state that was
previously held in server.py module globals:

  - audio_loop   (attach/detach lifecycle, pre-existing)
  - loop_task    (new in 4.3: set_loop_task / loop_task)
  - authenticator (new in 4.3: set_authenticator / authenticator)
  - get_status() reflecting the new ownership fields

No real audio, network, database, or Gemini APIs are invoked — dummy
sentinel objects and no-op fakes are used throughout.

Run:
    python -m unittest backend.tests.test_phase_4_3 -v
"""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.session import SessionManager


class _FakeBrainState:
    """Minimal IBrainState stand-in: transaction() ctx manager + reset."""
    def transaction(self):
        class _Ctx:
            def __enter__(self_inner):
                class _Draft: pass
                return _Draft()
            def __exit__(self_inner, *a):
                return False
        return _Ctx()

    def reset_session(self):
        pass


class _FakeEventBus:
    """Minimal IEventBus stand-in: records published topics."""
    def __init__(self):
        self.published = []

    def publish_sync(self, topic, payload):
        self.published.append(topic)


class TestSessionManagerOwnership(unittest.TestCase):
    def setUp(self):
        self.bus = _FakeEventBus()
        self.sm = SessionManager(brain_state=_FakeBrainState(), event_bus=self.bus)

    def test_owns_audio_loop(self):
        loop = object()
        self.assertIsNone(self.sm.audio_loop)
        self.sm.attach(loop)
        self.assertIs(self.sm.audio_loop, loop)
        self.assertTrue(self.sm.is_active)

    def test_owns_loop_task(self):
        task = object()
        self.assertIsNone(self.sm.loop_task)
        self.sm.set_loop_task(task)
        self.assertIs(self.sm.loop_task, task)
        self.sm.set_loop_task(None)
        self.assertIsNone(self.sm.loop_task)

    def test_owns_authenticator(self):
        auth = object()
        self.assertIsNone(self.sm.authenticator)
        self.sm.set_authenticator(auth)
        self.assertIs(self.sm.authenticator, auth)
        self.sm.set_authenticator(None)
        self.assertIsNone(self.sm.authenticator)

    def test_attach_detach_lifecycle(self):
        loop = object()
        self.sm.attach(loop)
        self.assertTrue(self.sm.is_active)
        self.assertIn("session.audio_attached", self.bus.published)
        self.sm.detach()
        self.assertFalse(self.sm.is_active)
        self.assertIsNone(self.sm.audio_loop)
        self.assertIn("session.audio_detached", self.bus.published)

    def test_detach_does_not_cancel_or_clear_loop_task(self):
        # 4.3 contract: cancellation/clearing of the task is an explicit
        # caller decision (shutdown path), detach only clears audio_loop.
        task = object()
        self.sm.attach(object())
        self.sm.set_loop_task(task)
        self.sm.detach()
        self.assertIs(self.sm.loop_task, task)

    def test_get_status_reflects_ownership(self):
        status = self.sm.get_status()
        self.assertFalse(status["has_loop_task"])
        self.assertFalse(status["has_authenticator"])
        self.sm.attach(object())
        self.sm.set_loop_task(object())
        self.sm.set_authenticator(object())
        status = self.sm.get_status()
        self.assertTrue(status["is_active"])
        self.assertTrue(status["has_loop_task"])
        self.assertTrue(status["has_authenticator"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
