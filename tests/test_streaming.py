from types import SimpleNamespace

import pytest

from pititino.agent.runtime import AgentRuntime
from pititino.config import Settings
from pititino.tools import build_registry
from pititino.workspace import Workspace


class StreamingClient:
    async def stream(self, messages, tools):
        async def chunks():
            for text in ("Revenue ", "contains ", "monthly data."):
                yield SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content=text, tool_calls=[]))]
                )

        return chunks()


@pytest.mark.anyio
async def test_agent_emits_streamed_text_deltas() -> None:
    deltas = []
    settings = Settings()
    runtime = AgentRuntime(settings, build_registry(Workspace("."), settings), StreamingClient())

    result = await runtime.run("Explain the workbook", on_text_delta=deltas.append)

    assert result == "Revenue contains monthly data."
    assert deltas == ["Revenue ", "contains ", "monthly data."]
