# 01 Architecture

## Three engines

```text
            ┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
 git URL ──▶│ 1 Repo Intelligence  │──▶│ 2 Skill Factory      │──▶│ 3 AISDLC Workbench   │──▶ project
            │ accel-extract        │   │ accel-skills         │   │ accel-sdlc           │
            │ static + REA + agent │   │ accel-package        │   │ accel-design         │
            │ → knowledge/<repo>/  │   │ accel-evals          │   │ accel-mcp            │
            └──────────────────────┘   │ → accel-registry     │   │ → aisdlc/ + code     │
                       ▲               └──────────────────────┘   └──────────┬───────────┘
                       └────────────── corrections and check failures ◀──────┘
```

Every engine reads and writes files with JSON Schema contracts (chapter 05). Nothing passes state through memory or a database that the next step can't read from disk.

## Packages

The platform is a uv workspace. Each package uses a `src/` layout and lives in `packages/<name>/`.

| Package | Responsibility | May import |
|---|---|---|
| `accel-core` | Contract models, config, errors, the Azure OpenAI gateway, redaction, audit log, file and git helpers | (nothing internal) |
| `accel-extract` | Engine 1: acquire, inventory, static graph, runtime capture, REA wrapper, playbooks, extract plan, batch investigator, verify, knowledge model | core |
| `accel-skills` | Engine 2: catalog, planner, writer, generalizer, check and eval generators, validator, registry PRs | core |
| `accel-package` | Copilot layout (skills, agents, prompts, AGENTS.md fragments), `skills sync`, `skills.lock`, asset lint | core, skills |
| `accel-design` | HTML wireframe intake, `ui-spec.json`, HTML mocks, visual diff | core |
| `accel-sdlc` | Engine 3: phases, gates, task state machine, maturity checks, blueprints and scaffolder, intake and plan | core, design, package |
| `accel-evals` | With and without skill eval harness on Copilot CLI, grading through the gateway, reports | core, package |
| `accel-mcp` | Local stdio MCP server exposing the workflow and code-graph tools | core, extract, sdlc |
| `accel-cli` | The `accel` command (Typer), a thin layer over the other packages | all |

Rules:

- Imports go one way only, as listed. CI checks this with `import-linter`, configured in T-001.
- Only `accel_core.gateway` may import the `openai` package, and only its `AzureOpenAI` and `AsyncAzureOpenAI` clients (C1).
- CLI commands and MCP tools are thin wrappers. Logic lives in the packages, so the CLI, MCP and tests all call the same functions.

## Platform repo layout

```text
prototype-accelerator/
├── AGENTS.md  CLAUDE.md          # dev-agent instructions (this build)
├── spec/  tasks/  handoff/       # spec, task list, handoff state
├── .agents/skills/               # dev-agent skills (Codex, Antigravity)
├── .claude/skills/               # generated mirror for Claude Code
├── pyproject.toml  uv.lock  Makefile  accel.toml.example
├── .github/
│   ├── workflows/ci.yml          # make check, schema drift, AI-endpoint guard
│   ├── agents/                   # product: accel-setup, investigator
│   ├── prompts/                  # product: accel-setup, accel-extract
│   ├── skills/rea-setup/         # product: REA setup troubleshooting
│   └── copilot-instructions.md   # product: Copilot users of this repo
├── .vscode/mcp.json              # product: rea and accel servers, portable paths
├── setup/                        # versions.lock, install.sh, rea-mcp.sh
├── packages/                     # the nine packages above
├── playbooks/                    # investigation playbooks (YAML + prompt)
├── catalog/taxonomy.yaml         # the 35-skill catalog and emission rules
├── blueprints/internal-data-app/ # project template
├── wireframe-kit/                # HTML starter for wireframe authors
├── schemas/                      # generated JSON Schemas
├── tests/  tests/fixtures/       # tests, sample repos, golden outputs
├── work/                         # cloned target repos (gitignored)
├── knowledge/                    # extraction output (gitignored until reviewed)
└── docs/                         # user docs (onboarding guide, phase 5)
```

The `.github/` and `.vscode/` folders hold **product** assets that the platform's users run in Copilot. They aren't instructions for the dev agents, which use `AGENTS.md` and `.agents/`.

The registry is a separate repo:

```text
accel-registry/
├── CODEOWNERS
├── standards/          # brand tokens, API style guide, auth policy (inputs owned by teams)
├── skills/<name>/      # approved skills
├── wireframe-kit/      # published copy of the starter
└── dist/               # Copilot skill folders; portable .agents/skills/ for later
```

## Runtime data layout

| Path | Contents |
|---|---|
| `~/.accel/tools/` | Node, JDK 21, Ghidra 12.1.4 and REA, installed by `/accel-setup` |
| `~/.accel/rea.env` | `GHIDRA_INSTALL_DIR`, `JAVA_HOME` and the Ghidra timeouts |
| `~/.accel/cache/` | REA and Ghidra results cached by file SHA-256 |
| `~/.accel/audit/` | Audit log, as JSON lines per day |
| `work/<repo>@<sha>/` | Redacted clone of a target repo |
| `knowledge/<repo>/` | Knowledge model (chapter 02) |
| `<project>/aisdlc/` | AISDLC state for a project (chapter 04) |

## Configuration

`accel.toml` in the platform repo root (with an example committed as `accel.toml.example`), overridden by environment variables:

| Setting | Env var | Default |
|---|---|---|
| Azure OpenAI endpoint | `AZURE_OPENAI_ENDPOINT` | none (required for batch mode, the skill writer and grading) |
| API key | `AZURE_OPENAI_API_KEY` | none (required with the endpoint). Environment or gitignored `.env` only, never `accel.toml` (ADR-0008) |
| Deployment | `AZURE_OPENAI_DEPLOYMENT_NAME` | `gpt-6.1-sol` |
| API version | `OPENAI_API_VERSION` | pinned in `accel.toml.example` |
| Token prices | (`accel.toml` only: `input_usd_per_mtok`, `output_usd_per_mtok`) | none; cost budgets need both set |
| Accel home | `ACCEL_HOME` | `~/.accel` |
| Download mirror | `ACCEL_MIRROR` | none (direct downloads) |
| Registry | `ACCEL_REGISTRY` | git URL of `accel-registry` |
| Monthly eval credit budget | `ACCEL_EVAL_CREDIT_BUDGET` | set per team |

## Tech stack

| Area | Choice |
|---|---|
| Language | Python 3.12, uv workspace |
| CLI and models | Typer; Pydantic v2 with JSON Schema export |
| Source parsing | tree-sitter (Python, TypeScript and JavaScript grammars) |
| Code graph | SQLite, one file per repo |
| Runtime evidence | REA at a pinned commit, Node as pinned by REA, Ghidra 12.1.4, JDK 21 |
| Browser automation | Playwright with Chromium |
| Model access | `openai` package's `AzureOpenAI` client, with API key auth |
| MCP | Official MCP Python SDK: the stdio server for `accel-mcp`, and the client for REA in batch mode |
| Checks | ESLint, Stylelint, Spectral, Semgrep, gitleaks, axe-core |
| Mock backends | Prism for OpenAPI, REA environments for HAR |
| Workbench (phase 5) | FastAPI, React, Postgres |
| Telemetry | OpenTelemetry |
| Dev quality | ruff, pyright (strict), pytest, import-linter, shellcheck, pre-commit |
