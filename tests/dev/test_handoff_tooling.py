"""Integration and unit tests for handoff validation tooling and agent skill mirror."""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "handoff"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HANDOFF_CHECK = _load_module("handoff_check", ROOT / "scripts" / "handoff_check.py")
SYNC_AGENT = _load_module("sync_agent_files", ROOT / "scripts" / "sync_agent_files.py")
DEV = _load_module("dev", ROOT / "scripts" / "dev.py")


def _create_minimal_workspace(root: Path) -> None:
    (root / "tasks").mkdir(parents=True, exist_ok=True)
    (root / "handoff" / "log").mkdir(parents=True, exist_ok=True)
    (root / "spec" / "decisions").mkdir(parents=True, exist_ok=True)
    (root / ".agents" / "skills" / "demo-skill").mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "skills" / "demo-skill").mkdir(parents=True, exist_ok=True)

    shutil.copyfile(FIXTURES / "valid_tasks.yaml", root / "tasks" / "tasks.yaml")
    shutil.copyfile(FIXTURES / "valid_HANDOFF.md", root / "handoff" / "HANDOFF.md")

    log_file = root / "handoff" / "log" / "2026-11-10-antigravity-T-001.md"
    log_file.write_text("# Log\nCompleted work.\n", encoding="utf-8")

    adr_file = root / "spec" / "decisions" / "ADR-0001-example-architecture.md"
    adr_file.write_text(
        "# ADR-0001\n\n**Status:** accepted\n\nContext and decision.\n", encoding="utf-8"
    )

    skill_file = root / ".agents" / "skills" / "demo-skill" / "SKILL.md"
    skill_file.write_text("# Demo Skill\n", encoding="utf-8")
    claude_skill_file = root / ".claude" / "skills" / "demo-skill" / "SKILL.md"
    claude_skill_file.write_text("# Demo Skill\n", encoding="utf-8")
    (root / ".claude" / "skills" / "GENERATED.md").write_text("# Generated\n", encoding="utf-8")


def test_valid_fixture_passes(tmp_path: Path) -> None:
    _create_minimal_workspace(tmp_path)
    report = HANDOFF_CHECK.Report()
    tasks = HANDOFF_CHECK.check_tasks(report, root=tmp_path)
    HANDOFF_CHECK.check_handoff(report, tasks, use_git=False, root=tmp_path)
    HANDOFF_CHECK.check_logs(report, tasks, root=tmp_path)
    HANDOFF_CHECK.check_adrs(report, root=tmp_path)
    assert not report.errors, report.errors
    assert not report.warnings, report.warnings


@pytest.mark.parametrize(
    "fixture_name,expected_error",
    [
        ("tasks_unknown_status.yaml", "status 'flying' not in"),
        ("tasks_unknown_need.yaml", "needs must be a list drawn from"),
        ("tasks_missing_acceptance.yaml", "acceptance must be a non-empty list of strings"),
        ("tasks_unknown_dependency.yaml", "depends on unknown task T-999"),
        ("tasks_cycle.yaml", "dependency cycle:"),
        ("tasks_done_dep_not_done.yaml", "is done but its dependency T-001 is 'todo'"),
        ("tasks_missing_field.yaml", "missing field 'goal'"),
        ("tasks_bad_id.yaml", "must look like T-###"),
        ("tasks_duplicate_id.yaml", "duplicate id"),
        ("tasks_phase_mismatch.yaml", "id's first digit should equal phase 1"),
        ("tasks_in_progress_no_owner.yaml", "status 'in_progress' needs an owner"),
        ("tasks_blocked_no_progress.yaml", "blocked tasks must say why in 'progress'"),
        ("tasks_self_dependency.yaml", "depends on itself"),
    ],
)
def test_tasks_rule_violations(tmp_path: Path, fixture_name: str, expected_error: str) -> None:
    _create_minimal_workspace(tmp_path)
    shutil.copyfile(FIXTURES / fixture_name, tmp_path / "tasks" / "tasks.yaml")
    report = HANDOFF_CHECK.Report()
    HANDOFF_CHECK.check_tasks(report, root=tmp_path)
    assert any(expected_error in err for err in report.errors), report.errors


