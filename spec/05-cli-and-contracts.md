# 05 CLI and contracts

## CLI conventions

- Every command supports `--json`, which prints one JSON object to stdout and logs to stderr. Copilot reads this output, so keep its shape stable.
- Exit codes: `0` ok, `1` checks or validation failed, `2` usage error, `3` a prerequisite is missing (REA, Azure config, Copilot CLI), `4` an external call failed (git, network, Azure, REA).
- Commands are idempotent where possible, and re-running resumes from files on disk.
- Long-running commands print progress to stderr and write their results to files. They never only print results.

## Commands

| Command | Does | Writes | Phase |
|---|---|---|---|
| `accel setup [--check] [--json] [component...]` | Wraps `setup/install.sh` | `~/.accel/` | 0 |
| `accel doctor` | Readiness of REA and Ghidra, the Azure deployment, Copilot CLI, and `uv` and `git` | (nothing) | 0 |
| `accel extract prepare <git-url> [--ref <sha>] [--no-runtime]` | Stages 1 to 5 | `work/`, `knowledge/<repo>/` partial, `extract-plan.md` | 1 |
| `accel extract verify <repo>` | Stages 7 and 8 | `knowledge/<repo>/` | 1 |
| `accel extract --batch <git-url> [--ref] [--playbooks a,b]` | All stages without Copilot | `knowledge/<repo>/` | 1 |
| `accel extract merge <repo>...` | Multi-repo consensus | `knowledge/_merged/` | 5 |
| `accel skills build --from knowledge/ [--only <skill>]` | Plan, write, generalize, validate, then open PRs | registry PRs, `build/skills/` | 2 |
| `accel skills eval [--changed] [--skill <name>]` | Copilot CLI eval runs and grading | `evals/reports/` | 4 |
| `accel skills sync` | Copies a project's skills from the registry | `.github/skills/`, `skills.lock` | 2 |
| `accel package [--lint]` | Builds Copilot assets, or lints them | `dist/` | 2 |
| `accel init --blueprint <name> <dir>` | Scaffolds a project | the project | 3 |
| `accel intake` | Interactive questions, then `brief.md` | `aisdlc/01-intake/` | 3 |
| `accel design import --html <path>` | Wireframe intake | `aisdlc/03-design/` | 3 |
| `accel design mock` | HTML mocks from `ui-spec.json` | `aisdlc/03-design/mocks/` | 3 |
| `accel contract draft` | OpenAPI from data needs | `aisdlc/04-contract/` | 3 |
| `accel plan` | Tasks tagged with skills | `aisdlc/05-plan/tasks.yaml` | 3 |
| `accel task next \| status \| complete <id>` | The CLI side of `accel-mcp`'s task tools | `tasks.yaml` | 3 |
| `accel check --level <level> [--scope <path>]` | Maturity checks | check report | 3 |
| `accel gate <name> --approve \| --request` | Gate records | `aisdlc/gates/` | 3 |

## Contracts

Each contract is a Pydantic model in `accel_core.contracts` with a `schema_version`. `make schemas` writes `schemas/<name>.schema.json`, and CI fails if the committed schemas drift from the models. The examples below are illustrative.

| Contract | Written by | Read by |
|---|---|---|
| `finding` | investigator (Copilot or batch), via `submit_finding` | verify, skills planner |
| `playbook` | platform team | extract prepare, investigator |
| `catalog-entry` | platform team | skills planner |
| `knowledge-manifest` | extract | skills, workbench |
| `extract-plan` | extract prepare (markdown with a YAML header) | investigator |
| `install-check` | `install.sh --check --json` | `/accel-setup`, `accel doctor` |
| `versions-lock` | platform team | `install.sh` |
| `skills-lock` | `accel skills sync` | projects, `accel check` |
| `provenance` | skills writer | registry review |
| `eval-case`, `eval-report` | evals | registry release |
| `ui-spec` | design import | mocks, contract, plan, verify |
| `project` | `accel init` | everything in Engine 3 |
| `task` | `accel plan` | `accel-mcp`, `accel task` |
| `gate-record` | `accel gate` | `project_status`, release |

