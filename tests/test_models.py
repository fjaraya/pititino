from pititino.config import ModelConfig
from pititino.models.chat_completions import create_chat_completions_model


def test_chat_completions_model_uses_configured_compatible_endpoint() -> None:
    model = create_chat_completions_model(
        ModelConfig(
            base_url="https://gateway.example/v1",
            model="Qwen/Qwen3-32B",
        )
    )

    assert model.model_name == "Qwen/Qwen3-32B"
    assert str(model.provider.base_url).rstrip("/") == "https://gateway.example/v1"
