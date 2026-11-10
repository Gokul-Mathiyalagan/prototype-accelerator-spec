# Handoff

- **Updated:** 2026-11-10 16:45 IST
- **Agent:** codex
- **Active task:** T-001 Repo scaffold and quality gates
- **Task status:** in_progress
- **Branch:** task/T-001-scaffold
- **Last commit:** 3f4e053 T-000: Import reviewed specification

## Summary

Git was initialized and the existing specification committed on `main` with Gokul's authorization. T-001 is claimed by Codex; the baseline handoff and skill-mirror checks pass.

## Acceptance criteria

See T-001 in `tasks/tasks.yaml`; implementation has not started.

## State of the active task

T-001 is in progress on its task branch. No remote is configured. Python 3.9 is installed, so uv must provision Python 3.12 for this workspace.

## Next step

1. Create `pyproject.toml` and the nine packages from `spec/01-architecture.md#packages`.
2. Configure quality gates, the AI-endpoint guard, Makefile targets and CI as required by T-001.
3. Verify and record the results, then hand off for review.

## How to verify

```bash
make check
```

This should report 0 errors and "in sync". Until T-001 replaces the Makefile, `make check` runs only the handoff and skill-mirror checks.

## Decisions and assumptions

- Six product decisions are confirmed; see `spec/decisions/ADR-0001` to `ADR-0006`.
- Ten are still open; see `spec/decisions/open-decisions.md`. Their recommendations are the working defaults until Gokul decides.

## Spec changes

None.

## Open questions for Gokul

- The open decisions in `spec/decisions/open-decisions.md`.

## Watch out

- Developing with Claude Code, Codex or Antigravity doesn't change the product's runtime constraint: product code calls only Azure OpenAI, and the generated assets target GitHub Copilot.
- Tasks with `needs` (azure, copilot, rea, ghidra, work-repos) can only be fully verified where those exist. Build and unit-test everything else, and mark the live tests.
