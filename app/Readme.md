# PromptOpt

PromptOpt lÃ  web app tá»‘i Æ°u prompt cho bÃ i toÃ¡n sinh Python unit test. NgÆ°á»i dÃ¹ng chá»n project vÃ 
function, cáº¥u hÃ¬nh dataset/model/CoverUp/GEPA, cháº¡y baseline, tá»‘i Æ°u prompt, so sÃ¡nh paired trÃªn
locked test split, sau Ä‘Ã³ approve hoáº·c reject prompt candidate.

TÃ i liá»‡u nÃ y lÃ  Ä‘iá»ƒm báº¯t Ä‘áº§u cho ngÆ°á»i tiáº¿p tá»¥c phÃ¡t triá»ƒn dá»± Ã¡n. Tráº¡ng thÃ¡i Ä‘Æ°á»£c cáº­p nháº­t láº§n cuá»‘i
ngÃ y **2026-08-08**.

## Tráº¡ng thÃ¡i hiá»‡n táº¡i

á»¨ng dá»¥ng Ä‘Ã£ cÃ³ vertical slice cháº¡y tá»« frontend Ä‘áº¿n Google Cloud:

1. Firebase Authentication xÃ¡c thá»±c ngÆ°á»i dÃ¹ng.
2. Frontend gá»i FastAPI qua Firebase Hosting rewrite `/api/**`.
3. NgÆ°á»i dÃ¹ng chá»n bundled sample repo vÃ  táº¡o experiment; upload ZIP váº«n chá»‰ phá»¥c vá»¥ phÃ¢n tÃ­ch project riÃªng.
4. Cloud Tasks Ä‘iá»u phá»‘i DSPy/GEPA sang Cloud Run Job; baseline prompt lÃ  candidate sá»‘ 0.
5. Job dÃ¹ng sample repo Ä‘Ã³ng gÃ³i sáºµn vÃ  chá»‰ nháº­n dataset/prompt qua GCS.
6. Candidate sá»‘ 0 vÃ  candidate tá»‘i Æ°u Ä‘Æ°á»£c so sÃ¡nh trÃªn locked test split.
7. Prompt Ä‘á»§ Ä‘iá»u kiá»‡n Ä‘Æ°á»£c táº¡o á»Ÿ tráº¡ng thÃ¡i `in_review`, rá»“i approve/reject cÃ³ audit data.

