# 04 AISDLC Workbench (Engine 3)

AI drafts each artifact from the brief, the wireframe and the skills, and a named person approves it before the next phase starts. Every artifact is a file under `aisdlc/`, so any Copilot session, in VS Code or Copilot CLI, can pick up where another stopped.

## Lifecycle

| # | Phase | AI does | Skills used | People do | Gate |
|---|---|---|---|---|---|
| 1 | Intake | Asks questions, drafts `brief.md` | accel intake, wireframe import | Answer the questions; attach the HTML wireframe | |
| 2 | Requirements | PRD, user stories, acceptance criteria (Gherkin) | requirements-to-spec | | **Gate 1:** product owner approves the spec |
| 3 | Design | `ui-spec.json`, then on-brand HTML mocks with mock data | wireframe-to-ui-spec, ui-mockup, mock-data | | **Gate 2:** design lead approves the screens |
| 4 | Plan | OpenAPI contract, Prism mock server, `tasks.yaml` | api-contract-first, spec-to-plan | | **Gate 3:** tech lead approves the contract and plan |
| 5 | Build | Copilot claims tasks and builds them, one PR each | task-execution plus each task's skills | Pair with Copilot in VS Code, or reassign a task | |
| 6 | Verify | Checks, tests, visual diff, PR review | standards-review, ui-accessibility | | **Gate 4:** a reviewer merges each PR |
| 7 | Release | Readiness report for the next maturity level | release-and-gates | | **Gate 5:** product and tech owners approve each level-up |

Each level-up loops back to Build, with new tasks for the next level.

A gate record is a file in `aisdlc/gates/<gate>-<level>.yaml` (schema `gate-record`) with the approver's GitHub handle, the time, the artifacts approved with their content hashes, and the commit. `accel gate <name> --approve` writes it. `request_gate` asks for it. An artifact that changes after its gate invalidates the gate, and `project_status` reports this.

## Project state: `aisdlc/`

```text
aisdlc/
├── project.yaml                 # blueprint, level, owners, model, adapters
├── skills.lock
├── 01-intake/brief.md
├── 02-requirements/prd.md, stories.yaml, acceptance/*.feature
├── 03-design/wireframes/*.html, ui-spec.json, mocks/, screenshots/
├── 04-contract/openapi.yaml
├── 05-plan/tasks.yaml
├── gates/
└── decisions/                   # decision records from record_decision
```

```yaml
# aisdlc/project.yaml
name: team-insights-app
blueprint: internal-data-app@1.0
level: mock                 # mock | prototype | pilot | production
assistant: github-copilot   # agent mode in VS Code, Copilot CLI
copilot_model: gpt-6.1-sol  # default in agent mode
design_source: html
owners: {product: "@pm", tech: "@tech-lead", design: "@designer"}
adapters:
  auth: mock-idp            # oidc from pilot onward
  data: sample-data         # postgres or databricks-sql from pilot onward
```

## Maturity levels

`accel check --level <level>` runs everything at that level and below.

| Level | What's real | Checks added at this level |
|---|---|---|
| mock | HTML mocks, Prism mock API, mock identity provider, synthetic data | HTML validity, axe-core, mock data has no real-looking personal data, `ui-spec` coverage |
| prototype | Real front end and back end against sample data; mock identity provider | ruff or ESLint, unit tests, Spectral on the contract, contract tests against Prism, visual diff against the wireframe |
| pilot | OIDC SSO, a real data source (read-only), structured logs and traces | Semgrep security rules, gitleaks, auth tests, observability present, dependency audit |
| production | Deployment, CI/CD, runbook | All of the above, with coverage threshold, container scan, and release notes required |

## Tasks

The task contract is in chapter 05. The states are:

```text
ready ──claim──▶ claimed ──complete──▶ in_review ──merge──▶ done
  ▲                 │                        │
  └──expire/reassign┘                        └──changes requested──▶ claimed
any ──▶ blocked (with reason) ──unblock──▶ ready
```

- Claiming sets `claimed_by`, `claimed_at` and the branch `task/<id>-<slug>`. A claim expires after `claim_ttl_hours` (default 8) without commits.
- One task, one branch, one PR. Tasks with no dependency between them can run in parallel in separate VS Code windows.
- The lock lives in `tasks.yaml`, committed to the branch, so two sessions can't silently claim the same task.

