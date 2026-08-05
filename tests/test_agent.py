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


@pytest.mark.anyio
async def test_agent_retains_context_for_follow_up_prompt(tmp_path) -> None:
    fake = FakeClient(
        [
            response(SimpleNamespace(content="Brief: monthly revenue grew.", tool_calls=[])),
            response(SimpleNamespace(content="I will add that brief to the document.", tool_calls=[])),
        ]
    )
    settings = Settings(model={"tool_calling": "json"})
    runtime = AgentRuntime(settings, build_registry(Workspace(tmp_path), settings), fake)

    await runtime.run("Give me a brief of the document")
    result = await runtime.run("Put that brief in the document")

    assert result == "I will add that brief to the document."
    second_messages = fake.calls[1][0]
    assert {"role": "assistant", "content": "Brief: monthly revenue grew."} in second_messages
    assert second_messages[-1] == {"role": "user", "content": "Put that brief in the document"}


@pytest.mark.anyio
async def test_agent_limits_retained_context(tmp_path) -> None:
    fake = FakeClient(
        [
            response(SimpleNamespace(content="first", tool_calls=[])),
            response(SimpleNamespace(content="second", tool_calls=[])),
            response(SimpleNamespace(content="third", tool_calls=[])),
        ]
    )
    settings = Settings(model={"tool_calling": "json"}, agent={"max_history_turns": 1})
    runtime = AgentRuntime(settings, build_registry(Workspace(tmp_path), settings), fake)

    await runtime.run("first prompt")
    await runtime.run("second prompt")
    await runtime.run("third prompt")

    assert runtime.conversation_history == [
        {"role": "user", "content": "third prompt"},
        {"role": "assistant", "content": "third"},
    ]
