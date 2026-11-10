# ADR-0007: Build with Claude Code, Codex and Antigravity through repo-based handoff

- **Status:** accepted
- **Date:** 2026-11-10
- **Decided by:** gokul
- **Task:** T-000

## Context

Gokul builds the platform with three coding agents and switches between them, sometimes mid-task. None of them can read another's chat history or memory.

## Decision

- The repo is the only shared state. `AGENTS.md` holds the canonical instructions; Codex and Antigravity read it natively, and `CLAUDE.md` imports it for Claude Code.
- Work is split into tasks in `tasks/tasks.yaml`, with one branch per task.
- Every session starts with the `start-session` skill and ends with the `end-session` skill. These rewrite `handoff/HANDOFF.md`, add a session log, and commit.
- Shared dev skills live in `.agents/skills/` (read by Codex and Antigravity) and are mirrored to `.claude/skills/` for Claude Code by `scripts/sync_agent_files.py`.
- Spec changes that alter behavior go through ADRs.
- `scripts/handoff_check.py` validates the task list and the handoff, and CI runs it.

## Alternatives considered

- **A tool's built-in memory or plan files:** not shared across tools.
- **One instruction file per tool, maintained by hand:** these drift apart. One canonical file plus an import is safer.

## Consequences

- Each session pays a small cost at the start and end. That cost is what makes switching tools safe.
- Dev agents mustn't make the product depend on them (C9).

## Affects

- Files: `AGENTS.md`, `CLAUDE.md`, `.agents/`, `handoff/`, `tasks/`, `scripts/`
- Tasks: T-002
