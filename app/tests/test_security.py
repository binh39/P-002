import pytest

from backend.core.errors import AppError
from backend.core.security import (
    AuthenticatedUser,
    DevelopmentTokenVerifier,
    UserRole,
    _role_from_claim,
    _workspace_from_claim,
)


def test_full_access_email_is_case_insensitive_and_exact():
    assert AuthenticatedUser("admin", " ADMIN@gmail.com ").has_full_access
    assert AuthenticatedUser("admin-test", "admintest@gmail.com").has_full_access
    assert not AuthenticatedUser("other", "admin+other@gmail.com").has_full_access
    assert not AuthenticatedUser("anonymous").has_full_access


def test_identity_defaults_to_engineer_and_private_workspace():
    user = AuthenticatedUser("user-1")
    assert user.role == UserRole.PROMPT_ENGINEER
    assert user.workspace_id == "user-1"
    assert "test_suites:write" in user.permissions


@pytest.mark.asyncio
async def test_development_tokens_expose_two_distinct_roles_in_one_workspace():
    verifier = DevelopmentTokenVerifier()
    engineer = await verifier.verify("dev-engineer-token")
    reviewer = await verifier.verify("dev-reviewer-token")
    assert engineer.uid == "local-engineer"
    assert engineer.role == UserRole.PROMPT_ENGINEER
    assert reviewer.uid == "local-reviewer"
    assert reviewer.role == UserRole.PROMPT_REVIEWER
    assert engineer.workspace_id == reviewer.workspace_id == "local-workspace"


def test_verified_claim_parsing_fails_closed_for_invalid_values():
    assert _role_from_claim(None) == UserRole.PROMPT_ENGINEER
    assert _workspace_from_claim(None, "uid-1") == "uid-1"
    with pytest.raises(AppError, match="Account role"):
        _role_from_claim("admin")
    with pytest.raises(AppError, match="Account workspace"):
        _workspace_from_claim("  ", "uid-1")
