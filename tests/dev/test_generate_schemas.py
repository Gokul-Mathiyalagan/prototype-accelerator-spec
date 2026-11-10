"""The schema generator writes every contract schema and detects drift."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "generate_schemas", ROOT / "scripts" / "generate_schemas.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GEN = _load_generator()


def test_committed_schemas_match_the_models() -> None:
    assert GEN.drift(ROOT / "schemas") == []


def test_write_creates_one_file_per_contract_and_removes_orphans(tmp_path: Path) -> None:
    (tmp_path / "retired.schema.json").write_text("{}", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("keep", encoding="utf-8")
    GEN.write(tmp_path)
    written = sorted(path.name for path in tmp_path.glob("*.schema.json"))
    assert written == sorted(f"{name}.schema.json" for name in GEN.CONTRACTS)
    assert (tmp_path / "notes.txt").exists()
    assert GEN.drift(tmp_path) == []
    raw = (tmp_path / "finding.schema.json").read_bytes()
    assert raw.endswith(b"}\n") and b"\r\n" not in raw


def test_drift_reports_missing_stale_and_orphaned(tmp_path: Path) -> None:
    GEN.write(tmp_path)
    (tmp_path / "task.schema.json").unlink()
    (tmp_path / "finding.schema.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "retired.schema.json").write_text("{}\n", encoding="utf-8")
    assert GEN.drift(tmp_path) == [
        "stale finding.schema.json",
        "missing task.schema.json",
        "orphaned retired.schema.json",
    ]


def test_check_mode_fails_on_drift_then_passes_after_write(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert GEN.main(["--check", "--out", str(tmp_path)]) == 1
    assert "Run `make schemas`" in capsys.readouterr().err
    assert GEN.main(["--out", str(tmp_path)]) == 0
    assert GEN.main(["--check", "--out", str(tmp_path)]) == 0
    assert "15 schemas are current." in capsys.readouterr().out


def test_make_check_runs_the_drift_check() -> None:
    dev = (ROOT / "scripts" / "dev.py").read_text(encoding="utf-8")
    assert '"scripts/generate_schemas.py", "--check"' in dev
