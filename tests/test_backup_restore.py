from pititino.config import Settings
from pititino.tools import build_registry
from pititino.transactions.executor import apply_changeset
from pititino.workspace import Workspace


def test_backup_list_and_restore_round_trip(tmp_path) -> None:
    path = tmp_path / "notes.md"
    path.write_text("before", encoding="utf-8")
    workspace = Workspace(tmp_path)
    settings = Settings()
    registry = build_registry(workspace, settings)

    change = registry.invoke(
        "text.replace", {"file": "notes.md", "old": "before", "new": "after"}
    )
    apply_changeset(change, workspace, settings)
    backups = registry.invoke("backup.list", {"file": "notes.md"})["backups"]
    assert len(backups) == 1

    path.write_text("later edit", encoding="utf-8")
    restore = registry.invoke(
        "backup.restore",
        {"file": "notes.md", "backup": backups[0]["backup"]},
    )
    apply_changeset(restore, workspace, settings)

    assert path.read_text(encoding="utf-8") == "before"
