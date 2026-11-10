# ADR-0001: REA, with its Ghidra provider, alongside static analysis

- **Status:** accepted
- **Date:** 2026-11-10
- **Decided by:** gokul
- **Task:** T-000

## Context

The platform needs to learn how an existing codebase works. "REA" was confirmed to mean Reverse Engineer Anything, an MIT-licensed MCP server and CLI. It analyzes built bundles, live UIs, HAR captures, .NET and Electron apps, and native binaries through Ghidra. It doesn't take a git URL or read a source tree on its own.

## Decision

Engine 1 combines static source analysis (tree-sitter code graph and framework adapters) with REA's runtime and artifact evidence. REA's Ghidra provider (Ghidra 12.1.x, JDK 21) analyzes native binaries that are committed to or built from a target repo, and only when their license allows (C8).

## Alternatives considered

- **REA alone:** it can't read source, so it would miss most of the code.
- **Static analysis alone:** it can't see runtime behavior, the built UI or binaries.

## Consequences

- Every finding needs evidence. Verification re-checks it, because REA can be confidently wrong.
- `/accel-setup` must install Ghidra and JDK 21 (ADR-0003).

## Affects

- Spec sections: 02, 06
- Tasks: T-005, T-007, T-008, T-101, T-105, T-107, T-113
