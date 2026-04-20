"""
Action Router — Deterministic NL parser for Quests, Events, and Archive Notes.

Converts natural language chat messages into structured CRUD actions that match
the existing panel socket event data models exactly. No LLM dependency.

Returns result_meta dicts (no user-facing text). The server formats replies.

Usage:
    from action_router import ActionRouter
    router = ActionRouter(memory_store)
    result = router.parse(text, last_ids={"quest": 5, "event": 3, "note": 7})
    # result is None (no action) or a dict with {action, panel, data, meta}
"""

import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Optional, Dict, List


# ============================================================
# Datetime resolution helpers
# ============================================================

_DAY_NAMES = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
}

_TIME_RE = re.compile(
    r'(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?',
    re.IGNORECASE
)

_RELATIVE_DAY_RE = re.compile(
    r'\b(today|tonight|tomorrow|day after tomorrow)\b',
    re.IGNORECASE
)

_NEXT_DAY_RE = re.compile(
    r'\b(?:next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)\b',
    re.IGNORECASE
)

_IN_DURATION_RE = re.compile(
    r'\bin\s+(\d+)\s*(hour|hr|minute|min|second|sec)s?\b',
    re.IGNORECASE
)

# Captures "in N units to TITLE" — the 'to ...' clause is the real title
_IN_DURATION_TO_RE = re.compile(
    r'\bin\s+\d+\s*(?:hour|hr|minute|min|second|sec)s?\s+to\s+(.+)',
    re.IGNORECASE
)

# "that quest / that note / that event / that reminder" reference patterns
_THAT_QUEST_RE = re.compile(r'\b(?:that|the last|this)\s+quest\b', re.IGNORECASE)
_THAT_EVENT_RE = re.compile(r'\b(?:that|the last|this)\s+(?:event|reminder)\b', re.IGNORECASE)
_THAT_NOTE_RE = re.compile(r'\b(?:that|the last|this)\s+(?:note|archive note)\b', re.IGNORECASE)


def _resolve_time(text: str) -> Optional[tuple]:
    """Extract hour, minute from text. Returns (hour24, minute) or None."""
    m = _TIME_RE.search(text)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2)) if m.group(2) else 0
    ampm = (m.group(3) or "").lower()
    if ampm == "pm" and hour < 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0
    elif not ampm and hour <= 7:
        # Heuristic: bare "7" probably means 7pm, not 7am
        hour += 12
    return (hour, minute)


def resolve_datetime(text: str) -> Optional[str]:
    """
    Parse natural language date/time into ISO format string.
    Returns None if no datetime can be extracted.
    """
    now = datetime.now()
    target_date = None
    target_time = _resolve_time(text)

    # "in N hours/minutes"
    m = _IN_DURATION_RE.search(text)
    if m:
        amount = int(m.group(1))
        unit = m.group(2).lower()
        if unit.startswith("hour") or unit.startswith("hr"):
            dt = now + timedelta(hours=amount)
        elif unit.startswith("min"):
            dt = now + timedelta(minutes=amount)
        else:
            dt = now + timedelta(seconds=amount)
        return dt.strftime("%Y-%m-%dT%H:%M")

    # Relative days
    m = _RELATIVE_DAY_RE.search(text)
    if m:
        day_word = m.group(1).lower()
        if day_word in ("today", "tonight"):
            target_date = now.date()
        elif day_word == "tomorrow":
            target_date = (now + timedelta(days=1)).date()
        elif day_word == "day after tomorrow":
            target_date = (now + timedelta(days=2)).date()

    # "next Monday" etc.
    if not target_date:
        m = _NEXT_DAY_RE.search(text)
        if m:
            day_name = m.group(1).lower()
            target_dow = _DAY_NAMES.get(day_name)
            if target_dow is not None:
                days_ahead = (target_dow - now.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7
                target_date = (now + timedelta(days=days_ahead)).date()

    if target_date:
        if target_time:
            h, m = target_time
        else:
            # Default time for "tonight" = 9pm, else 9am
            if "tonight" in text.lower():
                h, m = 21, 0
            else:
                h, m = 9, 0
        dt = datetime.combine(target_date, datetime.min.time().replace(hour=h, minute=m))
        return dt.strftime("%Y-%m-%dT%H:%M")

    # If we only got a time with no date, assume today (or tomorrow if time already passed)
    if target_time:
        h, m = target_time
        dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if dt < now:
            dt += timedelta(days=1)
        return dt.strftime("%Y-%m-%dT%H:%M")

    return None


# ============================================================
# Fuzzy title matching
# ============================================================

def _fuzzy_match(query: str, items: List[Dict], key: str = "title", threshold: float = 0.45) -> List[Dict]:
    """Return items sorted by fuzzy match score against query."""
    query_lower = query.lower().strip()
    scored = []
    for item in items:
        title = item.get(key, "").lower()
        # Exact substring match gets high score
        if query_lower in title or title in query_lower:
            scored.append((item, 0.95))
        else:
            ratio = SequenceMatcher(None, query_lower, title).ratio()
            if ratio >= threshold:
                scored.append((item, ratio))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in scored]


