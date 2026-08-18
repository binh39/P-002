import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4

from google.protobuf import duration_pb2, timestamp_pb2


class OptimizationDispatcher(Protocol):
    async def dispatch(self, run_id: str, delay_seconds: int = 0) -> None: ...


class ComparisonDispatcher(Protocol):
    async def dispatch(self, run_id: str) -> None: ...


class TestGenerationDispatcher(Protocol):
    async def dispatch(self, run_id: str, delay_seconds: int = 0) -> None: ...


class InlineOptimizationDispatcher:
    def __init__(self, handler: Callable[[str], Awaitable[None]]):
        self.handler = handler

    async def dispatch(self, run_id: str, delay_seconds: int = 0) -> None:
        if delay_seconds:
            await asyncio.sleep(delay_seconds)
        await self.handler(run_id)


class InlineComparisonDispatcher:
    def __init__(self, handler: Callable[[str], Awaitable[None]]):
        self.handler = handler

    async def dispatch(self, run_id: str) -> None:
        await self.handler(run_id)


class InlineTestGenerationDispatcher:
    def __init__(self, handler: Callable[[str], Awaitable[None]]):
        self.handler = handler

    async def dispatch(self, run_id: str, delay_seconds: int = 0) -> None:
        if delay_seconds:
            await asyncio.sleep(delay_seconds)
        await self.handler(run_id)


class CloudTasksOptimizationDispatcher:
    def __init__(self, project_id, location, queue, worker_url, audience, service_account_email):
        from google.cloud import tasks_v2

        self.tasks_v2, self.client = tasks_v2, tasks_v2.CloudTasksClient()
        self.parent = self.client.queue_path(project_id, location, queue)
        self.worker_url, self.audience, self.service_account_email = (
            worker_url.rstrip("/"),
            audience,
            service_account_email,
        )

    async def dispatch(self, run_id: str, delay_seconds: int = 0) -> None:
        task = {
            "name": f"{self.parent}/tasks/optimization-{uuid4().hex}",
            "http_request": {
                "http_method": self.tasks_v2.HttpMethod.POST,
                "url": f"{self.worker_url}/internal/v1/optimization-runs/{run_id}/execute",
                "headers": {"Content-Type": "application/json"},
                "oidc_token": {"service_account_email": self.service_account_email, "audience": self.audience},
            },
            "dispatch_deadline": duration_pb2.Duration(seconds=1800),
        }
        if delay_seconds:
            schedule_time = timestamp_pb2.Timestamp()
            schedule_time.FromDatetime(datetime.now(UTC) + timedelta(seconds=delay_seconds))
            task["schedule_time"] = schedule_time
        await asyncio.to_thread(self.client.create_task, parent=self.parent, task=task)


class CloudTasksComparisonDispatcher:
    def __init__(self, project_id, location, queue, worker_url, audience, service_account_email):
        from google.cloud import tasks_v2

        self.tasks_v2, self.client = tasks_v2, tasks_v2.CloudTasksClient()
        self.parent = self.client.queue_path(project_id, location, queue)
        self.worker_url, self.audience, self.service_account_email = (
            worker_url.rstrip("/"),
            audience,
            service_account_email,
        )

    async def dispatch(self, run_id: str) -> None:
        task = {
            "name": f"{self.parent}/tasks/comparison-{uuid4().hex}",
            "http_request": {
                "http_method": self.tasks_v2.HttpMethod.POST,
                "url": f"{self.worker_url}/internal/v1/comparison-runs/{run_id}/execute",
                "headers": {"Content-Type": "application/json"},
                "oidc_token": {"service_account_email": self.service_account_email, "audience": self.audience},
            },
            "dispatch_deadline": duration_pb2.Duration(seconds=1800),
        }
        await asyncio.to_thread(self.client.create_task, parent=self.parent, task=task)


class CloudTasksTestGenerationDispatcher:
    """Queue final user-requested test generation; GEPA work never uses this route."""

    def __init__(self, project_id, location, queue, worker_url, audience, service_account_email):
        from google.cloud import tasks_v2

        self.tasks_v2, self.client = tasks_v2, tasks_v2.CloudTasksClient()
        self.parent = self.client.queue_path(project_id, location, queue)
        self.worker_url, self.audience, self.service_account_email = (
            worker_url.rstrip("/"),
            audience,
            service_account_email,
        )

    async def dispatch(self, run_id: str, delay_seconds: int = 0) -> None:
        task = {
            "name": f"{self.parent}/tasks/test-generation-{uuid4().hex}",
            "http_request": {
                "http_method": self.tasks_v2.HttpMethod.POST,
                "url": f"{self.worker_url}/internal/v1/test-generation-runs/{run_id}/execute",
                "headers": {"Content-Type": "application/json"},
                "oidc_token": {"service_account_email": self.service_account_email, "audience": self.audience},
            },
            "dispatch_deadline": duration_pb2.Duration(seconds=1800),
        }
        if delay_seconds:
            schedule_time = timestamp_pb2.Timestamp()
            schedule_time.FromDatetime(datetime.now(UTC) + timedelta(seconds=delay_seconds))
            task["schedule_time"] = schedule_time
        await asyncio.to_thread(self.client.create_task, parent=self.parent, task=task)
