# ADR-0008: Authenticate to Azure OpenAI with a deployment API key

- **Status:** accepted
- **Date:** 2026-11-10
- **Proposed by:** gokul
- **Decided by:** gokul
- **Task:** T-004

## Context

ADR-0005 and spec/01 said the gateway authenticates with Microsoft Entra ID through `DefaultAzureCredential` (`az login` or a service principal), and that API keys aren't supported. Gokul will run the platform against an Azure OpenAI deployment using that resource's endpoint and API key, so Entra ID sign-in is no longer the path.

## Decision

The gateway authenticates with the Azure OpenAI resource's API key. It reads four environment variables:

| Env var | Purpose | Default |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | Resource endpoint, `https://<resource>.openai.azure.com/` | none (required) |
| `AZURE_OPENAI_API_KEY` | Resource API key | none (required; environment only) |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Deployment to call | `gpt-6.1-sol` |
| `OPENAI_API_VERSION` | Azure OpenAI API version | `2024-10-21`, pinned in `accel.toml.example` |

These names replace `AZURE_OPENAI_DEPLOYMENT` and `AZURE_OPENAI_API_VERSION` from spec/01. They're the names the `openai` package's `AzureOpenAI` client reads by default.

The key is a secret:

- It comes only from the environment or a gitignored `.env` file, never from `accel.toml`. The gateway rejects an `api_key` setting in `accel.toml`.
- It's never logged, written to the audit trail, or included in error messages.
- `.env.example` documents the four variables with placeholder values only.

Everything else in ADR-0005 still holds: Azure OpenAI is the only model API, reached only through `accel_core.gateway` with the `AzureOpenAI` client, and the CI guard is unchanged.

## Alternatives considered

- **Entra ID only (ADR-0005 as written).** Not available for how Gokul runs the platform.
- **Entra ID with an API key fallback.** That means two auth paths to build and test, and nothing needs Entra ID now. A later ADR can add it back.

## Consequences

- `azure-identity` isn't a dependency.
- A missing endpoint or key raises a typed configuration error that names the variable. The CLI maps it to exit code 3 (missing prerequisite).
- A leaked key grants access until it's rotated in Azure. `.env` and `accel.toml` are already gitignored, so the key stays out of the repo unless someone commits it deliberately.

## Affects

- Spec sections: 01 (configuration, tech stack), 02 (batch mode), 06 (C1 control); amends ADR-0005
- Tasks: T-004
