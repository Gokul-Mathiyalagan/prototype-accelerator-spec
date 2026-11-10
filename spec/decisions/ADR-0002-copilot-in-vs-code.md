# ADR-0002: GitHub Copilot in VS Code is the users' assistant

- **Status:** accepted
- **Date:** 2026-11-10
- **Decided by:** gokul
- **Task:** T-000
- **Amended by:** ADR-0009 (Claude Code can also run `/accel-setup`)

## Context

The platform's users, on Gokul's team and in the wider org, have GitHub Copilot Business. The org's settings (November 2026) are:

- enabled: agent mode in IDE chat, Copilot CLI, MCP servers in Copilot, and bring-your-own-key in VS Code and JetBrains;
- disabled: Copilot in the cloud, which covers the cloud agent, editor preview features, and web search;
- 10,000 AI credits a month per user;
- GPT-6.1 Sol enabled in the model picker, along with Claude Opus 5.5, Claude Sonnet 5.5, Gemini 3.8 Flash and others.

## Decision

The product targets agent mode in VS Code as the main surface, and Copilot CLI for scripted runs such as evals. No product feature uses the Copilot cloud agent (C3) or a VS Code preview feature (C4). Skills reach projects as `.github/skills/` through git.

## Alternatives considered

- **Copilot cloud agent for unattended tasks:** disabled by policy.
- **Other assistants (Claude Code, Codex):** not approved for the users. Skills stay portable through `.agents/skills/` in `dist/`.

## Consequences

- Extraction and evals spend Copilot AI credits, so they must be economical (T-009, T-402).
- Skills can't link to the web, so reference material is bundled with them.

## Affects

- Spec sections: 00, 03, 04
- Tasks: T-006, T-111, T-209, T-301, T-310, T-401
