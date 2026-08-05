from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.errors import AppError
from src.core.security import AuthenticatedUser

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(401, "AUTHENTICATION_REQUIRED", "A Firebase ID token is required")
    return await request.app.state.services.token_verifier.verify(credentials.credentials)


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
