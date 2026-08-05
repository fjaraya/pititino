from __future__ import annotations

from typing import Any

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from pititino.config import ModelConfig
from pititino.errors import ModelEndpointError


def create_chat_completions_client(config: ModelConfig) -> Any:
    """Create the underlying compatible async client through Pydantic AI."""
    return create_chat_completions_model(config).provider.client


def create_chat_completions_model(config: ModelConfig) -> OpenAIChatModel:
    """Create a Pydantic AI Chat Completions model for any compatible gateway."""
    if config.api != "chat_completions":
        raise ValueError(f"Unsupported model API: {config.api}")
    return OpenAIChatModel(
        config.model,
        provider=OpenAIProvider(
            base_url=config.base_url,
            api_key=config.api_key(),
        ),
    )


class ChatCompletionsClient:
    """Low-level Chat Completions transport for any compatible gateway."""

    def __init__(self, config: ModelConfig, client: Any | None = None) -> None:
        self.config = config
        self.client = client or create_chat_completions_client(config)

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
                request["tool_choice"] = "auto"
            return await self.client.chat.completions.create(**request)
        except Exception as exc:
            raise ModelEndpointError(f"Chat Completions request failed: {exc}") from exc

    async def stream(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
        """Start a streamed Chat Completions request."""
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
                request["tool_choice"] = "auto"
            return await self.client.chat.completions.create(**request)
        except Exception as exc:
            raise ModelEndpointError(f"Chat Completions streaming request failed: {exc}") from exc
