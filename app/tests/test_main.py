import pytest


@pytest.mark.asyncio
async def test_unexpected_error_response_keeps_cors_headers(app, client):
    async def fail():
        raise RuntimeError("simulated failure")

    app.add_api_route("/_test/unexpected-error", fail, methods=["GET"])

    response = await client.get(
        "/_test/unexpected-error",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["x-request-id"]
