# PromptOpt Delivery Checklist

## Production migration — 2026-08-10

- [x] Migrated production to GCP/Firebase project `project-7df9f963-9fe0-4b76-b3d`.
- [x] Provisioned Artifact Registry, private GCS, Firestore, Cloud Tasks, runtime/deploy service accounts, IAM and GitHub WIF with `app/infra/provision-production.ps1`.
- [x] Enabled Firebase Email/Password and Google Sign-In on the new project.
- [x] Configured Firebase Hosting at `https://project-7df9f963-9fe0-4b76-b3d.web.app`.
- [ ] Run authenticated production smoke tests for baseline, optimization, comparison and prompt review on the new project.

## Current handoff — 2026-08-08 (authoritative)

> Đây là trạng thái hiện tại và thứ tự thực hiện được đề xuất. Nếu một mục lịch sử phía dưới mâu
> thuẫn với phần này hoặc `Readme.md`, dùng phần Current handoff làm nguồn đúng. Các phase cũ được
> giữ lại để bảo toàn lịch sử quyết định.

### Đã hoàn thành: nền tảng và production vertical slice

- [x] Frontend React/Vite deploy tại `https://project-7df9f963-9fe0-4b76-b3d.web.app`.
- [x] Firebase Email/Password, Google Sign-In, register, login, logout và reset password.
- [x] FastAPI production chạy trên Cloud Run, được Firebase Hosting rewrite qua `/api/v1`.
- [x] Firebase token verification, owner-scoped API, Firestore repositories và private GCS.
- [x] Signed ZIP upload, project CRUD/settings, async AST analysis và function source viewer.
- [x] Cloud Tasks + OIDC internal endpoints cho analysis/baseline orchestration.
- [x] API container không chạy source người dùng; CoverUp và GEPA chạy trong hai Cloud Run Jobs riêng.
- [x] GitHub Actions dùng Workload Identity Federation; không dùng service-account JSON key.
- [x] Frontend và backend CI/deploy độc lập theo path filter; merge vào `main` deploy production.

### Đã hoàn thành: Experiment UI và backend contract

- [x] Chọn nhiều project, không giới hạn cứng 50 target ở request contract.
- [x] Sampling random/most branches/most statements/manual hoạt động ở backend.
- [x] `random_seed`, custom train/validation/test percentages và manual splits được lưu/chạy thật.
- [x] Dropdown COVERUP_MODEL/OPTIMIZE_MODEL; selected models được truyền xuống jobs.
- [x] Max attempts, repeat tests, concurrency, rate limit, pytest args, max metric calls,
  evaluation replicates và reflection temperature được nối frontend -> API -> runner.
- [x] Review cấu hình, create experiment, delete experiment và owner-scoped experiment list.
- [x] Queue/poll baseline, optimization và paired comparison bằng API thật.
- [x] Metrics, artifacts, candidate prompt, lineage và promotion decision hiển thị trên frontend.
- [x] Prompt review queue và approve/reject có comment/audit/idempotent decision.

### Đã hoàn thành: sample repositories và auto-setup

- [x] Catalog read-only cho `isort`, `mimesis`, `mlxtend`, `typesystem`; không ghi sample Project/Function dư
  vào Firestore.
- [x] Sample snapshots được deploy từ `src/sample_repo.zip`; CI tự extract trước test/build.
- [x] Preflight không chạy setup script của repo; tạo minimal distribution metadata và validate imports
  trước khi gọi Gemini.
- [x] isort: cung cấp metadata + `tomli`; loại `_vendored` và `deprecated` theo coverage config.
- [x] mlxtend: validate NumPy, SciPy, Pandas, scikit-learn, Matplotlib và joblib.
- [x] typesystem: validate Jinja2 và YAML.
- [x] Lưu `project_setup.json` làm artifact chẩn đoán cho baseline/GEPA.
- [x] Cùng setup environment được dùng khi sinh test và khi đo coverage cuối.

### Đã hoàn thành trong code: exact-target baseline fix

- [x] Phân tích artifact isort 10 target: setup pass nhưng `G=0, F=19, U=4`, không có accepted
  `.py`; 0% khi đó là kết quả thật, không phải lỗi công thức coverage.
- [x] Xác định runner cũ match 10 target thành 9 segment; `Config.__init__` bị bỏ vì chỉ lọc tên hàm.
- [x] Thay contract protocol v1 bằng protocol v2 có exact `source_file + qualified_name`.
- [x] Baseline web dùng `--target-spec-file` và `--prompt-template-file` giống pipeline `cloud`.
- [x] Loại wrapper `VersionedPrompter/get_missing_coverage` cũ khỏi sandbox entrypoint.
- [x] Đồng bộ baseline/error prompt với prompt chuẩn của GEPA, gồm hướng dẫn dùng `get_info`.
- [x] Metrics map theo `source_file::qualified_name`, không nhầm function trùng tên giữa các file.
- [x] Giữ structured attempt trace của CoverUp; chỉ parse raw log làm fallback.
- [x] Zero-test baseline giữ denominator hợp lệ và không báo covered branch khi covered statements = 0.
- [x] Backend test **38 passed**, optimizer invariant test **51 passed**, Ruff/py_compile/diff check pass.
- [x] Build local thành công API image và CoverUp runner image sau bản sửa.
- [ ] Merge/deploy bản exact-target fix lên `main`; production hiện chưa được xem là đã xác nhận cho
  tới khi backend deploy workflow xanh.

### P0 — Xác nhận runner mới trên production

- [ ] Xác nhận CI backend và backend deployment đều xanh trên cùng commit.
- [ ] Xác nhận `promptopt-api` revision, `promptopt-coverup-runner` và `promptopt-gepa-runner` cùng
  dùng image SHA của release mới.
- [ ] Tạo **experiment mới** cho isort; không dùng lại run/artifact trước exact-target fix.
- [ ] Smoke 10 random/manual target bằng `gemini-2.5-flash`, `max_attempts=5`, `repeat_tests=2`.
- [ ] Xác nhận số exact target trong spec bằng số target đã chọn; không còn 10 -> 9 ngoài trường hợp
  nhiều targets chủ động trỏ cùng một function.
- [ ] Xác nhận `project_setup.json.import_validation=passed`.
- [ ] Xác nhận `attempt_trace.jsonl` có outcome theo target; nếu có test tốt phải thấy
  `coverage_gain_saved`.
- [ ] Xác nhận `generated_tests.zip` chứa `test_opt_*.py` khi G > 0.
- [ ] Xác nhận `target_coverage.json` dùng key `source_file::qualified_name` và aggregate khớp raw units.
- [ ] Smoke `typesystem`, sau đó `mlxtend`; ghi lại model/settings/cost/latency và failure categories.
- [ ] Chạy full production pipeline baseline -> optimize -> locked comparison -> review.
- [ ] Lưu sanitized release evidence; không commit UID, token, signed URL, private object path hoặc
  raw `CheckOutput`.

### P1 — Tăng chất lượng baseline và khả năng chẩn đoán

- [ ] Hiển thị trực tiếp trên UI số `G/F/U/R`, accepted test count và nguyên nhân attempt thất bại.
- [ ] Hiển thị cảnh báo khi chọn “most statements” với function quá lớn; không tự thay đổi lựa chọn
  hoặc model của người dùng.
