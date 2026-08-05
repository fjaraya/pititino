from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel
from pydantic_ai import RunContext
from pydantic_ai.tools import Tool
from pydantic_ai.toolsets import FunctionToolset

from pititino.tools.registry import ToolDefinition, ToolRegistry
from pititino.transactions.changeset import ChangeSet


@dataclass
class PydanticToolDependencies:
    """Dependencies shared by generated Pydantic AI tools."""

    registry: ToolRegistry
    pending_changes: list[ChangeSet] = field(default_factory=list)
    on_activity: Callable[[str], Awaitable[None] | None] | None = None


def build_pydantic_toolset(
    registry: ToolRegistry,
) -> FunctionToolset[PydanticToolDependencies]:
    """Expose every validated Pititino tool through a Pydantic AI toolset."""
    tools = [
        _build_tool(definition)
        for definition in registry.definitions()
    ]
    return FunctionToolset(tools)


def _build_tool(definition: ToolDefinition) -> Tool[PydanticToolDependencies]:
    async def invoke(
        ctx: RunContext[PydanticToolDependencies],
        arguments: BaseModel,
    ) -> Any:
        if ctx.deps.on_activity is not None:
            result = ctx.deps.on_activity(f"calling {definition.name}")
            if inspect.isawaitable(result):
                await result
        result = ctx.deps.registry.invoke(definition.name, arguments.model_dump())
        if definition.mutating:
            change = ChangeSet.model_validate(result)
            ctx.deps.pending_changes.append(change)
        if ctx.deps.on_activity is not None:
            result = ctx.deps.on_activity(f"completed {definition.name}")
            if inspect.isawaitable(result):
                await result
        return result.model_dump() if isinstance(result, BaseModel) else result

    invoke.__name__ = definition.name.replace(".", "_")
    invoke.__doc__ = definition.description
    invoke.__annotations__ = {
        "ctx": RunContext[PydanticToolDependencies],
        "arguments": definition.args_model,
        "return": Any,
    }
    return Tool(
        invoke,
        takes_ctx=True,
        name=definition.name,
        description=definition.description,
        sequential=True,
    )
