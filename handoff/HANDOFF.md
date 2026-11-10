# Handoff

- **Updated:** 2026-11-10 21:50 IST
- **Agent:** claude-code
- **Active task:** none
- **Task status:** done
- **Branch:** task/T-005-verify-locale
- **Last commit:** 621e7e1 T-005: record decision to keep REA on Docker for Windows

## Summary

The installer, launcher and `accel setup`/`accel doctor` are built, and every offline criterion passes. A real install in a Linux container (Docker on Gokul's Windows host) works end to end, and the real REA 6.8.0 MCP server answers through `rea-mcp.sh`. T-005 is merged into `main` and done. The Linux `verify:ghidra` gap is now fixed on `task/T-005-verify-locale` (below): REA's own verifier passes against the real install. That fix is waiting for Gokul to merge it.

## Acceptance criteria

- [x] versions.lock pins the REA commit, Node, Temurin JDK 21 and Ghidra 12.1.4 with SHA-256 for darwin-arm64, darwin-x64 and linux-x64. Real values, fetched from nodejs.org SHASUMS256, the Adoptium API and the Ghidra GitHub release; validated by `test_versions_lock_matches_the_contract_and_pins`.
- [x] install.sh --check --json prints valid install-check JSON; install, verify subcommands follow the spec/02 contract and exit codes (`tests/setup/test_install.py`).
- [x] Installs only under $ACCEL_HOME, no sudo, no shell-profile edits; checksum mismatch exits 3; ACCEL_MIRROR replaces hosts only.
- [x] Builds the arm64 decompiler on Apple Silicon; skips it elsewhere. The flags are checked with a fake decompiler Makefile under `ACCEL_PLATFORM=darwin-arm64`; it hasn't been built on a real Mac.
- [x] Re-running after success changes nothing and exits 0 (the file-hash snapshot is identical, excluding `logs/`).
- [x] rea-mcp.sh starts REA's MCP server from $ACCEL_HOME and fails with a clear message if setup hasn't run (fake test, plus a live `initialize` reply from REA 6.8.0).
- [x] accel setup and accel doctor wrap the script with --json output (`tests/cli/test_setup_command.py`).
- [x] shellcheck clean; a Linux container test runs --check end to end with downloads faked; a live_rea test runs the full install and npm run verify:ghidra. Live in Docker: install, re-run, check and MCP passed earlier; `install.sh verify` passed against the same install after the fix below.

## State of the active task

- `setup/versions.lock`, `setup/install.sh` (bash 3.2 safe, with an awk parser for the lock), `setup/rea-mcp.sh`.
- `accel_cli/main.py` (new `accel` entry point) and `accel_cli/commands/setup.py` (`setup`, `doctor`). No other task created the CLI entry point, so it was added here.
- `tests/setup/`: `Dockerfile` and `make_fakes.sh` (a fake mirror and lock), `scenarios.sh` (every scenario in one container), `test_install.py`, plus `Dockerfile.live`, `live.sh` and `test_install_live.py` (real install in the `accel-live-home` Docker volume).
- Contract fix: `JdkPin.version` now accepts Temurin's `+build` suffix (`21.0.13+9`); the schema is regenerated.

## The verify:ghidra fix (Linux)

REA's verifier (`scripts/lib/native-value-e2e.mjs`, `environment()`) starts its MCP server with a hand-built environment that drops `LANG`/`LC_ALL`. Its socket-boundary check then uses a temp path containing `雪`. Without a locale, the JVM on Linux encodes file names as ASCII (`sun.jnu.encoding=ANSI_X3.4-1968`), the path becomes `???`, and Ghidra's LaunchSupport fails ("User home directory does not exist"). Tested in the container: only `LC_ALL=C.UTF-8` fixes it; `-Dsun.jnu.encoding` and `-Dfile.encoding` don't. Since the verifier strips that variable, the check can't pass on Linux at this commit (REA `main`, b2f3dc8). macOS Java always uses UTF-8 for file names, so it should pass there. The verifier does keep `NODE_OPTIONS`, so on Linux `install.sh verify` now preloads `setup/utf8-locale.cjs` (`--require`), which sets `LC_ALL=C.UTF-8` inside REA's Node processes when no UTF-8 locale is set. REA's code and pin are unchanged. `rea-mcp.sh` sets the same fallback directly, since its environment reaches REA intact. Result: `REA's Ghidra check passed.` (exit 0).

## Next step

1. Gokul merges `task/T-005-verify-locale` into `main`.
2. Optionally, file the upstream issue drafted in `handoff/log/2026-11-10-claude-code-T-005.md` (the preload is a workaround; REA's verifier is still wrong upstream). Then drop the preload when REA fixes it.
3. When convenient, confirm `setup/install.sh verify` on a Mac.
4. The next eligible tasks are T-006 (Copilot setup assets; needs copilot and rea), T-007 (fixture repos), T-108 (playbooks) and T-201 (catalog).

## How to verify

```bash
uv run make check                                   # all offline tests, including 25 container tests (needs Docker)
uv run make test-live NEEDS=rea,ghidra UV=uv        # real install in Docker; ~28 min first run, ~15 min after
```

## Decisions and assumptions

- Docker is used on Windows because install.sh targets macOS and Linux; the platform's users are on macOS and Linux.
- Gokul decided (2026-11-10) not to add native Windows support for REA. REA's Windows mode is experimental, analyzes only PE, DOS and 6502 binaries (not ELF or Mach-O), and needs the native add-on from the npm package. Windows developers run REA through Docker. Revisit only with an ADR.
- `--check` exits 1 when not ready, matching the CLI's "checks failed" code. Usage errors exit 1, since spec/02 reserves 2 to 5.
- CLI exit mapping from install.sh: 2→3 (prerequisite), 3, 4 and 5→4 (external failure).
- Downloads are deleted after extraction (Ghidra is 570 MB). Each install run writes a log to `$ACCEL_HOME/logs/`; the idempotency check excludes it.
- npm's cache and XDG config and cache folders are pointed into `$ACCEL_HOME`, and `HUSKY=0` stops REA installing git hooks.
- Test hooks: `ACCEL_VERSIONS_LOCK` and `ACCEL_PLATFORM` (documented in install.sh's header).

## Spec changes

None. (The `JdkPin` pattern fix is a contract correction from T-003.)

## Open questions for Gokul

- `make test-live` breaks on Windows: `uv run` sets `UV` to a backslash path that `sh` mangles in the `test-live` recipe. Pass `UV=uv` for now. Should I add a task to fix the Makefile?

## Watch out

- The `accel-live-home` Docker volume holds a full install (about 2 GB). Remove it with `docker volume rm accel-live-home`.
- The container tests mount the repo, so shell scripts need LF endings (`.gitattributes` enforces it).
