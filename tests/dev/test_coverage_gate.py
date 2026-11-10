"""Ensure aggregate coverage cannot hide an untested workspace package."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("dev", ROOT / "scripts/dev.py")
assert SPEC is not None and SPEC.loader is not None
DEV = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEV)


@pytest.mark.parametrize("covered, passes", [(8, True), (7, False), (0, False)])
def test_per_package_coverage_gate(tmp_path: Path, covered: int, passes: bool) -> None:
    report = {
        "files": {
            f"packages/accel-{name}/src/accel_{name}/__init__.py": {
                "summary": {
                    "num_statements": 10,
                    "covered_lines": covered if name == "core" else 10,
                }
            }
            for name in (
                "core",
                "extract",
                "skills",
                "package",
                "design",
                "sdlc",
                "evals",
                "mcp",
                "cli",
            )
        }
    }
    report_path = tmp_path / "coverage.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    if passes:
        DEV.check_package_coverage(report_path)
    else:
        with pytest.raises(SystemExit, match="accel-core"):
            DEV.check_package_coverage(report_path)
