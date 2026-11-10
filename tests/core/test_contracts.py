"""Contract models: spec examples, fixtures, rules, and the evidence path check."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from accel_core.contracts import (
    CONTRACTS,
    Finding,
    check_static_evidence,
    json_schema,
)
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
SPEC_05 = ROOT / "spec" / "05-cli-and-contracts.md"
FIXTURES = ROOT / "tests" / "fixtures" / "contracts"
DELETE = object()

# spec/05 headings with examples, and the contract each example belongs to.
SPEC_EXAMPLES = {
    "Finding": "finding",
    "Playbook": "playbook",
    "Catalog entry": "catalog-entry",
    "UI spec": "ui-spec",
    "Task": "task",
    "Gate record": "gate-record",
}


def _load(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)


def _valid(name: str) -> dict[str, Any]:
    matches = sorted((FIXTURES / "valid").glob(f"{name}.*"))
    assert len(matches) == 1, f"expected one valid fixture for {name}"
    return _load(matches[0])


def _spec_examples() -> dict[str, Any]:
    """Parse each example block under spec/05's contract headings."""
    text = SPEC_05.read_text(encoding="utf-8").split("## Contracts", 1)[1]
    examples: dict[str, Any] = {}
    for section in re.split(r"^### ", text, flags=re.MULTILINE)[1:]:
        heading = section.splitlines()[0].split(" (")[0].strip()
        block = re.search(r"```(json|yaml)\n(.*?)```", section, flags=re.DOTALL)
        assert block is not None, f"no example under '{heading}'"
        body = re.sub(r"<hash[^>]*>", "a" * 64, block.group(2))  # placeholder hashes
        examples[heading] = json.loads(body) if block.group(1) == "json" else yaml.safe_load(body)
    return examples


def _set(data: dict[str, Any], dotted: str, value: object) -> None:
    """Set or delete a nested key; list indexes are numeric path parts."""
    parts = dotted.split(".")
    node: Any = data
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    last = parts[-1]
    key: Any = int(last) if isinstance(node, list) else last
    if value is DELETE:
        del node[key]
    else:
        node[key] = value


def _mutated(name: str, changes: dict[str, object]) -> dict[str, Any]:
    data = copy.deepcopy(_valid(name))
    for dotted, value in changes.items():
        _set(data, dotted, value)
    return data


# ── Registry and schemas ─────────────────────────────────────────────────────


def test_registry_matches_spec_contract_table() -> None:
    table = SPEC_05.read_text(encoding="utf-8").split("## Contracts", 1)[1].split("###", 1)[0]
    names = {
        name
        for cell in re.findall(r"^\| (`[^|]+`) \|", table, flags=re.MULTILINE)
        for name in re.findall(r"`([^`]+)`", cell)
    }
    assert names == set(CONTRACTS)


@pytest.mark.parametrize("name", sorted(CONTRACTS))
def test_every_contract_is_versioned_strict_and_frozen(name: str) -> None:
    model = CONTRACTS[name]
    assert model.model_config.get("extra") == "forbid"
    assert model.model_config.get("frozen") is True
    field = model.model_fields["schema_version"]
    assert field.default == 1
    instance = model.model_validate(_valid(name))
    with pytest.raises(ValidationError, match="frozen"):
        instance.schema_version = 1  # type: ignore[misc]


def _objects(node: Any) -> list[dict[str, Any]]:
    if isinstance(node, dict):
        found = [node] if "properties" in node else []
        return found + [obj for value in node.values() for obj in _objects(value)]
    if isinstance(node, list):
        return [obj for value in node for obj in _objects(value)]
    return []


@pytest.mark.parametrize("name", sorted(CONTRACTS))
def test_schema_forbids_unknown_keys_at_every_level(name: str) -> None:
    schema = json_schema(name)
    assert schema["$id"] == f"{name}.schema.json"
    assert schema["properties"]["schema_version"] == {
        "const": 1,
        "default": 1,
        "description": "Contract version; bump on breaking changes.",
        "title": "Schema Version",
        "type": "integer",
    }
    for obj in _objects(schema):
        assert obj.get("additionalProperties") is False, obj.get("title")


# ── Spec examples and fixtures ───────────────────────────────────────────────


def test_spec_05_has_an_example_for_each_expected_heading() -> None:
    assert set(_spec_examples()) == set(SPEC_EXAMPLES)


