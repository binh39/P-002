# Projects vertical slice

This slice is the first production-shaped PromptOpt backend module. It owns authenticated ZIP uploads, project metadata and versioned Python execution settings.

## Local development

Install dependencies and start the API:

```powershell
cd codebase
python -m pip install -r requirements-dev.txt
$env:APP_ENV = "development"
$env:AUTH_MODE = "disabled"
$env:REPOSITORY_BACKEND = "memory"
$env:STORAGE_BACKEND = "local"
uvicorn src.main:app --reload --port 8000
```

Local protected endpoints require this header:

```text
Authorization: Bearer dev-token
```

The frontend remains visual/mock by default. To connect it to this API, run it with Firebase auth configured and:

```env
VITE_DATA_MODE=connected
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## API flow

```text
POST /api/v1/uploads
  -> PUT the ZIP to upload_url
  -> POST /api/v1/uploads/{upload_id}/complete
  -> POST /api/v1/projects
  -> GET /api/v1/projects
  -> GET /api/v1/projects/{project_id}
  -> PATCH /api/v1/projects/{project_id}/settings
```

Both `/health` and `/api/v1/health` are available. OpenAPI is served at `/docs` in the current build.

## Docker

Build and run from the `codebase` directory:

```powershell
docker build -t promptopt-api:local .
docker run --rm -p 8000:8000 `
  -e APP_ENV=development `
  -e AUTH_MODE=disabled `
  -e REPOSITORY_BACKEND=memory `
  -e STORAGE_BACKEND=local `
  promptopt-api:local
```

The runtime image installs only `requirements.txt`; local quality tools are isolated in `requirements-dev.txt`. It runs as non-root user `appuser` and only contains `/app/src` plus its writable data directory.

## Production configuration

Production startup fails fast unless all real adapters are enabled:

```env
APP_ENV=production
AUTH_MODE=firebase
REPOSITORY_BACKEND=firestore
STORAGE_BACKEND=gcs
GCP_PROJECT_ID=vinaip002
GCP_SERVICE_ACCOUNT_EMAIL=promptopt-api@vinaip002.iam.gserviceaccount.com
GCS_BUCKET=<private-source-bucket>
CORS_ORIGINS=https://vinaip002.web.app,https://c3-app-002.io.vn
```

The Cloud Run runtime service account needs only:

- Firestore read/write access for `projects` and `uploads`.
- Firebase Authentication viewer access because revoked-token checking reads the user record.
- Object create/read metadata access on the private source bucket.
- Permission to sign V4 upload URLs (`iam.serviceAccounts.signBlob`, normally granted with Service Account Token Creator on itself).

Configure bucket CORS to allow `PUT` with `Content-Type` from the production frontend origins. Do not make the bucket public. Uploaded size is verified again before a project can reference the archive.

The deployed production resources are `promptopt-api`, Firestore `(default)` and bucket `vinaip002-promptopt-sources` in `asia-southeast1`. The public same-origin API base is `https://vinaip002.web.app/api/v1`; the direct Cloud Run URL is an implementation detail.

## Deliberate boundary

Project analysis is the next slice. The connected frontend calls the future function endpoints explicitly and shows an API error until they exist; it never falls back silently to mock function data. The next backend contract is:

```text
POST /api/v1/projects/{project_id}/analyze -> 202
GET  /api/v1/projects/{project_id}/functions
GET  /api/v1/projects/{project_id}/functions/{function_id}/source
```
