from enum import StrEnum

from pydantic import Field, SecretStr

from backend.modules.experiments.schemas import StrictModel


class AIProvider(StrEnum):
    GEMINI = "gemini"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"


class ProviderCredentialInput(StrictModel):
    api_key: SecretStr = Field(min_length=8, max_length=512)


class ProviderCredentialResponse(StrictModel):
    provider: AIProvider
    configured: bool
    masked_key: str | None = None


class ProviderCredentialListResponse(StrictModel):
    items: list[ProviderCredentialResponse]


def mask_api_key(value: str) -> str:
    """Expose only enough of a credential for a user to recognize it."""
    if len(value) <= 8:
        return f"{value[:2]}**{value[-2:]}"
    return f"{value[:4]}**{value[-4:]}"
