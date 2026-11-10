# 02 Repo Intelligence (Engine 1)

Given a git URL and a commit, Engine 1 produces a **knowledge model** of how the codebase works, with evidence behind every claim. Static analysis says what the code is. REA shows what the running or built app actually does.

## Setup: `/accel-setup` (C5)

Users never install REA by hand. In the platform repo, they run `/accel-setup` in Copilot Chat. Copilot runs the installer, explains each step, applies known fixes, and reports when REA is ready. The user approves each terminal command, but doesn't type any.

### Files

| File | Purpose |
|---|---|
| `setup/versions.lock` | Pinned versions and SHA-256 checksums (format below) |
| `setup/install.sh` | Idempotent installer for macOS and Linux. Installs into `$ACCEL_HOME/tools` without admin rights. |
| `setup/rea-mcp.sh` | Launcher that starts REA's MCP server from `$ACCEL_HOME` |
| `.vscode/mcp.json` | Registers `rea` (through the launcher) and `accel` using `${workspaceFolder}`, so it works on every machine |
| `.github/agents/accel-setup.agent.md` | Setup agent: may run `setup/install.sh` and the fixes in the `rea-setup` skill, and nothing else |
| `.github/prompts/accel-setup.prompt.md` | `/accel-setup [update]` |
| `.github/skills/rea-setup/SKILL.md` | Steps, plus known failures and fixes: wrong `JAVA_HOME`, missing arm64 decompiler, proxy blocks, Node version mismatch, Gatekeeper quarantine |

### `versions.lock`

```yaml
rea:
  repo: https://github.com/morluto/rea
  commit: <40-char sha>          # REA has no tagged releases; move this deliberately
node:
  version: <from REA's .nvmrc at that commit>
  sha256: {darwin-arm64: <sha>, darwin-x64: <sha>, linux-x64: <sha>}
jdk:
  vendor: temurin
  version: 21.<x>
  sha256: {darwin-arm64: <sha>, darwin-x64: <sha>, linux-x64: <sha>}
ghidra:
  version: 12.1.4                # 12.2 needs JDK 25; stay on 12.1
  url: https://github.com/NationalSecurityAgency/ghidra/releases/download/...
  sha256: <sha>
```

### `install.sh` contract

- `install.sh --check --json` prints one JSON object (schema `install-check.schema.json`):
  `{"ok": bool, "platform": "darwin-arm64", "components": [{"name": "jdk", "status": "missing|ok|wrong_version", "detail": "..."}], "next_action": "..."}`
