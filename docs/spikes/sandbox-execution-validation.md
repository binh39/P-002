# Phase 4 sandbox execution validation

Validation date: 2026-08-27

## Immutable inputs

- Linux image: `sha256:5a9ec1908b8284471b9eb3ace920725ae9bda00f98c153871509d3e9ecf160eb`
- Python: `3.12.14`
- Managed runner: pytest `9.1.1`, coverage `7.15.3`
- Forbidden optimizer modules reported by the image contract: none present
- Native artifact fingerprint: `9d9b577a9fd6dcc991c7039e1f53b8f3f42c7bf5836c3e96ed2c4a0d8c953f95`
- Managed artifact fingerprint: `d700fc87a91d54b5b6184ce3413ab956cf9922741cddc9a3a72d3742bab81665`

## Execution evidence

Run with:

```powershell
.\.venv313\Scripts\python.exe scripts\run_sandbox_phase4_integration.py `
  --image-digest sha256:5a9ec1908b8284471b9eb3ace920725ae9bda00f98c153871509d3e9ecf160eb
```

The acceptance run completed successfully for:

| Profile | Pytest | Coverage | Tests | Statements | Branches |
|---|---:|---:|---:|---:|---:|
| `project_native` | 9.1.1 | 7.10.7 | 1/1 passed | 3/4 | 1/2 |
| `sandbox_managed` | 9.1.1 | 7.15.3 | 1/1 passed | 2/2 | 0/0 |
| `project_native` repeat | 9.1.1 | 7.10.7 | 1/1 passed | 3/4 | 1/2 |

The native run and its repeat used the same environment fingerprint and
returned identical normalized test counts and statement/branch coverage.
The project `fail_under = 100` setting did not reject the partial native
coverage result because evaluation uses its own controlled coverage config.

The generated native test also verifies at runtime that:

- `gepa` and `coverup` are not importable;
- AWS, Google and Azure credential variables are absent;
- an outbound socket connection fails while Docker uses `--network none`;
- the project `conftest.py` fixture is loaded.

The host launcher additionally enforces a read-only project mount, a separate
writable output mount, read-only container root, no added capabilities,
`no-new-privileges`, CPU/RAM/PID/file/output/wall-clock limits, and cleanup of
the named container on an outer timeout. It never mounts the Docker socket,
host home, or credential paths. Unit tests assert these command invariants and
the distinct collection/test/coverage/timeout error mappings.

Machine-readable results are written to
`eval/sandbox_phase4_integration/results/acceptance-summary.json`.
