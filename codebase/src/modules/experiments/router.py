from fastapi import APIRouter, Request, Response, status

from src.api.dependencies import CurrentUser, InternalTask

from .schemas import BaselineRunResponse, CreateExperimentRequest, ExperimentResponse

router = APIRouter(prefix="/experiments", tags=["experiments"])
internal_router = APIRouter(prefix="/internal/v1/baseline-runs", tags=["internal"])


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(payload: CreateExperimentRequest, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.create(user.uid, payload)


@router.post("/{experiment_id}/runs", response_model=BaselineRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_baseline(experiment_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.request_baseline(experiment_id, user.uid)


@router.get("/runs/{run_id}", response_model=BaselineRunResponse)
async def get_run(run_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.get_run(run_id, user.uid)


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.experiments.get(experiment_id, user.uid)


@internal_router.post("/{run_id}/execute", status_code=status.HTTP_204_NO_CONTENT)
async def execute_baseline(run_id: str, _task: InternalTask, request: Request):
    await request.app.state.services.experiments.execute_baseline(run_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
