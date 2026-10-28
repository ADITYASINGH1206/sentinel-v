from sv_core.settings import Settings


def test_default_settings():
    s = Settings()
    assert s.ENV in ["dev", "staging", "prod"]
    assert s.MAX_TRACKS == 4
    assert s.K_CLIPS == 8
    assert s.ENGINE_MODE in ["real", "mock"]
    assert s.RETENTION_MEDIA_DAYS == 30

