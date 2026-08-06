from typing import Protocol

from .schemas import BaselineRunRecord, ExperimentRecord


class ExperimentRepository(Protocol):
    async def create(self, item: ExperimentRecord) -> ExperimentRecord: ...
    async def get(self, experiment_id: str) -> ExperimentRecord | None: ...
    async def save(self, item: ExperimentRecord) -> ExperimentRecord: ...
    async def create_run(self, item: BaselineRunRecord) -> BaselineRunRecord: ...
    async def get_run(self, run_id: str) -> BaselineRunRecord | None: ...
    async def save_run(self, item: BaselineRunRecord) -> BaselineRunRecord: ...


class InMemoryExperimentRepository:
    def __init__(self):
        self.experiments: dict[str, ExperimentRecord] = {}
        self.runs: dict[str, BaselineRunRecord] = {}

    async def create(self, item):
        self.experiments[item.id] = item
        return item

    async def get(self, experiment_id):
        return self.experiments.get(experiment_id)

    async def save(self, item):
        self.experiments[item.id] = item
        return item

    async def create_run(self, item):
        self.runs[item.id] = item
        return item

    async def get_run(self, run_id):
        return self.runs.get(run_id)

    async def save_run(self, item):
        self.runs[item.id] = item
        return item


class FirestoreExperimentRepository:
    def __init__(self, client):
        self.client = client

    def _experiments(self):
        return self.client.collection("experiments")

    def _runs(self):
        return self.client.collection("baseline_runs")

    async def create(self, item):
        await self._experiments().document(item.id).create(item.model_dump(mode="python"))
        return item

    async def get(self, experiment_id):
        snapshot = await self._experiments().document(experiment_id).get()
        return ExperimentRecord.model_validate(snapshot.to_dict()) if snapshot.exists else None

    async def save(self, item):
        await self._experiments().document(item.id).set(item.model_dump(mode="python"))
        return item

    async def create_run(self, item):
        await self._runs().document(item.id).create(item.model_dump(mode="python"))
        return item

    async def get_run(self, run_id):
        snapshot = await self._runs().document(run_id).get()
        return BaselineRunRecord.model_validate(snapshot.to_dict()) if snapshot.exists else None

    async def save_run(self, item):
        await self._runs().document(item.id).set(item.model_dump(mode="python"))
        return item
