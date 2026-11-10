# ADR-0006: HTML wireframes are the only design input

- **Status:** accepted
- **Date:** 2026-11-10
- **Decided by:** gokul
- **Task:** T-000

## Context

Figma intake would need Figma's MCP server or API, and neither is available. Teams can sketch in HTML.

## Decision

`accel design import --html` is the only design intake. A `wireframe-kit/` of HTML starters and conventions (landmarks, labels, `th` headers, and `data-component`, `data-route` and `data-state` hints) makes mapping reliable.

## Alternatives considered

- **Figma via MCP:** out of scope for now. If it's added later, it must write the same `ui-spec.json`, so nothing downstream changes.

## Consequences

Intake has to infer structure from HTML, with confidence scores. Gaps become open questions at Gate 2.

## Affects

- Spec sections: 00 (C6), 04
- Tasks: T-304, T-305
