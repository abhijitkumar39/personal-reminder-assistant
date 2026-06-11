from fastapi import APIRouter, Depends

from app.api.deps import get_settings
from app.core.config import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {"status": "ok", "version": settings.app_version}
