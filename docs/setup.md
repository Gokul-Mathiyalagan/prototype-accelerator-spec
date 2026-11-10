# Setting up REA with /accel-setup

Prototype Accelerator uses REA (Reverse Engineer Anything) to see what a built or running app actually does. You don't install it yourself: your assistant runs the installer, explains each step, and asks you to approve every command.

## Before you start

- macOS (Apple Silicon or Intel) or Linux x64. Windows isn't supported; use WSL or a Linux container.
- `git`, `curl`, `tar` and `unzip`. On Apple Silicon, also Xcode's command-line tools (`xcode-select --install`).
- About 2 GB of free disk space. Everything goes under `~/.accel` (or `$ACCEL_HOME`); nothing needs admin rights.

## In VS Code with GitHub Copilot

1. Open this repo in VS Code and open Copilot Chat in agent mode.
2. Type `/accel-setup` and approve each command when Copilot asks.
3. When Copilot asks, start the `rea` server: run **MCP: List Servers**, choose `rea`, then **Start**.
4. Copilot calls one REA tool to prove it works.

## In Claude Code

1. Open a Claude Code session in this repo. Approve the project's MCP servers (`rea` and `accel`, from `.mcp.json`) when asked.
2. Type `/accel-setup` and approve each command.
3. When asked, run `/mcp` and connect `rea`.
4. Claude Code calls one REA tool to prove it works.

Claude Code support covers `/accel-setup` only (ADR-0009); use Copilot for everything else.

## What gets installed

Pinned in `setup/versions.lock`, each download checked against its SHA-256:

| Component | Version |
|---|---|
| Node.js | 24.22.1 (REA's pinned version) |
| Temurin JDK | 21.0.13+9 |
| Ghidra | 12.1.4 |
| REA | a pinned commit, built from source |

On Apple Silicon, the installer also builds Ghidra's arm64 decompiler, which takes a few minutes.

## Updating

When the platform team moves the pins, pull the repo and run `/accel-setup update`. Only the components that changed are reinstalled.

## When something goes wrong

Your assistant follows the fixes in `.github/skills/rea-setup/SKILL.md`. You can also run the installer yourself:

```bash
bash setup/install.sh --check          # what's installed, and what to do next
bash setup/install.sh install          # install what's missing
bash setup/install.sh verify           # run REA's Ghidra check
```

Logs are in `~/.accel/logs/`. Behind a proxy, ask your platform team for the mirror URL and set `ACCEL_MIRROR` for the install. A checksum mismatch is never safe to work around; report it.

The `accel` MCP server is Prototype Accelerator's own server. Until it's built (task T-110), it shows as failed to start; that's expected and doesn't affect REA.
