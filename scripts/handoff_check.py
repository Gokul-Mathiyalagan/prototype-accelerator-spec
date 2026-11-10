#!/usr/bin/env python3
"""Validate the multi-agent handoff state: tasks/tasks.yaml, handoff/HANDOFF.md, logs and ADRs.

Usage:
    python3 scripts/handoff_check.py           # errors fail, warnings print
    python3 scripts/handoff_check.py --git     # also require a clean tree on the handoff branch

Exit code 0 when there are no errors, 1 otherwise.
Needs PyYAML. If it's missing: uv run --with pyyaml python scripts/handoff_check.py
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: uv run --with pyyaml python scripts/handoff_check.py")

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "tasks" / "tasks.yaml"
HANDOFF = ROOT / "handoff" / "HANDOFF.md"
LOG_DIR = ROOT / "handoff" / "log"
ADR_DIR = ROOT / "spec" / "decisions"

STATUSES = {"todo", "in_progress", "blocked", "review", "done"}
OWNERS = {None, "claude-code", "codex", "antigravity", "gokul"}
NEEDS = {"azure", "copilot", "rea", "ghidra", "work-repos"}
AGENTS = {"claude-code", "codex", "antigravity", "gokul", "spec"}
REQUIRED_FIELDS = [
    "id",
    "phase",
    "title",
    "goal",
    "spec",
    "depends_on",
    "needs",
    "paths",
    "acceptance",
    "status",
    "owner",
    "progress",
]
TASK_ID = re.compile(r"^T-\d{3}$")
HANDOFF_SECTIONS = [
    "Summary",
    "Acceptance criteria",
    "State of the active task",
    "Next step",
    "How to verify",
    "Decisions and assumptions",
    "Spec changes",
    "Open questions for Gokul",
    "Watch out",
]
HANDOFF_FIELDS = ["Updated", "Agent", "Active task", "Task status", "Branch"]
LOG_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}-([a-z-]+?)-(T-\d{3})\.md$")
ADR_NAME = re.compile(r"^ADR-\d{4}-[a-z0-9-]+\.md$")
ADR_STATUS = re.compile(r"\*\*Status:\*\*\s*(proposed|accepted|rejected|superseded by ADR-\d{4})\b")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def check_tasks(r: Report) -> dict[str, dict]:
    if not TASKS.exists():
        r.error(f"missing {TASKS.relative_to(ROOT)}")
        return {}
    data = yaml.safe_load(TASKS.read_text(encoding="utf-8")) or {}
    tasks = data.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        r.error("tasks.yaml must have a non-empty top-level 'tasks' list")
        return {}

    by_id: dict[str, dict] = {}
    for i, t in enumerate(tasks):
        where = f"tasks[{i}]"
        if not isinstance(t, dict):
            r.error(f"{where}: must be a mapping")
            continue
        tid = t.get("id", where)
        for f in REQUIRED_FIELDS:
            if f not in t:
                r.error(f"{tid}: missing field '{f}'")
        if not isinstance(tid, str) or not TASK_ID.match(tid):
            r.error(f"{where}: id '{tid}' must look like T-###")
            continue
        if tid in by_id:
            r.error(f"{tid}: duplicate id")
        by_id[tid] = t

        phase = t.get("phase")
        if not isinstance(phase, int) or not 0 <= phase <= 5:
            r.error(f"{tid}: phase must be an integer 0-5")
        elif int(tid[2]) != phase:
            r.error(f"{tid}: id's first digit should equal phase {phase}")

        status = t.get("status")
        owner = t.get("owner")
        if status not in STATUSES:
            r.error(f"{tid}: status '{status}' not in {sorted(STATUSES)}")
        if owner not in OWNERS:
            r.error(f"{tid}: owner '{owner}' not in {sorted(o for o in OWNERS if o)} or null")
        if status in {"in_progress", "blocked", "review"} and not owner:
            r.error(f"{tid}: status '{status}' needs an owner")
        if status == "blocked" and not str(t.get("progress") or "").strip():
            r.error(f"{tid}: blocked tasks must say why in 'progress'")

        needs = t.get("needs") or []
        if not isinstance(needs, list) or any(n not in NEEDS for n in needs):
            r.error(f"{tid}: needs must be a list drawn from {sorted(NEEDS)}")

        acc = t.get("acceptance")
        if (
            not isinstance(acc, list)
            or not acc
            or not all(isinstance(a, str) and a.strip() for a in acc)
        ):
            r.error(f"{tid}: acceptance must be a non-empty list of strings")

        for ref in t.get("spec") or []:
            path = str(ref).split("#", 1)[0]
            if path and not (ROOT / path).exists():
                r.warn(f"{tid}: spec reference '{path}' doesn't exist yet")

    # dependencies
    for tid, t in by_id.items():
        deps = t.get("depends_on") or []
        if not isinstance(deps, list):
            r.error(f"{tid}: depends_on must be a list")
            continue
        for d in deps:
            if d == tid:
                r.error(f"{tid}: depends on itself")
            elif d not in by_id:
                r.error(f"{tid}: depends on unknown task {d}")
            else:
                dstat = by_id[d].get("status")
                if t.get("status") == "done" and dstat != "done":
                    r.error(f"{tid}: is done but its dependency {d} is '{dstat}'")
                elif t.get("status") in {"in_progress", "review"} and dstat not in {
                    "done",
                    "review",
                }:
                    r.warn(f"{tid}: is {t.get('status')} while dependency {d} is '{dstat}'")

    # cycles
    state: dict[str, int] = {}

    def visit(n: str, stack: list[str]) -> None:
        state[n] = 1
        for d in by_id[n].get("depends_on") or []:
            if d not in by_id:
                continue
            if state.get(d) == 1:
                r.error("dependency cycle: " + " -> ".join([*stack, n, d]))
            elif state.get(d) is None:
                visit(d, [*stack, n])
        state[n] = 2

    for n in by_id:
        if state.get(n) is None:
            visit(n, [])

    owners_in_progress: dict[str, list[str]] = {}
    for tid, t in by_id.items():
        if t.get("status") == "in_progress":
            owners_in_progress.setdefault(str(t.get("owner")), []).append(tid)
    for owner, ids in owners_in_progress.items():
        if len(ids) > 1:
            r.warn(f"{owner} has several tasks in progress: {', '.join(ids)}")
    return by_id


def field(text: str, name: str) -> str | None:
    m = re.search(rf"^\s*-\s*\*\*{re.escape(name)}:\*\*\s*(.+?)\s*$", text, re.MULTILINE)
    return m.group(1) if m else None


def section(text: str, name: str) -> str | None:
    m = re.search(rf"^## {re.escape(name)}\s*$(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not m:
        return None
    body = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.DOTALL)
    return body.strip()


def check_handoff(r: Report, tasks: dict[str, dict], use_git: bool) -> None:
    if not HANDOFF.exists():
        r.error("missing handoff/HANDOFF.md")
        return
    text = HANDOFF.read_text(encoding="utf-8")
    for f in HANDOFF_FIELDS:
        if field(text, f) is None:
            r.error(f"HANDOFF.md: missing header field '{f}'")
    for s in HANDOFF_SECTIONS:
        body = section(text, s)
        if body is None:
            r.error(f"HANDOFF.md: missing section '## {s}'")
        elif s in {"Summary", "Next step", "How to verify"} and (
            not body or body in {"...", "1. ..."}
        ):
            r.error(f"HANDOFF.md: section '{s}' is empty")

    active = (field(text, "Active task") or "").strip()
    status = (field(text, "Task status") or "").strip()
    m = re.match(r"(T-\d{3})\b", active)
    if m:
        tid = m.group(1)
        if tid not in tasks:
            r.error(f"HANDOFF.md: active task {tid} isn't in tasks.yaml")
        else:
            tstat = tasks[tid].get("status")
            if status and status != tstat:
                r.error(f"HANDOFF.md says {tid} is '{status}' but tasks.yaml says '{tstat}'")
    elif active.lower() not in {"none", ""}:
        r.warn(f"HANDOFF.md: active task '{active}' isn't a task id or 'none'")

    agent = (field(text, "Agent") or "").split()[0] if field(text, "Agent") else ""
    if agent and agent not in AGENTS | {"none"}:
        r.warn(f"HANDOFF.md: agent '{agent}' isn't one of {sorted(AGENTS)}")

    if use_git:
        branch = (field(text, "Branch") or "").strip()
        try:
            cur = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            dirty = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            r.error(f"git check failed: {exc}")
            return
        if branch and cur and branch != cur:
            r.error(f"HANDOFF.md branch '{branch}' but current branch is '{cur}'")
        if dirty:
            r.error("working tree has uncommitted changes; commit before handing off")


def check_logs(r: Report, tasks: dict[str, dict]) -> None:
    if not LOG_DIR.exists():
        r.warn("handoff/log/ doesn't exist")
        return
    for p in sorted(LOG_DIR.glob("*.md")):
        m = LOG_NAME.match(p.name)
        if not m:
            r.warn(f"log '{p.name}' should be named YYYY-MM-DD-<agent>-T-###.md")
            continue
        agent, tid = m.groups()
        if agent not in AGENTS:
            r.warn(f"log '{p.name}': agent '{agent}' isn't one of {sorted(AGENTS)}")
        if tid != "T-000" and tid not in tasks:
            r.warn(f"log '{p.name}': task {tid} isn't in tasks.yaml")


def check_adrs(r: Report) -> None:
    if not ADR_DIR.exists():
        return
    for p in sorted(ADR_DIR.glob("ADR-*.md")):
        if p.name == "ADR-template.md":
            continue
        if not ADR_NAME.match(p.name):
            r.error(f"ADR file '{p.name}' should be named ADR-####-<slug>.md")
        if not ADR_STATUS.search(p.read_text(encoding="utf-8")):
            r.error(
                f"{p.name}: needs a '**Status:**' of proposed, accepted, rejected "
                "or superseded by ADR-####"
            )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--git", action="store_true", help="also require a clean tree on the handoff branch"
    )
    args = ap.parse_args()
    r = Report()
    tasks = check_tasks(r)
    check_handoff(r, tasks, args.git)
    check_logs(r, tasks)
    check_adrs(r)
    for w in r.warnings:
        print(f"warning: {w}")
    for e in r.errors:
        print(f"error: {e}")
    counts: dict[str, int] = {}
    for t in tasks.values():
        counts[str(t.get("status"))] = counts.get(str(t.get("status")), 0) + 1
    summary = ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
    print(f"{len(tasks)} tasks ({summary}); {len(r.errors)} errors, {len(r.warnings)} warnings")
    return 1 if r.errors else 0


if __name__ == "__main__":
    sys.exit(main())
