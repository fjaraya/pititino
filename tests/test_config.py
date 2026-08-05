import os

import pytest

from pititino.config import Settings, load_dotenv, load_settings
from pititino.errors import ConfigurationError


def test_default_settings_disable_shell() -> None:
    settings = Settings()
    assert settings.security.allow_shell is False
    assert settings.security.confirm_writes is True
    assert settings.agent.max_tool_rounds == 20
    assert settings.agent.timeout_seconds == 120
    assert settings.agent.max_history_turns == 10
    assert settings.model.api == "chat_completions"


def test_load_settings_reads_toml(tmp_path, monkeypatch) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        '[model]\nmodel = "local"\ntemperature = 0.5\n\n[workspace]\nroot = "reports"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("PITITINO_API_KEY", "secret")

    settings = load_settings(path)

    assert settings.model.model == "local"
    assert settings.model.temperature == 0.5
    assert settings.workspace.root == "reports"


def test_load_settings_reports_malformed_toml(tmp_path) -> None:
    path = tmp_path / "config.toml"
    path.write_text("[model\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Invalid TOML"):
        load_settings(path)


def test_load_settings_reports_invalid_values(tmp_path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('[model]\ntool_calling = "unsupported"\n', encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Invalid configuration"):
        load_settings(path)


def test_load_dotenv_reads_key_without_overwriting_environment(tmp_path, monkeypatch) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text('PITITINO_API_KEY="from-file"\nOTHER=value\n', encoding="utf-8")
    monkeypatch.delenv("PITITINO_API_KEY", raising=False)

    load_dotenv(dotenv)

    assert os.environ["PITITINO_API_KEY"] == "from-file"
    monkeypatch.setenv("PITITINO_API_KEY", "explicit")
    load_dotenv(dotenv)
    assert os.environ["PITITINO_API_KEY"] == "explicit"
