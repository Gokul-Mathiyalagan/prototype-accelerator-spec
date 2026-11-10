"""setup/install.sh and rea-mcp.sh in a Linux container, with downloads faked.

The container builds a fake mirror (tests/setup/make_fakes.sh) and runs every scenario in
tests/setup/scenarios.sh once; each test asserts on one scenario's recorded results.
These tests need Docker and are skipped without it.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from accel_core.contracts import InstallCheck, VersionsLock

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
INSTALL = ROOT / "setup" / "install.sh"
REA_MCP = ROOT / "setup" / "rea-mcp.sh"


def _docker_ready() -> bool:
    docker = shutil.which("docker")
    if docker is None:
        return False
    return subprocess.run([docker, "info"], capture_output=True, check=False).returncode == 0


def image_tag(dockerfile: Path) -> str:
    """Tag a test image by the hash of its Dockerfile, so edits rebuild it."""
    digest = hashlib.sha256(dockerfile.read_bytes()).hexdigest()[:12]
    return f"accel-{dockerfile.stem.lower()}-test:{digest}"


def build_image(dockerfile: Path) -> str:
    """Build the image unless it already exists; return its tag."""
    tag = image_tag(dockerfile)
    exists = subprocess.run(["docker", "image", "inspect", tag], capture_output=True, check=False)
    if exists.returncode != 0:
        subprocess.run(
            ["docker", "build", "-q", "-t", tag, "-f", str(dockerfile), str(dockerfile.parent)],
            check=True,
            capture_output=True,
        )
    return tag


@pytest.fixture(scope="session")
def out(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if not _docker_ready():
        pytest.skip("Docker isn't available; the install.sh container tests need it")
    tag = build_image(HERE / "Dockerfile")
    results = tmp_path_factory.mktemp("setup-scenarios")
    subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{ROOT}:/repo:ro",
            "-v", f"{results}:/out",
            tag, "bash", "/repo/tests/setup/scenarios.sh",
        ],
        check=True,
        capture_output=True,
        timeout=600,
    )  # fmt: skip
    assert (results / "finished").exists(), "scenarios.sh didn't finish"
    return results


def _exit(out: Path, name: str) -> int:
    return int((out / name / "exit").read_text().strip())


def _text(out: Path, name: str, stream: str = "stderr") -> str:
    return (out / name / stream).read_text(encoding="utf-8")


def _check(out: Path, name: str) -> InstallCheck:
    return InstallCheck.model_validate_json(_text(out, name, "stdout"))


# ── --check ───────────────────────────────────────────────────────────────────


def test_check_on_a_fresh_machine_reports_missing_and_writes_nothing(out: Path) -> None:
    assert _exit(out, "check-empty") == 1
    check = _check(out, "check-empty")
    assert not check.ok
    assert check.platform == "linux-x64"
    statuses = {c.name: c.status for c in check.components}
    assert statuses == {
        "node": "missing",
        "jdk": "missing",
        "ghidra": "missing",
        "ghidra-arm64-decompiler": "ok",
        "rea": "missing",
        "env": "missing",
    }
    assert check.next_action == "Run setup/install.sh install node jdk ghidra rea env"
    assert not (out / "check-empty" / "home-created").exists()


def test_check_after_install_is_ready_in_json_and_text(out: Path) -> None:
    assert _exit(out, "install") == 0
    assert _exit(out, "check-after") == 0
    check = _check(out, "check-after")
    assert check.ok and check.next_action == ""
    assert [c.name for c in check.components] == [
        "node", "jdk", "ghidra", "ghidra-arm64-decompiler", "rea", "env",
    ]  # fmt: skip
    text = _text(out, "check-text", "stdout")
    assert "node                     ok             v24.22.1" in text
    assert text.rstrip().endswith("Ready.")


def test_a_wrong_version_is_reported_and_install_fixes_it(out: Path) -> None:
    assert _exit(out, "check-wrong-version") == 1
    check = _check(out, "check-wrong-version")
    ghidra = next(c for c in check.components if c.name == "ghidra")
    assert (ghidra.status, ghidra.detail) == ("wrong_version", "found 12.1.3, need 12.1.4")
    assert check.next_action == "Run setup/install.sh install ghidra"
    assert _exit(out, "fix-wrong-version") == 0
    assert "ghidra: installed (12.1.4)" in _text(out, "fix-wrong-version")


# ── install ───────────────────────────────────────────────────────────────────


def test_rerunning_after_success_changes_nothing(out: Path) -> None:
    assert _exit(out, "rerun") == 0
    before = (out / "install" / "snapshot").read_text()
    assert before.strip(), "the snapshot is empty"
    assert (out / "rerun" / "snapshot").read_text() == before
    stderr = _text(out, "rerun")
    assert stderr.count("already installed") == 6
    assert "Downloading" not in stderr


def test_nothing_is_written_outside_accel_home(out: Path) -> None:
    assert (out / "install" / "home-contents").read_text() == ""
    assert (out / "install" / "outside-writes").read_text() == ""


def test_npm_runs_without_git_hooks_and_caches_inside_accel_home(out: Path) -> None:
    calls = (out / "install" / "npm-calls.log").read_text().splitlines()
    assert calls == [
        "ci --no-audit --no-fund|HUSKY=0|cache=/accel/linux/cache/npm",
        "run build|HUSKY=0|cache=/accel/linux/cache/npm",
    ]


def test_rea_env_points_at_the_installed_tools_with_long_timeouts(out: Path) -> None:
    assert (out / "install" / "rea.env").read_text() == (
        "GHIDRA_INSTALL_DIR=/accel/linux/tools/ghidra\n"
        "JAVA_HOME=/accel/linux/tools/jdk\n"
        "REA_GHIDRA_STARTUP_TIMEOUT_MS=900000\n"
        "REA_GHIDRA_DECOMPILE_TIMEOUT_SECONDS=120\n"
    )


def test_mirror_replaces_hosts_and_logs_go_to_accel_home(out: Path) -> None:
    log = (out / "install" / "log").read_text()
    assert "Downloading file:///fakes/mirror/dist/v24.22.1/node-v24.22.1-linux-x64.tar.gz" in log
    assert (
        "file:///fakes/mirror/adoptium/temurin21-binaries/releases/download/jdk-21.0.13%2B9/"
        "OpenJDK21U-jdk_x64_linux_hotspot_21.0.13_9.tar.gz" in log
    )
    assert "https://" not in log


def test_only_the_requested_component_is_installed(out: Path) -> None:
    assert _exit(out, "only-jdk") == 0
    assert (out / "only-jdk" / "tools").read_text().split() == ["jdk"]


def test_apple_silicon_builds_the_arm64_decompiler(out: Path) -> None:
    assert _exit(out, "arm64") == 0
    assert (out / "arm64" / "make-args").read_text().strip() == "-arch arm64 mac_arm_64"
    assert (out / "arm64" / "decompiler-installed").exists()
    assert (
        "JAVA_HOME=/accel/arm64/tools/jdk/Contents/Home\n"
        in (out / "arm64" / "rea.env").read_text()
    )
    check = _check(out, "arm64-check")
    decompiler = next(c for c in check.components if c.name == "ghidra-arm64-decompiler")
    assert (check.platform, decompiler.status, decompiler.detail) == ("darwin-arm64", "ok", "built")


# ── Failures and exit codes ───────────────────────────────────────────────────


def test_checksum_mismatch_exits_3_and_installs_nothing(out: Path) -> None:
    assert _exit(out, "checksum") == 3
    assert "Checksum mismatch for node-v24.22.1-linux-x64.tar.gz" in _text(out, "checksum")
    assert (out / "checksum" / "tools").read_text() == ""
    assert (out / "checksum" / "downloads").read_text() == ""


def test_download_failure_exits_4(out: Path) -> None:
    assert _exit(out, "download-fail") == 4
    assert "Download failed: file:///fakes/mirror/NationalSecurityAgency/" in _text(
        out, "download-fail"
    )


def test_missing_prerequisite_exits_2_before_writing(out: Path) -> None:
    assert _exit(out, "prereq") == 2
    assert "Missing prerequisites: git." in _text(out, "prereq")
    assert not (out / "prereq" / "home-created").exists()


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("unknown-component", "Unknown component 'python'"),
        ("bad-usage", "install.sh install [component]"),
    ],
)
def test_usage_errors_exit_1(out: Path, name: str, message: str) -> None:
    assert _exit(out, name) == 1
    assert message in _text(out, name)


def test_verify_runs_reas_ghidra_check(out: Path) -> None:
    assert _exit(out, "verify") == 0
    assert "REA's Ghidra check passed." in _text(out, "verify")


def test_failed_verify_exits_5_and_prints_the_last_50_log_lines(out: Path) -> None:
    assert _exit(out, "verify-fail") == 5
    stderr = _text(out, "verify-fail")
    tail = stderr.split("--- last 50 lines of ", 1)[1].splitlines()[1:]
    assert len(tail) == 50
    assert "fake verify failure" in stderr


def test_verify_before_install_says_what_to_do(out: Path) -> None:
    assert _exit(out, "verify-not-installed") == 1
    assert "Run setup/install.sh install first." in _text(out, "verify-not-installed")


# ── rea-mcp.sh ────────────────────────────────────────────────────────────────


def test_rea_mcp_starts_reas_mcp_server_with_rea_env(out: Path) -> None:
    assert _exit(out, "rea-mcp") == 0
    assert _text(out, "rea-mcp", "stdout").splitlines() == [
        "node /accel/linux/tools/rea/scripts/rea.mjs mcp",
        "GHIDRA_INSTALL_DIR=/accel/linux/tools/ghidra",
        "REA_GHIDRA_STARTUP_TIMEOUT_MS=900000",
    ]


def test_rea_mcp_explains_when_setup_has_not_run(out: Path) -> None:
    assert _exit(out, "rea-mcp-missing") == 1
    assert _text(out, "rea-mcp-missing", "stdout") == ""
    assert "Run /accel-setup in Copilot Chat" in _text(out, "rea-mcp-missing")


# ── Static checks (no Docker) ─────────────────────────────────────────────────


def test_versions_lock_matches_the_contract_and_pins() -> None:
    lock = VersionsLock.model_validate(
        yaml.safe_load((ROOT / "setup" / "versions.lock").read_text())
    )
    assert str(lock.rea.repo) == "https://github.com/morluto/rea"
    assert lock.ghidra.version == "12.1.4"
    assert lock.jdk.version.startswith("21.")
    assert lock.ghidra.version in str(lock.ghidra.url)


def test_the_fake_lock_matches_the_contract(out: Path) -> None:
    VersionsLock.model_validate(yaml.safe_load((out / "fake-versions.lock").read_text()))


@pytest.mark.parametrize("script", [INSTALL, REA_MCP])
def test_scripts_are_strict_bash_with_no_sudo_or_profile_edits(script: Path) -> None:
    text = script.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "\nset -euo pipefail\n" in text
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    assert not re.search(r"\bsudo\b", code)
    assert not re.search(r"\.(bash_profile|bashrc|zshrc|zprofile|profile)\b", code)
    assert json.dumps(code)  # the script is valid UTF-8 text
