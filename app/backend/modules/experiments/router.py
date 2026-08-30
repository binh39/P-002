from fastapi import APIRouter, Query, Request, Response, status

from backend.api.dependencies import CurrentUser, EngineerUser, InternalTask

from .schemas import (
    ComparisonRunResponse,
    CreateExperimentRequest,
    CreateTestGenerationRequest,
    EvolutionResponse,
    ExperimentListResponse,
    ExperimentResponse,
    OptimizationRunResponse,
    PromptRegistryEntryResponse,
    PromptRegistryListResponse,
    PromptVersionListResponse,
    PromptVersionResponse,
    PromptVersionStatus,
    ResumeOptimizationRequest,
    ReviewPromptVersionRequest,
    TestGenerationRunListResponse,
    TestGenerationRunResponse,
)

router = APIRouter(prefix="/experiments", tags=["experiments"])
optimization_internal_router = APIRouter(prefix="/internal/v1/optimization-runs", tags=["internal"])
comparison_internal_router = APIRouter(prefix="/internal/v1/comparison-runs", tags=["internal"])
test_generation_internal_router = APIRouter(prefix="/internal/v1/test-generation-runs", tags=["internal"])
prompt_router = APIRouter(prefix="/prompt-versions", tags=["prompt-versions"])
prompt_registry_router = APIRouter(prefix="/prompt-registry", tags=["prompt-registry"])
test_generation_router = APIRouter(prefix="/test-generation-runs", tags=["test-generation"])


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(payload: CreateExperimentRequest, user: EngineerUser, request: Request):
    return await request.app.state.services.experiments.create(
        user.uid,
        payload,
        full_access=user.has_full_access,
    )


