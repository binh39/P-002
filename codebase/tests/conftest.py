import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.config import Settings
from src.main import create_app


@pytest_asyncio.fixture
async def client(tmp_path):
    settings = Settings(
        _env_file=None,
        app_env="test",
        auth_mode="disabled",
        repository_backend="memory",
        storage_backend="local",
        local_upload_dir=str(tmp_path / "uploads"),
    )
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
