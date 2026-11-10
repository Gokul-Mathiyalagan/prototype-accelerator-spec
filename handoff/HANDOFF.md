# Handoff

- **Updated:** 2026-11-10 23:00 IST
- **Agent:** claude-code
- **Active task:** T-006 Setup assets for /accel-setup (Copilot and Claude Code)
- **Task status:** review
- **Branch:** task/T-006-setup-assets
- **Last commit:** 43b8352 T-006: list the checks still pending on macOS

## Summary

The `/accel-setup` assets exist for both GitHub Copilot (VS Code) and Claude Code (ADR-0009), sharing one troubleshooting skill. Every offline criterion is tested; `make check` passes with 370 tests. The two live checks (running `/accel-setup` for real in each assistant on a macOS or Linux laptop) are Gokul's.

## Acceptance criteria

- [x] accel-setup agent may run setup/install.sh and the rea-setup skill's fixes only; its instructions say to stop and ask for anything else (`test_allowed_commands_are_only_the_installer_and_the_skill_fixes`).
- [x] /accel-setup runs check, explains what's missing, installs with approvals, verifies, asks the user to start the rea server, then calls one REA tool (`inspect_analysis_settings`, read-only and needs no target; confirmed in REA 6.8.0's tool list). Order checked by `test_procedure_checks_installs_verifies_then_proves_rea_works`.
- [x] /accel-setup update moves to new pins in versions.lock. The procedure installs only the `wrong_version` components; the container scenario `update-*` bumps the REA pin and checks that only `rea` is flagged and then moved.
- [x] rea-setup skill covers: wrong JAVA_HOME, missing arm64 decompiler, proxy or mirror, Node mismatch, Gatekeeper quarantine, MCP server not starting, registry enforcement. It also covers missing prerequisites, checksum mismatch and Windows.
- [x] .vscode/mcp.json registers rea (via rea-mcp.sh) and accel with ${workspaceFolder} paths only.
- [x] Frontmatter of all assets is valid YAML with name and description.
- [ ] Live check (Gokul, VS Code): on a laptop without REA, /accel-setup reaches a working REA tool call; result recorded in a session log.
- [x] Claude Code (ADR-0009): the command runs the subagent, which has the same allowed actions as the Copilot agent (`test_both_agents_state_exactly_the_same_allowed_actions`) and reads the shared SKILL.md.
- [x] .mcp.json registers rea and accel as local stdio servers with repo-relative paths and no url fields; the AI-endpoint guard covers .mcp.json (`test_claude_code_mcp_config_must_be_local`); nothing is added under .claude/skills/.
- [ ] Live check (Gokul, Claude Code): on a macOS or Linux laptop without REA, /accel-setup reaches a working REA tool call; result recorded in a session log.

## State of the active task

