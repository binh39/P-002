"""Assign trusted PromptOpt RBAC custom claims to a Firebase user."""

import argparse

VALID_ROLES = {"prompt_engineer", "prompt_reviewer"}


def main() -> int:
    from firebase_admin import auth, initialize_app

    parser = argparse.ArgumentParser()
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument("--uid")
    identity.add_argument("--email")
    parser.add_argument("--role", required=True, choices=sorted(VALID_ROLES))
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    workspace_id = args.workspace_id.strip()
    if not workspace_id:
        parser.error("--workspace-id cannot be blank")

    initialize_app()
    user = auth.get_user(args.uid) if args.uid else auth.get_user_by_email(args.email)
    claims = {**(user.custom_claims or {}), "role": args.role, "workspace_id": workspace_id}
    print(f"uid={user.uid} role={args.role} workspace_id={workspace_id} dry_run={args.dry_run}")
    if not args.dry_run:
        auth.set_custom_user_claims(user.uid, claims)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
