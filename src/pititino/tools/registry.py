from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

from pititino.errors import ToolValidationError


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    args_model: type[BaseModel]
    mutating: bool
    handler: Callable[[BaseModel], Any]

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Allow simple legacy callers to invoke a definition directly."""
        return self.handler(*args, **kwargs)

@dataclass
class ToolRegistry:
    """Simple controlled registry for operations exposed to the agent."""

    _tools: dict[str, ToolDefinition] = field(default_factory=dict)

    def register(
        self,
        definition: ToolDefinition | str,
        func: Callable[..., Any] | None = None,
    ) -> None:
        if isinstance(definition, str):
            if func is None:
                raise TypeError("Legacy registration requires a callable")
            self.register_legacy(definition, func)
            return
        name = definition.name
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        self._tools[name] = definition

    def register_legacy(self, name: str, func: Callable[..., Any]) -> None:
        """Register a callable for older integrations; new tools use ToolDefinition."""
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        self._tools[name] = ToolDefinition(
            name=name,
            description=name,
            args_model=_AnyArguments,
            mutating=False,
            handler=func,
        )

    def get(self, name: str) -> ToolDefinition:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def invoke(self, name: str, arguments: dict[str, Any]) -> Any:
        try:
            definition = self.get(name)
        except KeyError as exc:
            raise ToolValidationError(str(exc)) from exc
        try:
            validated = definition.args_model.model_validate(arguments)
        except ValidationError as exc:
            raise ToolValidationError(f"Invalid arguments for {name}: {exc}") from exc
        return definition.handler(validated)

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._tools[name] for name in sorted(self._tools))

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))


class _AnyArguments(BaseModel):
    """Compatibility schema for legacy callables; typed tools must not use this."""

    model_config = {"extra": "allow"}