def test_tasks_missing_and_invalid_yaml(tmp_path: Path) -> None:
    report = HANDOFF_CHECK.Report()
    HANDOFF_CHECK.check_tasks(report, root=tmp_path)
    assert any("missing tasks" in err for err in report.errors)

    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    tasks_file = tasks_dir / "tasks.yaml"

    tasks_file.write_text("tasks: []\n", encoding="utf-8")
    report = HANDOFF_CHECK.Report()
    HANDOFF_CHECK.check_tasks(report, root=tmp_path)
    assert any("non-empty top-level 'tasks' list" in err for err in report.errors)

    tasks_file.write_text("tasks:\n  - not-a-mapping\n", encoding="utf-8")
    report = HANDOFF_CHECK.Report()
    HANDOFF_CHECK.check_tasks(report, root=tmp_path)
    assert any("must be a mapping" in err for err in report.errors)


def test_tasks_phase_owner_and_depends_validation(tmp_path: Path) -> None:
    _create_minimal_workspace(tmp_path)
    tasks_file = tmp_path / "tasks" / "tasks.yaml"
    data = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))

    data["tasks"][0]["phase"] = 9
    tasks_file.write_text(yaml.safe_dump(data), encoding="utf-8")
    report = HANDOFF_CHECK.Report()
    HANDOFF_CHECK.check_tasks(report, root=tmp_path)
    assert any("phase must be an integer 0-5" in err for err in report.errors)

    data = yaml.safe_load((FIXTURES / "valid_tasks.yaml").read_text(encoding="utf-8"))
    data["tasks"][0]["owner"] = "invalid-agent"
    tasks_file.write_text(yaml.safe_dump(data), encoding="utf-8")
    report = HANDOFF_CHECK.Report()
    HANDOFF_CHECK.check_tasks(report, root=tmp_path)
    assert any("owner 'invalid-agent' not in" in err for err in report.errors)

    data = yaml.safe_load((FIXTURES / "valid_tasks.yaml").read_text(encoding="utf-8"))
    data["tasks"][0]["depends_on"] = "T-002"
    tasks_file.write_text(yaml.safe_dump(data), encoding="utf-8")
    report = HANDOFF_CHECK.Report()
    HANDOFF_CHECK.check_tasks(report, root=tmp_path)
    assert any("depends_on must be a list" in err for err in report.errors)


def test_tasks_warnings(tmp_path: Path) -> None:
    _create_minimal_workspace(tmp_path)
    tasks_file = tmp_path / "tasks" / "tasks.yaml"
    data = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))

    data["tasks"][0]["spec"] = ["spec/nonexistent.md"]
    data["tasks"][0]["status"] = "in_progress"
    data["tasks"][0]["owner"] = "antigravity"
    data["tasks"][1]["status"] = "in_progress"
    data["tasks"][1]["owner"] = "antigravity"
    tasks_file.write_text(yaml.safe_dump(data), encoding="utf-8")

    report = HANDOFF_CHECK.Report()
    HANDOFF_CHECK.check_tasks(report, root=tmp_path)
    assert any("spec reference 'spec/nonexistent.md' doesn't exist" in w for w in report.warnings)
    assert any("several tasks in progress" in w for w in report.warnings)


@pytest.mark.parametrize(
    "fixture_name,expected_error",
    [
        ("bad_handoff_missing_header.md", "missing header field 'Branch'"),
        ("bad_handoff_missing_section.md", "missing section '## Next step'"),
        ("bad_handoff_empty_section.md", "section 'Summary' is empty"),
        (
            "bad_handoff_status_mismatch.md",
            "HANDOFF.md says T-001 is 'in_progress' but tasks.yaml says 'done'",
        ),
    ],
)
def test_handoff_rule_violations(tmp_path: Path, fixture_name: str, expected_error: str) -> None:
    _create_minimal_workspace(tmp_path)
    shutil.copyfile(FIXTURES / fixture_name, tmp_path / "handoff" / "HANDOFF.md")
    report = HANDOFF_CHECK.Report()
    tasks = HANDOFF_CHECK.check_tasks(report, root=tmp_path)
    HANDOFF_CHECK.check_handoff(report, tasks, use_git=False, root=tmp_path)
    assert any(expected_error in err for err in report.errors), report.errors


