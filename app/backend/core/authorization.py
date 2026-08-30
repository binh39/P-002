from backend.core.errors import AppError
from backend.core.security import AuthenticatedUser, UserRole


def require_engineer(user: AuthenticatedUser) -> AuthenticatedUser:
    if user.role != UserRole.PROMPT_ENGINEER:
        raise AppError(403, "ROLE_FORBIDDEN", "Prompt Engineer role is required")
    return user


def require_reviewer(user: AuthenticatedUser) -> AuthenticatedUser:
    if user.role != UserRole.PROMPT_REVIEWER:
        raise AppError(403, "ROLE_FORBIDDEN", "Prompt Reviewer role is required")
    return user


def require_same_workspace(user: AuthenticatedUser, workspace_id: str | None) -> None:
    if not workspace_id or workspace_id != user.workspace_id:
        raise AppError(404, "RESOURCE_NOT_FOUND", "Resource was not found")


def require_owner(user: AuthenticatedUser, owner_id: str) -> None:
    if owner_id != user.uid:
        raise AppError(404, "RESOURCE_NOT_FOUND", "Resource was not found")


def forbid_self_review(user: AuthenticatedUser, creator_id: str) -> None:
    if creator_id == user.uid:
        raise AppError(403, "SELF_REVIEW_FORBIDDEN", "Reviewers cannot review their own candidate")