@pytest.mark.parametrize(("heading", "name"), sorted(SPEC_EXAMPLES.items()))
def test_spec_05_example_validates(heading: str, name: str) -> None:
    example = _spec_examples()[heading]
    items = example if isinstance(example, list) else [example]
    for item in items:
        CONTRACTS[name].model_validate(item)


@pytest.mark.parametrize("name", sorted(CONTRACTS))
def test_valid_fixture_validates_and_round_trips(name: str) -> None:
    model = CONTRACTS[name]
    instance = model.model_validate(_valid(name))
    assert model.model_validate(instance.model_dump(mode="json")) == instance
    assert model.model_validate_json(instance.model_dump_json()) == instance


def _invalid_cases() -> list[tuple[str, str]]:
    expected: dict[str, str] = _load(FIXTURES / "invalid" / "expected.yaml")
    return sorted(expected.items())


def test_every_contract_has_an_invalid_fixture_and_every_fixture_is_listed() -> None:
    listed = {path for path, _ in _invalid_cases()}
    on_disk = {
        path.relative_to(FIXTURES / "invalid").as_posix()
        for path in (FIXTURES / "invalid").rglob("*")
        if path.is_file() and path.name != "expected.yaml"
    }
    assert listed == on_disk
    assert {path.split("/")[0] for path in listed} == set(CONTRACTS)


@pytest.mark.parametrize(("fixture", "message"), _invalid_cases())
def test_invalid_fixture_is_rejected_with_a_clear_error(fixture: str, message: str) -> None:
    model = CONTRACTS[fixture.split("/")[0]]
    with pytest.raises(ValidationError) as caught:
        model.model_validate(_load(FIXTURES / "invalid" / fixture))
    assert message in str(caught.value)


# ── Rules not covered by a fixture file ──────────────────────────────────────

RULES: list[tuple[str, dict[str, object], str]] = [
    ("finding", {"surprise": True}, "Extra inputs are not permitted"),
    ("finding", {"schema_version": 2}, "Input should be 1"),
    ("finding", {"evidence.0.path": "/etc/passwd"}, "path must be relative"),
    ("finding", {"evidence.0.path": "C:/repo/app.py"}, "path must be relative"),
    ("finding", {"evidence.0.path": "service\\app.py"}, "use forward slashes"),
    ("finding", {"evidence.0.path": "../outside.py"}, "must not contain '..'"),
    ("finding", {"evidence.0.line": 0}, "greater than or equal to 1"),
    ("finding", {"evidence.0.kind": "guess"}, "does not match any of the expected tags"),
    ("finding", {"evidence.0.extra": 1}, "Extra inputs are not permitted"),
    ("finding", {"evidence.1.source": "har"}, "HAR evidence needs 'entry'"),
    ("finding", {"evidence.1.path": DELETE}, "screenshot evidence needs 'path'"),
    ("finding", {"recorded_by": "someone"}, "String should match pattern"),
    ("finding", {"claim": "   "}, "at least 1 character"),
    ("catalog-entry", {"emit_when": {"always": True, "playbook": "x"}}, "cannot be combined"),
    ("knowledge-manifest", {"updated_at": "2026-11-19T00:00:00Z"}, "earlier than created_at"),
    ("knowledge-manifest", {"created_at": "2026-11-20T10:02:00"}, "timezone info"),
    ("extract-plan", {"playbooks": ["api-surface", "api-surface"]}, "playbooks must be unique"),
    ("install-check", {"next_action": ""}, "next_action is required"),
    ("versions-lock", {"ghidra.version": "12.2.0"}, "String should match pattern"),
    ("versions-lock", {"rea.commit": "abc1234"}, "String should match pattern"),
    ("eval-report", {"pass_rate_with": 0.6}, "pass_rate_with should be 0.8"),
    ("eval-report", {"pass_rate_without": 0.4}, "pass_rate_without should be 0.2"),
    ("eval-report", {"lift": 0.5}, "lift must equal"),
    ("eval-report", {"stopped_early": True}, "passed should be false"),
    ("eval-report", {"cases.1.case_id": "sso-auth-01"}, "case_id must be unique"),
    ("ui-spec", {"screens.0.route": "members"}, "String should match pattern"),
    (
        "ui-spec",
        {"screens.0.components": [{"wireframe": "t", "maps_to": "X", "confidence": 2}]},
        "less than or equal to 1",
    ),
    ("project", {"adapters.data": "sample-data"}, "needs a real data adapter"),
    ("project", {"design_source": "figma"}, "Input should be 'html'"),
    ("task", {"status": "ready"}, "a ready task must have no claimed_by"),
    ("task", {"pr": None}, "an in_review task needs pr"),
    ("task", {"branch": "feature/members"}, "branch must be task/T-021-<slug>"),
    ("task", {"depends_on": ["T-021"]}, "cannot depend on itself"),
    ("task", {"status": "blocked", "claimed_by": None}, "a blocked task needs blocked_reason"),
    ("gate-record", {"approved_by": "tech-lead"}, "String should match pattern"),
    ("gate-record", {"artifacts.0.sha256": "abc"}, "String should match pattern"),
]


