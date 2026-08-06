import pytest

from tests.test_api.test_analysis import AUTH_HEADERS, create_project, python_archive


@pytest.mark.asyncio
async def test_create_experiment_and_queue_baseline(client):
    project_id = await create_project(client, python_archive())
    await client.post(f"/api/v1/projects/{project_id}/analyze", headers=AUTH_HEADERS)
    functions = (await client.get(f"/api/v1/projects/{project_id}/functions", headers=AUTH_HEADERS)).json()["items"]

    created = await client.post(
        "/api/v1/experiments",
        headers=AUTH_HEADERS,
        json={"project_id": project_id, "name": "Calculator baseline", "target_function_ids": [functions[0]["id"]]},
    )
    assert created.status_code == 201
    experiment = created.json()
    assert experiment["status"] == "draft"

    queued = await client.post(f"/api/v1/experiments/{experiment['id']}/runs", headers=AUTH_HEADERS)
    assert queued.status_code == 202
    run = queued.json()
    assert run["target_count"] == 1
    # The inline development worker refuses to execute user Python in the API container.
    assert run["status"] == "failed"
    assert run["error_message"] == "Baseline sandbox is not configured"

    fetched = await client.get(f"/api/v1/experiments/runs/{run['id']}", headers=AUTH_HEADERS)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == run["id"]


@pytest.mark.asyncio
async def test_experiment_requires_analyzed_project(client):
    project_id = await create_project(client, python_archive())
    response = await client.post(
        "/api/v1/experiments",
        headers=AUTH_HEADERS,
        json={"project_id": project_id, "name": "Blocked", "target_function_ids": ["missing"]},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ANALYSIS_NOT_READY"
