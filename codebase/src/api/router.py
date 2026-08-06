from fastapi import APIRouter

from src.modules.analysis.router import router as analysis_router
from src.modules.projects.router import router as projects_router
from src.modules.uploads.router import router as uploads_router

api_router = APIRouter()
api_router.include_router(uploads_router)
api_router.include_router(projects_router)
api_router.include_router(analysis_router)
