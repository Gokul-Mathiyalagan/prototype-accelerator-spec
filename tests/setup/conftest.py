"""Docker helpers shared by the install.sh container tests."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def docker_ready() -> bool:
    """True when the Docker CLI exists and its daemon answers."""
    docker = shutil.which("docker")
    if docker is None:
        return False
    return subprocess.run([docker, "info"], capture_output=True, check=False).returncode == 0


def image_tag(dockerfile: Path) -> str:
    """Tag a test image by the hash of its Dockerfile, so edits rebuild it."""
    digest = hashlib.sha256(dockerfile.read_bytes()).hexdigest()[:12]
    name = dockerfile.name.lower().replace("dockerfile", "setup").replace(".", "-")
    return f"accel-{name}-test:{digest}"


@pytest.fixture(scope="session")
def docker_image() -> Callable[[Path], str]:
    """Return a function that builds a Dockerfile's image (once) and returns its tag."""
    if not docker_ready():
        pytest.skip("Docker isn't available; the install.sh container tests need it")

    def build(dockerfile: Path) -> str:
        tag = image_tag(dockerfile)
        exists = subprocess.run(
            ["docker", "image", "inspect", tag], capture_output=True, check=False
        )
        if exists.returncode != 0:
            subprocess.run(
                ["docker", "build", "-q", "-t", tag, "-f", str(dockerfile), str(dockerfile.parent)],
                check=True,
                capture_output=True,
            )
        return tag

    return build


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """The platform repo, mounted read-only at /repo in the containers."""
    return ROOT
