# PromptOpt frontend

React 19, TypeScript, Vite and Tailwind CSS frontend for PromptOpt.

## Local development

```powershell
Copy-Item .env.example .env.local
npm ci
npm run dev
```

The default `VITE_AUTH_MODE=demo` uses an explicit demo session. Set it to `firebase` for Firebase Google Sign-In plus Email/Password login, registration and password reset.

The connected Firebase project is `vinai-505107`, with production at `https://vinai-505107.web.app`. Feature branches are tested with `npm run dev`; no public preview channel is kept. Local Firebase values belong in the ignored `.env.local`; start from `.env.example` on a new machine.

Projects, experiment creation, GEPA optimization runs and paired comparisons always use authenticated HTTP repositories and never fall back to fixture data. GEPA treats the baseline prompt as candidate zero; there is no separate baseline run. `VITE_DATA_MODE=demo` keeps unfinished dashboard, dataset and review screens in demo mode, so the UI displays a `hybrid data` badge until those slices are connected.

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