- [ ] Thêm artifact manifest version/checksum/size/content type cho mọi baseline output.
- [ ] Thêm runner tests cho malformed model response, empty response, timeout, partial artifact upload
  và target không tồn tại.
- [ ] Đánh giá cơ chế giữ các test function pass khi một generated module có cả test pass và fail;
  chỉ triển khai nếu vẫn đảm bảo isolation/determinism và có regression tests.
- [ ] Thêm controlled benchmark matrix cho sample repo/model/sampling method; mỗi lần benchmark dùng
  artifacts directory mới và budget được phê duyệt.
- [ ] Không coi unit tests pass là bằng chứng prompt/model tạo coverage tốt; chỉ kết luận bằng live
  benchmark cùng evaluation protocol.

### P2 — Correctness và recovery

- [ ] Idempotency key/transaction cho create baseline, optimize, compare và Cloud Task retry.
- [ ] Chặn double-click tạo hai active runs cùng loại cho một experiment.
- [ ] Cancellation API/state cho baseline, optimization, comparison và Cloud Run Job execution.
- [ ] Phân biệt rõ failed/timed_out/cancelled/queue failure/provider failure.
- [ ] Durable GEPA checkpoint/resume vượt giới hạn Cloud Tasks 30 phút.
- [ ] Freeze project/source/settings checksum, dataset checksum và baseline denominators.
- [ ] Version execution/result/coverage/final-validation schemas và migration strategy cho document cũ.
- [ ] Persist model/provider, token usage, estimated cost, latency và normalized runner config.

### P3 — Hoàn thiện frontend không mock

- [ ] Thêm Dashboard aggregate API rồi chuyển workflow production sang `VITE_DATA_MODE=connected`.
- [ ] Quyết định Datasets là resource độc lập hay experiment snapshot; nối API hoặc bỏ route.
- [ ] Xóa import trực tiếp `mocks/fixtures/platform` khỏi `Datasets.tsx`.
- [ ] Quyết định Playground là production feature hay demo-only; nếu production phải dùng isolated
  runner, auth, quota và cost ceiling.
- [ ] Nối/kiểm tra Save project settings end-to-end.
- [ ] Kiểm tra loading/empty/error/retry/403/expired-session cho mọi production screen.
- [ ] Responsive, keyboard navigation, focus, labels, contrast và browser E2E.

### P4 — Security, quota, observability và lifecycle

- [ ] Tenant-isolation tests cho project/experiment/run/prompt/artifact giữa user A và user B.
- [ ] Threat model và tests cho traversal, symlink, device file, ZIP bomb và malicious generated test.
- [ ] Quota theo user/workspace: uploads, targets, active jobs, LLM calls, runtime và cost ceiling.
- [ ] Rate limit, budget alert và emergency kill switch cho CoverUp/GEPA.
- [ ] Artifact/source retention, cascade delete và scheduled cleanup có dry-run/audit/retry.
- [ ] Correlation IDs và structured logs xuyên request -> task -> job -> artifact.
- [ ] Cloud Monitoring dashboard/alerts cho API, queue, job, provider và cost.
- [ ] Staging riêng, Firestore backup/restore, dependency/container scans và rollback drill.

### Definition of Done gần nhất

- [ ] Ba sample repo có production smoke evidence sau exact-target fix.
- [ ] User hoàn thành được baseline -> optimize -> compare -> review trên UI production.
- [ ] Không còn mock trên production routes hoặc mock được gắn nhãn demo-only rõ ràng.
- [ ] Retry/double-submit/timeout/restart không tạo duplicate hoặc state sai.
- [ ] Quota, cost controls, monitoring, alerts, retention và tenant isolation được kiểm chứng.
- [ ] CI/CD xanh, keyless, có staging/E2E/rollback evidence.

---

> Mục tiêu hiện tại: biến frontend prototype thành frontend production-ready, vẫn demo được khi backend chưa hoàn thiện, sau đó deploy Firebase Hosting. Backend chỉ deploy khi có vertical slice đầu tiên hoạt động; không deploy boilerplate hiện tại.

## Nguyên tắc đã chốt

- [ ] `main` luôn deploy production; mọi thay đổi đi qua pull request.
- [ ] Feature branch chỉ lint, typecheck, test và build; không deploy production.
- [x] Frontend và backend deploy độc lập bằng path filter trong GitHub Actions.
- [ ] UI không import dữ liệu mock trực tiếp trong page/component.
- [ ] Mock và HTTP cùng implement một repository/service interface.
- [ ] Production không tự fallback từ API sang mock khi API lỗi.
- [ ] Các tác vụ optimization luôn chạy bất đồng bộ; API không chờ Gemini/pytest hoàn tất.
- [ ] Public frontend không đồng nghĩa với public Python code execution; tính năng chạy code phải có auth và quota.

---

## Phase 1 — Audit và dọn frontend prototype

### 1.1 Dọn project sinh từ Figma

- [x] Tạo branch `feature/frontend-foundation`.
- [x] Chỉ giữ các plugin Figma thực sự cần; loại bỏ `.figma` plugin khỏi production Vite config.
- [ ] Sửa encoding lỗi trong metadata và source (`PromptOpt —`, comment tiếng Việt bị mojibake).
- [x] Đổi package name từ `figma-make-app` thành `promptopt-frontend`.
- [x] Chọn một package manager duy nhất: npm.
- [x] Giữ `package-lock.json` và xóa `pnpm-lock.yaml`.
- [x] Chuẩn hóa Node version bằng `.nvmrc` và trường `engines` trong `package.json`.
- [ ] Kiểm tra và bỏ dependency không sử dụng.
- [x] Thêm title, description, theme color và Open Graph metadata đúng tên sản phẩm (favicon riêng còn chờ brand asset).
- [ ] Quyết định robots: production cho phép index hoặc tiếp tục `noindex` nếu đang private beta.

### 1.2 Bổ sung quality scripts

- [x] Thêm script `typecheck`: `tsc --noEmit`.
- [x] Thêm ESLint và script `lint`.
- [x] Tách `format` và `format:check`.
- [x] Thêm Vitest + React Testing Library và script `test`.
- [ ] Thêm `test:coverage` nếu cần coverage frontend.
- [x] Đảm bảo clean `npm ci`, lint, typecheck, test và production build chạy thành công:

```powershell
cd app\frontend
npm ci
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run build
```

### 1.3 Cấu trúc frontend đích

- [ ] Chuyển từ cấu trúc `pages + components` phẳng sang cấu trúc theo feature:

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

- [ ] Giữ shared component thực sự dùng chung trong `components/`; component riêng nằm trong feature.
- [ ] Không tạo một file API/repository khổng lồ cho mọi domain.
- [x] Bật TypeScript strict và sửa toàn bộ type error.

---

## Phase 2 — Navigation, state và error handling thực tế

- [x] Cài router nhẹ (`wouter`) và thay `useState<Page>` bằng URL routes.
- [x] Định nghĩa các route nền tảng:

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

