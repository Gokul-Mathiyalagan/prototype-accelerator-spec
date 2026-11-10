"""Offline-by-default test collection and explicit live-resource opt-in."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

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


# ── Docker helpers (install.sh and fixture-repo container tests) ──────────────

_IGNORED_PARTS = {"node_modules", "dist", "__pycache__", ".pytest_cache"}


def docker_ready() -> bool:
    """True when the Docker CLI exists and its daemon answers."""
    docker = shutil.which("docker")
    if docker is None:
        return False
    return subprocess.run([docker, "info"], capture_output=True, check=False).returncode == 0


def image_tag(dockerfile: Path, context: Path | None = None) -> str:
    """Tag a test image by the hash of its Dockerfile and build context, so edits rebuild it."""
    digest = hashlib.sha256(dockerfile.read_bytes())
    if context is not None:
        for path in sorted(context.rglob("*")):
            if path.is_file() and not _IGNORED_PARTS.intersection(path.parts):
                digest.update(path.relative_to(context).as_posix().encode())
                digest.update(path.read_bytes())
    owner = (context or dockerfile.parent).name.lower()
    return (
        f"accel-{owner}-{dockerfile.name.lower().replace('.', '-')}-test:{digest.hexdigest()[:12]}"
    )


@pytest.fixture(scope="session")
def docker_image() -> Callable[..., str]:
    """Return a function that builds an image (once per content hash) and returns its tag."""
    if not docker_ready():
        pytest.skip("Docker isn't available; container tests need it")

    def build(dockerfile: Path, context: Path | None = None) -> str:
        tag = image_tag(dockerfile, context)
        exists = subprocess.run(
            ["docker", "image", "inspect", tag], capture_output=True, check=False
        )
        if exists.returncode != 0:
            subprocess.run(
                [
                    "docker",
                    "build",
                    "-q",
                    "-t",
                    tag,
                    "-f",
                    str(dockerfile),
                    str(context or dockerfile.parent),
                ],
                check=True,
                capture_output=True,
                timeout=1800,
            )
        return tag

    return build


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """The platform repo."""
    return Path(__file__).resolve().parents[1]
