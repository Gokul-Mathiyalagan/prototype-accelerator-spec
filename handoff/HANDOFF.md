# Handoff

- **Updated:** 2026-11-10 18:33 IST
- **Agent:** codex
- **Active task:** none
- **Task status:** done
- **Branch:** main
- **Last commit:** a99f8a6 T-001: handoff

## Summary

Merged T-001 into `main` at Gokul's request and marked it done. The existing `task/T-001-scaffold` branch is retained as a backup of the verified implementation. The full check passes with 34 offline tests and 100% line coverage in each scaffold package; no task is active.

## Acceptance criteria

- [x] uv workspace with all nine spec/01 packages, each using src/, py.typed, and a smoke test; `tests/dev/test_workspace.py` passes for every installed package.
- [x] Makefile targets setup, check, test, test-live, schemas, golden, handoff-check, sync-agent-files exist; verified setup, check, schemas, golden, test-live and handoff-check.
- [x] make check runs Ruff, strict Pyright, import-linter, ShellCheck, the AI-endpoint Semgrep guard, and pytest -m 'not live'; passes.
- [x] All five resource markers are registered and skipped by default; `tests/dev/test_live_selection.py` verifies default, offline-only, single-resource and multiple-resource selection.
- [x] The guard rejects the planted anthropic import with exit code 1 and passes the real tree; `tests/dev/test_ai_guard.py` covers SDKs, gateway boundaries, hosts, MCP configs, skill templates and JavaScript clients.
- [x] `.github/workflows/ci.yml` runs make check on push and pull_request; remote CI execution awaits a configured Git remote.
- [x] .gitignore covers work/, knowledge/, .venv, build outputs, coverage artifacts and local configuration.

## State of the active task

T-001 is done. T-002 is the next eligible task and has not been claimed.

- `pyproject.toml`, `uv.lock` and `packages/*`: Python 3.12 workspace, Hatchling builds, explicit internal dependencies.
- `scripts/dev.py` and `Makefile`: shared target implementation, per-package coverage enforcement and live-resource opt-in.
- `.importlinter`, `.semgrep/ai-endpoints.yml`, `.pre-commit-config.yaml` and `.github/workflows/ci.yml`: quality policies, installed local hooks and CI.
- `tests/dev/`: 34 passing tests. Existing handoff/sync scripts received lint-only cleanup. Shared skill sources and their mirrors are unchanged.

## Next step

1. Follow the start-session skill on `main`; read T-002 in `tasks/tasks.yaml`, `AGENTS.md` and `tasks/README.md`.
2. Create `task/T-002-handoff-tooling` from `main`, set T-002 in_progress with an owner, and commit `T-002: claim`.
3. Add the validation-rule tests in `tests/dev/` specified by T-002; verify handoff hooks, CI failures and skill-mirror enforcement.

## How to verify

```powershell
uv sync --locked --all-packages
uv run make check
uv run make handoff-check
```

Without Make: `uv run --locked --all-packages python scripts/dev.py check`.
Expected: 34 tests pass; every package has 100% scaffold coverage; 8 import contracts kept; no model-guard findings; 0 handoff errors/warnings; skills in sync.

## Decisions and assumptions

- Used existing GitHub Desktop Git rather than installing Git globally; no remote is configured.
- The requested local merge was a fast-forward; the task branch remains at a99f8a6 as the backup.
- uv provisions Python 3.12.13 independently of the installed Anaconda Python 3.9.
- Windows gets GNU Make through the locked gnumake development dependency; all platforms share the Python runner.
- schemas reports T-003's pending generator; golden and live targets explicitly report no selected tests until later tasks add them.
- `accel.toml.example` pins API version 2024-10-21; live Azure compatibility belongs to T-004.

## Spec changes

None. No product contracts or decisions changed.

## Open questions for Gokul

No T-001 blockers. Existing product decisions remain in `spec/decisions/open-decisions.md`.

## Watch out

- GitHub Desktop Git is at `C:\Users\sjai1\AppData\Local\GitHubDesktop\app-3.2.0\resources\app\git\cmd\git.exe`; put its directory on the process PATH for Git commands and hook installation.
- ShellCheck is installed and verified; there are no project shell scripts yet (T-005 adds them).
- No Azure, Copilot, REA or Ghidra calls were needed or made. CI is configured but has not run on GitHub.
