import asyncio
from dataclasses import dataclass
from typing import Protocol

from backend.core.errors import AppError

FULL_ACCESS_EMAILS = frozenset({"admin@gmail.com"})


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    uid: str
    email: str | None = None
    name: str | None = None

    @property
    def has_full_access(self) -> bool:
        return bool(self.email and self.email.strip().casefold() in FULL_ACCESS_EMAILS)


class TokenVerifier(Protocol):
    async def verify(self, token: str) -> AuthenticatedUser: ...


class DevelopmentTokenVerifier:
    async def verify(self, token: str) -> AuthenticatedUser:
        if token != "dev-token":
            raise AppError(401, "INVALID_TOKEN", "Use the local development token")
        return AuthenticatedUser(uid="local-user", email="local@promptopt.dev", name="Local User")


class FirebaseTokenVerifier:
    def __init__(self, project_id: str):
        self.project_id = project_id

    async def verify(self, token: str) -> AuthenticatedUser:
        try:
            claims = await asyncio.to_thread(self._verify_sync, token)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(401, "INVALID_TOKEN", "Firebase ID token is invalid or expired") from exc
        return AuthenticatedUser(
            uid=claims["uid"],
            email=claims.get("email"),
            name=claims.get("name"),
        )

    def _verify_sync(self, token: str) -> dict:
        import firebase_admin
        from firebase_admin import auth

        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(options={"projectId": self.project_id})
        return auth.verify_id_token(token, check_revoked=True)


class GoogleOidcTokenVerifier:
    def __init__(self, audience: str, service_account_email: str):
        self.audience = audience
        self.service_account_email = service_account_email

    async def verify(self, token: str) -> None:
        try:
            claims = await asyncio.to_thread(self._verify_sync, token)
        except Exception as exc:
            raise AppError(401, "INVALID_INTERNAL_TOKEN", "Internal task token is invalid") from exc
        if claims.get("email") != self.service_account_email or claims.get("email_verified") is not True:
            raise AppError(403, "INVALID_TASK_IDENTITY", "Internal task identity is not allowed")

    def _verify_sync(self, token: str) -> dict:
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token

        return id_token.verify_oauth2_token(token, Request(), audience=self.audience)
