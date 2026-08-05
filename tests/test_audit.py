import json

from pititino.config import Settings
from pititino.tools import build_registry
from pititino.transactions.executor import apply_changeset
from pititino.workspace import Workspace


def test_transaction_audit_records_metadata_without_arguments(tmp_path) -> None:
    path = tmp_path / "notes.md"
    path.write_text("old", encoding="utf-8")
    workspace = Workspace(tmp_path)
    change = build_registry(workspace, Settings()).invoke(
        "text.replace",
        {"file": "notes.md", "old": "old", "new": "new"},
    )

    apply_changeset(change, workspace, Settings())

    audit_path = tmp_path / ".pititino" / "history" / "operations.jsonl"
    entry = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
    assert entry["status"] == "applied"
    assert entry["target"] == "notes.md"
    assert entry["operations"] == ["text_replace"]
    assert "old" not in entry
    assert "new" not in entry