Production hiá»‡n táº¡i: [https://project-7df9f963-9fe0-4b76-b3d.web.app](https://project-7df9f963-9fe0-4b76-b3d.web.app).

á»¨ng dá»¥ng **chÆ°a production-complete**. CÃ¡c pháº§n cÃ²n thiáº¿u quan trá»ng nháº¥t lÃ  production smoke cho
ba sample repo sau báº£n runner má»›i, idempotency/cancellation/checkpoint, quota/cost controls,
observability, tenant-isolation tests vÃ  xÃ³a mock khá»i cÃ¡c mÃ n hÃ¬nh phá»¥.

## Quy táº¯c source code

- Application backend FastAPI chá»‰ Ä‘áº·t trong `app/backend`.
- Frontend React chá»‰ Ä‘áº·t trong `app/frontend`.
- KhÃ´ng xÃ³a root `src/`: production runner Ä‘ang dÃ¹ng `src/coverup`, `src/optimization` vÃ 
  `src/sample_repo.zip`.
- `cloud/` chá»©a entrypoint vÃ  deployment scripts cho GEPA Cloud Run Job.
- KhÃ´ng sá»­a, ghi Ä‘Ã¨ hoáº·c dÃ¹ng prefix benchmark Ä‘á»™c láº­p `prompt_optimization_v3` cho web workflow.
- KhÃ´ng commit `.env`, `.env.local`, Firebase token, service-account key, signed URL, raw smoke
  output hoáº·c `CheckOutput/`.

## Repository layout

```text
P-002/
  app/
    frontend/                 React/Vite frontend
    backend/                  FastAPI application backend
      api/                    public API dependencies/router assembly
      modules/                auth, uploads, projects, analysis, experiments
      infrastructure/         Firestore, GCS, Cloud Tasks, Cloud Run clients
    tests/                    backend tests
    infra/                    Google Cloud provisioning and runtime env
    scripts/                  local/production smoke scripts
    Dockerfile                API image
    Readme.md                 current architecture and handoff guide
    Checklist.md              delivery history and prioritized backlog
  src/
    coverup/                  project-owned CoverUp engine
    optimization/             DSPy/GEPA runner, metrics, cache and promotion logic
    sample_repo.zip           source archive for the bundled isort/mimesis/mlxtend/typesystem snapshots
    sample_repo/              bundled snapshots copied into the GEPA image during deployment
  cloud/
    run_job.py                GEPA Cloud Run Job entrypoint
    Dockerfile.web            GEPA runner image
    deploy_gepa_job.ps1       standalone GEPA deployment helper
    run_gepa_job.ps1          standalone GEPA execution/download helper
  tests/                      CoverUp/GEPA invariant and dataset tests
  .github/workflows/          CI and keyless production deployment
```

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript 5.7, Vite 8, Tailwind CSS 4 |
| Routing/state | Wouter 3, TanStack Query 5, React local state |
| Validation/charts | Zod 4, Recharts 3 |
| Frontend quality | Oxfmt, ESLint 10, Vitest 4, React Testing Library |
| Authentication | Firebase Authentication: Email/Password, Google Sign-In, reset password |
| API | FastAPI, Uvicorn, Pydantic v2, pydantic-settings |
| Persistence | Firestore Native mode; in-memory repositories for tests/local mode |
| Object storage | Private Google Cloud Storage with short-lived signed upload URLs |
| Async orchestration | Cloud Tasks with OIDC-protected internal endpoints |
| Isolated execution | Docker locally; Cloud Run Jobs in production |
| Test generation | Project-owned CoverUp, LiteLLM/Vertex AI Gemini, SlipCover and coverage.py |
| Prompt optimization | DSPy 3.2.1 and GEPA 0.0.27 |
| Hosting | Firebase Hosting with `/api/**` rewrite to Cloud Run |
| CI/CD | GitHub Actions, Workload Identity Federation, Artifact Registry |
| Runtime versions | Node >=22.12; API image Python 3.11; CoverUp/GEPA images Python 3.12 |

## Architecture

```text
Browser
  -> Firebase Hosting
     -> React SPA
     -> /api/** rewrite -> FastAPI Cloud Run service
                          -> Firebase token verification
                          -> Firestore metadata/state
                          -> private GCS source/artifacts
                          -> Cloud Tasks
                             -> OIDC internal worker endpoint
                                -> GEPA Cloud Run Job (candidate zero/optimization/comparison)
                                   -> Vertex AI Gemini
                                   -> pytest + SlipCover/coverage.py
                                   -> result manifest/artifacts in GCS
```

FastAPI khÃ´ng cháº¡y source cá»§a ngÆ°á»i dÃ¹ng trá»±c tiáº¿p trong API container. Production pháº£i fail closed
náº¿u isolated runner chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh.

### Public API groups

Táº¥t cáº£ public business endpoints náº±m dÆ°á»›i `/api/v1` vÃ  yÃªu cáº§u Firebase bearer token, trá»« health:

| NhÃ³m | Endpoints chÃ­nh |
| --- | --- |
| Upload | `POST /uploads`, `POST /uploads/{id}/complete` |
| Project | `GET/POST /projects`, `GET /projects/samples`, `PATCH /projects/{id}/settings` |
| Analysis | `POST /projects/{id}/analyze`, `GET /projects/{id}/functions`, function source endpoint |
| Experiment | `GET/POST /experiments`, `GET/DELETE /experiments/{id}` |
| Baseline | `POST /experiments/{id}/runs`, run polling vÃ  authenticated artifact download |
| Optimization | `POST /experiments/{id}/optimize`, optimization polling/artifacts |
| Comparison | `POST /experiments/{id}/compare`, comparison polling/artifacts |
| Prompt version | owner-scoped list/detail vÃ  `POST .../{id}/approve|reject` |

CÃ¡c `/internal/v1/**` endpoints chá»‰ dÃ nh cho Cloud Tasks vÃ  pháº£i xÃ¡c minh OIDC audience/service
account; frontend khÃ´ng Ä‘Æ°á»£c gá»i trá»±c tiáº¿p.

## Chá»©c nÄƒng Ä‘Ã£ implement

### Authentication

- Register báº±ng email/password vÃ  display name.
- Login, logout, reset-password email vÃ  Google Sign-In.
- Protected routes vÃ  tá»± refresh Firebase ID token.
- API ownership checks; token khÃ´ng Ä‘Æ°á»£c lÆ°u thá»§ cÃ´ng vÃ o local/session storage.

### Projects vÃ  analysis

- Táº¡o/list/detail/delete project.
- Signed ZIP upload trá»±c tiáº¿p tá»« browser vÃ o private GCS.
- LÆ°u runtime, dependency, test, coverage vÃ  security settings.
- Cloud Tasks cháº¡y AST analysis báº¥t Ä‘á»“ng bá»™.
- PhÃ¡t hiá»‡n function, method, async function, qualified name, source range, LOC, statements vÃ 
  branch candidates.
- Xem source chÃ­nh xÃ¡c cá»§a function vÃ  cháº¡y re-analysis.
- Catalog read-only cho `isort`, `mimesis`, `mlxtend`, `typesystem`; chá»n sample khÃ´ng táº¡o Project/Function
  documents dÆ° thá»«a trong Firestore.

### Experiment configuration

- Chá»n má»™t hoáº·c nhiá»u project; backend khÃ´ng Ä‘áº·t giá»›i háº¡n cá»©ng 50 target.
- Sampling: random, nhiá»u branch nháº¥t, nhiá»u statement nháº¥t hoáº·c manual.
- `random_seed` vÃ  tá»· lá»‡ train/validation/test do ngÆ°á»i dÃ¹ng chá»n, tá»•ng pháº£i báº±ng 100 vÃ  test split
  pháº£i khÃ¡c rá»—ng.
- Manual split Ä‘Æ°á»£c validate Ä‘á»ƒ target khÃ´ng xuáº¥t hiá»‡n á»Ÿ nhiá»u split.
- Dropdown Gemini cho `COVERUP_MODEL` vÃ  `OPTIMIZE_MODEL`; model chá»n trong UI Ä‘Æ°á»£c lÆ°u trong
  experiment settings vÃ  truyá»n xuá»‘ng runner.
- Cáº¥u hÃ¬nh tháº­t: max attempts, repeat tests, concurrency, rate limit, pytest args, max metric calls,
  evaluation replicates vÃ  reflection temperature.
- Review cáº¥u hÃ¬nh vÃ  xÃ³a experiment.

### CoverUp trong GEPA

- KhÃ´ng cÃ³ baseline job riÃªng; baseline prompt Ä‘Æ°á»£c GEPA Ä‘Ã¡nh giÃ¡ nhÆ° candidate sá»‘ 0.
- Auto-setup ba sample repo trÆ°á»›c khi gá»i model:
  - táº¡o distribution metadata an toÃ n mÃ  khÃ´ng cháº¡y setup script cá»§a repo;
  - kiá»ƒm tra import package vÃ  dependency báº¯t buá»™c;
  - `isort`: metadata + `tomli`, bá» `_vendored` vÃ  `deprecated` theo coverage config;
  - `mlxtend`: kiá»ƒm tra NumPy/SciPy/Pandas/scikit-learn/Matplotlib/joblib;
  - `typesystem`: kiá»ƒm tra Jinja2 vÃ  YAML.
- Target contract dÃ¹ng chÃ­nh xÃ¡c `source_file + qualified_name`, khÃ´ng match rá»™ng theo tÃªn hÃ m.
- Web runner dÃ¹ng dataset vÃ  prompt táº£i riÃªng tá»« GCS; source láº¥y tá»« sample repo trong image.
- Structured attempt trace giá»¯ outcome nhÆ° `test_error`, `coverage_gain_saved` vÃ 
  `max_attempts_exhausted`.
- Pytest exit code 5 lÃ  zero-test baseline há»£p lá»‡ náº¿u denominator cá»§a má»i target váº«n há»£p lá»‡.
- KhÃ´ng bÃ¡o branch coverage áº£o khi khÃ´ng statement nÃ o Ä‘Æ°á»£c cháº¡y.
- Artifacts gá»“m prompt, setup report, CoverUp logs, structured trace, coverage vÃ  káº¿t quáº£ GEPA.

### DSPy/GEPA optimization

- Train/validation search; locked test split khÃ´ng Ä‘Æ°á»£c dÃ¹ng Ä‘á»ƒ chá»n candidate.
- Seed candidate luÃ´n lÃ  baseline prompt tháº­t.
- Cache tÃ¡ch theo prompt digest, evaluation digest, split vÃ  replicate.
- Workspace tÃ¡ch theo candidate/split; target Ä‘Æ°á»£c xÃ¡c Ä‘á»‹nh báº±ng source file + qualname.
- Candidate prompt chá»‰ gá»“m `initial` vÃ  `error`, giá»¯ placeholder báº¯t buá»™c.
- Candidate vÃ  baseline prompt Ä‘Æ°á»£c lÆ°u riÃªng; optimization khÃ´ng tá»± ghi Ä‘Ã¨ production prompt.
- Cloud Tasks chá»‰ trigger/poll ngáº¯n; GEPA Cloud Run Job cÃ³ timeout tá»‘i Ä‘a 86400 giÃ¢y.

### Comparison vÃ  prompt review

- Paired baseline/candidate evaluation trÃªn cÃ¹ng locked targets vÃ  replicates.
- Strict promotion gate: candidate pháº£i tá»‘t hÆ¡n baseline vÃ  khÃ´ng fail/timeout/flaky/regress pass rate.
- Náº¿u GEPA giá»¯ nguyÃªn baseline digest thÃ¬ skip final comparison khÃ´ng cáº§n thiáº¿t.
- LÆ°u `final_validation.json`, absolute/relative gain vÃ  promotion decision.
- Prompt version `in_review`, owner-scoped list/filter/pagination, approve/reject idempotent vá»›i
  reviewer/comment/timestamp.

### Frontend screens

- Login/Register, Dashboard, Projects, Project Detail/Analysis, Create Experiment, Experiments,
  Run/Comparison, Review & Approval, Prompt Registry, Datasets, Playground vÃ  Settings.
- Projects, experiments, optimization, comparison vÃ  prompt review luÃ´n dÃ¹ng HTTP
  repositories.
- `VITE_DATA_MODE` hiá»‡n chá»‰ quyáº¿t Ä‘á»‹nh Dashboard dÃ¹ng mock hay HTTP. Workflow production Ä‘ang build
  vá»›i `VITE_DATA_MODE=demo`, nÃªn production lÃ  **hybrid**: Dashboard dÃ¹ng fixture; cÃ¡c workflow chÃ­nh
  váº«n gá»i API tháº­t.
- Datasets váº«n import fixture trá»±c tiáº¿p. Playground váº«n lÃ  UI tÄ©nh. ÄÃ¢y lÃ  mock cÃ²n láº¡i cáº§n xá»­ lÃ½.

## Experiment execution contract

Má»™t experiment lÆ°u snapshot báº¥t biáº¿n Ä‘á»§ Ä‘á»ƒ tÃ¡i hiá»‡n lá»±a chá»n:

- project IDs vÃ  runner-safe project names;
- source file, function ID vÃ  qualified symbol;
- sampling method, seed vÃ  dataset splits;
- CoverUp/GEPA settings vÃ  selected models;
- optimization, comparison vÃ  prompt-version IDs.

GEPA web workflow dÃ¹ng prefix riÃªng `runner-jobs/gepa/<execution-id>/`, upload dataset/prompt nhÆ°ng
khÃ´ng upload source ZIP. KhÃ´ng dÃ¹ng prefix `prompt_optimization_v3`.

## Frontend development

```powershell
cd app\frontend
npm ci
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run build
npm run dev
```

Local environment náº±m trong `app/frontend/.env.local` vÃ  khÃ´ng Ä‘Æ°á»£c commit. CÃ¡c mode:

| Auth | Data | Ã nghÄ©a |
| --- | --- | --- |
| `demo` | `demo` | Local UI/demo auth; Dashboard fixture |
| `firebase` | `demo` | Firebase auth; Dashboard fixture; core repositories váº«n dÃ¹ng API |
| `firebase` | `connected` | Firebase auth vÃ  Dashboard API |

## Backend development

```powershell
cd app
..\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:PYTHONPATH = (Resolve-Path .).Path
..\.venv\Scripts\python.exe -m ruff format --check src tests sandbox
..\.venv\Scripts\python.exe -m ruff check src tests sandbox
..\.venv\Scripts\python.exe -m pytest tests -q
..\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Máº·c Ä‘á»‹nh local dÃ¹ng auth disabled, memory repositories, local storage vÃ  inline dispatch. Xem
`app/.env.example` vÃ  `app/backend/config.py` trÆ°á»›c khi Ä‘á»•i backend mode.

## CoverUp/GEPA development

```powershell
cd D:\VinAI\P-002
uv sync --frozen --group dev
uv run ruff check src/optimization tests/test_coverage_optimization.py tests/test_dataset_builder.py cloud/run_job.py
uv run python -m py_compile src/coverup/coverup.py src/optimization/gepa.py src/optimization/metrics.py src/optimization/cli.py src/optimization/runner.py src/optimization/prompts.py cloud/run_job.py
uv run pytest -p no:pytest_isolate tests -q
```

Äá»c `Agent.md` trÆ°á»›c khi sá»­a optimizer. CÃ¡c invariant quan trá»ng gá»“m locked holdout, strict promotion,
per-target feedback, exact target identity, cache isolation vÃ  zero-test denominator validity.

KhÃ´ng tá»± cháº¡y live Gemini benchmark vÃ¬ phÃ¡t sinh chi phÃ­. Unit test pass khÃ´ng chá»©ng minh prompt má»›i
tá»‘t hÆ¡n; benchmark quyáº¿t Ä‘á»‹nh pháº£i dÃ¹ng artifacts directory má»›i vÃ  cÃ¹ng evaluation protocol.

## Docker verification

Cháº¡y tá»« repository root:

```powershell
docker build --file app/Dockerfile --tag promptopt-api:local .
docker build --file cloud/Dockerfile.web --tag promptopt-gepa-runner:local .
```

API container khÃ´ng cáº§n Docker socket. Docker chá»‰ cáº§n cho local isolated baseline/build verification;
commit/push khÃ´ng yÃªu cáº§u Docker vÃ¬ GitHub Actions tá»± build image.

## CI/CD

| Workflow | Trigger | Viá»‡c thá»±c hiá»‡n |
| --- | --- | --- |
| `frontend-ci.yml` | PR/main khi frontend Ä‘á»•i | format, lint, typecheck, test, build, npm audit |
| `frontend-deploy.yml` | merge/push main khi frontend Ä‘á»•i | WIF auth, láº¥y Firebase web config, build vÃ  deploy Hosting |
| `ci.yml` | PR/main khi backend/runner Ä‘á»•i | backend tests, optimizer tests, build API/CoverUp/GEPA images |
| `backend-deploy.yml` | merge/push main khi backend/runner Ä‘á»•i | WIF auth, push 3 images, deploy 2 Jobs vÃ  API |

Feature branch chá»‰ CI; `main` lÃ  production. Deployment dÃ¹ng Workload Identity Federation, khÃ´ng dÃ¹ng
service-account JSON key.

## Production resources

| Resource | Value |
| --- | --- |
| GCP/Firebase project | `project-7df9f963-9fe0-4b76-b3d` |
| Admin Vertex AI project | `project-7df9f963-9fe0-4b76-b3d` |
| Region | `asia-southeast1` |
| Hosting/API | `https://project-7df9f963-9fe0-4b76-b3d.web.app`, `/api/v1` |
| Cloud Run API | `promptopt-api` |
| CoverUp Job | `promptopt-coverup-runner` |
| GEPA Job | `promptopt-gepa-runner` |
| Artifact Registry | `asia-southeast1-docker.pkg.dev/project-7df9f963-9fe0-4b76-b3d/promptopt` |
| Private bucket | `project-7df9f963-9fe0-4b76-b3d-promptopt-sources` |
| Cloud Tasks queues | `promptopt-analysis`, `promptopt-baseline` |
| Runtime identity | `promptopt-api@project-7df9f963-9fe0-4b76-b3d.iam.gserviceaccount.com` |
| Runner identity | `promptopt-runner@project-7df9f963-9fe0-4b76-b3d.iam.gserviceaccount.com` |

Firebase Hosting rewrite lÃ  public, nhÆ°ng API business endpoints váº«n yÃªu cáº§u Firebase bearer token.
Runner identity chá»‰ Ä‘Æ°á»£c cáº¥p quyá»n tá»‘i thiá»ƒu trÃªn opaque runner exchange objects vÃ  Vertex AI.
Admin executions override only `VERTEXAI_PROJECT`; the API, Cloud Run Job, GCS, Firestore and non-admin
executions run in `project-7df9f963-9fe0-4b76-b3d`. The runner identity must have `roles/aiplatform.user` and
`roles/serviceusage.serviceUsageConsumer` on `project-7df9f963-9fe0-4b76-b3d`.

## Production smoke

Script cáº§n Firebase **ID token**; `gcloud auth login` khÃ´ng táº¡o Firebase user session.

```powershell
# GEPA smoke on bundled isort
.\app\scripts\smoke_production.ps1

# GEPA (candidate zero is baseline) -> optional locked comparison/review
.\app\scripts\smoke_production.ps1 -FullPipeline -ReviewDecision approve
```

Sanitized output Ä‘Æ°á»£c ghi vÃ o ignored `app/.smoke-results/`. KhÃ´ng commit raw response hoáº·c UID.

## Verification snapshot

Táº¡i láº§n cáº­p nháº­t 2026-08-08:

- Backend Ruff/pytest: **38 passed**.
- CoverUp/GEPA invariant tests: **51 passed**.
- API image vÃ  GEPA runner image dÃ¹ng cÃ¹ng sample repo Ä‘Ã³ng gÃ³i sáºµn.
- Production váº«n cáº§n deploy commit má»›i vÃ  cháº¡y láº¡i smoke 10-target/ba sample repo.
- Live Gemini benchmark khÃ´ng Ä‘Æ°á»£c cháº¡y tá»± Ä‘á»™ng trong láº§n kiá»ƒm tra tÃ i liá»‡u.

## Viá»‡c tiáº¿p theo

Thá»© tá»± Æ°u tiÃªn Ä‘Æ°á»£c theo dÃµi chi tiáº¿t trong `Checklist.md`:

1. Deploy exact-target/prompt-contract runner vÃ  smoke isort má»›i; khÃ´ng tÃ¡i sá»­ dá»¥ng experiment cÅ©.
2. Smoke `typesystem`, rá»“i `mlxtend`; xÃ¡c nháº­n setup report, accepted tests vÃ  metrics.
3. Cháº¡y full optimize -> comparison -> review trÃªn production.
4. HoÃ n thiá»‡n idempotency, cancellation, GEPA checkpoint/resume vÃ  immutable checksums.
5. ThÃªm quota, cost ceiling, artifact retention, structured monitoring vÃ  alerts.
6. XÃ³a mock Dashboard/Datasets/Playground hoáº·c Ä‘á»‹nh nghÄ©a API/product semantics tÆ°Æ¡ng á»©ng.
7. ThÃªm staging, browser E2E, tenant-isolation/security tests vÃ  rollback drill.
