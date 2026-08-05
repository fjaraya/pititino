from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    base_url: str = "http://localhost:8000/v1"
    model: str = "default"
    api_key_env: str = "PITITINO_API_KEY"
    tool_calling: Literal["auto", "native", "json"] = "auto"
    temperature: float = 0.2
    max_output_tokens: int = Field(default=8192, gt=0)

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


class Settings(BaseModel):
    model: ModelConfig = ModelConfig()
    workspace: WorkspaceConfig = WorkspaceConfig()
    security: SecurityConfig = SecurityConfig()
    excel: ExcelConfig = ExcelConfig()


def default_config_path() -> Path:
    return Path.home() / ".config" / "pititino" / "config.toml"


def load_settings(path: Path | None = None) -> Settings:
    config_path = path or default_config_path()
    if not config_path.exists():
        return Settings()
    with config_path.open("rb") as handle:
        return Settings.model_validate(tomllib.load(handle))
