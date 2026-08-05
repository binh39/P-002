import pytest

AUTH_HEADERS = {"Authorization": "Bearer dev-token"}


@pytest.mark.asyncio
async def test_projects_require_authentication(client):
    response = await client.get("/api/v1/projects")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_upload_and_project_lifecycle(client):
    archive = b"PK\x03\x04mock-zip-content"
    upload_response = await client.post(
        "/api/v1/uploads",
        headers=AUTH_HEADERS,
        json={
            "filename": "isort.zip",
            "content_type": "application/zip",
            "size_bytes": len(archive),
        },
    )
    assert upload_response.status_code == 201
    upload = upload_response.json()
    assert upload["status"] == "pending"
    assert upload["method"] == "PUT"

    content_response = await client.put(upload["upload_url"], headers=AUTH_HEADERS, content=archive)
    assert content_response.status_code == 204

    completed_response = await client.post(
        f"/api/v1/uploads/{upload['id']}/complete",
        headers=AUTH_HEADERS,
    )
    assert completed_response.status_code == 200
    assert completed_response.json()["status"] == "uploaded"

    create_response = await client.post(
        "/api/v1/projects",
        headers=AUTH_HEADERS,
        json={
            "name": "isort",
            "description": "Import sorting reference project",
            "upload_id": upload["id"],
            "branch": "main",
            "commit": "9262aa8",
        },
    )
    assert create_response.status_code == 201
    project = create_response.json()
    assert project["status"] == "uploaded"
    assert project["settings"]["runtime"]["python_version"] == "3.11"

    list_response = await client.get("/api/v1/projects", headers=AUTH_HEADERS)
    assert list_response.status_code == 200
    assert list_response.json()["total"] >= 1

    patch_response = await client.patch(
        f"/api/v1/projects/{project['id']}/settings",
        headers=AUTH_HEADERS,
        json={"runtime": {"python_version": "3.12", "memory_mb": 4096}},
    )
    assert patch_response.status_code == 200
    settings = patch_response.json()["settings"]
    assert settings["runtime"]["python_version"] == "3.12"
    assert settings["runtime"]["memory_mb"] == 4096
    assert settings["runtime"]["cpu"] == 1


@pytest.mark.asyncio
async def test_project_rejects_pending_upload(client):
    response = await client.post(
        "/api/v1/uploads",
        headers=AUTH_HEADERS,
        json={"filename": "pending.zip", "content_type": "application/zip", "size_bytes": 20},
    )
    upload_id = response.json()["id"]

    project_response = await client.post(
        "/api/v1/projects",
        headers=AUTH_HEADERS,
        json={"name": "pending", "upload_id": upload_id},
    )

    assert project_response.status_code == 409
    assert project_response.json()["error"]["code"] == "UPLOAD_NOT_READY"


@pytest.mark.asyncio
async def test_upload_validation_uses_error_envelope(client):
    response = await client.post(
        "/api/v1/uploads",
        headers=AUTH_HEADERS,
        json={"filename": "source.tar", "content_type": "application/zip", "size_bytes": 10},
    )

    assert response.status_code == 422
    payload = response.json()["error"]
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["request_id"]
