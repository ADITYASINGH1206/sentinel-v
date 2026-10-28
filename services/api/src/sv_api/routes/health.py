from fastapi import APIRouter
from sv_core.settings import settings

router = APIRouter()


@router.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "service": "sentinel-v-api",
        "env": settings.ENV,
        "engine_mode": settings.ENGINE_MODE,
    }


@router.get("/readyz")
async def readyz():
    return {
        "status": "ready",
        "bundle": settings.MODEL_BUNDLE,
    }
