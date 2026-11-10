# ADR-0003: Copilot runs setup and extraction

- **Status:** accepted
- **Date:** 2026-11-10
- **Decided by:** gokul
- **Task:** T-000

## Context

Gokul doesn't want users to install REA by hand, and wants Copilot to drive both installation and extraction.

## Decision

- `/accel-setup` (a Copilot prompt file and custom agent) runs `setup/install.sh`. The script installs Node, JDK 21, Ghidra 12.1.4 and REA at pinned, checksum-verified versions into `~/.accel/tools`, without admin rights. It builds the arm64 decompiler on Apple Silicon, verifies Ghidra, and writes `rea.env`. Copilot runs each step, reads the logs, applies known fixes from the `rea-setup` skill, and reports. Users approve commands but don't type them.
- `/accel-extract <git-url>` runs extraction in Copilot: deterministic `accel extract prepare`, then the `investigator` agent works through the playbooks in `extract-plan.md`, then `accel extract verify`.
- `accel extract --batch` (on Azure OpenAI) is optional, for re-runs without spending Copilot credits.

## Alternatives considered

- **Manual installation instructions:** rejected by Gokul.
- **Letting Copilot improvise installation commands:** not reproducible or reviewable, and risky. A pinned script with Copilot driving it gives both.
- **Batch-only extraction on Azure:** cheaper on Copilot credits, but Gokul wants Copilot to drive it. Batch mode stays as an option.

## Consequences

- The installer must be idempotent, machine-readable (`--check --json`) and strict about checksums.
- A clean-laptop test of `/accel-setup` is a phase 0 gate.

## Affects

- Spec sections: 00 (C5), 02, 06
- Tasks: T-005, T-006, T-009, T-109, T-111, T-112
