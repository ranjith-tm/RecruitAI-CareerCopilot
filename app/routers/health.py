from fastapi import APIRouter
from app.schemas.models import HealthResponse
from app.config.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    settings = get_settings()
    return HealthResponse(version=settings.app_version)
