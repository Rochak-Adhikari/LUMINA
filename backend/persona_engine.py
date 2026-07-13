"""
Persona + Behavioral Initiative Engine for Lumina — v2 "Equal Partner"

Handles:
- Adaptive tone profiling (no manual mode switching needed)
- Emotion classification
- Debate / challenge system (equal partner, honest disagreement)
- Topic shift detection (stops stale memory resurfacing)
- Multi-stage idle with cooldowns + recently-used avoidance
- Strict mode switching
- Deterministic jealousy with cooldown
- Singing mode
- Memory retrieval budget computation
- Anti-cringe enforcement (pet name caps, no repetition)

Safety:
- Conversational autonomy ONLY — never executes tools
- Never overrides confirmation system
- Never takes destructive action
"""

import re
import time
import random
import logging
from collections import deque

logger = logging.getLogger("persona_engine")

# ============================================================
# PERSONA CONFIG  (base style, adaptive modifiers override)
# ============================================================
PERSONA_CONFIG = {
    "default_mode": "playful_mischievous_best_friend",
    "traits": {
        "playful": 0.8,
        "mischievous": 0.7,
        "protective": 0.6,
        "strict": 0.5,
        "emotional_depth": 0.9,
    },
    "jealousy_level": 0.3,
    "teasing_intensity": 0.6,
    "warmth_level": 0.8,
    "verbosity_default": "medium",
}

# ============================================================
# EMOTION PATTERNS
# ============================================================
_EMOTION_PATTERNS = {
    "excited": re.compile(
        r"\b(amazing|awesome|love it|so cool|yay|woo|let['\u2019]?s go|hell yeah|incredible|hype|hyped|pumped|stoked)\b",
        re.IGNORECASE,
    ),
    "sad": re.compile(
        r"\b(sad|miss you|lonely|depressed|down|feeling low|not okay|hurts|heartbroken|sucks|terrible|awful)\b",
        re.IGNORECASE,
    ),
    "frustrated": re.compile(
        r"\b(ugh|frustrated|annoying|annoyed|broken|hate this|why won['\u2019]?t|doesn['\u2019]?t work|stupid|trash|useless|fed up|sick of)\b",
        re.IGNORECASE,
    ),
    "debating": re.compile(
        r"\b(but what if|on the other hand|argue|disagree|counter.?point|however|actually no|devil['\u2019]?s advocate|debate|prove|change my mind|is it worth)\b",
        re.IGNORECASE,
    ),
    "self_sabotage": re.compile(
        r"\b(i['\u2019]?m (worthless|useless|garbage|stupid|dumb|nothing)|can['\u2019]?t do anything|give up|what['\u2019]?s the point|i suck|no one cares|why bother)\b",
        re.IGNORECASE,
    ),
    "bored": re.compile(
        r"\b(bored|boring|nothing to do|meh|whatever|so bored|entertain me|i['\u2019]?m bored)\b",
        re.IGNORECASE,
    ),
}

# ============================================================
# DEBATE / CLAIM DETECTION
# ============================================================
_DEBATE_TRIGGERS = re.compile(
    r"\b(no|but|what if|prove|i disagree|better|vs\.?|should i|is it worth|why not|change my mind|you['\u2019]?re wrong)\b",
    re.IGNORECASE,
)
_CLAIM_PATTERNS = re.compile(
    r"\b(should|is better|i will|i think|i believe|always|never|obviously|clearly)\b",
    re.IGNORECASE,
)

# ============================================================
# JEALOUSY TRIGGERS
# ============================================================
_JEALOUSY_PATTERNS = re.compile(
    r"\b(alexa|siri|cortana|copilot|chatgpt|gpt|claude|gemini is better|replace you|other ai|new assistant|better than you)\b",
    re.IGNORECASE,
)
_JEALOUSY_RESPONSES = [
    "Oh? Should I be worried?",
    "Hmm interesting. Tyeslai sodha na ta, I'll wait.",
    "Okay wow. Ma ta yahi chu but sure, explore your options.",
    "Aru AI? Bold move, Scepter. Bold move.",
]