## `accel-mcp` tools

`accel-mcp` is a local stdio server (C2) built on the MCP Python SDK. Every tool validates its input and output against the contracts and returns structured errors.

| Tool | Input | Output |
|---|---|---|
| `project_status` | (none) | Current phase, level, open gates, stale gates |
| `get_spec` | `section?` | Requirements and acceptance criteria, whole or one section |
| `get_ui_spec` | `screen_id` | One screen's spec and its wireframe screenshot path |
| `get_contract` | `operation_id` | One OpenAPI operation with its request and response schemas |
| `next_task` | `claimant` | Claims the next ready task, then returns it with its branch name |
| `skills_for_task` | `task_id` | The skills the task is tagged with, and their paths |
| `run_checks` | `scope`, `level` | Check results and failures |
| `complete_task` | `task_id`, `summary`, `pr_url` | Moves the task to `in_review` |
| `record_decision` | `title`, `context`, `decision` | Path of the new file in `aisdlc/decisions/` |
| `request_gate` | `gate` | Who must approve, and what they're approving |
| `query_code_graph` | `repo`, `query` (`symbol`, `callers`, `callees`, `routes`, `components`) | Matching nodes with `path:line` |
| `submit_finding` | a finding | Accepted, or rejected with reasons; appended to `findings.jsonl` |

The last two serve Engine 1's `investigator` agent in the platform repo. Generated projects get the first ten.

## Copilot assets in a generated project

| Asset | Path | Notes |
|---|---|---|
| Always-on rules | `AGENTS.md`, `.github/copilot-instructions.md` | Generated from the skill fragments and the blueprint |
| Path rules | `.github/instructions/web.instructions.md`, `service.instructions.md` | `applyTo` globs |
| Skills | `.github/skills/<name>/` | From `accel skills sync` |
| Custom agents | `.github/agents/{spec-writer,ui-builder,api-builder,reviewer}.agent.md` | Each lists only the tools its role needs |
| Prompt files | `.github/prompts/{accel-intake,accel-plan,accel-next-task,accel-review}.prompt.md` | Slash commands in Copilot Chat |
| MCP | `.vscode/mcp.json` (`servers`) and `.github/mcp.json` (`mcpServers`) | `accel` only, local stdio |
| CI | `.github/workflows/accel-checks.yml` | `accel check` at the project's level |

## HTML wireframe intake (C6)

`accel design import --html <file or folder>`:

1. Render each page with Playwright at desktop (1440 px) and mobile (390 px) widths, and save screenshots.
2. Walk the DOM for regions (header, nav, main, aside), headings, forms and fields (type, label, required), tables and columns, actions (buttons, links) and repeated items (lists, cards).
3. Map each element to an approved component from `ui-components`, for example a `<table>` to `DataTable`. Each mapping gets a confidence score.
4. Infer data needs: each table, list and form becomes an entity with fields, which seeds the API contract.
5. Record what the wireframe doesn't say, such as empty, loading, error and no-access states, as open questions.

### Wireframe conventions

These ship in `wireframe-kit/`. Intake works on any HTML, but maps more reliably when wireframes:

- use landmark elements (`header`, `nav`, `main`, `aside`) and one `h1` per screen;
- give every form field a `label`, and mark required fields with `required`;
- build tables with `th` headers, so columns become entity fields;
- name components with `data-component="DataTable"` and routes with `data-route="/teams/:id"`;
- show other states as sections marked `data-state="empty"`, `loading`, `error` or `no-access`.

An explicit hint always wins, with confidence 1.0. Mappings below 0.6 confidence are listed for the design lead at Gate 2.

At Verify, a Playwright screenshot of each built screen is compared with its wireframe screenshot. The pixel-diff threshold is set per level, so layout drift shows up before review.

## Generated project layout

```text
team-insights-app/
├── AGENTS.md
├── .github/ (copilot-instructions.md, instructions/, skills/, agents/, prompts/, mcp.json, workflows/accel-checks.yml)
├── .vscode/mcp.json
├── aisdlc/
├── web/          # front end from the blueprint
├── service/      # back end from the blueprint
└── tests/
```

The `internal-data-app` blueprint is React with TypeScript for `web/`, FastAPI for `service/`, and Postgres or Databricks SQL behind the data adapter. It also includes a mock identity provider and Prism, wired for mock level.
