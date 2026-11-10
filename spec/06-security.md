# 06 Security, governance and risks

Internal code reaches a model only after secrets and personal data are stripped, and only through the two approved AI services: GitHub Copilot for setup, extraction and coding, and Azure OpenAI for the platform's own calls. No skill reaches a project without its owner's sign-off.

## Controls

| Control | How it's enforced | Task |
|---|---|---|
| **Two approved AI services only (C1)** | All model calls go through `accel_core.gateway` (Azure OpenAI with Entra ID). The CI guard (below) fails on any other model SDK or endpoint. | T-004, T-001 |
| **Local MCP servers only (C2)** | `.vscode/mcp.json` and `.github/mcp.json` list only `rea` and `accel` as stdio servers; `accel package --lint` rejects `url`-type servers | T-006, T-209 |
| **Pinned, verified setup (C5)** | `install.sh` installs only what `versions.lock` lists, checks every SHA-256, uses no `sudo`, and writes only under `~/.accel`. The setup agent may run only the installer and the skill's fixes. | T-005, T-006 |
| **Isolated extraction** | Target repos go into `work/`; apps run in a local container with outbound access limited to package registries | T-101, T-105 |
| **Redaction first (C7)** | gitleaks and personal-data patterns run in stage 1. HAR files lose auth headers, cookies and tokens. Runtime runs use synthetic data. Redaction runs again in the gateway before every model call. | T-101, T-106, T-004 |
| **License check before Ghidra (C8)** | A vendored binary is decompiled only if its license allows it; otherwise it's listed in `unknowns.md` | T-101, T-107 |
| **Skills are code** | CODEOWNERS review, signed release tags, pinned versions in `skills.lock`, and a scan for injected instructions and URLs | T-207, T-208 |
| **Scoped tools** | Each custom agent lists the tools it may use; `accel-mcp` can't write outside the project repo | T-110, T-302 |
| **Locked and default rules** | Security and privacy rules in skills can't be overridden; other rules can, with a decision record | T-310 |
| **Audit trail** | Every setup, extraction run, model call, skill approval and gate approval goes to `~/.accel/audit/` as JSON lines, with who, when and which commit | T-004, T-403 |

## AI-endpoint guard (CI)

A Semgrep rule set in `.semgrep/ai-endpoints.yml`, run by `make check`, fails when product code (`packages/`, `blueprints/`, generated skill templates):

- imports `anthropic`, `google.generativeai`, `google.genai`, `vertexai`, `cohere`, `mistralai`, `litellm`, `langchain_openai`, `langchain_anthropic` or `langchain_google_genai`;
- imports `openai` anywhere except `packages/accel-core/src/accel_core/gateway/`;
- uses `openai.OpenAI(` or `openai.AsyncOpenAI(` (non-Azure clients) anywhere;
- contains the hosts `api.openai.com`, `api.anthropic.com`, `generativelanguage.googleapis.com` or `aiplatform.googleapis.com`;
- configures an MCP server with a `url` field.

The dev agents' own files (`AGENTS.md`, `CLAUDE.md`, `.agents/`, `.claude/`, `spec/`, `tasks/`, `handoff/`) are excluded, since they may name those tools.

## Risks

| Risk | Mitigation |
|---|---|
| REA can't read a source tree directly | Static analysis covers source; REA covers runtime behavior and built artifacts |
| The app won't build or run locally | Static-only mode, with lower confidence flagged on each finding |
| The agent states something untrue | `submit_finding` rejects broken evidence, and verification drops any claim without a valid `path:line` or runtime proof |
| Code, secrets or personal data reach a model | Redaction before extraction, Copilot and Azure OpenAI as the only model endpoints, local MCP servers only |
| Copilot strays from the installer or improvises fixes | The setup agent may run only `setup/install.sh` and the fixes in the `rea-setup` skill, and every other command still needs approval |
| A proxy blocks downloads from GitHub, Adoptium or nodejs.org | `ACCEL_MIRROR` points the installer at an internal artifact store, with the same checksums |
| REA has no tagged releases, so its main branch can change | Pin a commit, and move the pin only after `npm run check:fast` and the Ghidra check pass |
| The org turns on MCP registry enforcement | Add `rea` and `accel` to the registry by server ID during phase 0 |
| Ghidra stalls on a large binary | Startup and decompile timeouts, analysis only of stage 2's flagged binaries, results cached by hash |
| A vendor license forbids reverse engineering | License check in stage 1; the binary is skipped and listed in `unknowns.md` |
| Extraction, coding and evals use up Copilot AI credits | Phase 0 measures credits per playbook; one chat per playbook; batch mode on Azure for re-runs; evals only for changed skills |
| Too many skills, or bloated ones | Emission rules, a 5,000-token cap, usage data to retire unused skills |
| Copilot follows skills differently on different models | Evals on the two or three models people actually pick, re-run when that changes |
| VS Code preview features are off | Skills reach projects through git; nothing depends on a preview feature |
| HTML wireframes leave out states or detail | Intake raises open questions, and the design lead approves at Gate 2 |
| Batch runs get expensive | Per-playbook budgets, caching, re-running only changed domains |
| Dev agents drift from each other's work | Repo-only state, the handoff protocol, `make handoff-check`, and ADRs for spec changes |
