"""
tests/test_port_recovery.py — Milestone 4.1 regression tests

Verifies the graceful port-recovery helpers added to server.py:
  - is_port_free(host, port)
  - select_startup_port(host)

Behavior contract:
  - Port 8000 is used unchanged whenever it is free (preserves the existing
    frontend/Electron contract).
  - Only when 8000 is occupied does selection scan forward to 8001–8009.
  - When the entire range is occupied, an OSError is raised (explicit failure
    instead of a silent uvicorn bind crash).

Written with stdlib unittest (not pytest) so it runs under the project's
lumina conda env, which does not currently ship pytest. Run with:

    python -m unittest backend.tests.test_port_recovery -v
"""

import os
import socket
import sys
import unittest

# Allow "import server" when run from the repo root or from backend/.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# server.py enforces a conda-env gate at import time; satisfy it for the test
# process without requiring an activated shell environment.
os.environ.setdefault("CONDA_DEFAULT_ENV", r"E:\AI\conda_envs\lumina")

import server  # noqa: E402

HOST = "127.0.0.1"


def _occupy(port):
    """Bind and listen on (HOST, port); caller must close the returned socket.

    No SO_REUSEADDR: we want a genuinely held port so is_port_free() (which
    also omits SO_REUSEADDR) correctly reports it as occupied on Windows.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, port))
    s.listen(1)
    return s


class TestPortRecovery(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(server.PORT_PRIMARY, 8000)
        self.assertEqual(server.PORT_SCAN_END, 8009)

    def test_is_port_free_true_when_unbound(self):
        # Find an ephemeral free port, close it, then assert it reads as free.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((HOST, 0))
        free_port = s.getsockname()[1]
        s.close()
        self.assertTrue(server.is_port_free(HOST, free_port))

    def test_is_port_free_false_when_bound(self):
        s = _occupy(0)
        port = s.getsockname()[1]
        try:
            self.assertFalse(server.is_port_free(HOST, port))
        finally:
            s.close()

    def test_selects_primary_when_free(self):
        # Only meaningful if 8000 is actually free in this environment.
        if not server.is_port_free(HOST, 8000):
            self.skipTest("Port 8000 already occupied in this environment")
        self.assertEqual(server.select_startup_port(HOST), 8000)

    def test_recovers_to_fallback_when_primary_busy(self):
        if not server.is_port_free(HOST, 8000):
            self.skipTest("Port 8000 already occupied in this environment")
        holder = _occupy(8000)
        try:
            selected = server.select_startup_port(HOST)
            self.assertNotEqual(selected, 8000)
            self.assertGreaterEqual(selected, 8001)
            self.assertLessEqual(selected, server.PORT_SCAN_END)
        finally:
            holder.close()

    def test_raises_when_entire_range_occupied(self):
        holders = []
        try:
            for port in range(8000, server.PORT_SCAN_END + 1):
                if server.is_port_free(HOST, port):
                    holders.append(_occupy(port))
            # If we could not occupy the whole range (something external holds
            # one), the scenario is untestable here — skip rather than falsely
            # pass/fail.
            if any(server.is_port_free(HOST, p) for p in range(8000, server.PORT_SCAN_END + 1)):
                self.skipTest("Could not occupy the full 8000–8009 range")
            with self.assertRaises(OSError):
                server.select_startup_port(HOST)
        finally:
            for h in holders:
                h.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
