import pytest


@pytest.mark.asyncio
async def test_registration_role_and_workspace_lifecycle(client):
    auth = {"Authorization": "Bearer dev-engineer-token"}
    onboarded = await client.post(
        "/api/v1/onboarding",
        headers=auth,
        json={"name": "Workspace Engineer", "role": "prompt_engineer"},
    )
    assert onboarded.status_code == 200
    assert onboarded.json()["role"] == "prompt_engineer"

    initial = await client.get("/api/v1/workspaces", headers=auth)
    assert initial.status_code == 200
    assert initial.json()["items"][0]["name"] == "Workspace 1"

    created = await client.post(
        "/api/v1/workspaces",
        headers=auth,
        json={"name": "Release Review"},
    )
    assert created.status_code == 201
    listed = await client.get("/api/v1/workspaces", headers=auth)
    assert listed.json()["active_workspace_id"] == created.json()["id"]


@pytest.mark.asyncio
async def test_workspace_owner_can_add_and_remove_registered_member(client):
    engineer = {"Authorization": "Bearer dev-engineer-token"}
    reviewer = {"Authorization": "Bearer dev-reviewer-token"}
    await client.get("/api/v1/me", headers=engineer)
    await client.get("/api/v1/me", headers=reviewer)
    workspaces = (await client.get("/api/v1/workspaces", headers=engineer)).json()
    workspace_id = workspaces["active_workspace_id"]

    added = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=engineer,
        json={"email": "reviewer@promptopt.dev"},
    )
    assert added.status_code == 200
    assert any(member["user_id"] == "local-reviewer" for member in added.json()["members"])

    removed = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/local-reviewer",
        headers=engineer,
    )
    assert removed.status_code == 200
    assert all(member["user_id"] != "local-reviewer" for member in removed.json()["members"])
