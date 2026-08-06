from datetime import UTC, datetime

import pytest

from src.modules.experiments.prompts import baseline_prompt
from src.modules.experiments.schemas import (
    ExperimentRecord,
    ExperimentStatus,
    OptimizationRunRecord,
    PromptVersionRecord,
    PromptVersionStatus,
)
from tests.test_api.test_analysis import AUTH_HEADERS, create_project, python_archive


@pytest.mark.asyncio
async def test_create_experiment_and_queue_baseline(client):
    project_id = await create_project(client, python_archive())
    await client.post(f"/api/v1/projects/{project_id}/analyze", headers=AUTH_HEADERS)
    functions = (await client.get(f"/api/v1/projects/{project_id}/functions", headers=AUTH_HEADERS)).json()["items"]

    created = await client.post(
        "/api/v1/experiments",
        headers=AUTH_HEADERS,
        json={"project_id": project_id, "name": "Calculator baseline", "target_function_ids": [functions[0]["id"]]},
    )
    assert created.status_code == 201
    experiment = created.json()
    assert experiment["status"] == "draft"

    listed = await client.get("/api/v1/experiments", headers=AUTH_HEADERS)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == experiment["id"]

    premature_optimization = await client.post(f"/api/v1/experiments/{experiment['id']}/optimize", headers=AUTH_HEADERS)
    assert premature_optimization.status_code == 409
    assert premature_optimization.json()["error"]["code"] == "BASELINE_NOT_READY"

    premature_comparison = await client.post(f"/api/v1/experiments/{experiment['id']}/compare", headers=AUTH_HEADERS)
    assert premature_comparison.status_code == 409
    assert premature_comparison.json()["error"]["code"] == "OPTIMIZATION_NOT_READY"

    queued = await client.post(f"/api/v1/experiments/{experiment['id']}/runs", headers=AUTH_HEADERS)
    assert queued.status_code == 202
    run = queued.json()
    assert run["target_count"] == 1
    # The inline development worker refuses to execute user Python in the API container.
    assert run["status"] == "failed"
    assert run["error_message"] == "Baseline sandbox is not configured"

    fetched = await client.get(f"/api/v1/experiments/runs/{run['id']}", headers=AUTH_HEADERS)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == run["id"]


@pytest.mark.asyncio
async def test_download_baseline_artifact_checks_run_manifest(client, app):
    project_id = await create_project(client, python_archive())
    await client.post(f"/api/v1/projects/{project_id}/analyze", headers=AUTH_HEADERS)
    functions = (await client.get(f"/api/v1/projects/{project_id}/functions", headers=AUTH_HEADERS)).json()["items"]
    experiment = (
        await client.post(
            "/api/v1/experiments",
            headers=AUTH_HEADERS,
            json={
                "project_id": project_id,
                "name": "Artifact baseline",
                "target_function_ids": [functions[0]["id"]],
            },
        )
    ).json()
    run = (await client.post(f"/api/v1/experiments/{experiment['id']}/runs", headers=AUTH_HEADERS)).json()
    repository = app.state.services.experiments.repository
    stored_run = await repository.get_run(run["id"])
    object_name = f"artifacts/local-user/{project_id}/{experiment['id']}/{run['id']}/coverup.log"
    stored_run.artifact_objects = {"coverup.log": object_name}
    await repository.save_run(stored_run)
    await app.state.services.experiments.storage.write(object_name, b"runner output", "text/plain")

    downloaded = await client.get(f"/api/v1/experiments/runs/{run['id']}/artifacts/coverup.log", headers=AUTH_HEADERS)
    missing = await client.get(f"/api/v1/experiments/runs/{run['id']}/artifacts/missing.log", headers=AUTH_HEADERS)

    assert downloaded.status_code == 200
    assert downloaded.content == b"runner output"
    assert downloaded.headers["content-disposition"] == 'attachment; filename="coverup.log"'
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "ARTIFACT_NOT_FOUND"