### Finding

One line of `findings.jsonl`:

```json
{
  "schema_version": 1,
  "id": "auth-sso.token-validation",
  "playbook": "auth-sso",
  "claim": "Access tokens are validated in one middleware against the identity provider's signing keys.",
  "evidence": [
    {"kind": "static", "repo": "repo-a", "path": "service/auth/middleware.py", "line": 42, "commit": "9f3c2e1"},
    {"kind": "runtime", "source": "har", "entry": 17, "note": "401, then redirect to the identity provider"}
  ],
  "confidence": "high",
  "unknowns": ["How refresh tokens are rotated"],
  "feeds_skills": ["sso-auth"],
  "recorded_by": "copilot:gpt-6.1-sol"
}
```

Rules: `evidence` must not be empty. A static evidence path must exist in `work/<repo>@<sha>/`, with `line` within the file. `confidence` is `low`, `medium` or `high`. `id` is `<playbook>.<slug>` and is unique per repo.

### Playbook

```yaml
schema_version: 1
id: auth-sso
questions:
  - How does a user sign in, end to end? Name every hop.
  - Where are tokens validated, refreshed and stored?
  - How are identity provider groups mapped to app roles?
evidence: [static, runtime]
tools: [code_graph, read_file, rea]
include_when: {inventory: [auth_library_or_middleware]}
budget: {max_turns: 40, max_cost_usd: 5}     # cost applies in batch mode
output: finding
feeds: [sso-auth, authorization-rbac]
```

### Catalog entry

```yaml
- skill: sso-auth
  group: security
  nature: [standard, generator]
  emit_when: {playbook: auth-sso, min_confidence: medium}
  owner: security-iam
  checks: [semgrep, verify_auth.sh]
```

### UI spec

```json
{
  "schema_version": 1,
  "source": {"kind": "html", "path": "aisdlc/03-design/wireframes/team-dashboard.html"},
  "screens": [{
    "id": "team-dashboard",
    "route": "/teams/:id",
    "pattern": "dashboard",
    "regions": ["header", "filters", "kpis", "table"],
    "components": [{"wireframe": "table#members", "maps_to": "DataTable", "confidence": 0.92}],
    "data": [{"entity": "TeamMember", "fields": ["name", "role", "start_date"]}],
    "actions": [{"label": "Export", "kind": "download"}],
    "states": ["loading", "empty", "error", "no-access"],
    "open_questions": ["Can managers export other teams?"],
    "screenshots": {"desktop": "screenshots/team-dashboard.desktop.png", "mobile": "screenshots/team-dashboard.mobile.png"}
  }]
}
```

### Task (a project's `tasks.yaml`)

```yaml
- id: T-014
  title: Team dashboard screen
  depends_on: [T-009]
  skills: [ui-page-patterns, ui-components, ui-data-and-state]
  inputs:
    - aisdlc/03-design/ui-spec.json#team-dashboard
    - aisdlc/04-contract/openapi.yaml#getTeamMembers
  acceptance: [aisdlc/02-requirements/acceptance/team-dashboard.feature]
  done_when: ["accel check --level prototype --scope web/teams"]
  status: ready            # ready | claimed | in_review | done | blocked
  claimed_by: null
  claimed_at: null
  branch: null
  pr: null
```

This is the **product's** task contract for generated projects. It's separate from this repo's own `tasks/tasks.yaml`, which tracks the build of the platform.

### Gate record

```yaml
schema_version: 1
gate: design            # spec | design | plan | review | release
level: mock
approved_by: "@designer"
approved_at: 2026-12-04T09:30:00+05:30
commit: 1a2b3c4
artifacts:
  - {path: aisdlc/03-design/ui-spec.json, sha256: <hash>}
  - {path: aisdlc/03-design/mocks/, sha256: <hash of tree>}
notes: Approved with two open questions moved to decisions/.
```
