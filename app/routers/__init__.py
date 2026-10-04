"""
FastAPI routers for The Blind Spot endpoints.
"""

from app.routers.analyze import router as analyze_router
from app.routers.followup import router as followup_router
from app.routers.health import router as health_router
from app.routers.map import router as map_router

__all__ = [
    "analyze_router",
    "followup_router",
    "health_router",
    "map_router",
]
