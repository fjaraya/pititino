from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from pititino.errors import ConfigurationError


class ModelConfig(BaseModel):
    api: Literal["chat_completions"] = "chat_completions"
    base_url: str = "http://localhost:8000/v1"
    model: str = "default"
    api_key_env: str = "PITITINO_API_KEY"
    tool_calling: Literal["auto", "native", "json"] = "auto"
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_output_tokens: int = Field(default=8192, gt=0)

    @field_validator("base_url", "model", "api_key_env")
    @classmethod
    def require_value(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "not-used")


class WorkspaceConfig(BaseModel):
    root: str = "."
    allow_parent_access: bool = False


class SecurityConfig(BaseModel):
    confirm_writes: bool = True
    confirm_deletes: bool = True
    create_backups: bool = True
    allow_shell: bool = False


class ExcelConfig(BaseModel):
    max_rows_per_read: int = Field(default=500, gt=0)
    max_cells_per_read: int = Field(default=10_000, gt=0)


class AgentConfig(BaseModel):
    max_tool_rounds: int = Field(default=20, gt=0, le=100)
    timeout_seconds: float = Field(default=120, gt=0, le=3600)
    max_history_turns: int = Field(default=10, gt=0, le=100)


class Settings(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    excel: ExcelConfig = Field(default_factory=ExcelConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)


def default_config_path() -> Path:
    return Path.home() / ".config" / "pititino" / "config.toml"


def load_settings(path: Path | None = None) -> Settings:
    load_dotenv()
    config_path = path or default_config_path()
    if not config_path.exists():
        return Settings()
    try:
        with config_path.open("rb") as handle:
            values = tomllib.load(handle)
        return Settings.model_validate(values)
    except OSError as exc:
        raise ConfigurationError(f"Unable to read configuration {config_path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError(f"Invalid TOML in {config_path}: {exc}") from exc
    except ValidationError as exc:
        raise ConfigurationError(f"Invalid configuration in {config_path}: {exc}") from exc


def load_dotenv(path: Path | None = None) -> None:
    """Load simple KEY=VALUE entries without replacing explicit environment values."""
    dotenv_path = path or Path.cwd() / ".env"
    if not dotenv_path.exists():
        return
    try:
        lines = dotenv_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ConfigurationError(f"Unable to read dotenv file {dotenv_path}: {exc}") from exc

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key.strip()):
            raise ConfigurationError(f"Invalid dotenv entry at {dotenv_path}:{line_number}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)
