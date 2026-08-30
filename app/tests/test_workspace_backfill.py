from scripts.backfill_workspace_ids import _workspace_update


def test_workspace_backfill_uses_owner_and_never_a_shared_default():
    owners = {"experiment-1": "owner-1"}
    assert _workspace_update("experiments", {"owner_id": "owner-1"}, owners) == {
        "workspace_id": "owner-1"
    }
    assert _workspace_update("test_generation_runs", {"owner_id": "owner-2"}, owners) == {
        "workspace_id": "owner-2"
    }
    assert _workspace_update("prompt_versions", {"experiment_id": "experiment-1"}, owners) == {
        "workspace_id": "owner-1",
        "created_by": "owner-1",
    }
    assert _workspace_update("experiments", {}, owners) is None
    assert _workspace_update("experiments", {"workspace_id": "existing"}, owners) is None
