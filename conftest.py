import os

os.environ.setdefault("SV_TESTING", "1")
os.environ.setdefault("SV_ENGINE_MODE", "mock")
os.environ.setdefault("SV_DATABASE_URL", "sqlite+aiosqlite:///./test_dev.db")
