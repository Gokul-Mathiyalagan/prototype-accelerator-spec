"""Integration tests for the offline Semgrep policy guard."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / ".semgrep/ai-endpoints.yml"


def scan(root: Path, files: dict[str, str]) -> dict:
    """Scan synthetic product files using local rules and no remote configuration."""
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    result = subprocess.run(
        [
            "semgrep",
            "scan",
            "--config",
            str(RULES),
            "--json",
            "--error",
            "--quiet",
            "--strict",
            "--metrics=off",
            "--disable-version-check",
            "--no-rewrite-rule-ids",
            "--disable-nosem",
            "--no-git-ignore",
            ".",
        ],
        cwd=root,
        env={**os.environ, "SEMGREP_SEND_METRICS": "off"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=120,
    )
    report = json.loads(result.stdout)
    assert not report["errors"], report["errors"]
    assert result.returncode == (1 if report["results"] else 0), result.stderr
    return report


def test_planted_sdk_import_is_rejected(tmp_path: Path) -> None:
    planted = (ROOT / "tests/fixtures/security/forbidden-sdk.py").read_text(encoding="utf-8")
    report = scan(tmp_path, {"packages/planted/src/planted/__init__.py": planted})
    assert {finding["check_id"] for finding in report["results"]} == {"forbidden-model-sdk"}


def test_sdk_aliases_submodules_and_all_disallowed_providers(tmp_path: Path) -> None:
    imports = [
        "import anthropic as vendor",
        "from anthropic.types import Message",
        "import google.generativeai",
        "from google import genai",
        "from google import generativeai",
        "import vertexai",
        "import cohere",
        "import mistralai",
        "import litellm",
        "import langchain_openai",
        "import langchain_anthropic",
        "import langchain_google_genai",
    ]
    report = scan(tmp_path, {"packages/planted/providers.py": "\n".join(imports)})
    assert {finding["start"]["line"] for finding in report["results"]} == set(
        range(1, len(imports) + 1)
    )


def test_only_azure_clients_inside_gateway_are_allowed(tmp_path: Path) -> None:
    files = {
        "packages/accel-core/src/accel_core/gateway/allowed.py": (
            "import openai\nfrom openai import AzureOpenAI, AsyncAzureOpenAI\n"
            "client = openai.AzureOpenAI()\n"
        ),
        "packages/accel-core/src/accel_core/gateway/forbidden.py": (
            "from openai import OpenAI as Client\nclient = Client()\n"
            "import openai as sdk\nclient = sdk.AsyncOpenAI()\n"
        ),
        "packages/accel-core/src/accel_core/gateway_extra/bypass.py": "import openai\n",
        "packages/accel-extract/src/accel_extract/outside.py": ("from openai import AzureOpenAI\n"),
    }
    report = scan(tmp_path, files)
    paths = {finding["path"].replace("\\", "/") for finding in report["results"]}
    assert paths == set(files) - {"packages/accel-core/src/accel_core/gateway/allowed.py"}
    assert {finding["check_id"] for finding in report["results"]} == {
        "openai-outside-gateway",
        "non-azure-openai-client",
    }


def test_hosts_templates_mcp_and_development_exclusions(tmp_path: Path) -> None:
    files = {
        "blueprints/example/settings.toml": (
            'a = "https://api.openai.com/v1"\nb = "https://api.anthropic.com/v1"\n'
            'c = "https://generativelanguage.googleapis.com"\n'
            'd = "https://aiplatform.googleapis.com"\n'
        ),
        "templates/skill/client.py": "import anthropic\n",
        ".vscode/mcp.json": '{"servers":{"rea":{"url":"https://example.invalid/mcp"}}}',
        "blueprints/example/mcp.yaml": "servers:\n  accel:\n    url: https://example.invalid\n",
        "blueprints/quoted/mcp.yaml": "servers:\n  accel:\n    'url': https://example.invalid\n",
        "blueprints/local/mcp.json": '{"servers":{"accel":{"command":"accel-mcp"}}}',
        "spec/example.py": "import anthropic\n",
        ".agents/skills/example.md": "https://api.openai.com\n",
        "handoff/log/example.md": "https://api.anthropic.com\n",
        "tests/fixtures/target/client.py": "import anthropic\n",
        "tests/fixtures/target/mcp.json": '{"servers":{"rea":{"url":"https://example.invalid"}}}',
        ".agents/example/mcp.json": '{"servers":{"rea":{"url":"https://example.invalid"}}}',
    }
    report = scan(tmp_path, files)
    counts: dict[str, int] = {}
    for finding in report["results"]:
        key = finding["path"].replace("\\", "/")
        counts[key] = counts.get(key, 0) + 1
    assert counts == {
        "blueprints/example/settings.toml": 4,
        "templates/skill/client.py": 1,
        ".vscode/mcp.json": 1,
        "blueprints/example/mcp.yaml": 1,
        "blueprints/quoted/mcp.yaml": 1,
    }


def test_skill_template_examples_use_the_gateway(tmp_path: Path) -> None:
    files = {
        ".github/skills/example/SKILL.md": "```python\nimport anthropic\n```\n",
        "templates/skill.md.template": "from openai import AzureOpenAI\n",
        "blueprints/example/skill.md": "from google import genai\n",
        ".github/skills/allowed/SKILL.md": "from accel_core.gateway import Gateway\n",
    }
    report = scan(tmp_path, files)
    assert {finding["path"].replace("\\", "/") for finding in report["results"]} == (
        set(files) - {".github/skills/allowed/SKILL.md"}
    )
    assert {finding["check_id"] for finding in report["results"]} == {"forbidden-template-sdk"}


def test_javascript_model_clients_are_rejected(tmp_path: Path) -> None:
    imports = [
        'import OpenAI from "openai";',
        'import Anthropic from "@anthropic-ai/sdk";',
        'const sdk = require("@google/genai");',
        'import { CohereClient } from "cohere-ai";',
    ]
    report = scan(tmp_path, {"blueprints/example/client.ts": "\n".join(imports)})
    assert {finding["start"]["line"] for finding in report["results"]} == {1, 2, 3, 4}
    assert {finding["check_id"] for finding in report["results"]} == {"forbidden-javascript-sdk"}
