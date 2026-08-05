import json

import pytest

from pititino.config import Settings
from pititino.errors import ToolExecutionError
from pititino.tools import build_registry
from pititino.transactions.executor import apply_changeset
from pititino.workspace import Workspace


def test_revisioned_proposal_rejects_external_file_change(tmp_path) -> None:
    path = tmp_path / "notes.md"
    path.write_text("original", encoding="utf-8")
    workspace = Workspace(tmp_path)
    registry = build_registry(workspace, Settings())
    change = registry.invoke(
        "text.replace", {"file": "notes.md", "old": "original", "new": "proposal"}
    )

    path.write_text("user edit", encoding="utf-8")

    with pytest.raises(ToolExecutionError, match="changed since"):
        apply_changeset(change, workspace, Settings())
    assert path.read_text(encoding="utf-8") == "user edit"
    audit = (tmp_path / ".pititino" / "history" / "operations.jsonl").read_text()
    assert json.loads(audit.splitlines()[-1])["status"] == "conflict"


def test_revisioned_proposal_applies_when_source_is_unchanged(tmp_path) -> None:
    path = tmp_path / "notes.md"
    path.write_text("original", encoding="utf-8")
    workspace = Workspace(tmp_path)
    registry = build_registry(workspace, Settings())
    change = registry.invoke(
        "text.replace", {"file": "notes.md", "old": "original", "new": "updated"}
    )

    apply_changeset(change, workspace, Settings())

    assert path.read_text(encoding="utf-8") == "updated"
