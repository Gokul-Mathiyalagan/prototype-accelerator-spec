# Prototype Accelerator: instructions for coding agents

This repo builds **Prototype Accelerator**, a platform that turns existing codebases into reviewed agent skills and then runs an AI-integrated SDLC (AISDLC) that builds new projects from those skills, a brief and an HTML wireframe.

Three coding agents build it: **Claude Code**, **Codex** and **Antigravity**. Work moves between them, often mid-task, and none of them can see another's chat history. The repo is the only shared memory. Everything below exists so the next agent can continue exactly where you stopped.

## Start of every session

1. Read `handoff/HANDOFF.md`. It names the active task, the branch, and the exact next step.
2. Read that task in `tasks/tasks.yaml`: its goal, acceptance criteria, dependencies and the spec sections it cites.
3. Read only the spec sections the task cites. `spec/README.md` explains the layout.
4. Run `git status`, `git branch --show-current` and `make check`. If the tree is dirty or checks fail and HANDOFF.md doesn't explain why, stop and tell Gokul before changing anything.
5. Tell Gokul in two or three lines what you're about to do.

If HANDOFF.md says there's no active task, pick the first task in `tasks.yaml` whose status is `todo`, whose `depends_on` are all `done`, and whose `needs` your environment can meet. Claim it (see below).

The `start-session` skill walks through this.

## End of every session: the handoff

Do this when you finish a task, when Gokul says "handoff" or "switch", or before your context or usage runs out. Don't wait until you're cut off.

1. Commit everything. Work in progress is fine on a task branch: `T-###: wip <what>`. Never leave uncommitted changes.
2. Update the task in `tasks/tasks.yaml`: `status`, and a one-line `progress` note.
3. Overwrite `handoff/HANDOFF.md` using `handoff/TEMPLATE.md`. Be specific: name files, functions and commands. "Continue the work" is not a next step.
4. Add a session log: `handoff/log/<YYYY-MM-DD>-<agent>-T-###.md`, with what you did, commands you ran and their results, and anything you tried that didn't work.
5. Run `make handoff-check` and fix what it reports.
6. Commit: `T-###: handoff`.
7. Tell Gokul the branch and the next step in one or two sentences.

The `end-session` skill walks through this.

## Hard constraints of the product

These describe the product you're building, not the tools you're building it with. Never break them, even though you may be one of the AI tools named below.

- **Runtime AI services.** The platform's users run it with GitHub Copilot (agent mode in VS Code, and Copilot CLI) and Azure OpenAI (the `gpt-6.1-sol` deployment). Claude Code is also supported, optionally, for `/accel-setup` only (ADR-0009). Product code calls models only through `accel_core.gateway`, which talks only to Azure OpenAI. Don't add Anthropic, OpenAI-direct, Google, or any other model SDK or endpoint to product code. CI enforces this.
- **MCP servers are local stdio only:** REA and `accel-mcp`. No remote or hosted MCP servers.
- **No Copilot cloud agent.** Copilot assets the platform generates target agent mode in VS Code and Copilot CLI only.
- **VS Code preview features are off for the users' org.** Nothing may depend on a preview feature, such as installing skills from a marketplace.
- **Design input is HTML wireframes only.** Figma is out of scope.
- **Secrets and personal data** are redacted before any model or Copilot sees code, HAR files or logs.
- **REA is installed by Copilot** through `/accel-setup` from pinned, checksum-verified versions. Users never install it by hand.

Full detail is in `spec/00-overview.md`.

## How work is organized

- **One task at a time.** Tasks are `T-###` entries in `tasks/tasks.yaml`.
- **Claim a task:** set `status: in_progress` and `owner` to your agent name (`claude-code`, `codex` or `antigravity`), create the branch, and commit `T-###: claim`.
- **Branch:** `task/T-###-<short-name>`, from `main`.
- **Commits:** small and frequent, `T-###: <imperative summary>`, with a trailer line `Agent: <agent>`.
- **Done** means every acceptance criterion is met, `make check` passes, new code has tests, and any spec change is recorded. Then set `status: review`. Gokul reviews, merges and sets `done`.
- **Blocked:** set `status: blocked`, write the reason in `progress`, and explain it in HANDOFF.md.
- **`needs`** lists outside resources a task requires: `azure`, `copilot`, `rea`, `ghidra`, `work-repos`. If you can't reach one, do every part that doesn't need it, mark the rest with `@pytest.mark.live_<need>`, and say so in the handoff.

