"""Verify resource-marked tests cannot run accidentally."""

from pathlib import Path

import pytest

pytest_plugins = ["pytester"]
ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "arguments, passed, skipped, deselected",
    [
        ([], 1, 6, 0),
        (["-m", "not live"], 1, 0, 6),
        (["-m", "live", "--live-needs", "azure"], 1, 5, 1),
        (["-m", "live", "--live-needs", "azure,copilot,rea,ghidra,work-repos"], 6, 0, 1),
    ],
)
def test_resource_selection(
    pytester: pytest.Pytester,
    arguments: list[str],
    passed: int,
    skipped: int,
    deselected: int,
) -> None:
    pytester.makeconftest((ROOT / "tests/conftest.py").read_text(encoding="utf-8"))
    # Register the markers in this isolated miniature test suite.
    pytester.makeini(
        "[pytest]\nmarkers =\n    live\n"
        + "".join(
            f"    live_{need}\n" for need in ("azure", "copilot", "rea", "ghidra", "work_repos")
        )
    )
    pytester.makepyfile(
        """
import pytest

def test_offline():
    pass

@pytest.mark.live_azure
def test_azure():
    pass

@pytest.mark.live_copilot
def test_copilot():
    pass

@pytest.mark.live_rea
def test_rea():
    pass

@pytest.mark.live_ghidra
def test_ghidra():
    pass

@pytest.mark.live_work_repos
def test_work_repos():
    pass

@pytest.mark.live_azure
@pytest.mark.live_copilot
def test_multiple_resources():
    pass
"""
    )
    result = pytester.runpytest(*arguments)
    result.assert_outcomes(passed=passed, skipped=skipped, deselected=deselected)
