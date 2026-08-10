from fastapi import APIRouter

from backend.modules.analysis.router import router as analysis_router
from backend.modules.experiments.router import prompt_router
from backend.modules.experiments.router import router as experiments_router
from backend.modules.projects.router import router as projects_router
from backend.modules.uploads.router import router as uploads_router

api_router = APIRouter()
api_router.include_router(uploads_router)
api_router.include_router(projects_router)
api_router.include_router(analysis_router)
api_router.include_router(experiments_router)
api_router.include_router(prompt_router)