@pytest.mark.asyncio
async def test_download_optimization_artifact_checks_run_manifest(client, app):
    repository = app.state.services.experiments.repository
    now = datetime.now(UTC)
    await repository.create(
        ExperimentRecord(
            id="optimization-artifact-experiment",
            owner_id="local-user",
            project_id="project-1",
            name="Optimization artifacts",
            target_function_ids=["fn-1"],
            status=ExperimentStatus.OPTIMIZATION_SUCCEEDED,
            optimization_run_id="optimization-artifact-run",
            created_at=now,
            updated_at=now,
        )
    )
    object_name = (
        "artifacts/local-user/project-1/optimization-artifact-experiment/optimization-artifact-run/gepa_result.json"
    )
    await repository.create_optimization_run(
        OptimizationRunRecord(
            id="optimization-artifact-run",
            experiment_id="optimization-artifact-experiment",
            status=ExperimentStatus.OPTIMIZATION_SUCCEEDED,
            parent_prompt_digest="parent",
            candidate_prompt_digest="candidate",
            artifact_objects={"gepa_result.json": object_name},
            created_at=now,
            finished_at=now,
        )
    )
    await app.state.services.experiments.storage.write(object_name, b'{"score": 0.8}', "application/json")

    downloaded = await client.get(
        "/api/v1/experiments/optimization-runs/optimization-artifact-run/artifacts/gepa_result.json",
        headers=AUTH_HEADERS,
    )
    missing = await client.get(
        "/api/v1/experiments/optimization-runs/optimization-artifact-run/artifacts/missing.json",
        headers=AUTH_HEADERS,
    )

    assert downloaded.status_code == 200
    assert downloaded.json() == {"score": 0.8}
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "ARTIFACT_NOT_FOUND"


@pytest.mark.asyncio
async def test_experiment_requires_analyzed_project(client):
    project_id = await create_project(client, python_archive())
    response = await client.post(
        "/api/v1/experiments",
        headers=AUTH_HEADERS,
        json={"project_id": project_id, "name": "Blocked", "target_function_ids": ["missing"]},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ANALYSIS_NOT_READY"


@pytest.mark.asyncio
async def test_prompt_version_review_api_is_idempotent_and_cannot_be_reversed(client, app):
    repository = app.state.services.experiments.repository
    now = datetime.now(UTC)
    prompt = baseline_prompt()
    await repository.create(
        ExperimentRecord(
            id="review-experiment",
            owner_id="local-user",
            project_id="project-1",
            name="Review candidate",
            target_function_ids=["fn-1"],
            status=ExperimentStatus.IN_REVIEW,
            prompt_version_id="version-1",
            created_at=now,
            updated_at=now,
        )
    )
    await repository.create_prompt_version(
        PromptVersionRecord(
            id="version-1",
            experiment_id="review-experiment",
            comparison_run_id="comparison-1",
            parent_prompt_digest="parent-digest",
            prompt_digest=prompt.digest(),
            prompt=prompt.as_candidate(),
            status=PromptVersionStatus.IN_REVIEW,
            created_at=now,
        )
    )

    approved = await client.post(
        "/api/v1/prompt-versions/version-1/approve",
        headers=AUTH_HEADERS,
        json={"comment": "Ready for controlled rollout"},
    )
    retried = await client.post(
        "/api/v1/prompt-versions/version-1/approve",
        headers=AUTH_HEADERS,
        json={"comment": "duplicate request"},
    )
    reversed_decision = await client.post(
        "/api/v1/prompt-versions/version-1/reject",
        headers=AUTH_HEADERS,
        json={"comment": "reverse"},
    )

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["reviewer_id"] == "local-user"
    assert retried.json()["reviewed_at"] == approved.json()["reviewed_at"]
    assert retried.json()["review_comment"] == "Ready for controlled rollout"
    assert reversed_decision.status_code == 409
    assert reversed_decision.json()["error"]["code"] == "PROMPT_VERSION_ALREADY_REVIEWED"
