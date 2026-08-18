# PromptOpt Delivery Checklist

## Production migration â€” 2026-08-10

- [X]  Migrated production to GCP/Firebase project `project-7df9f963-9fe0-4b76-b3d`.
- [X]  Provisioned Artifact Registry, private GCS, Firestore, Cloud Tasks, runtime/deploy service accounts, IAM and GitHub WIF with `app/infra/provision-production.ps1`.
- [X]  Enabled Firebase Email/Password and Google Sign-In on the new project.
- [X]  Configured Firebase Hosting at `https://project-7df9f963-9fe0-4b76-b3d.web.app`.
- [ ]  Run authenticated production smoke tests for baseline, optimization, comparison and prompt review on the new project.

## Current handoff â€” 2026-08-08 (authoritative)

> ÄÃ¢y lÃ  tráº¡ng thÃ¡i hiá»‡n táº¡i vÃ  thá»© tá»± thá»±c hiá»‡n Ä‘Æ°á»£c Ä‘á» xuáº¥t. Náº¿u má»™t má»¥c lá»‹ch sá»­ phÃ­a dÆ°á»›i mÃ¢u
> thuáº«n vá»›i pháº§n nÃ y hoáº·c `Readme.md`, dÃ¹ng pháº§n Current handoff lÃ m nguá»“n Ä‘Ãºng. CÃ¡c phase cÅ© Ä‘Æ°á»£c
> giá»¯ láº¡i Ä‘á»ƒ báº£o toÃ n lá»‹ch sá»­ quyáº¿t Ä‘á»‹nh.

### ÄÃ£ hoÃ n thÃ nh: ná»n táº£ng vÃ  production vertical slice

- [X]  Frontend React/Vite deploy táº¡i `https://project-7df9f963-9fe0-4b76-b3d.web.app`.
- [X]  Firebase Email/Password, Google Sign-In, register, login, logout vÃ  reset password.
- [X]  FastAPI production cháº¡y trÃªn Cloud Run, Ä‘Æ°á»£c Firebase Hosting rewrite qua `/api/v1`.
- [X]  Firebase token verification, owner-scoped API, Firestore repositories vÃ  private GCS.
- [X]  Signed ZIP upload, project CRUD/settings, async AST analysis vÃ  function source viewer.
- [X]  Cloud Tasks + OIDC internal endpoints cho analysis/baseline orchestration.
- [X]  API container khÃ´ng cháº¡y source ngÆ°á»i dÃ¹ng; CoverUp vÃ  GEPA cháº¡y trong hai Cloud Run Jobs riÃªng.
- [X]  GitHub Actions dÃ¹ng Workload Identity Federation; khÃ´ng dÃ¹ng service-account JSON key.
- [X]  Frontend vÃ  backend CI/deploy Ä‘á»™c láº­p theo path filter; merge vÃ o `main` deploy production.

### ÄÃ£ hoÃ n thÃ nh: Experiment UI vÃ  backend contract

- [X]  Chá»n nhiá»u project, khÃ´ng giá»›i háº¡n cá»©ng 50 target á»Ÿ request contract.
- [X]  Sampling random/most branches/most statements/manual hoáº¡t Ä‘á»™ng á»Ÿ backend.
- [X]  `random_seed`, custom train/validation/test percentages vÃ  manual splits Ä‘Æ°á»£c lÆ°u/cháº¡y tháº­t.
- [X]  Dropdown COVERUP_MODEL/OPTIMIZE_MODEL; selected models Ä‘Æ°á»£c truyá»n xuá»‘ng jobs.
- [X]  Max attempts, repeat tests, concurrency, rate limit, pytest args, max metric calls,
  evaluation replicates vÃ  reflection temperature Ä‘Æ°á»£c ná»‘i frontend -> API -> runner.
- [X]  Review cáº¥u hÃ¬nh, create experiment, delete experiment vÃ  owner-scoped experiment list.
- [X]  Queue/poll baseline, optimization vÃ  paired comparison báº±ng API tháº­t.
- [X]  Metrics, artifacts, candidate prompt, lineage vÃ  promotion decision hiá»ƒn thá»‹ trÃªn frontend.
- [X]  Prompt review queue vÃ  approve/reject cÃ³ comment/audit/idempotent decision.

### ÄÃ£ hoÃ n thÃ nh: sample repositories vÃ  auto-setup

- [X]  Catalog read-only cho `isort`, `mimesis`, `mlxtend`, `typesystem`; khÃ´ng ghi sample Project/Function dÆ°
  vÃ o Firestore.
- [X]  Sample snapshots Ä‘Æ°á»£c deploy tá»« `src/sample_repo.zip`; CI tá»± extract trÆ°á»›c test/build.
- [X]  Preflight khÃ´ng cháº¡y setup script cá»§a repo; táº¡o minimal distribution metadata vÃ  validate imports
  trÆ°á»›c khi gá»i Gemini.
- [X]  isort: cung cáº¥p metadata + `tomli`; loáº¡i `_vendored` vÃ  `deprecated` theo coverage config.
- [X]  mlxtend: validate NumPy, SciPy, Pandas, scikit-learn, Matplotlib vÃ  joblib.
- [X]  typesystem: validate Jinja2 vÃ  YAML.
- [X]  LÆ°u `project_setup.json` lÃ m artifact cháº©n Ä‘oÃ¡n cho baseline/GEPA.
- [X]  CÃ¹ng setup environment Ä‘Æ°á»£c dÃ¹ng khi sinh test vÃ  khi Ä‘o coverage cuá»‘i.

### ÄÃ£ hoÃ n thÃ nh trong code: exact-target baseline fix

- [X]  PhÃ¢n tÃ­ch artifact isort 10 target: setup pass nhÆ°ng `G=0, F=19, U=4`, khÃ´ng cÃ³ accepted
  `.py`; 0% khi Ä‘Ã³ lÃ  káº¿t quáº£ tháº­t, khÃ´ng pháº£i lá»—i cÃ´ng thá»©c coverage.
- [X]  XÃ¡c Ä‘á»‹nh runner cÅ© match 10 target thÃ nh 9 segment; `Config.__init__` bá»‹ bá» vÃ¬ chá»‰ lá»c tÃªn hÃ m.
- [X]  Thay contract protocol v1 báº±ng protocol v2 cÃ³ exact `source_file + qualified_name`.
- [X]  Baseline web dÃ¹ng `--target-spec-file` vÃ  `--prompt-template-file` giá»‘ng pipeline `cloud`.
- [X]  Loáº¡i wrapper `VersionedPrompter/get_missing_coverage` cÅ© khá»i sandbox entrypoint.
- [X]  Äá»“ng bá»™ baseline/error prompt vá»›i prompt chuáº©n cá»§a GEPA, gá»“m hÆ°á»›ng dáº«n dÃ¹ng `get_info`.
- [X]  Metrics map theo `source_file::qualified_name`, khÃ´ng nháº§m function trÃ¹ng tÃªn giá»¯a cÃ¡c file.
- [X]  Giá»¯ structured attempt trace cá»§a CoverUp; chá»‰ parse raw log lÃ m fallback.
- [X]  Zero-test baseline giá»¯ denominator há»£p lá»‡ vÃ  khÃ´ng bÃ¡o covered branch khi covered statements = 0.
- [X]  Backend test **38 passed**, optimizer invariant test **51 passed**, Ruff/py_compile/diff check pass.
- [X]  Build local thÃ nh cÃ´ng API image vÃ  CoverUp runner image sau báº£n sá»­a.
- [ ]  Merge/deploy báº£n exact-target fix lÃªn `main`; production hiá»‡n chÆ°a Ä‘Æ°á»£c xem lÃ  Ä‘Ã£ xÃ¡c nháº­n cho
  tá»›i khi backend deploy workflow xanh.

### P0 â€” XÃ¡c nháº­n runner má»›i trÃªn production

- [ ]  XÃ¡c nháº­n CI backend vÃ  backend deployment Ä‘á»u xanh trÃªn cÃ¹ng commit.
- [ ]  XÃ¡c nháº­n `promptopt-api` revision, `promptopt-coverup-runner` vÃ  `promptopt-gepa-runner` cÃ¹ng
  dÃ¹ng image SHA cá»§a release má»›i.
- [ ]  Táº¡o **experiment má»›i** cho isort; khÃ´ng dÃ¹ng láº¡i run/artifact trÆ°á»›c exact-target fix.
- [ ]  Smoke 10 random/manual target báº±ng `gemini-2.5-flash`, `max_attempts=5`, `repeat_tests=2`.
- [ ]  XÃ¡c nháº­n sá»‘ exact target trong spec báº±ng sá»‘ target Ä‘Ã£ chá»n; khÃ´ng cÃ²n 10 -> 9 ngoÃ i trÆ°á»ng há»£p
  nhiá»u targets chá»§ Ä‘á»™ng trá» cÃ¹ng má»™t function.
- [ ]  XÃ¡c nháº­n `project_setup.json.import_validation=passed`.
- [ ]  XÃ¡c nháº­n `attempt_trace.jsonl` cÃ³ outcome theo target; náº¿u cÃ³ test tá»‘t pháº£i tháº¥y
  `coverage_gain_saved`.
- [ ]  XÃ¡c nháº­n `generated_tests.zip` chá»©a `test_opt_*.py` khi G > 0.
- [ ]  XÃ¡c nháº­n `target_coverage.json` dÃ¹ng key `source_file::qualified_name` vÃ  aggregate khá»›p raw units.
- [ ]  Smoke `typesystem`, sau Ä‘Ã³ `mlxtend`; ghi láº¡i model/settings/cost/latency vÃ  failure categories.
- [ ]  Cháº¡y full production pipeline baseline -> optimize -> locked comparison -> review.
- [ ]  LÆ°u sanitized release evidence; khÃ´ng commit UID, token, signed URL, private object path hoáº·c
  raw `CheckOutput`.

### P1 â€” TÄƒng cháº¥t lÆ°á»£ng baseline vÃ  kháº£ nÄƒng cháº©n Ä‘oÃ¡n