- [x] Có auth gate cho các trang cần đăng nhập (demo auth adapter; Firebase Auth sẽ thay ở Phase 4).
- [x] Refresh hoặc mở deep link giữ đúng URL phía client (Firebase SPA rewrite sẽ hoàn thiện phía hosting).
- [x] Trang không tồn tại hiển thị `404`.
- [x] Thêm application-level error boundary.
- [ ] Mỗi màn hình dữ liệu có đủ loading, empty, error và retry state.
- [ ] Không lưu server data trong global React state thủ công.
- [x] Dùng TanStack Query cho Dashboard server state/cache.
- [x] Dùng local state cho UI state như form, tab và sidebar; tiếp tục migrate server data ở các feature còn lại.
- [ ] Thêm toast/notification dùng chung.
- [ ] Kiểm tra responsive desktop, tablet và mobile.
- [ ] Kiểm tra keyboard navigation, focus state, label và contrast cơ bản.

---

## Phase 3 — Cô lập và giảm mock data

### 3.1 Định nghĩa domain types trước API

- [ ] Định nghĩa `Project`, `Experiment`, `OptimizationRun`, `PromptVersion`, `Metrics`, `Artifact`.
- [ ] Định nghĩa run state machine dùng chung trong frontend:

```text
queued -> preparing -> baseline -> optimizing -> evaluating
       -> succeeded | failed | cancelled | timed_out
```

- [ ] Dùng ID/string timestamp giống contract backend dự kiến; không dùng label UI làm enum domain.
- [ ] Tất cả metrics có unit rõ ràng: percent, seconds, token count, USD estimate.

### 3.2 Repository contracts

- [x] Tạo interface `ProjectRepository` cho list/detail/create project và function contract kế tiếp.
- [ ] Tạo interface `ExperimentRepository`.
- [ ] Tạo interface `RunRepository`.
- [ ] Tạo interface `PromptRepository`.
- [ ] Page chỉ gọi hooks/use cases, không gọi `fetch` và không import mock fixture.
- [x] Tạo `MockProjectRepository` và `HttpProjectRepository` dùng cùng contract; Projects không fallback âm thầm.
- [ ] Đưa toàn bộ fixture vào `src/mocks/fixtures`; không rải object hardcode trong component.
- [ ] Mock phải mô phỏng cả latency, empty state và error state có kiểm soát.
- [x] Tạo `DashboardRepository`, `MockDashboardRepository` và `HttpDashboardRepository` làm mẫu chuẩn đầu tiên.

### 3.3 Chế độ chạy

- [x] Validate environment variables hiện có tại startup bằng Zod.
- [x] Chuẩn bị `.env.example` nền tảng; bổ sung Firebase variables ở Phase 4:

```env
VITE_APP_MODE=demo
VITE_API_BASE_URL=/api/v1
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_STORAGE_BUCKET=
VITE_FIREBASE_APP_ID=
```

- [x] `VITE_APP_MODE=demo`: dùng mock repository và hiển thị badge “demo data”.
- [x] `VITE_APP_MODE=connected`: chỉ dùng HTTP repository cho feature đã migrate.
- [x] Connected mode hiển thị lỗi API thật, không fallback âm thầm sang mock.
- [ ] Có thể bật connected mode theo từng feature trong quá trình ghép backend, nhưng flag phải explicit.

---

## Phase 4 — Firebase Authentication

- [ ] Tạo Firebase project development và production riêng nếu ngân sách cho phép.
- [x] Bật Firebase Authentication, Google Sign-In và Email/Password cho project `vinaip002`; OAuth brand là `PromptOpt`.
- [x] Hoàn thiện UI chuyển đổi Login/Register, validation confirm password và Firebase display name.
- [x] Hoàn thiện email login, account registration và password reset qua Firebase Auth.
- [x] Connected auth dùng Firebase Auth SDK; `sessionStorage` chỉ còn trong adapter demo tách biệt.
- [x] Tạo `AuthProvider` cung cấp `user`, `loading`, `error`, `signIn`, `signOut`.
- [x] API client tự lấy Firebase ID token và gắn `Authorization: Bearer <token>`.
- [x] Token refresh và phiên hết hạn do Firebase Auth SDK quản lý qua `onAuthStateChanged`/`getIdToken`.
- [x] Không lưu access token thủ công trong localStorage/sessionStorage.
- [x] Logout xóa query cache và dữ liệu nhạy cảm phía client.
- [x] Demo mode có demo account và badge rõ ràng; workflow production dùng Firebase Auth.

---

## Phase 5 — API contract sẵn sàng để ghép backend

- [x] Chốt prefix frontend `/api/v1`, có thể override bằng environment variable.
- [x] Chốt error envelope thống nhất:

```json
{
  "error": {
    "code": "RUN_NOT_FOUND",
    "message": "Optimization run was not found",
    "request_id": "..."
  }
}
```

- [ ] Chốt endpoint MVP:

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

- [ ] `POST /experiments/{id}/runs` trả `202` và `run_id`, không chờ job hoàn tất.
- [ ] Dùng `Idempotency-Key` khi tạo run để tránh submit trùng.
- [ ] Generate hoặc kiểm tra TypeScript types từ OpenAPI khi backend bắt đầu.
- [ ] Thêm contract tests cho mock repository và HTTP repository.

---

## Phase 6 — Chuẩn bị deploy frontend Firebase Hosting

### 6.1 Firebase config

- [x] Firebase CLI đã được cài, đăng nhập và liên kết production project `vinaip002`.
- [x] Tạo `.firebaserc` với alias `prod` và Hosting target `frontend`; giữ `.firebaserc.example` làm mẫu cho dev/prod tách biệt sau này.
- [x] Tạo `firebase.json` với public directory `app/frontend/dist`.
- [x] Thêm SPA rewrite về `/index.html`.
- [x] Thêm cache header dài cho hashed JS/CSS/assets.
- [x] Đặt `index.html` là `no-cache`.
- [x] Chưa thêm `/api/**` Cloud Run rewrite cho đến khi backend API được deploy.
- [x] Không dùng `pinTag: true` vì frontend/backend cần deploy độc lập.
- [x] Firebase web config dùng `VITE_*`; không đưa service-account credential vào frontend.

### 6.2 Pre-deploy acceptance

- [x] Clean `npm ci` và production build thành công.
- [x] Không còn TypeScript/lint error.
- [x] API base mặc định là same-origin `/api/v1`, không hardcode localhost trong production config.
- [x] `.env.local` và service-account JSON không được sử dụng/commit; CI dùng OIDC.
- [x] Test `/` và direct URL `/dashboard` trên Firebase Hosting: đều HTTP 200 và trả SPA shell.
- [ ] Test login/logout/refresh session.
- [x] Test demo auth gate và badge `demo data`.
- [ ] Test empty/error/loading states.
- [ ] Lighthouse sanity check cho performance, accessibility và best practices.
- [x] Production source map đang tắt trong Vite config.

### 6.3 Deploy thủ công lần đầu

- [x] Preview channel `frontend-foundation` đã dùng để nghiệm thu và đã xóa; feature branch hiện test bằng `npm run dev`.
- [x] Smoke test HTTPS, SPA rewrite và cache headers trên Firebase Hosting.
- [x] Deploy live production tự động từ `main` thành công.
- [x] Ghi lại Firebase project ID, Web App ID, Hosting site ID và live URL trong `app/Readme.md`.
- [ ] Kiểm tra rollback một Firebase release.

