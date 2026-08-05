import asyncio
from types import SimpleNamespace

import pytest

from pititino.agent.runtime import AgentRuntime
from pititino.config import Settings
from pititino.errors import AgentRuntimeError
from pititino.tools import build_registry
from pititino.workspace import Workspace


def tool_response(call_id: str = "call-1"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=None,
                    tool_calls=[
                        SimpleNamespace(
                            id=call_id,
                            function=SimpleNamespace(
                                name="filesystem.list", arguments='{"path":"."}'
                            ),
                        )
                    ],
                )
            )
        ]
    )


class RepeatingClient:
    async def complete(self, messages, tools):
        return tool_response()


class SlowClient:
    async def complete(self, messages, tools):
        await asyncio.sleep(0.05)
        return SimpleNamespace(choices=[])


class NativeFailJsonSlowClient:
    def __init__(self):
        self.calls = 0

    async def complete(self, messages, tools):
        self.calls += 1
        if self.calls == 1:
            from pititino.errors import ModelEndpointError

            raise ModelEndpointError("native tools unsupported")
        await asyncio.sleep(0.05)
        return SimpleNamespace(choices=[])


@pytest.mark.anyio
async def test_runtime_stops_after_max_tool_rounds(tmp_path) -> None:
    settings = Settings(agent={"max_tool_rounds": 2, "timeout_seconds": 1})
    runtime = AgentRuntime(settings, build_registry(Workspace(tmp_path), settings), RepeatingClient())

    with pytest.raises(AgentRuntimeError, match="max_tool_rounds"):
        await runtime.run("Keep inspecting")


@pytest.mark.anyio
async def test_runtime_enforces_request_timeout(tmp_path) -> None:
    settings = Settings(agent={"max_tool_rounds": 2, "timeout_seconds": 0.01})
    runtime = AgentRuntime(settings, build_registry(Workspace(tmp_path), settings), SlowClient())

    with pytest.raises(AgentRuntimeError, match="timeout"):
        await runtime.run("Inspect")


@pytest.mark.anyio
async def test_runtime_enforces_timeout_during_json_fallback(tmp_path) -> None:
    settings = Settings(agent={"max_tool_rounds": 2, "timeout_seconds": 0.01})
    runtime = AgentRuntime(
        settings,
        build_registry(Workspace(tmp_path), settings),
        NativeFailJsonSlowClient(),
    )

    with pytest.raises(AgentRuntimeError, match="timeout"):
        await runtime.run("Inspect")


@pytest.mark.anyio
async def test_runtime_clears_pending_changes_at_start_of_run(tmp_path) -> None:
    settings = Settings(agent={"max_tool_rounds": 2, "timeout_seconds": 1})

    class Client:
        def __init__(self):
            self.calls = 0

        async def complete(self, messages, tools):
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(
                                content=None,
                                tool_calls=[
                                    SimpleNamespace(
                                        id="write-1",
                                        function=SimpleNamespace(
                                            name="text.append",
                                            arguments='{"file":"notes.md","content":"x"}',
                                        ),
                                    )
                                ],
                            )
                        )
                    ]
                )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="done", tool_calls=[]))]
            )

    (tmp_path / "notes.md").write_text("notes", encoding="utf-8")
    client = Client()
    runtime = AgentRuntime(settings, build_registry(Workspace(tmp_path), settings), client)

    await runtime.run("Append")
    assert len(runtime.pending_changes) == 1
    await runtime.run("Finish")
    assert runtime.pending_changes == []
