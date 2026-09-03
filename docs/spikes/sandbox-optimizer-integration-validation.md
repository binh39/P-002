# Phase 5 optimizer sandbox integration validation

Validation date: 2026-08-27

## Outcome

The optimizer execution path now separates test generation from project test
execution. CoverUp generates tests in the optimizer environment, while
diagnostic, baseline and candidate scoring use `OptimizerSandboxClient` and a
versioned `RunSpec` against one immutable artifact per project.

Docker acceptance command:

```powershell
.\.venv313\Scripts\python.exe scripts\run_sandbox_phase5_integration.py `
  --image-digest sha256:5a9ec1908b8284471b9eb3ace920725ae9bda00f98c153871509d3e9ecf160eb
```

Observed result:

- environment fingerprint:
  `9d9b577a9fd6dcc991c7039e1f53b8f3f42c7bf5836c3e96ed2c4a0d8c953f95`;
- runner: `project_native`, pytest `9.1.1`, coverage `7.10.7`;
- two isolated repeat modules collected and both passed;
- target identity: `src/demo/__init__.py::classify`;
- normalized coverage: 3/4 statements and 1/2 branches;
- optimizer packages absent, credentials absent and outbound network denied.

The generated test input is mounted separately from the read-only source.
Project pytest configuration is still rooted at the project mount.

## Fingerprint and cache gates

- Cache schema 15 incorporates the per-project environment fingerprint in the
  evaluation digest, in addition to prompt, split and replicate identity.
- A changed artifact fingerprint therefore selects a new cache and reruns the
  baseline automatically during normal optimization.
- Finalize repairs baseline rows whose fingerprint is missing or differs from
  the active sandbox before candidate evaluation.
- Paired aggregation raises an error on any remaining baseline/candidate
  fingerprint mismatch; it never converts the mismatch to score zero.
- Result rows, batch cache, final validation and coverage report carry the
  environment fingerprint.

## Multi-project behavior

`OptimizerSandboxClient` resolves a separate source root, image and artifact
for every dataset project. Each target is submitted as a separate Docker run;
artifacts are never merged. Cross-project tests remain unsupported unless a
future explicit composite sandbox contract describes their dependency graph.

Machine-readable Docker evidence is stored at
`eval/sandbox_phase5_integration/acceptance-summary.json`.
