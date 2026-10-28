from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from prometheus_client import make_asgi_app
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False

from sv_api.routes import health, analyses, receipts, compat, review

app = FastAPI(
    title="SENTINEL-V Video Screening API",
    version="1.0.0",
    description="Calibrated, auditable video deepfake screening service on the S-MSDT detector family.",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics endpoint if available
if HAS_PROMETHEUS:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

# Include Routers
app.include_router(health.router, tags=["Health"])
app.include_router(analyses.router, prefix="/v1/analyses", tags=["Analyses"])
app.include_router(receipts.router, prefix="/v1/receipts", tags=["Receipts"])
app.include_router(review.router, prefix="/v1", tags=["Reviews"])
app.include_router(compat.router, prefix="/compat", tags=["SENTINEL Compatibility"])
