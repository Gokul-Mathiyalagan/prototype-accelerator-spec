---
name: spec-change
description: Use in the Prototype Accelerator repo when a task needs behavior, a data contract, a constraint, a dependency or scope to differ from what spec/ says, or when the spec is ambiguous or contradicts itself.
---

# Propose a spec change

The spec is what keeps three agents consistent across sessions. Change it deliberately, and never quietly work around it.

## Decide what kind of change it is

- **Wording only** (a typo, or a clearer sentence with the same meaning): edit the spec file, and mention it under "Spec changes" in HANDOFF.md. You're done.
- **Ambiguity** (two readings both seem valid): choose the more conservative reading and record it in HANDOFF.md as an assumption. If the choice affects contracts or other packages, treat it as a behavior change.
- **Behavior, contract, constraint, dependency or scope change:** write an ADR, as below.

## Write an ADR

1. Copy `spec/decisions/ADR-template.md` to `spec/decisions/ADR-####-<slug>.md`, using the next free number.
2. Fill it in: context, the decision you propose, the alternatives considered, the consequences, and which spec sections and tasks it touches.
3. Set `Status: proposed`.
4. Commit `T-###: propose ADR-####`.
5. Tell Gokul and ask for a decision. Until it's `accepted`, keep building only what doesn't depend on it. If everything depends on it, set the task to `blocked`.
6. Once it's accepted, update the affected spec sections and `tasks.yaml` in one commit that references the ADR.

## Never

- Change a hard constraint from `spec/00-overview.md` (runtime AI services, local MCP only, no cloud agent, HTML only, redaction) without an accepted ADR.
- Edit generated files (`schemas/*.json`, `.claude/skills/`) by hand.
