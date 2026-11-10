---
name: accel-setup
description: Install or update REA for Prototype Accelerator, fix setup problems, and prove REA works.
argument-hint: "[update]"
---

Set up REA for Prototype Accelerator.

1. Use the `accel-setup` subagent, passing it this argument: `$ARGUMENTS` (empty, or `update`). It installs and verifies REA under the rules in `.claude/agents/accel-setup.md`.
2. When it reports success, ask the user to connect the `rea` MCP server: run `/mcp` and connect (or reconnect) `rea`. Wait until they confirm.
3. Call the `inspect_analysis_settings` tool from the `rea` server, then tell the user REA is working and what was installed.

If the subagent stops with an error it couldn't fix, show the user its report and the rea-setup skill section it used (`.github/skills/rea-setup/SKILL.md`). Don't try other fixes.
