# Project sandbox v2 rollout and rollback runbook

Status: repository controls are implemented; production deployment and canary observation remain operator actions.

## Ownership

- Release owner: Backend/Platform release engineer.
- Rollback authority: incident commander or Backend/Platform on-call.
- Security stop authority: Security on-call.
- Dashboard owner: Backend/Platform observability owner.

Record the named people, change ticket and rollback deadline in the deployment record before starting a production rollout.

## Preconditions

1. Giai đoạn 7 infrastructure controls and Giai đoạn 8 remote CI are green.
2. Legacy runtime image/job remains deployed and readable for the complete rollback window.
3. Sandbox image is addressed by an immutable digest and its image contract/integration artifact is attached to the release.
4. Runtime v8 and sandbox v1 readers are both deployed.
5. Artifact retention is longer than `SANDBOX_ROLLBACK_WINDOW_DAYS`; do not migrate or delete the legacy cache.
6. Dashboard queries and alerts described below are active.

## Configuration states

The safe default is legacy-only:

```text
PROJECT_SANDBOX_V2=false
PROJECT_SANDBOX_ROLLOUT_MODE=disabled
SANDBOX_RUNTIME_EXECUTION_BACKEND=disabled
SANDBOX_ADVERTISED_PYTHON_VERSIONS=
```

Prepare shadow mode without changing activation:

```text
PROJECT_SANDBOX_V2=true
PROJECT_SANDBOX_ROLLOUT_MODE=shadow
RUNTIME_EXECUTION_BACKEND=cloud_run_job
CLOUD_RUN_RUNTIME_JOB=<legacy-runtime-job>
SANDBOX_RUNTIME_EXECUTION_BACKEND=cloud_run_job
SANDBOX_CLOUD_RUN_RUNTIME_JOB=<sandbox-v2-job>
SANDBOX_CANARY_PERCENT=0
SANDBOX_CANARY_PYTHON_VERSIONS=3.12
SANDBOX_ADVERTISED_PYTHON_VERSIONS=
```

Shadow runs both jobs but returns only the legacy report to atomic activation. A shadow start or result mismatch is recorded in rollout metrics and never replaces the active bundle.

Canary Python 3.12:

```text
PROJECT_SANDBOX_ROLLOUT_MODE=canary
SANDBOX_CANARY_PERCENT=5
SANDBOX_CANARY_PYTHON_VERSIONS=3.12
SANDBOX_ADVERTISED_PYTHON_VERSIONS=
```

Increase `SANDBOX_CANARY_PERCENT` through 5, 25, 50 and 100 only after each observation window passes. Project routing is stable because it is derived from the project ID hash.

After a stable 100% Python 3.12 window, switch to:

```text
PROJECT_SANDBOX_ROLLOUT_MODE=enabled
SANDBOX_ADVERTISED_PYTHON_VERSIONS=3.12
```

Advertise 3.11, 3.10 and 3.13 only after each corresponding image/job passes its own contract, security and Docker integration gates.

## Observation window and promotion gates

Use at least 24 hours and 100 completed admissions per step. Extend the window when traffic is lower. Do not promote when any condition fails:

- sandbox admission reject rate is more than 2 percentage points above paired legacy/shadow;
- shadow status/test-count/error-code mismatch exceeds 2%;
- fingerprint mismatch or cross-fingerprint scoring count is non-zero;
- sandbox security-policy violation count is non-zero;
- p95 total runtime duration exceeds legacy by more than 30%;
- cache corruption recovery fails or corruption rate exceeds 1%;
- active bundle activation differs from the selected rollout route;
- error-code distribution has a new unexplained deterministic failure cluster.

The authenticated `GET /api/v1/projects/runtime-rollout` endpoint returns rollout counters, protocol usage, shadow comparisons, failures and p50/p95 total duration. Production dashboards should derive build/execution stage, Python/image and cache metrics from structured runtime audit logs and worker metrics.

## Immediate rollback

1. Set `SANDBOX_ADVERTISED_PYTHON_VERSIONS=` so the UI stops offering new routes.
2. Set `PROJECT_SANDBOX_V2=false` and `PROJECT_SANDBOX_ROLLOUT_MODE=disabled`.
3. Deploy only the API configuration change. Do not delete or rewrite project records, active bundle references, environment artifacts or cache objects.
4. Confirm `GET /api/v1/projects/runtime-rollout` reports `enabled=false` and `mode=disabled`.
5. Upload a small known-good project and verify its route uses the legacy job and the existing active bundle remains readable.
6. Keep both worker images/jobs for the full rollback window. Preserve failure artifacts and audit logs.
7. Open an incident/change record with the trigger metric, first bad image digest/protocol and rollback timestamp.

Turning the feature flag off is the rollback mechanism; it does not mutate stored project/bundle/artifact data. Never run cache cleanup as part of rollback.

## Rollback drill

Before production rollout, run:

```powershell
$env:PYTHONPATH = "$(Get-Location);$(Get-Location)\app"
.\.venv\Scripts\python.exe -m pytest `
  app\tests\test_runtime_rollout.py `
  app\tests\test_runtime_preparation.py -q
Remove-Item Env:PYTHONPATH
```

Then perform the configuration transition in a staging environment:

1. legacy-only → shadow;
2. confirm shadow never activates its bundle;
3. shadow → 5% canary;
4. disable the flag;
5. confirm existing project IDs, active bundle object names and fingerprints are unchanged;
6. confirm a new admission uses legacy;
7. retain the drill artifacts and dashboard snapshot with the change record.

## Cleanup after rollback window

Removing the legacy reader, job or artifacts is a separate migration-cleanup PR. It is allowed only when protocol metrics show no legacy traffic for the agreed window, rollback has not been invoked, and the release owner plus incident commander approve the cleanup.
