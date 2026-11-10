"""fastapi-react-sso builds, passes its own tests and runs with the mock IdP; the native
sample's ctypes caller works. Needs Docker (skipped without it); the first build downloads
the fixture's npm and pip packages, and later runs reuse the cached image.
"""

from __future__ import annotations

import subprocess
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

REPOS = Path(__file__).resolve().parents[1] / "fixtures" / "repos"
SSO = REPOS / "fastapi-react-sso"
NATIVE = REPOS / "native-sdk-sample"

# Runs inside the network with httpx (installed in the app image).
SMOKE = """
import httpx
app = "http://app:8000"
def token(user):
    return httpx.post(f"{app}/auth/token", json={"username": user}).json()["access_token"]
def get(path, user=None):
    headers = {"Authorization": f"Bearer {token(user)}"} if user else {}
    return httpx.get(f"{app}{path}", headers=headers)
assert get("/healthz").json() == {"status": "ok"}
assert get("/api/v1/teams/1/members").status_code == 401
members = get("/api/v1/teams/1/members", "bob").json()
assert members["total"] == 3 and "email" not in members["items"][0]
assert get("/api/v1/teams/1/members.csv", "bob").status_code == 403
assert get("/api/v1/teams/1/members.csv", "alice").text.startswith("name,role,start_date")
assert "<title>Team Insights</title>" in get("/teams/1").text
print("smoke ok")
"""

WAIT = """
import httpx, time
for _ in range(60):
    try:
        httpx.get("http://app:8000/healthz")
        break
    except httpx.HTTPError:
        time.sleep(1)
"""


def _docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=check, timeout=600
    )


@pytest.fixture(scope="module")
def image(docker_image: Callable[..., str]) -> str:
    """Build the fixture image; its build runs the web (vitest) and service (pytest) tests."""
    return docker_image(SSO / "Dockerfile", SSO)


@pytest.fixture(scope="module")
def stack(image: str) -> Iterator[str]:
    """Start the mock IdP and the app on a private network; yield the network name."""
    name = f"accel-fixture-{uuid.uuid4().hex[:8]}"
    _docker("network", "create", name)
    common = ["run", "-d", "--rm", "--network", name]
    idp = [
        "uvicorn",
        "mock_idp:app",
        "--app-dir",
        "/mock-idp",
        "--host",
        "0.0.0.0",
        "--port",
        "9000",
    ]
    app_env = ["OIDC_ISSUER=http://idp:9000", "AUTH_MODE=mock", "LLM_MODE=fake"]
    app_env.append("DATABASE_URL=sqlite:////tmp/ti.db")
    try:
        idp_env = ["-e", "MOCK_IDP_ISSUER=http://idp:9000"]
        _docker(*common, "--name", f"{name}-idp", "--network-alias", "idp", *idp_env, image, *idp)
        env = [arg for value in app_env for arg in ("-e", value)]
        _docker(*common, "--name", f"{name}-app", "--network-alias", "app", *env, image)
        _docker("run", "--rm", "--network", name, image, "python", "-c", WAIT)
        yield name
    finally:
        _docker("stop", f"{name}-app", f"{name}-idp", check=False)
        _docker("network", "remove", name, check=False)


def test_app_signs_in_through_the_mock_idp_and_enforces_roles(stack: str, image: str) -> None:
    result = _docker("run", "--rm", "--network", stack, image, "python", "-c", SMOKE, check=False)
    assert result.returncode == 0, result.stderr[-3000:]
    assert "smoke ok" in result.stdout


def test_native_sample_ctypes_caller_runs(image: str) -> None:
    script = "python python/sdk_client.py && python -m pytest -q -p no:cacheprovider python/tests"
    mount = ["-v", f"{NATIVE}:/native:ro", "-w", "/native"]
    result = _docker("run", "--rm", *mount, image, "sh", "-c", script, check=False)
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    assert "tinymath 1.2.0 secretsauce 3.1.4" in result.stdout
    assert "2 passed" in result.stdout
