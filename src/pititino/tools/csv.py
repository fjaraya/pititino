from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from pititino.errors import UnsupportedFileTypeError
from pititino.transactions.changeset import ChangeOperation, ChangeSet
from pititino.workspace import Workspace


class CsvArguments(BaseModel):
    file: str
    max_rows: int = Field(default=100, gt=0, le=10_000)


class CsvWriteArguments(BaseModel):
    file: str
    rows: list[list[str]] = Field(min_length=1)


def propose_write(arguments: CsvWriteArguments) -> ChangeSet:
    return ChangeSet(
        target=arguments.file,
        summary=f"Append {len(arguments.rows)} CSV rows to {arguments.file}",
        operations=[
            ChangeOperation(
                operation="csv_append_rows",
                description=f"Append {len(arguments.rows)} rows to {arguments.file}",
                arguments=arguments.model_dump(),
            )
        ],
    )


def _csv_path(workspace: Workspace, file: str) -> Path:
    path = workspace.resolve(file, must_exist=True)
    if path.suffix.lower() != ".csv":
        raise UnsupportedFileTypeError("CSV tools require a .csv file")
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def inspect(workspace: Workspace, arguments: CsvArguments) -> dict[str, Any]:
    path = _csv_path(workspace, arguments.file)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        headers = next(reader, [])
        rows = []
        for row in reader:
            rows.append(row)
            if len(rows) >= arguments.max_rows:
                break
    types = Counter(
        "number" if _is_number(value) else "boolean" if value.lower() in {"true", "false"} else "text"
        for row in rows
        for value in row
        if value
    )
    return {
        "file": str(path.relative_to(workspace.root)),
        "headers": headers,
        "sample_rows": rows[:5],
        "sample_types": dict(types),
        "truncated": len(rows) >= arguments.max_rows,
    }


def read(workspace: Workspace, arguments: CsvArguments) -> dict[str, Any]:
    path = _csv_path(workspace, arguments.file)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append(dict(row))
            if len(rows) >= arguments.max_rows:
                break
    return {
        "file": str(path.relative_to(workspace.root)),
        "headers": reader.fieldnames or [],
        "rows": rows,
        "truncated": len(rows) >= arguments.max_rows,
    }


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True
