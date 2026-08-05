from types import SimpleNamespace

import pytest

from pititino.agent.runtime import AgentRuntime
from pititino.config import Settings
from pititino.errors import ModelEndpointError
from pititino.tools import build_registry
from pititino.workspace import Workspace


def response(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=[]))]
    )


class JsonClient:
    def __init__(self):
        self.calls = []

    async def complete(self, messages, tools):
        self.calls.append((messages, tools))
        if len(self.calls) == 1:
            return response('{"action":"filesystem.list","arguments":{"path":"."}}')
        return response("The workspace was inspected.")


class AutoFallbackClient(JsonClient):
    async def complete(self, messages, tools):
        self.calls.append((messages, tools))
        if len(self.calls) == 1:
            raise ModelEndpointError("tools are unsupported")
        if len(self.calls) == 2:
            return response('{"action":"filesystem.list","arguments":{"path":"."}}')
        return response("Fallback inspection completed.")


class SilentNativeClient(JsonClient):
    async def complete(self, messages, tools):
        self.calls.append((messages, tools))
        if len(self.calls) == 1:
            return response("I will inspect the workspace.")
        if len(self.calls) == 2:
            return response('{"action":"filesystem.list","arguments":{"path":"."}}')
        return response("Inspection completed after fallback.")


@pytest.mark.anyio
async def test_json_mode_executes_validated_actions_without_native_tools(tmp_path) -> None:
    client = JsonClient()
    settings = Settings(model={"tool_calling": "json"})
    runtime = AgentRuntime(settings, build_registry(Workspace(tmp_path), settings), client)

    result = await runtime.run("List the workspace")

    assert result == "The workspace was inspected."
    assert all(tools == [] for _, tools in client.calls)


@pytest.mark.anyio
async def test_auto_mode_falls_back_to_json_actions(tmp_path) -> None:
    client = AutoFallbackClient()
    settings = Settings(model={"tool_calling": "auto"})
    runtime = AgentRuntime(settings, build_registry(Workspace(tmp_path), settings), client)

    result = await runtime.run("List the workspace")

    assert result == "Fallback inspection completed."
    assert client.calls[0][1]
    assert client.calls[1][1] == []


@pytest.mark.anyio
async def test_auto_mode_falls_back_when_native_response_has_no_tool_call(tmp_path) -> None:
    client = SilentNativeClient()
    settings = Settings(model={"tool_calling": "auto"})
    activities = []
    runtime = AgentRuntime(
        settings,
        build_registry(Workspace(tmp_path), settings),
        client,
        on_tool_activity=activities.append,
    )

    result = await runtime.run("List the workspace")

    assert result == "Inspection completed after fallback."
    assert client.calls[0][1]
    assert client.calls[1][1] == []
    assert any("native response contained no tool call" in activity for activity in activities)
