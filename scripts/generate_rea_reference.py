#!/usr/bin/env python3
"""Regenerate the tool and command tables in spec/reference/rea-tools.md.

    python scripts/generate_rea_reference.py TOOLS_JSON CLI_HELP_TXT

TOOLS_JSON is REA's MCP `tools/list` reply (the JSON-RPC message, or just its `result`);
CLI_HELP_TXT is the output of `node scripts/rea.mjs --help`. Only the block between the
generated markers is replaced; the hand-written sections stay as they are.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "spec" / "reference" / "rea-tools.md"
START = "<!-- generated:start -->"
END = "<!-- generated:end -->"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _summary(description: str, limit: int = 140) -> str:
    sentence = re.split(r"(?<=\.)\s", description.strip(), maxsplit=1)[0]
    return sentence if len(sentence) <= limit else sentence[: limit - 1].rstrip() + "…"


def tools_from(reply: dict[str, Any]) -> list[dict[str, Any]]:
    """Accept a whole JSON-RPC reply or just its result; return tools sorted by name."""
    result = reply.get("result", reply)
    return sorted(result["tools"], key=lambda tool: tool["name"])


def commands_from(help_text: str) -> list[tuple[str, str]]:
    """Parse `name   description` rows from the Commands section of the CLI help."""
    section = help_text.split("Commands:", 1)[1]
    section = re.split(r"\n\S[^\n]*:\n", section, maxsplit=1)[0]
    rows = re.findall(r"^  ([a-z][a-z0-9-]*)\s{2,}(.+)$", section, flags=re.MULTILINE)
    return sorted(rows)


def render(tools: list[dict[str, Any]], commands: list[tuple[str, str]]) -> str:
    """Render the generated block: one table of MCP tools and one of CLI commands."""
    lines = [
        START,
        "",
        f"### MCP tools ({len(tools)})",
        "",
        "| Tool | Required inputs | Read-only | Summary |",
        "|---|---|---|---|",
    ]
    for tool in tools:
        required = ", ".join(tool.get("inputSchema", {}).get("required", [])) or "(none)"
        read_only = "yes" if tool.get("annotations", {}).get("readOnlyHint") else ""
        summary = _cell(_summary(tool.get("description", "")))
        lines.append(f"| `{tool['name']}` | {_cell(required)} | {read_only} | {summary} |")
    lines += ["", f"### CLI commands ({len(commands)})", "", "| Command | Summary |", "|---|---|"]
    lines += [f"| `{name}` | {_cell(_summary(text))} |" for name, text in commands]
    lines += ["", END]
    return "\n".join(lines)


def update(doc: Path, block: str) -> None:
    """Replace the generated block in `doc`, keeping everything else."""
    text = doc.read_text(encoding="utf-8")
    before, rest = text.split(START, 1)
    after = rest.split(END, 1)[1]
    doc.write_text(before + block + after, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    """Read the two captures and rewrite the generated block."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tools_json", type=Path)
    parser.add_argument("cli_help", type=Path)
    parser.add_argument("--doc", type=Path, default=DOC)
    args = parser.parse_args(argv)
    tools = tools_from(json.loads(args.tools_json.read_text(encoding="utf-8")))
    commands = commands_from(args.cli_help.read_text(encoding="utf-8"))
    update(args.doc, render(tools, commands))
    print(f"Wrote {len(tools)} tools and {len(commands)} commands to {args.doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
