from datetime import datetime
from typing import Protocol

from .schemas import (
    BaselineRunRecord,
    ComparisonRunRecord,
    ExperimentRecord,
    OptimizationRunRecord,
    PromptRole,
    PromptSnapshotRecord,
    PromptVersionRecord,
    TestGenerationRunRecord,
)


class ExperimentRepository(Protocol):
    async def create(self, item: ExperimentRecord) -> ExperimentRecord: ...
    async def get(self, experiment_id: str) -> ExperimentRecord | None: ...
    async def list_for_owner(self, owner_id: str) -> list[ExperimentRecord]: ...
    async def list_for_workspace(self, workspace_id: str) -> list[ExperimentRecord]: ...
    async def save(self, item: ExperimentRecord) -> ExperimentRecord: ...
    async def delete(self, experiment_id: str) -> None: ...
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
    async def list_prompt_versions_for_workspace(
        self, workspace_id: str, status: str | None = None
    ) -> list[PromptVersionRecord]: ...
    async def decide_prompt_version(
        self, version_id: str, decision: str, reviewer_id: str, comment: str, reviewed_at: datetime
    ) -> PromptVersionRecord | None: ...
    async def create_prompt_snapshot(self, item: PromptSnapshotRecord) -> PromptSnapshotRecord: ...
    async def get_prompt_snapshot(self, experiment_id: str, role: PromptRole) -> PromptSnapshotRecord | None: ...
    async def list_prompt_snapshots(self, experiment_id: str) -> list[PromptSnapshotRecord]: ...
    async def create_test_generation_run(self, item: TestGenerationRunRecord) -> TestGenerationRunRecord: ...
    async def get_test_generation_run(self, run_id: str) -> TestGenerationRunRecord | None: ...
    async def delete_test_generation_run(self, run_id: str) -> None: ...
    async def save_test_generation_run(self, item: TestGenerationRunRecord) -> TestGenerationRunRecord: ...
    async def list_test_generation_runs_for_owner(self, owner_id: str) -> list[TestGenerationRunRecord]: ...
    async def list_test_generation_runs_for_workspace(self, workspace_id: str) -> list[TestGenerationRunRecord]: ...


