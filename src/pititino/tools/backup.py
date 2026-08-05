from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from pititino.transactions.changeset import ChangeOperation, ChangeSet
from pititino.workspace import Workspace


class BackupListArguments(BaseModel):
    file: str | None = None


class RestoreArguments(BaseModel):
    file: str
    backup: str = Field(min_length=1)


def list_backups(workspace: Workspace, arguments: BackupListArguments) -> dict[str, Any]:
    backup_dir = workspace.root / ".pititino" / "backups"
    if not backup_dir.is_dir():
        return {"backups": []}
    target_name = Path(arguments.file).name if arguments.file else None
    backups = []
    for path in sorted(backup_dir.iterdir(), key=lambda value: value.stat().st_mtime, reverse=True):
        if not path.is_file() or not path.name.endswith(".bak"):
            continue
        if target_name and not path.name.startswith(f"{target_name}."):
            continue
        info = path.stat()
        backups.append(
            {
                "backup": str(path.relative_to(workspace.root)),
                "name": path.name,
                "size": info.st_size,
                "modified": info.st_mtime,
            }
        )
    return {"backups": backups}


def propose_restore(arguments: RestoreArguments) -> ChangeSet:
    return ChangeSet(
        target=arguments.file,
        summary=f"Restore {arguments.file} from backup {Path(arguments.backup).name}",
        operations=[
            ChangeOperation(
                operation="restore_backup",
                description=f"Restore {arguments.file} from {Path(arguments.backup).name}",
                arguments=arguments.model_dump(),
            )
        ],
    )