def test_handoff_missing_and_unknown_task(tmp_path: Path) -> None:
    _create_minimal_workspace(tmp_path)
    (tmp_path / "handoff" / "HANDOFF.md").unlink()
    report = HANDOFF_CHECK.Report()
    tasks = HANDOFF_CHECK.check_tasks(report, root=tmp_path)
    HANDOFF_CHECK.check_handoff(report, tasks, use_git=False, root=tmp_path)
    assert any("missing handoff/HANDOFF.md" in err for err in report.errors)

    _create_minimal_workspace(tmp_path)
    handoff_text = (tmp_path / "handoff" / "HANDOFF.md").read_text(encoding="utf-8")
    handoff_text = handoff_text.replace("T-002", "T-999")
    (tmp_path / "handoff" / "HANDOFF.md").write_text(handoff_text, encoding="utf-8")
    report = HANDOFF_CHECK.Report()
    tasks = HANDOFF_CHECK.check_tasks(report, root=tmp_path)
    HANDOFF_CHECK.check_handoff(report, tasks, use_git=False, root=tmp_path)
    assert any("active task T-999 isn't in tasks.yaml" in err for err in report.errors)


def test_handoff_git_checks(tmp_path: Path) -> None:
    _create_minimal_workspace(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "checkout", "-b", "task/T-002-second-task"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test Agent"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "agent@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"], cwd=tmp_path, check=True, capture_output=True
    )

    report = HANDOFF_CHECK.Report()
    tasks = HANDOFF_CHECK.check_tasks(report, root=tmp_path)
    HANDOFF_CHECK.check_handoff(report, tasks, use_git=True, root=tmp_path)
    assert not report.errors, report.errors

    (tmp_path / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    report = HANDOFF_CHECK.Report()
    HANDOFF_CHECK.check_handoff(report, tasks, use_git=True, root=tmp_path)
    assert any("working tree has uncommitted changes" in err for err in report.errors)


def test_adrs_and_logs_checks(tmp_path: Path) -> None:
    _create_minimal_workspace(tmp_path)
    bad_adr = tmp_path / "spec" / "decisions" / "ADR-bad-name.md"
    bad_adr.write_text("**Status:** accepted\n", encoding="utf-8")
    report = HANDOFF_CHECK.Report()
    HANDOFF_CHECK.check_adrs(report, root=tmp_path)
    assert any("should be named ADR-####-<slug>.md" in err for err in report.errors)

    bad_adr.unlink()
    no_status_adr = tmp_path / "spec" / "decisions" / "ADR-0002-missing-status.md"
    no_status_adr.write_text("# ADR\nDecision without status.\n", encoding="utf-8")
    report = HANDOFF_CHECK.Report()
    HANDOFF_CHECK.check_adrs(report, root=tmp_path)
    assert any("needs a '**Status:**'" in err for err in report.errors)

    bad_log = tmp_path / "handoff" / "log" / "bad-log-name.md"
    bad_log.write_text("# Log\n", encoding="utf-8")
    report = HANDOFF_CHECK.Report()
    tasks = HANDOFF_CHECK.check_tasks(report, root=tmp_path)
    HANDOFF_CHECK.check_logs(report, tasks, root=tmp_path)
    assert any("should be named YYYY-MM-DD-<agent>-T-###.md" in w for w in report.warnings)


def test_sync_agent_files_check_and_sync(tmp_path: Path) -> None:
    src = tmp_path / "agents" / "skills"
    dst = tmp_path / "claude" / "skills"
    (src / "skill-a").mkdir(parents=True, exist_ok=True)
    (src / "skill-a" / "SKILL.md").write_text("# Skill A\n", encoding="utf-8")

    diffs = SYNC_AGENT.differences(src=src, dst=dst)
    assert diffs == ["missing in .claude/skills: skill-a"]

    SYNC_AGENT.sync(src=src, dst=dst)
    assert (dst / "skill-a" / "SKILL.md").read_text(encoding="utf-8") == "# Skill A\n"
    assert (dst / "GENERATED.md").exists()
    assert SYNC_AGENT.differences(src=src, dst=dst) == []

    (dst / "stale-skill").mkdir(parents=True, exist_ok=True)
    diffs = SYNC_AGENT.differences(src=src, dst=dst)
    assert "stale in .claude/skills: stale-skill" in diffs

    SYNC_AGENT.sync(src=src, dst=dst)
    assert not (dst / "stale-skill").exists()
    assert SYNC_AGENT.differences(src=src, dst=dst) == []

    (dst / "skill-a" / "SKILL.md").write_text("# Modified\n", encoding="utf-8")
    diffs = SYNC_AGENT.differences(src=src, dst=dst)
    assert any("differs: skill-a/SKILL.md" in d for d in diffs)


def test_cli_execution_and_exit_codes(tmp_path: Path) -> None:
    _create_minimal_workspace(tmp_path)
    rc_good = HANDOFF_CHECK.main(["--root", str(tmp_path)])
    assert rc_good == 0

    (tmp_path / "tasks" / "tasks.yaml").unlink()
    rc_bad = HANDOFF_CHECK.main(["--root", str(tmp_path)])
    assert rc_bad == 1

    src = tmp_path / "src_skills"
    dst = tmp_path / "dst_skills"
    src.mkdir(parents=True, exist_ok=True)
    (src / "test-skill").mkdir()
    (src / "test-skill" / "SKILL.md").write_text("# Skill\n", encoding="utf-8")

    rc_sync_check_fail = SYNC_AGENT.main(["--check", "--src", str(src), "--dst", str(dst)])
    assert rc_sync_check_fail == 1

    rc_sync = SYNC_AGENT.main(["--src", str(src), "--dst", str(dst)])
    assert rc_sync == 0

    rc_sync_check_pass = SYNC_AGENT.main(["--check", "--src", str(src), "--dst", str(dst)])
    assert rc_sync_check_pass == 0


def test_pre_commit_configuration() -> None:
    config_path = ROOT / ".pre-commit-config.yaml"
    assert config_path.exists()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    hooks = {hook["id"]: hook for repo in config.get("repos", []) for hook in repo.get("hooks", [])}

    assert "handoff-check" in hooks
    assert "skill-mirror" in hooks

    handoff_hook = hooks["handoff-check"]
    skill_hook = hooks["skill-mirror"]

    assert "scripts/handoff_check.py" in handoff_hook["entry"]
    assert "scripts/sync_agent_files.py --check" in skill_hook["entry"]

    handoff_pattern = re.compile(handoff_hook["files"])
    assert handoff_pattern.search("tasks/tasks.yaml")
    assert handoff_pattern.search("handoff/HANDOFF.md")
    assert handoff_pattern.search("spec/decisions/ADR-0001-example.md")

    skill_pattern = re.compile(skill_hook["files"])
    assert skill_pattern.search(".agents/skills/demo/SKILL.md")
    assert skill_pattern.search(".claude/skills/demo/SKILL.md")


def test_ci_and_make_integration() -> None:
    ci_path = ROOT / ".github" / "workflows" / "ci.yml"
    assert ci_path.exists()
    ci_text = ci_path.read_text(encoding="utf-8")
    assert "make check" in ci_text

    makefile_path = ROOT / "Makefile"
    assert makefile_path.exists()
    makefile_text = makefile_path.read_text(encoding="utf-8")
    assert "handoff-check" in makefile_text
    assert "sync-agent-files" in makefile_text
