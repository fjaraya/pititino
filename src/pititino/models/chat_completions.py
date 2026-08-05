from __future__ import annotations

import inspect
import json
from typing import Any

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from pititino.config import ModelConfig
from pititino.errors import ModelEndpointError
from pititino.models.base import ModelResponse, ToolCall, ToolCallingMode


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

    async def next_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        mode: ToolCallingMode,
        on_text_delta: Any | None = None,
    ) -> ModelResponse:
        """Return one normalized native or JSON-mode model response."""
        if mode == "json":
            return await self.complete_json(messages)
        if on_text_delta is None:
            response = await self.complete(messages, tools)
            message = response.choices[0].message
            return ModelResponse(
                content=message.content or "",
                tool_calls=[
                    ToolCall(call.id, call.function.name, call.function.arguments)
                    for call in (message.tool_calls or [])
                ],
            )

        stream = await self.stream(messages, tools)
        text_parts: list[str] = []
        calls: dict[int, dict[str, str]] = {}
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                text_parts.append(delta.content)
                result = on_text_delta(delta.content)
                if inspect.isawaitable(result):
                    await result
            for tool_delta in delta.tool_calls or []:
                index = tool_delta.index
                call = calls.setdefault(index, {"id": "", "name": "", "arguments": ""})
                if tool_delta.id:
                    call["id"] = tool_delta.id
                if tool_delta.function:
                    if tool_delta.function.name:
                        call["name"] += tool_delta.function.name
                    if tool_delta.function.arguments:
                        call["arguments"] += tool_delta.function.arguments
        return ModelResponse(
            content="".join(text_parts),
            tool_calls=[ToolCall(call["id"], call["name"], call["arguments"]) for call in calls.values()],
        )

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

    async def complete_json(self, messages: list[dict[str, Any]]) -> ModelResponse:
        """Request and parse one structured JSON action response."""
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_output_tokens,
            )
            message = response.choices[0].message
            return self.parse_json_action(message.content or "")
        except Exception as exc:
            raise ModelEndpointError(f"JSON Chat Completions request failed: {exc}") from exc

    @staticmethod
    def parse_json_action(content: str) -> ModelResponse:
        candidate = content.strip()
        if candidate.startswith("```") and candidate.endswith("```"):
            lines = candidate.splitlines()
            candidate = "\n".join(lines[1:-1]).strip()
        try:
            action = json.loads(candidate)
        except json.JSONDecodeError:
            return ModelResponse(content=content, tool_calls=[])
        if not isinstance(action, dict) or not isinstance(action.get("action"), str):
            return ModelResponse(content=content, tool_calls=[])
        return ModelResponse(
            content="",
            tool_calls=[
                ToolCall(
                    id="json-call-1",
                    name=action["action"],
                    arguments=json.dumps(action.get("arguments", {}), ensure_ascii=True),
                )
            ],
        )

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
