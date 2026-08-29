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


def excluded():  # pragma: no cover
    return None


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
    # coverage.py counts the two outgoing arcs of the ``if``.
    assert project["branch_count"] == 2
    assert project["analyzed_at"]

    functions_response = await client.get(
        f"/api/v1/projects/{project_id}/functions",
        headers=AUTH_HEADERS,
    )
    functions = functions_response.json()
    assert functions["total"] == 3
    assert {item["name"] for item in functions["items"]} == {"add", "subtract", "choose"}
    method = next(item for item in functions["items"] if item["name"] == "choose")
    assert method["statements"] == 3
    assert method["branches"] == 2
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
async def test_analysis_routes_project_to_python_minor_required_by_pyproject(client):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "project-main/pyproject.toml",
            '[project]\nname = "python-313-project"\nrequires-python = ">=3.13"\n',
        )
        archive.writestr("project-main/src/example.py", "def value():\n    return 1\n")
    project_id = await create_project(client, buffer.getvalue())

    response = await client.post(f"/api/v1/projects/{project_id}/analyze", headers=AUTH_HEADERS)

    assert response.status_code == 202
    assert response.json()["settings"]["runtime"]["python_version"] == "3.13"


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


@pytest.mark.asyncio
async def test_analysis_failure_is_persisted_for_the_project_page(client):
    project_id = await create_project(client, b"not a zip archive")

    response = await client.post(f"/api/v1/projects/{project_id}/analyze", headers=AUTH_HEADERS)

    assert response.status_code == 202
    assert response.json()["status"] == "failed"
    assert response.json()["analysis_error"] == "The uploaded source archive is not a valid ZIP file"


@pytest.mark.asyncio
async def test_imported_project_can_be_deleted_with_its_functions(client, app):
    project_id = await create_project(client, python_archive())
    await client.post(f"/api/v1/projects/{project_id}/analyze", headers=AUTH_HEADERS)
    assert await app.state.services.analysis.functions.list_for_project(project_id)

    response = await client.delete(f"/api/v1/projects/{project_id}", headers=AUTH_HEADERS)

    assert response.status_code == 204
    assert (await client.get(f"/api/v1/projects/{project_id}", headers=AUTH_HEADERS)).status_code == 404
    assert await app.state.services.analysis.functions.list_for_project(project_id) == []


@pytest.mark.asyncio
async def test_bundled_sample_project_cannot_be_deleted(client):
    samples = await client.get("/api/v1/projects/samples", headers=AUTH_HEADERS)
    sample_id = samples.json()["items"][0]["id"]

    response = await client.delete(f"/api/v1/projects/{sample_id}", headers=AUTH_HEADERS)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SAMPLE_PROJECT_READ_ONLY"
