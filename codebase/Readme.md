# PromptOpt application

## Repository layout

```text
codebase/
  src/          # FastAPI backend (the only backend source root)
  tests/        # Backend tests
  frontend/     # React/Vite frontend
  Dockerfile
  requirements.txt
```

The legacy repository-level `src/` is not used by PromptOpt development and can be removed later. All new backend code must be placed under `codebase/src`.

## Backend development

```powershell
cd codebase
..\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
..\.venv\Scripts\python.exe -m ruff format --check src tests
..\.venv\Scripts\python.exe -m ruff check src tests
..\.venv\Scripts\python.exe -m pytest tests
..\.venv\Scripts\python.exe -m uvicorn src.main:app --reload --port 8000
```

The Projects/upload API and production configuration are documented in [docs/backend-projects-slice.md](docs/backend-projects-slice.md).

## Experiment and prompt optimization pipeline

The backend now supports the experiment lifecycle from an analyzed project through review:

- Create a deterministic train/validation/locked-test dataset from selected functions.
- Queue and poll an isolated CoverUp baseline run with structured coverage artifacts.
- Run GEPA prompt search on train/validation only and persist the locked candidate prompt.
- Queue a paired final comparison of baseline and candidate on the same locked test targets and replicates.
- Block promotion when generated tests fail, time out, are flaky, reduce pass rate, or do not improve coverage.
- Create an `in_review` prompt version and record an idempotent approve/reject decision with reviewer audit data.

Firestore stores durable run and prompt-version records. Cloud Tasks invokes OIDC-protected internal worker endpoints. Local execution uses the isolated Docker runner. Production sandbox execution still requires the Cloud Run Job runner described in the checklist; the Cloud Run API service remains fail-closed and does not execute uploaded source directly.

## Backend readiness (2026-08-07)

The backend is complete enough for the first end-to-end vertical slice, but it is not yet the complete product backend. The current production API is a FastAPI service with Firebase user authentication, OIDC-protected internal task endpoints, Firestore persistence, private GCS artifacts, Cloud Tasks dispatch and a Cloud Run Job execution boundary.

### Implemented backend capabilities

| Capability | API / infrastructure status |
| --- | --- |
| Firebase identity verification and user ownership checks | Implemented |
| Signed ZIP upload, private object storage and upload completion | Implemented |
| Python project CRUD and project settings persistence | Implemented |
| Asynchronous AST analysis and function/source snapshots | Implemented; Cloud Tasks in production |
| Experiment creation and deterministic train/validation/locked-test split | Implemented |
| CoverUp baseline execution, polling, metrics and artifacts | Implemented; Cloud Run Job in production configuration |
| DSPy/GEPA optimization, candidate validation and prompt lineage | Implemented; candidate is kept separate from baseline |
| Paired baseline-vs-candidate comparison and promotion gates | Implemented |
| `final_validation.json` and ownership-checked run artifacts | Implemented |
| Prompt version creation plus approve/reject API with audit fields | Implemented; frontend review screen is still pending |
| Firestore repositories, GCS storage and OIDC internal task authentication | Implemented |

### Backend work still required before calling it production-complete

- Push/deploy the latest backend workflow authentication fix and run the full production smoke path through review.
- Add durable GEPA checkpoint/resume, explicit cancellation, retry/idempotency handling and isolated candidate/replicate workspaces.
- Add workspace quotas and cost/concurrency limits, artifact retention/cleanup and operational monitoring/alerts.
- Complete Firestore ownership/isolation tests, fake-executor contract tests and malformed/timeout runner tests.
- Freeze dataset/project/settings checksums and baseline coverage denominators for reproducible comparisons.

These items are hardening and scale work; they do not block connecting the already-implemented experiment vertical slice to the frontend.

## Frontend status