# ============================================================
# Tag inference for archive notes
# ============================================================

_TAG_KEYWORDS = {
    "bug fix": ["bug", "error", "fix", "crash", "exception", "traceback", "stack trace", "debug", "patch"],
    "study": ["exam", "study", "homework", "assignment", "lecture", "course", "class", "learn", "tutorial"],
    "health": ["health", "exercise", "workout", "diet", "sleep", "medicine", "doctor", "gym", "run"],
    "idea": ["idea", "concept", "brainstorm", "maybe", "what if", "proposal", "suggest"],
    "personal": ["personal", "family", "friend", "birthday", "anniversary", "vacation", "trip"],
    "project": ["project", "build", "deploy", "release", "feature", "implement", "code", "develop"],
}

_VALID_TAGS = {"project", "study", "health", "idea", "bug fix", "personal"}


def _infer_tag(text: str) -> str:
    """Infer archive note tag from text content. Returns best match or 'project' default."""
    text_lower = text.lower()
    best_tag = "project"
    best_count = 0
    for tag, keywords in _TAG_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > best_count:
            best_count = count
            best_tag = tag
    return best_tag


def _extract_explicit_tag(text: str) -> Optional[str]:
    """Extract explicitly stated tag from text."""
    text_lower = text.lower()
    # Check multi-word tags first
    if "bug fix" in text_lower:
        return "bug fix"
    for tag in _VALID_TAGS:
        patterns = [
            rf'\btag[:\s]+{re.escape(tag)}\b',
            rf'\bunder\s+{re.escape(tag)}\b',
            rf'\bas\s+{re.escape(tag)}\b',
            rf'\bcategory[:\s]+{re.escape(tag)}\b',
            rf'\b{re.escape(tag)}\s+(?:tag|note|category)\b',
        ]
        for pat in patterns:
            if re.search(pat, text_lower):
                return tag
    return None


# ============================================================
# Main intent patterns
# ============================================================

# --- QUEST patterns ---
_QUEST_CREATE_RE = re.compile(
    r'(?:add|create|make|new|start)\s+(?:a\s+)?quest[:\s]+(.+)',
    re.IGNORECASE
)
_QUEST_CREATE_ALT_RE = re.compile(
    r'(?:add|create|make|new|start)\s+(?:a\s+)?(?:side\s+)?quest\s*(?:called|named|titled)?\s*[:\-]?\s*(.+)',
    re.IGNORECASE
)
_QUEST_TODO_RE = re.compile(
    r'^(?:todo|to-do|to do)[:\s]+(.+)',
    re.IGNORECASE
)
_QUEST_COMPLETE_RE = re.compile(
    r'(?:mark|set)\s+(?:the\s+)?(?:quest\s+)?["\']?(.+?)["\']?\s+(?:as\s+)?(?:done|complete|completed|finished)',
    re.IGNORECASE
)
_QUEST_COMPLETE_ALT_RE = re.compile(
    r'(?:complete|finish)\s+(?:the\s+)?(?:quest\s+)?["\']?(.+?)["\']?\s*$',
    re.IGNORECASE
)
_QUEST_REOPEN_RE = re.compile(
    r'(?:reopen|re-open|reactivate|mark\s+.+?\s+active(?:\s+again)?)\s*(?:the\s+)?(?:quest\s+)?["\']?(.+?)["\']?\s*$',
    re.IGNORECASE
)
_QUEST_REOPEN_ALT_RE = re.compile(
    r'(?:mark|set)\s+(?:the\s+)?(?:quest\s+)?["\']?(.+?)["\']?\s+(?:as\s+)?(?:active|active again|reopened)',
    re.IGNORECASE
)
_QUEST_DELETE_RE = re.compile(
    r'(?:delete|remove)\s+(?:the\s+)?(?:quest\s+)?["\']?(.+?)["\']?\s*$',
    re.IGNORECASE
)
_QUEST_PRIORITY_RE = re.compile(
    r'(?:change|set|update)\s+(?:the\s+)?priority\s+(?:of\s+)?["\']?(.+?)["\']?\s+to\s+(high|medium|low)',
    re.IGNORECASE
)
_QUEST_MOVE_SIDE_RE = re.compile(
    r'(?:move|change|set)\s+(?:the\s+)?(?:quest\s+)?["\']?(.+?)["\']?\s+to\s+side\s*quest',
    re.IGNORECASE
)
_QUEST_MOVE_MAIN_RE = re.compile(
    r'(?:move|change|set)\s+(?:the\s+)?(?:quest\s+)?["\']?(.+?)["\']?\s+to\s+main\s*quest',
    re.IGNORECASE
)

