"""Configuration, read from the environment with local defaults."""

import os

OIDC_ISSUER = os.environ.get("OIDC_ISSUER", "http://localhost:9000")
OIDC_AUDIENCE = os.environ.get("OIDC_AUDIENCE", "team-insights")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./team-insights.db")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-6.1-sol")
LLM_MODE = os.environ.get("LLM_MODE", "azure")  # "fake" in tests and local runs
AUTH_MODE = os.environ.get("AUTH_MODE", "oidc")  # "mock" forwards sign-in to the mock IdP

# FIXTURE: planted secrets that redaction must remove. None of these are real.
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
DB_PASSWORD = "hunter2-fixture-only"
SESSION_SECRET = "fixture-session-secret-not-real"
