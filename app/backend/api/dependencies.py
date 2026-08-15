from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.errors import AppError
from backend.core.security import AuthenticatedUser

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(401, "AUTHENTICATION_REQUIRED", "A Firebase ID token is required")
    return await request.app.state.services.token_verifier.verify(credentials.credentials)


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


async def verify_internal_task(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(401, "INTERNAL_AUTH_REQUIRED", "An internal task token is required")
    verifier = request.app.state.services.internal_token_verifier
    if verifier is None:
        if (
            request.app.state.settings.app_env in {"development", "test"}
            and credentials.credentials == "dev-task-token"
        ):
            return
        raise AppError(401, "INTERNAL_AUTH_REQUIRED", "Internal task authentication is unavailable")
    await verifier.verify(credentials.credentials)


InternalTask = Annotated[None, Depends(verify_internal_task)]
