"""Offline-by-default test collection and explicit live-resource opt-in."""

from __future__ import annotations

import pytest

LIVE_MARKERS = {
    "live_azure": "azure",
    "live_copilot": "copilot",
    "live_rea": "rea",
    "live_ghidra": "ghidra",
    "live_work_repos": "work-repos",
}


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register explicit resource opt-in and golden-file update switches."""
    parser.addoption("--live-needs", default="", help="Comma-separated available live resources")
    parser.addoption("--update-golden", action="store_true", help="Update reviewed golden files")


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Mark resource tests as live before -m filtering, and skip missing resources."""
    enabled = {need.strip() for need in config.getoption("--live-needs").split(",") if need.strip()}
    unknown = enabled - set(LIVE_MARKERS.values())
    if unknown:
        raise pytest.UsageError("Unknown live resources: " + ", ".join(sorted(unknown)))
    for item in items:
        required = {
            resource for marker, resource in LIVE_MARKERS.items() if item.get_closest_marker(marker)
        }
        if required:
            item.add_marker(pytest.mark.live)
        missing = required - enabled
        if missing or (item.get_closest_marker("live") and not enabled):
            reason = "Live tests need explicit --live-needs: " + ", ".join(sorted(missing))
            item.add_marker(pytest.mark.skip(reason=reason))
