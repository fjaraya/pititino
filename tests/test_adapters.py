import json

import pytest

from pititino.config import Settings
from pititino.errors import ToolExecutionError
from pititino.tools import build_registry
from pititino.workspace import Workspace


def test_read_only_adapters_return_bounded_model_friendly_data(tmp_path) -> None:
    (tmp_path / "sales.csv").write_text("month,amount\nJan,10\nFeb,20\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("# Notes\nhello", encoding="utf-8")
    (tmp_path / "settings.json").write_text(json.dumps({"debug": False}), encoding="utf-8")
    (tmp_path / "settings.yaml").write_text("debug: false\nreplicas: 2\n", encoding="utf-8")
    registry = build_registry(Workspace(tmp_path), Settings())

    csv_result = registry.invoke("csv.inspect", {"file": "sales.csv", "max_rows": 10})
    assert csv_result["headers"] == ["month", "amount"]
    assert csv_result["sample_rows"] == [["Jan", "10"], ["Feb", "20"]]
    assert registry.invoke("text.read", {"path": "notes.md"})["content"].startswith("# Notes")
    assert registry.invoke("json.read", {"file": "settings.json"})["value"]["debug"] is False
    assert registry.invoke("yaml.read", {"file": "settings.yaml"})["value"]["replicas"] == 2


def test_structured_adapters_bound_input_size(tmp_path) -> None:
    (tmp_path / "settings.json").write_text('{"large": true}', encoding="utf-8")
    registry = build_registry(Workspace(tmp_path), Settings())

    with pytest.raises(ToolExecutionError, match="max_chars"):
        registry.invoke("json.read", {"file": "settings.json", "max_chars": 2})
