# Handoff

- **Updated:** 2026-11-10 22:05 IST
- **Agent:** claude-code
- **Active task:** T-007 Fixture repos
- **Task status:** review
- **Branch:** task/T-007-fixture-repos
- **Last commit:** 73d1086 T-007: EXPECTED.md, fixture tests, redaction fix for prefixed secrets

## Summary

Both fixture repos are built and tested. `fastapi-react-sso` builds in Docker (vitest and pytest pass inside the build) and runs with its mock IdP: sign-in, role checks and the SPA all work. `native-sdk-sample` has two committed ELF `.so` files and a working ctypes caller. The fixture caught a real redaction gap (`DB_PASSWORD = "..."` leaked), which is now fixed in `accel_core.redaction`. `make check`: 346 passed.

## Acceptance criteria

- [x] fastapi-react-sso: FastAPI service with OIDC-style token middleware and role mapping, SQLAlchemy models, an LLM client call through an Azure gateway pattern, a React app with routes, a component library, design tokens, and tests; builds and runs with a mock identity provider. Verified by `tests/extract/test_fixture_repos_run.py`: the image build runs vitest (2) and pytest (9), then a smoke test signs in as bob (viewer, export 403) and alice (analyst, export 200).
- [x] Contains a planted fake secret and fake personal data that redaction must remove. Listed under "Planted sensitive data" in its EXPECTED.md; `test_redaction_removes_each_planted_value` runs the real `Redactor`.
- [x] native-sdk-sample: a tiny C library built to a .so/.dylib with a permissive license file, plus a Python ctypes caller; and a second binary with a no-reverse-engineering license. tinymath (MIT, with source and a Makefile for `.so`/`.dylib`) and secretsauce (prebuilt only, no-RE license); the ctypes caller and its tests run in Docker.
- [x] Expected findings for each playbook are written down in tests/fixtures/repos/<repo>/EXPECTED.md for later golden tests. Every playbook is listed; each finding is built into the `Finding` contract and passed through `check_static_evidence`, and each snippet must appear on its cited line.

## State of the active task

- `tests/fixtures/repos/fastapi-react-sso/`: `service/` (FastAPI, SQLAlchemy, JWT middleware, roles, LLM gateway, prompt file, JSON logs), `mock-idp/`, `web/` (React, Vite, components, tokens, vitest), `Dockerfile`, `docker-compose.yml`, `Makefile`, `.github/workflows/ci.yml`, `EXPECTED.md`.
- `tests/fixtures/repos/native-sdk-sample/`: `vendor/tinymath/` (source, MIT, `lib/libtinymath.so`), `vendor/secretsauce/` (header, no-RE license, `lib/libsecretsauce.so`), `python/sdk_client.py` and tests, `EXPECTED.md`.
- `tests/fixtures/repos/_sources/`: `secretsauce.c` and `build_native.sh` (rebuilds both `.so` files in a `gcc:14.2.0` container). They live outside the fixture so secretsauce looks source-less.
- `tests/extract/test_fixture_repos.py` (offline, 42 tests) and `test_fixture_repos_run.py` (Docker, 2 tests).
- The Docker helpers moved from `tests/setup/conftest.py` to `tests/conftest.py` (`docker_image(dockerfile, context=None)`, with the tag hashed from the context).
- `pyproject.toml`: pytest's `norecursedirs` now includes `fixtures`, because the fixture repos' own suites only run inside their images.

## Next step

1. Gokul reviews and merges `task/T-007-fixture-repos`, then sets T-007 `done`.
2. Push `main`: it has ADR-0009 (`0dc1ed6`), which is unpushed and already merged into this branch.
3. Next eligible tasks: T-006 (setup assets for Copilot and Claude Code, per ADR-0009), T-108 (playbooks), T-201 (catalog). T-101+ can now use these fixtures.

## How to verify

```bash
uv run make check     # 346 passed; includes the fixture Docker tests (first build downloads npm/pip packages)
bash tests/fixtures/repos/_sources/build_native.sh   # rebuild the .so files
```

## Decisions and assumptions

- Redaction fix (T-004 code): a new case-sensitive `secret` rule for UPPER_SNAKE names ending in PASSWORD, SECRET, TOKEN, API_KEY or ACCESS_KEY. Lower-case code such as `access_token = body.access_token` is deliberately not matched (`test_ordinary_code_and_text_is_left_alone`).
- The planted AWS key is AWS's documented example (`AKIAIOSFODNN7EXAMPLE`), so GitHub push protection doesn't block it. Passwords and secrets are obvious fake strings.
- The `.so` files are committed and Linux-only. The Makefile builds `.dylib` on macOS, but no `.dylib` is committed.
- Mock sign-in goes through the app (`/auth/token`, only when `AUTH_MODE=mock`), so tokens carry the IdP's in-network issuer.
- `make check` builds the fixture image when Docker is available; CI's first run downloads the pinned npm and pip packages.

## Spec changes

- ADR-0009 (accepted by Gokul, on `main`): Claude Code can also run `/accel-setup`. It amends C1, ADR-0002, spec/02 and spec/06, and T-006 now has Claude Code acceptance criteria.

## Open questions for Gokul

- `make test-live` breaks on Windows without `UV=uv` (the Makefile `$(UV)` path is mangled by sh). Should I add a task to fix it?

## Watch out

- In Git Bash, Docker arguments like `/mock-idp` are rewritten to `C:/Program Files/Git/...`; use `MSYS_NO_PATHCONV=1` (pytest's subprocess calls aren't affected).
- The `accel-live-home` Docker volume (about 2 GB) holds the T-005 live install.
