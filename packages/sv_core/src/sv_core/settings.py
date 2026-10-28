import os
from typing import Literal
from pydantic import BaseModel, Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    HAS_PYDANTIC_SETTINGS = False
    BaseSettings = BaseModel  # type: ignore


class Settings(BaseSettings):  # type: ignore
    if HAS_PYDANTIC_SETTINGS:
        model_config = SettingsConfigDict(
            env_prefix="SV_",
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

    # Environment
    ENV: Literal["dev", "staging", "prod"] = "dev"
    DATABASE_URL: str = "postgresql+asyncpg://sv:sv@localhost:5432/sv"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage (S3 / MinIO)
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_BUCKET: str = "sentinel-v"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_REGION: str = "us-east-1"

    # Engine Configuration
    ENGINE_MODE: Literal["real", "mock"] = "mock"
    MODEL_BUNDLE: str = "bundle-2026-11-default"
    DEVICE: str = "cuda:0"
    MAX_UPLOAD_MB: int = 500
    MAX_DURATION_S: int = 600
    MAX_TRACKS: int = 4
    K_CLIPS: int = 8

    # Retention
    RETENTION_MEDIA_DAYS: int = 30
    RETENTION_EVIDENCE_DAYS: int = 180

    # Cryptography & Receipts
    RECEIPT_SIGNING_KEY_PATH: str = "/run/secrets/receipt_ed25519.pem"
    PUBLIC_SCORE_DECIMALS: int = 2
    WEBHOOK_SECRET: str = "sv_default_webhook_secret_key_32b"
    JWT_SECRET: str = "sv_default_jwt_secret_change_in_production"

    # Blockchain Anchoring
    ANCHOR_ENABLED: bool = False
    ANCHOR_RPC_URL: str = ""
    ANCHOR_CONTRACT: str = ""
    ANCHOR_KEY_PATH: str = ""
    ANCHOR_CHAIN_ID: int = 11155111
    ANCHOR_BATCH_SECONDS: int = 600

    # Sentinel Integration
    COMPAT_SENTINEL_ENABLED: bool = True
    COMPAT_SYNC_TIMEOUT_S: int = 50
    SENTINEL_WEBHOOK_URL: str = ""

    # Auxiliary Models
    GEN_IMAGE_ONNX: str = "models/aux/swinv2_ai_image/model.onnx"

    # Licensing Compliance
    LICENSE_ACK: Literal["research-only", "cleared", ""] = "research-only"


settings = Settings()
