# PHASE 5.4 EXECUTION RULES

These rules are mandatory for every implementation session.
# Engineering Rules

Before reading any file:

1. Check VERIFICATION_CACHE.md.

2. If the file exists there AND
   SHA matches
   AND session has not invalidated it

DO NOT READ IT AGAIN.

Use cached knowledge.

Only reread if:

- modified
- user explicitly requested
- dependency changed
- implementation depends on new code

Every reread must explain WHY.
---

## 1. DO NOT RE-DISCOVER THE ARCHITECTURE

The architecture has already been documented.

Treat these documents as the source of truth.

docs/architecture/

Never re-read the entire repository unless explicitly requested.

---

## 2. READ ONLY WHAT IS REQUIRED

Before modifying code, read ONLY:

• files being modified
• directly dependent interfaces
• failing tests

Never scan unrelated folders.

Never inspect files outside the implementation scope.

---

## 3. TRUST PREVIOUS VERIFICATION

Unless I explicitly say the repository changed:

DO NOT

- rescan server.py
- reread architecture docs
- reread builtin skill catalog
- reread Truth documents
- rediscover invariants

Assume they are unchanged.

---

## 4. IMPLEMENTATION ORDER

Always follow

docs/architecture/05_IMPLEMENTATION_ROADMAP.md

Never skip ahead.

Never combine multiple roadmap steps.

---

## 5. KEEP COMMITS ATOMIC

One roadmap step

↓

One implementation

↓

One regression

↓

Stop.

Never continue automatically.

---

## 6. NEVER EXPAND SCOPE

Do not perform cleanup.

Do not modernize code.

Do not rename things.

Do not optimize unrelated code.

Only modify files required for the approved step.

---

## 7. MINIMIZE TOKEN USAGE

Assume previous analyses remain valid.

Only verify if

• repository changed

• dependency changed

• implementation requires it

Otherwise continue immediately.

---

## 8. IF SOMETHING IS UNKNOWN

Read ONLY the missing file.

Never restart repository analysis.

---

## 9. BEFORE CODING

Output ONLY

Files to modify

Files intentionally untouched

Dependencies

Risks

If unchanged from previous session, simply state

"No architectural changes detected.
Proceeding with implementation."

---

## 10. AFTER CODING

Only provide

Summary

Files modified

Tests run

Regression result

Commit message

Stop.

# 11. Repository Read Budget

Treat repository reads as expensive operations.

Before opening any file, ask internally:

"Is this file required to implement the current roadmap step?"

If the answer is NO,

do not read it.

If the answer is YES,

read it once.

Never read the same file multiple times during the same implementation session unless it has changed.