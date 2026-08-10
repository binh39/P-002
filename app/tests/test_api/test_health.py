import pytest


@pytest.mark.asyncio
async def test_health_endpoints(client):
    for path in ("/health", "/api/v1/health"):
        response = await client.get(path)
        assert response.status_code == 200
        assert response.json()["service"] == "promptopt-api"