---

## Phase 7 — CI/CD frontend

- [x] Tạo workflow frontend CI và deploy riêng; Python CI có backend path filter.
- [x] Dùng path filter `app/frontend/**`, `firebase.json` và workflow files.
- [x] Pull request/feature branch được cấu hình chỉ chạy:

```text
npm ci
format:check
lint
typecheck
test
build
```

- [x] Push/merge vào `main` chạy lại toàn bộ frontend checks trước deploy.
- [x] Workflow chỉ deploy Firebase Hosting sau khi verify frontend thành công.
- [x] Workflow dùng GitHub Environment `production`; Firebase Web App config được lấy lúc chạy bằng WIF, không cần copy API key vào GitHub secrets/variables.
- [x] Cấu hình deploy concurrency để hai commit không deploy đè nhau.
- [x] Workflow dùng WIF provider `github-actions/p002-main`, giới hạn repo `binh39/P-002` và nhánh `main`; service account chỉ có `roles/firebasehosting.admin`.
- [ ] Bật branch protection cho `main`: PR, required checks và cấm force push.
- [ ] Sau khi ổn định, cân nhắc PR preview channel trỏ vào dev resources, không dùng production backend/data.

---

## Phase 8 — Khi nào deploy backend?

### Không deploy backend hiện tại

- [ ] Không deploy boilerplate `/chat`/LangGraph/OpenAI hiện tại chỉ để có một Cloud Run URL.
- [ ] Có thể chuẩn bị Artifact Registry, service accounts và IAM trước nhưng chưa cần giữ một service rỗng đang chạy.

### Deploy backend ngay khi có vertical slice đầu tiên

- [ ] Deploy khi backend có tối thiểu:
  - [x] `GET /health`.
  - [x] Production configuration và structured logging.
  - [x] Firebase ID token verification.
  - [x] CORS/same-origin policy đúng.
  - [x] Module `projects + signed upload` đã được code với adapter local và Google Cloud.
  - [x] Unit/integration tests cho module đó.
  - [x] Docker context nằm tại `app/`, image chỉ copy `app/backend` và loại frontend khỏi image.
  - [x] Docker image chạy bằng non-root user và đã qua smoke test upload → create/list project.
  - [x] Service account quyền tối thiểu.
- [x] Khi API đã deploy, thêm Firebase Hosting rewrite `/api/**` sang Cloud Run.
- [x] Chuyển đúng frontend feature từ mock repository sang HTTP repository.
- [x] Deploy backend độc lập khi `app/backend/**` hoặc backend dependency thay đổi.
- [ ] Không chờ hoàn thiện nhiều module backend mới deploy; deploy từng vertical slice nhỏ sau khi đạt các điều kiện trên.

### Backend vertical slice đề xuất đầu tiên

```text
Firebase login
  -> POST /api/v1/uploads
  -> browser upload ZIP bằng signed URL
  -> POST /api/v1/projects
  -> GET /api/v1/projects
  -> Dashboard hiển thị project thật
```

Slice tiếp theo:

```text
Create experiment
  -> POST /experiments/{id}/runs
  -> Cloud Run Job chạy baseline pytest/coverage
  -> GET /runs/{id}
  -> UI hiển thị progress và artifact
```

---

## Phase 9 — Project Analysis vertical slice

- [x] `POST /api/v1/projects/{project_id}/analyze` trả `202` và enqueue Cloud Tasks.
- [x] Worker nội bộ xác thực Google OIDC token và không chấp nhận Firebase user token.
- [x] Phân tích ZIP bằng Python AST, có giới hạn số file và kích thước giải nén.
- [x] Lưu function snapshot, source range và aggregate metrics vào Firestore.
- [x] Hoàn thiện API list functions và xem source theo function ID.
- [x] Project Detail có re-analyze, polling khi đang chạy, loading/error/failed state.
- [x] Project tạo mới tự động bắt đầu analysis trong HTTP repository.
- [x] Provision queue `promptopt-analysis`, retry tối đa 5 lần và concurrency 2.
- [x] Smoke test production Firebase Auth → upload → Cloud Task → AST → function source.

Slice tiếp theo sau Project Analysis:

```text
Create experiment
  -> chọn project/functions đã phân tích
  -> POST /experiments
  -> POST /experiments/{id}/runs trả 202
  -> worker chạy baseline pytest/coverage trong sandbox
```

---

## Definition of Done cho mốc “Frontend deployed”

- [x] Preview public URL truy cập được và HTTPS hoạt động.
- [x] Navigation dùng URL, refresh/deep link hoạt động trên Firebase Hosting.
- [x] Firebase Auth token và API được kiểm thử end-to-end trên hạ tầng thật.
- [ ] Không còn auth giả bằng `sessionStorage`.
- [ ] Mock data chỉ tồn tại sau repository contracts và có badge demo.
- [ ] Không component/page nào import trực tiếp mock fixtures.
- [ ] Loading/empty/error states đã có cho các màn hình chính.
- [ ] CI frontend pass trên pull request.
- [ ] Merge `main` tự deploy Firebase Hosting.
- [ ] Có cách rollback và README ghi rõ quy trình deploy.

## Thứ tự thực hiện ngay

1. [ ] Phase 1: dọn Figma scaffold và thiết lập quality scripts.
2. [ ] Phase 2: thêm router, providers và error handling.
3. [ ] Phase 3: chuyển mock data sau repository contracts.
4. [x] Phase 4: tích hợp Firebase Auth, bật Google provider và điền Firebase project config thật.
5. [x] Phase 6: cấu hình Firebase Hosting, nghiệm thu preview, xóa preview và deploy live production.
6. [x] Phase 7: frontend CI/CD tự động deploy `main` đã hoạt động.
7. [x] Phase 5 + 8: backend vertical slice đầu tiên tại `app/backend` đã provision GCP, deploy Cloud Run và nối Firebase Hosting.

---

## Phase 10 — Experiment, CoverUp baseline và GEPA optimization

### 10.1 PR 1 — Experiment API và run lifecycle

- [x] Tạo branch `feature/experiment-baseline-slice` từ `main`.
- [x] Tạo module `app/backend/modules/experiments`.
- [x] Thêm trạng thái `draft`, `baseline_queued`, `baseline_running`, `baseline_succeeded`, `failed`.
- [x] Thêm API tạo/lấy experiment từ project đã analysis và các function hợp lệ.
- [x] Thêm API tạo baseline run trả `202` và API polling run.
- [x] Tạo in-memory repository cho local/test và Firestore repository cho production.
- [x] Tạo Cloud Tasks dispatcher và internal worker endpoint có Google OIDC authentication.
- [x] Không chạy source upload trực tiếp trong HTTP request.
- [x] Thêm API tests cho ownership, analysis prerequisite, queue run và polling.

### 10.2 PR 2 — Isolated CoverUp baseline runner

