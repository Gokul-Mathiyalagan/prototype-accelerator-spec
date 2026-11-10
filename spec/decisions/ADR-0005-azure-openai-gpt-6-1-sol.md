# ADR-0005: Azure OpenAI (gpt-6.1-sol) is the only model API

- **Status:** accepted
- **Date:** 2026-11-10
- **Decided by:** gokul
- **Task:** T-000
- **Amended by:** ADR-0008 (authentication uses a deployment API key, not Entra ID)

## Context

Besides Copilot, the only AI service officially available to the users is Azure OpenAI, with the GPT-6.1 Sol deployment.

## Decision

Product code calls models only through `accel_core.gateway`, which uses the `openai` package's `AzureOpenAI` client, authenticated as ADR-0008 describes. It's used for skill drafting, eval grading and batch extraction. A CI guard rejects any other model SDK or endpoint (spec/06).

## Alternatives considered

None. This is a policy constraint.

## Consequences

- Redaction, budgets and audit live in the gateway, so every call gets them.
- Dev agents (Claude Code, Codex, Antigravity) must not add their own providers' SDKs to product code (C9).

## Affects

- Spec sections: 00 (C1), 01, 06
- Tasks: T-004, T-112, T-203, T-206, T-401