## Changing the spec

The spec is the contract between sessions and agents, so it never changes silently.

- **Wording fixes** that don't change behavior: edit the spec and mention it in HANDOFF.md.
- **Anything that changes behavior, contracts, constraints or scope:** write `spec/decisions/ADR-####-<slug>.md` with `Status: proposed`, tell Gokul, and don't build on it until it's `accepted`. The `spec-change` skill has the steps.
- **Contracts** are Pydantic models in `packages/accel-core/src/accel_core/contracts/`. `make schemas` regenerates `schemas/*.json`. Change the model, regenerate the schemas, and update fixtures in the same commit.

## Commands

| Command | What it does |
|---|---|
| `make setup` | Installs the uv workspace and pre-commit hooks |
| `make check` | ruff, pyright, shellcheck, and `pytest -m "not live"` |
| `make test` | All offline tests |
| `make schemas` | Regenerates `schemas/*.json` from the contract models |
| `make handoff-check` | Validates `tasks.yaml` and `HANDOFF.md` |
| `make sync-agent-files` | Copies `.agents/skills/` to `.claude/skills/` |

Live tests are marked `live_azure`, `live_copilot`, `live_rea` or `live_ghidra` and are skipped by default. Run them with `make test-live NEEDS=azure`.

Until T-001 replaces it, the Makefile has only `check` (which runs the handoff checks and the skill-mirror check), `handoff-check` and `sync-agent-files`.

## Code conventions

The short version is below; `spec/07-conventions.md` has the rest.

- Python 3.12, uv workspace, one package per folder in `packages/`, `src/` layout.
- ruff for formatting and linting. pyright in strict mode on `packages/`.
- Pydantic v2 for every data contract, and Typer for the CLI.
- Unit tests make no network calls. Use the fixtures in `tests/fixtures/`.
- Errors are typed exceptions from `accel_core.errors`, never bare `Exception`.
- Use `pathlib` for paths and stdlib `logging` for logs. Never log secrets or file contents from target repos.
- Shell scripts: bash, `set -euo pipefail`, shellcheck-clean.
- Copilot assets (`.agent.md`, `.prompt.md`, `SKILL.md`) need valid frontmatter. `accel package lint` checks them once T-209 exists.

## Where things are

| Path | What's there |
|---|---|
| `spec/` | The product spec. Start at `spec/README.md`. |
| `spec/decisions/` | Decision records (ADRs), plus `open-decisions.md` |
| `tasks/tasks.yaml` | Every build task, with status and acceptance criteria |
| `handoff/` | `HANDOFF.md` (current state), `TEMPLATE.md`, `log/` |
| `packages/` | The nine Python packages (created by T-001) |
| `schemas/` | Generated JSON Schemas |
| `setup/` | `/accel-setup` installer, `versions.lock`, `rea-mcp.sh` |
| `playbooks/` | Investigation playbooks |
| `.agents/skills/` | Shared skills for developing this repo (Codex and Antigravity read them here) |
| `.claude/skills/` | Mirror for Claude Code. Generated, so don't edit it. |
| `.github/` | The product's own Copilot assets (agents, prompts, skills) and CI |

## Notes for each agent

- **Claude Code** reads `CLAUDE.md`, which imports this file. Its skills are a generated mirror in `.claude/skills/`, so edit the copy in `.agents/skills/` and run `make sync-agent-files`.
- **Codex** reads this file and the skills in `.agents/skills/`.
- **Antigravity** reads this file and the `.agents/` folder (rules and skills).
- **All three:** don't keep task state in your own memory, notes or plan files outside the repo. If it isn't in git, the next agent can't see it.
