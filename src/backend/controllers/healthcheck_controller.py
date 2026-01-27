from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel


healthcheck_router = APIRouter()


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: str
    version: str


@healthcheck_router.get("/healthcheck", response_model=HealthCheckResponse)
async def healthcheck():
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="0.1.0",
    )


@healthcheck_router.get("/health", response_model=HealthCheckResponse)
async def health():
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="0.1.0",
    )
