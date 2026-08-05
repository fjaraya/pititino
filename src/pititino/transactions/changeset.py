from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FileRevision(BaseModel):
    size: int
    mtime_ns: int
    sha256: str | None = None


class ChangeOperation(BaseModel):
    operation: Literal[
        "create_sheet",
        "write_range",
        "text_replace",
        "text_append",
        "structured_set",
        "csv_append_rows",
        "restore_backup",
    ]
    description: str
    arguments: dict[str, Any]


class ChangeSet(BaseModel):
    target: str
    operations: list[ChangeOperation] = Field(min_length=1)
    summary: str
    requires_confirmation: bool = True
    source_revision: FileRevision | None = None
