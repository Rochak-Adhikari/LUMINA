# Lumina V2 Developer Guide

This guide details environment setup, test verification commands, VAD calibration parameters, and conversation guidelines for Lumina developers.

---

## 1. Environment & Setup

Lumina backend relies on a specific Conda environment for environment consistency, audio libraries, and package availability.

### Activate Environment
```bash
conda activate lumina
```

### Verification
```bash
conda info --envs | grep "*"
# Output should confirm: lumina * (active)
```

---

## 2. Test Execution Suite

Lumina includes comprehensive integration tests in `backend/brain/` to verify DI container mappings, EventBus wildcards, configuration healing, and legacy paths.

All tests should be run in the active `lumina` environment from the repository root. Phase test suites live under `backend/tests/`:

```bash
# Run a specific phase suite (example: Phase 7 Skill Creator)
E:\AI\conda_envs\lumina\python.exe -m pytest backend/tests/test_phase_7_step1.py

# Run the full Phase 5 + 6 + 7 regression (694 tests)
E:\AI\conda_envs\lumina\python.exe -m pytest backend/tests/test_phase_5*.py backend/tests/test_phase_6*.py backend/tests/test_phase_7*.py
```

---

## 3. Voice Activity Detection (VAD) Calibration

To prevent audio word clipping, VAD parameters are defined in `backend/settings.json`.

| Parameter | Recommended | Purpose |
|---|---|---|
| `vad_min_speech_ms` | `250` - `350` | Silence duration required to ignore background pops. |
| `vad_silence_stop_ms` | `900` - `1200` | Silence duration before concluding Scepter has finished speaking. Prevents mid-sentence cut-offs. |
| `vad_pre_roll_ms` | `250` | Capture buffer duration prior to speech detection to preserve the first syllable. |
| `vad_post_roll_ms` | `300` | Buffer zone trailing speech detection. |

---

## 4. Companion Language & Nepali Guidelines

Lumina is a conversational companion, not a task scheduler or OS automation script. Her persona must conform to Scepter's custom identity rules.

### Nepali Conversational Directives
- **Colloquial Tone**: Converses in informal, Neplish code-swapped terms.
- **Informal "You"**: Always addresses Scepter (the user) using informal Nepali pronouns (`timi`, `timro`) rather than formal literary terms (`tapai`, `h हजुर`).
- **Nepali Words to Avoid**:
  - Do NOT use `निर्देशन` (direction) -> use `direction` or `suggestion`.
  - Do NOT use `जटिल` (complex) -> use `complex`.
  - Do NOT use `सटीक` (precise) -> use `precise`.
- **Nepali Phrases to Use**:
  - `Timi again YouTube ma bas-na lagyo?`
  - `Mero color settings kacha?`
  - `Bhayo bhayo, kura nagara!`

---

## 5. Core Companion Identity Seeds

Every session is initialized with two seeded identity facts in the memory store:
1. `"Lumina is a private companion made only for Scepter (Rochak Adhikari)."`
2. `"User's preferred name is Scepter. Scepter is Rochak Adhikari (the user)."`

Gemini Live instructions are configured to ensure Lumina always treats Scepter as "you" and never refers to Scepter in the third person.
