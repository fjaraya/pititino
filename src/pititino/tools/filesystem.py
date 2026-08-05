from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from pititino.workspace import Workspace


class ListArguments(BaseModel):
    path: str = "."


class StatArguments(BaseModel):
    path: str


class ReadTextArguments(BaseModel):
    path: str
    max_chars: int = Field(default=20_000, gt=0, le=1_000_000)


def list_files(workspace: Workspace, arguments: ListArguments) -> dict[str, Any]:
    directory = workspace.resolve(arguments.path, must_exist=True)
    if not directory.is_dir():
        raise NotADirectoryError(directory)
    entries = []
    for entry in sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        entries.append({"name": entry.name, "type": "directory" if entry.is_dir() else "file"})
    return {"path": str(directory.relative_to(workspace.root) or "."), "entries": entries}


def stat_file(workspace: Workspace, arguments: StatArguments) -> dict[str, Any]:
    path = workspace.resolve(arguments.path, must_exist=True)
    info = path.stat()
    return {
        "path": str(path.relative_to(workspace.root)),
        "name": path.name,
        "type": "directory" if path.is_dir() else "file",
        "size": info.st_size,
        "modified": info.st_mtime,
    }


def read_text(workspace: Workspace, arguments: ReadTextArguments) -> dict[str, Any]:
    path = workspace.resolve(arguments.path, must_exist=True)
    if not path.is_file():
        raise IsADirectoryError(path)
    content = path.read_text(encoding="utf-8")
    return {
        "path": str(path.relative_to(workspace.root)),
        "content": content[: arguments.max_chars],
        "truncated": len(content) > arguments.max_chars,
    }
