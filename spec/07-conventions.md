# 07 Conventions

These apply to every dev agent and every commit.

## Code

- Python 3.12, with type hints everywhere. pyright runs in strict mode on `packages/`.
- ruff handles formatting and linting (line length 100, rule sets `E,F,I,B,UP,SIM,RUF`).
- Each package has the layout `packages/<name>/src/<module>/`, with `<module>` in snake_case: `accel_core`, `accel_extract`, and so on.
- Keep modules small, with one responsibility. Public functions have docstrings that say what they do, not how.
- Models are Pydantic v2 with `model_config = ConfigDict(extra="forbid", frozen=True)` unless they need to be mutable. Every contract model has `schema_version: int`.
- Errors subclass `accel_core.errors.AccelError`, and each carries a stable `code` that the CLI maps to an exit code.
- Use `pathlib.Path`, never raw path strings. Write JSON with `indent=2` and sorted keys, so diffs stay small.
- Logging uses stdlib `logging`, with `accel.<package>` loggers. Never log secrets, tokens, file contents from target repos, or personal data.
- Use `subprocess.run([...], check=True)`, never `shell=True`. Run external tools (git, gitleaks, REA, Playwright) through wrappers in `accel_core.tools` so tests can fake them.
- Shell scripts use bash with `set -euo pipefail` and must be shellcheck-clean. They target macOS (bash 3.2 and zsh users) and Linux.

## Tests

- pytest. Tests live in `tests/<package>/`, and shared fixtures in `tests/fixtures/`.
- Unit tests make no network calls and need no external tools. Use the fakes in `accel_core.testing` for the gateway, REA, Copilot CLI and git.
- Live tests are marked with `@pytest.mark.live_azure`, `live_copilot`, `live_rea`, `live_ghidra` or `live_work_repos`, and are skipped unless enabled with `make test-live NEEDS=...`.
- Golden files: outputs such as knowledge models, `ui-spec.json` and Copilot assets are compared to `tests/golden/`. Update them with `make golden`, and review the diff.
- Fixture repos in `tests/fixtures/repos/` are small and synthetic: `fastapi-react-sso` and `native-sdk-sample`. Never commit real company code.
- New code needs at least 80% line coverage, checked per package in CI.

## CLI and MCP

- CLI commands live in `accel_cli/commands/<group>.py`, one Typer app per group. MCP tools live in `accel_mcp/tools/<tool>.py`. Both only call package functions.
- Every command supports `--json` (chapter 05). Error messages say what to do next.

## Git

- `main` is always green. Work happens on `task/T-###-<short-name>`.
- Commit messages: `T-###: <imperative summary>` (72 characters or fewer), an optional body, and the trailer `Agent: claude-code|codex|antigravity`.
- Handoff commits use `T-###: handoff`, and work-in-progress commits use `T-###: wip <what>`. Gokul squash-merges, so WIP commits are fine on branches.
- Never rewrite history on a branch another agent may continue. Don't force-push.
- One task per branch. If you find unrelated work worth doing, add a task to `tasks.yaml` rather than doing it in passing.

## Definition of done (dev tasks)

A task can move to `review` only when:

1. every acceptance criterion in `tasks/tasks.yaml` is met, and HANDOFF.md says how each was verified;
2. `make check` passes;
3. new behavior has tests, and live tests are marked;
4. contracts, schemas and golden files are regenerated if anything changed;
5. the spec matches the code: wording fixes are made, and anything bigger has an ADR;
6. user-facing commands are documented in `docs/` (from phase 3 on);
7. `make handoff-check` passes and the handoff is committed.

## Copilot assets (product)

- `.agent.md`, `.prompt.md`, `.instructions.md` and `SKILL.md` files need valid YAML frontmatter. `accel package --lint` checks the required keys, names that match folders, description length, and that there are no `url`-type MCP servers.
- Write them for Copilot in VS Code. Don't use preview-only features (C4).
- Use a second-person, imperative tone in instructions, and keep them short. Put depth in skill `reference/` files.