- [x] Tạo runner image riêng tại `app/sandbox/Dockerfile`.
- [x] Chạy source trong container với network disabled, source read-only, drop capabilities và giới hạn CPU/RAM/PID.
- [x] Thêm timeout tổng và kiểm tra ZIP path traversal.
- [x] Chỉ bật local Docker runner khi `BASELINE_EXECUTION_BACKEND=docker`; mặc định fail-closed.
- [x] Hỗ trợ Vertex ADC local và build được image `promptopt-coverup-runner:local`.
- [x] Thêm giới hạn tổng dung lượng giải nén và số file cho runner.
- [x] Chặn symlink, device file và ZIP entry không phải regular file.
- [ ] Không truyền secret trực tiếp trên Docker command line.
- [ ] Thêm maximum provider retries và maximum total LLM calls cho CoverUp.
- [x] Chạy smoke test thật với fixture project nhỏ và Vertex Gemini (`score=1.0`, statement/branch `100%`).
- [ ] Chạy smoke test isort với function được chọn qua API.

### 10.3 Prompt bundle và baseline artifacts

- [x] Định nghĩa `PromptBundle` gồm `initial` và `error`.
- [x] Validate placeholder bắt buộc và sinh prompt digest ổn định.
- [x] Mount prompt JSON riêng và gọi CoverUp bằng `--prompt-template-file`.
- [x] Giữ baseline prompt immutable trong một run.
- [x] Lưu prompt digest vào baseline run.
- [ ] Tạo và lưu prompt version ID riêng trong prompt registry.
- [x] Không parse coverage từ stdout; dùng structured coverage JSON làm nguồn chính.
- [x] Xuất `target_coverage.json` theo từng target function, không chỉ coverage tổng.
- [x] Bổ sung structured `attempt_trace.jsonl` từ CoverUp request/response log.
- [ ] Xác minh trace chứa đủ prompt input, model response, generated test, pytest error và reason dừng qua smoke test thật.
- [x] Lưu generated tests ZIP, CoverUp log, stdout và prompt JSON.
- [ ] Lưu command metadata và runner config đã chuẩn hóa.
- [x] Upload artifacts vào object storage theo owner/project/experiment/run.
- [ ] Lưu checksum, object name, size, content type và retention metadata vào Firestore.
- [ ] Thêm `GET /api/v1/runs/{run_id}/artifacts` và signed download URL có ownership check.
- [x] Tính deterministic statement/branch score theo từng symbol.
- [x] Aggregate theo executable units; không trung bình đơn giản phần trăm giữa các function.
- [ ] Lưu token usage, cost estimate, latency, model và provider.

### 10.4 Dataset và split chống data leakage

- [x] Tạo dataset snapshot từ function người dùng chọn, không hard-code isort.
- [ ] Lưu project version, source checksum và settings checksum cùng dataset.
- [x] Chia `train`, `validation`, `test` bằng seed cố định và lưu split trong experiment.
- [x] Dataset dưới 3 targets được đánh dấu baseline-only, không giả lập validation/test.
- [x] Chỉ đánh dấu `optimization_eligible` khi train/validation/test đều không rỗng (tối thiểu 3 targets).
- [x] Không dùng locked `test` split trong GEPA search/candidate selection.
- [ ] Không để cùng function/source version xuất hiện ở nhiều split.
- [ ] Đóng băng denominator statement/branch từ baseline preflight.

### 10.5 PR 3 — DSPy/GEPA prompt optimization

- [x] Tích hợp pipeline GEPA của `duyvu1105` qua Cloud Run Job riêng `promptopt-gepa-runner`, dùng namespace `runner-jobs/gepa/<run-id>` và không truy cập `prompt_optimization_v3`.
- [ ] Deploy image/job GEPA theo workflow mới và chạy authenticated smoke test với budget web giới hạn 30 metric calls.

- [x] Pin `dspy==3.2.1` và `gepa==0.0.27`.
- [x] Tách model sinh test (`COVERUP_MODEL`) và reflection (`OPTIMIZE_MODEL`).
- [x] Validate Gemini/Vertex provider configuration và model allowlist.
- [x] Tạo GEPA adapter nhận `PromptBundle`, coverage và attempt trace thật.
- [x] Reward phải do coverage code tính; không dùng LLM judge.
- [x] Reflection chỉ sửa `initial` và `error`.
- [x] Loại candidate thiếu placeholder, format lỗi hoặc vượt size trước khi gọi CoverUp.
- [x] Cache theo prompt digest, source checksum, targets, split, model và runner config.
- [ ] Tách workspace theo candidate/target/replicate để không rò generated tests.
- [ ] Thêm `max_metric_calls`, reflection minibatch, replicate, rate limit và concurrency limit.
- [ ] Persist GEPA checkpoint để resume sau timeout/restart.
- [x] Thêm `POST /api/v1/experiments/{id}/optimize`, trả `202`.
- [ ] Bổ sung trạng thái `optimizing`, `candidate_evaluating`, `optimization_succeeded`, `timed_out`, `cancelled`.
- [ ] Lưu candidate prompt, parent prompt, generation, score, cost, latency và failure reason.
- [x] Không tự ghi đè baseline hoặc production prompt sau GEPA search.

#### E67 validation-only Pareto output portfolio

- [x] Candidate-test archive khóa theo split/evaluation digest, content-deduplicate, greedy set-cover và verify suite 5 lần.
- [x] Portfolio hai replicate từ 5 Pareto prompts đạt 96,32–97,59%, hơn single-best ít nhất 18,85 điểm.
- [x] Cost gate validation: baseline trước, chỉ mở stage cho target còn gap; 29/180 calls đạt 96,93% và pass 5 lần.
- [x] Chạy one-shot holdout gate: 10/60 calls, tiết kiệm 83,33% nhưng gain coverage = 0; reject E67, không promote production.

#### E70 failure-stratified benchmark

- [x] Tạo builder AST deterministic cho 7 challenge strata; không dùng model hoặc coverage để chọn target.
- [x] Khóa dataset mới 16 train / 8 validation / 8 test, cân bằng 4 project và difficulty 25/50/25.
- [x] Loại toàn bộ 35 target cũ, holdout E67 và structural duplicate; contract test khóa dataset/holdout hash.
- [x] Import/setup preflight pass cho isort, mimesis, mlxtend và typesystem.
- [x] Chạy baseline labeling chỉ trên train/validation bằng Gemini 3.5 Flash-Lite; E70 test vẫn chưa mở.
- [x] Xác định hai hard target bằng 0 chiếm 99,64% statement và 95,24% branch headroom.
- [ ] Triển khai failure-triggered E42/E44 retrieval cho constructor/callee/usage/setup contract.
- [ ] Paired validation candidate với baseline; chỉ freeze winner trước one-shot E70 holdout.

### 10.6 PR 4 — Paired comparison và promotion gate

- [x] Chọn candidate bằng validation rồi khóa candidate trước final evaluation.
- [x] Chạy baseline và candidate trên cùng locked test targets, runner config và replicate count.
- [ ] So sánh paired statement/branch coverage, pass rate, cost và latency.
- [x] Chỉ promote khi candidate tốt hơn baseline và qua hard gate.
- [x] Hard gate: pytest hợp lệ, không flaky, không timeout và không giảm pass rate.
- [x] Nếu GEPA giữ nguyên baseline digest thì skip final evaluation và ghi rõ reason.
- [x] Lưu `final_validation.json`, absolute/relative gain và promotion decision.
- [x] Tạo prompt version `in_review`; không tự động chuyển production.
- [x] Thêm approve/reject API có reviewer, comment, audit timestamp và idempotency.

