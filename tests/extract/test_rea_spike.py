"""Live: REA from Python over MCP stdio (T-008). REA runs in the T-005 live container.

Run with `make test-live NEEDS=rea,ghidra` (Docker required). It reuses the
`accel-live-home` volume, installing REA there first if needed, and analyzes the
fixture's built web bundle, a recorded HAR and the permissive native library.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SSO = ROOT / "tests" / "fixtures" / "repos" / "fastapi-react-sso"
HAR = ROOT / "tests" / "fixtures" / "har" / "fastapi-react-sso.har"
TINYMATH = ROOT / "tests" / "fixtures" / "repos" / "native-sdk-sample" / "vendor" / "tinymath"
DOC = ROOT / "spec" / "reference" / "rea-tools.md"


def _documented_tools() -> set[str]:
    table = DOC.read_text(encoding="utf-8").split("### MCP tools", 1)[1].split("### CLI", 1)[0]
    return set(re.findall(r"^\| `([a-z0-9_]+)` \|", table, flags=re.MULTILINE))


def _built_web_bundle(image: str, into: Path) -> Path:
    container = subprocess.run(
        ["docker", "create", image], capture_output=True, text=True, check=True
    ).stdout.strip()
    try:
        subprocess.run(["docker", "cp", f"{container}:/service/static", str(into)], check=True)
    finally:
        subprocess.run(
            ["docker", "container", "remove", container], capture_output=True, check=False
        )
    return into


async def _session(server: list[str], calls: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    replies: dict[str, Any] = {}
    params = StdioServerParameters(command=server[0], args=server[1:])
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        listed = await session.list_tools()
        replies["tools/list"] = {tool.name for tool in listed.tools}
        for name, arguments in calls:
            result = await session.call_tool(name, arguments)
            text = "".join(getattr(item, "text", "") for item in result.content)
            replies[name] = {"is_error": result.isError, "body": json.loads(text)}
    return replies


@pytest.mark.live_rea
@pytest.mark.live_ghidra
def test_rea_analyzes_bundle_har_and_native_binary_from_python(
    tmp_path: Path, docker_image: Callable[..., str], repo_root: Path
) -> None:
    rea_image = docker_image(ROOT / "tests" / "setup" / "Dockerfile.live")
    web_image = docker_image(SSO / "Dockerfile", SSO)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    _built_web_bundle(web_image, inputs / "web-dist")
    shutil.copy(HAR, inputs / "capture.har")
    shutil.copy(TINYMATH / "lib" / "libtinymath.so", inputs / "libtinymath.so")

    mounts = ["-v", "accel-live-home:/accel", "-v", f"{repo_root}:/repo:ro"]
    install = ["bash", "/repo/setup/install.sh", "install"]
    subprocess.run(
        ["docker", "run", "--rm", *mounts, "-e", "ACCEL_HOME=/accel/home", rea_image, *install],
        check=True,
        timeout=3600,
    )
    server = [
        "docker", "run", "-i", "--rm", *mounts, "-v", f"{inputs}:/inputs:ro",
        "-e", "ACCEL_HOME=/accel/home", rea_image, "bash", "/repo/setup/rea-mcp.sh",
    ]  # fmt: skip
    replies = asyncio.run(
        _session(
            server,
            [
                ("inspect_analysis_settings", {}),
                (
                    "inspect_web_network_capture",
                    {"capture_path": "/inputs/capture.har", "format": "har", "detail": "complete"},
                ),
                (
                    "inspect_native_exports",
                    {"path": "/inputs/libtinymath.so", "detail": "complete"},
                ),
                ("open_binary", {"path": "/inputs/libtinymath.so", "provider_id": "ghidra"}),
                ("analyze_function", {"procedure": "tm_clamp", "detail": "complete"}),
                ("analyze_javascript_application", {"input_path": "/inputs/web-dist"}),
            ],
        )
    )

    assert replies["tools/list"] == _documented_tools(), "regenerate spec/reference/rea-tools.md"
    for name, reply in replies.items():
        if name != "tools/list":
            assert reply["is_error"] is False, (name, reply["body"])

    assert "900000" in json.dumps(replies["inspect_analysis_settings"]["body"])

    har = replies["inspect_web_network_capture"]["body"]["normalized_result"]
    statuses = [record["reported"]["response"]["status"] for record in har["records"]]
    assert (har["total_records"], statuses) == (5, [401, 200, 200, 403, 200])

    exports = replies["inspect_native_exports"]["body"]["normalized_result"]["exports"]
    assert {export["name"] for export in exports} == {"tm_add", "tm_mul", "tm_clamp", "tm_version"}

    assert replies["open_binary"]["body"]["result"]["format"] == "elf"
    function = json.dumps(replies["analyze_function"]["body"])
    assert "int tm_clamp(int param_1,int param_2,int param_3)" in function

    bundle = replies["analyze_javascript_application"]["body"]
    sources = bundle["normalized_result"]["route_inventory"]["sources"]
    assert [source["path"] for source in sources] == [
        p.relative_to(inputs / "web-dist").as_posix() for p in (inputs / "web-dist").rglob("*.js")
    ]
    # Known limit (spec/reference/rea-tools.md): minified bundles may exhaust the default
    # heap; the analysis still returns Evidence and says why a source is unavailable.
    for source in sources:
        assert source["status"] == "available" or "Resource constraint" in source["reason"]
