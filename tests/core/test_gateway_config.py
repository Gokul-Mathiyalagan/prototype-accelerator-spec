"""Gateway settings: env, .env and accel.toml precedence, and key handling (ADR-0008)."""

from __future__ import annotations

from pathlib import Path

import pytest
from accel_core.errors import ConfigError
from accel_core.gateway import load_settings
from accel_core.gateway.config import read_dotenv

ENV = {
    "AZURE_OPENAI_ENDPOINT": "https://env-resource.openai.azure.com/",
    "AZURE_OPENAI_API_KEY": "env-key-0123456789",
}


def test_environment_alone_is_enough_and_defaults_apply(tmp_path: Path) -> None:
    settings = load_settings(root=tmp_path, environ=ENV)
    assert settings.endpoint == ENV["AZURE_OPENAI_ENDPOINT"]
    assert settings.api_key.get_secret_value() == ENV["AZURE_OPENAI_API_KEY"]
    assert settings.deployment == "gpt-6.1-sol"
    assert settings.api_version == "2024-10-21"
    assert settings.pricing is None


def test_dotenv_fills_gaps_and_the_environment_wins(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "# comment\n"
        "\n"
        'export AZURE_OPENAI_ENDPOINT="https://dotenv.openai.azure.com/"\n'
        "AZURE_OPENAI_API_KEY='dotenv-key-0123456789'\n"
        "AZURE_OPENAI_DEPLOYMENT_NAME=my-deployment  # trailing comment\n"
        "OPENAI_API_VERSION=2025-04-01-preview\n"
        "not a setting\n",
        encoding="utf-8",
    )
    from_dotenv = load_settings(root=tmp_path, environ={})
    assert from_dotenv.endpoint == "https://dotenv.openai.azure.com/"
    assert from_dotenv.api_key.get_secret_value() == "dotenv-key-0123456789"
    assert from_dotenv.deployment == "my-deployment"
    assert from_dotenv.api_version == "2025-04-01-preview"
    assert load_settings(root=tmp_path, environ=ENV).endpoint == ENV["AZURE_OPENAI_ENDPOINT"]


def test_accel_toml_supplies_non_secret_settings_and_pricing(tmp_path: Path) -> None:
    (tmp_path / "accel.toml").write_text(
        "[azure_openai]\n"
        'endpoint = "https://toml.openai.azure.com/"\n'
        'deployment = "toml-deployment"\n'
        'api_version = "2024-06-01"\n'
        "input_usd_per_mtok = 2.0\n"
        "output_usd_per_mtok = 8.0\n",
        encoding="utf-8",
    )
    settings = load_settings(root=tmp_path, environ={"AZURE_OPENAI_API_KEY": "k" * 20})
    assert settings.endpoint == "https://toml.openai.azure.com/"
    assert settings.deployment == "toml-deployment"
    assert settings.api_version == "2024-06-01"
    assert settings.pricing is not None
    assert settings.pricing.cost(1_000_000, 500_000) == pytest.approx(6.0)
    overridden = load_settings(
        root=tmp_path, environ={**ENV, "AZURE_OPENAI_DEPLOYMENT_NAME": "env-deployment"}
    )
    assert overridden.endpoint == ENV["AZURE_OPENAI_ENDPOINT"]
    assert overridden.deployment == "env-deployment"


@pytest.mark.parametrize(
    ("environ", "variable"),
    [
        ({"AZURE_OPENAI_API_KEY": "k" * 20}, "AZURE_OPENAI_ENDPOINT"),
        ({"AZURE_OPENAI_ENDPOINT": "https://x.openai.azure.com/"}, "AZURE_OPENAI_API_KEY"),
        ({**ENV, "AZURE_OPENAI_API_KEY": "   "}, "AZURE_OPENAI_API_KEY"),
    ],
)
def test_missing_setting_names_the_variable(
    tmp_path: Path, environ: dict[str, str], variable: str
) -> None:
    with pytest.raises(ConfigError) as caught:
        load_settings(root=tmp_path, environ=environ)
    assert caught.value.message.startswith(f"{variable} is not set.")
    assert ".env.example" in caught.value.message
    assert caught.value.exit_code == 3


@pytest.mark.parametrize("key", ["api_key", "API_KEY", "azure_openai_api_key"])
def test_an_api_key_in_accel_toml_is_rejected(tmp_path: Path, key: str) -> None:
    (tmp_path / "accel.toml").write_text(
        f'[azure_openai]\n{key} = "secret-in-toml"\n', encoding="utf-8"
    )
    with pytest.raises(ConfigError, match=r"Remove the API key from accel.toml") as caught:
        load_settings(root=tmp_path, environ=ENV)
    assert "secret-in-toml" not in caught.value.message


@pytest.mark.parametrize(
    ("toml", "message"),
    [
        (
            "[azure_openai]\nregion = 'eastus'\n",
            "Unknown [azure_openai] keys in accel.toml: region",
        ),
        ("[azure_openai\n", "accel.toml is not valid TOML"),
        ("azure_openai = 3\n", "[azure_openai] in accel.toml must be a table"),
        ("[azure_openai]\ninput_usd_per_mtok = 1.0\n", "Set both input_usd_per_mtok"),
    ],
)
def test_bad_accel_toml_is_rejected(tmp_path: Path, toml: str, message: str) -> None:
    (tmp_path / "accel.toml").write_text(toml, encoding="utf-8")
    with pytest.raises(ConfigError) as caught:
        load_settings(root=tmp_path, environ=ENV)
    assert message in caught.value.message


def test_invalid_values_name_the_field_but_never_echo_the_key(tmp_path: Path) -> None:
    environ = {**ENV, "AZURE_OPENAI_ENDPOINT": "http://plain-http.example.com"}
    with pytest.raises(ConfigError) as caught:
        load_settings(root=tmp_path, environ=environ)
    assert caught.value.message == "Invalid Azure OpenAI setting: endpoint"
    assert ENV["AZURE_OPENAI_API_KEY"] not in caught.value.message


def test_settings_never_show_the_key(tmp_path: Path) -> None:
    settings = load_settings(root=tmp_path, environ=ENV)
    for text in (repr(settings), str(settings), settings.model_dump_json()):
        assert ENV["AZURE_OPENAI_API_KEY"] not in text


def test_defaults_to_the_process_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.chdir(tmp_path)
    assert load_settings().endpoint == ENV["AZURE_OPENAI_ENDPOINT"]


def test_read_dotenv_of_a_missing_file_is_empty(tmp_path: Path) -> None:
    assert read_dotenv(tmp_path / ".env") == {}


def test_env_example_lists_the_four_variables_with_placeholders() -> None:
    root = Path(__file__).resolve().parents[2]
    values = read_dotenv(root / ".env.example")
    assert set(values) == {
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT_NAME",
        "OPENAI_API_VERSION",
    }
    assert "your-resource-name" in values["AZURE_OPENAI_ENDPOINT"]
    assert values["AZURE_OPENAI_API_KEY"].startswith("your-")
