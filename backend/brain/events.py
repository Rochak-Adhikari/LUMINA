"""
brain/events.py — Lumina V2 InProcessEventBus

A lightweight, zero-dependency, in-process publish/subscribe event bus.

Design principles
─────────────────
1. LOCAL ONLY
   In-memory pub/sub.  No networking, no Redis, no RabbitMQ, no asyncio
   message broker.  All handlers run in the calling thread/coroutine.

2. SATISFIES IEventBus CONTRACT
   Implements the abstract interface defined in core/interfaces.py so
   the container can resolve IEventBus anywhere without knowing the
   concrete implementation.

3. WILDCARD TOPIC MATCHING
   Topic patterns use dot-separated segments.  A ``*`` segment matches
   any single segment.  A ``**`` suffix matches any remaining segments.

   Examples:
     "session.started"        — exact match
     "session.*"              — matches session.started, session.ended
     "tool.*.success"         — matches tool.generate_cad.success
     "memory.**"              — matches memory.write, memory.search.hit

4. SYNCHRONOUS DELIVERY
   Handlers are invoked synchronously in the publisher's thread.
   For asyncio coroutine handlers, the caller must be inside an async
   context (the bus will await them).  Non-async handlers are called
   directly.

5. THREAD SAFETY
   Subscription mutation (subscribe/unsubscribe) is protected by a
   threading.Lock.  Handler iteration takes a snapshot copy of the
   subscriber list before invoking — late unsubscribes during dispatch
   are safe (they take effect on the next publish call).

6. SUBSCRIPTION TOKEN
   subscribe() returns a SubscriptionToken (opaque UUID string).
   Pass that token to unsubscribe() to remove the handler.

7. ERROR ISOLATION
   If a handler raises an exception, it is logged and the bus continues
   delivering to the remaining subscribers.  One bad handler cannot
   break other handlers.

Lifecycle
─────────
  Created: at server startup via factory lambda in container
  Used:    publish/subscribe/unsubscribe at any point in the process
  Destroyed: process exit

Usage (synchronous context)::

    from brain.events import InProcessEventBus

    bus = InProcessEventBus()

    def on_session_start(topic: str, payload: dict) -> None:
        print(f"[EVENT] {topic}: {payload}")

    token = bus.subscribe_sync("session.*", on_session_start)
    bus.publish_sync("session.started", {"client_sid": "abc123"})
    bus.unsubscribe_sync(token)

Usage (async context)::

    token = await bus.subscribe("session.*", on_session_start)
    await bus.publish("session.started", {"client_sid": "abc123"})
    await bus.unsubscribe(token)
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.interfaces import IEventBus

logger = logging.getLogger("lumina.events")


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Topic = str
SubscriptionToken = str
Handler = Callable[[Topic, Dict], Any]


# ---------------------------------------------------------------------------
# Internal subscription record
# ---------------------------------------------------------------------------

class _Subscription:
    """Holds one registered handler and its token."""

    __slots__ = ("token", "pattern", "handler", "is_coro")

    def __init__(self, pattern: Topic, handler: Handler) -> None:
        self.token: SubscriptionToken = str(uuid.uuid4())
        self.pattern = pattern
        self.handler = handler
        self.is_coro = inspect.iscoroutinefunction(handler)


# ---------------------------------------------------------------------------
# Topic pattern matching
# ---------------------------------------------------------------------------

def _topic_matches(pattern: Topic, topic: Topic) -> bool:
    """
    Return True if *topic* matches *pattern*.

    Rules:
    - Segments are split by '.'.
    - A '*' segment matches any single segment.
    - '**' as the LAST segment of the pattern matches zero or more remaining
      segments.
    - Exact equality always matches.
    """
    if pattern == topic:
        return True

    p_parts = pattern.split(".")
    t_parts = topic.split(".")

    # Handle trailing '**' wildcard
    if p_parts[-1] == "**":
        # The prefix (everything before '**') must match
        prefix = p_parts[:-1]
        if len(t_parts) < len(prefix):
            return False
        return all(
            pp == tp or pp == "*"
            for pp, tp in zip(prefix, t_parts)
        )

    if len(p_parts) != len(t_parts):
        return False

    return all(
        pp == tp or pp == "*"
        for pp, tp in zip(p_parts, t_parts)
    )


# ---------------------------------------------------------------------------
# InProcessEventBus
# ---------------------------------------------------------------------------

class InProcessEventBus(IEventBus):
    """
    Concrete implementation of IEventBus.

    Registered in the DI container as IEventBus at server startup.
    Future phases may swap this for an external broker without touching
    any subscriber code.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # List of _Subscription objects — protected by self._lock
        self._subscriptions: List[_Subscription] = []
        # Token → _Subscription index for O(1) unsubscribe
        self._token_map: Dict[SubscriptionToken, _Subscription] = {}
        logger.info("[EventBus] InProcessEventBus initialized.")

    # ------------------------------------------------------------------
    # IEventBus async interface (satisfies ABC)
    # ------------------------------------------------------------------

    async def publish(
        self,
        topic: str,
        payload: Dict,
        priority: str = "MEDIUM",
    ) -> None:
        """
        Publish *payload* to all subscribers whose pattern matches *topic*.

        Async handlers are awaited; sync handlers are called directly.
        Exceptions from individual handlers are caught and logged so that
        a failing handler never breaks delivery to other subscribers.

        *priority* is stored for future use (e.g. priority queues).
        It has no effect on this in-process synchronous implementation.
        """
        await self._deliver(topic, payload)

    async def subscribe(self, topic: str, callback: Any) -> Any:
        """
        Register *callback* to receive events matching *topic*.
        Returns a SubscriptionToken that can be passed to unsubscribe().
        """
        return self._add_subscription(topic, callback)

    async def unsubscribe(self, token: Any) -> None:
        """Remove the subscription identified by *token*."""
        self._remove_subscription(token)

    # ------------------------------------------------------------------
    # Synchronous convenience API (for use outside async contexts)
    # ------------------------------------------------------------------

    def publish_sync(self, topic: str, payload: Dict, priority: str = "MEDIUM") -> None:
        """
        Synchronous version of publish().

        Calls sync handlers directly.  Skips async (coroutine) handlers —
        use asyncio.run() or publish() from an async context for those.
        """
        self._deliver_sync(topic, payload)

    def subscribe_sync(self, topic: str, callback: Handler) -> SubscriptionToken:
        """Synchronous version of subscribe(). Returns subscription token."""
        return self._add_subscription(topic, callback)

    def unsubscribe_sync(self, token: SubscriptionToken) -> None:
        """Synchronous version of unsubscribe()."""
        self._remove_subscription(token)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a snapshot of the current subscription table."""
        with self._lock:
            subs = [
                {"token": s.token[:8] + "…", "pattern": s.pattern, "is_coro": s.is_coro}
                for s in self._subscriptions
            ]
        return {"subscription_count": len(subs), "subscriptions": subs}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_subscription(self, pattern: Topic, handler: Handler) -> SubscriptionToken:
        sub = _Subscription(pattern, handler)
        with self._lock:
            self._subscriptions.append(sub)
            self._token_map[sub.token] = sub
        logger.debug("[EventBus] Subscribed token=%s pattern='%s'", sub.token[:8], pattern)
        return sub.token

    def _remove_subscription(self, token: SubscriptionToken) -> None:
        with self._lock:
            sub = self._token_map.pop(token, None)
            if sub is not None:
                try:
                    self._subscriptions.remove(sub)
                    logger.debug("[EventBus] Unsubscribed token=%s", token[:8])
                except ValueError:
                    pass  # Already removed — safe to ignore
            else:
                logger.warning("[EventBus] unsubscribe: unknown token %s", token)

    def _matching_subscriptions(self, topic: Topic) -> List[_Subscription]:
        """Return a snapshot list of subscriptions matching *topic*."""
        with self._lock:
            return [s for s in self._subscriptions if _topic_matches(s.pattern, topic)]

    async def _deliver(self, topic: Topic, payload: Dict) -> None:
        """Deliver to all matching subscribers, async-aware."""
        matching = self._matching_subscriptions(topic)
        for sub in matching:
            try:
                if sub.is_coro:
                    await sub.handler(topic, payload)
                else:
                    sub.handler(topic, payload)
            except Exception as exc:
                logger.exception(
                    "[EventBus] Handler error for topic='%s' pattern='%s': %s",
                    topic, sub.pattern, exc,
                )

    def _deliver_sync(self, topic: Topic, payload: Dict) -> None:
        """Deliver to all matching sync-only subscribers."""
        matching = self._matching_subscriptions(topic)
        for sub in matching:
            if sub.is_coro:
                logger.warning(
                    "[EventBus] Skipping async handler for topic='%s' in sync deliver.",
                    topic,
                )
                continue
            try:
                sub.handler(topic, payload)
            except Exception as exc:
                logger.exception(
                    "[EventBus] Sync handler error for topic='%s': %s", topic, exc
                )
