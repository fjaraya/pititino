from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pititino.transactions.changeset import ChangeSet
from pititino.workspace import Workspace


def record_transaction(
    workspace: Workspace,
    changeset: ChangeSet,
    status: str,
    *,
    backup_path: Path | None = None,
    error: str | None = None,
) -> None:
    """Append metadata about a write without recording file contents or arguments."""
    entry: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "status": status,
        "target": changeset.target,
        "operations": [operation.operation for operation in changeset.operations],
    }
    if backup_path is not None:
        entry["backup"] = str(backup_path)
    if error is not None:
        entry["error"] = error

    try:
        history_dir = workspace.root / ".pititino" / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        with (history_dir / "operations.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
    except OSError:
        # Audit persistence must not turn an already-applied write into a failure.
        return
