"""`accel setup` and `accel doctor`: thin wrappers over setup/install.sh (spec/05)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
from accel_core.contracts import InstallCheck
from accel_core.errors import ConfigError
from accel_core.gateway import load_settings
from pydantic import ValidationError

# install.sh exit code -> CLI exit code (spec/05: 3 prerequisite missing, 4 external failure).
_EXIT_CODES = {0: 0, 1: 1, 2: 3, 3: 4, 4: 4, 5: 4}
_NO_INSTALLER = "setup/install.sh or bash wasn't found. Run accel from the platform repo."


def run_tool(command: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    """Run an external tool. Tests replace this function."""
    return subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def find_installer() -> Path | None:
    """Locate setup/install.sh in the current repo, or next to this package's checkout."""
    candidates = [Path.cwd() / "setup" / "install.sh"]
    candidates += [parent / "setup" / "install.sh" for parent in Path(__file__).resolve().parents]
    return next((path for path in candidates if path.is_file()), None)


def _emit(payload: dict[str, Any], as_json: bool, lines: list[str]) -> None:
    if as_json:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for line in lines:
            typer.echo(line)


def _installer_command(*arguments: str) -> list[str] | None:
    installer = find_installer()
    bash = shutil.which("bash")
    if installer is None or bash is None:
        return None
    return [bash, str(installer), *arguments]


def read_install_check() -> tuple[InstallCheck | None, str]:
    """Run `install.sh --check --json` and parse it. Returns the result or a reason."""
    command = _installer_command("--check", "--json")
    if command is None:
        return None, _NO_INSTALLER
    result = run_tool(command)
    try:
        return InstallCheck.model_validate_json(result.stdout), ""
    except ValidationError:
        reason = (result.stderr or "").strip().splitlines()
        return None, reason[-1] if reason else f"install.sh exited {result.returncode}"


def _check_lines(check: InstallCheck) -> list[str]:
    lines = [f"Platform: {check.platform}"]
    lines += [f"  {c.name:<24} {c.status:<14} {c.detail}" for c in check.components]
    lines.append(f"Next: {check.next_action}" if check.next_action else "Ready.")
    return lines


def setup(
    components: Annotated[
        list[str] | None, typer.Argument(help="Components to install (default: all).")
    ] = None,
    check: Annotated[bool, typer.Option("--check", help="Only report what's installed.")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Print one JSON object.")] = False,
) -> None:
    """Install REA, Node, the JDK and Ghidra under ~/.accel, or check them."""
    if check and components:
        typer.echo("--check doesn't take components.", err=True)
        raise typer.Exit(2)
    installer_exit = 0
    if not check:
        command = _installer_command("install", *(components or []))
        if command is None:
            typer.echo(_NO_INSTALLER, err=True)
            raise typer.Exit(3)
        # Progress streams to stderr; install.sh prints nothing on stdout.
        installer_exit = run_tool(command, capture=False).returncode
    status, reason = read_install_check()
    if status is None:
        _emit({"ok": False, "error": reason}, as_json, [f"error: {reason}"])
        raise typer.Exit(3)
    payload: dict[str, Any] = {"check": status.model_dump(mode="json"), "ok": status.ok}
    if not check:
        payload["installer_exit_code"] = installer_exit
    _emit(payload, as_json, _check_lines(status))
    if installer_exit:
        raise typer.Exit(_EXIT_CODES.get(installer_exit, 1))
    if not status.ok:
        raise typer.Exit(1)


def _version(tool: str, *arguments: str) -> tuple[bool, str]:
    path = shutil.which(tool)
    if path is None:
        return False, f"{tool} isn't on PATH"
    try:
        result = run_tool([path, *arguments])
    except OSError as error:
        return False, f"{tool} didn't run: {error.strerror}"
    output = (result.stdout or result.stderr or "").strip().splitlines()
    return result.returncode == 0, output[0] if output else f"exit {result.returncode}"


def _azure() -> tuple[bool, str]:
    try:
        settings = load_settings()
    except ConfigError as error:
        return False, error.message
    host = settings.endpoint.split("://", 1)[-1].split("/", 1)[0]
    return True, f"deployment {settings.deployment} at {host} (configured; not called)"


def doctor(
    as_json: Annotated[bool, typer.Option("--json", help="Print one JSON object.")] = False,
) -> None:
    """Check REA and Ghidra, the Azure OpenAI settings, Copilot CLI, uv and git."""
    status, reason = read_install_check()
    rea_ok = status is not None and status.ok
    rea_detail = reason if status is None else (status.next_action or "ready")
    checks: list[tuple[str, bool, str]] = [
        ("rea", rea_ok, rea_detail),
        ("azure-openai", *_azure()),
        ("copilot-cli", *_version("copilot", "--version")),
        ("uv", *_version("uv", "--version")),
        ("git", *_version("git", "--version")),
    ]
    ok = all(passed for _, passed, _ in checks)
    payload: dict[str, Any] = {
        "ok": ok,
        "checks": [{"name": n, "ok": p, "detail": d} for n, p, d in checks],
        "install_check": status.model_dump(mode="json") if status else None,
    }
    lines = [f"  {'ok' if p else 'FAIL':<5}{n:<14} {d}" for n, p, d in checks]
    _emit(payload, as_json, [*lines, "Ready." if ok else "Not ready."])
    if not ok:
        sys.stdout.flush()
        raise typer.Exit(1)
