#!/usr/bin/env python3
"""Write schemas/<name>.schema.json for every contract model, or check they are current."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from accel_core.contracts import CONTRACTS, json_schema

ROOT = Path(__file__).resolve().parent.parent
SUFFIX = ".schema.json"


def render(name: str) -> str:
    """Return the committed text for one contract's schema."""
    return json.dumps(json_schema(name), indent=2, sort_keys=True) + "\n"


def expected_files() -> dict[str, str]:
    """Map each schema file name to its expected contents."""
    return {f"{name}{SUFFIX}": render(name) for name in CONTRACTS}


def drift(schema_dir: Path) -> list[str]:
    """List schema files that are missing, stale, or no longer backed by a model."""
    expected = expected_files()
    problems: list[str] = []
    for file_name, text in sorted(expected.items()):
        path = schema_dir / file_name
        if not path.is_file():
            problems.append(f"missing {file_name}")
        elif path.read_text(encoding="utf-8") != text:
            problems.append(f"stale {file_name}")
    for path in sorted(schema_dir.glob(f"*{SUFFIX}")):
        if path.name not in expected:
            problems.append(f"orphaned {path.name}")
    return problems


def write(schema_dir: Path) -> None:
    """Regenerate every schema file and remove orphaned ones."""
    schema_dir.mkdir(parents=True, exist_ok=True)
    expected = expected_files()
    for file_name, text in expected.items():
        (schema_dir / file_name).write_text(text, encoding="utf-8", newline="\n")
    for path in schema_dir.glob(f"*{SUFFIX}"):
        if path.name not in expected:
            path.unlink()


def main(argv: list[str] | None = None) -> int:
    """Regenerate schemas, or with --check report drift and exit 1."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if schemas are out of date")
    parser.add_argument("--out", type=Path, default=ROOT / "schemas", help="Schema directory")
    args = parser.parse_args(argv)
    if args.check:
        problems = drift(args.out)
        for problem in problems:
            print(problem, file=sys.stderr)
        if problems:
            print("Run `make schemas` and commit the result.", file=sys.stderr)
            return 1
        print(f"{len(CONTRACTS)} schemas are current.")
        return 0
    write(args.out)
    print(f"Wrote {len(CONTRACTS)} schemas to {args.out}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