The frontend is deployed at [https://vinaip002.web.app](https://vinaip002.web.app). It uses Firebase Authentication and a hybrid data mode: Project, Experiment, baseline, optimization and paired-comparison features call the production API, while screens without a connected backend slice remain demo data.

## Implemented web features

### Authentication and workspace access

- Email/password registration with display name.
- Email/password login and logout.
- Password reset email flow.
- Google Sign-In.
- Protected workspace routes: unauthenticated visitors are redirected to `/login`.
- Firebase manages session refresh; the browser does not store an API token manually.

### Python projects and source upload

- Create a Python project with name, description, branch, commit and ZIP archive.
- Upload ZIP files directly from the browser to a private Cloud Storage bucket through a short-lived signed URL.
- Validate upload metadata and archive size before the project is created.
- List projects and open a project detail page.
- View project runtime, dependency, test, coverage and security settings in the UI.

### Project analysis

- Automatically start analysis after creating a project; users can also run **Re-analyze** from Project Detail.
- Show queued/running/failed/ready states and poll only while analysis is running.
- Process analysis asynchronously with Cloud Tasks, so the browser request returns immediately.
- Safely inspect the uploaded ZIP and extract Python functions, methods, async functions, source ranges, LOC, statement count and branch candidates using Python AST.
- View analyzed functions and open the exact extracted source for each function.

### Experiments, baseline, optimization and comparison

- List experiments owned by the signed-in user without fixture fallback.
- Create an experiment from one analyzed project and up to 50 selected functions.
- Queue and poll the isolated baseline run, then display aggregate and per-target coverage metrics.
- Download baseline artifacts through authenticated ownership-checked API endpoints.
- Start GEPA optimization only for experiments with non-empty train, validation and locked test splits.
- Poll optimization status and display the selected candidate prompt, validation scores, prompt lineage and artifacts.
- Start and poll the paired final comparison on the locked test split.
- Display baseline/candidate score, statement and branch coverage, pass rate, absolute/relative gain and promotion-gate decision.
- Download the ownership-checked `final_validation.json` comparison artifact.

### Available UI screens

- Dashboard, Projects, Project Detail, Create Experiment, Experiments, Runs/Comparison, Prompt Registry, Playground, Datasets and Settings.
- Projects, Project Analysis, Experiments, Baseline Runs, Optimization Runs and Paired Comparison use production backend data. Review, Dashboard and Datasets remain UI/demo workflows until their next vertical slices are connected.

### Current delivery status

| Capability | Status |
| --- | --- |
| Firebase login, registration, reset password and Google Sign-In | Production |
| Project ZIP upload and project metadata | Production |
| Async Python AST analysis and function source viewer | Production |
| Project settings UI | UI ready; persistence is available for project settings API |
| Experiment creation, baseline run and GEPA optimization | Production API connected in frontend |
| Paired comparison | Production API connected in frontend |
| Prompt review and approve/reject | Backend implemented; frontend integration pending |

### Frontend/API integration boundary

The following screens can use the real API now and should not reintroduce fixture repositories:

- Projects, ZIP upload, project detail/settings and Python function analysis.
- Experiment creation, baseline run, optimization run and paired comparison.

The following screens still require an API slice before their mock data can be deleted:

- Dashboard KPI/activity data: no dashboard aggregate endpoint exists yet.
- Datasets: the UI currently imports `mocks/fixtures/platform`; experiment split data is returned inside an experiment but there is no standalone dataset repository/API.
- Review & Approval: backend prompt-version GET/approve/reject exists, but the page still contains hard-coded review queue and prompt content.
- Prompt Registry: no prompt-version list/search/archive endpoint is connected to the page.
- Playground: currently a static UI/code example, not a persisted execution feature.

`DemoAuthService` and `VITE_DATA_MODE=demo` may remain for local UI development. They are not production fallbacks. Production should use `VITE_AUTH_MODE=firebase` and `VITE_DATA_MODE=connected`; an API error must remain visible instead of silently switching to mock data.

The frontend can also run in these modes during development:

| Auth mode | Data mode | Use case |
| --- | --- | --- |
| `demo` | `demo` | Local development and UI review |
| `firebase` | `demo` | Public frontend with real login before backend APIs exist |
| `firebase` | `connected` | Production frontend connected to `/api/v1` |

## Connect a Firebase project

The first production project is connected:

| Resource | Value |
| --- | --- |
| Firebase project | `vinaip002` |
| Firebase Web App | `PromptOpt Frontend` |
| Web App ID | `1:891999064201:web:69022a3951a6ff42eaf658` |
| Hosting site | `vinaip002` |
| Live URL | `https://vinaip002.web.app` |
| Preview channels | None; feature branches are tested locally |

Firebase Authentication supports Google Sign-In and Email/Password login, registration and password reset. The production Hosting domain is authorized. Production uses real Firebase authentication and a hybrid data mode: Projects uses the real API, while modules without backend slices continue to use explicit demo repositories.

The ignored `codebase/frontend/.env.local` contains the Firebase Web App configuration. Feature branches are reviewed locally:

```powershell
cd codebase\frontend
npm ci
npm run dev
```

Do not commit `.env.local`, service-account JSON files, generated credentials or OAuth client secrets. Firebase Web App values are public identifiers, but deployment credentials must use Workload Identity Federation.

Merges to `main` deploy automatically. A manual production deploy, when explicitly needed, uses:

```powershell
firebase deploy --only hosting:frontend --project vinaip002
```

## GitHub production deployment

The production workflow is fully configured with keyless Google Cloud authentication:

```text
Workload Identity Pool: github-actions
Provider: p002-main
Allowed identity: binh39/P-002 on refs/heads/main
Service account: github-frontend-deploy@vinaip002.iam.gserviceaccount.com
Project roles: roles/firebasehosting.admin, roles/run.viewer
```

`frontend-deploy.yml` retrieves the Firebase Web App config at runtime after WIF authentication, then builds and deploys Hosting after a merge to `main`. It does not require a service-account key or GitHub secret. Create the optional GitHub Environment named `production` only when you want approval gates or environment protection rules.

## Backend production

The first vertical slice is deployed in Singapore:

| Resource | Value |
| --- | --- |
| Cloud Run | `promptopt-api` |
| Region | `asia-southeast1` |
| API through Hosting | `https://vinaip002.web.app/api/v1` |
| Firestore | `(default)`, Native mode, `asia-southeast1` |
| Artifact Registry | `asia-southeast1-docker.pkg.dev/vinaip002/promptopt` |
| Private source bucket | `vinaip002-promptopt-sources` |
| Analysis task queue | `promptopt-analysis` |
| Experiment task queue | `promptopt-baseline` |
| CoverUp Cloud Run Job | `promptopt-coverup-runner` |
| Runner identity | `promptopt-runner@vinaip002.iam.gserviceaccount.com` |
| Runtime identity | `promptopt-api@vinaip002.iam.gserviceaccount.com` |
| Deploy identity | `github-backend-deploy@vinaip002.iam.gserviceaccount.com` |

The bucket has public access prevention and only permits browser `PUT` requests from the production domains through short-lived signed URLs. Firebase Hosting rewrites `/api/**` to Cloud Run. Backend changes under `codebase/src/**` build and deploy independently after merging to `main` through `.github/workflows/backend-deploy.yml`.

Project analysis runs asynchronously through Cloud Tasks. Production extracts Python functions and source ranges with `ast`, stores function snapshots below each Firestore project, and exposes them through the authenticated Projects API. The frontend polls only while a project is analyzing and does not fall back to fixture data when an API call fails.

### Provision the production runner once

The deployment workflow builds separate API and CoverUp images. It deploys the CoverUp image as a Cloud Run Job with one task, no retries, a 15-minute timeout and a dedicated runtime identity. Before the first merge that contains the runner workflow, a project administrator must run:

```powershell
cd codebase
.\infra\provision-production-runner.ps1
```

The script enables the required APIs, creates `promptopt-runner` when absent, and creates a custom object role containing only `storage.objects.get/create`. An IAM condition restricts that role to the opaque `runner-jobs/` prefix; the runner cannot list, overwrite or delete bucket objects and cannot read original uploads outside this prefix. A second project-level custom role grants the API only `run.operations.get`, which is required to poll the long-running operation after starting a job; permission to run with overrides remains scoped to the individual runner Job by the deployment workflow. The script also grants Vertex AI access, lets the GitHub deploy identity attach the runner account, and creates or limits the `promptopt-baseline` queue. It does not create service-account keys or store credentials.

The API writes source, prompt and a versioned execution manifest under `runner-jobs/<execution-id>/` in the private bucket. The Cloud Run Job receives only the bucket and object prefix as overrides, uses its workload identity to read/write those objects, and publishes `result.json` plus artifacts. No Docker socket, ADC file or prompt/source payload is passed on the command line.

Current limitation: each CoverUp evaluation is one Cloud Run Job execution. Baseline and paired comparison fit the Cloud Tasks 30-minute request deadline. A large GEPA search still needs durable checkpoint/resume orchestration before it should be enabled for high `max_metric_calls` in production.

### Production smoke test

Run the production smoke script from the repository root. It asks for a fresh Firebase **ID token**; Google Cloud CLI login alone is not a Firebase user session.

```powershell
# Upload → analysis → one-target baseline
.\codebase\scripts\smoke_production.ps1

# Upload → analysis → three-target baseline → optimize → paired comparison → review when eligible
.\codebase\scripts\smoke_production.ps1 -FullPipeline -ReviewDecision approve
```

The full mode selects the requested target plus two deterministic valid functions, because optimization needs non-empty train, validation and locked-test splits. A candidate that fails the promotion gate finishes as `comparison_succeeded`; in that case review is intentionally not called and the script emits a warning. Results are sanitized and written under ignored `codebase/.smoke-results/`; do not commit raw smoke output, Firebase user identifiers, private artifact paths or fixture archives.
