# Prototype Accelerator

Turns existing codebases into reviewed agent skills, then runs an AI-integrated SDLC in which GitHub Copilot builds new projects from those skills, a brief and an HTML wireframe.

This repo is built with **Claude Code**, **Codex** and **Antigravity**, and you can switch between them at any point. The repo holds all the state, so whichever tool you open next picks up where the last one stopped.

## What's here

| Path | For |
|---|---|
| `AGENTS.md` | Instructions every coding agent follows (Claude Code reads it through `CLAUDE.md`) |
| `spec/` | What to build: overview, architecture, engines, contracts, security, conventions, roadmap, decisions |
| `tasks/tasks.yaml` | Every build task, with acceptance criteria and status |
| `handoff/HANDOFF.md` | Where work stands right now, and the exact next step |
| `handoff/log/` | One log per session |
| `.agents/skills/` | `start-session`, `end-session` and `spec-change` skills (Codex, Antigravity) |
| `.claude/skills/` | The same skills, mirrored for Claude Code |
| `scripts/` | Cross-platform development targets, handoff validation and skill synchronization |
| `packages/` | Nine typed Python packages in one uv workspace |

## Development

Install Git and uv, then run these commands from the repository root. uv provisions Python 3.12 and installs the development tools from `uv.lock`.

```bash
make setup
make check
```

In Windows PowerShell, use the workspace's bundled GNU Make:

```powershell
Set-Location D:\Github\prototype-accelerator-spec
uv sync --locked --all-packages
uv run make setup
uv run make check
```

Every target also works without Make, for example:

```powershell
uv run --locked --all-packages python scripts/dev.py check
uv run --locked --all-packages python scripts/dev.py handoff-check
```

`check` runs Ruff, strict Pyright, import-linter, ShellCheck, the local Semgrep model-endpoint guard, handoff and skill-mirror validation, and offline tests. It enforces at least 80% line coverage for each package. The model guard uses only local rules and disables scan metrics.

`make test` runs offline tests. Resource-marked tests are skipped by default, even with plain `pytest`. Enable only available resources with `make test-live NEEDS=azure` (PowerShell: `uv run make test-live NEEDS=azure`); use a comma-separated list when a test needs several resources.

`make schemas` invokes `scripts/generate_schemas.py` once T-003 supplies the contract models. `make golden` selects golden tests with `--update-golden`; until those tests exist it reports that no tests were selected. CI runs the complete check on pushes and pull requests and rejects schema drift.

## Switching between tools

**To start or continue,** open the repo in any of the three tools and say:

> Continue the Prototype Accelerator build. Follow the start-session skill.

**Before you switch tools, or when a session gets long,** say:

> Hand off now. Follow the end-session skill.

The agent commits its work, updates `tasks/tasks.yaml`, rewrites `handoff/HANDOFF.md`, writes a session log, and runs the checks. Then open the next tool and use the first prompt.

**To check the state yourself:**

```bash
make handoff-check    # validates tasks.yaml, HANDOFF.md, logs and ADRs
cat handoff/HANDOFF.md
```

## Your role

- Review each task that reaches `review`, merge it, and set it to `done` in `tasks/tasks.yaml`.
- Decide the items in `spec/decisions/open-decisions.md`, and accept or reject proposed ADRs.
- Run the live checks that need your work environment (Azure OpenAI, Copilot, the reference repos), and record the results in a session log.

## Getting started

1. Run the development setup and checks above.
2. Read `handoff/HANDOFF.md` for the active task, branch and exact next step.
3. Open the repo in any of the three tools, and use the "continue" prompt above.
