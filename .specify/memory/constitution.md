<!--
    Sync Impact Report:
    - Version change: none -> 1.0.0
    - Summary: Initial constitution established from existing project documentation and refined with user feedback.
    - Added Principles:
        - I. Full-Stack, Service-Oriented Architecture
        - II. Container-First Development
        - III. Pragmatic, Feature-Driven Testing (NON-NEGOTIABLE)
        - IV. Researched, Specification, and Test-Driven Workflow (NON-NEGOTIABLE)
        - V. Simplicity and Readability
    - Templates requiring updates:
        - ✅ .specify/templates/plan-template.md (updated for alignment)
-->
# AI Language Tutor Constitution

## Core Principles

### I. Full-Stack, Service-Oriented Architecture
**Rule**: The project MUST maintain a strict architectural separation between its core components: the `backend` (FastAPI), `frontend` (Next.js), and `validation-ui` (Streamlit).
**Rationale**: This is the foundational structure from `PLANNING.md`, ensuring modularity and independent development.

### II. Container-First Development
**Rule**: All development, testing, and production environments MUST be managed through Docker and Docker Compose.
**Rationale**: The `README.md` and `docker-compose.yml` establish this as the single source of truth for running the application, guaranteeing consistency.

### III. Pragmatic, Feature-Driven Testing (NON-NEGOTIABLE)
**Rule**: Tests must validate real-world usage by focusing on integrated features within the `/tests` directory. The goal is to verify complete user stories and API endpoints, not just isolated functions with mocks.
**Rationale**: This ensures tests provide true confidence that the system works as a whole, prioritizing the validation of real, implemented features.

### IV. Researched, Specification, and Test-Driven Workflow (NON-NEGOTIABLE)
**Rule**: Development MUST follow a structured, research-informed, and test-driven process. The mandatory workflow is:
1.  **`/specify`**: Define the feature's requirements and user stories.
2.  **`/plan`**: Create a technical design. During this phase, developers **MUST** use `mcp_context7_get_library_docs` to research libraries, APIs, and best practices, ensuring the plan is based on current and accurate information.
3.  **`/tasks`**: Break down the plan into actionable steps.
4.  **Write Failing Tests**: Implement tests in the `/tests` directory that validate the feature's requirements. These tests must fail before implementation begins.
5.  **Implement to Pass**: Write the feature code required to make the tests pass. During implementation, developers **SHOULD** reference the up-to-date examples and documentation retrieved via `Context7`.
6.  **Refactor**: Improve the code while ensuring all tests continue to pass.
**Rationale**: This principle ensures that every feature is well-planned, informed by current best practices, and rigorously tested before completion.

### V. Simplicity and Readability
**Rule**: Code should be simple, readable, and self-documenting. To maintain modularity, individual source code files MUST NOT exceed 500 lines.
**Rationale**: This is a direct quote from the "Design Principles" section of your `PLANNING.md`.

## Governance
This Constitution supersedes all other practices and ad-hoc decisions. Amendments require a documented proposal, team review, and an approved migration plan if changes are backward-incompatible.
- **Compliance**: All code reviews MUST verify compliance with the principles outlined in this document.
- **Guidance**: The `.specify/` directory and its templates provide the tooling to enforce and guide development according to this constitution.

**Version**: 1.0.0 | **Ratified**: 2025-09-27 | **Last Amended**: 2025-09-27