# Handoff

- **Updated:** 2026-11-10 19:26 IST
- **Agent:** claude-code
- **Active task:** T-003 Contract models and generated schemas
- **Task status:** review
- **Branch:** task/T-003-contracts-and-schemas
- **Last commit:** f0845e9 T-003: add contract models, schemas and fixtures

## Summary

T-003 is ready for review. `accel_core.contracts` has 15 Pydantic contract models (spec/05's table has 14 rows, but `eval-case` and `eval-report` share one). `make schemas` writes `schemas/*.schema.json`, and `make check` now fails on schema drift. All 185 offline tests pass.

## Acceptance criteria

- [x] Models exist for all 14 contracts in spec/05, each with schema_version, extra='forbid'. Verified by `test_registry_matches_spec_contract_table` and `test_every_contract_is_versioned_strict_and_frozen`.
- [x] make schemas writes schemas/<name>.schema.json; CI fails on drift between models and committed schemas. CI already ran `make schemas` + `git diff`; `make check` now also runs `scripts/generate_schemas.py --check` (tests in `tests/dev/test_generate_schemas.py`).
- [x] Each spec/05 example validates; at least one invalid fixture per contract is rejected with a clear error. The examples are parsed from the spec/05 markdown itself (`test_spec_05_example_validates`). The invalid fixtures and the error text each must produce are listed in `tests/fixtures/contracts/invalid/expected.yaml`.
- [x] Finding validation enforces non-empty evidence, id format <playbook>.<slug>, and confidence enum; path existence is a separate function that takes a repo root: `check_static_evidence(finding, repo_root) -> list[str]` in `contracts/finding.py`.

## State of the active task

- `packages/accel-core/src/accel_core/contracts/`: `_base.py` holds the `Contract` and `Part` bases and shared field types; there is one module per area (`finding`, `playbook`, `knowledge`, `setup`, `skills`, `evals`, `ui_spec`, `project`, `task`, `gate`); `__init__.py` has the `CONTRACTS` registry (name → model) and `json_schema(name)`.
- `scripts/generate_schemas.py`: writes the schemas and removes orphaned ones; `--check` reports drift and exits 1. `scripts/dev.py` now calls it from `schemas` and `check`.
- `schemas/`: 15 generated files. Don't hand-edit them.
- Tests: `tests/core/test_contracts.py` (spec examples, fixtures, 36 rule mutations, evidence path checks) and `tests/dev/test_generate_schemas.py`.

## Next step

1. Gokul reviews `task/T-003-contracts-and-schemas`, merges it, and sets T-003 `status: done`.
2. After that, the next eligible tasks are T-004 (gateway; needs `azure`), plus T-108 and T-201, which depend only on T-003.

## How to verify

```bash
uv run make check
uv run make schemas && git status --short schemas   # expect no changes
```

Expected: 185 passed and 1 skipped (the symlink-escape test skips on Windows without symlink rights and runs on Linux CI). `accel-core` has 99.8% line coverage.

## Decisions and assumptions

- `schema_version` is `Literal[1]` with a default of 1, because the catalog-entry, task and project examples omit it. A version 2 file is rejected with a clear error.
- Inferred shapes where the spec gives no full example: `knowledge-manifest` (`stages`, `tool_versions`), the `extract-plan` YAML header, `eval-report` (stored rates must match the cases; `passed` must match the thresholds; `stopped_early` forces a fail), and catalog `emit_when` (`always`, or `playbook` and/or `inventory`, plus `min_confidence`).
- Rules added from spec prose: in a finding, the id prefix must equal `playbook`; static evidence needs `line`; HAR evidence needs `entry` and screenshot evidence needs `path`; `recorded_by` is `copilot:<model>` or `batch:<model>`. Pilot and production projects need `oidc` and a real data adapter. Task claim fields must match the status, a blocked task needs the new `blocked_reason` field, and an in_review task needs `pr`. `install-check.ok` must equal "every component is ok". Timestamps must include a timezone.
- Inventory signals (`auth_library_or_middleware`) are snake_case, unlike slugs.

## Spec changes

- Wording fix in `spec/03-skill-factory.md#evals`: the example rubric moved its weights out of YAML comments into `{criterion, weight}` items, to match `EvalCase`.

## Open questions for Gokul

- Is `blocked_reason` on the product task contract OK? spec/04 says "blocked (with reason)" but spec/05's example has no field for it.

## Watch out

- The spec/05 gate-record example uses `<hash>` placeholders; the test replaces them with a dummy hex digest before validating.
- In YAML, an all-digit hash or commit parses as an int and is rejected. Quote such values in fixtures.