class InMemoryExperimentRepository:
    def __init__(self):
        self.experiments: dict[str, ExperimentRecord] = {}
        self.runs: dict[str, BaselineRunRecord] = {}
        self.optimization_runs: dict[str, OptimizationRunRecord] = {}
        self.comparison_runs: dict[str, ComparisonRunRecord] = {}
        self.prompt_versions: dict[str, PromptVersionRecord] = {}
        self.prompt_snapshots: dict[str, PromptSnapshotRecord] = {}
        self.test_generation_runs: dict[str, TestGenerationRunRecord] = {}

    async def create(self, item):
        self.experiments[item.id] = item
        return item

    async def get(self, experiment_id):
        return self.experiments.get(experiment_id)

    async def list_for_owner(self, owner_id):
        return sorted(
            (item for item in self.experiments.values() if item.owner_id == owner_id),
            key=lambda item: item.created_at,
            reverse=True,
        )

    async def list_for_workspace(self, workspace_id):
        return sorted(
            (item for item in self.experiments.values() if item.workspace_id == workspace_id),
            key=lambda item: item.created_at,
            reverse=True,
        )

    async def save(self, item):
        self.experiments[item.id] = item
        return item

    async def delete(self, experiment_id):
        self.experiments.pop(experiment_id, None)
        self.runs = {key: item for key, item in self.runs.items() if item.experiment_id != experiment_id}
        self.optimization_runs = {
            key: item for key, item in self.optimization_runs.items() if item.experiment_id != experiment_id
        }
        self.comparison_runs = {
            key: item for key, item in self.comparison_runs.items() if item.experiment_id != experiment_id
        }
        self.prompt_versions = {
            key: item for key, item in self.prompt_versions.items() if item.experiment_id != experiment_id
        }
        self.prompt_snapshots = {
            key: item for key, item in self.prompt_snapshots.items() if item.experiment_id != experiment_id
        }
        self.test_generation_runs = {
            key: item for key, item in self.test_generation_runs.items() if item.experiment_id != experiment_id
        }

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

    async def list_prompt_versions_for_workspace(self, workspace_id, status=None):
        return sorted(
            (
                item
                for item in self.prompt_versions.values()
                if item.workspace_id == workspace_id and (status is None or item.status == status)
            ),
            key=lambda item: item.created_at,
            reverse=True,
        )

    async def decide_prompt_version(self, version_id, decision, reviewer_id, comment, reviewed_at):
        item = self.prompt_versions.get(version_id)
        if item is None or item.status != "in_review":
            return item
        item.status = decision
        item.reviewer_id = reviewer_id
        item.review_comment = comment
        item.reviewed_at = reviewed_at
        item.decision = decision
        item.baseline_digest_at_review = item.parent_prompt_digest
        item.candidate_digest_at_review = item.prompt_digest
        self.prompt_versions[item.id] = item
        return item

    async def create_prompt_snapshot(self, item):
        if item.id in self.prompt_snapshots:
            raise ValueError(f"Prompt snapshot already exists: {item.id}")
        self.prompt_snapshots[item.id] = item
        return item

    async def get_prompt_snapshot(self, experiment_id, role):
        return self.prompt_snapshots.get(_prompt_snapshot_id(experiment_id, role))

    async def list_prompt_snapshots(self, experiment_id):
        return sorted(
            (item for item in self.prompt_snapshots.values() if item.experiment_id == experiment_id),
            key=lambda item: item.created_at,
        )

    async def create_test_generation_run(self, item):
        if item.id in self.test_generation_runs:
            raise ValueError(f"Test generation run already exists: {item.id}")
        self.test_generation_runs[item.id] = item
        return item

    async def get_test_generation_run(self, run_id):
        return self.test_generation_runs.get(run_id)

    async def delete_test_generation_run(self, run_id):
        self.test_generation_runs.pop(run_id, None)

    async def save_test_generation_run(self, item):
        self.test_generation_runs[item.id] = item
        return item

    async def list_test_generation_runs_for_owner(self, owner_id):
        return sorted(
            (item for item in self.test_generation_runs.values() if item.owner_id == owner_id),
            key=lambda item: item.created_at,
            reverse=True,
        )

    async def list_test_generation_runs_for_workspace(self, workspace_id):
        return sorted(
            (item for item in self.test_generation_runs.values() if item.workspace_id == workspace_id),
            key=lambda item: item.created_at,
            reverse=True,
        )


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

    def _prompt_snapshots(self):
        return self.client.collection("prompt_snapshots")

    def _test_generation_runs(self):
        return self.client.collection("test_generation_runs")

    async def create(self, item):
        await self._experiments().document(item.id).create(item.model_dump(mode="python"))
        return item

    async def get(self, experiment_id):
        snapshot = await self._experiments().document(experiment_id).get()
        return ExperimentRecord.model_validate(snapshot.to_dict()) if snapshot.exists else None

    async def list_for_owner(self, owner_id):
        from google.cloud.firestore_v1.base_query import FieldFilter

        snapshots = self._experiments().where(filter=FieldFilter("owner_id", "==", owner_id)).stream()
        items = [ExperimentRecord.model_validate(snapshot.to_dict()) async for snapshot in snapshots]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    async def list_for_workspace(self, workspace_id):
        from google.cloud.firestore_v1.base_query import FieldFilter

        snapshots = self._experiments().where(filter=FieldFilter("workspace_id", "==", workspace_id)).stream()
        items = [ExperimentRecord.model_validate(snapshot.to_dict()) async for snapshot in snapshots]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    async def save(self, item):
        await self._experiments().document(item.id).set(item.model_dump(mode="python"))
        return item

    async def delete(self, experiment_id):
        from google.cloud.firestore_v1.base_query import FieldFilter

        references = [self._experiments().document(experiment_id)]
        for collection in (
            self._runs(),
            self._optimization_runs(),
            self._comparison_runs(),
            self._prompt_versions(),
            self._prompt_snapshots(),
            self._test_generation_runs(),
        ):
            snapshots = collection.where(filter=FieldFilter("experiment_id", "==", experiment_id)).stream()
            references.extend([snapshot.reference async for snapshot in snapshots])
        for offset in range(0, len(references), 400):
            batch = self.client.batch()
            for reference in references[offset : offset + 400]:
                batch.delete(reference)
            await batch.commit()

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

    async def list_prompt_versions_for_workspace(self, workspace_id, status=None):
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self._prompt_versions().where(filter=FieldFilter("workspace_id", "==", workspace_id))
        if status is not None:
            query = query.where(filter=FieldFilter("status", "==", status))
        snapshots = query.stream()
        return sorted(
            [PromptVersionRecord.model_validate(snapshot.to_dict()) async for snapshot in snapshots],
            key=lambda item: item.created_at,
            reverse=True,
        )

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
            item.decision = decision
            item.baseline_digest_at_review = item.parent_prompt_digest
            item.candidate_digest_at_review = item.prompt_digest
            transaction.set(reference, item.model_dump(mode="python"))
            return item

        return await decide(transaction)

    async def create_prompt_snapshot(self, item):
        await self._prompt_snapshots().document(item.id).create(item.model_dump(mode="python"))
        return item

    async def get_prompt_snapshot(self, experiment_id, role):
        snapshot = await self._prompt_snapshots().document(_prompt_snapshot_id(experiment_id, role)).get()
        return PromptSnapshotRecord.model_validate(snapshot.to_dict()) if snapshot.exists else None

    async def list_prompt_snapshots(self, experiment_id):
        from google.cloud.firestore_v1.base_query import FieldFilter

        snapshots = self._prompt_snapshots().where(filter=FieldFilter("experiment_id", "==", experiment_id)).stream()
        return sorted(
            [PromptSnapshotRecord.model_validate(snapshot.to_dict()) async for snapshot in snapshots],
            key=lambda item: item.created_at,
        )

    async def create_test_generation_run(self, item):
        await self._test_generation_runs().document(item.id).create(item.model_dump(mode="python"))
        return item

    async def get_test_generation_run(self, run_id):
        snapshot = await self._test_generation_runs().document(run_id).get()
        return TestGenerationRunRecord.model_validate(snapshot.to_dict()) if snapshot.exists else None

    async def delete_test_generation_run(self, run_id):
        await self._test_generation_runs().document(run_id).delete()

    async def save_test_generation_run(self, item):
        await self._test_generation_runs().document(item.id).set(item.model_dump(mode="python"))
        return item

    async def list_test_generation_runs_for_owner(self, owner_id):
        from google.cloud.firestore_v1.base_query import FieldFilter

        snapshots = self._test_generation_runs().where(filter=FieldFilter("owner_id", "==", owner_id)).stream()
        return sorted(
            [TestGenerationRunRecord.model_validate(snapshot.to_dict()) async for snapshot in snapshots],
            key=lambda item: item.created_at,
            reverse=True,
        )

    async def list_test_generation_runs_for_workspace(self, workspace_id):
        from google.cloud.firestore_v1.base_query import FieldFilter

        snapshots = self._test_generation_runs().where(filter=FieldFilter("workspace_id", "==", workspace_id)).stream()
        return sorted(
            [TestGenerationRunRecord.model_validate(snapshot.to_dict()) async for snapshot in snapshots],
            key=lambda item: item.created_at,
            reverse=True,
        )


def _prompt_snapshot_id(experiment_id: str, role: PromptRole) -> str:
    return f"{experiment_id}:{role.value}"
