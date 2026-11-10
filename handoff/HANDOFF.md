# Handoff

- **Updated:** 2026-11-10 16:45 IST
- **Agent:** none yet (spec created)
- **Active task:** none
- **Task status:** todo
- **Branch:** main
- **Last commit:** spec import

## Summary

The spec, task list and handoff protocol are in place. No code exists yet. The first session starts the build with T-001.

## Acceptance criteria

Not applicable: no task is active.

## State of the active task

No task is active. Phase 0 tasks T-001 to T-008 are `todo`. T-001 has no dependencies.

## Next step

1. Follow the `start-session` skill.
2. Claim **T-001 Repo scaffold and quality gates**: create the branch `task/T-001-scaffold` from `main`, set `status: in_progress` and `owner` in `tasks/tasks.yaml`, and commit `T-001: claim`.
3. Build T-001 as specified in `tasks/tasks.yaml` and `spec/01-architecture.md` (Repository layout) and `spec/07-conventions.md`.

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
