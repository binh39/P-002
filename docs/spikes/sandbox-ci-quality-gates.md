# Sandbox CI quality-gate validation

Date: 2026-08-28

## Implemented CI gates

- `sandbox-image-contract` builds Python 3.10, 3.11, 3.12 and 3.13 images, runs the machine-readable contract and uploads one evidence artifact per Python version.
- `sandbox-docker-integration` builds Python 3.12 and runs the real upload-to-execution lifecycle without an LLM call.
- Docker integration logs and the JSON acceptance summary are uploaded with `if: always()` and retained for 14 days.

The Python 3.12 integration covers:

1. creation and extraction of an actual uploaded ZIP;
2. dependency planning and an immutable project environment build;
3. project-native pytest 9.1.1 with coverage 7.10.7 while the sandbox agent uses coverage 7.15.3;
4. baseline and generated candidate tests in separate Docker executions using the same environment fingerprint;
5. denied execution networking and absence of optimizer packages/credential environment variables;
6. cache hit reuse;
7. deliberate artifact corruption, quarantine and atomic rebuild.

## Local evidence

- Docker image build: pass for `promptopt-sandbox:py3.12`.
- Acceptance summary: `eval/sandbox_phase8_current/acceptance-summary.json`.
- Admission: `runtime_ready`.
- Baseline: `succeeded`, one test passed.
- Candidate: `succeeded`, one test passed.
- Project-native coverage version: 7.10.7.
- Cache recovery: same fingerprint restored and one corrupt entry quarantined.
- Root suite: 256 passed, 1 documented expected failure.
- Backend suite: 84 passed.
- Ruff, required `py_compile` and `git diff --check`: pass.

No live GEPA benchmark was run.

## Remaining before Phase 8 completion

- Obtain a successful remote GitHub Actions run for the new jobs.
- Add real Docker cases for two mutually conflicting projects in separate sandboxes.
- Add the no-tests, fail-under, setup-only and incompatible-Python Docker cases.
- Add real Docker timeout/output-limit cases; execution network denial is already exercised locally.

The current unit/contract suite covers these edge cases, but they remain unchecked in the Docker matrix until the real-container harness covers them.
