# 03 Skill Factory (Engine 2)

The Skill Factory turns knowledge models into skills a team can trust. Each skill is generalized, checked, approved by a named owner, and tested for lift before it ships. It runs as `accel skills build --from knowledge/`. A person can also start it from Copilot, since the drafting itself calls `gpt-6.1-sol` through the gateway.

## Steps

1. **Plan.** Map findings onto the catalog. A skill is emitted only when its emission rule is met; for example, `sso-auth` needs an `auth-sso` finding at medium confidence or higher. One topic per skill. If `SKILL.md` would go over about 5,000 tokens (estimated as characters ÷ 4), split the skill.
2. **Write.** GPT-6.1 Sol drafts each skill from its findings, using the Jinja templates in `accel_skills/templates/`.
3. **Generalize.** Strip project names, hostnames, secrets and real data. Turn literals into parameters such as `{{service_name}}`. When there are several repos, keep only consensus patterns.
4. **Validate.** Lint the frontmatter and size, run each check against known-good and known-bad fixtures, and scan the skill text for injected instructions and unknown URLs.
5. **Review.** Open one pull request per skill in `accel-registry`. CODEOWNERS assigns the owner, who approves, edits or rejects it. Nothing ships without approval.
6. **Evaluate.** Run the eval prompts in Copilot CLI with and without the skill, and grade each result with GPT-6.1 Sol against the prompt's rubric. Evals run only for new or changed skills, because each run spends Copilot AI credits.
7. **Package.** Publish approved skills from the registry. `accel skills sync` copies the ones a project needs into its `.github/skills/` at pinned versions, recorded in `skills.lock`. Nothing uses the VS Code marketplace (C4).

The owner's review matters most. The factory drafts quickly, but a skill earns trust only when the person who owns that standard signs it off.

## Skill natures

| Nature | What it holds | Example |
|---|---|---|
| Standard | Rules with reasons, plus a check that proves them | api-design |
| Workflow | A step-by-step procedure the agent follows | api-endpoint-scaffold |
| Generator | Templates and scaffold files the agent copies | ui-page-patterns |
| Reference | Knowledge the agent looks up | architecture-map |
| Review | A checklist a reviewing agent applies to a pull request | standards-review |

## Default catalog: 35 skills in 8 groups

There are 27 extracted skills and 8 authored workflow skills. The catalog lives in `catalog/taxonomy.yaml`; this table is its human-readable form.

| Skill | Group | Nature | What it encodes | Emitted when |
|---|---|---|---|---|
| repo-conventions | foundation | Standard | Layout, naming, code style, how to build, test and run | Always |
| architecture-map | foundation | Reference | Components, what calls what, where things live | Always |
| config-and-secrets | foundation | Standard | Env vars, config loading, secret handling | Config found |
| testing-standards | foundation | Standard, Generator | Test layout, fixtures, mocking, coverage | Tests found |
| ui-design-tokens | ui | Standard | Comcast color, type and spacing tokens, and how code uses them | Front end found |
| ui-components | ui | Standard, Generator | Approved components and their prop patterns | Component library found |
| ui-page-patterns | ui | Generator | App shell, dashboard, list and detail, form and chat page templates | Two or more page types found |
| ui-data-and-state | ui | Standard | State management, API client, loading, empty and error states | Front end found |
| ui-accessibility | ui | Standard | Labels, focus order, contrast, keyboard use | Front end found |
| api-design | api | Standard | Naming, versioning, pagination, error envelope, validation | API found |
| api-contract-first | api | Workflow | OpenAPI first, code generation, typed client, Prism mock | API found |
| api-endpoint-scaffold | api | Workflow, Generator | Add an endpoint end to end: route, schema, service, test, docs | API found |
| sso-auth | security | Standard, Generator | Sign-in flow, token validation, mock identity provider for prototypes | Auth finding |
| authorization-rbac | security | Standard | Role mapping, route and data guards | Roles found |
| secure-coding | security | Standard | Input validation, secret handling, OWASP rules | Always (authored baseline) |
| backend-architecture | backend | Standard | Layering, modules, dependency injection, error handling | Backend found |
| data-access | backend | Standard | ORM and SQL patterns, migrations, Postgres, Databricks and Snowflake access, query safety | Database found |
| background-jobs | backend | Standard | Queues, schedulers, retries, idempotency | Jobs found |
| observability | backend | Standard | Structured logs, traces, metrics, correlation IDs | Logging found |
| llm-integration | ai | Standard | Model gateway and provider config, retries, streaming, token and cost tracking | LLM client found |
| prompt-management | ai | Standard | Where prompts live, templating, versioning, prompt tests | Prompt files found |
| agent-tools | ai | Standard, Generator | Agent loop, tool schemas, tool error handling | Agent code found |
| rag-patterns | ai | Standard | Chunking, embeddings, retrieval, citations, index refresh | Retrieval found |
| ai-guardrails | ai | Standard | Personal data, prompt injection, output validation, human approval for actions | LLM client found (authored baseline) |
| ai-evaluation | ai | Workflow | Eval sets, judges, regression gates, tracing | LLM client found |
| ci-cd | delivery | Standard | Pipeline stages and required checks | CI found |
| containerization-deploy | delivery | Standard, Generator | Dockerfile, environments, config promotion | Docker or infrastructure code found |
| requirements-to-spec | sdlc | Workflow | Brief to PRD, user stories and acceptance criteria | Authored |
| wireframe-to-ui-spec | sdlc | Workflow | HTML wireframe to ui-spec.json | Authored |
| ui-mockup | sdlc | Workflow | Brief to on-brand HTML mocks with mock data | Authored |
| mock-data | sdlc | Generator | Synthetic domain data, never real records | Authored |
| spec-to-plan | sdlc | Workflow | Spec and contract to tasks.yaml, each task tagged with its skills | Authored |
| task-execution | sdlc | Workflow | How an assistant claims, builds, checks and hands off a task | Authored |
| standards-review | sdlc | Review | Pull request review against every skill that applies | Authored |
| release-and-gates | sdlc | Workflow | Maturity gates from mock to production, release notes | Authored |

