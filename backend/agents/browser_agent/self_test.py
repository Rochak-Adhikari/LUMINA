"""
Phase T1: Browser Agent — Self-test script.

Usage:
    conda activate lumina
    python backend/agents/browser_agent/self_test.py

Tests:
    1) Start agent
    2) open_url("https://example.com")
    3) Screenshot captured
    4) DOM snapshot contains "Example Domain"
    5) Stop agent
    6) Controller permission gate (denied when browser_control=False)
    7) Controller permission gate (allowed when browser_control=True)
"""

import asyncio
import sys
import os

# Ensure backend/ is on path (self_test.py is in backend/agents/browser_agent/)
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _backend_dir)

from agents.browser_agent.agent import BrowserAgent
from agents.browser_agent.schemas import ActionType, BrowserAction
from tools.browser_control import execute_browser_intent


PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
results = []


def report(name: str, ok: bool, detail: str = ""):
    tag = PASS if ok else FAIL
    results.append((name, ok))
    print(f"  [{tag}] {name}" + (f" — {detail}" if detail else ""))


async def test_agent_direct():
    """Test the BrowserAgent directly (unit-ish)."""
    print("\n=== BrowserAgent Direct Tests ===")
    agent = BrowserAgent()

    # T1: Start
    await agent.start()
    report("start()", agent.is_running)

    # T2: open_url
    r = await agent.execute(BrowserAction(ActionType.OPEN_URL, {"url": "https://example.com"}))
    report("open_url(example.com)", r.success, f"url={r.state.url if r.state else '?'}")

    # T3: screenshot
    r = await agent.execute(BrowserAction(ActionType.SCREENSHOT))
    ss_path = r.artifacts.get("screenshot", "")
    report("screenshot()", r.success and bool(ss_path), f"path={ss_path}")

    # T4: dom_snapshot contains "Example Domain"
    r = await agent.execute(BrowserAction(ActionType.DOM_SNAPSHOT))
    dom_text = r.data.get("dom_text", "")
    has_domain = "Example Domain" in dom_text
    report("dom_snapshot contains 'Example Domain'", r.success and has_domain,
           f"length={len(dom_text)}, found={'yes' if has_domain else 'NO'}")

    # T5: get_state
    state = await agent.get_state()
    report("get_state()", state.url != "", f"url={state.url}, title={state.title}")

    # T6: stop
    await agent.stop()
    report("stop()", not agent.is_running)


async def test_controller_permission_gate():
    """Test controller permission gating."""
    print("\n=== Controller Permission Gate Tests ===")

    # T7: Denied when browser_control = False
    resp = await execute_browser_intent(
        intent="open_url",
        params={"url": "https://example.com"},
        context={"tool_permissions": {"browser_control": False}},
    )
    report(
        "permission denied (browser_control=False)",
        resp["ok"] is False and "disabled" in resp["message"].lower(),
        resp["message"][:80],
    )

    # T8: Allowed when browser_control = True
    resp = await execute_browser_intent(
        intent="open_url",
        params={"url": "https://example.com"},
        context={"tool_permissions": {"browser_control": True}},
    )
    report(
        "permission allowed (browser_control=True)",
        resp["ok"] is True,
        resp.get("data", {}).get("url", "?")[:80],
    )

    # Cleanup
    from tools.browser_control import get_browser_controller
    await get_browser_controller().shutdown()


async def test_search_google():
    """Test search_google intent (stable state, no duplicate contexts)."""
    print("\n=== Search Google Intent Test ===")

    resp = await execute_browser_intent(
        intent="search_google",
        params={"query": "Playwright Python testing"},
        context={"tool_permissions": {"browser_control": True}},
    )
    report(
        "search_google",
        resp["ok"] is True,
        resp.get("data", {}).get("url", "?")[:80],
    )

    # Run again — should reuse existing context, not spawn a new one
    resp2 = await execute_browser_intent(
        intent="search_google",
        params={"query": "asyncio Python"},
        context={"tool_permissions": {"browser_control": True}},
    )
    report(
        "search_google (2nd, reuse context)",
        resp2["ok"] is True,
        resp2.get("data", {}).get("url", "?")[:80],
    )

    from tools.browser_control import get_browser_controller
    await get_browser_controller().shutdown()


async def main():
    print("=" * 60)
    print("  Phase T1: Browser Agent Self-Test")
    print("=" * 60)

    await test_agent_direct()
    await test_controller_permission_gate()
    await test_search_google()

    # Summary
    print("\n" + "=" * 60)
    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    failed = total - passed
    print(f"  Results: {passed}/{total} passed" + (f", {failed} FAILED" if failed else ""))
    print("=" * 60)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
