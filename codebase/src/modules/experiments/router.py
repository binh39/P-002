from fastapi import APIRouter, Request, Response, status

from src.api.dependencies import CurrentUser, InternalTask

from .schemas import (
    BaselineRunResponse,
    ComparisonRunResponse,
    CreateExperimentRequest,
    ExperimentListResponse,
    ExperimentResponse,
    OptimizationRunResponse,
    PromptVersionResponse,
    PromptVersionStatus,
    ReviewPromptVersionRequest,
)

router = APIRouter(prefix="/experiments", tags=["experiments"])
internal_router = APIRouter(prefix="/internal/v1/baseline-runs", tags=["internal"])
optimization_internal_router = APIRouter(prefix="/internal/v1/optimization-runs", tags=["internal"])
comparison_internal_router = APIRouter(prefix="/internal/v1/comparison-runs", tags=["internal"])
prompt_router = APIRouter(prefix="/prompt-versions", tags=["prompt-versions"])


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(payload: CreateExperimentRequest, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.create(user.uid, payload)


@router.get("", response_model=ExperimentListResponse)
async def list_experiments(user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.list(user.uid)


@router.post("/{experiment_id}/runs", response_model=BaselineRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_baseline(experiment_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.request_baseline(experiment_id, user.uid)


@router.get("/runs/{run_id}", response_model=BaselineRunResponse)
async def get_run(run_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.get_run(run_id, user.uid)


@router.get("/runs/{run_id}/artifacts/{artifact_name}")
async def get_baseline_artifact(run_id: str, artifact_name: str, user: CurrentUser, request: Request):
    content_types = {
        "coverage_after.json": "application/json",
        "prompt.json": "application/json",
        "attempt_trace.jsonl": "application/x-ndjson",
        "generated_tests.zip": "application/zip",
        "target_coverage.json": "application/json",
        "coverage.data": "application/octet-stream",
    }
    content = await request.app.state.services.experiments.get_baseline_artifact(run_id, artifact_name, user.uid)
    safe_name = artifact_name.replace('"', "")
    return Response(
        content=content,
        media_type=content_types.get(artifact_name, "text/plain"),
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.post("/{experiment_id}/optimize", response_model=OptimizationRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_optimization(experiment_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.request_optimization(experiment_id, user.uid)


@router.get("/optimization-runs/{run_id}", response_model=OptimizationRunResponse)
async def get_optimization_run(run_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.get_optimization_run(run_id, user.uid)


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
async def request_comparison(experiment_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.request_comparison(experiment_id, user.uid)


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


@internal_router.post("/{run_id}/execute", status_code=status.HTTP_204_NO_CONTENT)
async def execute_baseline(run_id: str, _task: InternalTask, request: Request):
    await request.app.state.services.experiments.execute_baseline(run_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
