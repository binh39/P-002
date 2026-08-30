import asyncio
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from backend.core.errors import AppError

FULL_ACCESS_EMAILS = frozenset({"admin@gmail.com", "admintest@gmail.com"})


class UserRole(StrEnum):
    PROMPT_ENGINEER = "prompt_engineer"
    PROMPT_REVIEWER = "prompt_reviewer"


ROLE_PERMISSIONS = {
    UserRole.PROMPT_ENGINEER: (
        "projects:write",
        "experiments:write",
        "test_suites:write",
    ),
    UserRole.PROMPT_REVIEWER: (
        "reviews:read",
        "reviews:decide",
        "test_suites:read",
    ),
}


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    uid: str
    email: str | None = None
    name: str | None = None
    role: UserRole = UserRole.PROMPT_ENGINEER
    workspace_id: str | None = None

    def __post_init__(self):
        if self.workspace_id is None:
            object.__setattr__(self, "workspace_id", self.uid)

    @property
    def permissions(self) -> tuple[str, ...]:
        return ROLE_PERMISSIONS[self.role]

    @property
    def has_full_access(self) -> bool:
        return bool(self.email and self.email.strip().casefold() in FULL_ACCESS_EMAILS)


class TokenVerifier(Protocol):
    async def verify(self, token: str) -> AuthenticatedUser: ...


class DevelopmentTokenVerifier:
    async def verify(self, token: str) -> AuthenticatedUser:
        identities = {
            # Kept as a compatibility alias for existing local scripts and tests.
            "dev-token": AuthenticatedUser(
                uid="local-user",
                email="local@promptopt.dev",
                name="Local User",
                workspace_id="local-workspace",
            ),
            "dev-engineer-token": AuthenticatedUser(
                uid="local-engineer",
                email="engineer@promptopt.dev",
                name="Local Engineer",
                workspace_id="local-workspace",
            ),
            "dev-reviewer-token": AuthenticatedUser(
                uid="local-reviewer",
                email="reviewer@promptopt.dev",
                name="Local Reviewer",
                role=UserRole.PROMPT_REVIEWER,
                workspace_id="local-workspace",
            ),
        }
        user = identities.get(token)
        if user is None:
            raise AppError(401, "INVALID_TOKEN", "Use a local development token")
        return user


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
            role=_role_from_claim(claims.get("role")),
            workspace_id=_workspace_from_claim(claims.get("workspace_id"), claims["uid"]),
        )

    def _verify_sync(self, token: str) -> dict:
        import firebase_admin
        from firebase_admin import auth

        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(options={"projectId": self.project_id})
        return auth.verify_id_token(token, check_revoked=True)


def _role_from_claim(value: object) -> UserRole:
    if value is None:
        return UserRole.PROMPT_ENGINEER
    try:
        return UserRole(str(value))
    except ValueError as exc:
        raise AppError(403, "INVALID_ROLE_CLAIM", "Account role is not supported") from exc


def _workspace_from_claim(value: object, uid: str) -> str:
    if value is None:
        return uid
    workspace_id = str(value).strip()
    if not workspace_id:
        raise AppError(403, "INVALID_WORKSPACE_CLAIM", "Account workspace is invalid")
    return workspace_id


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
