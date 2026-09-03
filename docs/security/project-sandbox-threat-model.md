# Project sandbox threat model

Status: implemented controls reviewed on 2026-08-28. This document follows ADR 0001, 0004 and 0005.

## Scope and trust boundaries

An uploaded ZIP, its dependency metadata, dependencies downloaded during build, and all project tests are untrusted. The optimizer process, host filesystem, Docker socket, cloud credentials, active environment pointers and artifacts belonging to other projects are trusted assets and must remain outside the project sandbox.

The lifecycle has two distinct boundaries:

1. Build creates an immutable environment artifact from a canonical dependency plan. It does not execute an arbitrary user shell command.
2. Execution mounts that artifact and project inputs read-only, writes only to dedicated temporary/output mounts, and has no network access.

## Threats and controls

| Threat | Control | Verification |
| --- | --- | --- |
| Zip Slip and platform-specific path confusion | Reject absolute paths, traversal, duplicate case-folded paths, Windows device names, alternate data streams and trailing dot/space names before extracting any entry. Resolve every destination below the extraction root. | `tests/test_runtime_workspace.py` |
| Symlink, hardlink or device escape | Uploaded ZIP symlinks are not materialized. Special Unix entries are rejected. Environment/runtime archives validate links and destination paths before extraction. | Runtime workspace and sandbox execution tests |
| Archive bomb or oversized file | Bound entry count, declared per-file/total size and actual streamed output size. | Runtime workspace tests and constants in `cloud/runtime_workspace.py` |
| Arbitrary dependency command | Convert supported metadata into a typed Dependency Plan; reject direct URL/path requirements and unknown index references. | Dependency-plan and builder tests |
| Dependency exfiltration during execution | Docker execution uses `--network none`; credentials are not in the environment allowlist. | Docker command tests and Phase 4 Docker integration evidence |
| Host/container privilege escape | Non-root UID 10001, read-only root filesystem, `no-new-privileges`, all capabilities dropped and Docker's default seccomp profile. Docker socket and home/credential mounts are absent. | Dockerfile contract and executor command tests |
| Resource exhaustion | CPU, memory, PID, timeout, file-size, tmpfs and output-byte limits; timed-out process groups are killed. | Executor tests |
| Secret leakage through diagnostics | Credential URLs, authorization headers, secret-like assignments, signed query parameters and configured index values are redacted before reports are persisted or returned to the UI. | `tests/test_sandbox_security.py` and builder tests |
| Cross-project cache confusion | Immutable artifact identity binds dependency plan, Python/image/runner identities and content hash; execution checks the artifact digest and fingerprint. | Builder/cache/executor tests |

## Intended compatibility failures

Tests that require Internet access fail closed during execution. The result is classified as `EXECUTION_NETWORK_DENIED` when the failure happens during collection. A project should replace or exclude those upstream integration tests; PromptOpt must not enable execution networking to make them pass.

Projects that require a build hook to generate import-time source (for example a generated version module) remain a separate compatibility task. Security hardening does not silently execute arbitrary project build scripts.

## Residual risks and open controls

- Build-stage Docker networking is currently enabled while the dependency resolver runs. Dependency sources are policy-checked, but Docker itself does not enforce a hostname-level registry/index allowlist. Production completion requires an allowlisting proxy, internal wheelhouse or equivalent infrastructure control. This checklist item remains open.
- Short-lived secret references for private registries are designed in the protocol, but a production secret broker and rotation proof are not yet integrated.
- Artifact ownership/trusted-root validation and structured audit events for build, execution, retry, activation and rollback are not complete.
- Image/cache/log scanning for secrets must be added to CI before the final security acceptance criterion can close.

These residual items block declaring all of Phase 7 complete; they do not justify weakening the execution sandbox.
