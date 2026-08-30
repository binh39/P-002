"""Fail-safe Firestore workspace backfill for legacy PromptOpt records."""

import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime

COLLECTIONS = ("projects", "experiments", "prompt_versions", "test_generation_runs")


def _deduplicated_names(records: list[tuple[str, dict]]) -> dict[str, str]:
    updates = {}
    used: set[str] = set()
    for record_id, data in sorted(records, key=lambda item: (str(item[1].get("created_at", "")), item[0])):
        original = str(data.get("name") or "Untitled").strip()
        candidate = original
        suffix = 2
        while candidate.casefold() in used:
            candidate = f"{original} {suffix}"
            suffix += 1
        used.add(candidate.casefold())
        if candidate != data.get("name"):
            updates[record_id] = candidate
    return updates


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
    from firebase_admin import auth, firestore, initialize_app

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
    by_workspace = defaultdict(lambda: defaultdict(list))
    counts = Counter()
    for collection in COLLECTIONS:
        snapshots = experiments if collection == "experiments" else database.collection(collection).stream()
        for snapshot in snapshots:
            counts["read"] += 1
            try:
                update = _workspace_update(collection, snapshot.to_dict(), experiment_owners)
                data = {**snapshot.to_dict(), **(update or {})}
                if collection in {"experiments", "test_generation_runs"} and data.get("workspace_id"):
                    by_workspace[data["workspace_id"]][collection].append((snapshot.id, data))
                if update is None:
                    counts["skipped"] += 1
                    continue
                counts["changed"] += 1
                if args.apply:
                    snapshot.reference.update(update)
            except Exception:
                counts["errors"] += 1
    for workspace_id, grouped in by_workspace.items():
        owner = next(
            (data.get("owner_id") for _, data in grouped.get("experiments", []) if data.get("owner_id")), workspace_id
        )
        now = datetime.now(UTC)
        try:
            account = auth.get_user(owner)
            owner_email = account.email.casefold() if account.email else None
            owner_name = account.display_name or account.email or owner
        except Exception:
            owner_email = None
            owner_name = owner
        workspace_ref = database.collection("workspaces").document(workspace_id)
        if not workspace_ref.get().exists:
            counts["workspaces_created"] += 1
            if args.apply:
                workspace_ref.set(
                    {
                        "id": workspace_id,
                        "name": "Workspace 1",
                        "owner_id": owner,
                        "member_ids": [owner],
                        "members": [
                            {
                                "user_id": owner,
                                "email": owner_email,
                                "name": owner_name,
                                "role": "prompt_engineer",
                                "joined_at": now,
                            }
                        ],
                        "created_at": now,
                        "updated_at": now,
                    }
                )
        profile_ref = database.collection("user_profiles").document(owner)
        if not profile_ref.get().exists:
            counts["profiles_created"] += 1
            if args.apply:
                profile_ref.set(
                    {
                        "id": owner,
                        "email": owner_email,
                        "name": owner_name,
                        "role": "prompt_engineer",
                        "active_workspace_id": workspace_id,
                        "onboarding_completed": True,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
        for collection in ("experiments", "test_generation_runs"):
            for record_id, data in grouped.get(collection, []):
                if not data.get("creator_name"):
                    counts["creator_names"] += 1
                    if args.apply:
                        database.collection(collection).document(record_id).update({"creator_name": owner_name})
            for record_id, name in _deduplicated_names(grouped.get(collection, [])).items():
                counts["renamed"] += 1
                if args.apply:
                    database.collection(collection).document(record_id).update({"name": name})
    print(
        f"mode={'apply' if args.apply else 'dry-run'} read={counts['read']} changed={counts['changed']} "
        f"skipped={counts['skipped']} workspaces_created={counts['workspaces_created']} "
        f"profiles_created={counts['profiles_created']} creator_names={counts['creator_names']} "
        f"renamed={counts['renamed']} errors={counts['errors']}"
    )
    return 1 if counts["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
