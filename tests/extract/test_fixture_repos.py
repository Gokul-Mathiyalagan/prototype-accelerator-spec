"""The synthetic fixture repos: EXPECTED.md stays true, planted data is caught, binaries are right.

These checks need no network and no external tools; the container build-and-run test is in
test_fixture_repos_run.py.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest
from accel_core.contracts import Finding, check_static_evidence
from accel_core.redaction import Redactor

REPOS = Path(__file__).resolve().parents[1] / "fixtures" / "repos"
SSO = REPOS / "fastapi-react-sso"
NATIVE = REPOS / "native-sdk-sample"
PLAYBOOKS = (
    "repo-overview", "ui-architecture", "design-system", "api-surface", "auth-sso",
    "data-access", "ai-llm", "backend-architecture", "observability", "delivery",
    "native-artifacts",
)  # fmt: skip

QUOTED = r'"(?:[^"\\]|\\.)*"'
FINDING = re.compile(
    r"^- \*\*(?P<id>[a-z0-9-]+\.[a-z0-9-]+)\*\* · (?P<confidence>low|medium|high) · "
    r"(?P<claim>.+?) Evidence: (?P<evidence>.+)$",
    re.MULTILINE,
)
EVIDENCE = re.compile(rf"`(?P<path>[^`]+?):(?P<line>\d+)` (?P<snippet>{QUOTED})")
PLANTED = re.compile(
    rf"^- `(?P<kind>[a-z_]+)` at `(?P<path>[^`]+):(?P<line>\d+)` (?P<value>{QUOTED})$",
    re.MULTILINE,
)


def _expected(repo: Path) -> str:
    return (repo / "EXPECTED.md").read_text(encoding="utf-8")


def _sections(text: str) -> dict[str, str]:
    parts = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
    return {part.splitlines()[0].strip(): part for part in parts}


def _findings(repo: Path) -> list[tuple[str, re.Match[str]]]:
    found = []
    for heading, body in _sections(_expected(repo)).items():
        found += [(heading, match) for match in FINDING.finditer(body)]
    return found


def _line(repo: Path, path: str, number: int) -> str:
    lines = (repo / path).read_text(encoding="utf-8").splitlines()
    assert 1 <= number <= len(lines), f"{path}:{number} is past the end ({len(lines)} lines)"
    return lines[number - 1]


@pytest.mark.parametrize("repo", [SSO, NATIVE], ids=lambda p: p.name)
def test_expected_md_accounts_for_every_playbook(repo: Path) -> None:
    text = _expected(repo)
    sections = _sections(text)
    for playbook in PLAYBOOKS:
        listed_as_excluded = f"`{playbook}`" in sections.get("Not included", "")
        assert playbook in sections or listed_as_excluded, f"{repo.name}: no entry for {playbook}"


@pytest.mark.parametrize("repo", [SSO, NATIVE], ids=lambda p: p.name)
def test_every_expected_finding_is_a_valid_contract_with_resolving_evidence(repo: Path) -> None:
    findings = _findings(repo)
    assert findings, f"{repo.name}: no findings parsed"
    ids = [match["id"] for _, match in findings]
    assert len(ids) == len(set(ids)), "finding ids must be unique"
    for heading, match in findings:
        assert match["id"].split(".")[0] == heading, f"{match['id']} is under ## {heading}"
        evidence = list(EVIDENCE.finditer(match["evidence"]))
        assert evidence, f"{match['id']}: no evidence parsed"
        static = []
        for item in evidence:
            snippet = json.loads(item["snippet"])
            line = _line(repo, item["path"], int(item["line"]))
            assert snippet in line, (
                f"{match['id']}: {item['path']}:{item['line']} lacks {snippet!r}"
            )
            static.append(
                {
                    "kind": "static",
                    "repo": repo.name,
                    "path": item["path"],
                    "line": int(item["line"]),
                    "commit": "0000000",
                }
            )
        finding = Finding.model_validate(
            {
                "id": match["id"],
                "playbook": heading,
                "claim": match["claim"],
                "evidence": static,
                "confidence": match["confidence"],
                "recorded_by": "batch:expected-md",
            }
        )
        assert check_static_evidence(finding, repo) == []


def test_sso_fixture_covers_the_main_playbooks() -> None:
    covered = {heading for heading, _ in _findings(SSO)}
    assert covered == set(PLAYBOOKS) - {"native-artifacts"}


def test_native_fixture_finds_both_binaries_and_their_licenses() -> None:
    ids = {match["id"] for _, match in _findings(NATIVE)}
    assert {"native-artifacts.tinymath-license", "native-artifacts.secretsauce-license"} <= ids


# ── Planted sensitive data ────────────────────────────────────────────────────


def _planted() -> list[re.Match[str]]:
    return list(PLANTED.finditer(_sections(_expected(SSO))["Planted sensitive data"]))


def test_planted_data_is_listed_and_present() -> None:
    planted = _planted()
    kinds = {match["kind"] for match in planted}
    assert {"aws_access_key", "secret", "email", "phone", "employee_id"} <= kinds
    for match in planted:
        assert json.loads(match["value"]) in _line(SSO, match["path"], int(match["line"]))


@pytest.mark.parametrize("match", _planted(), ids=lambda m: f"{m['kind']}@{m['path']}:{m['line']}")
def test_redaction_removes_each_planted_value(match: re.Match[str]) -> None:
    line = _line(SSO, match["path"], int(match["line"]))
    redacted, counts = Redactor().redact(line)
    assert json.loads(match["value"]) not in redacted
    assert counts.get(match["kind"], 0) >= 1


@pytest.mark.parametrize("path", ["service/app/settings.py", "service/data/seed_members.json"])
def test_no_planted_value_survives_redacting_the_whole_file(path: str) -> None:
    redacted, _ = Redactor().redact((SSO / path).read_text(encoding="utf-8"))
    for match in _planted():
        assert json.loads(match["value"]) not in redacted


# ── Source and binaries ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "path", sorted(p for repo in (SSO, NATIVE) for p in repo.rglob("*.py")), ids=lambda p: p.name
)
def test_python_sources_parse(path: Path) -> None:
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_web_app_lockfile_matches_package_json() -> None:
    package = json.loads((SSO / "web" / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((SSO / "web" / "package-lock.json").read_text(encoding="utf-8"))
    root = lock["packages"][""]
    assert root["dependencies"] == package["dependencies"]
    assert root["devDependencies"] == package["devDependencies"]
    assert {"react", "react-router-dom"} <= set(package["dependencies"])


@pytest.mark.parametrize(
    ("library", "exports"),
    [
        ("tinymath", [b"tm_add", b"tm_mul", b"tm_clamp", b"tm_version"]),
        ("secretsauce", [b"ss_score", b"ss_version"]),
    ],
)
def test_vendored_libraries_are_elf_shared_objects_with_their_exports(
    library: str, exports: list[bytes]
) -> None:
    data = (NATIVE / "vendor" / library / "lib" / f"lib{library}.so").read_bytes()
    assert data[:4] == b"\x7fELF"
    assert data[16] == 3, "e_type should be ET_DYN (a shared object)"
    for name in exports:
        assert name in data


def test_only_tinymath_ships_source_and_licenses_say_so() -> None:
    assert (NATIVE / "vendor" / "tinymath" / "src" / "tinymath.c").is_file()
    assert not list((NATIVE / "vendor" / "secretsauce").rglob("*.c"))
    tinymath = (NATIVE / "vendor" / "tinymath" / "LICENSE").read_text(encoding="utf-8")
    secretsauce = (NATIVE / "vendor" / "secretsauce" / "LICENSE").read_text(encoding="utf-8")
    assert tinymath.startswith("MIT License")
    assert "may not reverse engineer, decompile, disassemble" in secretsauce
