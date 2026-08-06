from fastapi import APIRouter, Request, Response, status

from src.api.dependencies import CurrentUser
from src.modules.uploads.schemas import CreateUploadRequest, UploadResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def create_upload(payload: CreateUploadRequest, user: CurrentUser, request: Request):
    return await request.app.state.services.uploads.create(user.uid, payload)


@router.put("/{upload_id}/content", status_code=status.HTTP_204_NO_CONTENT)
async def put_local_upload(upload_id: str, user: CurrentUser, request: Request):
    content = await request.body()
    await request.app.state.services.uploads.put_local(upload_id, user.uid, content)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{upload_id}/complete", response_model=UploadResponse)
async def complete_upload(upload_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.uploads.complete(upload_id, user.uid)
