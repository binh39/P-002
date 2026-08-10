import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.config import Settings
from backend.main import create_app


@pytest.fixture
def app(tmp_path):
    settings = Settings(
        _env_file=None,
        app_env="test",
        auth_mode="disabled",
        repository_backend="memory",
        storage_backend="local",
        local_upload_dir=str(tmp_path / "uploads"),
    )
    return create_app(settings)


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
