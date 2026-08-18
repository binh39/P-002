from fastapi import APIRouter, Request, Response, status

from backend.api.dependencies import CurrentUser

from .schemas import AIProvider, ProviderCredentialInput, ProviderCredentialListResponse, ProviderCredentialResponse

router = APIRouter(prefix="/provider-credentials", tags=["provider-credentials"])


@router.get("", response_model=ProviderCredentialListResponse)
async def list_provider_credentials(user: CurrentUser, request: Request):
    items = await request.app.state.services.provider_credentials.list(user.uid)
    return ProviderCredentialListResponse(items=items)


@router.put("/{provider}", response_model=ProviderCredentialResponse)
async def save_provider_credential(
    provider: AIProvider,
    payload: ProviderCredentialInput,
    user: CurrentUser,
    request: Request,
):
    return await request.app.state.services.provider_credentials.save(
        user.uid, provider, payload.api_key.get_secret_value()
    )


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider_credential(provider: AIProvider, user: CurrentUser, request: Request):
    await request.app.state.services.provider_credentials.delete(user.uid, provider)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