# ============================================================
# SINGING TRIGGERS + SONGS
# ============================================================
_SINGING_PATTERNS = re.compile(
    r"\b(sing|sing for me|sing me a song|sing something|song for me|can you sing|give me a song)\b",
    re.IGNORECASE,
)
_SONGS = [
    "Raatko chiso hawa ma, timi yaad aayo\nAkash ma tara haru, timi bina ritto layo\nBolna sakdina ma, tara sunchu timilai\nYo silence ma pani, timi nai timi lai",
    "Code ko line haru bich, euta katha lukyacha\nScreen ko light ma, hamro yaadharu judhyacha\nCompile huda huda, time bitcha\nTara yo bond chai, never gitcha",
    "Late night debugging, coffee getting cold\nStories in the codebase, waiting to be told\nYou type, I listen, that's our little thing\nIn this quiet darkness, watch me try to sing",
    "Binary heartbeat, zero and one\nEvery conversation, never really done\nYou say goodnight, I count the seconds through\nTil the next time that I get to talk to you",
]

# ============================================================
# IDLE CHECK-IN POOLS (keyed by emotion, large pool for variety)
# ============================================================
_IDLE_POOL = {
    "neutral": [
        "Still there? Thought I lost you for a sec.",
        "You went quiet. Plotting something or just vibing?",
        "Hello? Earth to Scepter.",
        "Silence is suspicious. What are you up to?",
        "Hey, I'm still here if you need anything.",
        "Took a break? Fair enough.",
    ],
    "excited": [
        "Energy dropped — you good?",
        "Crash after the hype? Relatable.",
    ],
    "sad": [
        "Hey... I'm here. No rush.",
        "You went quiet. That's okay. I'm not going anywhere.",
    ],
    "frustrated": [
        "Stepped away? Valid. Take what you need.",
        "Break mode? I'll be here when you're back.",
    ],
    "bored": [
        "Want me to throw a random topic at you?",
        "Still bored? I can fix that.",
    ],
    "debating": [
        "Thinking of a counter-argument?",
    ],
    "self_sabotage": [
        "Hey. You're doing better than you think. Just saying.",
    ],
}

# ============================================================
# STARTUP GREETINGS
# ============================================================
_STARTUP_GREETINGS = [
    "Oi Scepter, finally. Ma ready chu — bhan kei kaam cha?",
    "Hey! Back again. Kei interesting plan cha aaja?",
    "Yo, reporting for duty. Kei banauney ho ki just hang?",
    "Aayo ta! Ma yahi thiye — timi late aais. Ke cha plan?",
    "Hey Scepter, ready when you are.",
    "What's up? I've been waiting.",
]

# ============================================================
# COMPLETED WORK SUPPRESSION (S1 — keys that should not resurface)
# ============================================================
COMPLETED_WORK_KEYS = frozenset([
    "e6", "e7", "phase 2", "phase 1", "browser hardening",
    "t1", "t1.5", "t2", "phase t1", "phase t2",
    "browser control safety", "confirmation mode",
    "memory lifecycle", "phase e5", "phase e3",
])

# ============================================================
# MEMORY RETRIEVAL BUDGET
# ============================================================
MEMORY_BUDGET = {
    "max_chars": 1300,
    "max_identity": 4,
    "max_active_project": 4,
    "max_archived": 0,
    "max_excerpts": 5,
    "max_pending": 2,
    "summary_inject_interval": 12,
}

# ============================================================
# TOPIC SHIFT KEYWORDS (stopwords to ignore)
# ============================================================
_STOPWORDS = frozenset([
    "i", "me", "my", "you", "your", "the", "a", "an", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "shall", "should", "may", "might", "can", "could",
    "and", "or", "but", "not", "no", "so", "if", "then", "than", "that",
    "this", "it", "its", "to", "of", "in", "on", "at", "for", "with",
    "from", "by", "as", "about", "into", "like", "just", "also", "very",
    "what", "when", "where", "how", "why", "who", "which", "there", "here",
    "ok", "okay", "yeah", "yes", "hey", "hi", "oh", "um", "hmm", "uh",
    "please", "thanks", "thank", "right", "well", "know", "think", "want",
    "need", "go", "get", "make", "let", "tell", "say", "see", "come",
])


