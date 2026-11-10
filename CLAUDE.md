@AGENTS.md

## Claude Code

- Skills live in `.agents/skills/` and are copied to `.claude/skills/` by `make sync-agent-files` (or `python3 scripts/sync_agent_files.py`). Edit the `.agents/` copy only.
- Before starting a new task, use plan mode, then write the plan into the "State of the active task" section of `handoff/HANDOFF.md` so another agent can follow it.
- Keep task state in the repo, not in auto memory: anything only you remember is lost when Gokul switches to Codex or Antigravity.
