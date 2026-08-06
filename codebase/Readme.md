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

## Frontend status

The frontend is deployed at [https://vinaip002.web.app](https://vinaip002.web.app). It uses Firebase Authentication and a hybrid data mode: implemented Project features call the production API, while screens without a backend slice remain clearly marked as demo data.

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

### Available UI screens

- Dashboard, Projects, Project Detail, Create Experiment, Experiments, Runs/Comparison, Prompt Registry, Playground, Datasets and Settings.
- Only the Projects and Project Analysis flow currently uses production backend data. The remaining product screens are UI/demo workflows and do not silently fall back when a connected API call fails.

### Current delivery status

| Capability | Status |
| --- | --- |
| Firebase login, registration, reset password and Google Sign-In | Production |
| Project ZIP upload and project metadata | Production |
| Async Python AST analysis and function source viewer | Production |
| Project settings UI | UI ready; persistence is available for project settings API |
| Experiments, optimization runs, coverage execution and prompt optimization | UI/demo only; backend slice is next |

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
| Runtime identity | `promptopt-api@vinaip002.iam.gserviceaccount.com` |
| Deploy identity | `github-backend-deploy@vinaip002.iam.gserviceaccount.com` |

The bucket has public access prevention and only permits browser `PUT` requests from the production domains through short-lived signed URLs. Firebase Hosting rewrites `/api/**` to Cloud Run. Backend changes under `codebase/src/**` build and deploy independently after merging to `main` through `.github/workflows/backend-deploy.yml`.

Project analysis runs asynchronously through Cloud Tasks. Production extracts Python functions and source ranges with `ast`, stores function snapshots below each Firestore project, and exposes them through the authenticated Projects API. The frontend polls only while a project is analyzing and does not fall back to fixture data when an API call fails.
