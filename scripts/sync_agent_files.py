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


def differences(src: Path = SRC, dst: Path = DST) -> list[str]:
    diffs: list[str] = []
    if not src.exists():
        return [f"missing {src}"]
    src_skills = {p.name for p in src.iterdir() if p.is_dir()}
    dst_skills = {p.name for p in dst.iterdir() if p.is_dir()} if dst.exists() else set()
    for name in sorted(src_skills - dst_skills):
        diffs.append(f"missing in .claude/skills: {name}")
    for name in sorted(dst_skills - src_skills):
        diffs.append(f"stale in .claude/skills: {name}")
    for name in sorted(src_skills & dst_skills):
        cmp = filecmp.dircmp(src / name, dst / name)
        stack = [cmp]
        while stack:
            c = stack.pop()
            for f in c.left_only + c.right_only + c.diff_files:
                diffs.append(f"differs: {name}/{Path(c.left).relative_to(src / name) / f}")
            stack.extend(c.subdirs.values())
    return diffs


def sync(src: Path = SRC, dst: Path = DST) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    src_skills = {p.name for p in src.iterdir() if p.is_dir()} if src.exists() else set()
    for p in dst.iterdir():
        if p.is_dir() and p.name not in src_skills:
            shutil.rmtree(p)
    for name in sorted(src_skills):
        target = dst / name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src / name, target)
    (dst / NOTE).write_text(NOTE_TEXT, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="report differences instead of copying")
    ap.add_argument("--src", type=Path, default=SRC, help="source directory")
    ap.add_argument("--dst", type=Path, default=DST, help="destination directory")
    args = ap.parse_args(argv)
    if args.check:
        diffs = differences(src=args.src, dst=args.dst)
        for d in diffs:
            print(d)
        print(
            "in sync"
            if not diffs
            else f"{len(diffs)} differences; run python3 scripts/sync_agent_files.py"
        )
        return 1 if diffs else 0
    sync(src=args.src, dst=args.dst)
    skill_count = len([p for p in args.src.iterdir() if p.is_dir()]) if args.src.exists() else 0
    dst_label = ".claude/skills/" if args.dst == DST else str(args.dst)
    print(f"synced {skill_count} skills to {dst_label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
