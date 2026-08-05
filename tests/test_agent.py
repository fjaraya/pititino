from types import SimpleNamespace

import pytest

from pititino.agent.runtime import AgentRuntime
from pititino.config import Settings
from pititino.tools import build_registry
from pititino.workspace import Workspace


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    async def complete(self, messages, tools):
        self.calls.append((messages, tools))
        return next(self.responses)


def response(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.mark.anyio
async def test_agent_executes_read_only_tool_and_continues() -> None:
    first = response(
        SimpleNamespace(
            content=None,
            tool_calls=[
                SimpleNamespace(
                    id="call-1",
                    function=SimpleNamespace(
                        name="filesystem.list", arguments='{"path": "."}'
                    ),
                )
            ],
        )
    )
    second = response(SimpleNamespace(content="The workspace contains the requested entries.", tool_calls=[]))
    fake = FakeClient([first, second])
    activities = []
    settings = Settings()
    runtime = AgentRuntime(
        settings,
        build_registry(Workspace("."), settings),
        fake,
        on_tool_activity=activities.append,
    )

    result = await runtime.run("List the workspace")

    assert result == "The workspace contains the requested entries."
    assert len(fake.calls) == 2
    assert any(tool["function"]["name"] == "filesystem.list" for tool in fake.calls[0][1])
    assert activities == ["calling filesystem.list", "completed filesystem.list"]
    assert fake.calls[1][0][-1]["role"] == "tool"
