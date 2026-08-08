from datetime import UTC, datetime

import pytest

from src.modules.experiments.prompts import baseline_prompt
from src.modules.experiments.schemas import (
    ComparisonRunRecord,
    ExperimentRecord,
    ExperimentStatus,
    OptimizationRunRecord,
    PromptVersionRecord,
    PromptVersionStatus,
)
from tests.test_api.test_analysis import AUTH_HEADERS, create_project, python_archive


@pytest.mark.asyncio
async def test_create_experiment_and_reject_unbundled_optimization(client):
    project_id = await create_project(client, python_archive())
    await client.post(f"/api/v1/projects/{project_id}/analyze", headers=AUTH_HEADERS)

    created = await client.post(
        "/api/v1/experiments",
        headers=AUTH_HEADERS,
        json={
            "project_ids": [project_id],
            "name": "Calculator baseline",
            "max_targets": 3,
            "random_seed": 91,
            "split_percentages": {"train": 34, "validation": 33, "test": 33},
            "settings": {
                "coverup_model": "vertex_ai/gemini-2.5-flash-lite",
                "optimize_model": "vertex_ai/gemini-3.5-flash",
                "max_attempts": 4,
                "repeat_tests": 3,
                "max_concurrency": 6,
                "rate_limit": 12000,
                "pytest_args": "-m not_slow",
                "max_metric_calls": 41,
                "evaluation_replicates": 2,
                "reflection_temperature": 0.5,
            },
        },
    )
    assert created.status_code == 201
    experiment = created.json()
    assert experiment["status"] == "draft"
    assert experiment["split_seed"] == 91
    assert experiment["split_percentages"] == {"train": 34, "validation": 33, "test": 33}
    assert experiment["settings"]["coverup_model"] == "vertex_ai/gemini-2.5-flash-lite"
    assert experiment["settings"]["optimize_model"] == "vertex_ai/gemini-3.5-flash"

    listed = await client.get("/api/v1/experiments", headers=AUTH_HEADERS)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == experiment["id"]

    premature_optimization = await client.post(f"/api/v1/experiments/{experiment['id']}/optimize", headers=AUTH_HEADERS)
    assert premature_optimization.status_code == 409
    assert premature_optimization.json()["error"]["code"] == "BUNDLED_SAMPLE_REQUIRED"

    premature_comparison = await client.post(f"/api/v1/experiments/{experiment['id']}/compare", headers=AUTH_HEADERS)
    assert premature_comparison.status_code == 409
    assert premature_comparison.json()["error"]["code"] == "OPTIMIZATION_NOT_READY"

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
async def test_download_comparison_artifact_checks_run_manifest(client, app):
    repository = app.state.services.experiments.repository
    now = datetime.now(UTC)
    await repository.create(
        ExperimentRecord(
            id="comparison-artifact-experiment",
            owner_id="local-user",
            project_id="project-1",
            name="Comparison artifacts",
            target_function_ids=["fn-1"],
            status=ExperimentStatus.COMPARISON_SUCCEEDED,
            comparison_run_id="comparison-artifact-run",
            created_at=now,
            updated_at=now,
        )
    )
    object_name = (
        "artifacts/local-user/project-1/comparison-artifact-experiment/comparison-artifact-run/final_validation.json"
    )
    await repository.create_comparison_run(
        ComparisonRunRecord(
            id="comparison-artifact-run",
            experiment_id="comparison-artifact-experiment",
            optimization_run_id="optimization-1",
            status=ExperimentStatus.COMPARISON_SUCCEEDED,
            baseline_prompt_digest="parent",
            candidate_prompt_digest="candidate",
            test_target_ids=["fn-1"],
            replicate_count=2,
            artifact_objects={"final_validation.json": object_name},
            created_at=now,
            finished_at=now,
        )
    )
    await app.state.services.experiments.storage.write(object_name, b'{"absolute_gain": 0.4}', "application/json")

    downloaded = await client.get(
        "/api/v1/experiments/comparison-runs/comparison-artifact-run/artifacts/final_validation.json",
        headers=AUTH_HEADERS,
    )
    missing = await client.get(
        "/api/v1/experiments/comparison-runs/comparison-artifact-run/artifacts/missing.json",
        headers=AUTH_HEADERS,
    )

    assert downloaded.status_code == 200
    assert downloaded.json() == {"absolute_gain": 0.4}
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "ARTIFACT_NOT_FOUND"


@pytest.mark.asyncio
async def test_experiment_requires_analyzed_project(client):
    project_id = await create_project(client, python_archive())
    response = await client.post(
        "/api/v1/experiments",
        headers=AUTH_HEADERS,
        json={"project_ids": [project_id], "name": "Blocked"},
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


@pytest.mark.asyncio
async def test_prompt_version_list_is_owned_and_filters_by_status(client, app):
    repository = app.state.services.experiments.repository
    now = datetime.now(UTC)
    prompt = baseline_prompt()
    for owner_id, experiment_id, version_id, version_status in (
        ("local-user", "owned-review-experiment", "owned-review-version", PromptVersionStatus.IN_REVIEW),
        ("local-user", "owned-approved-experiment", "owned-approved-version", PromptVersionStatus.APPROVED),
        ("another-user", "foreign-experiment", "foreign-version", PromptVersionStatus.IN_REVIEW),
    ):
        await repository.create(
            ExperimentRecord(
                id=experiment_id,
                owner_id=owner_id,
                project_id="project-1",
                name=experiment_id,
                target_function_ids=["fn-1"],
                status=ExperimentStatus.IN_REVIEW,
                prompt_version_id=version_id,
                created_at=now,
                updated_at=now,
            )
        )
        await repository.create_prompt_version(
            PromptVersionRecord(
                id=version_id,
                experiment_id=experiment_id,
                comparison_run_id=f"{version_id}-comparison",
                parent_prompt_digest="parent-digest",
                prompt_digest=prompt.digest(),
                prompt=prompt.as_candidate(),
                status=version_status,
                created_at=now,
            )
        )

    listed = await client.get("/api/v1/prompt-versions", headers=AUTH_HEADERS)
    awaiting_review = await client.get("/api/v1/prompt-versions?status=in_review", headers=AUTH_HEADERS)

    assert listed.status_code == 200
    assert listed.json()["total"] == 2
    assert {item["id"] for item in listed.json()["items"]} == {
        "owned-review-version",
        "owned-approved-version",
    }
    assert awaiting_review.json()["total"] == 1
    assert awaiting_review.json()["items"][0]["id"] == "owned-review-version"
