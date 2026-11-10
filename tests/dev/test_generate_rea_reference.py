"""The REA reference generator, and the committed HAR fixture it's documented against."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "generate_rea_reference", ROOT / "scripts" / "generate_rea_reference.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GEN = _load()
TOOLS = [
    {
        "name": "inspect_b",
        "description": "Inspect B. More detail here.",
        "inputSchema": {"required": ["path"]},
        "annotations": {"readOnlyHint": True},
    },
    {"name": "analyze_a", "description": "Analyze A | with a pipe.", "inputSchema": {}},
]
HELP = """rea@6.8.0

Usage: rea <command>

Commands:
  analyze           Get an overview of an app
  doctor            Check whether REA is ready

Options:
  --timings  Write measured command timing to stderr.
"""


def test_tools_from_accepts_a_whole_reply_or_its_result() -> None:
    names = [t["name"] for t in GEN.tools_from({"jsonrpc": "2.0", "result": {"tools": TOOLS}})]
    assert names == ["analyze_a", "inspect_b"]
    assert [t["name"] for t in GEN.tools_from({"tools": TOOLS})] == names


def test_commands_from_reads_only_the_commands_section() -> None:
    assert GEN.commands_from(HELP) == [
        ("analyze", "Get an overview of an app"),
        ("doctor", "Check whether REA is ready"),
    ]


def test_render_builds_both_tables_with_escaped_cells() -> None:
    block = GEN.render(GEN.tools_from({"tools": TOOLS}), GEN.commands_from(HELP))
    assert block.startswith(GEN.START) and block.endswith(GEN.END)
    assert "### MCP tools (2)" in block and "### CLI commands (2)" in block
    assert "| `analyze_a` | (none) |  | Analyze A \\| with a pipe. |" in block
    assert "| `inspect_b` | path | yes | Inspect B. |" in block


def test_update_replaces_only_the_generated_block(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text(f"intro\n\n{GEN.START}\nold\n{GEN.END}\n\noutro\n", encoding="utf-8")
    tools_json = tmp_path / "tools.json"
    tools_json.write_text(json.dumps({"result": {"tools": TOOLS}}), encoding="utf-8")
    cli = tmp_path / "help.txt"
    cli.write_text(HELP, encoding="utf-8")
    assert GEN.main([str(tools_json), str(cli), "--doc", str(doc)]) == 0
    text = doc.read_text(encoding="utf-8")
    assert text.startswith("intro\n\n") and text.endswith("\n\noutro\n")
    assert "old" not in text and "`inspect_b`" in text


def test_committed_reference_lists_the_pinned_servers_tools() -> None:
    text = (ROOT / "spec" / "reference" / "rea-tools.md").read_text(encoding="utf-8")
    assert "### MCP tools (253)" in text
    for tool in ("inspect_analysis_settings", "analyze_javascript_application", "analyze_function"):
        assert f"| `{tool}` |" in text


def test_har_fixture_is_valid_har_with_no_credentials() -> None:
    raw = (ROOT / "tests" / "fixtures" / "har" / "fastapi-react-sso.har").read_text(
        encoding="utf-8"
    )
    har = json.loads(raw)
    assert har["log"]["version"] == "1.2"
    entries = har["log"]["entries"]
    assert [e["response"]["status"] for e in entries] == [401, 200, 200, 403, 200]
    assert "eyJ" not in raw and "Bearer " not in raw
    auth = [
        h["value"] for e in entries for h in e["request"]["headers"]
        if h["name"].lower() == "authorization"
    ]  # fmt: skip
    assert auth and set(auth) == {"[REDACTED]"}
