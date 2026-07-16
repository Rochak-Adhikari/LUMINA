# Lumina - Development Rules and Guidelines

Every contribution, whether by a human engineer or an agentic AI assistant, must adhere strictly to these engineering regulations to preserve the system's runtime stability, modular design, and clean architecture.

---

## 1. Documentation & Source of Truth

*   **TRUTH is Authoritative**: The directory [Docs/TRUTH/](file:///E:/AI/LUMINA/Docs/TRUTH/) is the single source of truth for the system's specifications, APIs, and roadmap. If code or other files conflict with these specifications, the spec must be addressed first.
*   **Archive is Historical Only**: The directory [Docs/Archive/](file:///E:/AI/LUMINA/Docs/Archive/) is maintained strictly for historical reference. **Never modify archived documentation.**
*   **Keep Docs Synchronized**: Documentation must be updated concurrently with the codebase. When a feature's behavior changes, the corresponding specifications must be updated in the same pull request or milestone.

---

## 2. Milestone Execution Workflow

*   **Repository Inspection First**: Every milestone must begin with a thorough inspection of the active codebase. Never rely on cache or context history.
*   **Compare Against Specification**: Before designing any change, compare the current repository state directly against the authoritative specification.
*   **Gap Analysis Requirement**: Always produce a Gap Analysis detailing missing components, conflicting designs, and files to be touched before writing any code.
*   **Implementation Plan Requirement**: Compile and present an Implementation Plan detailing the proposed file changes, design choices, and verification plan. Obtain developer approval before starting implementation.
*   **One Milestone at a Time**: Execute work sequentially. Never skip ahead to later milestones or implement speculative features.
*   **Milestone Deliverables**: Every completed milestone must include:
    1.  **Implementation Notes**: A brief description of architectural/design decisions.
    2.  **Walkthrough**: Clickable links to created or edited files and visual validation (if UI changed).
    3.  **Regression Tests**: Test scripts covering the new changes.
    4.  **Documentation Update**: Updates to the relevant files in `Docs/`.

---

## 3. Engineering & Code Guidelines

*   **No Unapproved Architecture Changes**: The core layers (DI, state sandbox, pipeline) are stable. Do not modify the framework or change existing public interfaces without explicit authorization.
*   **No Hidden Refactors**: Do not refactor files or modify styling unless it is directly required by the active task. Keep diffs focused.
*   **Avoid Code Duplication**: Do not copy-paste code blocks. Consolidate shared logic into utility files or services.
*   **Prefer Dependency Injection (DI)**: Always register new managers, engines, or helpers in the DI container in `container.py` and resolve them through accessor interfaces. Avoid global instantiation.
*   **Prefer Event-Driven Communication**: Use the `InProcessEventBus` for upward notifications and decoupling components. Do not call handlers on client loops or server threads directly.
*   **RuntimeFacade as Primary Interface**: All interaction with the backend from startup routers and sockets must go through `RuntimeFacade`. Keep internal sub-systems decoupled.
*   **Extend over Duplicate**: Prefer extending existing classes, models, or engines rather than introducing parallel implementations.

---

## 4. Guidelines for AI Coding Assistants

*   **Ask Before Broad Changes**: AI assistants must query and obtain explicit approval before attempting any workspace-wide changes, large file relocations, or package updates.
*   **No Code Placeholders**: Never write mock or placeholder functions in production files. Write complete, functional implementations.
*   **Informal Companion Pronouns**: When speaking to the user, Lumina must use informal Nepali pronouns (`timi`, `timro`). AI coding assistant agents, however, must communicate with the user using professional, clear English.
