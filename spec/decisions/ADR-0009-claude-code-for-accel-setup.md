# ADR-0009: Claude Code can also run /accel-setup

- **Status:** accepted
- **Date:** 2026-11-10
- **Proposed by:** gokul
- **Decided by:** gokul
- **Task:** T-006

## Context

C1 (spec/00) and ADR-0002 say GitHub Copilot is the users' only assistant, and ADR-0002 lists Claude Code as "not approved for the users". T-006 builds `/accel-setup` as Copilot assets only. Gokul wants users to be able to run `/accel-setup` from Claude Code as well.

## Decision

Claude Code is a second, optional assistant for `/accel-setup` (installing and troubleshooting REA). Copilot stays the default and the only assistant for every other workflow. Nothing in the product may require Claude Code (C9).

In the platform repo:

| File | Purpose |
|---|---|
| `.claude/commands/accel-setup.md` | The `/accel-setup [update]` command for Claude Code |
| `.claude/agents/accel-setup.md` | Setup subagent. It may run `setup/install.sh` and the fixes in the `rea-setup` skill, and nothing else. Same rules as the Copilot agent. |
| `.mcp.json` | Registers `rea` (through `setup/rea-mcp.sh`) and `accel` as local stdio servers for Claude Code |

- Both assistants use one troubleshooting guide, `.github/skills/rea-setup/SKILL.md`. Claude Code's agent reads it from there; there's no second copy to drift.
- Product assets go in `.claude/commands/` and `.claude/agents/`, never in `.claude/skills/`, which stays the generated mirror of the dev agents' `.agents/skills/` (T-002).
- C2 still holds: `.mcp.json` lists only local stdio servers, with no `url` fields, and the AI-endpoint guard checks it.
- The model rules don't change: product code calls models only through `accel_core.gateway` (Azure OpenAI). Claude Code is a user's assistant, like Copilot, not something product code calls.

## Alternatives considered

- **Copilot only (ADR-0002 as written).** Gokul wants Claude Code supported too.
- **Claude Code for extraction and generated projects as well.** Out of scope. `/accel-extract` would send redacted target code to a second model provider, and generated projects would need a second asset set. Each needs its own decision.
- **Product skills in `.claude/skills/`.** That would break the dev-skill mirror check, or mix product and dev skills in one folder.

## Consequences

- Users who pick Claude Code need it approved and licensed by their org; Copilot Business doesn't cover it.
- `/accel-setup`'s behavior is described twice (a Copilot prompt and agent, and a Claude Code command and agent), so T-006 tests that both state the same allowed actions.
- Dev agents working in this repo with Claude Code will also see `/accel-setup` and the `.mcp.json` servers. Claude Code asks before starting project MCP servers.

## Affects

- Spec sections: 00 (C1), 02 (setup files), 06 (C2 control); amends ADR-0002
- Tasks: T-006
