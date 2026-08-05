import asyncio
from dataclasses import dataclass
from typing import Protocol

from src.core.errors import AppError


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    uid: str
    email: str | None = None
    name: str | None = None


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
