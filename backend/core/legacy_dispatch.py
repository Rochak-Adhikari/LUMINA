"""
core/legacy_dispatch.py — Phase 5.4 Step 3 (Order 6): session dispatch closure

Builds the callable that LegacyToolExecutor binds to at session start. The
closure reproduces the legacy two-tier tool dispatch that lives inside
AudioLoop's Gemini tool loop, so a Brain-planned Task can execute through the
exact same handlers the voice path uses — without the Brain layer importing
server.py, lumina.py, or any agent.

This module is the sanctioned core-layer bridge between the cognitive layer
and the legacy registries. It lives in core/ (NOT brain/) precisely because
brain/* may not import the registries; the executor receives this closure as
an injected value, keeping brain/* free of legacy imports.

Dispatch contract (matches LegacyToolExecutor._dispatch):

    dispatch(provider_ref: str, params: dict) -> Any            (async)

Behavior, mirroring lumina.py's tool loop exactly:

  Permission gate (audio_loop.permissions.get(name)):
    True            → auto-run
    False           → deny (raise PermissionError → executor → failed result)
    absent / other  → requires confirmation. Phase 5.4 REFUSES here instead
                      of driving the confirmation futures map, so the Brain
                      path never touches _pending_confirmations (invariant 8).
                      Browser tools auto-confirm when not in strict mode,
                      matching the legacy auto-confirm rule.

  Liveness (D7): if the bound session is gone (reconnect/teardown), refuse —
    a stale loop must not mutate a dead Gemini session.

  Dispatch (two-tier, order preserved):
    tier 1  ToolDispatcherRegistry.contains(name) → await handler(fc, loop)
    tier 2  name in ACTION_REGISTRY               → await to_thread(fn, dict,
                                                     None, None, memory_store)
    else                                          → raise KeyError (unknown)

The `fc` handed to tier-1 handlers is a SimpleNamespace(id, name, args) — the
same synthetic-function-call shape the legacy browser-reroute already builds.
"""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, Dict

from core.registry import ToolDispatcherRegistry

# Browser tools follow the legacy auto-confirm-unless-strict rule.
_BROWSER_TOOLS = ("browser_control", "local_browser_control")


class ToolDenied(Exception):
    """Permission gate denied the tool (explicitly disabled)."""


class ToolNeedsConfirmation(Exception):
    """Tool would require user confirmation; the Brain path refuses it in 5.4."""


class SessionGone(Exception):
    """The bound session is no longer live (D7 stale-loop guard)."""


def build_session_dispatch(audio_loop: Any) -> Callable[[str, Dict[str, Any]], Awaitable[Any]]:
    """
    Build an async dispatch closure bound to *audio_loop*.

    The returned callable reproduces the legacy two-tier dispatch and the
    permission gate. It is bound into LegacyToolExecutor at session start
    (Step 6) and cleared at session end.
    """
    # Imported lazily: ACTION_REGISTRY is a live dict view; importing here (not
    # at module import) keeps this bridge from pulling the actions package
    # unless a session actually binds a dispatch.
    from actions import ACTION_REGISTRY

    bound_session = getattr(audio_loop, "session", None)

    async def dispatch(provider_ref: str, params: Dict[str, Any]) -> Any:
        name = provider_ref

        # ---- Liveness guard (D7) --------------------------------------
        current = getattr(audio_loop, "session", None)
        if current is None or current is not bound_session:
            raise SessionGone(
                f"Session for tool '{name}' is no longer live; refusing dispatch."
            )

        # ---- Permission gate (parity with lumina.py) ------------------
        perms = getattr(audio_loop, "permissions", {}) or {}
        perm_value = perms.get(name, None)
        if perm_value is False:
            raise ToolDenied(f"Tool '{name}' is disabled in permissions.")

        explicitly_enabled = (perm_value is True)
        is_browser = name in _BROWSER_TOOLS
        auto_confirm_browser = getattr(
            audio_loop, "_browser_confirmation_mode", "strict") != "strict"

        if not explicitly_enabled and not (is_browser and auto_confirm_browser):
            # Would require a confirmation dialog. The Brain path does not own
            # the confirmation futures map, so it refuses rather than prompts.
            raise ToolNeedsConfirmation(
                f"Tool '{name}' requires user confirmation; not runnable via "
                f"the Brain path in Phase 5.4."
            )

        # ---- Two-tier dispatch (order + conventions preserved) --------
        fc = SimpleNamespace(id=uuid.uuid4().hex, name=name, args=dict(params))

        if ToolDispatcherRegistry.contains(name):
            handler = ToolDispatcherRegistry.get(name)
            return await handler(fc, audio_loop)

        if name in ACTION_REGISTRY:
            action_fn = ACTION_REGISTRY[name]
            return await asyncio.to_thread(
                action_fn,
                dict(params),
                None,                          # response arg (unused in Lumina)
                None,                          # player arg (unused in Lumina)
                getattr(audio_loop, "memory_store", None),
            )

        raise KeyError(f"Unknown tool '{name}' — not in any legacy registry.")

    return dispatch
