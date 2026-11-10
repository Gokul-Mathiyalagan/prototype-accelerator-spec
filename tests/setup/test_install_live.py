"""Live: the full install from the internet, REA's verify:ghidra, and an MCP handshake.

Runs in a Linux container (Docker), so it works on any host. ACCEL_HOME lives in the
`accel-live-home` volume, so later runs reuse the install. Run with
`make test-live NEEDS=rea,ghidra`; the first run downloads about 1 GB.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from accel_core.contracts import InstallCheck

HERE = Path(__file__).resolve().parent


@pytest.mark.live_rea
@pytest.mark.live_ghidra
def test_full_install_verify_and_mcp_handshake(
    tmp_path: Path, docker_image: Callable[[Path], str], repo_root: Path
) -> None:
    tag = docker_image(HERE / "Dockerfile.live")
    subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", "accel-live-home:/accel",
            "-v", f"{repo_root}:/repo:ro",
            "-v", f"{tmp_path}:/out",
            tag, "bash", "/repo/tests/setup/live.sh",
        ],
        check=True,
        timeout=3600,
    )  # fmt: skip
    assert (tmp_path / "finished").exists()

    def step(name: str) -> tuple[int, str, str]:
        code = int((tmp_path / f"{name}.exit").read_text().strip())
        out = (tmp_path / f"{name}.stdout").read_text(encoding="utf-8")
        err = (tmp_path / f"{name}.stderr").read_text(encoding="utf-8")
        return code, out, err

    for name in ("install", "rerun", "check", "mcp"):
        code, _, err = step(name)
        assert code == 0, f"{name} exited {code}:\n{err[-4000:]}"

    assert "Downloading" not in step("rerun")[2]
    check = InstallCheck.model_validate_json(step("check")[1])
    assert check.ok and check.platform == "linux-x64"

    reply = json.loads(step("mcp")[1])
    assert reply["id"] == 1
    assert reply["result"]["serverInfo"]["name"] == "rea"

    # Last, so a failure here can't hide the results above.
    code, _, err = step("verify")
    assert code == 0, f"verify exited {code}:\n{err[-4000:]}"