### 10.7 Production runner trên Google Cloud

- [x] Không dùng Docker socket/Docker-in-Docker trong Cloud Run API service.
- [x] Push runner image riêng lên Artifact Registry.
- [x] Dùng Cloud Run Job cho execution; Cloud Tasks chỉ dispatch/orchestrate.
- [x] Tạo runner service account riêng với quyền tối thiểu trên source/artifact objects.
- [x] Dùng workload identity/Secret Manager; không mount ADC file trong production.
- [ ] Cấu hình job timeout, retries, parallelism, maximum instances và cancellation.
- [ ] Thêm quota theo user/workspace: concurrent runs, functions, LLM calls và cost ceiling.
- [ ] Thêm retention policy và xóa artifacts theo project.
- [x] Provision queue `promptopt-baseline`, hoàn thiện OIDC/IAM và production smoke test baseline.

### 10.8 Frontend integration

- [x] Tạo `ExperimentRepository` HTTP và domain types đúng backend contract.
- [x] Chuyển Create Experiment từ mock sang project/functions thật.
- [x] Gọi create experiment/run và polling bằng TanStack Query.
- [x] Hiển thị state machine thật từ queued đến succeeded/failed.
- [x] Hiển thị baseline metrics theo function và aggregate.
- [ ] Hiển thị prompt diff, generated tests, coverage artifacts, logs và failure reason.
- [ ] Hoàn thiện comparison và review/approve/reject bằng API thật.
- [x] Xóa mock experiment/run/comparison sau khi từng màn hình đã nối backend.

### 10.9 Verification và Definition of Done

- [x] Ruff format/check pass cho experiment foundation.
- [x] Backend tests pass (`36 passed` sau comparison artifact API).
- [x] Unit test score, cache key, prompt validation và promotion rule.
- [ ] Contract/integration test cho experiment, run và artifact APIs bằng fake executor.
- [ ] Docker smoke test fixture project và test timeout/retry/malformed response.
- [ ] Test Firestore ownership isolation và GCS artifact authorization.
- [ ] Test GEPA resume checkpoint và idempotent Cloud Task retry.
- [x] CI build cả API image và runner image khi source liên quan thay đổi.
- [ ] Production smoke test baseline → optimize → locked comparison → review.
- [ ] Chỉ merge GEPA khi report chứng minh baseline và optimized dùng cùng evaluation protocol.

---

## Phase 11 — Roadmap từ hiện tại đến production-complete

> Đây là danh sách ưu tiên cập nhật ngày 2026-08-07 và là nguồn theo dõi chính cho phần việc còn lại. Các mục chưa hoàn thành ở Phase 1–10 vẫn giữ giá trị kỹ thuật, nhưng nên được thực hiện theo thứ tự P0 → P5 dưới đây.

### P0 — Khôi phục release pipeline và xác nhận production hiện tại

- [x] Merge branch `fix/backend-artifact-registry-auth` vào `main`.
- [x] Xác nhận backend workflow dùng WIF access token và `docker/login-action`, không dùng user credential hoặc service-account key.
- [x] Xác nhận API image và runner image push thành công lên Artifact Registry.
- [x] Xác nhận Cloud Run API và Cloud Run Job cùng dùng image SHA của release mới nhất.
- [x] Chạy lại `Deploy frontend production` trên `main` sau sự cố GitHub Actions.
- [ ] Xác nhận `Frontend CI`, backend `CI`, frontend deploy và backend deploy đều xanh trên cùng release (workflow có path filter; cần một run kiểm chứng riêng sau outage).
- [x] Kiểm tra `/health`, Firebase Hosting rewrite `/api/v1`, Firebase login guard và CORS trên production.
- [x] Chạy smoke test authenticated: upload ZIP → create project → analysis → chọn functions → create experiment.
- [ ] Chạy smoke test đầy đủ: baseline → optimize → paired comparison → tạo prompt version → approve/reject.
- [ ] Lưu report smoke test đã loại token/sensitive data làm release evidence (không commit Firebase UID, private artifact path hoặc ZIP fixture lớn).
- [x] Ghi lại image SHA, Cloud Run revision và Firebase Hosting release để có điểm rollback.

#### P0 release evidence — 2026-08-07

