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
| `scripts/` | `handoff_check.py` and `sync_agent_files.py` |

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

1. Put these files at the root of a new git repo and commit them to `main`.
2. Run `python3 scripts/sync_agent_files.py` and `make handoff-check`. Both should pass.
3. Open the repo in any of the three tools, and use the "continue" prompt above. The first task is T-001.
