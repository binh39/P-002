"""Fail-safe Firestore workspace backfill for legacy PromptOpt records."""

import argparse
from collections import Counter

COLLECTIONS = ("experiments", "prompt_versions", "test_generation_runs")


def _workspace_update(collection: str, data: dict, experiment_owners: dict[str, str]) -> dict | None:
    if data.get("workspace_id"):
        return None
    owner_id = data.get("owner_id") or data.get("created_by")
    if not owner_id and collection == "prompt_versions":
        owner_id = experiment_owners.get(str(data.get("experiment_id", "")))
    if not owner_id:
        return None
    update = {"workspace_id": owner_id}
    if collection == "prompt_versions" and not data.get("created_by"):
        update["created_by"] = owner_id
    return update


def main() -> int:
    from firebase_admin import firestore, initialize_app

    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes; default is dry-run")
    args = parser.parse_args()
    initialize_app()
    database = firestore.client()
    experiments = list(database.collection("experiments").stream())
    experiment_owners = {
        snapshot.id: snapshot.to_dict().get("owner_id")
        for snapshot in experiments
        if snapshot.to_dict().get("owner_id")
    }
    counts = Counter()
    for collection in COLLECTIONS:
        snapshots = experiments if collection == "experiments" else database.collection(collection).stream()
        for snapshot in snapshots:
            counts["read"] += 1
            try:
                update = _workspace_update(collection, snapshot.to_dict(), experiment_owners)
                if update is None:
                    counts["skipped"] += 1
                    continue
                counts["changed"] += 1
                if args.apply:
                    snapshot.reference.update(update)
            except Exception:
                counts["errors"] += 1
    print(
        f"mode={'apply' if args.apply else 'dry-run'} read={counts['read']} changed={counts['changed']} "
        f"skipped={counts['skipped']} errors={counts['errors']}"
    )
    return 1 if counts["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