@pytest.mark.parametrize(("name", "changes", "message"), RULES)
def test_rule_rejects_bad_input(name: str, changes: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError) as caught:
        CONTRACTS[name].model_validate(_mutated(name, changes))
    assert message in str(caught.value)


def test_ui_spec_rejects_duplicate_screens() -> None:
    data = _valid("ui-spec")
    data["screens"].append(copy.deepcopy(data["screens"][0]))
    with pytest.raises(ValidationError, match="screen ids must be unique"):
        CONTRACTS["ui-spec"].model_validate(data)


ACCEPTED: list[tuple[str, dict[str, object]]] = [
    ("project", {"level": "mock", "adapters": {"auth": "mock-idp", "data": "sample-data"}}),
    ("task", {"status": "blocked", "blocked_reason": "Waiting on the contract"}),
    ("task", {"status": "done"}),
    ("catalog-entry", {"emit_when": {"inventory": ["config_files"]}}),
    ("provenance", {"sources": [], "approved_by": None}),
    ("gate-record", {"artifacts.0.path": "aisdlc/03-design/mocks/"}),
]


@pytest.mark.parametrize(("name", "changes"), ACCEPTED)
def test_rule_accepts_good_variant(name: str, changes: dict[str, object]) -> None:
    CONTRACTS[name].model_validate(_mutated(name, changes))


def test_ready_task_with_no_claim_is_valid() -> None:
    changes: dict[str, object] = {
        "status": "ready",
        "claimed_by": None,
        "claimed_at": None,
        "branch": None,
        "pr": None,
    }
    CONTRACTS["task"].model_validate(_mutated("task", changes))


# ── Static evidence paths ────────────────────────────────────────────────────


def _finding(*evidence: dict[str, Any]) -> Finding:
    data = _valid("finding")
    data["evidence"] = list(evidence)
    return Finding.model_validate(data)


def _static(path: str, line: int) -> dict[str, Any]:
    return {"kind": "static", "repo": "repo-a", "path": path, "line": line, "commit": "9f3c2e1"}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "work" / "repo-a@9f3c2e1"
    (root / "service").mkdir(parents=True)
    (root / "service" / "app.py").write_text("one\ntwo\nthree\n", encoding="utf-8")
    (root / "service" / "tail.py").write_text("one\ntwo", encoding="utf-8")
    (root / "service" / "empty.py").write_text("", encoding="utf-8")
    return root


def test_static_evidence_that_resolves_has_no_problems(repo: Path) -> None:
    runtime = {"kind": "runtime", "source": "har", "entry": 3, "note": "302 to the IdP"}
    finding = _finding(_static("service/app.py", 3), _static("service/tail.py", 2), runtime)
    assert check_static_evidence(finding, repo) == []


def test_static_evidence_reports_missing_file_and_line_past_end(repo: Path) -> None:
    finding = _finding(
        _static("service/missing.py", 1),
        _static("service/app.py", 4),
        _static("service/tail.py", 3),
        _static("service/empty.py", 1),
        _static("service", 1),
    )
    assert check_static_evidence(finding, repo) == [
        "evidence[0] service/missing.py: file not found",
        "evidence[1] service/app.py: line 4 is past the end (3 lines)",
        "evidence[2] service/tail.py: line 3 is past the end (2 lines)",
        "evidence[3] service/empty.py: line 1 is past the end (0 lines)",
        "evidence[4] service: file not found",
    ]


def test_static_evidence_rejects_a_symlink_that_leaves_the_repo(repo: Path, tmp_path: Path) -> None:
    outside = tmp_path / "secret.txt"
    outside.write_text("x\n", encoding="utf-8")
    try:
        (repo / "link.txt").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are not available on this machine")
    finding = _finding(_static("link.txt", 1))
    assert check_static_evidence(finding, repo) == [
        "evidence[0] link.txt: path leaves the repo root"
    ]
