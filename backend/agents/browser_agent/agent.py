"""
Phase T1: Browser Agent — Playwright runtime.

Owns a single persistent Chromium context. Exposes atomic actions only.
No LLM logic here — this is pure "hands + eyes".
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .schemas import (
    ActionType,
    BrowserAction,
    BrowserActionResult,
    BrowserState,
)

# ---------------------------------------------------------------------------
# Config (env-driven)
# ---------------------------------------------------------------------------
BROWSER_HEADLESS = os.environ.get("BROWSER_HEADLESS", "true").lower() == "true"
BROWSER_SLOWMO_MS = int(os.environ.get("BROWSER_SLOWMO_MS", "0"))
BROWSER_DEFAULT_TIMEOUT_MS = int(os.environ.get("BROWSER_DEFAULT_TIMEOUT_MS", "15000"))

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent.parent / "artifacts" / "browser"


# ---------------------------------------------------------------------------
# BrowserAgent
# ---------------------------------------------------------------------------
class BrowserAgent:
    """
    Persistent browser runtime.  Call ``start()`` before any actions,
    ``stop()`` when done.  All public action methods are async.
    """

    def __init__(self):
        self._pw = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._state = BrowserState()
        self._started = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def start(self) -> None:
        if self._started:
            print("[BROWSER] Already started — reusing context")
            return
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=BROWSER_HEADLESS,
            slow_mo=BROWSER_SLOWMO_MS,
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
        )
        self._context.set_default_timeout(BROWSER_DEFAULT_TIMEOUT_MS)
        self._page = await self._context.new_page()
        self._started = True
        self._refresh_state()
        print(f"[BROWSER] Started (headless={BROWSER_HEADLESS}, timeout={BROWSER_DEFAULT_TIMEOUT_MS}ms)")

    async def stop(self) -> None:
        if not self._started:
            return
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._pw:
                await self._pw.stop()
        except Exception as e:
            print(f"[BROWSER] Error during stop: {e}")
        finally:
            self._pw = None
            self._browser = None
            self._context = None
            self._page = None
            self._started = False
            self._state = BrowserState()
            print("[BROWSER] Stopped")

    @property
    def is_running(self) -> bool:
        return self._started

    # ------------------------------------------------------------------
    # State helper
    # ------------------------------------------------------------------
    def _refresh_state(self) -> BrowserState:
        if not self._page or self._page.is_closed():
            self._state = BrowserState()
            return self._state
        try:
            self._state = BrowserState(
                url=self._page.url,
                title=self._page.url,  # title needs await; we patch in _async_refresh
                tab_count=len(self._context.pages) if self._context else 0,
                active_tab_index=self._active_tab_index(),
                loading=False,
                last_action_ts=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            pass
        return self._state

    async def _async_refresh_state(self) -> BrowserState:
        if not self._page or self._page.is_closed():
            self._state = BrowserState()
            return self._state
        try:
            title = await self._page.title()
            self._state = BrowserState(
                url=self._page.url,
                title=title,
                tab_count=len(self._context.pages) if self._context else 0,
                active_tab_index=self._active_tab_index(),
                loading=False,
                last_action_ts=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            self._refresh_state()
        return self._state

    def _active_tab_index(self) -> int:
        if not self._context or not self._page:
            return 0
        pages = self._context.pages
        for i, p in enumerate(pages):
            if p == self._page:
                return i
        return 0

    # ------------------------------------------------------------------
    # Core action dispatcher
    # ------------------------------------------------------------------
    async def execute(self, action: BrowserAction) -> BrowserActionResult:
        if not self._started:
            return BrowserActionResult(
                success=False,
                action_type=action.action_type.value,
                error="Browser agent not started. Call start() first.",
            )
        t0 = time.monotonic()
        try:
            result = await self._dispatch(action)
            result.elapsed_ms = int((time.monotonic() - t0) * 1000)
            result.state = await self._async_refresh_state()
            print(
                f"[BROWSER] action={action.action_type.value} ok={result.success} "
                f"url={result.state.url[:80]} title={result.state.title[:60]}"
            )
            return result
        except Exception as e:
            elapsed = int((time.monotonic() - t0) * 1000)
            state = await self._async_refresh_state()
            # Capture failure screenshot
            ss_path = await self._take_screenshot("error")
            print(f"[BROWSER] action={action.action_type.value} FAILED: {e}")
            return BrowserActionResult(
                success=False,
                action_type=action.action_type.value,
                error=str(e),
                state=state,
                artifacts={"screenshot": str(ss_path)} if ss_path else {},
                elapsed_ms=elapsed,
            )

    async def _dispatch(self, action: BrowserAction) -> BrowserActionResult:
        at = action.action_type
        p = action.params

        if at == ActionType.OPEN_URL:
            return await self._open_url(p.get("url", ""))
        elif at == ActionType.CLICK:
            return await self._click(p.get("selector"), p.get("text"), p.get("x"), p.get("y"))
        elif at == ActionType.TYPE:
            return await self._type_text(p.get("text", ""))
        elif at == ActionType.PRESS:
            return await self._press_key(p.get("key", ""))
        elif at == ActionType.SCROLL:
            return await self._scroll(p.get("px", 300))
        elif at == ActionType.WAIT:
            return await self._wait(p.get("ms", 1000))
        elif at == ActionType.SCREENSHOT:
            return await self._screenshot()
        elif at == ActionType.DOM_SNAPSHOT:
            return await self._dom_snapshot(p.get("max_length", 4000))
        elif at == ActionType.NEW_TAB:
            return await self._new_tab(p.get("url"))
        elif at == ActionType.SWITCH_TAB:
            return await self._switch_tab(p.get("index", 0))
        elif at == ActionType.CLOSE_TAB:
            return await self._close_tab()
        else:
            return BrowserActionResult(
                success=False, action_type=at.value, error=f"Unknown action: {at.value}"
            )

    # ------------------------------------------------------------------
    # Atomic action implementations
    # ------------------------------------------------------------------
    async def _open_url(self, url: str) -> BrowserActionResult:
        if not url:
            return BrowserActionResult(success=False, action_type="open_url", error="url is required")
        await self._page.goto(url, wait_until="domcontentloaded")
        return BrowserActionResult(success=True, action_type="open_url")

    async def _click(
        self,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> BrowserActionResult:
        if text:
            # Preferred: use Playwright get_by_text (safe strategy)
            loc = self._page.get_by_text(text, exact=False).first
            await loc.wait_for(state="visible", timeout=BROWSER_DEFAULT_TIMEOUT_MS)
            await loc.click()
            return BrowserActionResult(success=True, action_type="click")
        elif selector:
            await self._page.click(selector, timeout=BROWSER_DEFAULT_TIMEOUT_MS)
            return BrowserActionResult(success=True, action_type="click")
        elif x is not None and y is not None:
            await self._page.mouse.click(x, y)
            return BrowserActionResult(success=True, action_type="click")
        return BrowserActionResult(success=False, action_type="click", error="Need text, selector, or x/y")

    async def _type_text(self, text: str) -> BrowserActionResult:
        if not text:
            return BrowserActionResult(success=False, action_type="type", error="text is required")
        await self._page.keyboard.type(text, delay=30)
        return BrowserActionResult(success=True, action_type="type")

    async def _press_key(self, key: str) -> BrowserActionResult:
        if not key:
            return BrowserActionResult(success=False, action_type="press", error="key is required")
        await self._page.keyboard.press(key)
        return BrowserActionResult(success=True, action_type="press")

    async def _scroll(self, px: int) -> BrowserActionResult:
        await self._page.mouse.wheel(0, px)
        await asyncio.sleep(0.3)
        return BrowserActionResult(success=True, action_type="scroll")

    async def _wait(self, ms: int) -> BrowserActionResult:
        ms = min(max(ms, 100), 30000)  # clamp 100ms–30s
        await asyncio.sleep(ms / 1000)
        return BrowserActionResult(success=True, action_type="wait")

    async def _screenshot(self, label: str = "step") -> BrowserActionResult:
        path = await self._take_screenshot(label)
        if path:
            return BrowserActionResult(
                success=True, action_type="screenshot",
                artifacts={"screenshot": str(path)},
            )
        return BrowserActionResult(success=False, action_type="screenshot", error="Screenshot failed")

    async def _dom_snapshot(self, max_length: int = 4000) -> BrowserActionResult:
        raw = await self._page.evaluate(
            """() => {
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT, null
                );
                let text = '';
                while (walker.nextNode()) {
                    const t = walker.currentNode.textContent.trim();
                    if (t) text += t + '\\n';
                }
                return text;
            }"""
        )
        truncated = (raw or "")[:max_length]
        return BrowserActionResult(
            success=True, action_type="dom_snapshot",
            data={"dom_text": truncated, "length": len(raw or ""), "truncated": len(raw or "") > max_length},
        )

    async def _new_tab(self, url: Optional[str] = None) -> BrowserActionResult:
        page = await self._context.new_page()
        self._page = page
        if url:
            await page.goto(url, wait_until="domcontentloaded")
        return BrowserActionResult(success=True, action_type="new_tab")

    async def _switch_tab(self, index: int) -> BrowserActionResult:
        pages = self._context.pages
        if 0 <= index < len(pages):
            self._page = pages[index]
            await self._page.bring_to_front()
            return BrowserActionResult(success=True, action_type="switch_tab")
        return BrowserActionResult(
            success=False, action_type="switch_tab",
            error=f"Tab index {index} out of range (0-{len(pages)-1})",
        )

    async def _close_tab(self) -> BrowserActionResult:
        if len(self._context.pages) <= 1:
            return BrowserActionResult(
                success=False, action_type="close_tab", error="Cannot close last tab"
            )
        await self._page.close()
        self._page = self._context.pages[-1]
        await self._page.bring_to_front()
        return BrowserActionResult(success=True, action_type="close_tab")

    # ------------------------------------------------------------------
    # Screenshot helper
    # ------------------------------------------------------------------
    async def _take_screenshot(self, label: str = "step") -> Optional[Path]:
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            path = ARTIFACTS_DIR / f"{label}_{ts}.png"
            ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
            await self._page.screenshot(path=str(path), full_page=False)
            return path
        except Exception as e:
            print(f"[BROWSER] Screenshot error: {e}")
            return None

    # ------------------------------------------------------------------
    # Convenience: get current state without action
    # ------------------------------------------------------------------
    async def get_state(self) -> BrowserState:
        return await self._async_refresh_state()
