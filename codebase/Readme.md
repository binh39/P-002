# PromptOpt application

## Frontend status

The frontend can be deployed before the backend in either of these combinations:

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

Firebase Authentication supports Google Sign-In and Email/Password login, registration and password reset. The production Hosting domain is authorized. The deployed frontend uses real Firebase authentication with repository-backed demo data because the backend is not deployed.

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
Project role: roles/firebasehosting.admin
```

`frontend-deploy.yml` retrieves the Firebase Web App config at runtime after WIF authentication, then builds and deploys Hosting after a merge to `main`. It does not require a service-account key or GitHub secret. Create the optional GitHub Environment named `production` only when you want approval gates or environment protection rules.
