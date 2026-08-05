from pathlib import Path

from pititino.config import Settings
from pititino.transactions.changeset import ChangeOperation, ChangeSet
from pititino.tui.app import PititinoApp


def test_tui_groups_pending_operations_by_target(tmp_path) -> None:
    app = PititinoApp(Path(tmp_path), Settings())
    app.runtime.pending_changes = [
        ChangeSet(
            target="notes.md",
            summary="Replace heading",
            operations=[
                ChangeOperation(
                    operation="text_replace",
                    description="Replace heading",
                    arguments={"file": "notes.md", "old": "A", "new": "B", "count": 1},
                )
            ],
        ),
        ChangeSet(
            target="notes.md",
            summary="Append note",
            operations=[
                ChangeOperation(
                    operation="text_append",
                    description="Append note",
                    arguments={"file": "notes.md", "content": "\nDone"},
                )
            ],
        ),
    ]

    grouped = app._group_pending_changes()

    assert len(grouped) == 1
    assert grouped[0].target == "notes.md"
    assert [operation.operation for operation in grouped[0].operations] == [
        "text_replace",
        "text_append",
    ]


def test_tui_status_exposes_execution_context(tmp_path) -> None:
    app = PititinoApp(Path(tmp_path), Settings())
    app.selected_file = "notes.md"

    status = app._status_text("working")

    assert "notes.md" in status
    assert "model: default" in status
    assert "tools: auto" in status
    assert "state: working" in status


def test_tui_plan_includes_targets_and_operation_details(tmp_path) -> None:
    app = PititinoApp(Path(tmp_path), Settings())
    app.runtime.pending_changes = [
        ChangeSet(
            target="notes.md",
            summary="Replace heading",
            operations=[
                ChangeOperation(
                    operation="text_replace",
                    description="Replace 'old' with 'new'",
                    arguments={},
                )
            ],
        )
    ]

    plan = app._pending_plan_text()

    assert "notes.md" in plan
    assert "+ Replace 'old' with 'new'" in plan
