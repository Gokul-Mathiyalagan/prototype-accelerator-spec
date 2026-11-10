"""The /accel-setup assets for Copilot and Claude Code (T-006, ADR-0009)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COPILOT_AGENT = ROOT / ".github" / "agents" / "accel-setup.agent.md"
COPILOT_PROMPT = ROOT / ".github" / "prompts" / "accel-setup.prompt.md"
SKILL = ROOT / ".github" / "skills" / "rea-setup" / "SKILL.md"
CLAUDE_AGENT = ROOT / ".claude" / "agents" / "accel-setup.md"
CLAUDE_COMMAND = ROOT / ".claude" / "commands" / "accel-setup.md"
ASSETS = [COPILOT_AGENT, COPILOT_PROMPT, SKILL, CLAUDE_AGENT, CLAUDE_COMMAND]
AGENTS = [COPILOT_AGENT, CLAUDE_AGENT]


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    assert match, f"{path.name} has no frontmatter"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict)
    return data


def _section(path: Path, heading: str) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"^## {heading}\n(.*?)(?=^## |\Z)", text, flags=re.MULTILINE | re.DOTALL)
    assert match, f"{path.name} has no '## {heading}'"
    return match.group(1).strip()


@pytest.mark.parametrize("path", ASSETS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_every_asset_has_valid_frontmatter_with_name_and_description(path: Path) -> None:
    meta = _frontmatter(path)
    assert isinstance(meta.get("name"), str) and meta["name"]
    description = meta.get("description")
    assert isinstance(description, str) and 0 < len(description) <= 1024


def test_skill_name_matches_its_folder() -> None:
    assert _frontmatter(SKILL)["name"] == SKILL.parent.name


def test_both_agents_state_exactly_the_same_allowed_actions() -> None:
    copilot, claude = (_section(path, "Allowed actions") for path in AGENTS)
    assert copilot == claude


def test_allowed_commands_are_only_the_installer_and_the_skill_fixes() -> None:
    allowed = _section(COPILOT_AGENT, "Allowed actions")
    commands = re.findall(r"`(bash [^`]+)`", allowed)
    assert commands and all(c.startswith("bash setup/install.sh") for c in commands)
    assert ".github/skills/rea-setup/SKILL.md" in allowed
    assert "stop and ask the user first" in allowed


@pytest.mark.parametrize("path", AGENTS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_procedure_checks_installs_verifies_then_proves_rea_works(path: Path) -> None:
    text = path.read_text(encoding="utf-8") + CLAUDE_COMMAND.read_text(encoding="utf-8")
    steps = [
        "bash setup/install.sh --check --json",
        "bash setup/install.sh install",
        "bash setup/install.sh verify",
        "inspect_analysis_settings",
    ]
    positions = [text.find(step) for step in steps]
    assert -1 not in positions and positions == sorted(positions), steps
    procedure = _section(path, "Procedure")
    assert "update" in procedure and "wrong_version" in procedure


def test_both_assistants_use_the_one_shared_skill_not_a_copy() -> None:
    for path in [*AGENTS, CLAUDE_COMMAND]:
        assert ".github/skills/rea-setup/SKILL.md" in path.read_text(encoding="utf-8")
    copies = [p for p in (ROOT / ".claude").rglob("SKILL.md") if "rea-setup" in p.parts]
    assert copies == []
    mirrored = {p.name for p in (ROOT / ".claude" / "skills").iterdir() if p.is_dir()}
    assert mirrored == {p.name for p in (ROOT / ".agents" / "skills").iterdir() if p.is_dir()}


def test_prompt_and_command_start_the_setup_agent() -> None:
    assert _frontmatter(COPILOT_PROMPT)["agent"] == "accel-setup"
    assert "`accel-setup` subagent" in CLAUDE_COMMAND.read_text(encoding="utf-8")
    assert _frontmatter(CLAUDE_AGENT)["tools"] == "Bash, Read, Grep, Glob"


SKILL_TOPICS = [
    "Wrong JAVA_HOME",
    "Missing arm64 decompiler",
    "Proxy or mirror",
    "Node mismatch",
    "Gatekeeper quarantine",
    "MCP server not starting",
    "Registry enforcement",
]


@pytest.mark.parametrize("topic", SKILL_TOPICS)
def test_rea_setup_skill_covers_each_known_failure(topic: str) -> None:
    section = _section(SKILL, topic)
    assert "Fix" in section


def test_rea_setup_fixes_never_use_sudo_or_edit_profiles() -> None:
    blocks = re.findall(r"```bash\n(.*?)```", SKILL.read_text(encoding="utf-8"), flags=re.DOTALL)
    code = "\n".join(blocks)
    assert blocks and not re.search(r"\bsudo\b", code)
    assert not re.search(r"\.(zshrc|bashrc|bash_profile|profile)\b", code)
    assert "xattr -dr com.apple.quarantine ~/.accel/tools" in code


def _servers(path: Path, key: str) -> dict[str, dict[str, object]]:
    return json.loads(path.read_text(encoding="utf-8"))[key]


def test_vscode_mcp_registers_rea_and_accel_with_workspace_folder_paths() -> None:
    servers = _servers(ROOT / ".vscode" / "mcp.json", "servers")
    assert set(servers) == {"rea", "accel"}
    assert servers["rea"]["args"] == ["${workspaceFolder}/setup/rea-mcp.sh"]
    for server in servers.values():
        assert server["type"] == "stdio" and "url" not in server
        assert "${workspaceFolder}" in " ".join(map(str, server["args"]))  # type: ignore[arg-type]
        assert not any(str(a).startswith("/") for a in server["args"])  # type: ignore[union-attr]


def test_claude_code_mcp_registers_the_same_local_servers_with_relative_paths() -> None:
    servers = _servers(ROOT / ".mcp.json", "mcpServers")
    assert set(servers) == {"rea", "accel"}
    assert servers["rea"] == {"type": "stdio", "command": "bash", "args": ["setup/rea-mcp.sh"]}
    for server in servers.values():
        assert server["type"] == "stdio" and "url" not in server
        args = " ".join(map(str, server["args"]))  # type: ignore[arg-type]
        assert "${" not in args and not args.startswith("/")
