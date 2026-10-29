import pytest
from sv_core.settings import Settings


def test_default_settings():
    s = Settings()
    assert s.ENV in ["dev", "staging", "prod"]
    assert s.MAX_TRACKS == 4
    assert s.K_CLIPS == 8
    assert s.ENGINE_MODE in ["real", "mock"]
    assert s.RETENTION_MEDIA_DAYS == 30
    assert len(s.JWT_SECRET) > 0


def test_prod_settings_without_jwt_secret_fails():
    with pytest.raises(ValueError, match="SV_JWT_SECRET must be explicitly set"):
        Settings(ENV="prod", JWT_SECRET="", WEBHOOK_SECRET="secure_webhook_key_32b_custom")


def test_prod_settings_with_default_jwt_secret_fails():
    with pytest.raises(ValueError, match="SV_JWT_SECRET must be explicitly set"):
        Settings(ENV="prod", JWT_SECRET="sv_default_jwt_secret", WEBHOOK_SECRET="secure_webhook_key_32b_custom")


def test_prod_settings_with_valid_secrets_succeeds():
    s = Settings(
        ENV="prod",
        JWT_SECRET="super_secure_random_key_production_123",
        WEBHOOK_SECRET="secure_webhook_key_32b_custom"
    )
    assert s.ENV == "prod"
    assert s.JWT_SECRET == "super_secure_random_key_production_123"
