# PromptOpt frontend

React 19, TypeScript, Vite and Tailwind CSS frontend for PromptOpt.

## Local development

```powershell
Copy-Item .env.example .env.local
npm ci
npm run dev
```

The default `VITE_AUTH_MODE=demo` uses an explicit demo session. Set it to `firebase` for Firebase Google Sign-In.

The connected Firebase project is `vinaip002`. Its current preview is `https://vinaip002--frontend-foundation-k738rydv.web.app` and expires on 2026-08-12. Local Firebase values belong in the ignored `.env.local`; start from `.env.example` on a new machine.

The independent `VITE_DATA_MODE=demo` uses repository-backed fixtures and displays a `demo data` badge. Set it to `connected` feature-by-feature only when the matching `/api/v1` endpoints are available. Connected mode never falls back to demo data when an API request fails.

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
