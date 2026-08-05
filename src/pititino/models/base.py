from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol


class ModelBackend(Protocol):
    """Transport contract used by the provider-neutral agent runtime."""

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
        """Request one non-streaming Chat Completions response."""

    async def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[Any]:
        """Request a streaming Chat Completions response."""
