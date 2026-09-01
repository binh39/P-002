from datetime import UTC, datetime

import pytest

from backend.modules.experiments import schemas as experiment_schemas


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
async def test_registration_can_select_reviewer_after_early_identity_resolution(client):
    auth = {"Authorization": "Bearer dev-token"}

    # Firebase emits an auth-state event as soon as the account is created, so
    # /me can arrive before the explicit onboarding request.
    early_identity = await client.get("/api/v1/me", headers=auth)
    assert early_identity.status_code == 200
    assert early_identity.json()["role"] == "prompt_engineer"

    onboarded = await client.post(
        "/api/v1/onboarding",
        headers=auth,
        json={"name": "Registered Reviewer", "role": "prompt_reviewer"},
    )
    assert onboarded.status_code == 200
    assert onboarded.json()["role"] == "prompt_reviewer"

    restored = await client.get("/api/v1/me", headers=auth)
    assert restored.status_code == 200
    assert restored.json()["role"] == "prompt_reviewer"
    assert restored.json()["permissions"] == ["reviews:read", "reviews:decide", "test_suites:read"]

    role_change = await client.post(
        "/api/v1/onboarding",
        headers=auth,
        json={"name": "Registered Reviewer", "role": "prompt_engineer"},
    )
    assert role_change.status_code == 409
    assert role_change.json()["error"]["code"] == "ONBOARDING_ALREADY_COMPLETED"


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


@pytest.mark.asyncio
async def test_legacy_records_only_appear_in_personal_workspace(client, app):
    auth = {"Authorization": "Bearer dev-engineer-token"}
    await client.get("/api/v1/me", headers=auth)
    now = datetime.now(UTC)
    repository = app.state.services.experiments.repository
    await repository.create(
        experiment_schemas.ExperimentRecord(
            id="legacy-experiment",
            owner_id="local-engineer",
            name="Legacy experiment",
            status=experiment_schemas.ExperimentStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )
    )
    await repository.create_test_generation_run(
        experiment_schemas.TestGenerationRunRecord(
            id="legacy-suite",
            owner_id="local-engineer",
            experiment_id="legacy-experiment",
            name="Legacy suite",
            prompt_snapshot_id="snapshot",
            prompt_digest="digest",
            prompt_role=experiment_schemas.PromptRole.BASELINE,
            status=experiment_schemas.TestGenerationStatus.COMPLETED,
            source_snapshot_digest="source",
            dataset_digest="dataset",
            scope=experiment_schemas.TestGenerationScope.PROJECT,
            model="google/gemini-2.5-flash",
            random_seed=115,
            repeat_tests=1,
            max_attempts=1,
            max_concurrency=1,
            runner_protocol_version=13,
            created_at=now,
        )
    )

    assert (await client.get("/api/v1/experiments", headers=auth)).json()["total"] == 1
    assert (await client.get("/api/v1/test-generation-runs", headers=auth)).json()["total"] == 1

    await client.post("/api/v1/workspaces", headers=auth, json={"name": "Empty workspace"})
    assert (await client.get("/api/v1/experiments", headers=auth)).json()["total"] == 0
    assert (await client.get("/api/v1/test-generation-runs", headers=auth)).json()["total"] == 0
