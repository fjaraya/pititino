from __future__ import annotations

import json
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from pititino.errors import ToolExecutionError, UnsupportedFileTypeError
from pititino.transactions.changeset import ChangeOperation, ChangeSet
from pititino.workspace import Workspace


class StructuredReadArguments(BaseModel):
    file: str
    max_chars: int = Field(default=50_000, gt=0, le=1_000_000)


class StructuredSetArguments(BaseModel):
    file: str
    path: str = Field(min_length=1, description="Dotted object path, such as service.replicas")
    value: Any


def read_json(workspace: Workspace, arguments: StructuredReadArguments) -> dict[str, Any]:
    return _read(workspace, arguments, ".json", json.loads, "json")


def read_yaml(workspace: Workspace, arguments: StructuredReadArguments) -> dict[str, Any]:
    return _read(workspace, arguments, (".yaml", ".yml"), yaml.safe_load, "yaml")


def propose_set(arguments: StructuredSetArguments, format_name: Literal["json", "yaml"]) -> ChangeSet:
    return ChangeSet(
        target=arguments.file,
        summary=f"Set {format_name.upper()} value at {arguments.path}",
        operations=[
            ChangeOperation(
                operation="structured_set",
                description=f"Set {arguments.path} in {arguments.file}",
                arguments={**arguments.model_dump(), "format": format_name},
            )
        ],
    )


def _read(
    workspace: Workspace,
    arguments: StructuredReadArguments,
    extensions: str | tuple[str, ...],
    parser: Any,
    format_name: Literal["json", "yaml"],
) -> dict[str, Any]:
    path = workspace.resolve(arguments.file, must_exist=True)
    accepted = (extensions,) if isinstance(extensions, str) else extensions
    if path.suffix.lower() not in accepted:
        raise UnsupportedFileTypeError(f"{format_name.upper()} tools require {accepted} files")
    if not path.is_file():
        raise FileNotFoundError(path)
    raw = path.read_text(encoding="utf-8")
    if len(raw) > arguments.max_chars:
        raise ToolExecutionError(f"{format_name.upper()} file exceeds max_chars ({arguments.max_chars})")
    try:
        value = parser(raw)
    except (ValueError, yaml.YAMLError) as exc:
        raise ToolExecutionError(f"Invalid {format_name.upper()} document {path.name}: {exc}") from exc
    return {"file": str(path.relative_to(workspace.root)), "format": format_name, "value": value}
