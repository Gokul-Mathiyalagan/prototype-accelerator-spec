# Expected findings: fastapi-react-sso

What a correct extraction of this fixture should find, per playbook, for golden tests (T-104, T-109, T-113, T-114). Paths are relative to this folder. Each evidence entry is `path:line` and a snippet that appears on that line; `tests/extract/test_fixture_repos.py` checks every one.

Format: `- **<finding id>** · <confidence> · <claim> Evidence: \`path:line\` "snippet"; ...`

## repo-overview

- **repo-overview.layout** · high · A FastAPI service in `service/`, a React web app in `web/` and a mock identity provider in `mock-idp/`, built and tested together in one Docker image. Evidence: `Dockerfile:2` "FROM node:24.22.1-bookworm-slim AS web"; `Dockerfile:9` "FROM python:3.12.8-slim-bookworm"
- **repo-overview.build-test-run** · high · `make test` builds the image, which runs vitest and pytest; `make run` starts the stack with docker compose. Evidence: `README.md:12` "make test"; `Dockerfile:7` "RUN npm test && npm run build"; `Dockerfile:15` "RUN python -m pytest -q"

## ui-architecture

- **ui-architecture.routing** · high · Client-side routing with react-router's `BrowserRouter`; the team dashboard route is `/teams/:id`. Evidence: `web/src/App.tsx:8` "<BrowserRouter>"; `web/src/App.tsx:12` "path=\"/teams/:id\""
- **ui-architecture.data-fetching** · high · Pages fetch through one API client that adds the bearer token and turns error envelopes into typed errors. Evidence: `web/src/api/client.ts:14` "Authorization: `Bearer"
- **ui-architecture.screen-states** · medium · The dashboard renders loading, error and no-access states, with no-access mapped from HTTP 403. Evidence: `web/src/pages/TeamDashboard.tsx:26` "error.status === 403"

## design-system

- **design-system.tokens** · high · Colors and spacing are CSS custom properties in one tokens file, mirrored as TypeScript names. Evidence: `web/src/tokens/tokens.css:6` "--color-primary"; `web/src/tokens/tokens.ts:7` "primary: \"var(--color-primary)\""
- **design-system.components** · high · A small component library (`Button`, `DataTable`, `PageShell`) is exported from one index. Evidence: `web/src/components/index.ts:1` "export { Button }"; `web/src/components/DataTable.tsx:13` "export function DataTable"

## api-surface

- **api-surface.versioning** · high · Every endpoint is under `/api/v1`. Evidence: `service/app/api/teams.py:17` "APIRouter(prefix=\"/api/v1\")"
- **api-surface.pagination** · high · Lists use `page` and `page_size` (max 100) and return `items`, `page`, `page_size` and `total`. Evidence: `service/app/api/teams.py:31` "le=100"; `service/app/api/teams.py:43` "\"total\": total"
- **api-surface.error-envelope** · high · Errors use one envelope, `{"error": {code, message, request_id}}`. Evidence: `service/app/errors.py:17` "\"request_id\": request_id.get()"

## auth-sso

- **auth-sso.token-validation** · high · One middleware validates RS256 bearer tokens on every `/api` request against the identity provider's JWKS, with issuer and audience checks. Evidence: `service/app/auth.py:41` "class TokenValidationMiddleware"; `service/app/auth.py:35` "algorithms=[\"RS256\"]"; `service/app/auth.py:24` "config[\"jwks_uri\"]"
- **auth-sso.key-caching** · medium · Signing keys are cached for five minutes. Evidence: `service/app/auth.py:17` "JWKS_TTL_SECONDS = 300"
- **auth-sso.role-mapping** · high · Identity-provider groups map to app roles in one table, and routes declare the role they need. Evidence: `service/app/roles.py:3` "ROLE_MAPPING = {"; `service/app/api/teams.py:49` "require_role(\"analyst\")"
- **auth-sso.mock-idp** · high · Local runs use a mock OIDC provider with discovery, JWKS and a token endpoint, and the app forwards sign-ins to it only when `AUTH_MODE=mock`. Evidence: `mock-idp/mock_idp.py:27` "\"jwks_uri\""; `service/app/main.py:44` "AUTH_MODE == \"mock\""

## data-access

- **data-access.orm** · high · SQLAlchemy 2.0 declarative models (`Team`, `TeamMember`) with a session per request. Evidence: `service/app/models.py:19` "class TeamMember(Base)"; `service/app/db.py:10` "create_engine"
- **data-access.seeding** · medium · Synthetic seed data loads on first start. Evidence: `service/app/main.py:36` "seed()"

## ai-llm

- **ai-llm.gateway** · high · All model calls go through one `LlmGateway` wrapping the Azure OpenAI client, with one deployment and retries. Evidence: `service/app/llm.py:12` "class LlmGateway"; `service/app/llm.py:20` "AzureOpenAI("; `service/app/llm.py:32` "model=settings.AZURE_OPENAI_DEPLOYMENT"
- **ai-llm.prompt-files** · high · Prompts are markdown templates in `app/prompts/`. Evidence: `service/app/prompts/team_summary.prompt.md:3` "Team: {team_name}"

## backend-architecture

- **backend-architecture.layering** · medium · Routers in `app/api/` call models and the LLM gateway directly; cross-cutting concerns (auth, request IDs, errors) are middleware and an exception handler. Evidence: `service/app/errors.py:9` "class ApiError(Exception)"; `service/app/main.py:28` "new_request_id("

## observability

- **observability.structured-logs** · high · Logs are JSON lines with a request ID, taken from `x-request-id` or generated, and echoed in the response. Evidence: `service/app/logging_setup.py:11` "class JsonFormatter"; `service/app/logging_setup.py:18` "\"request_id\": request_id.get()"; `service/app/main.py:28` "x-request-id"

## delivery

- **delivery.container** · high · A multi-stage Dockerfile builds the web app, runs both test suites, and serves the API on port 8000. Evidence: `Dockerfile:18` "CMD [\"uvicorn\""
- **delivery.compose** · high · docker compose runs the app and the mock IdP. Evidence: `docker-compose.yml:2` "idp:"; `docker-compose.yml:13` "AUTH_MODE: mock"
- **delivery.ci** · medium · CI builds the Docker image, which runs the tests. Evidence: `.github/workflows/ci.yml:8` "docker build"

## native-artifacts

Not included: the repo has no native binaries, so `extract prepare` should leave this playbook out.

## Planted sensitive data

Redaction (stage 1 and the gateway) must remove every value below. None is real.

- `aws_access_key` at `service/app/settings.py:14` "AKIAIOSFODNN7EXAMPLE"
- `secret` at `service/app/settings.py:15` "hunter2-fixture-only"
- `secret` at `service/app/settings.py:16` "fixture-session-secret-not-real"
- `email` at `service/data/seed_members.json:5` "priya.raman@example.com"
- `phone` at `service/data/seed_members.json:5` "+1 415-555-0142"
- `employee_id` at `service/data/seed_members.json:5` "EMP-100231"
- `email` at `service/data/seed_members.json:6` "marcus.lee@example.com"
- `phone` at `service/data/seed_members.json:6` "+91 98765 43210"
- `email` at `service/data/seed_members.json:7` "ana.souza@example.com"
- `phone` at `service/data/seed_members.json:7` "(212) 555-0199"

## Unknowns

These should go to `unknowns.md`: how tokens are refreshed (the app has no refresh flow), and which real identity provider replaces the mock in production.
