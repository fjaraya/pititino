"""Compatibility imports for the former OpenAI-named client module."""

from pititino.models.chat_completions import ChatCompletionsClient

OpenAIChatClient = ChatCompletionsClient

__all__ = ["OpenAIChatClient"]
