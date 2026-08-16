r"""Print five deterministic, sanitized API evaluation cases.

Run from the repository root:
    .\.venv\Scripts\python.exe eval\run_local_api_evidence.py

The script uses the ASGI app directly. It does not call Vertex AI or mutate
production state.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from httpx import ASGITransport, AsyncClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from backend.config import Settings  # noqa: E402
from backend.main import create_app  # noqa: E402


def compact_error(payload: dict) -> dict:
    error = payload["error"]
    return {key: error[key] for key in ("code", "message")}


async def main() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        log_level="ERROR",
        auth_mode="disabled",
        repository_backend="memory",
        storage_backend="local",
        local_upload_dir=str(ROOT / "eval" / ".local-api-evidence-uploads"),
        sample_repos_dir=str(ROOT / "src" / "sample_repo"),
    )
    app = create_app(settings)
    transport = ASGITransport(app=app)
    auth = {"Authorization": "Bearer dev-token"}
    cases = []

    async with AsyncClient(transport=transport, base_url="http://local-eval") as client:
        response = await client.get("/health")
        cases.append(
            {
                "id": "health",
                "request": "GET /health",
                "status": response.status_code,
                "output": response.json(),
            }
        )

        response = await client.get("/api/v1/projects")
        cases.append(
            {
                "id": "authentication-required",
                "request": "GET /api/v1/projects (no bearer token)",
                "status": response.status_code,
                "output": {"error": compact_error(response.json())},
            }
        )

        response = await client.get("/api/v1/projects/samples", headers=auth)
        sample_payload = response.json()
        cases.append(
            {
                "id": "sample-catalog",
                "request": "GET /api/v1/projects/samples",
                "status": response.status_code,
                "output": {
                    "total": sample_payload["total"],
                    "ids": [item["id"] for item in sample_payload["items"]],
                    "statuses": [item["status"] for item in sample_payload["items"]],
                },
            }
        )

        response = await client.get("/api/v1/dashboard", headers=auth)
        dashboard_payload = response.json()
        cases.append(
            {
                "id": "empty-dashboard",
                "request": "GET /api/v1/dashboard",
                "status": response.status_code,
                "output": {
                    "project_name": dashboard_payload["project_name"],
                    "experiments": dashboard_payload["experiments"],
                    "coverage": dashboard_payload["coverage"],
                    "first_kpi": dashboard_payload["kpis"][0],
                },
            }
        )

        response = await client.post(
            "/api/v1/experiments",
            headers=auth,
            json={
                "project_ids": ["sample:isort"],
                "name": "Invalid prompt evidence",
                "max_targets": 3,
                "baseline_prompt": {
                    "initial": "No required placeholders",
                    "error": "Failure: {error}",
                },
            },
        )
        cases.append(
            {
                "id": "invalid-baseline-prompt",
                "request": "POST /api/v1/experiments (invalid baseline placeholders)",
                "status": response.status_code,
                "output": {"error": compact_error(response.json())},
            }
        )

    print(
        json.dumps(
            {
                "schema_version": 1,
                "scope": "local ASGI integration; no live LLM calls",
                "case_count": len(cases),
                "cases": cases,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
