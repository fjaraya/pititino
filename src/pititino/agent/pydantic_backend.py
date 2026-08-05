from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic_ai import Agent

from pititino.agent.pydantic_tools import PydanticToolDependencies, build_pydantic_toolset
from pititino.config import Settings
from pititino.errors import ModelEndpointError
from pititino.models.chat_completions import create_chat_completions_model
from pititino.tools.registry import ToolRegistry
from pititino.transactions.changeset import ChangeSet

ToolActivity = Callable[[str], Awaitable[None] | None]


class PydanticAgentBackend:
    """Native tool-calling agent powered by Pydantic AI."""

    def __init__(
        self,
        settings: Settings,
        registry: ToolRegistry,
        on_tool_activity: ToolActivity | None = None,
        *,
        model: Any | None = None,
    ) -> None:
        self.settings = settings
        self.registry = registry
        self.on_tool_activity = on_tool_activity
        self.message_history: list[Any] = []
        self.pending_changes: list[ChangeSet] = []
        self.agent = Agent(
            model or create_chat_completions_model(settings.model),
            deps_type=PydanticToolDependencies,
            system_prompt=(
                "You are Pititino, a safe local file workbench. Use the provided typed tools "
                "to inspect files instead of inventing contents. Inspect before modifying. "
                "Only claim a tool operation succeeded when its result says it did. "
                "Keep responses concise and grounded in returned data."
            ),
            toolsets=[build_pydantic_toolset(registry)],
        )

    async def run(
        self,
        user_message: str,
        *,
        selected_file: str | None = None,
        on_text_delta: Callable[[str], Awaitable[None] | None] | None = None,
    ) -> str:
        deps = PydanticToolDependencies(
            registry=self.registry,
            pending_changes=[],
            on_activity=self.on_tool_activity,
        )
        instructions = (
            f"The user currently selected this workspace file: {selected_file}"
            if selected_file
            else None
        )
        try:
            if on_text_delta is None:
                result = await self.agent.run(
                    user_message,
                    deps=deps,
                    instructions=instructions,
                    message_history=self.message_history,
                )
            else:
                async with self.agent.run_stream(
                    user_message,
                    deps=deps,
                    instructions=instructions,
                    message_history=self.message_history,
                ) as streamed:
                    async for text in streamed.stream_text(delta=True):
                        callback_result = on_text_delta(text)
                        if hasattr(callback_result, "__await__"):
                            await callback_result
                    result = streamed
        except Exception as exc:
            raise ModelEndpointError(f"Pydantic AI agent request failed: {exc}") from exc
        self.message_history = list(result.all_messages())
        self.pending_changes = deps.pending_changes
        return str(result.output)

    def reset_conversation(self) -> None:
        self.message_history.clear()
