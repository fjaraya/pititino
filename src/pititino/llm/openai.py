from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from pititino.config import ModelConfig
from pititino.errors import ModelEndpointError


def create_client(config: ModelConfig) -> AsyncOpenAI:
    """Create an OpenAI-compatible async client from Pititino configuration."""
    return AsyncOpenAI(base_url=config.base_url, api_key=config.api_key())


class OpenAIChatClient:
    """Small provider boundary used by the agent runtime."""

    def __init__(self, config: ModelConfig, client: AsyncOpenAI | None = None) -> None:
        self.config = config
        self.client = client or create_client(config)

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
        try:
            request: dict[str, Any] = {
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_output_tokens,
            }
            if tools:
                request["tools"] = tools
            return await self.client.chat.completions.create(**request)
        except Exception as exc:
            raise ModelEndpointError(f"Model request failed: {exc}") from exc

    async def stream(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
        """Start a streamed completion while keeping provider details in this layer."""
        try:
            request: dict[str, Any] = {
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_output_tokens,
                "stream": True,
            }
            if tools:
                request["tools"] = tools
            return await self.client.chat.completions.create(**request)
        except Exception as exc:
            raise ModelEndpointError(f"Model streaming request failed: {exc}") from exc
