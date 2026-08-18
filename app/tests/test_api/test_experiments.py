import io
import zipfile
from datetime import UTC, datetime

import pytest

from backend.core.security import AuthenticatedUser
from backend.modules.experiments.prompts import baseline_prompt
from backend.modules.experiments.schemas import (
    ComparisonRunRecord,
    ExperimentRecord,
    ExperimentStatus,
    OptimizationRunRecord,
    PromptVersionRecord,
    PromptVersionStatus,
)
from backend.modules.experiments.schemas import (
    TestGenerationRunRecord as FinalTestGenerationRunRecord,
)
from backend.modules.projects.schemas import RuntimeReport, RuntimeStatus
from tests.test_api.test_analysis import AUTH_HEADERS, create_project, python_archive


class AdminTokenVerifier:
    async def verify(self, token: str) -> AuthenticatedUser:
        assert token == "admin-token"
        return AuthenticatedUser(uid="admin-user", email="admin@gmail.com")


@pytest.mark.asyncio
async def test_experiment_rejects_projects_from_different_runtime_environments(client):
    uploaded_id = await create_project(client, python_archive())
    analyzed = await client.post(
        f"/api/v1/projects/{uploaded_id}/analyze",
        headers=AUTH_HEADERS,
    )
    assert analyzed.status_code == 202

    response = await client.post(
        "/api/v1/experiments",
        headers=AUTH_HEADERS,
        json={
            "project_ids": ["sample:isort", uploaded_id],
            "name": "Invalid cross-environment run",
            "max_targets": 3,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "RUNTIME_ENVIRONMENT_MISMATCH"


@pytest.mark.asyncio
async def test_only_full_access_account_can_exceed_metric_budget(client, app):
    payload = {
        "project_ids": ["sample:isort"],
        "name": "Large GEPA budget",
        "max_targets": 3,
        "settings": {"max_metric_calls": 4500},
    }

    rejected = await client.post("/api/v1/experiments", headers=AUTH_HEADERS, json=payload)
    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "METRIC_BUDGET_LIMIT"

    app.state.services.token_verifier = AdminTokenVerifier()
    accepted = await client.post(
        "/api/v1/experiments",
        headers={"Authorization": "Bearer admin-token"},
        json=payload,
    )
    assert accepted.status_code == 201
    assert accepted.json()["settings"]["max_metric_calls"] == 4500


@pytest.mark.asyncio
async def test_uploaded_project_requires_runtime_before_experiment(client):
    project_id = await create_project(client, python_archive())
    await client.post(f"/api/v1/projects/{project_id}/analyze", headers=AUTH_HEADERS)

    custom_prompt = {
        "initial": "Test {filename} at {coverage_targets}.\n{source_excerpt}",
        "error": "Repair this failure: {error}",
    }
    created = await client.post(
        "/api/v1/experiments",
        headers=AUTH_HEADERS,
        json={
            "project_ids": [project_id],
            "name": "Calculator baseline",
            "max_targets": 3,
            "random_seed": 91,
            "split_percentages": {"train": 34, "validation": 33, "test": 33},
            "baseline_prompt": custom_prompt,
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
    assert created.status_code == 409
    assert created.json()["error"]["code"] == "RUNTIME_NOT_READY"


@pytest.mark.asyncio
async def test_uploaded_experiment_requires_current_runtime_and_only_uses_source_targets(client, app):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "repo-main/pkg/core.py",
            "def one():\n    return 1\n\ndef two():\n    return 2\n\ndef three():\n    return 3\n",
        )
        archive.writestr("repo-main/setup.py", "def packaging_helper():\n    return 'ignored'\n")
    project_id = await create_project(client, buffer.getvalue())
    await client.post(f"/api/v1/projects/{project_id}/analyze", headers=AUTH_HEADERS)
    repository = app.state.services.projects.repository
    project = await repository.get(project_id)
    project.settings.runtime.source_directory = "pkg"
    project.runtime_status = RuntimeStatus.READY
    project.runtime_report = RuntimeReport(status=RuntimeStatus.READY, protocol_version=2)
    await repository.save(project)
    payload = {
        "project_ids": [project_id],
        "name": "Wrapped source project",
        "max_targets": 4,
        "random_seed": 7,
    }

    outdated = await client.post("/api/v1/experiments", headers=AUTH_HEADERS, json=payload)

    assert outdated.status_code == 409
    assert outdated.json()["error"]["code"] == "RUNTIME_REBUILD_REQUIRED"

    project.runtime_report = RuntimeReport(status=RuntimeStatus.READY, protocol_version=3)
    await repository.save(project)
    created = await client.post("/api/v1/experiments", headers=AUTH_HEADERS, json=payload)

    assert created.status_code == 201, created.text
    assert {target["source_file"] for target in created.json()["targets"]} == {"pkg/core.py"}
    assert len(created.json()["targets"]) == 3


@pytest.mark.asyncio
async def test_create_experiment_rejects_invalid_custom_baseline(client):
    response = await client.post(
        "/api/v1/experiments",
        headers=AUTH_HEADERS,
        json={
            "project_ids": ["sample:isort"],
            "name": "Invalid prompt",
            "max_targets": 3,
            "baseline_prompt": {"initial": "No placeholders", "error": "Failure: {error}"},
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_BASELINE_PROMPT"


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


@pytest.mark.asyncio
async def test_prompt_registry_is_experiment_centric_and_owner_scoped(client, app):
    repository = app.state.services.experiments.repository
    now = datetime.now(UTC)
    prompt = baseline_prompt()
    for owner_id, experiment_id in (("local-user", "owned-registry"), ("another-user", "foreign-registry")):
        await repository.create(
            ExperimentRecord(
                id=experiment_id,
                owner_id=owner_id,
                project_id="project-1",
                project_ids=["project-1"],
                name=f"{experiment_id} prompt optimization",
                target_function_ids=["fn-1"],
                baseline_prompt=prompt.as_candidate(),
                status=ExperimentStatus.DRAFT,
                created_at=now,
                updated_at=now,
            )
        )

    listed = await client.get("/api/v1/prompt-registry", headers=AUTH_HEADERS)
    detail = await client.get("/api/v1/prompt-registry/owned-registry", headers=AUTH_HEADERS)
    foreign = await client.get("/api/v1/prompt-registry/foreign-registry", headers=AUTH_HEADERS)

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    entry = listed.json()["items"][0]
    assert entry["experiment_id"] == "owned-registry"
    assert entry["baseline"]["role"] == "baseline"
    assert entry["baseline"]["prompt"] == prompt.as_candidate()
    assert entry["optimized"] is None
    assert detail.status_code == 200
    assert detail.json()["experiment_name"] == "owned-registry prompt optimization"
    assert foreign.status_code == 404
    assert foreign.json()["error"]["code"] == "EXPERIMENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_final_test_generation_is_owner_scoped_and_idempotent(client, app):
    created = await client.post(
        "/api/v1/experiments",
        headers=AUTH_HEADERS,
        json={"project_ids": ["sample:isort"], "name": "Final suite source", "max_targets": 3},
    )
    assert created.status_code == 201, created.text
    experiment = created.json()
    function_id = experiment["targets"][0]["function_id"]
    payload = {
        "prompt_role": "baseline",
        "scope": "functions",
        "function_ids": [function_id],
        "idempotency_key": "browser-retry-0001",
    }
    first = await client.post(
        f"/api/v1/prompt-registry/{experiment['id']}/test-generation",
        headers=AUTH_HEADERS,
        json=payload,
    )
    retried = await client.post(
        f"/api/v1/prompt-registry/{experiment['id']}/test-generation",
        headers=AUTH_HEADERS,
        json=payload,
    )
    assert first.status_code == 202, first.text
    assert retried.status_code == 202
    run = first.json()
    assert retried.json()["id"] == run["id"]
    assert run["prompt_role"] == "baseline"
    assert run["target_ids"] == [f"sample:isort::{function_id}"]
    assert run["cloud_artifact_prefix"] is None
    listed = await client.get("/api/v1/test-generation-runs", headers=AUTH_HEADERS)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == run["id"]
    foreign_record = FinalTestGenerationRunRecord.model_validate(
        {**run, "id": "foreign-final-suite", "owner_id": "another-user"}
    )
    await app.state.services.experiments.repository.create_test_generation_run(foreign_record)
    foreign = await client.get("/api/v1/test-generation-runs/foreign-final-suite", headers=AUTH_HEADERS)
    assert foreign.status_code == 404
    assert foreign.json()["error"]["code"] == "TEST_GENERATION_RUN_NOT_FOUND"


@pytest.mark.asyncio
async def test_final_test_generation_rejects_optimized_prompt_before_comparison(client):
    created = await client.post(
        "/api/v1/experiments",
        headers=AUTH_HEADERS,
        json={"project_ids": ["sample:isort"], "name": "No final prompt yet", "max_targets": 3},
    )
    response = await client.post(
        f"/api/v1/prompt-registry/{created.json()['id']}/test-generation",
        headers=AUTH_HEADERS,
        json={"prompt_role": "optimized"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "OPTIMIZED_PROMPT_NOT_READY"
