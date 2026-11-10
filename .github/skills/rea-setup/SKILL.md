---
name: rea-setup
description: Use when /accel-setup or setup/install.sh fails, REA's MCP server won't start, or REA reports a missing JDK, Ghidra, decompiler or Node problem. Gives each known failure's symptom, cause and exact fix.
---

# Fixing REA setup

`setup/install.sh` installs everything under `~/.accel` (or `$ACCEL_HOME`) from the pins in `setup/versions.lock`. Start every diagnosis with:

```bash
bash setup/install.sh --check --json
```

Read `components[].status` and `next_action`, then find the matching section below. Install logs are in `~/.accel/logs/install-*.log`; the installer prints the last 50 lines on failure.

## Rules

1. Only apply the fixes written here, exactly as written. Reason: they're the ones known to be safe.
2. Never use `sudo`, and never edit shell profiles (`.zshrc`, `.bashrc`, `.profile`). Reason: setup must stay inside `~/.accel` (C5).
3. Never download or install anything the installer didn't. Reason: every download is pinned and checksum-verified.
4. If no section matches, stop and show the user the error and the last lines of the log. Reason: guessing can leave a half-installed toolchain.

## Exit codes

| Code | Meaning | What to do |
|---|---|---|
| 1 | Not ready, or a usage error | Run the `next_action` from `--check --json` |
| 2 | A prerequisite the script can't install is missing | See "Missing prerequisite" |
| 3 | Checksum mismatch | See "Checksum mismatch". Never retry with a different file. |
| 4 | Download failed | See "Proxy or mirror" |
| 5 | Build or verify failed | Read the log tail, then the matching section |

## Missing prerequisite

Symptom: `error: Missing prerequisites: git curl ...` (exit 2).
Fix: ask the user to install the named tools with their usual package manager, then re-run `bash setup/install.sh install`. On macOS, if `xcode-command-line-tools` is listed, the user runs `xcode-select --install` and accepts the dialog.

## Wrong JAVA_HOME

Symptom: REA or Ghidra reports the wrong Java version, or "a full JDK is required", although `--check` says `jdk` is ok.
Cause: REA was started without `setup/rea-mcp.sh`, so it used the user's own `JAVA_HOME`, or `~/.accel/rea.env` is out of date.
Fix:

```bash
bash setup/install.sh install env
```

Then make sure the MCP server is started through `setup/rea-mcp.sh` (it is, in `.vscode/mcp.json` and `.mcp.json`). Don't change the user's own `JAVA_HOME`.

## Missing arm64 decompiler

Symptom (Apple Silicon only): `ghidra-arm64-decompiler` is `missing`, or Ghidra reports no decompiler for `mac_arm_64`.
Cause: Ghidra doesn't ship an arm64 decompiler for macOS; the installer builds it.
Fix:

```bash
bash setup/install.sh install ghidra-arm64-decompiler
```

If the build fails, Xcode's command-line tools are missing or broken: the user runs `xcode-select --install`, then retry.

## Proxy or mirror

Symptom: `error: Download failed: ...` (exit 4), or `Couldn't fetch REA from ...`, or `npm ci` times out.
Cause: a proxy or firewall blocks GitHub, nodejs.org, Adoptium or the npm registry.
Fix: ask the user for their internal artifact mirror URL, then run, for this one command only:

```bash
ACCEL_MIRROR=<mirror-url> bash setup/install.sh install
```

`ACCEL_MIRROR` replaces download hosts but not checksums. If `npm ci` is what fails, the user's npm proxy settings (`HTTPS_PROXY`, or `registry` in their own npm config) apply; ask them to check those. Don't edit their npm config.

## Checksum mismatch

Symptom: `error: Checksum mismatch for <file>` (exit 3).
Cause: the download was altered, truncated, or the mirror serves a different file.
Fix: none in place. Stop, show the user the message, and tell them to report it to the platform team. Don't edit `setup/versions.lock` and don't download the file another way.

## Node mismatch

Symptom: REA says its Node version is unsupported, or `npm ci` fails with `EBADENGINE`.
Cause: REA ran under the user's own `node` instead of the pinned one, or `~/.accel/tools/node` is out of date.
Fix:

```bash
bash setup/install.sh install node rea
```

The launcher always uses `~/.accel/tools/node/bin/node`; the user's own Node version doesn't matter.

## Gatekeeper quarantine

Symptom (macOS): "cannot be opened because the developer cannot be verified", or a downloaded binary is killed on launch.
Cause: macOS marked a downloaded file as quarantined.
Fix: remove the quarantine attribute from the installed tools only:

```bash
xattr -dr com.apple.quarantine ~/.accel/tools
```

Never run it on anything outside `~/.accel/tools`.

## MCP server not starting

Symptom: the `rea` server shows as failed or stopped in VS Code (MCP: List Servers) or in Claude Code (`/mcp`).
Fix, in order:

1. Run `bash setup/install.sh --check --json`. If anything isn't `ok`, fix that first.
2. Run `bash setup/rea-mcp.sh </dev/null` and read the message. "REA isn't set up" means run `bash setup/install.sh install`.
3. Restart the server: in VS Code, MCP: List Servers, choose `rea`, then Restart; in Claude Code, run `/mcp` and reconnect `rea`.
4. If it still fails, show the user the server's output (VS Code: Show Output for `rea`).

## Registry enforcement

Symptom: VS Code or Claude Code refuses to start `rea` or `accel` because the org only allows MCP servers from its registry.
Cause: the org turned on MCP registry enforcement.
Fix: nothing to change locally. Tell the user to ask their admin to add these server IDs to the org registry: `io.github.morluto/rea` (REA) and `accel` (Prototype Accelerator's own server).

## Windows

`setup/install.sh` supports macOS (arm64, x64) and Linux x64. On Windows, tell the user to run the platform from WSL or a Linux container; don't try to install natively.

## Done when

- `bash setup/install.sh --check --json` prints `"ok": true`.
- `bash setup/install.sh verify` exits 0.
- The `rea` MCP server is running, and its `inspect_analysis_settings` tool answers.
