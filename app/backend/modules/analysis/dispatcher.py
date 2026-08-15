import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol
from uuid import uuid4

from google.protobuf import duration_pb2


class AnalysisDispatcher(Protocol):
    async def dispatch(self, project_id: str) -> None: ...


class InlineAnalysisDispatcher:
    def __init__(self, handler: Callable[[str], Awaitable[None]]):
        self.handler = handler

    async def dispatch(self, project_id: str) -> None:
        await self.handler(project_id)


class CloudTasksAnalysisDispatcher:
    def __init__(
        self,
        project_id: str,
        location: str,
        queue: str,
        worker_url: str,
        audience: str,
        service_account_email: str,
    ):
        from google.cloud import tasks_v2

        self.tasks_v2 = tasks_v2
        self.client = tasks_v2.CloudTasksClient()
        self.parent = self.client.queue_path(project_id, location, queue)
        self.worker_url = worker_url.rstrip("/")
        self.audience = audience
        self.service_account_email = service_account_email

    async def dispatch(self, project_id: str) -> None:
        task = {
            "name": f"{self.parent}/tasks/analysis-{uuid4().hex}",
            "http_request": {
                "http_method": self.tasks_v2.HttpMethod.POST,
                "url": f"{self.worker_url}/internal/v1/projects/{project_id}/analyze",
                "headers": {"Content-Type": "application/json"},
                "oidc_token": {
                    "service_account_email": self.service_account_email,
                    "audience": self.audience,
                },
            },
            "dispatch_deadline": duration_pb2.Duration(seconds=600),
        }
        await asyncio.to_thread(self.client.create_task, parent=self.parent, task=task)
