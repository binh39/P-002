from fastapi import APIRouter

from backend.modules.analysis.router import router as analysis_router
from backend.modules.dashboard.router import router as dashboard_router
from backend.modules.experiments.router import (
    prompt_registry_router,
    prompt_router,
    review_router,
    test_generation_router,
)
from backend.modules.experiments.router import router as experiments_router
from backend.modules.identity.router import router as identity_router
from backend.modules.projects.router import router as projects_router
from backend.modules.providers.router import router as provider_credentials_router
from backend.modules.uploads.router import router as uploads_router

api_router = APIRouter()
api_router.include_router(identity_router)
api_router.include_router(uploads_router)
api_router.include_router(projects_router)
api_router.include_router(analysis_router)
api_router.include_router(dashboard_router)
api_router.include_router(experiments_router)
api_router.include_router(review_router)
api_router.include_router(prompt_router)
api_router.include_router(prompt_registry_router)
api_router.include_router(test_generation_router)
api_router.include_router(provider_credentials_router)