Notes:

- Brand values in `ui-design-tokens` come from the brand team's token file in `accel-registry/standards/`, never from colors a repo happens to use. The factory records only how the code consumes tokens.
- Generated `llm-integration` and `agent-tools` skills must describe the Azure OpenAI gateway pattern, never another provider (C1).

## Skill folder

```text
skills/sso-auth/
├── SKILL.md            # frontmatter + numbered rules with reasons, steps, "Done when"
├── templates/          # golden files from the repo at the pinned commit, parameterized
├── reference/          # deeper detail, loaded only when needed
├── checks/             # semgrep.yml, spectral.yaml, eslint fragments, or small scripts
├── evals/              # 5–10 task prompts, each with a rubric
└── provenance.yaml     # evidence, owner, commit pins, catalog version
```

`SKILL.md` frontmatter:

```yaml
---
name: sso-auth                       # equals the folder name; lowercase and hyphens
description: Use when adding sign-in, protecting routes, validating tokens, or mocking the identity provider in a prototype.
---
```

Rules for `SKILL.md`:

- The description says **when** to use the skill, in one sentence of no more than 1,024 characters.
- Rules are numbered, and each has a one-line reason.
- It ends with a "Done when" checklist that the checks can verify.
- No external links. Copilot's web search is off, so reference material goes in `reference/`.
- No secrets, hostnames, people's names or real data.

`provenance.yaml`:

```yaml
skill: sso-auth
version: 1.2.0
catalog_version: 1
owner: security-iam
sources:
  - repo: ebi-atlas-api
    commit: 9f3c2e1
    findings: [auth-sso.token-validation, auth-sso.role-mapping]
generated_by: {tool: accel-skills, version: 0.3.0, model: gpt-6.1-sol}
approved_by: {github: <owner-handle>, pr: 42, date: 2026-12-02}
```

## Evals

Each `evals/<n>.yaml` holds one prompt:

```yaml
id: sso-auth-03
prompt: Add a protected /reports route to the FastAPI service that only the analyst role can reach.
fixture: blueprints/internal-data-app        # repo state the eval starts from
rubric:                                      # weights sum to 1
  - {criterion: "Uses the shared token validation dependency, not a new one", weight: 0.4}
  - {criterion: "Maps the analyst role through the role-mapping config", weight: 0.4}
  - {criterion: "Adds a test for the 403 case", weight: 0.2}
```

`accel skills eval` runs each prompt in Copilot CLI with the skill folder present and then absent:

```bash
copilot -p "<prompt>" --agent eval-runner --allow-tool <tool list> --output-format json
```

It grades the resulting diff with GPT-6.1 Sol against the rubric, giving a score from 0 to 1. Default publish thresholds, set in `accel.toml`: pass rate with the skill at least 0.8 (a pass is a score of at least 0.7), and lift (pass rate with the skill minus pass rate without it) at least 0.15. Reports go to `evals/reports/<skill>-<version>.json`. The run stops early if it would exceed `ACCEL_EVAL_CREDIT_BUDGET`.

## Registry and delivery

- `accel skills build` opens one PR per skill in `accel-registry`, using `gh`, with the findings and the validation report in the PR description.
- Merging needs the CODEOWNERS approval. The release workflow tags `skills/<name>/v<semver>`.
- `accel skills sync` in a project reads `aisdlc/project.yaml`, resolves the skills the blueprint and tasks need, copies them into `.github/skills/`, and writes `skills.lock`:

```yaml
registry: git@github.com:<org>/accel-registry.git
skills:
  sso-auth: {version: 1.2.0, commit: 4b1e9d0}
  ui-components: {version: 2.0.1, commit: 77ac3f2}
```

- The packager also writes each skill's `AGENTS.md` fragment, and the custom agents and prompt files that start the workflow skills (chapter 04).
- `dist/` keeps a portable `.agents/skills/` build for other assistants later. Nothing in this release uses it.