- Copilot: `.github/agents/accel-setup.agent.md`, `.github/prompts/accel-setup.prompt.md`, `.github/skills/rea-setup/SKILL.md`, `.github/copilot-instructions.md`, `.vscode/mcp.json`.
- Claude Code: `.claude/commands/accel-setup.md` (the main session: subagent, then `/mcp`, then the REA call), `.claude/agents/accel-setup.md` (tools: Bash, Read, Grep, Glob), `.mcp.json`.
- `docs/setup.md`: the user guide for both assistants.
- Live-check tooling: `tests/setup/Dockerfile.claude` and `tests/setup/claude-session.sh` (an interactive Claude Code session on Linux; the `accel-claude-home` volume keeps the login and `~/.accel`).
- Tests: `tests/setup/test_setup_assets.py`, a new scenario in `tests/setup/scenarios.sh` (#14), and a new guard test in `tests/dev/test_ai_guard.py`.

## Next step

1. Gokul runs the two live checks, and records the results in a session log. Watch the points under "Watch out".
   - Claude Code, on this Windows machine: run `tests/setup/claude-session.sh` in Git Bash (or, in PowerShell, `docker run -it --rm -v "${PWD}:/workspace:ro" -v accel-claude-home:/home/dev accel-claude-session:latest`). Sign in, approve the `rea` and `accel` project servers, type `/accel-setup`, approve each `bash setup/install.sh` command, run `/mcp` to connect `rea` when asked, and confirm the `inspect_analysis_settings` call. The image is Debian, Node 24.22.1 and Claude Code 2.1.322, running as a non-root user with the repo mounted read-only.
   - Copilot: in VS Code agent mode on a macOS or Linux laptop without `~/.accel`.
2. If both pass, merge `task/T-006-setup-assets` and set T-006 `done`.
3. Push `main`: it has unpushed commits (ADR-0009, the T-007 merge and its done commit).
4. Next eligible tasks: T-108 (playbooks), T-201 (catalog), T-008 if its dependencies are done.

## Pending on macOS

None of this can run on the Windows dev machine. Do it on a Mac (Apple Silicon first, Intel if available) without `~/.accel`, and record the results in a session log.

1. **Copilot live check (T-006):** in VS Code agent mode, run `/accel-setup` and approve each command. Confirm it ends with a working `inspect_analysis_settings` call on the `rea` server (MCP: List Servers, start `rea`). Check that VS Code accepts the agent's `tools` names (`execute`, `read`, `search`, `rea/*`) and the prompt's `agent:` key; adjust them if VS Code reports unknown tools.
2. **Claude Code live check (T-006):** run `/accel-setup` in Claude Code, then `/mcp` to connect `rea`. Check that `.mcp.json`'s relative path (`setup/rea-mcp.sh`) starts the server. The Linux container (`tests/setup/claude-session.sh`) can cover this check on Windows instead.
3. **macOS installer paths (T-005), never run for real:**
   - the darwin downloads: Node `darwin-arm64`/`darwin-x64`, and the Temurin mac tarball with its `Contents/Home` layout (`JAVA_HOME`);
   - the arm64 decompiler build (`make ghidra_opt ARCH_TYPE="-arch arm64" OSDIR=mac_arm_64` in `Ghidra/Features/Decompiler/src/decompile/cpp`, copying `ghidra_opt` to `os/mac_arm_64/decompile`). This was tested only with a fake Makefile, so the source path and output name are assumptions;
   - the `xcode-select -p` prerequisite check;
   - `/bin/bash` 3.2 with BSD `sed`, `awk`, `find` and `shasum` (the script avoids bash 4 features, but has only run on Linux bash 5);
   - `bash setup/install.sh verify` (REA's `verify:ghidra`), which should pass on macOS without the Linux locale workaround;
   - the Gatekeeper fix in the rea-setup skill (`xattr -dr com.apple.quarantine ~/.accel/tools`), if macOS quarantines anything.
4. **Optional (T-007):** `make -C tests/fixtures/repos/native-sdk-sample/vendor/tinymath` builds `libtinymath.dylib`.

## How to verify

```bash
uv run make check   # 370 passed, 1 skipped
```

## Decisions and assumptions

- The setup procedure lives in each agent; the prompt and command only start it. In Claude Code, the subagent installs and verifies, then the main session asks the user to `/mcp` connect and calls REA, because a subagent can't be relied on to see newly connected MCP tools.
- The Claude Code subagent's tools are Bash, Read, Grep and Glob (no Edit or Write), so it physically can't edit files.
- The proof-of-life REA call is `inspect_analysis_settings`, chosen from the real server's 253 tools as read-only with no required input.

## Spec changes

None in this task (ADR-0009 was adopted earlier on `main`).

## Open questions for Gokul

- `make test-live` breaks on Windows without `UV=uv`. Should I add a task to fix the Makefile?

## Watch out

These are things only the live checks can confirm:


- The Copilot agent's `tools` names (`execute`, `read`, `search`, `rea/*`) and the prompt's `agent:` key follow current VS Code docs as I know them. If VS Code reports unknown tools, adjust the names; the instructions don't depend on them.
- `.mcp.json` uses repo-relative paths (`setup/rea-mcp.sh`), assuming Claude Code starts project servers from the project root.
- The `accel` server fails to start until T-110 builds `accel-mcp`; `docs/setup.md` says this is expected.
- This repo now has `.mcp.json`, so Claude Code dev sessions here will offer to start `rea` and `accel`. Declining is fine.
