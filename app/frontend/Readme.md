# PromptOpt frontend

React 19, TypeScript, Vite and Tailwind CSS frontend for PromptOpt.

## Local development

```powershell
Copy-Item .env.example .env.local
npm ci
npm run dev
```

The checked-in example is a working full-local profile: `VITE_AUTH_MODE=demo` returns the backend's explicit `dev-token`, `VITE_DATA_MODE=connected` uses HTTP repositories, and `VITE_API_PROXY_TARGET=http://127.0.0.1:8000` sends `/api` to the local FastAPI process. This token is accepted only when the backend uses `AUTH_MODE=disabled`.

Set `VITE_AUTH_MODE=firebase` and fill the public Firebase Web App identifiers for Firebase Google Sign-In, Email/Password login, registration and password reset. Production builds must use Firebase mode; never put a service-account credential in a `VITE_*` variable.

The connected Firebase project is `project-7df9f963-9fe0-4b76-b3d`, with production at `https://project-7df9f963-9fe0-4b76-b3d.web.app`. Feature branches are tested with `npm run dev`; no public preview channel is kept. Local Firebase values belong in the ignored `.env.local`; start from `.env.example` on a new machine.

Projects, experiment creation, GEPA optimization runs and paired comparisons always use authenticated HTTP repositories and never fall back to fixture data. GEPA treats the baseline prompt as candidate zero; there is no separate baseline run. `VITE_DATA_MODE=demo` only keeps the dashboard on fixture data, so use `connected` when verifying the full local API path.

## Quality checks

```powershell
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run build
```

## Data boundary

Pages access remote data through repository contracts under `src/repositories/contracts`. Demo and HTTP implementations live separately under `mock` and `http`. New backend integrations should replace the implementation selected in `src/app/providers.tsx`, not introduce `fetch` calls inside page components.
