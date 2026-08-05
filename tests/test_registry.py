import pytest

from pititino.tools.registry import ToolRegistry


def test_registry_registers_and_resolves_tools() -> None:
    registry = ToolRegistry()
    registry.register("example.echo", lambda value: value)
    assert registry.get("example.echo")("hello") == "hello"
    assert registry.names() == ("example.echo",)


def test_registry_rejects_duplicate_names() -> None:
    registry = ToolRegistry()
    registry.register("example.echo", lambda value: value)
    with pytest.raises(ValueError):
        registry.register("example.echo", lambda value: value)
