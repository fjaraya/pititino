from pathlib import Path

import pytest
from pydantic_ai.models.test import TestModel

from pititino.agent.pydantic_backend import PydanticAgentBackend
from pititino.config import Settings
from pititino.tools import build_registry
from pititino.workspace import Workspace


@pytest.mark.anyio
async def test_pydantic_backend_runs_native_tool_and_keeps_history(tmp_path: Path) -> None:
    settings = Settings(model={"tool_calling": "native"})
    registry = build_registry(Workspace(tmp_path), settings)
    backend = PydanticAgentBackend(
        settings,
        registry,
        model=TestModel(call_tools=["filesystem.list"], custom_output_text="Finished"),
    )

    result = await backend.run("List the workspace")

    assert result == "Finished"
    assert backend.message_history