- [ ]  Hiá»ƒn thá»‹ trá»±c tiáº¿p trÃªn UI sá»‘ `G/F/U/R`, accepted test count vÃ  nguyÃªn nhÃ¢n attempt tháº¥t báº¡i.
- [ ]  Hiá»ƒn thá»‹ cáº£nh bÃ¡o khi chá»n â€œmost statementsâ€ vá»›i function quÃ¡ lá»›n; khÃ´ng tá»± thay Ä‘á»•i lá»±a chá»n
  hoáº·c model cá»§a ngÆ°á»i dÃ¹ng.
- [ ]  ThÃªm artifact manifest version/checksum/size/content type cho má»i baseline output.
- [ ]  ThÃªm runner tests cho malformed model response, empty response, timeout, partial artifact upload
  vÃ  target khÃ´ng tá»“n táº¡i.
- [ ]  ÄÃ¡nh giÃ¡ cÆ¡ cháº¿ giá»¯ cÃ¡c test function pass khi má»™t generated module cÃ³ cáº£ test pass vÃ  fail;
  chá»‰ triá»ƒn khai náº¿u váº«n Ä‘áº£m báº£o isolation/determinism vÃ  cÃ³ regression tests.
- [ ]  ThÃªm controlled benchmark matrix cho sample repo/model/sampling method; má»—i láº§n benchmark dÃ¹ng
  artifacts directory má»›i vÃ  budget Ä‘Æ°á»£c phÃª duyá»‡t.
- [ ]  KhÃ´ng coi unit tests pass lÃ  báº±ng chá»©ng prompt/model táº¡o coverage tá»‘t; chá»‰ káº¿t luáº­n báº±ng live
  benchmark cÃ¹ng evaluation protocol.

### P2 â€” Correctness vÃ  recovery

- [ ]  Idempotency key/transaction cho create baseline, optimize, compare vÃ  Cloud Task retry.
- [ ]  Cháº·n double-click táº¡o hai active runs cÃ¹ng loáº¡i cho má»™t experiment.
- [ ]  Cancellation API/state cho baseline, optimization, comparison vÃ  Cloud Run Job execution.
- [ ]  PhÃ¢n biá»‡t rÃµ failed/timed_out/cancelled/queue failure/provider failure.
- [ ]  Durable GEPA checkpoint/resume vÆ°á»£t giá»›i háº¡n Cloud Tasks 30 phÃºt.
- [ ]  Freeze project/source/settings checksum, dataset checksum vÃ  baseline denominators.
- [ ]  Version execution/result/coverage/final-validation schemas vÃ  migration strategy cho document cÅ©.
- [ ]  Persist model/provider, token usage, estimated cost, latency vÃ  normalized runner config.

### P3 â€” HoÃ n thiá»‡n frontend khÃ´ng mock

- [ ]  ThÃªm Dashboard aggregate API rá»“i chuyá»ƒn workflow production sang `VITE_DATA_MODE=connected`.
- [ ]  Quyáº¿t Ä‘á»‹nh Datasets lÃ  resource Ä‘á»™c láº­p hay experiment snapshot; ná»‘i API hoáº·c bá» route.
- [ ]  XÃ³a import trá»±c tiáº¿p `mocks/fixtures/platform` khá»i `Datasets.tsx`.
- [ ]  Quyáº¿t Ä‘á»‹nh Playground lÃ  production feature hay demo-only; náº¿u production pháº£i dÃ¹ng isolated
  runner, auth, quota vÃ  cost ceiling.
- [ ]  Ná»‘i/kiá»ƒm tra Save project settings end-to-end.
- [ ]  Kiá»ƒm tra loading/empty/error/retry/403/expired-session cho má»i production screen.
- [ ]  Responsive, keyboard navigation, focus, labels, contrast vÃ  browser E2E.

### P4 â€” Security, quota, observability vÃ  lifecycle

- [ ]  Tenant-isolation tests cho project/experiment/run/prompt/artifact giá»¯a user A vÃ  user B.
- [ ]  Threat model vÃ  tests cho traversal, symlink, device file, ZIP bomb vÃ  malicious generated test.
- [ ]  Quota theo user/workspace: uploads, targets, active jobs, LLM calls, runtime vÃ  cost ceiling.
- [ ]  Rate limit, budget alert vÃ  emergency kill switch cho CoverUp/GEPA.
- [ ]  Artifact/source retention, cascade delete vÃ  scheduled cleanup cÃ³ dry-run/audit/retry.
- [ ]  Correlation IDs vÃ  structured logs xuyÃªn request -> task -> job -> artifact.
- [ ]  Cloud Monitoring dashboard/alerts cho API, queue, job, provider vÃ  cost.
- [ ]  Staging riÃªng, Firestore backup/restore, dependency/container scans vÃ  rollback drill.

### Definition of Done gáº§n nháº¥t

- [ ]  Ba sample repo cÃ³ production smoke evidence sau exact-target fix.
- [ ]  User hoÃ n thÃ nh Ä‘Æ°á»£c baseline -> optimize -> compare -> review trÃªn UI production.
- [ ]  KhÃ´ng cÃ²n mock trÃªn production routes hoáº·c mock Ä‘Æ°á»£c gáº¯n nhÃ£n demo-only rÃµ rÃ ng.
- [ ]  Retry/double-submit/timeout/restart khÃ´ng táº¡o duplicate hoáº·c state sai.
- [ ]  Quota, cost controls, monitoring, alerts, retention vÃ  tenant isolation Ä‘Æ°á»£c kiá»ƒm chá»©ng.
- [ ]  CI/CD xanh, keyless, cÃ³ staging/E2E/rollback evidence.

---

> Má»¥c tiÃªu hiá»‡n táº¡i: biáº¿n frontend prototype thÃ nh frontend production-ready, váº«n demo Ä‘Æ°á»£c khi backend chÆ°a hoÃ n thiá»‡n, sau Ä‘Ã³ deploy Firebase Hosting. Backend chá»‰ deploy khi cÃ³ vertical slice Ä‘áº§u tiÃªn hoáº¡t Ä‘á»™ng; khÃ´ng deploy boilerplate hiá»‡n táº¡i.

## NguyÃªn táº¯c Ä‘Ã£ chá»‘t

- [ ]  `main` luÃ´n deploy production; má»i thay Ä‘á»•i Ä‘i qua pull request.
- [ ]  Feature branch chá»‰ lint, typecheck, test vÃ  build; khÃ´ng deploy production.
- [X]  Frontend vÃ  backend deploy Ä‘á»™c láº­p báº±ng path filter trong GitHub Actions.
- [ ]  UI khÃ´ng import dá»¯ liá»‡u mock trá»±c tiáº¿p trong page/component.
- [ ]  Mock vÃ  HTTP cÃ¹ng implement má»™t repository/service interface.
- [ ]  Production khÃ´ng tá»± fallback tá»« API sang mock khi API lá»—i.
- [ ]  CÃ¡c tÃ¡c vá»¥ optimization luÃ´n cháº¡y báº¥t Ä‘á»“ng bá»™; API khÃ´ng chá» Gemini/pytest hoÃ n táº¥t.
- [ ]  Public frontend khÃ´ng Ä‘á»“ng nghÄ©a vá»›i public Python code execution; tÃ­nh nÄƒng cháº¡y code pháº£i cÃ³ auth vÃ  quota.

---

## Phase 1 â€” Audit vÃ  dá»n frontend prototype

### 1.1 Dá»n project sinh tá»« Figma

- [X]  Táº¡o branch `feature/frontend-foundation`.
- [X]  Chá»‰ giá»¯ cÃ¡c plugin Figma thá»±c sá»± cáº§n; loáº¡i bá» `.figma` plugin khá»i production Vite config.
- [ ]  Sá»­a encoding lá»—i trong metadata vÃ  source (`PromptOpt Ã¢â‚¬â€`, comment tiáº¿ng Viá»‡t bá»‹ mojibake).
- [X]  Äá»•i package name tá»« `figma-make-app` thÃ nh `promptopt-frontend`.
- [X]  Chá»n má»™t package manager duy nháº¥t: npm.
- [X]  Giá»¯ `package-lock.json` vÃ  xÃ³a `pnpm-lock.yaml`.
- [X]  Chuáº©n hÃ³a Node version báº±ng `.nvmrc` vÃ  trÆ°á»ng `engines` trong `package.json`.
- [ ]  Kiá»ƒm tra vÃ  bá» dependency khÃ´ng sá»­ dá»¥ng.
- [X]  ThÃªm title, description, theme color vÃ  Open Graph metadata Ä‘Ãºng tÃªn sáº£n pháº©m (favicon riÃªng cÃ²n chá» brand asset).
- [ ]  Quyáº¿t Ä‘á»‹nh robots: production cho phÃ©p index hoáº·c tiáº¿p tá»¥c `noindex` náº¿u Ä‘ang private beta.

### 1.2 Bá»• sung quality scripts

- [X]  ThÃªm script `typecheck`: `tsc --noEmit`.
- [X]  ThÃªm ESLint vÃ  script `lint`.
- [X]  TÃ¡ch `format` vÃ  `format:check`.
- [X]  ThÃªm Vitest + React Testing Library vÃ  script `test`.
- [ ]  ThÃªm `test:coverage` náº¿u cáº§n coverage frontend.
- [X]  Äáº£m báº£o clean `npm ci`, lint, typecheck, test vÃ  production build cháº¡y thÃ nh cÃ´ng:

```powershell
cd app\frontend
npm ci
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run build
```

### 1.3 Cáº¥u trÃºc frontend Ä‘Ã­ch

- [ ]  Chuyá»ƒn tá»« cáº¥u trÃºc `pages + components` pháº³ng sang cáº¥u trÃºc theo feature:

```text
src/
  app/
    App.tsx
    router.tsx
    providers.tsx
  auth/
    AuthProvider.tsx
    ProtectedRoute.tsx
  features/
    dashboard/
    projects/
    experiments/
    runs/
    comparison/
    prompt-registry/
    settings/
  api/
    client.ts
    types.ts
  repositories/
    contracts/
    http/
    mock/
  components/
  config/
    env.ts
  mocks/
  test/
```

- [ ]  Giá»¯ shared component thá»±c sá»± dÃ¹ng chung trong `components/`; component riÃªng náº±m trong feature.
- [ ]  KhÃ´ng táº¡o má»™t file API/repository khá»•ng lá»“ cho má»i domain.
- [X]  Báº­t TypeScript strict vÃ  sá»­a toÃ n bá»™ type error.

