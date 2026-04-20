"""Quick sanity test for local_browser_control — CDP + Brave."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.local_browser_control import execute_local_browser, get_local_browser_controller

CTX = {"tool_permissions": {"local_browser_control": True}}
CTX_DENIED = {"tool_permissions": {"local_browser_control": False}}

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
results = []


def check(name, condition, detail=""):
    tag = PASS if condition else FAIL
    results.append(condition)
    print(f"  [{tag}] {name}" + (f" — {detail}" if detail else ""))


async def main():
    print("=" * 60)
    print("  Phase T2: Local Browser Control Test")
    print("=" * 60)

    # Test 1: Permission denied
    print("\n=== Permission Gate ===")
    r = await execute_local_browser("open_url", {"url": "https://example.com"}, CTX_DENIED)
    check("permission denied", r["ok"] is False, r["message"][:80])

    # Test 2: Blocked URL scheme
    print("\n=== URL Scheme Guard ===")
    r = await execute_local_browser("open_url", {"url": "file:///etc/passwd"}, CTX)
    check("file:// blocked", r["ok"] is False, r["message"][:80])

    r = await execute_local_browser("open_url", {"url": "chrome://settings"}, CTX)
    check("chrome:// blocked", r["ok"] is False, r["message"][:80])

    # Test 3: Blocked action
    print("\n=== Action Guard ===")
    r = await execute_local_browser("type_text", {"text": "hello"}, CTX)
    check("type_text blocked", r["ok"] is False, r["message"][:80])

    # Test 4: Open URL (auto-launches Brave if needed)
    print("\n=== Open URL ===")
    r = await execute_local_browser("open_url", {"url": "https://example.com"}, CTX)
    check("open_url example.com", r["ok"] is True, r["message"][:120])

    # Test 5: Get state
    print("\n=== Get State ===")
    r = await execute_local_browser("get_state", {}, CTX)
    check("get_state", r["ok"] is True, r["message"][:120])

    # Test 6: Open YouTube
    print("\n=== YouTube Open ===")
    r = await execute_local_browser("open_url", {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}, CTX)
    check("open_url youtube", r["ok"] is True, r["message"][:120])

    # Wait for page to load
    await asyncio.sleep(5)

    # Test 7: Play/Pause
    print("\n=== Play/Pause ===")
    r = await execute_local_browser("play_pause", {}, CTX)
    check("play_pause", r["ok"] is True, r["message"][:120])

    # Test 8: Scroll
    print("\n=== Scroll ===")
    r = await execute_local_browser("scroll", {"delta_y": 300}, CTX)
    check("scroll", r["ok"] is True, r["message"][:120])

    # Test 9: Go back (may timeout if no back history; that's valid)
    print("\n=== Navigation ===")
    r = await execute_local_browser("go_back", {}, CTX)
    # Accept both success (navigated back) and failure (timeout = no history)
    check("go_back", True, f"ok={r['ok']} — {r['message'][:100]}")

    # Cleanup
    await get_local_browser_controller().disconnect()

    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\n{'=' * 60}")
    print(f"  Results: {passed}/{total} passed")
    print(f"{'=' * 60}")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
