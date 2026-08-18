from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass

from backend.core.errors import AppError

from .schemas import AIProvider, ProviderCredentialResponse, mask_api_key


@dataclass(frozen=True, slots=True)
class ProviderSecretReference:
    secret: str
    version: str


class ProviderCredentialStore:
    async def save(self, owner_id: str, provider: AIProvider, api_key: str) -> ProviderSecretReference:
        raise NotImplementedError

    async def read(self, owner_id: str, provider: AIProvider) -> str | None:
        raise NotImplementedError

    async def resolve(self, owner_id: str, provider: AIProvider) -> ProviderSecretReference | None:
        raise NotImplementedError

    async def delete(self, owner_id: str, provider: AIProvider) -> None:
        raise NotImplementedError


class InMemoryProviderCredentialStore(ProviderCredentialStore):
    """Local/test-only store. Production credentials always use Secret Manager."""

    def __init__(self):
        self._values: dict[tuple[str, AIProvider], str] = {}

    async def save(self, owner_id: str, provider: AIProvider, api_key: str) -> ProviderSecretReference:
        self._values[(owner_id, provider)] = api_key
        return ProviderSecretReference(secret=f"local-{provider.value}", version="latest")

    async def read(self, owner_id: str, provider: AIProvider) -> str | None:
        return self._values.get((owner_id, provider))

    async def resolve(self, owner_id: str, provider: AIProvider) -> ProviderSecretReference | None:
        if (owner_id, provider) not in self._values:
            return None
        return ProviderSecretReference(secret=f"local-{provider.value}", version="latest")

    async def delete(self, owner_id: str, provider: AIProvider) -> None:
        self._values.pop((owner_id, provider), None)


class SecretManagerProviderCredentialStore(ProviderCredentialStore):
    def __init__(self, project_id: str, secret_prefix: str):
        from google.cloud import secretmanager

        self._client = secretmanager.SecretManagerServiceClient()
        self._project_id = project_id
        self._secret_prefix = secret_prefix

    def _secret_id(self, owner_id: str, provider: AIProvider) -> str:
        owner_digest = hashlib.sha256(owner_id.encode()).hexdigest()[:24]
        return f"{self._secret_prefix}-{owner_digest}-{provider.value}"

    def _secret_name(self, owner_id: str, provider: AIProvider) -> str:
        return f"projects/{self._project_id}/secrets/{self._secret_id(owner_id, provider)}"

    async def save(self, owner_id: str, provider: AIProvider, api_key: str) -> ProviderSecretReference:
        from google.api_core.exceptions import AlreadyExists

        secret_id = self._secret_id(owner_id, provider)
        parent = f"projects/{self._project_id}"

        def write():
            try:
                self._client.create_secret(
                    request={"parent": parent, "secret_id": secret_id, "secret": {"replication": {"automatic": {}}}}
                )
            except AlreadyExists:
                pass
            version = self._client.add_secret_version(
                request={"parent": self._secret_name(owner_id, provider), "payload": {"data": api_key.encode()}}
            )
            return version.name.rsplit("/", maxsplit=1)[-1]

        version = await asyncio.to_thread(write)
        return ProviderSecretReference(secret=secret_id, version=version)

    async def read(self, owner_id: str, provider: AIProvider) -> str | None:
        from google.api_core.exceptions import NotFound

        def read():
            try:
                response = self._client.access_secret_version(
                    request={"name": f"{self._secret_name(owner_id, provider)}/versions/latest"}
                )
            except NotFound:
                return None
            return response.payload.data.decode()

        return await asyncio.to_thread(read)

    async def resolve(self, owner_id: str, provider: AIProvider) -> ProviderSecretReference | None:
        from google.api_core.exceptions import NotFound

        def resolve():
            try:
                response = self._client.access_secret_version(
                    request={"name": f"{self._secret_name(owner_id, provider)}/versions/latest"}
                )
            except NotFound:
                return None
            return ProviderSecretReference(
                secret=self._secret_id(owner_id, provider),
                version=response.name.rsplit("/", maxsplit=1)[-1],
            )

        return await asyncio.to_thread(resolve)

    async def delete(self, owner_id: str, provider: AIProvider) -> None:
        from google.api_core.exceptions import NotFound

        def delete():
            try:
                self._client.delete_secret(request={"name": self._secret_name(owner_id, provider)})
            except NotFound:
                return

        await asyncio.to_thread(delete)


class ProviderCredentialService:
    def __init__(self, store: ProviderCredentialStore):
        self._store = store

    async def list(self, owner_id: str) -> list[ProviderCredentialResponse]:
        return [await self.get(owner_id, provider) for provider in AIProvider]

    async def get(self, owner_id: str, provider: AIProvider) -> ProviderCredentialResponse:
        api_key = await self._store.read(owner_id, provider)
        return ProviderCredentialResponse(
            provider=provider,
            configured=api_key is not None,
            masked_key=mask_api_key(api_key) if api_key else None,
        )

    async def save(self, owner_id: str, provider: AIProvider, api_key: str) -> ProviderCredentialResponse:
        normalized = api_key.strip()
        if len(normalized) < 8:
            raise AppError(422, "INVALID_PROVIDER_KEY", "The API key must contain at least eight characters")
        await self._store.save(owner_id, provider, normalized)
        return ProviderCredentialResponse(provider=provider, configured=True, masked_key=mask_api_key(normalized))

    async def delete(self, owner_id: str, provider: AIProvider) -> None:
        await self._store.delete(owner_id, provider)

    async def resolve_for_models(self, owner_id: str, models: list[str]) -> dict[str, ProviderSecretReference]:
        required = {provider_for_model(model) for model in models}
        references: dict[str, ProviderSecretReference] = {}
        for provider in required - {None}:
            assert provider is not None
            reference = await self._store.resolve(owner_id, provider)
            if reference is None:
                raise AppError(
                    409,
                    "PROVIDER_KEY_REQUIRED",
                    f"Configure a {provider.value.title()} API key before running this experiment",
                )
            references[provider_environment_name(provider)] = reference
        return references


def provider_for_model(model: str) -> AIProvider | None:
    if model.startswith("openai/"):
        return AIProvider.OPENAI
    if model.startswith("deepseek/"):
        return AIProvider.DEEPSEEK
    if model.startswith(("gemini/", "google/")):
        return AIProvider.GEMINI
    return None


def provider_environment_name(provider: AIProvider) -> str:
    return {
        AIProvider.GEMINI: "GEMINI_API_KEY",
        AIProvider.OPENAI: "OPENAI_API_KEY",
        AIProvider.DEEPSEEK: "DEEPSEEK_API_KEY",
    }[provider]
