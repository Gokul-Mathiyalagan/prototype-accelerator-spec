# Handoff

- **Updated:** 2026-11-10 18:56 IST
- **Agent:** antigravity
- **Active task:** T-002 Dev handoff tooling in CI
- **Task status:** in_progress
- **Branch:** task/T-002-handoff-tooling
- **Last commit:** 3d5dd1d T-001: handoff

## Summary

Claimed T-002 on branch `task/T-002-handoff-tooling`. The baseline from T-001 is completely green across all 34 offline tests and quality gates. Starting work on handoff validation unit tests in `tests/dev/` and verifying pre-commit and CI hooks.

## Acceptance criteria

- [ ] make handoff-check and make sync-agent-files wrap the two scripts
- [ ] CI fails if .claude/skills/ differs from .agents/skills/ (sync_agent_files.py --check)
- [ ] CI fails if tasks.yaml is invalid (unknown status or need, missing acceptance, unknown dependency, cycle, or a done task with a not-done dependency)
- [ ] A pre-commit hook runs handoff_check.py when tasks/ or handoff/ change
- [ ] Tests in tests/dev/ cover each handoff_check rule with good and bad fixtures

## State of the active task

- `scripts/handoff_check.py`: validates `tasks.yaml`, `HANDOFF.md`, logs, and ADRs.
- `scripts/sync_agent_files.py`: synchronizes `.agents/skills/` to `.claude/skills/` with `--check` option.
- `Makefile` & `scripts/dev.py`: wrap `handoff-check` and `sync-agent-files`.
- `.pre-commit-config.yaml`: has hooks for `handoff-check` and `skill-mirror`.
- `.github/workflows/ci.yml`: runs `make check` which includes both handoff check and sync check.
- `tests/dev/`: tests need to be added to thoroughly test `scripts/handoff_check.py` and `scripts/sync_agent_files.py` validation rules and failure modes.

## Next step

1. Write unit tests in `tests/dev/test_handoff_tooling.py` covering all `handoff_check.py` validation rules (tasks schema, unknown status/needs, missing acceptance, dependencies, cycles, done with not-done dep) with fixtures.
2. Add tests verifying `sync_agent_files.py` detection of drift and check behavior.
3. Verify pre-commit hook file pattern matching and CI execution behavior.

## How to verify

```powershell
uv run python scripts/handoff_check.py
uv run python scripts/dev.py check
```

Expected: all checks and tests pass with 0 errors.

## Decisions and assumptions

- Test fixtures will use temporary directories or in-memory YAML/Markdown representations to avoid mutating actual workspace files during test runs.

## Spec changes

None.

## Open questions for Gokul

None.

## Watch out

- Keep `handoff_check.py` and `sync_agent_files.py` runnable directly and via `dev.py`.
