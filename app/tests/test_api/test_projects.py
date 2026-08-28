import pytest

AUTH_HEADERS = {"Authorization": "Bearer dev-token"}


@pytest.mark.asyncio
async def test_projects_require_authentication(client):
    response = await client.get("/api/v1/projects")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_sample_catalog_creates_experiment_without_persisting_projects(client):
    samples_response = await client.get("/api/v1/projects/samples", headers=AUTH_HEADERS)

    assert samples_response.status_code == 200
    samples = samples_response.json()["items"]
    assert [item["id"] for item in samples] == [
        "sample:isort",
        "sample:mimesis",
        "sample:mlxtend",
        "sample:typesystem",
    ]
    assert all(item["status"] in {"ready", "warning"} for item in samples)

    functions_response = await client.get(
        "/api/v1/projects/sample:isort/functions",
        headers=AUTH_HEADERS,
    )
    assert functions_response.status_code == 200
    functions = functions_response.json()["items"]
    assert len(functions) >= 3
    assert all(item["project_id"] == "sample:isort" for item in functions)
    assert all("/_vendored/" not in f"/{item['file']}" for item in functions)
    assert all("/deprecated/" not in f"/{item['file']}" for item in functions)

    mimesis_response = await client.get(
        "/api/v1/projects/sample:mimesis/functions",
        headers=AUTH_HEADERS,
    )
    assert mimesis_response.status_code == 200
    mimesis_functions = mimesis_response.json()["items"]
    assert len(mimesis_functions) == 389
    assert all(item["project_id"] == "sample:mimesis" for item in mimesis_functions)

    created = await client.post(
        "/api/v1/experiments",
        headers=AUTH_HEADERS,
        json={
            "project_ids": ["sample:isort"],
            "name": "Bundled isort experiment",
            "max_targets": 3,
        },
    )
    assert created.status_code == 201
    assert created.json()["project_id"] == "sample:isort"
    assert created.json()["optimization_eligible"] is True

    persisted_projects = await client.get("/api/v1/projects", headers=AUTH_HEADERS)
    assert persisted_projects.status_code == 200
    assert persisted_projects.json()["total"] == 0

    read_only = await client.patch(
        "/api/v1/projects/sample:isort/settings",
        headers=AUTH_HEADERS,
        json={"runtime": {"memory_mb": 4096}},
    )
    assert read_only.status_code == 409
    assert read_only.json()["error"]["code"] == "SAMPLE_PROJECT_READ_ONLY"


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
    assert project["settings"]["runtime"]["python_version"] == "3.12"

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
async def test_runtime_labels_allow_projects_with_different_python_versions(client):
    async def upload(name: str) -> dict:
        archive = f"{name}-archive".encode()
        created = await client.post(
            "/api/v1/uploads",
            headers=AUTH_HEADERS,
            json={"filename": f"{name}.zip", "content_type": "application/zip", "size_bytes": len(archive)},
        )
        upload = created.json()
        await client.put(upload["upload_url"], headers=AUTH_HEADERS, content=archive)
        completed = await client.post(f"/api/v1/uploads/{upload['id']}/complete", headers=AUTH_HEADERS)
        assert completed.status_code == 200
        return upload

    first_upload = await upload("python312")
    first = await client.post(
        "/api/v1/projects",
        headers=AUTH_HEADERS,
        json={"name": "python312", "upload_id": first_upload["id"], "branch": "main"},
    )
    assert first.status_code == 201
    first_project = first.json()

    second_upload = await upload("python311")
    second = await client.post(
        "/api/v1/projects",
        headers=AUTH_HEADERS,
        json={
            "name": "python311",
            "upload_id": second_upload["id"],
            "branch": "main",
            "runtime_environment_id": first_project["runtime_environment_id"],
            "settings": {"runtime": {"python_version": "3.11"}},
        },
    )

    assert second.status_code == 201, second.text
    assert second.json()["runtime_environment_id"] == first_project["runtime_environment_id"]
    assert second.json()["settings"]["runtime"]["python_version"] == "3.11"


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
