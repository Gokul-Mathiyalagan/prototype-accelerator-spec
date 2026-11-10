# Prototype Accelerator spec

This folder is the build spec for Prototype Accelerator. It's written for the coding agents that build it (Claude Code, Codex and Antigravity) and for Gokul, who reviews their work. It's based on the reviewed plan, "Prototype Accelerator: AISDLC Platform Plan".

## Reading order

You don't need to read everything. Each task in `tasks/tasks.yaml` lists the sections it depends on.

| File | Read it when |
|---|---|
| `00-overview.md` | Always, once. It has the product, its scope and the hard constraints. |
| `01-architecture.md` | You touch package boundaries, repository layout, configuration or the tech stack |
| `02-repo-intelligence.md` | Engine 1: `/accel-setup`, REA and Ghidra, extraction, playbooks, knowledge model |
| `03-skill-factory.md` | Engine 2: skill catalog, SKILL.md format, registry, evals, packaging |
| `04-aisdlc.md` | Engine 3: lifecycle, gates, `accel-mcp`, wireframes, generated projects |
| `05-cli-and-contracts.md` | You add a CLI command or change a data contract |
| `06-security.md` | Anything that touches models, secrets, downloads or external tools |
| `07-conventions.md` | Before your first commit: code, tests, git and the definition of done |
| `08-roadmap.md` | Planning: phases, gates and which tasks belong to each |
| `decisions/` | ADRs. `open-decisions.md` lists what Gokul hasn't decided yet. |

## How the spec relates to other files

- **`tasks/tasks.yaml`** turns the spec into work. Each task's `spec` field links back here.
- **`handoff/HANDOFF.md`** is where work stands right now. The spec says what to build; the handoff says where the last session stopped.
- **`schemas/*.json`** are generated from Pydantic models. Chapter 05 describes the contracts, but the models in `accel_core.contracts` are the source of truth.

## Words used throughout

| Term | Meaning |
|---|---|
| **Platform repo** | This repo, `prototype-accelerator` |
| **Target repo** | An existing codebase the platform extracts knowledge from |
| **Registry** | The separate `accel-registry` repo of approved skills |
| **Project** | A new codebase that `accel init` creates and the AISDLC builds |
| **Dev agent** | Claude Code, Codex or Antigravity, used to build this repo |
| **User's assistant** | GitHub Copilot, which the platform's users run in VS Code |
| **Finding** | One evidence-backed claim about a target repo |
| **Skill** | A folder with `SKILL.md` that teaches Copilot one standard or workflow |
| **Gate** | A named person's recorded approval between AISDLC phases |
| **Maturity level** | mock, prototype, pilot or production; it decides which checks apply |
| **REA** | Reverse Engineer Anything: an MIT-licensed MCP server and CLI for analyzing built apps, binaries and network captures |
