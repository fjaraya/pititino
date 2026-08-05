from types import SimpleNamespace

import pytest

from pititino.config import ModelConfig
from pititino.models.chat_completions import ChatCompletionsClient


class FakeCompletions:
    def __init__(self):
        self.requests = []

    async def create(self, **request):
        self.requests.append(request)
        return SimpleNamespace(choices=[])


class FakeSDKClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=FakeCompletions())


@pytest.mark.anyio
async def test_json_fallback_omits_native_tools_parameter() -> None:
    sdk_client = FakeSDKClient()
    client = ChatCompletionsClient(ModelConfig(), sdk_client)

    await client.complete([], [])
    await client.complete([], [{"type": "function"}])

    assert "tools" not in sdk_client.chat.completions.requests[0]
    assert sdk_client.chat.completions.requests[1]["tools"] == [{"type": "function"}]
    assert sdk_client.chat.completions.requests[1]["tool_choice"] == "auto"
