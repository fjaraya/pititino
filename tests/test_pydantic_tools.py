from pathlib import Path

from pititino.agent.pydantic_tools import build_pydantic_toolset
from pititino.config import Settings
from pititino.tools import build_registry
from pititino.workspace import Workspace


def test_pydantic_toolset_mirrors_registry_schemas(tmp_path: Path) -> None:
    settings = Settings()
    registry = build_registry(Workspace(tmp_path), settings)
    toolset = build_pydantic_toolset(registry)

    assert set(toolset.tools) == set(registry.names())
    schema = toolset.tools["excel.create_sheet"].function_schema.json_schema
    assert schema["properties"]["file"]["type"] == "string"
    assert schema["required"] == ["file", "sheet"]
