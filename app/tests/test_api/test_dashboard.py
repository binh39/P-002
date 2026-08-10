import pytest


@pytest.mark.asyncio
async def test_dashboard_endpoint_returns_owner_scoped_empty_snapshot(client):
    response = await client.get(
        "/api/v1/dashboard",
        headers={"Authorization": "Bearer dev-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_name"] == "Prompt research"
    assert payload["experiments"] == []
    assert payload["coverage"] == []
    assert payload["kpis"][0]["value"] == "0"
    assert payload["quick_stats"][1] == {"label": "Metric calls", "value": "0"}
