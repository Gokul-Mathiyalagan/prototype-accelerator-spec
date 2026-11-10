"""Azure OpenAI settings from the environment, a `.env` file and `accel.toml` (ADR-0008)."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from accel_core.errors import ConfigError

ENDPOINT_VAR = "AZURE_OPENAI_ENDPOINT"
API_KEY_VAR = "AZURE_OPENAI_API_KEY"
DEPLOYMENT_VAR = "AZURE_OPENAI_DEPLOYMENT_NAME"
API_VERSION_VAR = "OPENAI_API_VERSION"

DEFAULT_DEPLOYMENT = "gpt-6.1-sol"
DEFAULT_API_VERSION = "2024-10-21"

# accel.toml [azure_openai] keys, and the env var that overrides each.
_TOML_KEYS = {
    "endpoint": ENDPOINT_VAR,
    "deployment": DEPLOYMENT_VAR,
    "api_version": API_VERSION_VAR,
}
_PRICING_KEYS = ("input_usd_per_mtok", "output_usd_per_mtok")
_FIX = "Set it in your environment or in a gitignored .env file (see .env.example)."


class Pricing(BaseModel):
    """US dollars per million tokens, used to cost calls and enforce cost budgets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_usd_per_mtok: float = Field(ge=0)
    output_usd_per_mtok: float = Field(ge=0)

    def cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Return the cost of one call in US dollars."""
        return (
            prompt_tokens * self.input_usd_per_mtok + completion_tokens * self.output_usd_per_mtok
        ) / 1_000_000


class AzureOpenAISettings(BaseModel):
    """Everything the gateway needs to reach one Azure OpenAI deployment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    endpoint: str = Field(pattern=r"^https://\S+$")
    api_key: SecretStr
    deployment: str = Field(min_length=1)
    api_version: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}(-preview)?$")
    pricing: Pricing | None = None


def read_dotenv(path: Path) -> dict[str, str]:
    """Parse simple KEY=VALUE lines from a `.env` file. Missing files yield nothing."""
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].strip()
        values[key.strip()] = value
    return values


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path.name} is not valid TOML: {error}") from error
    section: object = data.get("azure_openai", {})
    if not isinstance(section, dict):
        raise ConfigError(f"[azure_openai] in {path.name} must be a table")
    table = cast("dict[str, Any]", section)
    if any("key" in key.lower() for key in table):
        raise ConfigError(f"Remove the API key from {path.name}. Set {API_KEY_VAR} instead. {_FIX}")
    unknown = sorted(set(table) - set(_TOML_KEYS) - set(_PRICING_KEYS))
    if unknown:
        raise ConfigError(f"Unknown [azure_openai] keys in {path.name}: {', '.join(unknown)}")
    return table


def load_settings(
    *,
    root: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> AzureOpenAISettings:
    """Resolve settings. Precedence: environment, then `.env`, then `accel.toml`, then defaults.

    `root` is the folder holding `.env` and `accel.toml` (default: the current directory).
    Raises ConfigError naming the variable when the endpoint or key is missing.
    """
    base = root or Path.cwd()
    env = dict(os.environ if environ is None else environ)
    dotenv = read_dotenv(base / ".env")
    toml = _read_toml(base / "accel.toml")

    def pick(var: str, toml_key: str | None, default: str | None) -> str | None:
        for source in (env.get(var), dotenv.get(var)):
            if source and source.strip():
                return source.strip()
        if toml_key is not None and toml.get(toml_key):
            return str(toml[toml_key])
        return default

    endpoint = pick(ENDPOINT_VAR, "endpoint", None)
    if endpoint is None:
        raise ConfigError(f"{ENDPOINT_VAR} is not set. {_FIX}")
    api_key = pick(API_KEY_VAR, None, None)
    if api_key is None:
        raise ConfigError(f"{API_KEY_VAR} is not set. {_FIX}")
    deployment = pick(DEPLOYMENT_VAR, "deployment", DEFAULT_DEPLOYMENT)
    api_version = pick(API_VERSION_VAR, "api_version", DEFAULT_API_VERSION)

    pricing: Pricing | None = None
    present = [key for key in _PRICING_KEYS if key in toml]
    if present:
        if len(present) != len(_PRICING_KEYS):
            raise ConfigError("Set both input_usd_per_mtok and output_usd_per_mtok, or neither")
        pricing = Pricing.model_validate({key: toml[key] for key in _PRICING_KEYS})

    try:
        return AzureOpenAISettings(
            endpoint=endpoint,
            api_key=SecretStr(api_key),
            deployment=deployment or DEFAULT_DEPLOYMENT,
            api_version=api_version or DEFAULT_API_VERSION,
            pricing=pricing,
        )
    except ValidationError as error:
        # Name the fields only: input values could include the key.
        fields = sorted({str(item["loc"][0]) for item in error.errors()})
        raise ConfigError(f"Invalid Azure OpenAI setting: {', '.join(fields)}") from None
