from pititino.config import Settings


def test_default_settings_disable_shell() -> None:
    settings = Settings()
    assert settings.security.allow_shell is False
    assert settings.security.confirm_writes is True
