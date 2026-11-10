"""Smoke-test the installed distributions and their typing markers."""

from importlib import import_module, metadata, resources

import pytest

PACKAGES = ("core", "extract", "skills", "package", "design", "sdlc", "evals", "mcp", "cli")


@pytest.mark.parametrize("name", PACKAGES)
def test_installed_package(name: str) -> None:
    module = import_module(f"accel_{name}")
    assert module.__version__ == metadata.version(f"accel-{name}") == "0.1.0"
    assert resources.files(module).joinpath("py.typed").is_file()