---

## Phase 2 â€” Navigation, state vÃ  error handling thá»±c táº¿

- [X]  CÃ i router nháº¹ (`wouter`) vÃ  thay `useState<Page>` báº±ng URL routes.
- [X]  Äá»‹nh nghÄ©a cÃ¡c route ná»n táº£ng:

```text
/login
/dashboard
/projects/new
/experiments/:experimentId
/runs/:runId
/runs/:runId/compare
/prompts
/settings
```

- [X]  CÃ³ auth gate cho cÃ¡c trang cáº§n Ä‘Äƒng nháº­p (demo auth adapter; Firebase Auth sáº½ thay á»Ÿ Phase 4).
- [X]  Refresh hoáº·c má»Ÿ deep link giá»¯ Ä‘Ãºng URL phÃ­a client (Firebase SPA rewrite sáº½ hoÃ n thiá»‡n phÃ­a hosting).
- [X]  Trang khÃ´ng tá»“n táº¡i hiá»ƒn thá»‹ `404`.
- [X]  ThÃªm application-level error boundary.
- [ ]  Má»—i mÃ n hÃ¬nh dá»¯ liá»‡u cÃ³ Ä‘á»§ loading, empty, error vÃ  retry state.
- [ ]  KhÃ´ng lÆ°u server data trong global React state thá»§ cÃ´ng.
- [X]  DÃ¹ng TanStack Query cho Dashboard server state/cache.
- [X]  DÃ¹ng local state cho UI state nhÆ° form, tab vÃ  sidebar; tiáº¿p tá»¥c migrate server data á»Ÿ cÃ¡c feature cÃ²n láº¡i.
- [ ]  ThÃªm toast/notification dÃ¹ng chung.
- [ ]  Kiá»ƒm tra responsive desktop, tablet vÃ  mobile.
- [ ]  Kiá»ƒm tra keyboard navigation, focus state, label vÃ  contrast cÆ¡ báº£n.

---

## Phase 3 â€” CÃ´ láº­p vÃ  giáº£m mock data

### 3.1 Äá»‹nh nghÄ©a domain types trÆ°á»›c API

- [ ]  Äá»‹nh nghÄ©a `Project`, `Experiment`, `OptimizationRun`, `PromptVersion`, `Metrics`, `Artifact`.
- [ ]  Äá»‹nh nghÄ©a run state machine dÃ¹ng chung trong frontend:

```text
queued -> preparing -> baseline -> optimizing -> evaluating
       -> succeeded | failed | cancelled | timed_out
```

- [ ]  DÃ¹ng ID/string timestamp giá»‘ng contract backend dá»± kiáº¿n; khÃ´ng dÃ¹ng label UI lÃ m enum domain.
- [ ]  Táº¥t cáº£ metrics cÃ³ unit rÃµ rÃ ng: percent, seconds, token count, USD estimate.

### 3.2 Repository contracts

- [X]  Táº¡o interface `ProjectRepository` cho list/detail/create project vÃ  function contract káº¿ tiáº¿p.
- [ ]  Táº¡o interface `ExperimentRepository`.
- [ ]  Táº¡o interface `RunRepository`.
- [ ]  Táº¡o interface `PromptRepository`.
- [ ]  Page chá»‰ gá»i hooks/use cases, khÃ´ng gá»i `fetch` vÃ  khÃ´ng import mock fixture.
- [X]  Táº¡o `MockProjectRepository` vÃ  `HttpProjectRepository` dÃ¹ng cÃ¹ng contract; Projects khÃ´ng fallback Ã¢m tháº§m.
- [ ]  ÄÆ°a toÃ n bá»™ fixture vÃ o `src/mocks/fixtures`; khÃ´ng ráº£i object hardcode trong component.
- [ ]  Mock pháº£i mÃ´ phá»ng cáº£ latency, empty state vÃ  error state cÃ³ kiá»ƒm soÃ¡t.
- [X]  Táº¡o `DashboardRepository`, `MockDashboardRepository` vÃ  `HttpDashboardRepository` lÃ m máº«u chuáº©n Ä‘áº§u tiÃªn.

### 3.3 Cháº¿ Ä‘á»™ cháº¡y

- [X]  Validate environment variables hiá»‡n cÃ³ táº¡i startup báº±ng Zod.
- [X]  Chuáº©n bá»‹ `.env.example` ná»n táº£ng; bá»• sung Firebase variables á»Ÿ Phase 4:

```env
VITE_APP_MODE=demo
VITE_API_BASE_URL=/api/v1
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_STORAGE_BUCKET=
VITE_FIREBASE_APP_ID=
```

- [X]  `VITE_APP_MODE=demo`: dÃ¹ng mock repository vÃ  hiá»ƒn thá»‹ badge â€œdemo dataâ€.
- [X]  `VITE_APP_MODE=connected`: chá»‰ dÃ¹ng HTTP repository cho feature Ä‘Ã£ migrate.
- [X]  Connected mode hiá»ƒn thá»‹ lá»—i API tháº­t, khÃ´ng fallback Ã¢m tháº§m sang mock.
- [ ]  CÃ³ thá»ƒ báº­t connected mode theo tá»«ng feature trong quÃ¡ trÃ¬nh ghÃ©p backend, nhÆ°ng flag pháº£i explicit.

---

## Phase 4 â€” Firebase Authentication

- [ ]  Táº¡o Firebase project development vÃ  production riÃªng náº¿u ngÃ¢n sÃ¡ch cho phÃ©p.
- [X]  Báº­t Firebase Authentication, Google Sign-In vÃ  Email/Password cho project `vinaip002`; OAuth brand lÃ  `PromptOpt`.
- [X]  HoÃ n thiá»‡n UI chuyá»ƒn Ä‘á»•i Login/Register, validation confirm password vÃ  Firebase display name.
- [X]  HoÃ n thiá»‡n email login, account registration vÃ  password reset qua Firebase Auth.
- [X]  Connected auth dÃ¹ng Firebase Auth SDK; `sessionStorage` chá»‰ cÃ²n trong adapter demo tÃ¡ch biá»‡t.
- [X]  Táº¡o `AuthProvider` cung cáº¥p `user`, `loading`, `error`, `signIn`, `signOut`.
- [X]  API client tá»± láº¥y Firebase ID token vÃ  gáº¯n `Authorization: Bearer <token>`.
- [X]  Token refresh vÃ  phiÃªn háº¿t háº¡n do Firebase Auth SDK quáº£n lÃ½ qua `onAuthStateChanged`/`getIdToken`.
- [X]  KhÃ´ng lÆ°u access token thá»§ cÃ´ng trong localStorage/sessionStorage.
- [X]  Logout xÃ³a query cache vÃ  dá»¯ liá»‡u nháº¡y cáº£m phÃ­a client.
- [X]  Demo mode cÃ³ demo account vÃ  badge rÃµ rÃ ng; workflow production dÃ¹ng Firebase Auth.

---

## Phase 5 â€” API contract sáºµn sÃ ng Ä‘á»ƒ ghÃ©p backend

- [X]  Chá»‘t prefix frontend `/api/v1`, cÃ³ thá»ƒ override báº±ng environment variable.
- [X]  Chá»‘t error envelope thá»‘ng nháº¥t:

```json
{
  "error": {
    "code": "RUN_NOT_FOUND",
    "message": "Optimization run was not found",
    "request_id": "..."
  }
}
```

- [ ]  Chá»‘t endpoint MVP:

```text
POST /uploads
POST /projects
GET  /projects
POST /experiments
GET  /experiments/{id}
POST /experiments/{id}/runs
GET  /runs/{id}
POST /runs/{id}/cancel
GET  /runs/{id}/artifacts
POST /prompt-versions/{id}/approve
```

- [ ]  `POST /experiments/{id}/runs` tráº£ `202` vÃ  `run_id`, khÃ´ng chá» job hoÃ n táº¥t.
- [ ]  DÃ¹ng `Idempotency-Key` khi táº¡o run Ä‘á»ƒ trÃ¡nh submit trÃ¹ng.
- [ ]  Generate hoáº·c kiá»ƒm tra TypeScript types tá»« OpenAPI khi backend báº¯t Ä‘áº§u.
- [ ]  ThÃªm contract tests cho mock repository vÃ  HTTP repository.

---

## Phase 6 â€” Chuáº©n bá»‹ deploy frontend Firebase Hosting

### 6.1 Firebase config

- [X]  Firebase CLI Ä‘Ã£ Ä‘Æ°á»£c cÃ i, Ä‘Äƒng nháº­p vÃ  liÃªn káº¿t production project `vinaip002`.
- [X]  Táº¡o `.firebaserc` vá»›i alias `prod` vÃ  Hosting target `frontend`; giá»¯ `.firebaserc.example` lÃ m máº«u cho dev/prod tÃ¡ch biá»‡t sau nÃ y.
- [X]  Táº¡o `firebase.json` vá»›i public directory `app/frontend/dist`.
- [X]  ThÃªm SPA rewrite vá» `/index.html`.
- [X]  ThÃªm cache header dÃ i cho hashed JS/CSS/assets.
- [X]  Äáº·t `index.html` lÃ  `no-cache`.
- [X]  ChÆ°a thÃªm `/api/**` Cloud Run rewrite cho Ä‘áº¿n khi backend API Ä‘Æ°á»£c deploy.
- [X]  KhÃ´ng dÃ¹ng `pinTag: true` vÃ¬ frontend/backend cáº§n deploy Ä‘á»™c láº­p.
- [X]  Firebase web config dÃ¹ng `VITE_*`; khÃ´ng Ä‘Æ°a service-account credential vÃ o frontend.

### 6.2 Pre-deploy acceptance

- [X]  Clean `npm ci` vÃ  production build thÃ nh cÃ´ng.
- [X]  KhÃ´ng cÃ²n TypeScript/lint error.
- [X]  API base máº·c Ä‘á»‹nh lÃ  same-origin `/api/v1`, khÃ´ng hardcode localhost trong production config.
- [X]  `.env.local` vÃ  service-account JSON khÃ´ng Ä‘Æ°á»£c sá»­ dá»¥ng/commit; CI dÃ¹ng OIDC.
- [X]  Test `/` vÃ  direct URL `/dashboard` trÃªn Firebase Hosting: Ä‘á»u HTTP 200 vÃ  tráº£ SPA shell.
- [ ]  Test login/logout/refresh session.
- [X]  Test demo auth gate vÃ  badge `demo data`.
- [ ]  Test empty/error/loading states.
- [ ]  Lighthouse sanity check cho performance, accessibility vÃ  best practices.
- [X]  Production source map Ä‘ang táº¯t trong Vite config.

