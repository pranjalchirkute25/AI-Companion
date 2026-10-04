"""
Health check and system status router.
"""

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.response_schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["System"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Returns application health, version, model, and configuration status."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        model=settings.GEMINI_MODEL,
        gemini_configured=bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip()),
    )
