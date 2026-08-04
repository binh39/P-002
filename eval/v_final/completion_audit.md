# v-final completion audit

Audit date: 2026-08-04

This audit maps `plan/test-gen-prompt-optimization-guide.md` to repository
evidence and the corrected locked evaluation.

| Plan requirement | Evidence | Status |
|---|---|---|
| 6.1 Docker pytest/coverage/mutation harness | `harness/`, `sandbox/Dockerfile`, focal-symbol tests | Complete |
| 6.2 `GenerateUnitTest` and bounded DSPy ReAct | `optimizer/signatures.py`, `optimizer/module.py`, `optimizer/tools.py` | Complete |
| 6.3 shared metrics and disjoint 20/10/10 split | `optimizer/metrics.py`, `optimizer/dataset.py`, `evaluation/holdout.py` | Complete |
| 6.4 LangGraph stages and Langfuse tracing | `orchestration/` | Complete |
| 6.5 FastAPI, SQLAlchemy, Alembic, PostgreSQL | `src/api/`, `db/`, `alembic/`, `docker-compose.yml` | Complete |
| 6.6 mutation/cost Pareto frontier | `analytics/pareto.py`, frontend chart | Complete |
| 6.7 evidence-grounded explanations | `analytics/explanation.py` and tests | Complete |
| 6.8 review/Approve flow | approval endpoint, database record, frontend review panel | Complete |
| 6.9 frontend workflows | form, result view, Pareto chart, review flow | Complete |
| 6.10 Docker Compose deployment | healthy backend/PostgreSQL/frontend plus nested sandbox smoke | Complete |
| Section 7 locked comparison | five result files, digest `9e351f2c9da37d43`, ten rows each | Complete |
| Section 7 final analysis | aggregate table, four-mode ranking, paired bootstrap, regressions and five qualitative examples in `corrected/report.md` | Complete |

## Corrected evaluation result

| Mode | Build | Pass | Statement | Branch | Mutation | Cost | Latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| zero-shot | 70.0% | 26.3% | 43.3% | 33.7% | 4.0% | $0.0030 | 199.30s |
| static SymPrompt | 80.0% | 28.2% | 57.0% | 49.7% | 4.5% | $0.0041 | 387.70s |
| BootstrapFewShot | 100.0% | 27.3% | 68.5% | 58.7% | 0.0% | $0.0554 | 1526.64s |
| GEPA (15 iterations) | 90.0% | 32.0% | 60.4% | 50.5% | 20.3% | $0.4100 | 2271.11s |
| CoverUp reference | 100.0% | 100.0% | 32.8% | 33.9% | 17.4% | $0.0075 | 728.10s |

GEPA ranks first among the four LLM modes by mutation score. Its paired mean
mutation improvement is +16.3 points over zero-shot, +15.8 over static
SymPrompt, and +20.3 over BootstrapFewShot. Compared with CoverUp the mean
improvement is +2.9 points, but its 95% paired-bootstrap interval crosses zero.

## Deployment smoke evidence

- Backend health endpoint returned `status=ok`.
- PostgreSQL and backend containers became healthy; frontend returned HTTP 200.
- Alembic reported revision `20260803_0001 (head)`.
- The backend could access Docker and execute a nested sandbox test with build,
  pass, statement coverage, and branch coverage all equal to 100%.

## Final verification

- `python -m pytest -q`: **94 passed**; only 11 upstream DSPy deprecation
  warnings.
- `npm.cmd test` in `frontend/`: production build passed and **2/2 tests
  passed**.
- Scoped Ruff check for the owned optimizer, evaluation, harness,
  orchestration, analytics, API, database, migrations, and v-final tests:
  **passed**.
- Result integrity: **5/5 files**, **10/10 held-out rows each**, one digest
  `9e351f2c9da37d43`, and matching ledger entries.
- GEPA checkpoint: internal `i=14`, `130` metric evaluations, and no iteration
  16 in the valid run.
- Compose: PostgreSQL and backend healthy, frontend running; backend health
  returned `{"status":"ok","env":"development"}` and frontend returned HTTP
  200.
