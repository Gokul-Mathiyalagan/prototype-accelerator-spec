#!/usr/bin/env python3
"""Run repository development targets on Windows, macOS, and Linux."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = tuple(sorted((ROOT / "packages").glob("accel-*")))
LIVE_NEEDS = ("azure", "copilot", "rea", "ghidra", "work-repos")


def run(*command: str) -> None:
    """Run a development tool and stop on failure."""
    print(f"> {shlex.join(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def pytest_command(*arguments: str) -> None:
    """Run pytest, accepting an empty golden/live suite during scaffolding."""
    try:
        run(sys.executable, "-m", "pytest", *arguments)
    except subprocess.CalledProcessError as exc:
        if exc.returncode != 5:
            raise
        print("No tests selected for this target yet.", flush=True)


def offline_tests(*, coverage: bool = False) -> None:
    """Run only offline tests, optionally enforcing coverage per package."""
    arguments = ["-m", "not live"]
    if coverage:
        arguments.extend(f"--cov=accel_{path.name[6:]}" for path in PACKAGES)
        arguments.extend(("--cov-report=term-missing", "--cov-report=json"))
    # The offline suite must contain tests; do not accept pytest's empty-suite status.
    run(sys.executable, "-m", "pytest", *arguments)
    if coverage:
        check_package_coverage(ROOT / "coverage.json")


def check_package_coverage(report_path: Path) -> None:
    """Require at least 80 percent line coverage in every workspace package."""
    files = json.loads(report_path.read_text(encoding="utf-8"))["files"]
    failures: list[str] = []
    for package in PACKAGES:
        prefix = package.relative_to(ROOT).as_posix() + "/src/"
        summaries = [
            data["summary"]
            for name, data in files.items()
            if name.replace("\\", "/").startswith(prefix)
        ]
        total = sum(summary["num_statements"] for summary in summaries)
        covered = sum(summary["covered_lines"] for summary in summaries)
        percent = 100.0 * covered / total if total else 0.0
        print(f"{package.name}: {percent:.1f}% line coverage", flush=True)
        if percent < 80:
            failures.append(package.name)
    if failures:
        raise SystemExit("Coverage below 80%: " + ", ".join(failures))


def shellcheck() -> None:
    """Lint every project shell script, including untracked new files."""
    roots = ("scripts", "setup", "packages", "blueprints", ".github")
    scripts = sorted(
        str(path.relative_to(ROOT))
        for name in roots
        for path in (ROOT / name).rglob("*.sh")
        if "fixtures" not in path.parts
    )
    # Check the installation even before the installer task introduces shell scripts.
    run("shellcheck", "--version")
    if scripts:
        run("shellcheck", "--shell=bash", *scripts)
    else:
        print("No project shell scripts yet.", flush=True)


def check() -> None:
    """Run all offline quality gates."""
    run("ruff", "check", ".")
    run("ruff", "format", "--check", ".")
    run("pyright")
    run("lint-imports", "--no-cache")
    shellcheck()
    run(
        "semgrep",
        "scan",
        "--config",
        ".semgrep/ai-endpoints.yml",
        "--error",
        "--strict",
        "--metrics=off",
        "--disable-version-check",
        "--no-rewrite-rule-ids",
        "--disable-nosem",
        ".",
    )
    run(sys.executable, "scripts/handoff_check.py")
    run(sys.executable, "scripts/sync_agent_files.py", "--check")
    run(sys.executable, "scripts/generate_schemas.py", "--check")
    offline_tests(coverage=True)


def schemas() -> None:
    """Regenerate schemas/*.json from the contract models."""
    run(sys.executable, "scripts/generate_schemas.py")


def main() -> None:
    """Dispatch the same targets exposed by the Makefile."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        choices=(
            "setup",
            "check",
            "test",
            "test-live",
            "schemas",
            "golden",
            "handoff-check",
            "sync-agent-files",
        ),
    )
    parser.add_argument("--needs", default="", help="Comma-separated live test resources")
    args = parser.parse_args()
    os.chdir(ROOT)
    if args.target == "setup":
        run("pre-commit", "install")
    elif args.target == "check":
        check()
    elif args.target == "test":
        offline_tests()
    elif args.target == "test-live":
        needs = tuple(need.strip() for need in args.needs.split(",") if need.strip())
        if not needs or set(needs) - set(LIVE_NEEDS):
            parser.error("--needs must list resources from: " + ", ".join(LIVE_NEEDS))
        pytest_command("-m", "live", "--live-needs", ",".join(needs))
    elif args.target == "schemas":
        schemas()
    elif args.target == "golden":
        pytest_command("-m", "golden", "--update-golden")
    elif args.target == "handoff-check":
        run(sys.executable, "scripts/handoff_check.py")
    elif args.target == "sync-agent-files":
        run(sys.executable, "scripts/sync_agent_files.py")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
    except FileNotFoundError as error:
        sys.exit(
            f"Missing development tool: {error.filename}. Run uv sync --locked --all-packages."
        )
