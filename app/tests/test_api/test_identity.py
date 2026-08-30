import pytest


@pytest.mark.asyncio
async def test_current_identity_returns_verified_role_workspace_and_permissions(client):
    response = await client.get(
        "/api/v1/me",
        headers={"Authorization": "Bearer dev-reviewer-token"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": "local-reviewer",
        "name": "Local Reviewer",
        "email": "reviewer@promptopt.dev",
        "role": "prompt_reviewer",
        "workspace_id": "local-workspace",
        "permissions": ["reviews:read", "reviews:decide", "test_suites:read"],
    }


@pytest.mark.asyncio
async def test_reviewer_cannot_call_engineer_mutation(client):
    response = await client.post(
        "/api/v1/uploads",
        headers={"Authorization": "Bearer dev-reviewer-token"},
        json={"filename": "source.zip", "content_type": "application/zip", "size_bytes": 10},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ROLE_FORBIDDEN"
