# Team Insights (fixture)

A small, synthetic internal app used to test Prototype Accelerator's extraction. It isn't real company code.

- `service/`: FastAPI API with OIDC token validation, role mapping, SQLAlchemy models and an Azure OpenAI summary endpoint.
- `web/`: React and TypeScript single-page app built with Vite.
- `mock-idp/`: a mock OpenID Connect identity provider for local runs.

## Build, test and run

```bash
make test      # backend pytest and web vitest, inside Docker
make run       # docker compose up: mock IdP on :9000, app on :8000
```

Sign in at http://localhost:8000/login as `alice` (analyst) or `bob` (viewer).
