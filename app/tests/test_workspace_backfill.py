from scripts.backfill_workspace_ids import _collection_snapshots, _deduplicated_names, _workspace_update


class _Snapshot:
    exists = True


class _Reference:
    def get(self):
        return _Snapshot()


class _Collection:
    def list_documents(self, page_size):
        assert page_size == 100
        return [_Reference(), _Reference()]


class _Database:
    def collection(self, name):
        assert name == "experiments"
        return _Collection()


def test_collection_snapshots_avoid_streaming_queries():
    assert len(_collection_snapshots(_Database(), "experiments")) == 2


def test_workspace_backfill_uses_owner_and_never_a_shared_default():
    owners = {"experiment-1": "owner-1"}
    assert _workspace_update("experiments", {"owner_id": "owner-1"}, owners) == {"workspace_id": "owner-1"}
    assert _workspace_update("test_generation_runs", {"owner_id": "owner-2"}, owners) == {"workspace_id": "owner-2"}
    assert _workspace_update("prompt_versions", {"experiment_id": "experiment-1"}, owners) == {
        "workspace_id": "owner-1",
        "created_by": "owner-1",
    }
    assert _workspace_update("experiments", {}, owners) is None
    assert _workspace_update("experiments", {"workspace_id": "existing"}, owners) is None


def test_duplicate_names_are_renamed_in_creation_order_and_case_insensitively():
    records = [
        ("second", {"name": "isort prompt optimization", "created_at": "2025-01-02"}),
        ("first", {"name": "Isort Prompt Optimization", "created_at": "2025-01-01"}),
        ("third", {"name": "isort prompt optimization", "created_at": "2025-01-03"}),
    ]
    assert _deduplicated_names(records) == {
        "second": "isort prompt optimization 2",
        "third": "isort prompt optimization 3",
    }
