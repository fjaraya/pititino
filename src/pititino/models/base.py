from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class ModelResponse:
    content: str
    tool_calls: list[ToolCall]


ToolCallingMode = Literal["native", "json"]


class ModelBackend(Protocol):
    """Transport contract used by the provider-neutral agent runtime."""

    async def next_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        mode: ToolCallingMode,
        on_text_delta: Callable[[str], Awaitable[None] | None] | None = None,
    ) -> ModelResponse:
        """Request and normalize one model response."""