- [x] `main`: `085df3a`; backend deploy release: `fd8f3ce`.
- [x] Backend deploy [#13](https://github.com/binh39/P-002/actions/runs/31138705068) thành công sau khi dùng WIF access token + `docker/login-action`.
- [x] Cloud Run API revision: `promptopt-api-00014-j46`, 100% traffic, image `api:fd8f3ce85f222655f6fe8217abfb5701f3ba361f`.
- [x] Cloud Run Job image: `coverup-runner:fd8f3ce85f222655f6fe8217abfb5701f3ba361f`; latest execution `promptopt-coverup-runner-qsqr7` succeeded.
- [x] Firebase Hosting redeployed manually from `main` in `firebase + connected` mode. Production bundle contains `Comparison-CtGvmjBI.js` with paired-comparison API UI and no previous comparison fixture.
- [x] `GET https://vinaip002.web.app/api/v1/health` returns 200; unauthenticated `GET /experiments` returns 401; CORS preflight allows `https://c3-app-002.io.vn` and rejects an untrusted origin.
- [x] Existing authenticated baseline smoke evidence confirms upload → analysis → experiment → Cloud Tasks → Cloud Run Job → artifact result.
- [x] `smoke_production.ps1 -FullPipeline` supports deterministic multi-target selection, optimization, comparison and optional approve/reject; its result is sanitized and written to ignored `app/.smoke-results/`.
- [ ] Before marking P0 complete: run full authenticated smoke with a freshly generated Firebase ID token, then store a sanitized summary outside Git-tracked fixture/output paths.

### P1 — Hoàn tất frontend bằng API thật và loại bỏ mock production

- [x] Thêm catalog chỉ đọc cho `isort`, `mimesis`, `mlxtend`, `typesystem`; không ghi Upload/Project/Function sample vào Firestore.
- [x] Nối Projects và Create Experiment vào `GET /projects/samples` và pipeline Cloud Run thật.
- [ ] Deploy sample-project slice rồi chạy smoke từng repo; ưu tiên isort trước, sau đó mimesis, typesystem và mlxtend.

#### Uploaded Project — ZIP → analysis → isolated runner

- [x] Backend hỗ trợ signed ZIP upload, complete upload, tạo Project và owner-scoped project CRUD.
- [x] Static analysis không import/chạy source người dùng; đã đếm Python files, functions, statements, branches và lưu function source/LOC.
- [x] `HttpProjectRepository.create` đã nối upload → complete → create project → request analysis.
- [ ] Thêm Upload Project form/dropzone trên Projects, chỉ nhận ZIP và hiển thị size/type validation trước khi upload.
- [ ] Đổi Projects thành hai nguồn rõ ràng: **My Projects** từ `GET /projects` và **Sample Projects** từ `GET /projects/samples`.
- [ ] Hiển thị upload progress, analysis polling, ready/warning/failed state, retry và thông báo archive không hợp lệ.
- [ ] Hiển thị tổng files/functions/statements/branches và function table sau khi analysis hoàn tất.
- [ ] Cho Create Experiment chọn cả uploaded project và sample project; không chỉ gọi `listSamples()`.
- [ ] Tạo immutable project source snapshot gồm object name, archive checksum, analysis checksum, settings version và created timestamp.
- [ ] Chốt source-exchange contract cho Cloud Run Job: API truyền manifest + private GCS object của đúng project snapshot, không truyền signed URL dài hạn.
- [ ] Runner tải snapshot bằng service account, xác minh checksum, chống path traversal/symlink/ZIP bomb rồi giải nén vào workspace cô lập.
- [ ] Tự phát hiện package/source root, test directory, requirements/lock file và lưu `project_setup.json`; cho user override khi auto-detect không chắc chắn.
- [ ] Cài dependency trong image/workspace có timeout, cache có checksum và network policy; không chạy `setup.py` hoặc script tùy ý trong API container.
- [ ] Dùng cùng một source/setup snapshot cho baseline, GEPA candidate, paired comparison và coverage denominator.
- [ ] Cập nhật CoverUp/GEPA Cloud Run Jobs để nhận source snapshot của uploaded project thay vì chỉ đọc bundled `sample_repo`.
- [ ] Chỉ bỏ `BUNDLED_SAMPLE_REQUIRED` và bật `optimization_eligible` cho uploaded project sau khi source runner contract đã qua integration test.
- [ ] Thêm ownership check cho source object/manifest và bảo đảm user A không thể đưa object của user B vào runner.
- [ ] Thêm E2E/smoke: upload ZIP → analysis → chọn functions → baseline → optimize → compare trên uploaded project thật.

#### Review & Approval

- [x] Tạo frontend `PromptVersionRepository` và domain types đúng backend contract.
- [x] Nối prompt version từ `comparison.promptVersionId` vào trang Review.
- [x] Nối approve/reject API, comment, loading/error state và chống double-submit.
- [x] Sau review, invalidate/refetch experiment, comparison và prompt version queries.
- [x] Hiển thị reviewer, review timestamp, comment và trạng thái quyết định cuối.
- [x] Thay toàn bộ prompt/review queue hard-code trong `ReviewApproval.tsx`.
- [x] Thêm frontend repository tests cho approve/reject API contract; backend test ownership, filter và idempotent retry.

#### Prompt Registry

- [x] Backend đã có owner-scoped API get/list prompt versions, status filter và pagination cơ bản.
- [x] Frontend đã có `PromptVersionRepository` và `HttpPromptVersionRepository`; trang Registry chưa sử dụng chúng.
- [ ] Chốt Registry row là một prompt family/experiment; khi expand mới tải baseline, optimized versions và generation history.
- [ ] Tạo baseline thành Prompt Version bất biến, có `kind=baseline`, digest, nội dung, model/config và source experiment.
- [ ] Tạo optimized Prompt Version với `kind=optimized`, `parent_version_id`, lineage và optimization/comparison run IDs.
- [ ] Lưu optimized candidate dù không thắng dưới trạng thái `candidate`/`rejected`; chỉ `approved` version mới được active/promoted.
- [ ] Chốt semantics cho `active`, `approved`, `rejected`, `archived`; không dùng status chỉ tồn tại trong UI.
- [ ] Không gắn coverage cố định vào Prompt Version vì coverage phụ thuộc project snapshot, targets, model, seed và runner config.
- [ ] Tạo resource `PromptGenerationRun` riêng gồm prompt version, project snapshot, selected targets, model/settings, status và timestamps.
- [ ] Thêm API tạo/list/get/cancel PromptGenerationRun và API tải artifact có ownership check.
- [ ] Nút **Generate & verify tests** phải enqueue Cloud Task/Cloud Run Job; không sinh/chạy source trong API request hoặc API container.
- [ ] Lưu generated test modules, pytest log, coverage JSON và manifest trong private GCS; Firestore chỉ lưu metadata, metrics và object references.
- [ ] Artifact manifest phải có checksum, size, content type, schema version, source snapshot digest và retention deadline.
- [ ] Lưu statement coverage, branch coverage, aggregate score, pass rate, flaky/timeout/failure counts theo từng Generation Run.
- [ ] Khi so baseline với optimized, bắt buộc dùng cùng project snapshot, target set, model, seed, replicates và runner settings.
- [ ] Thêm endpoint/detail projection trả baseline + optimized pair, lineage, comparison metrics và generation runs gần nhất cho một Registry row.
- [ ] Nối Prompt Registry vào repository HTTP thật.
- [ ] Giữ UI dạng list; expand row để hiển thị hai prompt, lineage, source experiment, audit decision, run history và artifact download.
- [ ] Thêm Copy/View Prompt và Generate & verify riêng cho baseline và optimized version.
- [ ] Hiển thị loading/empty/error/running/failed/cancelled/succeeded state và polling có backoff cho generation run.
- [ ] Thêm filter theo project, experiment, kind, model, review status và created date; pagination phải dùng API thật.
- [ ] Xóa danh sách prompt hard-code trong `Registry.tsx` sau khi API list hoạt động.
- [ ] Thêm backend contract/integration tests và browser E2E cho Registry → generate baseline tests → generate optimized tests → xem coverage/artifacts.

#### Dashboard, Datasets, Settings và Playground

- [ ] Thêm dashboard aggregate endpoint hoặc tổng hợp có kiểm soát từ API hiện có.
- [ ] Nối Dashboard KPI, recent experiments và coverage trend vào dữ liệu thật.
- [ ] Xóa `MockDashboardRepository` khỏi production path; chỉ giữ demo repository trong local demo mode.
- [ ] Quyết định Datasets là resource độc lập hay chỉ là snapshot nằm trong Experiment.
- [ ] Nếu giữ trang Datasets: thêm list/detail API, checksum, split seed và source version.
- [ ] Nếu không giữ: bỏ route Datasets và hiển thị snapshot trong Experiment Detail.
- [ ] Xóa import trực tiếp `mocks/fixtures/platform` khỏi `Datasets.tsx`.
- [ ] Nối nút Save project settings với `PATCH /projects/{id}/settings`, có dirty/loading/success/error state.
- [ ] Quyết định Playground là tính năng production hay trang demo; nếu production phải dùng cùng sandbox/quota với runner.
- [ ] Không cho Playground chạy source người dùng trực tiếp trong API container.

#### Production frontend mode

- [ ] Build production với `VITE_AUTH_MODE=firebase` và `VITE_DATA_MODE=connected`.
- [ ] API lỗi phải hiển thị lỗi thật, tuyệt đối không fallback âm thầm sang fixture.
- [ ] Chỉ giữ `DemoAuthService` và fixture repositories cho local development/test có badge rõ ràng.
- [ ] Xóa constants/sample records hard-code khỏi Review, Registry và các màn hình production đã nối API.
- [ ] Kiểm tra loading, empty, error, retry, forbidden và expired-session state cho mọi trang thật.

### P2 — Độ đúng và khả năng phục hồi của experiment pipeline

- [ ] Tạo idempotency key/transaction cho create run, optimize, compare và Cloud Task retry.
- [ ] Không tạo hai active run cùng loại cho một experiment khi user double-click hoặc task retry.
- [ ] Thêm trạng thái và API cancellation cho baseline, optimization, comparison và Cloud Run Job.
- [ ] Phân biệt rõ `failed`, `timed_out`, `cancelled`, queue failure và infrastructure failure.
- [ ] Persist GEPA checkpoint và resume sau worker timeout/restart.
- [ ] Tách workspace/artifact prefix theo candidate, target và replicate để không rò generated tests.
- [ ] Đóng băng project/source/settings checksum khi tạo experiment.
- [ ] Đóng băng statement/branch denominator và runner/model config cho protocol so sánh.
- [ ] Ngăn cùng function/source version xuất hiện ở nhiều split.
- [ ] Lưu model/provider, token usage, latency, estimated cost và normalized runner command metadata.
- [ ] Lưu artifact manifest gồm checksum, size, content type, schema version và retention deadline.
- [ ] Version schema cho execution manifest, result JSON, coverage JSON và final validation report.
- [ ] Thêm migration/backward-compatibility strategy cho Firestore documents và artifacts cũ.
- [ ] Xác minh paired comparison dùng đúng cùng targets, replicates, model và runner config.
- [ ] Chốt promotion policy bằng config/version thay vì điều kiện không version hóa trong code.

### P3 — Security, tenant isolation, quota và data lifecycle

- [ ] Hoàn thành threat model cho upload, ZIP extraction, generated tests, Cloud Tasks, runner và artifact download.
- [ ] Test path traversal, symlink, device file, ZIP bomb, oversized archive và malformed manifest.
- [ ] Xác minh mọi public API đều kiểm tra Firebase user ownership ở service/repository boundary.
- [ ] Test user A không đọc/sửa/chạy project, experiment, run, prompt version hoặc artifact của user B.
- [ ] Xác minh internal endpoints chỉ nhận OIDC token đúng audience và service account.
- [ ] Giới hạn số project, upload size, functions/experiment, active runs và concurrent jobs theo user/workspace.
- [ ] Giới hạn CoverUp/GEPA total LLM calls, provider retries, metric calls, runtime và cost ceiling.
- [ ] Thêm rate limiting cho upload, analysis, baseline, optimize, compare và review endpoints.
- [ ] Đặt budget alert và kill switch để tắt optimize/runner khi vượt chi phí hoặc có abuse.
- [ ] Thiết kế delete project/experiment có cascade an toàn cho Firestore, GCS và queued tasks.
- [ ] Cấu hình retention policy cho source ZIP, runner exchange objects, logs và artifacts.
- [ ] Tạo scheduled cleanup có dry-run, audit log và khả năng retry.
- [ ] Rà IAM least privilege cho frontend deploy, backend deploy, API runtime và runner identities.
- [ ] Xác nhận không có service-account key, Firebase token hoặc generated credential được commit/log.
- [ ] Chốt egress policy cho runner để source/test người dùng không truy cập tùy ý ra ngoài.

### P4 — Observability, vận hành và kiểm soát chi phí

- [ ] Chuẩn hóa correlation IDs: request, user, project, experiment, run, task và job execution.
- [ ] Structured log mọi state transition, dispatch, retry, runner result và review decision.
- [ ] Không log Firebase token, source code, prompt nhạy cảm hoặc signed URL đầy đủ.
- [ ] Tạo Cloud Monitoring dashboard cho API latency/error rate, Cloud Tasks depth/age và Cloud Run Job failures.
- [ ] Tạo alert cho API 5xx, task retry/dead-letter, job timeout/failure, auth failure và quota exhaustion.
- [ ] Theo dõi LLM call count, token usage, latency và estimated cost theo user/experiment/model.
- [ ] Định nghĩa SLO ban đầu cho API availability, queue delay, baseline completion và optimization completion.
- [ ] Viết runbook cho failed deploy, stuck task, failed job, missing artifact, Firestore/GCS incident và provider outage.
- [ ] Thêm admin-safe diagnostic command/script theo run ID, không yêu cầu đọc dữ liệu tenant khác.
- [ ] Thiết lập Firestore backup/export và kiểm thử restore.
- [ ] Kiểm tra Artifact Registry cleanup policy và giữ đủ image SHA để rollback.

### P5 — Test strategy, staging, release và rollback

- [ ] Tạo GCP/Firebase staging tách production cho integration/E2E và preview frontend.
- [ ] CI chạy Ruff, backend tests, frontend format/lint/typecheck/test/build và build cả hai container images.
- [ ] Thêm contract tests cho upload, project, function, experiment, run, artifact và prompt-version APIs.
- [ ] Thêm integration tests bằng fake executor cho baseline → optimize → compare → review.
- [ ] Thêm Firestore emulator/repository tests cho transaction, ownership và concurrent update.
- [ ] Thêm GCS fake/emulator tests cho signed upload, artifact manifest, authorization và missing object.
- [ ] Thêm Cloud Task retry/idempotency và Cloud Run operation polling failure tests.
- [ ] Thêm runner tests cho timeout, malformed CoverUp output, provider retry và partial artifact upload.
- [ ] Thêm browser E2E cho auth, upload, analysis, create experiment, polling, comparison và review.
- [ ] Chạy load test có giới hạn cho concurrent polling, list APIs và task enqueue; không load test LLM production tùy ý.
- [ ] Kiểm tra accessibility, responsive layout, deep link, refresh và expired Firebase session.
- [ ] Scan dependencies/container images và xử lý vulnerability mức critical/high trước release.
- [ ] Pin/review version của actions, Python/Node dependencies, CoverUp, DSPy/GEPA và model names.
- [ ] Viết rollback frontend Hosting release, Cloud Run revision và runner Job image bằng SHA.
- [ ] Tạo release checklist có approver, migration step, smoke test, monitoring window và rollback owner.

### Definition of Done — Production-complete v1

- [ ] Không còn mock/fixture trên bất kỳ production route nào; demo mode chỉ bật rõ ràng ở local/test.
- [ ] User có thể hoàn thành upload → analysis → baseline → optimize → compare → review trên production UI.
- [ ] Mọi dữ liệu và artifact đều có ownership check, schema version, checksum và lifecycle policy.
- [ ] Pipeline chịu được double-submit, task retry, timeout và worker restart mà không tạo state sai/duplicate run.
- [ ] Quota, rate limit, concurrency limit, cost ceiling và emergency kill switch hoạt động.
- [ ] CI/CD xanh, keyless, có staging, smoke test tự động và rollback đã diễn tập.
- [ ] Dashboard/alerts/runbooks đủ để phát hiện và xử lý lỗi production mà không cần truy cập thủ công database.
- [ ] Security, dependency/container scan và tenant-isolation tests không còn issue critical/high chưa xử lý.
- [ ] Production smoke/E2E report chứng minh baseline và candidate dùng cùng locked evaluation protocol.
- [ ] README, API contract, architecture, operations runbook và release checklist khớp với hệ thống đang deploy.
