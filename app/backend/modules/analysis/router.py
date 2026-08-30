from fastapi import APIRouter, Request, Response, status

from backend.api.dependencies import CurrentUser, EngineerUser, InternalTask
from backend.modules.analysis.schemas import FunctionSourceResponse, ProjectFunctionListResponse
from backend.modules.projects.schemas import ProjectResponse

router = APIRouter(prefix="/projects", tags=["project-analysis"])
internal_router = APIRouter(prefix="/internal/v1/projects", tags=["internal"])


@router.post("/{project_id}/analyze", response_model=ProjectResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_project(project_id: str, user: EngineerUser, request: Request):
    return await request.app.state.services.analysis.request(project_id, user.uid)


@router.get("/{project_id}/functions", response_model=ProjectFunctionListResponse)
async def list_project_functions(project_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.analysis.list_functions(project_id, user.uid)


@router.get(
    "/{project_id}/functions/{function_id}/source",
    response_model=FunctionSourceResponse,
)
async def get_function_source(
    project_id: str,
    function_id: str,
    user: CurrentUser,
    request: Request,
):
    return await request.app.state.services.analysis.get_source(project_id, function_id, user.uid)


@internal_router.post("/{project_id}/analyze", status_code=status.HTTP_204_NO_CONTENT)
async def run_project_analysis(project_id: str, _task: InternalTask, request: Request):
    await request.app.state.services.analysis.run(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
