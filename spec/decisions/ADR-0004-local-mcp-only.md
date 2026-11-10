# ADR-0004: Local stdio MCP servers only

- **Status:** accepted
- **Date:** 2026-11-10
- **Decided by:** gokul
- **Task:** T-000

## Context

External MCP servers aren't allowed in Gokul's org. REA has to run locally from its GitHub repo and be used from Copilot.

## Decision

Only two MCP servers exist, both local stdio:

- `rea`, started by `setup/rea-mcp.sh` from the install in `~/.accel`;
- `accel`, the platform's own `accel-mcp`.

The platform repo registers both in `.vscode/mcp.json` using `${workspaceFolder}` paths. Generated projects register only `accel`. `accel package --lint` rejects `url`-type servers.

## Alternatives considered

- **User-level MCP config with absolute paths:** it works, but each user has to edit it. The launcher keeps the committed config portable.

## Consequences

If the org turns on MCP registry enforcement, `rea` and `accel` must be added to the registry by server ID.

## Affects

- Spec sections: 00 (C2), 02, 04, 06
- Tasks: T-006, T-110, T-209, T-302