### 6.3 Deploy thá»§ cÃ´ng láº§n Ä‘áº§u

- [X]  Preview channel `frontend-foundation` Ä‘Ã£ dÃ¹ng Ä‘á»ƒ nghiá»‡m thu vÃ  Ä‘Ã£ xÃ³a; feature branch hiá»‡n test báº±ng `npm run dev`.
- [X]  Smoke test HTTPS, SPA rewrite vÃ  cache headers trÃªn Firebase Hosting.
- [X]  Deploy live production tá»± Ä‘á»™ng tá»« `main` thÃ nh cÃ´ng.
- [X]  Ghi láº¡i Firebase project ID, Web App ID, Hosting site ID vÃ  live URL trong `app/Readme.md`.
- [ ]  Kiá»ƒm tra rollback má»™t Firebase release.

---

## Phase 7 â€” CI/CD frontend

- [X]  Táº¡o workflow frontend CI vÃ  deploy riÃªng; Python CI cÃ³ backend path filter.
- [X]  DÃ¹ng path filter `app/frontend/**`, `firebase.json` vÃ  workflow files.
- [X]  Pull request/feature branch Ä‘Æ°á»£c cáº¥u hÃ¬nh chá»‰ cháº¡y:

```text
npm ci
format:check
lint
typecheck
test
build
```

- [X]  Push/merge vÃ o `main` cháº¡y láº¡i toÃ n bá»™ frontend checks trÆ°á»›c deploy.
- [X]  Workflow chá»‰ deploy Firebase Hosting sau khi verify frontend thÃ nh cÃ´ng.
- [X]  Workflow dÃ¹ng GitHub Environment `production`; Firebase Web App config Ä‘Æ°á»£c láº¥y lÃºc cháº¡y báº±ng WIF, khÃ´ng cáº§n copy API key vÃ o GitHub secrets/variables.
- [X]  Cáº¥u hÃ¬nh deploy concurrency Ä‘á»ƒ hai commit khÃ´ng deploy Ä‘Ã¨ nhau.
- [X]  Workflow dÃ¹ng WIF provider `github-actions/p002-main`, giá»›i háº¡n repo `binh39/P-002` vÃ  nhÃ¡nh `main`; service account chá»‰ cÃ³ `roles/firebasehosting.admin`.
- [ ]  Báº­t branch protection cho `main`: PR, required checks vÃ  cáº¥m force push.
- [ ]  Sau khi á»•n Ä‘á»‹nh, cÃ¢n nháº¯c PR preview channel trá» vÃ o dev resources, khÃ´ng dÃ¹ng production backend/data.

---

## Phase 8 â€” Khi nÃ o deploy backend?

### KhÃ´ng deploy backend hiá»‡n táº¡i

- [ ]  KhÃ´ng deploy boilerplate `/chat`/LangGraph/OpenAI hiá»‡n táº¡i chá»‰ Ä‘á»ƒ cÃ³ má»™t Cloud Run URL.
- [ ]  CÃ³ thá»ƒ chuáº©n bá»‹ Artifact Registry, service accounts vÃ  IAM trÆ°á»›c nhÆ°ng chÆ°a cáº§n giá»¯ má»™t service rá»—ng Ä‘ang cháº¡y.

### Deploy backend ngay khi cÃ³ vertical slice Ä‘áº§u tiÃªn

- [ ]  Deploy khi backend cÃ³ tá»‘i thiá»ƒu:
  - [X]  `GET /health`.
  - [X]  Production configuration vÃ  structured logging.
  - [X]  Firebase ID token verification.
  - [X]  CORS/same-origin policy Ä‘Ãºng.
  - [X]  Module `projects + signed upload` Ä‘Ã£ Ä‘Æ°á»£c code vá»›i adapter local vÃ  Google Cloud.
  - [X]  Unit/integration tests cho module Ä‘Ã³.
  - [X]  Docker context náº±m táº¡i `app/`, image chá»‰ copy `app/backend` vÃ  loáº¡i frontend khá»i image.
  - [X]  Docker image cháº¡y báº±ng non-root user vÃ  Ä‘Ã£ qua smoke test upload â†’ create/list project.
  - [X]  Service account quyá»n tá»‘i thiá»ƒu.
- [X]  Khi API Ä‘Ã£ deploy, thÃªm Firebase Hosting rewrite `/api/**` sang Cloud Run.
- [X]  Chuyá»ƒn Ä‘Ãºng frontend feature tá»« mock repository sang HTTP repository.
- [X]  Deploy backend Ä‘á»™c láº­p khi `app/backend/**` hoáº·c backend dependency thay Ä‘á»•i.
- [ ]  KhÃ´ng chá» hoÃ n thiá»‡n nhiá»u module backend má»›i deploy; deploy tá»«ng vertical slice nhá» sau khi Ä‘áº¡t cÃ¡c Ä‘iá»u kiá»‡n trÃªn.

### Backend vertical slice Ä‘á» xuáº¥t Ä‘áº§u tiÃªn

```text
Firebase login
  -> POST /api/v1/uploads
  -> browser upload ZIP báº±ng signed URL
  -> POST /api/v1/projects
  -> GET /api/v1/projects
  -> Dashboard hiá»ƒn thá»‹ project tháº­t
```

Slice tiáº¿p theo:

```text
Create experiment
  -> POST /experiments/{id}/runs
  -> Cloud Run Job cháº¡y baseline pytest/coverage
  -> GET /runs/{id}
  -> UI hiá»ƒn thá»‹ progress vÃ  artifact
```

---

## Phase 9 â€” Project Analysis vertical slice

- [X]  `POST /api/v1/projects/{project_id}/analyze` tráº£ `202` vÃ  enqueue Cloud Tasks.
- [X]  Worker ná»™i bá»™ xÃ¡c thá»±c Google OIDC token vÃ  khÃ´ng cháº¥p nháº­n Firebase user token.
- [X]  PhÃ¢n tÃ­ch ZIP báº±ng Python AST, cÃ³ giá»›i háº¡n sá»‘ file vÃ  kÃ­ch thÆ°á»›c giáº£i nÃ©n.
- [X]  LÆ°u function snapshot, source range vÃ  aggregate metrics vÃ o Firestore.
- [X]  HoÃ n thiá»‡n API list functions vÃ  xem source theo function ID.
- [X]  Project Detail cÃ³ re-analyze, polling khi Ä‘ang cháº¡y, loading/error/failed state.
- [X]  Project táº¡o má»›i tá»± Ä‘á»™ng báº¯t Ä‘áº§u analysis trong HTTP repository.
- [X]  Provision queue `promptopt-analysis`, retry tá»‘i Ä‘a 5 láº§n vÃ  concurrency 2.
- [X]  Smoke test production Firebase Auth â†’ upload â†’ Cloud Task â†’ AST â†’ function source.

Slice tiáº¿p theo sau Project Analysis:

```text
Create experiment
  -> chá»n project/functions Ä‘Ã£ phÃ¢n tÃ­ch
  -> POST /experiments
  -> POST /experiments/{id}/runs tráº£ 202
  -> worker cháº¡y baseline pytest/coverage trong sandbox
```

---

## Definition of Done cho má»‘c â€œFrontend deployedâ€

- [X]  Preview public URL truy cáº­p Ä‘Æ°á»£c vÃ  HTTPS hoáº¡t Ä‘á»™ng.
- [X]  Navigation dÃ¹ng URL, refresh/deep link hoáº¡t Ä‘á»™ng trÃªn Firebase Hosting.
- [X]  Firebase Auth token vÃ  API Ä‘Æ°á»£c kiá»ƒm thá»­ end-to-end trÃªn háº¡ táº§ng tháº­t.
- [ ]  KhÃ´ng cÃ²n auth giáº£ báº±ng `sessionStorage`.
- [ ]  Mock data chá»‰ tá»“n táº¡i sau repository contracts vÃ  cÃ³ badge demo.
- [ ]  KhÃ´ng component/page nÃ o import trá»±c tiáº¿p mock fixtures.
- [ ]  Loading/empty/error states Ä‘Ã£ cÃ³ cho cÃ¡c mÃ n hÃ¬nh chÃ­nh.
- [ ]  CI frontend pass trÃªn pull request.
- [ ]  Merge `main` tá»± deploy Firebase Hosting.
- [ ]  CÃ³ cÃ¡ch rollback vÃ  README ghi rÃµ quy trÃ¬nh deploy.

## Thá»© tá»± thá»±c hiá»‡n ngay

1. [ ]  Phase 1: dá»n Figma scaffold vÃ  thiáº¿t láº­p quality scripts.
2. [ ]  Phase 2: thÃªm router, providers vÃ  error handling.
3. [ ]  Phase 3: chuyá»ƒn mock data sau repository contracts.
4. [X]  Phase 4: tÃ­ch há»£p Firebase Auth, báº­t Google provider vÃ  Ä‘iá»n Firebase project config tháº­t.
5. [X]  Phase 6: cáº¥u hÃ¬nh Firebase Hosting, nghiá»‡m thu preview, xÃ³a preview vÃ  deploy live production.
6. [X]  Phase 7: frontend CI/CD tá»± Ä‘á»™ng deploy `main` Ä‘Ã£ hoáº¡t Ä‘á»™ng.
7. [X]  Phase 5 + 8: backend vertical slice Ä‘áº§u tiÃªn táº¡i `app/backend` Ä‘Ã£ provision GCP, deploy Cloud Run vÃ  ná»‘i Firebase Hosting.

---

## Phase 10 â€” Experiment, CoverUp baseline vÃ  GEPA optimization

### 10.1 PR 1 â€” Experiment API vÃ  run lifecycle

