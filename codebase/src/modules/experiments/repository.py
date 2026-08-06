from datetime import datetime
from typing import Protocol

from .schemas import (
    BaselineRunRecord,
    ComparisonRunRecord,
    ExperimentRecord,
    OptimizationRunRecord,
    PromptVersionRecord,
)


class ExperimentRepository(Protocol):
    async def create(self, item: ExperimentRecord) -> ExperimentRecord: ...
    async def get(self, experiment_id: str) -> ExperimentRecord | None: ...
    async def save(self, item: ExperimentRecord) -> ExperimentRecord: ...
    async def create_run(self, item: BaselineRunRecord) -> BaselineRunRecord: ...
    async def get_run(self, run_id: str) -> BaselineRunRecord | None: ...
    async def save_run(self, item: BaselineRunRecord) -> BaselineRunRecord: ...
    async def create_optimization_run(self, item: OptimizationRunRecord) -> OptimizationRunRecord: ...
    async def get_optimization_run(self, run_id: str) -> OptimizationRunRecord | None: ...
    async def save_optimization_run(self, item: OptimizationRunRecord) -> OptimizationRunRecord: ...
    async def create_comparison_run(self, item: ComparisonRunRecord) -> ComparisonRunRecord: ...
    async def get_comparison_run(self, run_id: str) -> ComparisonRunRecord | None: ...
    async def save_comparison_run(self, item: ComparisonRunRecord) -> ComparisonRunRecord: ...
    async def create_prompt_version(self, item: PromptVersionRecord) -> PromptVersionRecord: ...
    async def get_prompt_version(self, version_id: str) -> PromptVersionRecord | None: ...
    async def save_prompt_version(self, item: PromptVersionRecord) -> PromptVersionRecord: ...
    async def decide_prompt_version(
        self, version_id: str, decision: str, reviewer_id: str, comment: str, reviewed_at: datetime
    ) -> PromptVersionRecord | None: ...


class InMemoryExperimentRepository:
    def __init__(self):
        self.experiments: dict[str, ExperimentRecord] = {}
        self.runs: dict[str, BaselineRunRecord] = {}
        self.optimization_runs: dict[str, OptimizationRunRecord] = {}
        self.comparison_runs: dict[str, ComparisonRunRecord] = {}
        self.prompt_versions: dict[str, PromptVersionRecord] = {}

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

    async def create_optimization_run(self, item):
        self.optimization_runs[item.id] = item
        return item

    async def get_optimization_run(self, run_id):
        return self.optimization_runs.get(run_id)

    async def save_optimization_run(self, item):
        self.optimization_runs[item.id] = item
        return item

    async def create_comparison_run(self, item):
        self.comparison_runs[item.id] = item
        return item

    async def get_comparison_run(self, run_id):
        return self.comparison_runs.get(run_id)

    async def save_comparison_run(self, item):
        self.comparison_runs[item.id] = item
        return item

    async def create_prompt_version(self, item):
        self.prompt_versions[item.id] = item
        return item

    async def get_prompt_version(self, version_id):
        return self.prompt_versions.get(version_id)

    async def save_prompt_version(self, item):
        self.prompt_versions[item.id] = item
        return item

    async def decide_prompt_version(self, version_id, decision, reviewer_id, comment, reviewed_at):
        item = self.prompt_versions.get(version_id)
        if item is None or item.status != "in_review":
            return item
        item.status = decision
        item.reviewer_id = reviewer_id
        item.review_comment = comment
        item.reviewed_at = reviewed_at
        self.prompt_versions[item.id] = item
        return item


class FirestoreExperimentRepository:
    def __init__(self, client):
        self.client = client

    def _experiments(self):
        return self.client.collection("experiments")

    def _runs(self):
        return self.client.collection("baseline_runs")

    def _optimization_runs(self):
        return self.client.collection("optimization_runs")

    def _comparison_runs(self):
        return self.client.collection("comparison_runs")

    def _prompt_versions(self):
        return self.client.collection("prompt_versions")

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

    async def create_optimization_run(self, item):
        await self._optimization_runs().document(item.id).create(item.model_dump(mode="python"))
        return item

    async def get_optimization_run(self, run_id):
        snapshot = await self._optimization_runs().document(run_id).get()
        return OptimizationRunRecord.model_validate(snapshot.to_dict()) if snapshot.exists else None

    async def save_optimization_run(self, item):
        await self._optimization_runs().document(item.id).set(item.model_dump(mode="python"))
        return item

    async def create_comparison_run(self, item):
        await self._comparison_runs().document(item.id).create(item.model_dump(mode="python"))
        return item

    async def get_comparison_run(self, run_id):
        snapshot = await self._comparison_runs().document(run_id).get()
        return ComparisonRunRecord.model_validate(snapshot.to_dict()) if snapshot.exists else None

    async def save_comparison_run(self, item):
        await self._comparison_runs().document(item.id).set(item.model_dump(mode="python"))
        return item

    async def create_prompt_version(self, item):
        await self._prompt_versions().document(item.id).create(item.model_dump(mode="python"))
        return item

    async def get_prompt_version(self, version_id):
        snapshot = await self._prompt_versions().document(version_id).get()
        return PromptVersionRecord.model_validate(snapshot.to_dict()) if snapshot.exists else None

    async def save_prompt_version(self, item):
        await self._prompt_versions().document(item.id).set(item.model_dump(mode="python"))
        return item

    async def decide_prompt_version(self, version_id, decision, reviewer_id, comment, reviewed_at):
        from google.cloud.firestore_v1.async_transaction import async_transactional

        reference = self._prompt_versions().document(version_id)
        transaction = self.client.transaction()

        @async_transactional
        async def decide(transaction):
            snapshot = await reference.get(transaction=transaction)
            if not snapshot.exists:
                return None
            item = PromptVersionRecord.model_validate(snapshot.to_dict())
            if item.status != "in_review":
                return item
            item.status = decision
            item.reviewer_id = reviewer_id
            item.review_comment = comment
            item.reviewed_at = reviewed_at
            transaction.set(reference, item.model_dump(mode="python"))
            return item

        return await decide(transaction)
