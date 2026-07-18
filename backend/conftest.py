"""
backend/conftest.py — root pytest configuration (Phase 5.4 Order 5).

Centralizes two things every phase test previously did by hand:

  1. Put backend/ on sys.path so `import core`, `import brain`, etc. resolve
     regardless of which directory (tests/, core/, brain/) a test lives in.
  2. Install the Gemini SDK mock into sys.modules BEFORE any test imports
     `core` (which, until Order 4, transitively imported google.genai; the
     mock is retained as defence-in-depth for optional heavy deps).

This runs at collection time, before test modules are imported, so the
per-file `sys.modules.setdefault('google', ...)` guards in the phase tests
become redundant (they remain harmless — setdefault is idempotent).

This file complements tests/conftest.py (device fixtures); it does not
replace it.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

BACKEND_DIR = Path(__file__).parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Mock heavy/optional SDKs before any `core` import during collection.
for _mod in ("google", "google.genai", "google.genai.types"):
    sys.modules.setdefault(_mod, MagicMock())
