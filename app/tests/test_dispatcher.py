from types import SimpleNamespace

import pytest

from backend.modules.experiments.dispatcher import CloudTasksOptimizationDispatcher


class FakeTasksClient:
    def __init__(self):
        self.parent = None
        self.task = None

    def create_task(self, *, parent, task):
        self.parent = parent
        self.task = task


@pytest.mark.asyncio
async def test_optimization_poll_is_scheduled_without_holding_worker_request():
    dispatcher = CloudTasksOptimizationDispatcher.__new__(CloudTasksOptimizationDispatcher)
    dispatcher.tasks_v2 = SimpleNamespace(HttpMethod=SimpleNamespace(POST="POST"))
    dispatcher.client = FakeTasksClient()
    dispatcher.parent = "projects/p/locations/r/queues/q"
    dispatcher.worker_url = "https://worker.example"
    dispatcher.audience = "https://worker.example"
    dispatcher.service_account_email = "worker@example.iam.gserviceaccount.com"

    await dispatcher.dispatch("run-1", delay_seconds=60)

    assert dispatcher.client.task["http_request"]["url"].endswith("/internal/v1/optimization-runs/run-1/execute")
    assert dispatcher.client.task["schedule_time"].seconds > 0
