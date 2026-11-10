"""Integration tests for the package dependency rules from spec/01."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULES = ("core", "extract", "skills", "package", "design", "sdlc", "evals", "mcp", "cli")


@pytest.mark.parametrize(
    "source,target,allowed",
    [
        ("core", "extract", False),
        ("extract", "skills", False),
        ("skills", "package", False),
        ("design", "sdlc", False),
        ("package", "extract", False),
        ("evals", "sdlc", False),
        ("sdlc", "skills", False),
        ("mcp", "evals", False),
        ("package", "skills", True),
        ("sdlc", "package", True),
        ("mcp", "sdlc", True),
        ("cli", "mcp", True),
    ],
)
def test_internal_import_contract(tmp_path: Path, source: str, target: str, allowed: bool) -> None:
    for name in MODULES:
        module = tmp_path / f"accel_{name}"
        module.mkdir()
        (module / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / f"accel_{source}/__init__.py").write_text(
        f"import accel_{target}\n", encoding="utf-8"
    )
    result = subprocess.run(
        ["lint-imports", "--config", str(ROOT / ".importlinter"), "--no-cache"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == (0 if allowed else 1), result.stdout + result.stderr
    if not allowed:
        assert "BROKEN" in result.stdout
