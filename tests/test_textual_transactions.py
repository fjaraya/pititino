import json

import pytest
import yaml

from pititino.config import Settings
from pititino.errors import ToolExecutionError
from pititino.tools import build_registry
from pititino.transactions.executor import apply_changeset
from pititino.workspace import Workspace


def test_text_json_yaml_and_csv_mutations_are_proposals(tmp_path) -> None:
    (tmp_path / "notes.md").write_text("hello world", encoding="utf-8")
    (tmp_path / "settings.json").write_text('{"service": {"replicas": 1}}', encoding="utf-8")
    (tmp_path / "settings.yaml").write_text("debug: true\n", encoding="utf-8")
    (tmp_path / "sales.csv").write_text("month,amount\nJan,10\n", encoding="utf-8")
    registry = build_registry(Workspace(tmp_path), Settings())

    changes = [
        registry.invoke("text.replace", {"file": "notes.md", "old": "world", "new": "Pititino"}),
        registry.invoke("json.set", {"file": "settings.json", "path": "service.replicas", "value": 2}),
        registry.invoke("yaml.set", {"file": "settings.yaml", "path": "service.replicas", "value": 3}),
        registry.invoke("csv.write", {"file": "sales.csv", "rows": [["Feb", "20"]]}),
    ]

    assert all(change.requires_confirmation for change in changes)
    assert (tmp_path / "notes.md").read_text(encoding="utf-8") == "hello world"

    for change in changes:
        apply_changeset(change, Workspace(tmp_path), Settings())

    assert (tmp_path / "notes.md").read_text(encoding="utf-8") == "hello Pititino"
    assert json.loads((tmp_path / "settings.json").read_text())["service"]["replicas"] == 2
    assert yaml.safe_load((tmp_path / "settings.yaml").read_text())["service"]["replicas"] == 3
    assert (tmp_path / "sales.csv").read_text(encoding="utf-8").endswith("Feb,20\n")


def test_csv_write_rejects_rows_with_wrong_width(tmp_path) -> None:
    (tmp_path / "sales.csv").write_text("month,amount\nJan,10\n", encoding="utf-8")
    registry = build_registry(Workspace(tmp_path), Settings())
    change = registry.invoke("csv.write", {"file": "sales.csv", "rows": [["Feb"]]})

    with pytest.raises(ToolExecutionError, match="row width"):
        apply_changeset(change, Workspace(tmp_path), Settings())

    assert (tmp_path / "sales.csv").read_text(encoding="utf-8") == "month,amount\nJan,10\n"
