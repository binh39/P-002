import io
import zipfile

import pytest

AUTH_HEADERS = {"Authorization": "Bearer dev-token"}


def python_archive() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "sample/calculator.py",
            """def add(left, right):
    return left + right


def subtract(left, right):
    return left - right


class Calculator:
    async def choose(self, value):
        if value > 0:
            return value
        return 0
""",
        )
        archive.writestr("sample/README.md", "ignored")
    return buffer.getvalue()


async def create_project(client, archive: bytes) -> str:
    upload_response = await client.post(
        "/api/v1/uploads",
        headers=AUTH_HEADERS,
        json={
            "filename": "sample.zip",
            "content_type": "application/zip",
            "size_bytes": len(archive),
        },
    )
    upload = upload_response.json()
    await client.put(upload["upload_url"], headers=AUTH_HEADERS, content=archive)
    await client.post(f"/api/v1/uploads/{upload['id']}/complete", headers=AUTH_HEADERS)
    project_response = await client.post(
        "/api/v1/projects",
        headers=AUTH_HEADERS,
        json={"name": "sample", "upload_id": upload["id"]},
    )
    return project_response.json()["id"]


@pytest.mark.asyncio
async def test_project_analysis_lifecycle(client):
    project_id = await create_project(client, python_archive())

    analysis_response = await client.post(
        f"/api/v1/projects/{project_id}/analyze",
        headers=AUTH_HEADERS,
    )

    assert analysis_response.status_code == 202
    assert analysis_response.json()["status"] == "ready"

    project_response = await client.get(f"/api/v1/projects/{project_id}", headers=AUTH_HEADERS)
    project = project_response.json()
    assert project["python_file_count"] == 1
    assert project["function_count"] == 3
    assert project["statement_count"] >= 5
    assert project["branch_count"] == 1
    assert project["analyzed_at"]

    functions_response = await client.get(
        f"/api/v1/projects/{project_id}/functions",
        headers=AUTH_HEADERS,
    )
    functions = functions_response.json()
    assert functions["total"] == 3
    method = next(item for item in functions["items"] if item["name"] == "choose")
    assert method["class_name"] == "Calculator"
    assert method["start_line"] < method["end_line"]
    assert "source" not in method

    source_response = await client.get(
        f"/api/v1/projects/{project_id}/functions/{method['id']}/source",
        headers=AUTH_HEADERS,
    )
    assert source_response.status_code == 200
    assert "async def choose" in source_response.json()["source"]


@pytest.mark.asyncio
async def test_functions_are_unavailable_before_analysis(client):
    project_id = await create_project(client, python_archive())

    response = await client.get(
        f"/api/v1/projects/{project_id}/functions",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ANALYSIS_NOT_READY"


@pytest.mark.asyncio
async def test_internal_worker_requires_task_identity(client):
    response = await client.post("/internal/v1/projects/missing/analyze")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INTERNAL_AUTH_REQUIRED"
