#!/usr/bin/env python3
"""Mirror .agents/skills/ into .claude/skills/ for Claude Code.

Usage:
    python3 scripts/sync_agent_files.py          # copy, removing skills that no longer exist
    python3 scripts/sync_agent_files.py --check  # exit 1 if the mirror is out of date (for CI)

Always edit .agents/skills/. Never edit .claude/skills/ by hand.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".agents" / "skills"
DST = ROOT / ".claude" / "skills"
NOTE = "GENERATED.md"
NOTE_TEXT = (
    "# Generated\n\n"
    "This folder mirrors `.agents/skills/` for Claude Code. Don't edit it.\n"
    "Edit `.agents/skills/`, then run `python3 scripts/sync_agent_files.py`.\n"
)


def differences() -> list[str]:
    diffs: list[str] = []
    if not SRC.exists():
        return ["missing .agents/skills/"]
    src_skills = {p.name for p in SRC.iterdir() if p.is_dir()}
    dst_skills = {p.name for p in DST.iterdir() if p.is_dir()} if DST.exists() else set()
    for name in sorted(src_skills - dst_skills):
        diffs.append(f"missing in .claude/skills: {name}")
    for name in sorted(dst_skills - src_skills):
        diffs.append(f"stale in .claude/skills: {name}")
    for name in sorted(src_skills & dst_skills):
        cmp = filecmp.dircmp(SRC / name, DST / name)
        stack = [cmp]
        while stack:
            c = stack.pop()
            for f in c.left_only + c.right_only + c.diff_files:
                diffs.append(f"differs: {name}/{Path(c.left).relative_to(SRC / name) / f}")
            stack.extend(c.subdirs.values())
    return diffs


def sync() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    src_skills = {p.name for p in SRC.iterdir() if p.is_dir()}
    for p in DST.iterdir():
        if p.is_dir() and p.name not in src_skills:
            shutil.rmtree(p)
    for name in sorted(src_skills):
        target = DST / name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(SRC / name, target)
    (DST / NOTE).write_text(NOTE_TEXT, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="report differences instead of copying")
    args = ap.parse_args()
    if args.check:
        diffs = differences()
        for d in diffs:
            print(d)
        print(
            "in sync"
            if not diffs
            else f"{len(diffs)} differences; run python3 scripts/sync_agent_files.py"
        )
        return 1 if diffs else 0
    sync()
    print(f"synced {len([p for p in SRC.iterdir() if p.is_dir()])} skills to .claude/skills/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