# --- EVENT / REMINDER patterns ---
_EVENT_CREATE_RE = re.compile(
    r'(?:remind\s+me|set\s+(?:a\s+)?reminder|schedule(?:\s+an?\s+event)?)\s+(.+)',
    re.IGNORECASE
)
_EVENT_CREATE_ALT_RE = re.compile(
    r'(?:add|create|make|new)\s+(?:an?\s+)?(?:event|reminder)[:\s]+(.+)',
    re.IGNORECASE
)
_EVENT_COMPLETE_RE = re.compile(
    r'(?:mark|set)\s+(?:the\s+)?(?:event|reminder)\s+["\']?(.+?)["\']?\s+(?:as\s+)?(?:done|complete|completed)',
    re.IGNORECASE
)
_EVENT_DELETE_RE = re.compile(
    r'(?:delete|remove|cancel)\s+(?:the\s+)?(?:event|reminder)\s+["\']?(.+?)["\']?\s*$',
    re.IGNORECASE
)

# --- ARCHIVE NOTE patterns ---
_NOTE_CREATE_RE = re.compile(
    r'(?:note\s+this|save\s+this|remember\s+this|important)[:\s]+(.+)',
    re.IGNORECASE | re.DOTALL
)
_NOTE_CREATE_ALT_RE = re.compile(
    r'(?:add|create|make|new|save)\s+(?:a\s+)?(?:note|archive\s+note)[:\s]+(.+)',
    re.IGNORECASE | re.DOTALL
)
_NOTE_DELETE_RE = re.compile(
    r'(?:delete|remove)\s+(?:the\s+)?(?:note|archive\s+note)\s+["\']?(.+?)["\']?\s*$',
    re.IGNORECASE
)
_NOTE_TAG_UPDATE_RE = re.compile(
    r'(?:change|set|update)\s+(?:the\s+)?tag\s+(?:of\s+)?(?:note\s+)?["\']?(.+?)["\']?\s+to\s+(.+)',
    re.IGNORECASE
)

# --- IMPLICIT CAPTURE patterns (Phase 5) ---
# Quest-like implicit phrases
_IMPLICIT_QUEST_RE = re.compile(
    r'^(?:(?:I|we)\s+(?:need|have|got)\s+to|'
    r'(?:I|we)\s+should|'
    r"don'?t\s+(?:forget|let\s+me\s+forget)\s+(?:to\s+|this\s*[:\s]?)?|"
    r'(?:I|we)\s+must|'
    r'(?:I|we)\s+gotta|'
    r'this\s+needs?\s+(?:fixing|to\s+be\s+fixed|work))\s*(.+)',
    re.IGNORECASE
)
# "fix X" at start of message — strong quest signal
_IMPLICIT_FIX_RE = re.compile(
    r'^fix\s+(?:the\s+)?(.+)',
    re.IGNORECASE
)
# "we have a lot to do" — too vague, just ask
_IMPLICIT_VAGUE_QUEST_RE = re.compile(
    r'^(?:(?:I|we)\s+have\s+(?:a\s+lot|so\s+much|tons?)\s+to\s+do|'
    r'there\'?s?\s+(?:a\s+lot|so\s+much)\s+to\s+do)',
    re.IGNORECASE
)

# Event-like implicit phrases
_IMPLICIT_EVENT_RE = re.compile(
    r'^(?:ping\s+me|alert\s+me|buzz\s+me|nudge\s+me|'
    r'later\s+at|at\s+\d)\s*(.+)',
    re.IGNORECASE
)

# Archive-like implicit phrases
_IMPLICIT_NOTE_RE = re.compile(
    r'^(?:log\s+this|save\s+this\s+thought|remember\s+that|'
    r'note\s+to\s+self)\s*[:\s]*(.+)',
    re.IGNORECASE | re.DOTALL
)

# --- PANEL NAVIGATION patterns (Phase 5) ---
_NAV_QUEST_RE = re.compile(
    r'^(?:open|show|go\s+to|switch\s+to|view)\s+(?:my\s+)?(?:the\s+)?'
    r'(?:(main|side|completed|active|done)\s+)?quests?(?:\s+panel)?$',
    re.IGNORECASE
)
_NAV_ARCHIVE_RE = re.compile(
    r'^(?:open|show|go\s+to|switch\s+to|view)\s+(?:my\s+)?(?:the\s+)?'
    r'(?:archive|notes?|knowledge)(?:\s+panel)?$',
    re.IGNORECASE
)
_NAV_ARCHIVE_TAG_RE = re.compile(
    r'^(?:show|open|view)\s+(?:my\s+)?(\w+)\s+notes?$',
    re.IGNORECASE
)
_NAV_EVENTS_RE = re.compile(
    r'^(?:open|show|go\s+to|switch\s+to|view)\s+(?:my\s+)?(?:the\s+)?'
    r'(?:events?|reminders?|schedule)(?:\s+panel)?$',
    re.IGNORECASE
)
_NAV_EVENTS_QUERY_RE = re.compile(
    r'^(?:what|which)\s+(?:reminders?|events?)\s+(?:are|is)\s+(?:active|pending|due|upcoming)',
    re.IGNORECASE
)
_NAV_SETTINGS_RE = re.compile(
    r'^(?:open|show|go\s+to)\s+(?:the\s+)?settings(?:\s+panel)?$',
    re.IGNORECASE
)
_NAV_HOME_RE = re.compile(
    r'^(?:go\s+)?(?:home|back\s+to\s+(?:home|chat|main))$',
    re.IGNORECASE
)