- [X]  Táº¡o branch `feature/experiment-baseline-slice` tá»« `main`.
- [X]  Táº¡o module `app/backend/modules/experiments`.
- [X]  ThÃªm tráº¡ng thÃ¡i `draft`, `baseline_queued`, `baseline_running`, `baseline_succeeded`, `failed`.
- [X]  ThÃªm API táº¡o/láº¥y experiment tá»« project Ä‘Ã£ analysis vÃ  cÃ¡c function há»£p lá»‡.
- [X]  ThÃªm API táº¡o baseline run tráº£ `202` vÃ  API polling run.
- [X]  Táº¡o in-memory repository cho local/test vÃ  Firestore repository cho production.
- [X]  Táº¡o Cloud Tasks dispatcher vÃ  internal worker endpoint cÃ³ Google OIDC authentication.
- [X]  KhÃ´ng cháº¡y source upload trá»±c tiáº¿p trong HTTP request.
- [X]  ThÃªm API tests cho ownership, analysis prerequisite, queue run vÃ  polling.

### 10.2 PR 2 â€” Isolated CoverUp baseline runner

- [X]  Táº¡o runner image riÃªng táº¡i `app/sandbox/Dockerfile`.
- [X]  Cháº¡y source trong container vá»›i network disabled, source read-only, drop capabilities vÃ  giá»›i háº¡n CPU/RAM/PID.
- [X]  ThÃªm timeout tá»•ng vÃ  kiá»ƒm tra ZIP path traversal.
- [X]  Chá»‰ báº­t local Docker runner khi `BASELINE_EXECUTION_BACKEND=docker`; máº·c Ä‘á»‹nh fail-closed.
- [X]  Há»— trá»£ Vertex ADC local vÃ  build Ä‘Æ°á»£c image `promptopt-coverup-runner:local`.
- [X]  ThÃªm giá»›i háº¡n tá»•ng dung lÆ°á»£ng giáº£i nÃ©n vÃ  sá»‘ file cho runner.
- [X]  Cháº·n symlink, device file vÃ  ZIP entry khÃ´ng pháº£i regular file.
- [ ]  KhÃ´ng truyá»n secret trá»±c tiáº¿p trÃªn Docker command line.
- [ ]  ThÃªm maximum provider retries vÃ  maximum total LLM calls cho CoverUp.
- [X]  Cháº¡y smoke test tháº­t vá»›i fixture project nhá» vÃ  Vertex Gemini (`score=1.0`, statement/branch `100%`).
- [ ]  Cháº¡y smoke test isort vá»›i function Ä‘Æ°á»£c chá»n qua API.

### 10.3 Prompt bundle vÃ  baseline artifacts

- [X]  Äá»‹nh nghÄ©a `PromptBundle` gá»“m `initial` vÃ  `error`.
- [X]  Validate placeholder báº¯t buá»™c vÃ  sinh prompt digest á»•n Ä‘á»‹nh.
- [X]  Mount prompt JSON riÃªng vÃ  gá»i CoverUp báº±ng `--prompt-template-file`.
- [X]  Giá»¯ baseline prompt immutable trong má»™t run.
- [X]  LÆ°u prompt digest vÃ o baseline run.
- [ ]  Táº¡o vÃ  lÆ°u prompt version ID riÃªng trong prompt registry.
- [X]  KhÃ´ng parse coverage tá»« stdout; dÃ¹ng structured coverage JSON lÃ m nguá»“n chÃ­nh.
- [X]  Xuáº¥t `target_coverage.json` theo tá»«ng target function, khÃ´ng chá»‰ coverage tá»•ng.
- [X]  Bá»• sung structured `attempt_trace.jsonl` tá»« CoverUp request/response log.
- [ ]  XÃ¡c minh trace chá»©a Ä‘á»§ prompt input, model response, generated test, pytest error vÃ  reason dá»«ng qua smoke test tháº­t.
- [X]  LÆ°u generated tests ZIP, CoverUp log, stdout vÃ  prompt JSON.
- [ ]  LÆ°u command metadata vÃ  runner config Ä‘Ã£ chuáº©n hÃ³a.
- [X]  Upload artifacts vÃ o object storage theo owner/project/experiment/run.
- [ ]  LÆ°u checksum, object name, size, content type vÃ  retention metadata vÃ o Firestore.
- [ ]  ThÃªm `GET /api/v1/runs/{run_id}/artifacts` vÃ  signed download URL cÃ³ ownership check.
- [X]  TÃ­nh deterministic statement/branch score theo tá»«ng symbol.
- [X]  Aggregate theo executable units; khÃ´ng trung bÃ¬nh Ä‘Æ¡n giáº£n pháº§n trÄƒm giá»¯a cÃ¡c function.
- [ ]  LÆ°u token usage, cost estimate, latency, model vÃ  provider.

### 10.4 Dataset vÃ  split chá»‘ng data leakage

- [X]  Táº¡o dataset snapshot tá»« function ngÆ°á»i dÃ¹ng chá»n, khÃ´ng hard-code isort.
- [ ]  LÆ°u project version, source checksum vÃ  settings checksum cÃ¹ng dataset.
- [X]  Chia `train`, `validation`, `test` báº±ng seed cá»‘ Ä‘á»‹nh vÃ  lÆ°u split trong experiment.
- [X]  Dataset dÆ°á»›i 3 targets Ä‘Æ°á»£c Ä‘Ã¡nh dáº¥u baseline-only, khÃ´ng giáº£ láº­p validation/test.
- [X]  Chá»‰ Ä‘Ã¡nh dáº¥u `optimization_eligible` khi train/validation/test Ä‘á»u khÃ´ng rá»—ng (tá»‘i thiá»ƒu 3 targets).
- [X]  KhÃ´ng dÃ¹ng locked `test` split trong GEPA search/candidate selection.
- [ ]  KhÃ´ng Ä‘á»ƒ cÃ¹ng function/source version xuáº¥t hiá»‡n á»Ÿ nhiá»u split.
- [ ]  ÄÃ³ng bÄƒng denominator statement/branch tá»« baseline preflight.

### 10.5 PR 3 â€” DSPy/GEPA prompt optimization

- [X]  TÃ­ch há»£p pipeline GEPA cá»§a `duyvu1105` qua Cloud Run Job riÃªng `promptopt-gepa-runner`, dÃ¹ng namespace `runner-jobs/gepa/<run-id>` vÃ  khÃ´ng truy cáº­p `prompt_optimization_v3`.
- [ ]  Deploy image/job GEPA theo workflow má»›i vÃ  cháº¡y authenticated smoke test vá»›i budget web giá»›i háº¡n 30 metric calls.
- [X]  Pin `dspy==3.2.1` vÃ  `gepa==0.0.27`.
- [X]  TÃ¡ch model sinh test (`COVERUP_MODEL`) vÃ  reflection (`OPTIMIZE_MODEL`).
- [X]  Validate Gemini/Vertex provider configuration vÃ  model allowlist.
- [X]  Táº¡o GEPA adapter nháº­n `PromptBundle`, coverage vÃ  attempt trace tháº­t.
- [X]  Reward pháº£i do coverage code tÃ­nh; khÃ´ng dÃ¹ng LLM judge.
- [X]  Reflection chá»‰ sá»­a `initial` vÃ  `error`.
- [X]  Loáº¡i candidate thiáº¿u placeholder, format lá»—i hoáº·c vÆ°á»£t size trÆ°á»›c khi gá»i CoverUp.
- [X]  Cache theo prompt digest, source checksum, targets, split, model vÃ  runner config.
- [ ]  TÃ¡ch workspace theo candidate/target/replicate Ä‘á»ƒ khÃ´ng rÃ² generated tests.
- [ ]  ThÃªm `max_metric_calls`, reflection minibatch, replicate, rate limit vÃ  concurrency limit.
- [ ]  Persist GEPA checkpoint Ä‘á»ƒ resume sau timeout/restart.
- [X]  ThÃªm `POST /api/v1/experiments/{id}/optimize`, tráº£ `202`.
- [ ]  Bá»• sung tráº¡ng thÃ¡i `optimizing`, `candidate_evaluating`, `optimization_succeeded`, `timed_out`, `cancelled`.
- [ ]  LÆ°u candidate prompt, parent prompt, generation, score, cost, latency vÃ  failure reason.
- [X]  KhÃ´ng tá»± ghi Ä‘Ã¨ baseline hoáº·c production prompt sau GEPA search.

### 10.6 PR 4 â€” Paired comparison vÃ  promotion gate

- [X]  Chá»n candidate báº±ng validation rá»“i khÃ³a candidate trÆ°á»›c final evaluation.
- [X]  Cháº¡y baseline vÃ  candidate trÃªn cÃ¹ng locked test targets, runner config vÃ  replicate count.
- [ ]  So sÃ¡nh paired statement/branch coverage, pass rate, cost vÃ  latency.
- [X]  Chá»‰ promote khi candidate tá»‘t hÆ¡n baseline vÃ  qua hard gate.
- [X]  Hard gate: pytest há»£p lá»‡, khÃ´ng flaky, khÃ´ng timeout vÃ  khÃ´ng giáº£m pass rate.
- [X]  Náº¿u GEPA giá»¯ nguyÃªn baseline digest thÃ¬ skip final evaluation vÃ  ghi rÃµ reason.
- [X]  LÆ°u `final_validation.json`, absolute/relative gain vÃ  promotion decision.
- [X]  Táº¡o prompt version `in_review`; khÃ´ng tá»± Ä‘á»™ng chuyá»ƒn production.
- [X]  ThÃªm approve/reject API cÃ³ reviewer, comment, audit timestamp vÃ  idempotency.

### 10.7 Production runner trÃªn Google Cloud

- [X]  KhÃ´ng dÃ¹ng Docker socket/Docker-in-Docker trong Cloud Run API service.
- [X]  Push runner image riÃªng lÃªn Artifact Registry.
- [X]  DÃ¹ng Cloud Run Job cho execution; Cloud Tasks chá»‰ dispatch/orchestrate.
- [X]  Táº¡o runner service account riÃªng vá»›i quyá»n tá»‘i thiá»ƒu trÃªn source/artifact objects.
- [X]  DÃ¹ng workload identity/Secret Manager; khÃ´ng mount ADC file trong production.
- [ ]  Cáº¥u hÃ¬nh job timeout, retries, parallelism, maximum instances vÃ  cancellation.
- [ ]  ThÃªm quota theo user/workspace: concurrent runs, functions, LLM calls vÃ  cost ceiling.
- [ ]  ThÃªm retention policy vÃ  xÃ³a artifacts theo project.
- [X]  Provision queue `promptopt-baseline`, hoÃ n thiá»‡n OIDC/IAM vÃ  production smoke test baseline.

