# 00 Overview

## Purpose

Teams keep rebuilding the same things: Comcast-styled UI, API conventions, SSO, backend layering and LLM integration. Prototype Accelerator captures how the best existing codebases do these, as reviewed **agent skills**, then uses those skills to build new projects quickly and to the same standard.

It does three things:

1. **Repo Intelligence (Engine 1).** Given a git URL, it works out how the codebase works, with evidence for every claim. It combines static analysis with REA's runtime and artifact analysis.
2. **Skill Factory (Engine 2).** It turns that knowledge into skills: generalized, checked, approved by a named owner, and tested for lift.
3. **AISDLC Workbench (Engine 3).** It runs an AI-integrated SDLC in which GitHub Copilot builds a new project from a brief, an HTML wireframe and the skills, with people approving each phase.

## Users

| User | What they do |
|---|---|
| Platform team (Gokul's team) | Runs extraction on reference repos, curates the catalog, runs the platform |
| Skill owners (security, design, architecture) | Approve, edit or reject skills in the registry |
| Project teams (product owner, designer, tech lead, developers) | Start projects with `accel init`, go through the AISDLC with Copilot, and approve gates |

## End-to-end flow

```text
git URL ─▶ /accel-setup (once per machine)
        ─▶ /accel-extract ─▶ knowledge/<repo>/  (findings with evidence)
        ─▶ accel skills build ─▶ registry PRs ─▶ owner approval ─▶ evals ─▶ published skills
brief + HTML wireframe ─▶ accel init ─▶ AISDLC phases 1–7 in Copilot ─▶ project at mock → prototype → pilot → production
```

## Scope of the first release

**In scope**

- Extraction from Python and TypeScript/JavaScript repos: FastAPI, Express, React, SQLAlchemy, LLM client code.
- REA for front-end bundles, live UI, HAR captures, and native binaries through Ghidra.
- The 35-skill default catalog, in 8 groups.
- Skills delivered to projects as `.github/skills/` through `accel skills sync`.
- AISDLC phases 1 to 7 with five gates, and maturity levels mock to production.
- HTML wireframe intake.
- The CLI and `accel-mcp` first. The web workbench comes in phase 5.

**Out of scope for now**

- Figma intake.
- Java and other languages beyond Python and TypeScript/JavaScript.
- Assistants other than GitHub Copilot as the users' assistant. Skills are still built in a portable `.agents/skills/` layout so this can change later.
- Copilot cloud agent, remote MCP servers, and VS Code preview features.

## Hard constraints

These are fixed by Gokul's environment and confirmed decisions (see `decisions/`). Changing any of them needs an accepted ADR. Refer to them by ID.

| ID | Constraint |
|---|---|
| **C1** | The platform's users have exactly two AI services: **GitHub Copilot** (Business; agent mode in VS Code and Copilot CLI) and **Azure OpenAI** (deployment `gpt-6.1-sol`). Product code calls models only through `accel_core.gateway`, which supports only Azure OpenAI. |
| **C2** | **MCP servers are local stdio only:** REA and `accel-mcp`. No remote, hosted or third-party MCP servers. |
| **C3** | **No Copilot cloud agent.** Generated assets target agent mode in VS Code and Copilot CLI. |
| **C4** | **VS Code preview features are off.** Nothing may depend on one, such as installing from the skills marketplace. |
| **C5** | **Copilot does setup and extraction.** Users don't install REA by hand. `/accel-setup` installs it from pinned, checksum-verified versions, and `/accel-extract` runs extraction. Users approve commands but don't type them. |
| **C6** | **Design input is HTML wireframes only.** |
| **C7** | **Secrets and personal data are redacted** before any model or Copilot sees code, HAR files or logs. Runtime analysis uses synthetic data only. |
| **C8** | **REA's Ghidra provider** analyzes only binaries committed to or built from a target repo, never public registry packages, and only when the binary's license allows reverse engineering. |
| **C9** | **Dev agents aren't product dependencies.** Claude Code, Codex and Antigravity build this repo, but nothing in the product may require them. |

Useful facts about the users' Copilot setup (Copilot Business, November 2026):

- GPT-6.1 Sol is in Copilot's model picker, so agent mode can use the same model as the platform. Claude Opus 5.5, Claude Sonnet 5.5, Gemini 3.8 Flash and others are also enabled.
- Each user has 10,000 AI credits a month, so extraction and evals must be economical.
- Copilot's web search is off, so skills must carry their own reference material.
- MCP servers in Copilot are enabled, but the org may turn on registry enforcement. If it does, `rea` and `accel` must be in the registry by server ID.

## Success measures

- **Phase 1:** two reference repos produce knowledge models in which every kept finding has valid evidence.
- **Phase 2:** owners approve the first 10 skills, and Copilot loads them in VS Code and Copilot CLI.
- **Phase 3:** a pilot project goes from a brief and an HTML wireframe to mock level in Copilot.
- **Phase 4:** skill lift is measured, meaning the eval pass rate with a skill against without it, on two or three Copilot models.
- **Phase 5:** the pilot readout gives a go or no-go for wider rollout.