@router.get("", response_model=ExperimentListResponse)
async def list_experiments(user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.list(user.uid)


@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(experiment_id: str, user: EngineerUser, request: Request):
    await request.app.state.services.experiments.delete(experiment_id, user.uid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{experiment_id}/optimize", response_model=OptimizationRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_optimization(experiment_id: str, user: EngineerUser, request: Request):
    return await request.app.state.services.experiments.request_optimization(
        experiment_id,
        user.uid,
        full_access=user.has_full_access,
    )


@router.get("/optimization-runs/{run_id}", response_model=OptimizationRunResponse)
async def get_optimization_run(run_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.get_optimization_run(run_id, user.uid)


@router.post("/optimization-runs/{run_id}/cancel", response_model=OptimizationRunResponse)
async def cancel_optimization(run_id: str, user: EngineerUser, request: Request):
    return await request.app.state.services.experiments.cancel_optimization(run_id, user.uid)


@router.post("/optimization-runs/{run_id}/resume", response_model=OptimizationRunResponse)
async def resume_optimization(
    run_id: str,
    user: EngineerUser,
    request: Request,
    payload: ResumeOptimizationRequest | None = None,
):
    return await request.app.state.services.experiments.resume_optimization(
        run_id,
        user.uid,
        max_concurrency=payload.max_concurrency if payload else None,
        full_access=user.has_full_access,
    )


@router.get("/optimization-runs/{run_id}/evolution", response_model=EvolutionResponse)
async def get_optimization_evolution(run_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.get_optimization_evolution(run_id, user.uid)


@router.get("/optimization-runs/{run_id}/artifacts/{artifact_name}")
async def get_optimization_artifact(run_id: str, artifact_name: str, user: CurrentUser, request: Request):
    content = await request.app.state.services.experiments.get_optimization_artifact(run_id, artifact_name, user.uid)
    safe_name = artifact_name.replace('"', "")
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.post("/{experiment_id}/compare", response_model=ComparisonRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_comparison(experiment_id: str, user: EngineerUser, request: Request):
    return await request.app.state.services.experiments.request_comparison(
        experiment_id,
        user.uid,
        full_access=user.has_full_access,
    )


@router.get("/comparison-runs/{run_id}", response_model=ComparisonRunResponse)
async def get_comparison_run(run_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.get_comparison_run(run_id, user.uid)


@router.get("/comparison-runs/{run_id}/artifacts/{artifact_name}")
async def get_comparison_artifact(run_id: str, artifact_name: str, user: CurrentUser, request: Request):
    content = await request.app.state.services.experiments.get_comparison_artifact(run_id, artifact_name, user.uid)
    safe_name = artifact_name.replace('"', "")
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.get(experiment_id, user.uid)


@optimization_internal_router.post("/{run_id}/execute", status_code=status.HTTP_204_NO_CONTENT)
async def execute_optimization(run_id: str, _task: InternalTask, request: Request):
    await request.app.state.services.experiments.execute_optimization(run_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@comparison_internal_router.post("/{run_id}/execute", status_code=status.HTTP_204_NO_CONTENT)
async def execute_comparison(run_id: str, _task: InternalTask, request: Request):
    await request.app.state.services.experiments.execute_comparison(run_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@prompt_router.get("/{version_id}", response_model=PromptVersionResponse)
async def get_prompt_version(version_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.get_prompt_version(version_id, user.uid)


@prompt_router.get("", response_model=PromptVersionListResponse)
async def list_prompt_versions(
    user: CurrentUser,
    request: Request,
    status_filter: PromptVersionStatus | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    return await request.app.state.services.experiments.list_prompt_versions(user.uid, status_filter, offset, limit)


@prompt_router.post("/{version_id}/approve", response_model=PromptVersionResponse)
async def approve_prompt_version(
    version_id: str, payload: ReviewPromptVersionRequest, user: CurrentUser, request: Request
):
    return await request.app.state.services.experiments.review_prompt_version(
        version_id, user.uid, PromptVersionStatus.APPROVED, payload.comment
    )


@prompt_router.post("/{version_id}/reject", response_model=PromptVersionResponse)
async def reject_prompt_version(
    version_id: str, payload: ReviewPromptVersionRequest, user: CurrentUser, request: Request
):
    return await request.app.state.services.experiments.review_prompt_version(
        version_id, user.uid, PromptVersionStatus.REJECTED, payload.comment
    )


@prompt_registry_router.get("", response_model=PromptRegistryListResponse)
async def list_prompt_registry(
    user: CurrentUser,
    request: Request,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    return await request.app.state.services.experiments.list_prompt_registry(user.uid, offset, limit)


@prompt_registry_router.get("/{experiment_id}", response_model=PromptRegistryEntryResponse)
async def get_prompt_registry_entry(experiment_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.get_prompt_registry_entry(experiment_id, user.uid)


@prompt_registry_router.post(
    "/{experiment_id}/test-generation",
    response_model=TestGenerationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_test_generation(
    experiment_id: str,
    payload: CreateTestGenerationRequest,
    user: EngineerUser,
    request: Request,
):
    return await request.app.state.services.experiments.request_test_generation(experiment_id, user.uid, payload)


@test_generation_router.get("", response_model=TestGenerationRunListResponse)
async def list_test_generation_runs(
    user: CurrentUser,
    request: Request,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    return await request.app.state.services.experiments.list_test_generation_runs(user.uid, offset, limit)


@test_generation_router.get("/{run_id}", response_model=TestGenerationRunResponse)
async def get_test_generation_run(run_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.get_test_generation_run(run_id, user.uid)


@test_generation_router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_generation_run(run_id: str, user: EngineerUser, request: Request):
    await request.app.state.services.experiments.delete_test_generation_run(run_id, user.uid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@test_generation_router.get("/{run_id}/artifacts/manifest/content")
async def get_test_generation_manifest(run_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.get_test_generation_manifest(run_id, user.uid)


@test_generation_router.get("/{run_id}/artifacts/{artifact_name}/content")
async def get_test_generation_text_artifact(run_id: str, artifact_name: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.get_test_generation_text_artifact(
        run_id, artifact_name, user.uid
    )


@test_generation_router.get("/{run_id}/artifacts/{artifact_name}")
async def get_test_generation_artifact(run_id: str, artifact_name: str, user: CurrentUser, request: Request):
    content = await request.app.state.services.experiments.get_test_generation_artifact(run_id, artifact_name, user.uid)
    media_type = "application/zip" if artifact_name == "suite_zip" else "application/json"
    return Response(content=content, media_type=media_type)


@test_generation_internal_router.post("/{run_id}/execute", status_code=status.HTTP_204_NO_CONTENT)
async def execute_test_generation(run_id: str, _task: InternalTask, request: Request):
    await request.app.state.services.experiments.execute_test_generation(run_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