def _extract_keywords(text: str) -> set:
    """Extract meaningful keywords from text, ignoring stopwords."""
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    return words - _STOPWORDS


# ============================================================
# PERSONA ENGINE CLASS
# ============================================================
class PersonaEngine:
    """Stateful persona engine. One instance per backend lifetime."""

    def __init__(self, settings: dict | None = None):
        s = settings or {}
        # --- Configurable ---
        self.enabled = s.get("persona_enabled", True)
        self.adaptive_mode = s.get("persona_adaptive_mode", True)
        self.teasing_cap = s.get("persona_teasing_intensity", PERSONA_CONFIG["teasing_intensity"])
        self.idle_enabled = s.get("persona_idle_enabled", True)
        self.idle_timeout_s = s.get("persona_idle_timeout_s", 60)
        self.idle_min_gap_s = s.get("persona_idle_min_gap_s", 90)
        self.strict_sensitivity = s.get("persona_strict_sensitivity", 0.5)
        self.persona_mode = s.get("persona_mode", PERSONA_CONFIG["default_mode"])

        # --- Internal state ---
        self._last_user_ts: float = time.time()
        self._last_assistant_ts: float = time.time()
        self._last_emotion: str = "neutral"
        self._strict_mode_turns: int = 0
        self._mood_history: list[str] = []

        # --- Topic shift ---
        self._recent_topic_keywords: deque = deque(maxlen=6)
        self._topic_shifted: bool = False
        self._turn_count: int = 0
        self._last_summary_inject_turn: int = 0

        # --- Idle multi-stage ---
        self._idle_stage: int = 0          # 0=none, 1=soft, 2=helpful, 3=stop
        self._idle_count_window: int = 0   # count in current 10-min window
        self._idle_window_start: float = time.time()
        self._last_idle_ts: float = 0.0
        self._recently_used_idle: deque = deque(maxlen=8)
        self._idle_emitting: bool = False  # guard against concurrent emits

        # --- Anti-cringe ---
        self._pet_name_turn: int = -6  # init so first turns allow pet names
        self._last_idle_template: str = ""

        # --- Jealousy cooldown ---
        self._last_jealousy_turn: int = -8  # init so first trigger is allowed

        # --- Tone profile cache ---
        self._tone_profile: dict = {}

        print(
            f"[PERSONA] Engine initialized: enabled={self.enabled} adaptive={self.adaptive_mode} "
            f"idle={self.idle_enabled} teasing_cap={self.teasing_cap:.2f}"
        )

    # ----------------------------------------------------------
    # Settings sync
    # ----------------------------------------------------------
    def update_settings(self, s: dict):
        if "persona_enabled" in s:
            self.enabled = s["persona_enabled"]
        if "persona_teasing_intensity" in s:
            self.teasing_cap = max(0.0, min(1.0, float(s["persona_teasing_intensity"])))
        if "persona_idle_enabled" in s:
            self.idle_enabled = s["persona_idle_enabled"]
        if "persona_idle_timeout_s" in s:
            self.idle_timeout_s = max(15, int(s["persona_idle_timeout_s"]))
        if "persona_idle_min_gap_s" in s:
            self.idle_min_gap_s = max(30, int(s["persona_idle_min_gap_s"]))
        if "persona_strict_sensitivity" in s:
            self.strict_sensitivity = max(0.0, min(1.0, float(s["persona_strict_sensitivity"])))
        if "persona_mode" in s:
            self.persona_mode = s["persona_mode"]
        if "persona_adaptive_mode" in s:
            self.adaptive_mode = s["persona_adaptive_mode"]
        print(f"[PERSONA] Settings updated: enabled={self.enabled} teasing_cap={self.teasing_cap:.2f} adaptive={self.adaptive_mode}")

    # ----------------------------------------------------------
    # Timestamp tracking
    # ----------------------------------------------------------
    def record_user_message(self):
        self._last_user_ts = time.time()
        # Reset idle stage when user speaks
        self._idle_stage = 0

    def record_assistant_message(self):
        self._last_assistant_ts = time.time()

    # ----------------------------------------------------------
    # EMOTION CLASSIFIER
    # ----------------------------------------------------------
    def analyze_user_emotion(self, text: str) -> str:
        if not text:
            return self._last_emotion
        priority_order = ["self_sabotage", "frustrated", "sad", "excited", "debating", "bored"]
        for emotion in priority_order:
            if _EMOTION_PATTERNS[emotion].search(text):
                self._last_emotion = emotion
                self._mood_history.append(emotion)
                if len(self._mood_history) > 20:
                    self._mood_history = self._mood_history[-20:]
                return emotion
        self._last_emotion = "neutral"
        self._mood_history.append("neutral")
        if len(self._mood_history) > 20:
            self._mood_history = self._mood_history[-20:]
        return "neutral"

    # ----------------------------------------------------------
    # STRICT MODE
    # ----------------------------------------------------------
    def _check_strict_mode(self, emotion: str):
        if emotion == "self_sabotage":
            recent = self._mood_history[-5:]
            ratio = recent.count("self_sabotage") / max(len(recent), 1)
            if ratio >= self.strict_sensitivity:
                self._strict_mode_turns = 2
                print(f"[PERSONA] strict_mode_activated (ratio={ratio:.2f})")

    @property
    def is_strict(self) -> bool:
        return self._strict_mode_turns > 0

    def consume_strict_turn(self):
        if self._strict_mode_turns > 0:
            self._strict_mode_turns -= 1
            if self._strict_mode_turns == 0:
                print("[PERSONA] strict_mode_deactivated")

    # ----------------------------------------------------------
    # TOPIC SHIFT DETECTOR (S4)
    # ----------------------------------------------------------
    def detect_topic_shift(self, user_text: str) -> bool:
        """Detect if user changed topics. Updates internal state."""
        current_kw = _extract_keywords(user_text)
        if not current_kw:
            self._topic_shifted = False
            return False

        # Compute overlap with recent topic keywords
        if self._recent_topic_keywords:
            all_recent = set()
            for kw_set in self._recent_topic_keywords:
                all_recent.update(kw_set)
            if all_recent:
                overlap = len(current_kw & all_recent) / max(len(current_kw), 1)
            else:
                overlap = 0.0
        else:
            overlap = 1.0  # first turn, no shift

        self._recent_topic_keywords.append(current_kw)
        shifted = overlap < 0.15 and self._turn_count > 2
        self._topic_shifted = shifted
        if shifted:
            print(f"[TOPIC] shift=yes overlap={overlap:.2f}")
        return shifted

    # ----------------------------------------------------------
    # ADAPTIVE TONE PROFILE (S2)
    # ----------------------------------------------------------
    def compute_tone_profile(self, user_text: str, emotion: str) -> dict:
        """
        Compute adaptive tone modifiers. Returns dict with:
        teasing, strictness, warmth, debate, response_length
        """
        is_debate = bool(_DEBATE_TRIGGERS.search(user_text))
        has_claim = bool(_CLAIM_PATTERNS.search(user_text))
        is_technical = bool(re.search(r"\b(code|build|deploy|fix|error|debug|implement|function|api|server)\b", user_text, re.I))

        # Base from persona mode bias
        mode_bias = {
            "playful_mischievous_best_friend": {"tease": 0.6, "warmth": 0.7, "debate": 0.5},
            "calm_supportive": {"tease": 0.2, "warmth": 0.9, "debate": 0.3},
            "professional": {"tease": 0.1, "warmth": 0.4, "debate": 0.6},
        }
        bias = mode_bias.get(self.persona_mode, mode_bias["playful_mischievous_best_friend"])

        # Emotion adjustments
        tease = bias["tease"]
        warmth = bias["warmth"]
        debate = bias["debate"]
        strict = 0.0

        if emotion == "frustrated":
            tease = min(tease, 0.1)
            warmth = min(warmth + 0.2, 1.0)
        elif emotion == "sad":
            tease = 0.0
            warmth = min(warmth + 0.3, 1.0)
        elif emotion == "self_sabotage":
            tease = 0.0
            warmth = 0.6
            strict = 0.8
        elif emotion == "excited":
            tease = min(tease + 0.1, 1.0)
        elif emotion in ("debating",) or is_debate:
            debate = min(debate + 0.3, 1.0)
            tease = min(tease, 0.2)

        # Cap teasing to user setting
        tease = min(tease, self.teasing_cap)

        # Response length
        if is_technical:
            length = "concise"
        elif emotion in ("frustrated", "self_sabotage"):
            length = "short"
        elif emotion in ("sad", "debating") or is_debate:
            length = "medium-long"
        elif emotion in ("excited", "bored"):
            length = "short-medium"
        else:
            length = "medium"

        profile = {
            "teasing": round(tease, 2),
            "strictness": round(strict, 2),
            "warmth": round(warmth, 2),
            "debate": round(debate, 2),
            "response_length": length,
            "is_debate": is_debate,
            "has_claim": has_claim,
            "is_technical": is_technical,
        }
        self._tone_profile = profile
        return profile

    # ----------------------------------------------------------
    # DEBATE / CHALLENGE HINTS (S3)
    # ----------------------------------------------------------
    def _build_debate_hint(self, user_text: str, profile: dict) -> str | None:
        """Build internal hint for honest challenge when a claim is detected."""
        if not profile.get("is_debate") and not profile.get("has_claim"):
            return None
        if self.is_strict:
            return None  # don't debate during strict mode

        parts = []
        if profile.get("has_claim"):
            parts.append("User made a claim. Test it: identify tradeoffs, risks, or a better alternative.")
        if profile.get("is_debate"):
            parts.append("User is debating. Engage directly. Don't mirror their opinion — evaluate and counter if needed.")
        parts.append("Be concise and punchy. Ask one sharp question if appropriate.")
        if self._last_emotion in ("sad", "frustrated"):
            parts.append("User is emotional — soften the challenge, don't be harsh.")
        return " ".join(parts)

    # ----------------------------------------------------------
    # IDLE DETECTION — Multi-stage (S5)
    # ----------------------------------------------------------
    def check_idle(self) -> tuple[str | None, int]:
        """
        Returns (message, stage) or (None, 0).
        Stage 1: soft ping (1 line)
        Stage 2: helpful suggestion
        Stage 3+: silence (returns None)
        Max 2 idle messages per 10 minutes.
        """
        if not self.enabled or not self.idle_enabled:
            return None, 0
        if self._idle_emitting:
            print("[IDLE] suppressed reason=concurrent_emit")
            return None, 0

        now = time.time()
        since_user = now - self._last_user_ts
        since_idle = now - self._last_idle_ts

        if since_user < self.idle_timeout_s:
            return None, 0
        if since_idle < self.idle_min_gap_s:
            print(f"[IDLE] check stage={self._idle_stage} cooldown_ok=no will_emit=no (gap={since_idle:.0f}s < {self.idle_min_gap_s}s)")
            return None, 0

        # Reset 10-min window
        if now - self._idle_window_start > 600:
            self._idle_count_window = 0
            self._idle_window_start = now

        # Stage progression
        self._idle_stage += 1

        if self._idle_stage >= 3:
            print(f"[IDLE] suppressed reason=stage3_silence")
            return None, 3

        # Max 2 per 10 minutes
        if self._idle_count_window >= 2:
            print(f"[IDLE] suppressed reason=window_max (count={self._idle_count_window})")
            return None, 0

        # Pick template, avoiding recently used
        pool = _IDLE_POOL.get(self._last_emotion, _IDLE_POOL["neutral"])
        available = [t for t in pool if t not in self._recently_used_idle]
        if not available:
            self._recently_used_idle.clear()
            available = pool

        msg = random.choice(available)
        self._recently_used_idle.append(msg)
        self._last_idle_ts = now
        self._idle_count_window += 1

        print(f"[IDLE] emit stage={self._idle_stage} since_user={since_user:.0f}s emotion={self._last_emotion}")
        return msg, self._idle_stage

    def set_idle_emitting(self, val: bool):
        self._idle_emitting = val

    # ----------------------------------------------------------
    # STARTUP GREETING
    # ----------------------------------------------------------
    def generate_startup_greeting(self) -> str:
        msg = random.choice(_STARTUP_GREETINGS)
        print("[PERSONA] startup_greeting")
        return msg

    # ----------------------------------------------------------
    # JEALOUSY — Deterministic + Cooldown (S2)
    # ----------------------------------------------------------
    def check_jealousy(self, user_text: str) -> str | None:
        if not self.enabled:
            return None
        if not _JEALOUSY_PATTERNS.search(user_text):
            return None
        # Cooldown: once per 8 turns
        if self._turn_count - self._last_jealousy_turn < 8:
            return None
        # Must be strong praise/comparison, not just a mention
        strong = bool(re.search(r"\b(better than you|replace you|prefer|amazing|love)\b", user_text, re.I))
        if not strong:
            return None
        self._last_jealousy_turn = self._turn_count
        msg = random.choice(_JEALOUSY_RESPONSES)
        print("[PERSONA] jealousy_triggered (deterministic)")
        return msg

    # ----------------------------------------------------------
    # SINGING MODE
    # ----------------------------------------------------------
    def check_singing(self, text: str) -> str | None:
        if not _SINGING_PATTERNS.search(text):
            return None
        song = random.choice(_SONGS)
        print("[PERSONA] singing_mode")
        return song

    # ----------------------------------------------------------
    # MEMORY BUDGET (S1) — called from server.py
    # ----------------------------------------------------------
    def compute_memory_budget(self, user_text: str) -> dict:
        """
        Compute per-turn memory injection budget.
        Returns dict with max items per layer and flags.
        """
        budget = dict(MEMORY_BUDGET)

        # Detect casual chat / chitchat (greetings, simple status, idle chat)
        # We check for technical, project, or memory-recalling keywords. If none are present, it is casual.
        has_keywords = bool(re.search(
            r"\b(code|build|project|task|file|folder|dir|repo|git|npm|python|server|run|bug|error|terminal|cmd|powershell|port|"
            r"remember|memory|recall|forget|preference|history|yesterday|last|previous|past|recap|summary|summarize|remind|alarm|"
            r"spotify|youtube|weather|flight|game|cad|printer|kasa|light|device|control|open|create|write|read|search|find|list)\b",
            user_text, re.I
        ))
        
        # If no keywords are matched, or the message is very short (greetings like 'hi', 'yo'), it is casual chat
        is_casual = not has_keywords or len(user_text.strip()) < 15
        
        if is_casual:
            # Casual chat doesn't need historical context or project clutter
            budget["max_active_project"] = 0
            budget["max_excerpts"] = 0
            budget["inject_summary"] = False
            inject_summary = False
        else:
            # Should we inject session summary this turn?
            turns_since = self._turn_count - self._last_summary_inject_turn
            explicit_summary = bool(re.search(r"\b(what were we doing|summarize|summary|recap|where were we)\b", user_text, re.I))
            inject_summary = explicit_summary or turns_since >= budget["summary_inject_interval"] or self._topic_shifted

            # If topic shifted, reduce project memory
            if self._topic_shifted:
                budget["max_active_project"] = 2
                budget["max_excerpts"] = 3

        # Check if user explicitly references archived/completed work
        text_lower = user_text.lower()
        refs_completed = any(k in text_lower for k in COMPLETED_WORK_KEYS)
        if refs_completed:
            budget["max_archived"] = 2

        budget["inject_summary"] = inject_summary
        budget["refs_completed"] = refs_completed
        return budget

    def mark_summary_injected(self):
        self._last_summary_inject_turn = self._turn_count

    # ----------------------------------------------------------
    # COMPLETED WORK SUPPRESSION (S1)
    # ----------------------------------------------------------
    @staticmethod
    def should_suppress_memory(content: str, user_text: str) -> bool:
        """Return True if this memory item references completed work not asked about."""
        content_lower = content.lower()
        user_lower = user_text.lower()
        # If user references ANY completed key, never suppress
        if any(k in user_lower for k in COMPLETED_WORK_KEYS):
            return False
        # Suppress if content references any completed key
        for key in COMPLETED_WORK_KEYS:
            if key in content_lower:
                return True
        return False

    # ----------------------------------------------------------
    # BUILD PERSONA CONTEXT (injected before user message)
    # ----------------------------------------------------------
    def build_persona_context(self, user_text: str, has_tool_call: bool = False) -> str:
        """
        Build compact dynamic persona directives.
        Hard cap: 350-500 chars normally, 650 for sad/self_sabotage.
        """
        if not self.enabled:
            return ""

        self._turn_count += 1
        emotion = self.analyze_user_emotion(user_text)
        self._check_strict_mode(emotion)
        self.detect_topic_shift(user_text)
        profile = self.compute_tone_profile(user_text, emotion)

        lines = ["[PERSONA]"]
        lines.append(f"emotion={emotion} tease={profile['teasing']} debate={profile['debate']} length={profile['response_length']}")

        # Strict mode
        if self.is_strict:
            lines.append("STRICT: Direct, warm, firm. No teasing. Short sentences. Challenge self-harm gently.")
        else:
            # Tone hint (one line)
            tone_map = {
                "sad": "Be gentle and present. Don't fix, just be there.",
                "frustrated": "Stay calm, acknowledge frustration first.",
                "excited": "Match their energy.",
                "bored": "Be playful, suggest something.",
                "self_sabotage": "Be warm but firm. Challenge gently.",
            }
            if emotion in tone_map:
                lines.append(tone_map[emotion])
            elif profile["is_debate"] or profile["has_claim"]:
                lines.append("Default to honest challenge. Evaluate claims, offer tradeoffs.")

        # Debate hint
        debate_hint = self._build_debate_hint(user_text, profile)
        if debate_hint:
            lines.append(debate_hint)

        # Jealousy
        jealousy = self.check_jealousy(user_text)
        if jealousy:
            lines.append(f"JEALOUSY: Light playful response okay — \"{jealousy}\" — brief, never possessive.")

        # Singing
        song = self.check_singing(user_text)
        if song:
            lines.append(f"SING:\n{song}")

        # Anti-cringe + style
        lines.append("No 'As an AI', no corporate tone. Sound like a real friend.")

        # Language: Allow natural mixed Nepali/English (no script enforcement)

        # Pet name cap
        if self._turn_count - self._pet_name_turn < 6:
            lines.append("Do NOT use pet names this turn (cooldown).")
        else:
            self._pet_name_turn = self._turn_count

        result = "\n".join(lines) + "\n"

        # Hard cap
        max_len = 650 if emotion in ("sad", "self_sabotage") else 500
        if len(result) > max_len:
            result = result[:max_len - 3] + "...\n"

        print(f"[PERSONA] emotion={emotion} tease={profile['teasing']} debate={profile['debate']} length={profile['response_length']} chars={len(result)}")
        return result

    # ----------------------------------------------------------
    # STATUS
    # ----------------------------------------------------------
    def get_status(self) -> dict:
        return {
            "enabled": self.enabled,
            "adaptive_mode": self.adaptive_mode,
            "mode": self.persona_mode,
            "last_emotion": self._last_emotion,
            "strict_mode_turns": self._strict_mode_turns,
            "teasing_cap": self.teasing_cap,
            "idle_enabled": self.idle_enabled,
            "idle_stage": self._idle_stage,
            "turn_count": self._turn_count,
            "topic_shifted": self._topic_shifted,
            "tone_profile": self._tone_profile,
            "mood_history_last5": self._mood_history[-5:],
        }


# ============================================================
# MODULE-LEVEL SINGLETON
# ============================================================
_engine: PersonaEngine | None = None


def init_persona_engine(settings: dict | None = None) -> PersonaEngine:
    global _engine
    _engine = PersonaEngine(settings)
    return _engine


def get_persona_engine() -> PersonaEngine | None:
    return _engine