- `install.sh install [component...]` installs what's missing, in order: node, jdk, ghidra, ghidra-arm64-decompiler (Apple Silicon only), rea, env.
- `install.sh verify` runs `npm run verify:ghidra` in the REA checkout with `GHIDRA_INSTALL_DIR` set.
- Every download is verified against `versions.lock`; a mismatch is a hard failure. `ACCEL_MIRROR`, if set, replaces download hosts but not checksums.
- It's idempotent: re-running when everything is installed changes nothing and exits 0.
- Exit codes: 0 ok, 2 missing prerequisite the script can't install (Xcode command-line tools, git), 3 checksum mismatch, 4 download failed, 5 build or verify failed.
- Logs go to `$ACCEL_HOME/logs/install-<timestamp>.log`, and the last 50 lines are printed on failure so Copilot can read them.
- It never uses `sudo`, never edits shell profiles, and never writes outside `$ACCEL_HOME` (except the REA checkout's own build output inside `$ACCEL_HOME/tools/rea`).

### Apple Silicon

Ghidra doesn't ship an arm64 decompiler for macOS. The installer builds it with `make ghidra_opt ARCH_TYPE="-arch arm64" OSDIR=mac_arm_64` in Ghidra's decompiler source folder, and copies the result to `Ghidra/Features/Decompiler/os/mac_arm_64/decompile`. This needs Xcode's command-line tools.

### Launcher and MCP config

```bash
#!/usr/bin/env bash
# setup/rea-mcp.sh: starts the local REA MCP server that /accel-setup installed
set -euo pipefail
ACCEL_HOME="${ACCEL_HOME:-$HOME/.accel}"
set -a; source "$ACCEL_HOME/rea.env"; set +a
exec "$ACCEL_HOME/tools/node/bin/node" "$ACCEL_HOME/tools/rea/scripts/rea.mjs" mcp
```

```json
{
  "servers": {
    "rea":   {"type": "stdio", "command": "bash", "args": ["${workspaceFolder}/setup/rea-mcp.sh"]},
    "accel": {"type": "stdio", "command": "uv", "args": ["run", "--directory", "${workspaceFolder}", "accel-mcp"]}
  }
}
```

`rea.env` sets `GHIDRA_INSTALL_DIR`, `JAVA_HOME`, `REA_GHIDRA_STARTUP_TIMEOUT_MS=900000` (the default of 330 seconds is too short for large binaries) and `REA_GHIDRA_DECOMPILE_TIMEOUT_SECONDS=120` (decompilation is unbounded by default).

## Extraction stages

| # | Stage | Package module | Input | Output |
|---|---|---|---|---|
| 1 | **Acquire.** Clone at a pinned commit into `work/`. Run gitleaks, redact secrets and personal data, and record the license of the repo and of each vendored binary. | `extract.acquire` | git URL, ref | `work/<repo>@<sha>/`, `acquire.json` |
| 2 | **Inventory.** Read manifests for languages, frameworks and versions. Find build, test and CI files, Dockerfiles, infrastructure code, OpenAPI files, environment variables, and native binaries (ELF, PE and Mach-O, detected by magic bytes). | `extract.inventory` | clone | `repo-profile.json`, `native-inventory.json` (partial) |
| 3 | **Static graph.** Parse every file with tree-sitter into symbols, imports and calls. Framework adapters add FastAPI and Express routes, React components and props, SQLAlchemy models, prompt files and LLM client calls. | `extract.static` | clone | `graph.sqlite` |
| 4 | **Build and run** (optional). Build the app in a local container with its own scripts, seed synthetic data, and swap real sign-in for a mock identity provider. If the app can't run, continue with static evidence at lower confidence. | `extract.runtime` | clone | running app URL or `runtime-skipped` |
| 5 | **REA capture.** REA analyzes the built front-end bundle. Playwright walks the main routes while REA observes the UI and records a HAR. The HAR is sanitized and turned into a runnable environment. Native binaries go through REA's Ghidra provider if C8 allows. | `extract.rea`, `extract.runtime` | bundle, app, binaries | screenshots, `har/`, `env/`, REA results |
| 6 | **Investigate.** Run one playbook per domain. Each answer cites evidence and lists what it couldn't determine. | Copilot `investigator` agent, or `extract.investigate` in batch mode | graph, REA, files | `findings.jsonl` |
| 7 | **Verify.** Re-check every cited `path:line` at the commit, match runtime claims to a HAR entry or screenshot, drop unsupported claims, and score confidence. | `extract.verify` | findings | verified `findings.jsonl` |
| 8 | **Write the knowledge model.** | `extract.knowledge` | all of the above | files listed below |

`accel extract prepare <git-url> [--ref]` runs stages 1 to 5 and writes `extract-plan.md`. `accel extract verify <repo>` runs stages 7 and 8.

## Extraction in Copilot: `/accel-extract <git-url>`

The prompt file starts the `investigator` custom agent. Its tools are REA (MCP), `accel-mcp`'s `query_code_graph` and `submit_finding`, file reads, and the terminal.

1. Copilot runs `accel extract prepare <git-url>` and reads the summary.
2. For each unchecked playbook in `knowledge/<repo>/extract-plan.md`, Copilot follows the playbook's questions and evidence rules, then records each answer with `submit_finding`. `submit_finding` rejects findings that fail the schema or cite a missing path or line.
3. Copilot ticks the playbook off in `extract-plan.md`. Progress lives in that file, so a new chat resumes where the last stopped. Users are told to start a fresh chat per playbook, which keeps context small and AI-credit use predictable.
4. When all playbooks are ticked, Copilot runs `accel extract verify <repo>` and summarizes the knowledge model and `unknowns.md`.

`extract-plan.md` format:

```markdown
# Extract plan: <repo> @ <sha>
Prepared: 2026-11-20T10:02Z · runtime: ok · REA: ok · native binaries: 2 (1 licensed for analysis)

- [ ] repo-overview
- [x] ui-architecture  <!-- 14 findings · 2026-11-20 · copilot -->
- [ ] api-surface
...
```

### Batch mode

`accel extract --batch <git-url>` runs all stages without Copilot. Stage 6 is a small agent loop in `extract.investigate` that:

- calls `gpt-6.1-sol` through `accel_core.gateway` (chat completions with tool calling, API key auth);
- offers the same tools: code-graph queries and file reads locally, REA through an MCP client to the local stdio server, and `submit_finding`, whose arguments must match the finding schema;
- enforces each playbook's `budget` (turns and cost), and logs every call to the audit log;
- uses high reasoning effort for investigation and low effort for summarizing.

Batch mode is for re-runs over many repos and scheduled refreshes. Its findings are identical in format to Copilot's.

## Playbooks

Each playbook is `playbooks/<id>.yaml` plus `playbooks/<id>.prompt.md`.

| Playbook | Questions it answers | Evidence | Feeds |
|---|---|---|---|
| repo-overview | Purpose, modules, how to build, test and run | Static | Foundation skills |
| ui-architecture | Routing, app shell, component library, state, data fetching | Static, REA bundle, screenshots | UI skills |
| design-system | Colors, type, spacing and components actually in use | Static, screenshots | ui-design-tokens |
| api-surface | Endpoints, naming, versioning, pagination, errors, validation | Static, HAR | API skills |
| auth-sso | Sign-in end to end, token validation, role mapping | Static, observed redirects | Security skills |
| data-access | Database clients, ORM, migrations, warehouse queries | Static | data-access |
| ai-llm | Model clients and providers, prompts, tools, retrieval, guardrails, evals, cost tracking | Static, HAR for model calls | AI skills |
| backend-architecture | Layering, dependency injection, error handling, background jobs | Static | Backend skills |
| observability | Logging, tracing, metrics | Static, runtime logs | observability |
| delivery | CI/CD, containers, environments | Static | Delivery skills |
| native-artifacts | What each vendored or built binary exports, and which of its functions the code calls | REA Ghidra provider, static | architecture-map, and the skill for the library's domain |

`extract prepare` includes a playbook in `extract-plan.md` only if the inventory gives it something to examine. For example, `native-artifacts` is included only when C8-eligible binaries exist, and `ai-llm` only when LLM client code is found.

## Confidence

- **High:** static and runtime evidence agree, or there are two or more independent occurrences.
- **Medium:** consistent static evidence only.
- **Low:** a single occurrence, or an agent inference.

Anything the agent couldn't establish goes to `unknowns.md` as an open question. Skills are emitted only from findings at the confidence their emission rule requires (chapter 03).

## Knowledge model: `knowledge/<repo>/`

| File | Contents |
|---|---|
| `manifest.json` | Repo, commit, timestamps, stage results, tool versions (schema `knowledge-manifest`) |
| `repo-profile.json` | Languages, frameworks, versions, build and test commands |
| `architecture.md` | Components and what calls what, with a generated Mermaid diagram |
| `graph.sqlite` | The code graph |
| `findings.jsonl` | Every claim, with evidence and confidence |
| `api/openapi.reconstructed.yaml` | The API surface, rebuilt from code and traffic |
| `ui-inventory.json` | Routes, screens with screenshots, components and tokens in use |
| `ai-inventory.json` | Models, prompts, tools, retrieval and guardrails |
| `native-inventory.json` | Native binaries, with hashes, licenses and what Ghidra found |
| `unknowns.md` | What couldn't be determined |
| `extract-plan.md` | The playbook checklist and its progress |
| `env/` | The runnable environment REA built from the HAR |

## Multi-repo merge

`accel extract merge <repo>...` (phase 5) compares findings across two or three reference repos and marks each as **consensus**, **majority** or **divergent**. Divergent findings go to architects as decisions, never straight into skills.

## REA and Ghidra rules

- REA only ever sees redacted clones and sanitized HAR files (C7).
- REA's tool results go to the model: to Copilot during `/accel-extract`, and to Azure OpenAI in batch mode.
- Ghidra runs only on C8-eligible binaries, with the timeouts in `rea.env`. Results are cached by SHA-256 in `~/.accel/cache/`.
- Known REA limits: confident but wrong call paths, context exhaustion on large bundles, and vague results on minified code. Verification (stage 7) is what makes findings trustworthy, so never skip it.
