# 08 Roadmap

The build runs in six phases over about 14 weeks. Each phase ends at a gate, and the next phase starts only when that gate passes. Task details are in `tasks/tasks.yaml`.

| Phase | Weeks | Goal | Tasks | Gate |
|---|---|---|---|---|
| 0 · Foundations and spikes | 1 | Repo scaffold, contracts, gateway, `/accel-setup`, REA proven in Copilot, credit cost per playbook measured | T-001 to T-009 | Decisions signed off; REA works in VS Code agent mode on a clean laptop |
| 1 · Repo Intelligence | 2–4 | Stages 1 to 8, `/accel-extract`, batch mode, the knowledge model | T-101 to T-115 | Copilot extracts two reference repos, and every kept finding has valid evidence |
| 2 · Skill Factory | 5–7 | Catalog, writer, validator, registry, packaging and sync | T-201 to T-210 | Owners approve the first 10 skills, and Copilot loads them in VS Code and the CLI |
| 3 · AISDLC core | 8–10 | `accel init`, `accel-mcp`, intake, wireframes, mocks, contract, plan, checks, gates | T-301 to T-311 | A pilot project reaches mock level from a brief and an HTML wireframe |
| 4 · Evals and feedback | 11–12 | Eval harness, model comparison, audit, feedback loop | T-401 to T-405 | Skill lift is measured for each Copilot model used |
| 5 · Workbench and scale | 13–14 | Web workbench, multi-repo merge, telemetry, onboarding | T-501 to T-506 | Pilot readout: go or no-go for wider rollout |

## Where each task can run

Most tasks can be built and unit-tested anywhere. Tasks with `needs` require Gokul's work environment for their live verification:

| Need | Available where |
|---|---|
| `azure` | Machines with access to the Azure OpenAI `gpt-6.1-sol` deployment |
| `copilot` | VS Code with Gokul's Copilot Business seat, or Copilot CLI |
| `rea`, `ghidra` | Any machine where `/accel-setup` has run |
| `work-repos` | Machines that can clone the reference repos (EBI Atlas, Genie/Cortex app) |

The dev agents build these tasks against fakes and fixtures, and mark the live tests. Gokul runs the live tests in the work environment and records the results in the task's `progress` and in a session log.
