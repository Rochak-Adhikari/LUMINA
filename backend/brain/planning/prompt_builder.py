"""
brain/planning/prompt_builder.py — Phase 5.9.10: workspace prompt formatting

Deterministic, read-only formatting of the frozen PromptWorkspaceContext into a
prompt section. Extracted from llm_planner.py (Phase 5.9.9) so the string-building
logic is isolated and independently testable; behavior is byte-identical.

Treats prompt_workspace as opaque: reads ONLY its four List[str] fields
(decisions/notes/tasks/architecture). No object inspection, ids, tags, metadata,
ranking, sorting, truncation, or dedup. Imports nothing from brain.workspace —
duck-typed on the list fields — so no dependency edge into the workspace package.
"""

from __future__ import annotations

from typing import Any, List, Optional

_WS_SECTIONS = (
    ("decisions", "Decisions"),
    ("notes", "Notes"),
    ("tasks", "Tasks"),
    ("architecture", "Architecture"),
)


def format_workspace_context(prompt_workspace: Optional[Any]) -> str:
    """
    Format PromptWorkspaceContext into a deterministic prompt section.

    Empty/absent context and all-empty fields yield "" — the prompt is then
    byte-identical to before Phase 5.9.9 (no injection). Non-empty sections
    preserve insertion order; empty sections are skipped.
    """
    if prompt_workspace is None:
        return ""

    blocks: List[str] = []
    for attr, heading in _WS_SECTIONS:
        items = getattr(prompt_workspace, attr, None) or []
        if not items:
            continue
        lines = "\n".join(f"- {item}" for item in items)
        blocks.append(f"{heading}\n{lines}")

    if not blocks:
        return ""
    return "\nWorkspace Context\n" + "\n\n".join(blocks) + "\n"
