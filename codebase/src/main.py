import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.router import api_router
from src.config import Settings, get_settings
from src.core.errors import AppError
from src.core.logging import configure_logging
from src.modules.analysis.router import internal_router
from src.modules.experiments.router import internal_router as experiments_internal_router
from src.services.container import build_services

logger = logging.getLogger("promptopt.api")


def error_response(request: Request, status_code: int, code: str, message: str, details=None):
    error = {
        "code": code,
        "message": message,
        "request_id": getattr(request.state, "request_id", "unknown"),
    }
    if details is not None:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error})


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        logger.info("application_started", extra={"app_env": settings.app_env})
        yield
        logger.info("application_stopped")

    application = FastAPI(
        title="PromptOpt API",
        description="Project and experiment API for PromptOpt",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.services = build_services(settings)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return response

    @application.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return error_response(request, exc.status_code, exc.code, exc.message)

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        details = [
            {"location": list(error["loc"]), "message": error["msg"], "type": error["type"]} for error in exc.errors()
        ]
        return error_response(request, 422, "VALIDATION_ERROR", "Request validation failed", details)

    @application.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException):
        return error_response(request, exc.status_code, "HTTP_ERROR", str(exc.detail))

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.exception("unhandled_exception", extra={"request_id": request.state.request_id})
        return error_response(request, 500, "INTERNAL_ERROR", "An unexpected error occurred")

    application.include_router(api_router, prefix=settings.api_prefix)
    application.include_router(internal_router)
    application.include_router(experiments_internal_router)

    async def health():
        return {"status": "ok", "service": "promptopt-api", "env": settings.app_env}

    application.add_api_route("/health", health, methods=["GET"], tags=["health"])
    application.add_api_route(
        f"{settings.api_prefix}/health",
        health,
        methods=["GET"],
        tags=["health"],
    )
    return application


app = create_app()
