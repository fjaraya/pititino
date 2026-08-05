from openai import AsyncOpenAI

from pititino.config import ModelConfig


def create_client(config: ModelConfig) -> AsyncOpenAI:
    """Create an OpenAI-compatible async client from Pititino configuration."""
    return AsyncOpenAI(base_url=config.base_url, api_key=config.api_key())
