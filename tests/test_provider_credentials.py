import asyncio
import sys
from pathlib import Path

from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from backend.config import Settings
from backend.main import create_app
from backend.modules.providers.schemas import AIProvider, mask_api_key
from backend.modules.providers.service import InMemoryProviderCredentialStore, ProviderCredentialService


def test_mask_api_key_keeps_only_first_and_last_four_characters():
    assert mask_api_key("sk-abcdefgh1234") == "sk-a**1234"


def test_provider_credentials_are_isolated_per_owner_and_resolve_for_models():
    async def exercise():
        service = ProviderCredentialService(InMemoryProviderCredentialStore())
        saved = await service.save("owner-a", AIProvider.OPENAI, "sk-abcdefgh1234")

        assert saved.configured is True
        assert saved.masked_key == "sk-a**1234"
        assert (await service.get("owner-b", AIProvider.OPENAI)).configured is False
        refs = await service.resolve_for_models("owner-a", ["openai/gpt-5-mini", "vertex_ai/gemini-3.6-flash"])
        assert refs["OPENAI_API_KEY"].secret == "local-openai"

        await service.delete("owner-a", AIProvider.OPENAI)
        assert (await service.get("owner-a", AIProvider.OPENAI)).configured is False

    asyncio.run(exercise())


def test_provider_credential_api_never_returns_the_raw_key():
    async def exercise():
        app = create_app(Settings(app_env="test", auth_mode="disabled"))
        transport = ASGITransport(app=app)
        headers = {"Authorization": "Bearer dev-token"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            saved = await client.put(
                "/api/v1/provider-credentials/openai",
                headers=headers,
                json={"api_key": "sk-abcdefgh1234"},
            )
            assert saved.status_code == 200
            assert saved.json()["masked_key"] == "sk-a**1234"

            listed = await client.get("/api/v1/provider-credentials", headers=headers)
            assert listed.status_code == 200
            assert listed.json()["items"] == [
                {"provider": "gemini", "configured": False, "masked_key": None},
                {"provider": "openai", "configured": True, "masked_key": "sk-a**1234"},
                {"provider": "deepseek", "configured": False, "masked_key": None},
            ]

    asyncio.run(exercise())