# --- Priority & category extraction helpers ---
_PRIORITY_RE = re.compile(r'\bpriority\s+(high|medium|low)\b', re.IGNORECASE)
_PRIORITY_WORD_RE = re.compile(r'\b(high|medium|low)\s+priority\b', re.IGNORECASE)
_SIDE_QUEST_RE = re.compile(r'\bside\s*quest\b', re.IGNORECASE)
_MAIN_QUEST_RE = re.compile(r'\bmain\s*quest\b', re.IGNORECASE)


def _clean_quest_title(raw: str) -> tuple:
    """
    Extract title + metadata from raw quest creation text.
    Returns (title, priority, status).
    """
    text = raw.strip().rstrip(".")

    # Extract priority
    priority = "medium"
    m = _PRIORITY_RE.search(text)
    if m:
        priority = m.group(1).lower()
        text = text[:m.start()] + text[m.end():]
    else:
        m = _PRIORITY_WORD_RE.search(text)
        if m:
            priority = m.group(1).lower()
            text = text[:m.start()] + text[m.end():]

    # Extract category (side/main -> status)
    status = "active"
    if _SIDE_QUEST_RE.search(text):
        status = "side"
        text = _SIDE_QUEST_RE.sub("", text)
    elif _MAIN_QUEST_RE.search(text):
        status = "active"
        text = _MAIN_QUEST_RE.sub("", text)

    # Clean up separators and extra whitespace
    title = re.sub(r'[\s,\-]+$', '', text)
    title = re.sub(r'^[,\-\s]+', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    title = title.rstrip(',.;:')

    return title, priority, status


def _extract_event_parts(raw: str) -> tuple:
    """
    Extract title, datetime, description from raw event text.
    E.g. "tomorrow at 7pm to submit assignment" -> ("submit assignment", "2025-...", "")
    E.g. "in 30 seconds to drink water" -> ("drink water", "2025-...", "")
    """
    text = raw.strip().rstrip(".")

    # Resolve datetime first
    dt = resolve_datetime(text)

    # Priority: if "in N units to TITLE" pattern, extract title from 'to' clause directly
    m_to = _IN_DURATION_TO_RE.search(text)
    if m_to:
        title_text = m_to.group(1).strip()
        title_text = re.sub(r'[,\-\s]+$', '', title_text)
        return title_text or "Untitled Event", dt, ""

    # Otherwise: for "tomorrow at 7pm to X" style, look for 'to' after datetime fragments
    # First try to find a 'to CLAUSE' after removing datetime
    title_text = text
    for pat in [_TIME_RE, _RELATIVE_DAY_RE, _NEXT_DAY_RE, _IN_DURATION_RE]:
        title_text = pat.sub("", title_text)
    # Remove leading connector words (to, that, about)
    title_text = re.sub(r'^\s*\b(to|that|about)\b\s*', '', title_text)
    title_text = re.sub(r'\s+', ' ', title_text).strip()
    title_text = re.sub(r'^[,\-\s]+', '', title_text)
    title_text = re.sub(r'[,\-\s]+$', '', title_text)

    return title_text or "Untitled Event", dt, ""


def _extract_note_parts(raw: str) -> tuple:
    """
    Extract title, body, tag from raw note text.
    Returns (title, body, tag).
    """
    text = raw.strip()

    # Check for explicit tag
    explicit_tag = _extract_explicit_tag(text)

    # Remove tag mention from text
    if explicit_tag:
        # Remove patterns like "tag: bug fix", "under bug fix", etc.
        for pat in [
            rf'\btag[:\s]+{re.escape(explicit_tag)}\b',
            rf'\bunder\s+{re.escape(explicit_tag)}\b',
            rf'\bas\s+{re.escape(explicit_tag)}\b',
            rf'\bcategory[:\s]+{re.escape(explicit_tag)}\b',
            rf'\b{re.escape(explicit_tag)}\s+(?:tag|note|category)\b',
        ]:
            text = re.sub(pat, '', text, flags=re.IGNORECASE)

    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^[,.\-\s]+', '', text)
    text = re.sub(r'[,.\-\s]+$', '', text)

    tag = explicit_tag or _infer_tag(text)

    # Split title from body: first sentence or first ~60 chars
    if ". " in text:
        parts = text.split(". ", 1)
        title = parts[0].strip()
        body = parts[1].strip() if len(parts) > 1 else text
    elif len(text) > 80:
        # Use first ~60 chars as title
        idx = text.rfind(' ', 0, 60)
        if idx > 20:
            title = text[:idx].strip()
            body = text
        else:
            title = text[:60].strip()
            body = text
    else:
        title = text
        body = text

    return title, body, tag


# ============================================================
# ActionRouter
# ============================================================

class ActionRouter:
    """
    Deterministic router that converts natural language into panel CRUD actions.
    Returns None if no action is detected (message should go to LLM).

    All returns carry 'meta' (structured info for formatting) instead of
    pre-baked confirmation strings.  The server formats Lumina-persona replies.
    """

    def __init__(self, memory_store):
        self.store = memory_store

    def parse(self, text: str, last_ids: Optional[Dict] = None,
              auto_capture: bool = True) -> Optional[Dict]:
        """
        Parse user text and return an action dict or None.

        last_ids: {"quest": int|None, "event": int|None, "note": int|None}
            Session-scoped IDs of the last-created/last-actioned items.
        auto_capture: If True, implicit phrases can auto-create tasks.

        Returns: {
            "action": "create"|"update"|"delete",
            "panel": "quests"|"events"|"archive",
            "data": {...},
            "meta": {"action_type", "entity_type", "title", ...},
        }
        Or: {
            "action": "ask_followup",
            "panel": str,
            "meta": {"followup_text": str},
        }
        Or: None (no action detected)
        """
        text = text.strip()
        if not text:
            return None

        self._last_ids = last_ids or {}
        self._auto_capture = auto_capture

        # Try navigation first (highest priority, short-circuits)
        result = self._try_navigate(text)
        if result:
            return result

        # Try explicit patterns (high confidence)
        result = self._try_quest(text)
        if result:
            return result

        result = self._try_event(text)
        if result:
            return result

        result = self._try_archive(text)
        if result:
            return result

        # Try implicit natural language capture (lower confidence)
        if auto_capture:
            result = self._try_implicit(text)
            if result:
                return result

        return None

    # --------------------------------------------------------
    # "that quest / that note / that event" resolution
    # --------------------------------------------------------
    def _resolve_that_entity(self, entity_type: str) -> Optional[Dict]:
        """Look up the last-actioned item by type from session last_ids."""
        key_map = {"quest": "quest", "event": "event", "reminder": "event", "note": "note", "archive note": "note"}
        key = key_map.get(entity_type)
        item_id = self._last_ids.get(key) if key else None
        if not item_id:
            return None
        if key == "quest":
            quests = self.store.list_quests()
            return next((q for q in quests if q["id"] == item_id), None)
        elif key == "event":
            events = self.store.list_events()
            return next((e for e in events if e["id"] == item_id), None)
        elif key == "note":
            notes = self.store.list_archive_notes()
            return next((n for n in notes if n["id"] == item_id), None)
        return None

    # --------------------------------------------------------
    # PANEL NAVIGATION (Phase 5)
    # --------------------------------------------------------
    def _try_navigate(self, text: str) -> Optional[Dict]:
        """Detect panel navigation intents like 'open quests', 'show archive', etc."""
        # Quests panel
        m = _NAV_QUEST_RE.match(text)
        if m:
            view_filter = (m.group(1) or "active").lower()
            if view_filter in ("done",):
                view_filter = "completed"
            return {"action": "navigate", "panel": "quests",
                    "data": {"view": view_filter},
                    "meta": {"panel": "quests", "view": view_filter}}

        # Archive panel
        if _NAV_ARCHIVE_RE.match(text):
            return {"action": "navigate", "panel": "archive",
                    "data": {"view": "all"},
                    "meta": {"panel": "archive", "view": "all"}}

        # Archive with tag filter: "show study notes"
        m = _NAV_ARCHIVE_TAG_RE.match(text)
        if m:
            tag = m.group(1).lower()
            # Skip generic words that aren't tags
            if tag not in ("my", "the", "all", "some", "any"):
                return {"action": "navigate", "panel": "archive",
                        "data": {"view": "tag", "tag": tag},
                        "meta": {"panel": "archive", "view": "tag", "tag": tag}}

        # Events panel
        if _NAV_EVENTS_RE.match(text):
            return {"action": "navigate", "panel": "events",
                    "data": {"view": "all"},
                    "meta": {"panel": "events", "view": "all"}}

        # Events query: "what reminders are active?"
        if _NAV_EVENTS_QUERY_RE.match(text):
            return {"action": "navigate", "panel": "events",
                    "data": {"view": "active"},
                    "meta": {"panel": "events", "view": "active"}}

        # Settings
        if _NAV_SETTINGS_RE.match(text):
            return {"action": "navigate", "panel": "settings",
                    "data": {}, "meta": {"panel": "settings"}}

        # Home
        if _NAV_HOME_RE.match(text):
            return {"action": "navigate", "panel": "home",
                    "data": {}, "meta": {"panel": "home"}}

        return None

    # --------------------------------------------------------
    # IMPLICIT NATURAL LANGUAGE CAPTURE
    # --------------------------------------------------------
    def _try_implicit(self, text: str) -> Optional[Dict]:
        """Detect implicit task/event/note phrases and either auto-create or ask."""
        # --- Vague quest phrases (always ask) ---
        if _IMPLICIT_VAGUE_QUEST_RE.match(text):
            return {"action": "ask_followup", "panel": "quests",
                    "meta": {"followup_text": "Want me to add that as a quest? What specifically?"}}

        # --- "fix X" — high confidence quest ---
        m = _IMPLICIT_FIX_RE.match(text)
        if m:
            raw_title = m.group(1).strip().rstrip(".")
            if len(raw_title) > 3:
                title, priority, status = _clean_quest_title(raw_title)
                if title:
                    return {
                        "action": "create", "panel": "quests",
                        "data": {"title": f"Fix {title}", "description": "", "priority": "high", "status": "active"},
                        "meta": {"action_type": "create", "entity_type": "quest",
                                 "title": f"Fix {title}", "priority": "high", "category": "main",
                                 "implicit": True},
                    }

        # --- "I need to / we have to / don't forget to / I should" ---
        m = _IMPLICIT_QUEST_RE.match(text)
        if m:
            raw_title = m.group(1).strip().rstrip(".")
            if len(raw_title) < 5:
                return None  # Too short — probably conversational
            # If message is very long (>120 chars), it's likely a conversation, not a task
            if len(text) > 120:
                return None
            title, priority, status = _clean_quest_title(raw_title)
            if title:
                return {
                    "action": "create", "panel": "quests",
                    "data": {"title": title, "description": "", "priority": priority, "status": "active"},
                    "meta": {"action_type": "create", "entity_type": "quest",
                             "title": title, "priority": priority, "category": "main",
                             "implicit": True},
                }

        # --- "ping me / alert me / buzz me" + time ---
        m = _IMPLICIT_EVENT_RE.match(text)
        if m:
            raw = m.group(1).strip()
            title, dt, notes = _extract_event_parts(text)  # parse full text for datetime
            if dt and title and len(title) > 2:
                return {
                    "action": "create", "panel": "events",
                    "data": {"title": title, "datetime": dt, "notes": notes},
                    "meta": {"action_type": "create", "entity_type": "event",
                             "title": title, "datetime": dt, "implicit": True},
                }

        # --- "log this / save this thought / remember that" ---
        m = _IMPLICIT_NOTE_RE.match(text)
        if m:
            raw = m.group(1).strip()
            if len(raw) > 5:
                title, body, tag = _extract_note_parts(raw)
                if title:
                    return {
                        "action": "create", "panel": "archive",
                        "data": {"title": title, "body": body, "tags": tag},
                        "meta": {"action_type": "create", "entity_type": "note",
                                 "title": title, "tag": tag, "implicit": True},
                    }

        return None

    # --------------------------------------------------------
    # QUESTS
    # --------------------------------------------------------
    def _try_quest(self, text: str) -> Optional[Dict]:
        # --- CREATE ---
        raw = None
        for pat in [_QUEST_CREATE_RE, _QUEST_CREATE_ALT_RE, _QUEST_TODO_RE]:
            m = pat.match(text)
            if m:
                raw = m.group(1)
                break
        if raw:
            title, priority, status = _clean_quest_title(raw)
            if not title:
                return None
            category = "side" if status == "side" else "main"
            return {
                "action": "create",
                "panel": "quests",
                "data": {"title": title, "description": "", "priority": priority, "status": status},
                "meta": {"action_type": "create", "entity_type": "quest", "title": title, "priority": priority, "category": category},
            }

        # --- COMPLETE (including "that quest") ---
        for pat in [_QUEST_COMPLETE_RE, _QUEST_COMPLETE_ALT_RE]:
            m = pat.match(text)
            if m:
                query = m.group(1).strip()
                if _THAT_QUEST_RE.search(query):
                    return self._resolve_that_action("quest", "complete")
                return self._resolve_quest_action(query, "complete")

        # --- REOPEN ---
        for pat in [_QUEST_REOPEN_RE, _QUEST_REOPEN_ALT_RE]:
            m = pat.match(text)
            if m:
                query = m.group(1).strip()
                if _THAT_QUEST_RE.search(query):
                    return self._resolve_that_action("quest", "reopen")
                return self._resolve_quest_action(query, "reopen")

        # --- PRIORITY UPDATE ---
        m = _QUEST_PRIORITY_RE.match(text)
        if m:
            query = m.group(1).strip()
            new_priority = m.group(2).lower()
            if _THAT_QUEST_RE.search(query):
                item = self._resolve_that_entity("quest")
                if item:
                    return {"action": "update", "panel": "quests", "data": {"id": item["id"], "priority": new_priority},
                            "meta": {"action_type": "update", "entity_type": "quest", "title": item["title"], "changes": {"priority": new_priority}}}
                return {"action": "ask_followup", "panel": "quests", "meta": {"followup_text": "Which quest? I lost track."}}
            return self._resolve_quest_update(query, priority=new_priority)

        # --- MOVE TO SIDE/MAIN ---
        m = _QUEST_MOVE_SIDE_RE.match(text)
        if m:
            query = m.group(1).strip()
            if _THAT_QUEST_RE.search(query):
                item = self._resolve_that_entity("quest")
                if item:
                    return {"action": "update", "panel": "quests", "data": {"id": item["id"], "status": "side"},
                            "meta": {"action_type": "update", "entity_type": "quest", "title": item["title"], "changes": {"category": "side"}}}
            return self._resolve_quest_update(query, status="side")

        m = _QUEST_MOVE_MAIN_RE.match(text)
        if m:
            query = m.group(1).strip()
            if _THAT_QUEST_RE.search(query):
                item = self._resolve_that_entity("quest")
                if item:
                    return {"action": "update", "panel": "quests", "data": {"id": item["id"], "status": "active"},
                            "meta": {"action_type": "update", "entity_type": "quest", "title": item["title"], "changes": {"category": "main"}}}
            return self._resolve_quest_update(query, status="active")

        # --- DELETE ---
        m = _QUEST_DELETE_RE.match(text)
        if m:
            query = m.group(1).strip()
            if re.search(r'\bquest\b', text, re.IGNORECASE):
                if _THAT_QUEST_RE.search(query):
                    return self._resolve_that_action("quest", "delete")
                return self._resolve_quest_action(query, "delete")

        return None

    def _resolve_that_action(self, entity_type: str, action: str) -> Optional[Dict]:
        """Resolve 'that quest/event/note' to last-actioned item."""
        item = self._resolve_that_entity(entity_type)
        if not item:
            panel = {"quest": "quests", "event": "events", "reminder": "events", "note": "archive"}.get(entity_type, "quests")
            return {"action": "ask_followup", "panel": panel,
                    "meta": {"followup_text": f"Which {entity_type}? I don't have one in mind right now."}}
        panel = {"quest": "quests", "event": "events", "note": "archive"}.get(entity_type, "quests")
        title = item.get("title", "")
        if action == "complete":
            if entity_type == "quest":
                return {"action": "update", "panel": panel, "data": {"id": item["id"], "status": "completed", "progress": 100},
                        "meta": {"action_type": "complete", "entity_type": entity_type, "title": title, "entity_id": item["id"]}}
            else:
                return {"action": "update", "panel": panel, "data": {"id": item["id"], "completed": 1},
                        "meta": {"action_type": "complete", "entity_type": entity_type, "title": title, "entity_id": item["id"]}}
        elif action == "reopen":
            return {"action": "update", "panel": panel, "data": {"id": item["id"], "status": "active"},
                    "meta": {"action_type": "reopen", "entity_type": entity_type, "title": title, "entity_id": item["id"]}}
        elif action == "delete":
            return {"action": "delete", "panel": panel, "data": {"id": item["id"]},
                    "meta": {"action_type": "delete", "entity_type": entity_type, "title": title, "entity_id": item["id"]}}
        return None

    def _resolve_quest_action(self, query: str, action: str) -> Optional[Dict]:
        """Resolve a quest by fuzzy title match and return action dict."""
        all_quests = self.store.list_quests()
        matches = _fuzzy_match(query, all_quests, "title")
        if not matches:
            return {"action": "ask_followup", "panel": "quests",
                    "meta": {"followup_text": f"I couldn't find a quest matching \"{query}\". Which one did you mean?"}}
        if len(matches) > 1 and matches[0].get("title", "").lower() != query.lower():
            top_title = matches[0].get("title", "").lower()
            if query.lower() not in top_title and top_title not in query.lower():
                options = ", ".join(f'"{m["title"]}"' for m in matches[:5])
                return {"action": "ask_followup", "panel": "quests",
                        "meta": {"followup_text": f"I found a few: {options}. Which one?"}}

        quest = matches[0]
        if action == "complete":
            return {"action": "update", "panel": "quests",
                    "data": {"id": quest["id"], "status": "completed", "progress": 100},
                    "meta": {"action_type": "complete", "entity_type": "quest", "title": quest["title"], "entity_id": quest["id"]}}
        elif action == "reopen":
            return {"action": "update", "panel": "quests",
                    "data": {"id": quest["id"], "status": "active"},
                    "meta": {"action_type": "reopen", "entity_type": "quest", "title": quest["title"], "entity_id": quest["id"]}}
        elif action == "delete":
            return {"action": "delete", "panel": "quests",
                    "data": {"id": quest["id"]},
                    "meta": {"action_type": "delete", "entity_type": "quest", "title": quest["title"], "entity_id": quest["id"]}}
        return None

    def _resolve_quest_update(self, query: str, **kwargs) -> Optional[Dict]:
        """Resolve quest + apply field updates."""
        all_quests = self.store.list_quests()
        matches = _fuzzy_match(query, all_quests, "title")
        if not matches:
            return {"action": "ask_followup", "panel": "quests",
                    "meta": {"followup_text": f"I couldn't find a quest matching \"{query}\". Which one?"}}
        quest = matches[0]
        data = {"id": quest["id"], **kwargs}
        return {"action": "update", "panel": "quests", "data": data,
                "meta": {"action_type": "update", "entity_type": "quest", "title": quest["title"], "entity_id": quest["id"], "changes": kwargs}}

    # --------------------------------------------------------
    # EVENTS / REMINDERS
    # --------------------------------------------------------
    def _try_event(self, text: str) -> Optional[Dict]:
        raw = None
        for pat in [_EVENT_CREATE_RE, _EVENT_CREATE_ALT_RE]:
            m = pat.match(text)
            if m:
                raw = m.group(1)
                break
        if raw:
            title, dt, notes = _extract_event_parts(raw)
            if not dt:
                if re.match(r'(?:remind\s+me\s+to)\b', text, re.IGNORECASE) and not resolve_datetime(text):
                    return {"action": "ask_followup", "panel": "events",
                            "meta": {"followup_text": f"When should I remind you about \"{title}\"? Give me a time."}}
            if not dt:
                return None
            return {
                "action": "create",
                "panel": "events",
                "data": {"title": title, "datetime": dt, "notes": notes},
                "meta": {"action_type": "create", "entity_type": "event", "title": title, "datetime": dt},
            }

        # --- COMPLETE (including "that event/reminder") ---
        m = _EVENT_COMPLETE_RE.match(text)
        if m:
            query = m.group(1).strip()
            if _THAT_EVENT_RE.search(query):
                return self._resolve_that_action("event", "complete")
            return self._resolve_event_action(query, "complete")

        # --- DELETE ---
        m = _EVENT_DELETE_RE.match(text)
        if m:
            query = m.group(1).strip()
            if _THAT_EVENT_RE.search(query):
                return self._resolve_that_action("event", "delete")
            return self._resolve_event_action(query, "delete")

        return None

    def _resolve_event_action(self, query: str, action: str) -> Optional[Dict]:
        all_events = self.store.list_events()
        matches = _fuzzy_match(query, all_events, "title")
        if not matches:
            return {"action": "ask_followup", "panel": "events",
                    "meta": {"followup_text": f"I couldn't find an event matching \"{query}\". Which one?"}}
        event = matches[0]
        if action == "complete":
            return {"action": "update", "panel": "events",
                    "data": {"id": event["id"], "completed": 1},
                    "meta": {"action_type": "complete", "entity_type": "event", "title": event["title"], "entity_id": event["id"]}}
        elif action == "delete":
            return {"action": "delete", "panel": "events",
                    "data": {"id": event["id"]},
                    "meta": {"action_type": "delete", "entity_type": "event", "title": event["title"], "entity_id": event["id"]}}
        return None

    # --------------------------------------------------------
    # ARCHIVE NOTES
    # --------------------------------------------------------
    def _try_archive(self, text: str) -> Optional[Dict]:
        raw = None
        for pat in [_NOTE_CREATE_RE, _NOTE_CREATE_ALT_RE]:
            m = pat.match(text)
            if m:
                raw = m.group(1)
                break
        if raw:
            title, body, tag = _extract_note_parts(raw)
            if not title:
                return None
            return {
                "action": "create",
                "panel": "archive",
                "data": {"title": title, "body": body, "tags": tag},
                "meta": {"action_type": "create", "entity_type": "note", "title": title, "tag": tag},
            }

        # --- TAG UPDATE (including "that note") ---
        m = _NOTE_TAG_UPDATE_RE.match(text)
        if m:
            query = m.group(1).strip()
            new_tag = m.group(2).strip().lower()
            if new_tag not in _VALID_TAGS:
                return {"action": "ask_followup", "panel": "archive",
                        "meta": {"followup_text": f"'{new_tag}' isn't a valid tag. Pick from: {', '.join(sorted(_VALID_TAGS))}."}}
            # Resolve "that note"
            if _THAT_NOTE_RE.search(query):
                item = self._resolve_that_entity("note")
                if item:
                    return {"action": "update", "panel": "archive",
                            "data": {"id": item["id"], "tags": new_tag},
                            "meta": {"action_type": "update", "entity_type": "note", "title": item["title"], "changes": {"tag": new_tag}, "entity_id": item["id"]}}
                return {"action": "ask_followup", "panel": "archive",
                        "meta": {"followup_text": "Which note? I don't have one in mind right now."}}
            all_notes = self.store.list_archive_notes()
            matches = _fuzzy_match(query, all_notes, "title")
            if not matches:
                return {"action": "ask_followup", "panel": "archive",
                        "meta": {"followup_text": f"I couldn't find a note matching \"{query}\"."}}
            note = matches[0]
            return {"action": "update", "panel": "archive",
                    "data": {"id": note["id"], "tags": new_tag},
                    "meta": {"action_type": "update", "entity_type": "note", "title": note["title"], "changes": {"tag": new_tag}, "entity_id": note["id"]}}

        # --- DELETE (including "that note") ---
        m = _NOTE_DELETE_RE.match(text)
        if m:
            query = m.group(1).strip()
            if _THAT_NOTE_RE.search(query):
                return self._resolve_that_action("note", "delete")
            all_notes = self.store.list_archive_notes()
            matches = _fuzzy_match(query, all_notes, "title")
            if not matches:
                return {"action": "ask_followup", "panel": "archive",
                        "meta": {"followup_text": f"I couldn't find a note matching \"{query}\"."}}
            note = matches[0]
            return {"action": "delete", "panel": "archive",
                    "data": {"id": note["id"]},
                    "meta": {"action_type": "delete", "entity_type": "note", "title": note["title"], "entity_id": note["id"]}}

        return None
