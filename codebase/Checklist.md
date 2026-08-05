# PromptOpt Delivery Checklist

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
- [ ] Sửa encoding lỗi trong metadata và source (`PromptOpt â€”`, comment tiếng Việt bị mojibake).
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
cd codebase\frontend
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
- [x] Tạo `firebase.json` với public directory `codebase/frontend/dist`.
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
- [x] Ghi lại Firebase project ID, Web App ID, Hosting site ID và live URL trong `codebase/Readme.md`.
- [ ] Kiểm tra rollback một Firebase release.

---

## Phase 7 — CI/CD frontend

- [x] Tạo workflow frontend CI và deploy riêng; Python CI có backend path filter.
- [x] Dùng path filter `codebase/frontend/**`, `firebase.json` và workflow files.
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
  - [x] Docker context nằm tại `codebase/`, image chỉ copy `codebase/src` và loại frontend khỏi image.
  - [x] Docker image chạy bằng non-root user và đã qua smoke test upload → create/list project.
  - [ ] Service account quyền tối thiểu.
- [ ] Khi API đã deploy, thêm Firebase Hosting rewrite `/api/**` sang Cloud Run.
- [ ] Chuyển đúng frontend feature từ mock repository sang HTTP repository.
- [ ] Deploy backend độc lập khi `codebase/src/**` hoặc backend dependency thay đổi.
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

## Definition of Done cho mốc “Frontend deployed”

- [x] Preview public URL truy cập được và HTTPS hoạt động.
- [x] Navigation dùng URL, refresh/deep link hoạt động trên Firebase Hosting.
- [ ] Firebase login/logout hoạt động trên domain thật.
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
7. [ ] Phase 5 + 8: backend vertical slice đầu tiên đã code tại `codebase/src`; còn provision GCP và deploy.
