"""
Phase T1: Browser Controller — Lumina integration layer.

Single entrypoint: ``execute_browser_intent(intent, params, context)``

Validates permissions, converts high-level intents into atomic BrowserAction
plans, runs OBSERVE → ACT → VERIFY loops, and returns structured results.
Lumina core never touches Playwright directly.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agents.browser_agent.agent import BrowserAgent
from agents.browser_agent.schemas import (
    ActionType,
    BrowserAction,
    BrowserActionResult,
    BrowserState,
    ControllerResponse,
)

# ---------------------------------------------------------------------------
# Supported high-level intents
# ---------------------------------------------------------------------------
SUPPORTED_INTENTS = {
    "open_url",
    "search_google",
    "click_text",
    "type_into_focused",
    "send_keys",
    "read_page_summary",
    "screenshot",
    "login_flow_placeholder",
}

# Max retries for observe-act-verify fallback
MAX_VERIFY_RETRIES = 2


# ---------------------------------------------------------------------------
# Controller singleton
# ---------------------------------------------------------------------------
class BrowserController:
    """Adapter between Lumina core and the BrowserAgent."""

    def __init__(self):
        self._agent = BrowserAgent()

    @property
    def agent(self) -> BrowserAgent:
        return self._agent

    # ------------------------------------------------------------------
    # Permission gate
    # ------------------------------------------------------------------
    @staticmethod
    def _check_permission(context: Dict[str, Any]) -> Optional[str]:
        """Return an error string if permission denied, else None."""
        tool_perms = context.get("tool_permissions", {})
        if not tool_perms.get("browser_control", False):
            return "Browser control is disabled. Enable it in settings to use this feature."
        return None

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------
    async def execute_browser_intent(
        self,
        intent: str,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> ControllerResponse:
        """
        Single entrypoint for Lumina tool calls.

        Parameters
        ----------
        intent : str
            One of SUPPORTED_INTENTS.
        params : dict
            Intent-specific parameters.
        context : dict
            Must include ``tool_permissions`` dict from SETTINGS.
        """
        # 1) Permission gate
        perm_err = self._check_permission(context)
        if perm_err:
            print(f"[BROWSER] Permission denied: {perm_err}")
            return ControllerResponse(ok=False, message=perm_err)

        # 2) Validate intent
        if intent not in SUPPORTED_INTENTS:
            return ControllerResponse(
                ok=False,
                message=f"Unknown browser intent: '{intent}'. Supported: {sorted(SUPPORTED_INTENTS)}",
            )

        # 3) Ensure agent is running
        if not self._agent.is_running:
            await self._agent.start()

        # 4) Dispatch to intent handler
        handler = getattr(self, f"_intent_{intent}", None)
        if not handler:
            return ControllerResponse(ok=False, message=f"Intent handler not implemented: {intent}")

        try:
            return await handler(params)
        except Exception as e:
            # Capture error screenshot
            ss = None
            if self._agent.is_running:
                ss_result = await self._agent.execute(BrowserAction(ActionType.SCREENSHOT))
                ss = ss_result.artifacts.get("screenshot")
            print(f"[BROWSER] Intent '{intent}' failed: {e}")
            return ControllerResponse(
                ok=False,
                message=f"Browser intent '{intent}' failed: {e}",
                screenshot=ss,
            )

    # ------------------------------------------------------------------
    # Observe → Act → Verify helper
    # ------------------------------------------------------------------
    async def _observe_act_verify(
        self,
        actions: List[BrowserAction],
        verify_fn=None,
        label: str = "step",
    ) -> ControllerResponse:
        """
        Execute a list of actions with optional verification after the last one.
        If verification fails, retry with the same actions up to MAX_VERIFY_RETRIES.
        Returns a ControllerResponse with step trace.
        """
        trace: List[Dict[str, Any]] = []
        last_result: Optional[BrowserActionResult] = None

        for action in actions:
            result = await self._agent.execute(action)
            trace.append({
                "action": action.action_type.value,
                "params": action.params,
                "ok": result.success,
                "error": result.error,
                "elapsed_ms": result.elapsed_ms,
                "url": result.state.url if result.state else "",
                "title": result.state.title if result.state else "",
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            last_result = result
            if not result.success:
                ss = result.artifacts.get("screenshot")
                return ControllerResponse(
                    ok=False,
                    message=f"Action {action.action_type.value} failed: {result.error}",
                    screenshot=ss,
                    step_trace=trace,
                )

        # Verify
        if verify_fn and last_result:
            for attempt in range(MAX_VERIFY_RETRIES + 1):
                verified, reason = await verify_fn(last_result)
                trace.append({
                    "verify_attempt": attempt,
                    "verified": verified,
                    "reason": reason,
                    "ts": datetime.now(timezone.utc).isoformat(),
                })
                print(f"[BROWSER] verify={verified} outcome={reason}")
                if verified:
                    break
                if attempt < MAX_VERIFY_RETRIES:
                    # Wait briefly and retry last action
                    await asyncio.sleep(0.5)
                    last_result = await self._agent.execute(actions[-1])
                    trace.append({
                        "action": actions[-1].action_type.value + " (retry)",
                        "ok": last_result.success,
                        "ts": datetime.now(timezone.utc).isoformat(),
                    })
            else:
                ss_r = await self._agent.execute(BrowserAction(ActionType.SCREENSHOT))
                return ControllerResponse(
                    ok=False,
                    message=f"Verification failed after {MAX_VERIFY_RETRIES} retries: {reason}",
                    screenshot=ss_r.artifacts.get("screenshot"),
                    step_trace=trace,
                )

        # Success
        ss_path = None
        if last_result and last_result.artifacts.get("screenshot"):
            ss_path = last_result.artifacts["screenshot"]
        state_data = {}
        if last_result and last_result.state:
            state_data = {
                "url": last_result.state.url,
                "title": last_result.state.title,
                "tab_count": last_result.state.tab_count,
            }
        return ControllerResponse(
            ok=True,
            message="OK",
            data={**state_data, **last_result.data} if last_result else state_data,
            screenshot=ss_path,
            step_trace=trace,
        )

    # ==================================================================
    # Intent handlers
    # ==================================================================

    async def _intent_open_url(self, params: Dict[str, Any]) -> ControllerResponse:
        url = params.get("url", "")
        if not url:
            return ControllerResponse(ok=False, message="'url' parameter is required")

        actions = [BrowserAction(ActionType.OPEN_URL, {"url": url})]

        async def verify(result: BrowserActionResult):
            state = await self._agent.get_state()
            if state.url and state.url != "about:blank":
                return True, f"Navigated to {state.url}"
            return False, "Page did not load"

        resp = await self._observe_act_verify(actions, verify_fn=verify, label="open_url")
        # Append a screenshot
        if resp.ok:
            ss = await self._agent.execute(BrowserAction(ActionType.SCREENSHOT))
            if ss.artifacts.get("screenshot"):
                resp.screenshot = ss.artifacts["screenshot"]
        return resp

    async def _intent_search_google(self, params: Dict[str, Any]) -> ControllerResponse:
        query = params.get("query", "")
        if not query:
            return ControllerResponse(ok=False, message="'query' parameter is required")

        # Step 1: Navigate to Google
        nav = await self._agent.execute(
            BrowserAction(ActionType.OPEN_URL, {"url": "https://www.google.com"})
        )
        if not nav.success:
            return ControllerResponse(ok=False, message=f"Could not open Google: {nav.error}")

        # Step 2: Type query into search box
        # Use Playwright's fill on the known Google search input
        await asyncio.sleep(0.5)
        type_result = await self._agent.execute(
            BrowserAction(ActionType.CLICK, {"selector": 'textarea[name="q"], input[name="q"]'})
        )
        if not type_result.success:
            return ControllerResponse(ok=False, message=f"Could not find search box: {type_result.error}")

        await self._agent.execute(BrowserAction(ActionType.TYPE, {"text": query}))

        # Step 3: Press Enter
        await self._agent.execute(BrowserAction(ActionType.PRESS, {"key": "Enter"}))
        await asyncio.sleep(1.0)

        # Verify: URL should contain /search
        state = await self._agent.get_state()
        ss = await self._agent.execute(BrowserAction(ActionType.SCREENSHOT))

        if "search" in state.url.lower() or "q=" in state.url.lower():
            return ControllerResponse(
                ok=True,
                message=f"Searched Google for: {query}",
                data={"url": state.url, "title": state.title},
                screenshot=ss.artifacts.get("screenshot"),
            )
        return ControllerResponse(
            ok=False,
            message="Search verification failed — URL does not look like results page",
            data={"url": state.url},
            screenshot=ss.artifacts.get("screenshot"),
        )

    async def _intent_click_text(self, params: Dict[str, Any]) -> ControllerResponse:
        text = params.get("text", "")
        if not text:
            return ControllerResponse(ok=False, message="'text' parameter is required")

        # Observe before
        before_state = await self._agent.get_state()

        actions = [BrowserAction(ActionType.CLICK, {"text": text})]

        async def verify(result: BrowserActionResult):
            after = await self._agent.get_state()
            changed = (
                after.url != before_state.url
                or after.title != before_state.title
            )
            if changed:
                return True, f"Page changed after clicking '{text}'"
            # Even if URL/title didn't change, the click succeeded (DOM may have changed)
            return True, f"Click executed on '{text}' (no navigation detected)"

        return await self._observe_act_verify(actions, verify_fn=verify, label="click_text")

    async def _intent_type_into_focused(self, params: Dict[str, Any]) -> ControllerResponse:
        text = params.get("text", "")
        if not text:
            return ControllerResponse(ok=False, message="'text' parameter is required")
        actions = [BrowserAction(ActionType.TYPE, {"text": text})]
        return await self._observe_act_verify(actions, label="type_into_focused")

    async def _intent_send_keys(self, params: Dict[str, Any]) -> ControllerResponse:
        keys = params.get("keys", "")
        if not keys:
            return ControllerResponse(ok=False, message="'keys' parameter is required")
        actions = [BrowserAction(ActionType.PRESS, {"key": keys})]
        return await self._observe_act_verify(actions, label="send_keys")

    async def _intent_read_page_summary(self, params: Dict[str, Any]) -> ControllerResponse:
        dom_result = await self._agent.execute(
            BrowserAction(ActionType.DOM_SNAPSHOT, {"max_length": params.get("max_length", 4000)})
        )
        if not dom_result.success:
            return ControllerResponse(ok=False, message=f"DOM snapshot failed: {dom_result.error}")
        state = await self._agent.get_state()
        return ControllerResponse(
            ok=True,
            message="Page summary retrieved",
            data={
                "url": state.url,
                "title": state.title,
                "dom_text": dom_result.data.get("dom_text", ""),
                "text_length": dom_result.data.get("length", 0),
                "truncated": dom_result.data.get("truncated", False),
            },
        )

    async def _intent_screenshot(self, params: Dict[str, Any]) -> ControllerResponse:
        ss = await self._agent.execute(BrowserAction(ActionType.SCREENSHOT))
        if not ss.success:
            return ControllerResponse(ok=False, message=f"Screenshot failed: {ss.error}")
        state = await self._agent.get_state()
        return ControllerResponse(
            ok=True,
            message="Screenshot captured",
            data={"url": state.url, "title": state.title},
            screenshot=ss.artifacts.get("screenshot"),
        )

    async def _intent_login_flow_placeholder(self, params: Dict[str, Any]) -> ControllerResponse:
        site = params.get("site", "")
        if not site:
            return ControllerResponse(ok=False, message="'site' parameter is required")

        url = site if site.startswith("http") else f"https://{site}"
        nav = await self._agent.execute(BrowserAction(ActionType.OPEN_URL, {"url": url}))
        if not nav.success:
            return ControllerResponse(ok=False, message=f"Could not navigate to {url}: {nav.error}")

        await asyncio.sleep(1.0)
        ss = await self._agent.execute(BrowserAction(ActionType.SCREENSHOT))
        state = await self._agent.get_state()

        return ControllerResponse(
            ok=True,
            message=f"Navigated to login page for {site}. Please take over and complete login manually. I won't store any passwords.",
            data={"url": state.url, "title": state.title},
            screenshot=ss.artifacts.get("screenshot"),
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    async def shutdown(self):
        await self._agent.stop()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_controller: Optional[BrowserController] = None


def get_browser_controller() -> BrowserController:
    global _controller
    if _controller is None:
        _controller = BrowserController()
    return _controller


async def execute_browser_intent(
    intent: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Module-level convenience function — the ONLY function Lumina core calls.

    Returns a plain dict suitable for JSON serialization.
    """
    ctrl = get_browser_controller()
    resp = await ctrl.execute_browser_intent(intent, params, context)
    return resp.to_dict()
