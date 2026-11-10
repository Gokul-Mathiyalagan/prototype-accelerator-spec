"""`accel setup` and `accel doctor` wrap install.sh; the tool runner is faked here."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from accel_cli.commands import setup as setup_cmd
from accel_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def _check_json(ok: bool) -> str:
    status = "ok" if ok else "missing"
    return json.dumps(
        {
            "ok": ok,
            "platform": "linux-x64",
            "components": [
                {"name": "node", "status": "ok", "detail": "v24.22.1"},
                {"name": "rea", "status": status, "detail": "f5a12cc" if ok else "not installed"},
            ],
            "next_action": "" if ok else "Run setup/install.sh install rea",
        }
    )


class FakeTools:
    """Replaces run_tool: answers install.sh and version probes, and records calls."""

    def __init__(
        self, *, ready: bool = True, install_exit: int = 0, check_stdout: str | None = None
    ):
        self.ready = ready
        self.install_exit = install_exit
        self.check_stdout = check_stdout
        self.calls: list[list[str]] = []

    def __call__(
        self, command: list[str], *, capture: bool = True
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(command)
        if command[-2:] == ["--check", "--json"]:
            stdout = self.check_stdout if self.check_stdout is not None else _check_json(self.ready)
            return subprocess.CompletedProcess(
                command, 0 if self.ready else 1, stdout, "error: boom\n"
            )
        if "install" in command:
            return subprocess.CompletedProcess(command, self.install_exit, None, None)
        return subprocess.CompletedProcess(command, 0, f"{Path(command[0]).name} 1.0.0\n", "")


@pytest.fixture
def tools(monkeypatch: pytest.MonkeyPatch) -> FakeTools:
    fake = FakeTools()
    monkeypatch.setattr(setup_cmd, "run_tool", fake)
    monkeypatch.setattr(setup_cmd.shutil, "which", lambda name: f"/usr/bin/{name}")
    return fake


def test_setup_check_json_passes_the_install_check_through(tools: FakeTools) -> None:
    result = runner.invoke(app, ["setup", "--check", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["check"]["components"][1] == {"name": "rea", "status": "ok", "detail": "f5a12cc"}
    assert "installer_exit_code" not in payload
    assert tools.calls[0][0] == "/usr/bin/bash"
    assert tools.calls[0][1].replace("\\", "/").endswith("setup/install.sh")


def test_setup_check_text_and_not_ready_exits_1(tools: FakeTools) -> None:
    tools.ready = False
    result = runner.invoke(app, ["setup", "--check"])
    assert result.exit_code == 1
    assert "rea                      missing        not installed" in result.stdout
    assert "Next: Run setup/install.sh install rea" in result.stdout


def test_setup_installs_the_requested_components_then_reports(tools: FakeTools) -> None:
    result = runner.invoke(app, ["setup", "--json", "node", "rea"])
    assert result.exit_code == 0, result.output
    assert tools.calls[0][2:] == ["install", "node", "rea"]
    payload = json.loads(result.stdout)
    assert (payload["ok"], payload["installer_exit_code"]) == (True, 0)


@pytest.mark.parametrize(("installer", "cli"), [(2, 3), (3, 4), (4, 4), (5, 4), (1, 1), (9, 1)])
def test_installer_failures_map_to_cli_exit_codes(
    tools: FakeTools, installer: int, cli: int
) -> None:
    tools.install_exit = installer
    result = runner.invoke(app, ["setup", "--json"])
    assert result.exit_code == cli
    assert json.loads(result.stdout)["installer_exit_code"] == installer


def test_setup_check_rejects_components(tools: FakeTools) -> None:
    result = runner.invoke(app, ["setup", "--check", "rea"])
    assert result.exit_code == 2
    assert tools.calls == []


def test_unparseable_check_output_reports_the_installers_last_error(tools: FakeTools) -> None:
    tools.check_stdout = "not json"
    result = runner.invoke(app, ["setup", "--check", "--json"])
    assert result.exit_code == 3
    assert json.loads(result.stdout) == {"ok": False, "error": "error: boom"}


def test_missing_installer_or_bash_exits_3(
    tools: FakeTools, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(setup_cmd, "find_installer", lambda: None)
    assert runner.invoke(app, ["setup"]).exit_code == 3
    result = runner.invoke(app, ["setup", "--check", "--json"])
    assert result.exit_code == 3
    assert "setup/install.sh or bash wasn't found" in json.loads(result.stdout)["error"]


def test_find_installer_locates_the_repo_script() -> None:
    found = setup_cmd.find_installer()
    assert found is not None and found.as_posix().endswith("setup/install.sh")


AZURE_ENV = {
    "AZURE_OPENAI_ENDPOINT": "https://unit.openai.azure.com/",
    "AZURE_OPENAI_API_KEY": "unit-key-123",
}


@pytest.fixture
def azure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for name, value in AZURE_ENV.items():
        monkeypatch.setenv(name, value)


def test_doctor_reports_every_check(tools: FakeTools, azure: None) -> None:
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    checks = {c["name"]: (c["ok"], c["detail"]) for c in payload["checks"]}
    assert checks == {
        "rea": (True, "ready"),
        "azure-openai": (
            True,
            "deployment gpt-6.1-sol at unit.openai.azure.com (configured; not called)",
        ),
        "copilot-cli": (True, "copilot 1.0.0"),
        "uv": (True, "uv 1.0.0"),
        "git": (True, "git 1.0.0"),
    }
    assert "unit-key-123" not in result.stdout
    assert payload["install_check"]["ok"] is True


def test_doctor_text_flags_failures_and_exits_1(
    tools: FakeTools, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tools.ready = False
    monkeypatch.chdir(tmp_path)
    for name in AZURE_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        setup_cmd.shutil, "which", lambda name: None if name == "copilot" else f"/x/{name}"
    )
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "FAIL rea            Run setup/install.sh install rea" in result.stdout
    assert "FAIL azure-openai   AZURE_OPENAI_ENDPOINT is not set." in result.stdout
    assert "FAIL copilot-cli    copilot isn't on PATH" in result.stdout
    assert result.stdout.rstrip().endswith("Not ready.")


def test_doctor_handles_a_tool_that_will_not_run(
    tools: FakeTools, azure: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(command: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
        if command[0].endswith("uv"):
            raise PermissionError(13, "Permission denied")
        if command[0].endswith("git"):
            return subprocess.CompletedProcess(command, 1, "", "")
        return tools(command, capture=capture)

    monkeypatch.setattr(setup_cmd, "run_tool", broken)
    payload = json.loads(runner.invoke(app, ["doctor", "--json"]).stdout)
    checks = {c["name"]: (c["ok"], c["detail"]) for c in payload["checks"]}
    assert checks["uv"] == (False, "uv didn't run: Permission denied")
    assert checks["git"] == (False, "exit 1")


def test_run_tool_runs_a_real_command() -> None:
    result = setup_cmd.run_tool(["git", "--version"])
    assert result.returncode == 0 and result.stdout.startswith("git version")


def test_no_arguments_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "setup" in result.output and "doctor" in result.output