### 10.8 Frontend integration

- [X]  Táº¡o `ExperimentRepository` HTTP vÃ  domain types Ä‘Ãºng backend contract.
- [X]  Chuyá»ƒn Create Experiment tá»« mock sang project/functions tháº­t.
- [X]  Gá»i create experiment/run vÃ  polling báº±ng TanStack Query.
- [X]  Hiá»ƒn thá»‹ state machine tháº­t tá»« queued Ä‘áº¿n succeeded/failed.
- [X]  Hiá»ƒn thá»‹ baseline metrics theo function vÃ  aggregate.
- [ ]  Hiá»ƒn thá»‹ prompt diff, generated tests, coverage artifacts, logs vÃ  failure reason.
- [ ]  HoÃ n thiá»‡n comparison vÃ  review/approve/reject báº±ng API tháº­t.
- [X]  XÃ³a mock experiment/run/comparison sau khi tá»«ng mÃ n hÃ¬nh Ä‘Ã£ ná»‘i backend.

### 10.9 Verification vÃ  Definition of Done

- [X]  Ruff format/check pass cho experiment foundation.
- [X]  Backend tests pass (`36 passed` sau comparison artifact API).
- [X]  Unit test score, cache key, prompt validation vÃ  promotion rule.
- [ ]  Contract/integration test cho experiment, run vÃ  artifact APIs báº±ng fake executor.
- [ ]  Docker smoke test fixture project vÃ  test timeout/retry/malformed response.
- [ ]  Test Firestore ownership isolation vÃ  GCS artifact authorization.
- [ ]  Test GEPA resume checkpoint vÃ  idempotent Cloud Task retry.
- [X]  CI build cáº£ API image vÃ  runner image khi source liÃªn quan thay Ä‘á»•i.
- [ ]  Production smoke test baseline â†’ optimize â†’ locked comparison â†’ review.
- [ ]  Chá»‰ merge GEPA khi report chá»©ng minh baseline vÃ  optimized dÃ¹ng cÃ¹ng evaluation protocol.

---

## Phase 11 â€” Roadmap tá»« hiá»‡n táº¡i Ä‘áº¿n production-complete

> ÄÃ¢y lÃ  danh sÃ¡ch Æ°u tiÃªn cáº­p nháº­t ngÃ y 2026-08-07 vÃ  lÃ  nguá»“n theo dÃµi chÃ­nh cho pháº§n viá»‡c cÃ²n láº¡i. CÃ¡c má»¥c chÆ°a hoÃ n thÃ nh á»Ÿ Phase 1â€“10 váº«n giá»¯ giÃ¡ trá»‹ ká»¹ thuáº­t, nhÆ°ng nÃªn Ä‘Æ°á»£c thá»±c hiá»‡n theo thá»© tá»± P0 â†’ P5 dÆ°á»›i Ä‘Ã¢y.

### P0 â€” KhÃ´i phá»¥c release pipeline vÃ  xÃ¡c nháº­n production hiá»‡n táº¡i

- [X]  Merge branch `fix/backend-artifact-registry-auth` vÃ o `main`.
- [X]  XÃ¡c nháº­n backend workflow dÃ¹ng WIF access token vÃ  `docker/login-action`, khÃ´ng dÃ¹ng user credential hoáº·c service-account key.
- [X]  XÃ¡c nháº­n API image vÃ  runner image push thÃ nh cÃ´ng lÃªn Artifact Registry.
- [X]  XÃ¡c nháº­n Cloud Run API vÃ  Cloud Run Job cÃ¹ng dÃ¹ng image SHA cá»§a release má»›i nháº¥t.
- [X]  Cháº¡y láº¡i `Deploy frontend production` trÃªn `main` sau sá»± cá»‘ GitHub Actions.
- [ ]  XÃ¡c nháº­n `Frontend CI`, backend `CI`, frontend deploy vÃ  backend deploy Ä‘á»u xanh trÃªn cÃ¹ng release (workflow cÃ³ path filter; cáº§n má»™t run kiá»ƒm chá»©ng riÃªng sau outage).
- [X]  Kiá»ƒm tra `/health`, Firebase Hosting rewrite `/api/v1`, Firebase login guard vÃ  CORS trÃªn production.
- [X]  Cháº¡y smoke test authenticated: upload ZIP â†’ create project â†’ analysis â†’ chá»n functions â†’ create experiment.
- [ ]  Cháº¡y smoke test Ä‘áº§y Ä‘á»§: baseline â†’ optimize â†’ paired comparison â†’ táº¡o prompt version â†’ approve/reject.
- [ ]  LÆ°u report smoke test Ä‘Ã£ loáº¡i token/sensitive data lÃ m release evidence (khÃ´ng commit Firebase UID, private artifact path hoáº·c ZIP fixture lá»›n).
- [X]  Ghi láº¡i image SHA, Cloud Run revision vÃ  Firebase Hosting release Ä‘á»ƒ cÃ³ Ä‘iá»ƒm rollback.

#### P0 release evidence â€” 2026-08-07

