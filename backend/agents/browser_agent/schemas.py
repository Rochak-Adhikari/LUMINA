"""
Phase T1: Browser Agent — Action & State schemas (Pydantic).

Defines the strict contract between Browser Controller and Browser Agent.
No free-form JS execution. Every action is typed and validated.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Action enum — every allowed atomic browser operation
# ---------------------------------------------------------------------------
class ActionType(str, enum.Enum):
    OPEN_URL = "open_url"
    CLICK = "click"
    TYPE = "type"
    PRESS = "press"
    SCROLL = "scroll"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    DOM_SNAPSHOT = "dom_snapshot"
    SWITCH_TAB = "switch_tab"
    NEW_TAB = "new_tab"
    CLOSE_TAB = "close_tab"


# ---------------------------------------------------------------------------
# BrowserAction — a single atomic instruction
# ---------------------------------------------------------------------------
@dataclass
class BrowserAction:
    action_type: ActionType
    # Flexible params dict; validated per action_type by the agent before exec.
    params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.action_type, str):
            self.action_type = ActionType(self.action_type)


# ---------------------------------------------------------------------------
# BrowserState — snapshot of the browser at a point in time
# ---------------------------------------------------------------------------
@dataclass
class BrowserState:
    url: str = ""
    title: str = ""
    tab_count: int = 0
    active_tab_index: int = 0
    loading: bool = False
    last_action_ts: Optional[str] = None  # ISO timestamp


# ---------------------------------------------------------------------------
# BrowserActionResult — returned after every atomic action
# ---------------------------------------------------------------------------
@dataclass
class BrowserActionResult:
    success: bool
    action_type: str
    error: Optional[str] = None
    state: Optional[BrowserState] = None
    artifacts: Dict[str, str] = field(default_factory=dict)  # e.g. {"screenshot": "/path/to/file.png"}
    data: Dict[str, Any] = field(default_factory=dict)       # e.g. {"dom_text": "..."}
    elapsed_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action_type": self.action_type,
            "error": self.error,
            "state": {
                "url": self.state.url,
                "title": self.state.title,
                "tab_count": self.state.tab_count,
                "loading": self.state.loading,
            } if self.state else None,
            "artifacts": self.artifacts,
            "data": self.data,
            "elapsed_ms": self.elapsed_ms,
        }


# ---------------------------------------------------------------------------
# ControllerResponse — returned to Lumina core from the controller
# ---------------------------------------------------------------------------
@dataclass
class ControllerResponse:
    ok: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    screenshot: Optional[str] = None  # path
    step_trace: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "message": self.message,
            "data": self.data,
            "screenshot": self.screenshot,
            "step_trace": self.step_trace,
        }