- [X]  `main`: `085df3a`; backend deploy release: `fd8f3ce`.
- [X]  Backend deploy [#13](https://github.com/binh39/P-002/actions/runs/31138705068) thÃ nh cÃ´ng sau khi dÃ¹ng WIF access token + `docker/login-action`.
- [X]  Cloud Run API revision: `promptopt-api-00014-j46`, 100% traffic, image `api:fd8f3ce85f222655f6fe8217abfb5701f3ba361f`.
- [X]  Cloud Run Job image: `coverup-runner:fd8f3ce85f222655f6fe8217abfb5701f3ba361f`; latest execution `promptopt-coverup-runner-qsqr7` succeeded.
- [X]  Firebase Hosting redeployed manually from `main` in `firebase + connected` mode. Production bundle contains `Comparison-CtGvmjBI.js` with paired-comparison API UI and no previous comparison fixture.
- [X]  `GET https://vinaip002.web.app/api/v1/health` returns 200; unauthenticated `GET /experiments` returns 401; CORS preflight allows `https://c3-app-002.io.vn` and rejects an untrusted origin.
- [X]  Existing authenticated baseline smoke evidence confirms upload â†’ analysis â†’ experiment â†’ Cloud Tasks â†’ Cloud Run Job â†’ artifact result.
- [X]  `smoke_production.ps1 -FullPipeline` supports deterministic multi-target selection, optimization, comparison and optional approve/reject; its result is sanitized and written to ignored `app/.smoke-results/`.
- [ ]  Before marking P0 complete: run full authenticated smoke with a freshly generated Firebase ID token, then store a sanitized summary outside Git-tracked fixture/output paths.

### P1 â€” HoÃ n táº¥t frontend báº±ng API tháº­t vÃ  loáº¡i bá» mock production

- [X]  ThÃªm catalog chá»‰ Ä‘á»c cho `isort`, `mimesis`, `mlxtend`, `typesystem`; khÃ´ng ghi Upload/Project/Function sample vÃ o Firestore.
- [X]  Ná»‘i Projects vÃ  Create Experiment vÃ o `GET /projects/samples` vÃ  pipeline Cloud Run tháº­t.
- [ ]  Deploy sample-project slice rá»“i cháº¡y smoke tá»«ng repo; Æ°u tiÃªn isort trÆ°á»›c, sau Ä‘Ã³ mimesis, typesystem vÃ  mlxtend.

#### Review & Approval

- [X]  Táº¡o frontend `PromptVersionRepository` vÃ  domain types Ä‘Ãºng backend contract.
- [X]  Ná»‘i prompt version tá»« `comparison.promptVersionId` vÃ o trang Review.
- [X]  Ná»‘i approve/reject API, comment, loading/error state vÃ  chá»‘ng double-submit.
- [X]  Sau review, invalidate/refetch experiment, comparison vÃ  prompt version queries.
- [X]  Hiá»ƒn thá»‹ reviewer, review timestamp, comment vÃ  tráº¡ng thÃ¡i quyáº¿t Ä‘á»‹nh cuá»‘i.
- [X]  Thay toÃ n bá»™ prompt/review queue hard-code trong `ReviewApproval.tsx`.
- [X]  ThÃªm frontend repository tests cho approve/reject API contract; backend test ownership, filter vÃ  idempotent retry.

#### Prompt Registry

- [ ]  ThÃªm backend API list prompt versions theo owner, status, experiment vÃ  pagination.
- [ ]  Chá»‘t semantics cho `active`, `approved`, `rejected`, `archived`; khÃ´ng dÃ¹ng status chá»‰ tá»“n táº¡i trong UI.
- [ ]  Ná»‘i Prompt Registry vÃ o repository HTTP tháº­t.
- [ ]  Hiá»ƒn thá»‹ prompt lineage, source experiment, comparison metrics vÃ  audit decision.
- [ ]  XÃ³a danh sÃ¡ch prompt hard-code trong `Registry.tsx` sau khi API list hoáº¡t Ä‘á»™ng.

#### Prompt Registry và Final Test Cases

> Phạm vi đã chốt: trang Test Cases chỉ quản lý các bộ test mà người dùng chủ động sinh sau khi
> experiment đã có prompt cuối cùng. Test tạm sinh trong quá trình baseline/GEPA/evaluation chỉ là
> artifact kỹ thuật của experiment và tuyệt đối không xuất hiện trong Test Cases.

##### A. Chốt domain và dữ liệu Prompt Registry

- [ ]  Mỗi experiment chỉ hiển thị một row trong Prompt Registry; không tách baseline và optimized thành hai row.
- [ ]  Row experiment hiển thị tên experiment, baseline score (khi di chuột vào hiện statement coverage, branch coverage của baseline), optimized score (khi di chuột vào hiện statement coverage, branch coverage), mức cải thiện, generation model, optimization model, cost và thời điểm tạo. Lưu ý hiển thị gọn trong bảng đó luôn để người dùng không phải cuộn sang trái, phải. (Nếu nội dung dài quá thì bảo tôi để xem xét bỏ thời điểm tạo)
- [ ]  Không hiển thị version/latency ở danh sách chính; chỉ hiển thị trạng thái khi experiment chưa hoàn tất
  hoặc thất bại.
- [ ]  Lưu hai prompt snapshot immutable cho mỗi experiment với role `baseline` và `optimized`.
- [ ]  Mỗi prompt snapshot lưu `initial`, `error`, prompt digest, experiment ID, source snapshot digest,
  dataset/split/seed, runner protocol, COVERUP_MODEL, OPTIMIZE_MODEL, metrics và cost tương ứng.
- [ ]  Không sửa prompt snapshot đã có kết quả; mọi chỉnh sửa thủ công phải tạo draft/prompt mới với digest mới.
- [ ]  Phân biệt rõ COVERUP_MODEL dùng prompt để sinh test và OPTIMIZE_MODEL dùng để đề xuất prompt mới.
- [ ]  Thiết kế API owner-scoped để list experiment registry có pagination/filter/search và lấy detail của
  một experiment cùng hai prompt snapshot.
- [ ]  Thiết kế artifact references; metadata nhỏ lưu Firestore, prompt/report/code/artifact lớn lưu private GCS.
- [ ]  Migrate hoặc map prompt-version documents hiện có sang contract mới mà không làm sai audit/review history.
- [ ]  Chỉ khi nào Experiment chạy xong thì mới lưu vào Prompt Registry, chưa chạy xong experiment thì chưa lưu.

##### B. Hoàn thiện Prompt Registry frontend

- [X]  Xóa toàn bộ prompt registry mock/fixture khỏi production path sau khi API list/detail hoạt động.
- [X]  Hiển thị một row mỗi experiment với baseline, optimized và delta để so sánh trực tiếp.
- [X]  Click row mở trang chi tiết experiment/prompt riêng, không nhồi toàn bộ nội dung vào table.
- [X]  Trang chi tiết hiển thị hai cột Baseline Prompt và Optimized Prompt cùng metrics/cost/model tương ứng.
- [X]  Thêm chế độ side-by-side, unified diff, chỉ xem `initial` và chỉ xem `error`.
- [X]  Thêm nút `Generate Test Cases` riêng cho baseline và optimized prompt.
- [ ]  Thêm nút `Compare baseline vs optimized` để tạo paired generation với cùng project snapshot,
  targets, model, seed và runner config.
- [ ]  Có loading, empty, error, retry, forbidden, expired-session và trạng thái experiment chưa có optimized prompt.

##### C. Backend Final Test Generation

- [X]  Tạo entity `TestGenerationRun` độc lập với baseline/optimization/evaluation run.
- [X]  Mỗi run lưu owner, experiment ID, prompt ID/digest, `prompt_role` (`baseline` hoặc `optimized`),
  project/source snapshot, target scope, model/provider, seed, runner config và thời điểm tạo.
- [X]  Chỉ cho phép tạo run từ prompt snapshot thuộc experiment của chính user và project snapshot còn hợp lệ.
- [X]  Tạo API generate test trả `202`; dispatch qua Cloud Tasks và chạy source/test trong Cloud Run Job cô lập.
- [X]  Hỗ trợ target scope: toàn project, module/file hoặc danh sách function được chọn.
- [ ]  Hỗ trợ tùy chọn model sinh test, repeat count, max attempts, concurrency/rate limit và cost ceiling.
- [ ]  Tạo state machine `queued -> preparing -> generating -> running_tests -> completed | partial | failed | cancelled | timed_out`.
- [X]  Thêm idempotency key và chống double-click tạo hai active run giống nhau.
- [X]  Sau khi sinh, luôn chạy pytest + statement/branch coverage nếu runtime hợp lệ.
- [X]  Báo riêng coverage toàn project và coverage của target/function được chọn; không trộn hai loại metric.
- [ ]  Lưu test count, passed/failed/skipped, statement/branch units, cost, token usage, model config và failure reason.
- [X]  Test generation run là immutable; regenerate luôn tạo run ID mới để kết quả còn tái lập được.
- [X]  Không đưa bất kỳ generated test workspace nội bộ nào của GEPA vào Final Test Cases API/list.

##### D. Paired generation baseline vs optimized

- [ ]  Tạo `comparison_id` liên kết hai TestGenerationRun baseline/optimized.
- [ ]  Khóa cùng project/source snapshot, targets, generation model, model parameters, seed, repeat count và runtime
  protocol cho cả hai bên.
- [ ]  Tính statement delta, branch delta, pass-rate delta, cost delta và số target improved/unchanged/regressed/failed.
- [ ]  Không kết luận optimized tốt hơn nếu hai run khác evaluation protocol hoặc thiếu coverage denominator hợp lệ.
- [ ]  Cho phép rerun paired comparison thành comparison mới; không ghi đè kết quả cũ.

##### E. Artifact và lưu trữ

- [ ]  Firestore chỉ lưu metadata, state, metrics và private artifact references của TestGenerationRun.
- [ ]  Private GCS lưu generated `.py`, source excerpts/snapshot references, pytest output, coverage JSON/HTML,
  target coverage, generation log, manifest và downloadable ZIP.
- [ ]  Artifact manifest có schema version, checksum, size, content type, prompt/source digest và retention deadline.
- [ ]  Tạo API owner-scoped để list artifact, xem text/code an toàn và cấp signed download ngắn hạn.
- [ ]  Không lưu API key, credential, Firebase token hoặc signed URL lâu dài trong run/manifest/log.
- [ ]  Thiết kế retention và cascade delete cho test run mà không xóa nhầm experiment, prompt hoặc project source.

##### F. Trang Test Cases mới

- [X]  Thêm route `/test-cases` chỉ liệt kê Final TestGenerationRun do người dùng chủ động tạo.
- [X]  Danh sách hiển thị run, project, experiment, prompt role, model, target count, tests, passed/failed,
  statement/branch coverage, status và created time.
- [ ]  Thêm filter theo project, experiment, prompt role, model, status và khoảng thời gian.
- [X]  Click run mở detail có prompt snapshot, project/source digest, config, metrics, cost và artifact downloads.
- [ ]  Tạo cây chọn project -> file -> function để xem source và generated tests tương ứng.
- [ ]  Thêm toggle `Source function`, `Baseline tests`, `Optimized tests`, `Coverage` và `Pytest output`;
  panel không được chọn phải ẩn hoàn toàn.
- [ ]  Desktop hỗ trợ ba panel Source | Baseline tests | Optimized tests; màn hình nhỏ chuyển thành tabs.
- [ ]  Thêm syntax highlighting, copy code, unified test diff, download file và download toàn bộ suite ZIP.
- [ ]  Nếu có coverage line data, đánh dấu dòng source covered/missed và branch còn thiếu.
- [ ]  Với paired run, hiển thị target improved/unchanged/regressed/failed và cho chuyển nhanh giữa các target.
- [ ]  Test Cases không có mock data trong connected/production mode.

##### G. Verification và Definition of Done

- [ ]  Unit test domain/state machine, prompt immutability, metric aggregation và paired protocol validation.
- [ ]  Backend contract/integration test generate -> Cloud Task -> isolated Job -> pytest/coverage -> artifacts.
- [ ]  Test idempotency, retry, cancellation, timeout, provider failure, partial tests và missing artifact.
- [ ]  Test user A không thể list/xem/download/delete TestGenerationRun hoặc artifact của user B.
- [ ]  Browser E2E: experiment thành công -> chọn optimized -> generate -> poll -> xem code/coverage -> download ZIP.
- [ ]  Browser E2E paired comparison: cùng config -> xem baseline/optimized tests và coverage delta.
- [ ]  Xác nhận Test Cases API không trả về run/artifact nội bộ của quá trình optimize prompt.
- [ ]  Production smoke trên ít nhất một project upload thật với optimized prompt và một paired comparison nhỏ.
- [ ]  Cập nhật README/API contract/runbook sau khi vertical slice Final Test Cases chạy production thành công.

#### Dashboard, Datasets, Settings vÃ  Playground

- [ ]  ThÃªm dashboard aggregate endpoint hoáº·c tá»•ng há»£p cÃ³ kiá»ƒm soÃ¡t tá»« API hiá»‡n cÃ³.
- [ ]  Ná»‘i Dashboard KPI, recent experiments vÃ  coverage trend vÃ o dá»¯ liá»‡u tháº­t.
- [ ]  XÃ³a `MockDashboardRepository` khá»i production path; chá»‰ giá»¯ demo repository trong local demo mode.
- [ ]  Quyáº¿t Ä‘á»‹nh Datasets lÃ  resource Ä‘á»™c láº­p hay chá»‰ lÃ  snapshot náº±m trong Experiment.
- [ ]  Náº¿u giá»¯ trang Datasets: thÃªm list/detail API, checksum, split seed vÃ  source version.
- [ ]  Náº¿u khÃ´ng giá»¯: bá» route Datasets vÃ  hiá»ƒn thá»‹ snapshot trong Experiment Detail.
- [ ]  XÃ³a import trá»±c tiáº¿p `mocks/fixtures/platform` khá»i `Datasets.tsx`.
- [ ]  Ná»‘i nÃºt Save project settings vá»›i `PATCH /projects/{id}/settings`, cÃ³ dirty/loading/success/error state.
- [ ]  Quyáº¿t Ä‘á»‹nh Playground lÃ  tÃ­nh nÄƒng production hay trang demo; náº¿u production pháº£i dÃ¹ng cÃ¹ng sandbox/quota vá»›i runner.
- [ ]  KhÃ´ng cho Playground cháº¡y source ngÆ°á»i dÃ¹ng trá»±c tiáº¿p trong API container.

#### Production frontend mode

- [ ]  Build production vá»›i `VITE_AUTH_MODE=firebase` vÃ  `VITE_DATA_MODE=connected`.
- [ ]  API lá»—i pháº£i hiá»ƒn thá»‹ lá»—i tháº­t, tuyá»‡t Ä‘á»‘i khÃ´ng fallback Ã¢m tháº§m sang fixture.
- [ ]  Chá»‰ giá»¯ `DemoAuthService` vÃ  fixture repositories cho local development/test cÃ³ badge rÃµ rÃ ng.
- [ ]  XÃ³a constants/sample records hard-code khá»i Review, Registry vÃ  cÃ¡c mÃ n hÃ¬nh production Ä‘Ã£ ná»‘i API.
- [ ]  Kiá»ƒm tra loading, empty, error, retry, forbidden vÃ  expired-session state cho má»i trang tháº­t.

### P2 â€” Äá»™ Ä‘Ãºng vÃ  kháº£ nÄƒng phá»¥c há»“i cá»§a experiment pipeline

- [ ]  Táº¡o idempotency key/transaction cho create run, optimize, compare vÃ  Cloud Task retry.
- [ ]  KhÃ´ng táº¡o hai active run cÃ¹ng loáº¡i cho má»™t experiment khi user double-click hoáº·c task retry.
- [ ]  ThÃªm tráº¡ng thÃ¡i vÃ  API cancellation cho baseline, optimization, comparison vÃ  Cloud Run Job.
- [ ]  PhÃ¢n biá»‡t rÃµ `failed`, `timed_out`, `cancelled`, queue failure vÃ  infrastructure failure.
- [ ]  Persist GEPA checkpoint vÃ  resume sau worker timeout/restart.
- [ ]  TÃ¡ch workspace/artifact prefix theo candidate, target vÃ  replicate Ä‘á»ƒ khÃ´ng rÃ² generated tests.
- [ ]  ÄÃ³ng bÄƒng project/source/settings checksum khi táº¡o experiment.
- [ ]  ÄÃ³ng bÄƒng statement/branch denominator vÃ  runner/model config cho protocol so sÃ¡nh.
- [ ]  NgÄƒn cÃ¹ng function/source version xuáº¥t hiá»‡n á»Ÿ nhiá»u split.
- [ ]  LÆ°u model/provider, token usage, latency, estimated cost vÃ  normalized runner command metadata.
- [ ]  LÆ°u artifact manifest gá»“m checksum, size, content type, schema version vÃ  retention deadline.
- [ ]  Version schema cho execution manifest, result JSON, coverage JSON vÃ  final validation report.
- [ ]  ThÃªm migration/backward-compatibility strategy cho Firestore documents vÃ  artifacts cÅ©.
- [ ]  XÃ¡c minh paired comparison dÃ¹ng Ä‘Ãºng cÃ¹ng targets, replicates, model vÃ  runner config.
- [ ]  Chá»‘t promotion policy báº±ng config/version thay vÃ¬ Ä‘iá»u kiá»‡n khÃ´ng version hÃ³a trong code.

### P3 â€” Security, tenant isolation, quota vÃ  data lifecycle

- [ ]  HoÃ n thÃ nh threat model cho upload, ZIP extraction, generated tests, Cloud Tasks, runner vÃ  artifact download.
- [ ]  Test path traversal, symlink, device file, ZIP bomb, oversized archive vÃ  malformed manifest.
- [ ]  XÃ¡c minh má»i public API Ä‘á»u kiá»ƒm tra Firebase user ownership á»Ÿ service/repository boundary.
- [ ]  Test user A khÃ´ng Ä‘á»c/sá»­a/cháº¡y project, experiment, run, prompt version hoáº·c artifact cá»§a user B.
- [ ]  XÃ¡c minh internal endpoints chá»‰ nháº­n OIDC token Ä‘Ãºng audience vÃ  service account.
- [ ]  Giá»›i háº¡n sá»‘ project, upload size, functions/experiment, active runs vÃ  concurrent jobs theo user/workspace.
- [ ]  Giá»›i háº¡n CoverUp/GEPA total LLM calls, provider retries, metric calls, runtime vÃ  cost ceiling.
- [ ]  ThÃªm rate limiting cho upload, analysis, baseline, optimize, compare vÃ  review endpoints.
- [ ]  Äáº·t budget alert vÃ  kill switch Ä‘á»ƒ táº¯t optimize/runner khi vÆ°á»£t chi phÃ­ hoáº·c cÃ³ abuse.
- [ ]  Thiáº¿t káº¿ delete project/experiment cÃ³ cascade an toÃ n cho Firestore, GCS vÃ  queued tasks.
- [ ]  Cáº¥u hÃ¬nh retention policy cho source ZIP, runner exchange objects, logs vÃ  artifacts.
- [ ]  Táº¡o scheduled cleanup cÃ³ dry-run, audit log vÃ  kháº£ nÄƒng retry.
- [ ]  RÃ  IAM least privilege cho frontend deploy, backend deploy, API runtime vÃ  runner identities.
- [ ]  XÃ¡c nháº­n khÃ´ng cÃ³ service-account key, Firebase token hoáº·c generated credential Ä‘Æ°á»£c commit/log.
- [ ]  Chá»‘t egress policy cho runner Ä‘á»ƒ source/test ngÆ°á»i dÃ¹ng khÃ´ng truy cáº­p tÃ¹y Ã½ ra ngoÃ i.

### P4 â€” Observability, váº­n hÃ nh vÃ  kiá»ƒm soÃ¡t chi phÃ­

- [ ]  Chuáº©n hÃ³a correlation IDs: request, user, project, experiment, run, task vÃ  job execution.
- [ ]  Structured log má»i state transition, dispatch, retry, runner result vÃ  review decision.
- [ ]  KhÃ´ng log Firebase token, source code, prompt nháº¡y cáº£m hoáº·c signed URL Ä‘áº§y Ä‘á»§.
- [ ]  Táº¡o Cloud Monitoring dashboard cho API latency/error rate, Cloud Tasks depth/age vÃ  Cloud Run Job failures.
- [ ]  Táº¡o alert cho API 5xx, task retry/dead-letter, job timeout/failure, auth failure vÃ  quota exhaustion.
- [ ]  Theo dÃµi LLM call count, token usage, latency vÃ  estimated cost theo user/experiment/model.
- [ ]  Äá»‹nh nghÄ©a SLO ban Ä‘áº§u cho API availability, queue delay, baseline completion vÃ  optimization completion.
- [ ]  Viáº¿t runbook cho failed deploy, stuck task, failed job, missing artifact, Firestore/GCS incident vÃ  provider outage.
- [ ]  ThÃªm admin-safe diagnostic command/script theo run ID, khÃ´ng yÃªu cáº§u Ä‘á»c dá»¯ liá»‡u tenant khÃ¡c.
- [ ]  Thiáº¿t láº­p Firestore backup/export vÃ  kiá»ƒm thá»­ restore.
- [ ]  Kiá»ƒm tra Artifact Registry cleanup policy vÃ  giá»¯ Ä‘á»§ image SHA Ä‘á»ƒ rollback.

### P5 â€” Test strategy, staging, release vÃ  rollback

- [ ]  Táº¡o GCP/Firebase staging tÃ¡ch production cho integration/E2E vÃ  preview frontend.
- [ ]  CI cháº¡y Ruff, backend tests, frontend format/lint/typecheck/test/build vÃ  build cáº£ hai container images.
- [ ]  ThÃªm contract tests cho upload, project, function, experiment, run, artifact vÃ  prompt-version APIs.
- [ ]  ThÃªm integration tests báº±ng fake executor cho baseline â†’ optimize â†’ compare â†’ review.
- [ ]  ThÃªm Firestore emulator/repository tests cho transaction, ownership vÃ  concurrent update.
- [ ]  ThÃªm GCS fake/emulator tests cho signed upload, artifact manifest, authorization vÃ  missing object.
- [ ]  ThÃªm Cloud Task retry/idempotency vÃ  Cloud Run operation polling failure tests.
- [ ]  ThÃªm runner tests cho timeout, malformed CoverUp output, provider retry vÃ  partial artifact upload.
- [ ]  ThÃªm browser E2E cho auth, upload, analysis, create experiment, polling, comparison vÃ  review.
- [ ]  Cháº¡y load test cÃ³ giá»›i háº¡n cho concurrent polling, list APIs vÃ  task enqueue; khÃ´ng load test LLM production tÃ¹y Ã½.
- [ ]  Kiá»ƒm tra accessibility, responsive layout, deep link, refresh vÃ  expired Firebase session.
- [ ]  Scan dependencies/container images vÃ  xá»­ lÃ½ vulnerability má»©c critical/high trÆ°á»›c release.
- [ ]  Pin/review version cá»§a actions, Python/Node dependencies, CoverUp, DSPy/GEPA vÃ  model names.
- [ ]  Viáº¿t rollback frontend Hosting release, Cloud Run revision vÃ  runner Job image báº±ng SHA.
- [ ]  Táº¡o release checklist cÃ³ approver, migration step, smoke test, monitoring window vÃ  rollback owner.

### Definition of Done â€” Production-complete v1

- [ ]  KhÃ´ng cÃ²n mock/fixture trÃªn báº¥t ká»³ production route nÃ o; demo mode chá»‰ báº­t rÃµ rÃ ng á»Ÿ local/test.
- [ ]  User cÃ³ thá»ƒ hoÃ n thÃ nh upload â†’ analysis â†’ baseline â†’ optimize â†’ compare â†’ review trÃªn production UI.
- [ ]  Má»i dá»¯ liá»‡u vÃ  artifact Ä‘á»u cÃ³ ownership check, schema version, checksum vÃ  lifecycle policy.
- [ ]  Pipeline chá»‹u Ä‘Æ°á»£c double-submit, task retry, timeout vÃ  worker restart mÃ  khÃ´ng táº¡o state sai/duplicate run.
- [ ]  Quota, rate limit, concurrency limit, cost ceiling vÃ  emergency kill switch hoáº¡t Ä‘á»™ng.
- [ ]  CI/CD xanh, keyless, cÃ³ staging, smoke test tá»± Ä‘á»™ng vÃ  rollback Ä‘Ã£ diá»…n táº­p.
- [ ]  Dashboard/alerts/runbooks Ä‘á»§ Ä‘á»ƒ phÃ¡t hiá»‡n vÃ  xá»­ lÃ½ lá»—i production mÃ  khÃ´ng cáº§n truy cáº­p thá»§ cÃ´ng database.
- [ ]  Security, dependency/container scan vÃ  tenant-isolation tests khÃ´ng cÃ²n issue critical/high chÆ°a xá»­ lÃ½.
- [ ]  Production smoke/E2E report chá»©ng minh baseline vÃ  candidate dÃ¹ng cÃ¹ng locked evaluation protocol.
- [ ]  README, API contract, architecture, operations runbook vÃ  release checklist khá»›p vá»›i há»‡ thá»‘ng Ä‘ang deploy.
