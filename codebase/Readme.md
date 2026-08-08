# PromptOpt

PromptOpt là web app tối ưu prompt cho bài toán sinh Python unit test. Người dùng chọn project và
function, cấu hình dataset/model/CoverUp/GEPA, chạy baseline, tối ưu prompt, so sánh paired trên
locked test split, sau đó approve hoặc reject prompt candidate.

Tài liệu này là điểm bắt đầu cho người tiếp tục phát triển dự án. Trạng thái được cập nhật lần cuối
ngày **2026-08-08**.

## Trạng thái hiện tại

Ứng dụng đã có vertical slice chạy từ frontend đến Google Cloud:

1. Firebase Authentication xác thực người dùng.
2. Frontend gọi FastAPI qua Firebase Hosting rewrite `/api/**`.
3. Người dùng chọn bundled sample repo và tạo experiment; upload ZIP vẫn chỉ phục vụ phân tích project riêng.
4. Cloud Tasks điều phối DSPy/GEPA sang Cloud Run Job; baseline prompt là candidate số 0.
5. Job dùng sample repo đóng gói sẵn và chỉ nhận dataset/prompt qua GCS.
6. Candidate số 0 và candidate tối ưu được so sánh trên locked test split.
7. Prompt đủ điều kiện được tạo ở trạng thái `in_review`, rồi approve/reject có audit data.

Production hiện tại: [https://vinaip002.web.app](https://vinaip002.web.app).

Ứng dụng **chưa production-complete**. Các phần còn thiếu quan trọng nhất là production smoke cho
ba sample repo sau bản runner mới, idempotency/cancellation/checkpoint, quota/cost controls,
observability, tenant-isolation tests và xóa mock khỏi các màn hình phụ.

## Quy tắc source code

- Application backend FastAPI chỉ đặt trong `codebase/src`.
- Frontend React chỉ đặt trong `codebase/frontend`.
- Không xóa root `src/`: production runner đang dùng `src/coverup`, `src/optimization` và
  `src/sample_repo.zip`.
- `cloud/` chứa entrypoint và deployment scripts cho GEPA Cloud Run Job.
- Không sửa, ghi đè hoặc dùng prefix benchmark độc lập `prompt_optimization_v3` cho web workflow.
- Không commit `.env`, `.env.local`, Firebase token, service-account key, signed URL, raw smoke
  output hoặc `CheckOutput/`.

## Repository layout

```text
P-002/
  codebase/
    frontend/                 React/Vite frontend
    src/                      FastAPI application backend
      api/                    public API dependencies/router assembly
      modules/                auth, uploads, projects, analysis, experiments
      infrastructure/         Firestore, GCS, Cloud Tasks, Cloud Run clients
    tests/                    backend tests
    infra/                    Google Cloud provisioning and runtime env
    scripts/                  local/production smoke scripts
    Dockerfile                API image
    Readme.md                 current architecture and handoff guide
    Checklist.md              delivery history and prioritized backlog
  src/
    coverup/                  project-owned CoverUp engine
    optimization/             DSPy/GEPA runner, metrics, cache and promotion logic
    sample_repo.zip           source archive for the bundled isort/mlxtend/typesystem snapshots
    sample_repo/              bundled snapshots copied into the GEPA image during deployment
  cloud/
    run_job.py                GEPA Cloud Run Job entrypoint
    Dockerfile.web            GEPA runner image
    deploy_gepa_job.ps1       standalone GEPA deployment helper
    run_gepa_job.ps1          standalone GEPA execution/download helper
  tests/                      CoverUp/GEPA invariant and dataset tests
  .github/workflows/          CI and keyless production deployment
```

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript 5.7, Vite 8, Tailwind CSS 4 |
| Routing/state | Wouter 3, TanStack Query 5, React local state |
| Validation/charts | Zod 4, Recharts 3 |
| Frontend quality | Oxfmt, ESLint 10, Vitest 4, React Testing Library |
| Authentication | Firebase Authentication: Email/Password, Google Sign-In, reset password |
| API | FastAPI, Uvicorn, Pydantic v2, pydantic-settings |
| Persistence | Firestore Native mode; in-memory repositories for tests/local mode |
| Object storage | Private Google Cloud Storage with short-lived signed upload URLs |
| Async orchestration | Cloud Tasks with OIDC-protected internal endpoints |
| Isolated execution | Docker locally; Cloud Run Jobs in production |
| Test generation | Project-owned CoverUp, LiteLLM/Vertex AI Gemini, SlipCover and coverage.py |
| Prompt optimization | DSPy 3.2.1 and GEPA 0.0.27 |
| Hosting | Firebase Hosting with `/api/**` rewrite to Cloud Run |
| CI/CD | GitHub Actions, Workload Identity Federation, Artifact Registry |
| Runtime versions | Node >=22.12; API image Python 3.11; CoverUp/GEPA images Python 3.12 |

## Architecture

```text
Browser
  -> Firebase Hosting
     -> React SPA
     -> /api/** rewrite -> FastAPI Cloud Run service
                          -> Firebase token verification
                          -> Firestore metadata/state
                          -> private GCS source/artifacts
                          -> Cloud Tasks
                             -> OIDC internal worker endpoint
                                -> GEPA Cloud Run Job (candidate zero/optimization/comparison)
                                   -> Vertex AI Gemini
                                   -> pytest + SlipCover/coverage.py
                                   -> result manifest/artifacts in GCS
```

FastAPI không chạy source của người dùng trực tiếp trong API container. Production phải fail closed
nếu isolated runner chưa được cấu hình.

### Public API groups

Tất cả public business endpoints nằm dưới `/api/v1` và yêu cầu Firebase bearer token, trừ health:

| Nhóm | Endpoints chính |
| --- | --- |
| Upload | `POST /uploads`, `POST /uploads/{id}/complete` |
| Project | `GET/POST /projects`, `GET /projects/samples`, `PATCH /projects/{id}/settings` |
| Analysis | `POST /projects/{id}/analyze`, `GET /projects/{id}/functions`, function source endpoint |
| Experiment | `GET/POST /experiments`, `GET/DELETE /experiments/{id}` |
| Baseline | `POST /experiments/{id}/runs`, run polling và authenticated artifact download |
| Optimization | `POST /experiments/{id}/optimize`, optimization polling/artifacts |
| Comparison | `POST /experiments/{id}/compare`, comparison polling/artifacts |
| Prompt version | owner-scoped list/detail và `POST .../{id}/approve|reject` |

Các `/internal/v1/**` endpoints chỉ dành cho Cloud Tasks và phải xác minh OIDC audience/service
account; frontend không được gọi trực tiếp.

## Chức năng đã implement

### Authentication

- Register bằng email/password và display name.
- Login, logout, reset-password email và Google Sign-In.
- Protected routes và tự refresh Firebase ID token.
- API ownership checks; token không được lưu thủ công vào local/session storage.

### Projects và analysis

- Tạo/list/detail/delete project.
- Signed ZIP upload trực tiếp từ browser vào private GCS.
- Lưu runtime, dependency, test, coverage và security settings.
- Cloud Tasks chạy AST analysis bất đồng bộ.
- Phát hiện function, method, async function, qualified name, source range, LOC, statements và
  branch candidates.
- Xem source chính xác của function và chạy re-analysis.
- Catalog read-only cho `isort`, `mlxtend`, `typesystem`; chọn sample không tạo Project/Function
  documents dư thừa trong Firestore.

### Experiment configuration

- Chọn một hoặc nhiều project; backend không đặt giới hạn cứng 50 target.
- Sampling: random, nhiều branch nhất, nhiều statement nhất hoặc manual.
- `random_seed` và tỷ lệ train/validation/test do người dùng chọn, tổng phải bằng 100 và test split
  phải khác rỗng.
- Manual split được validate để target không xuất hiện ở nhiều split.
- Dropdown Gemini cho `COVERUP_MODEL` và `OPTIMIZE_MODEL`; model chọn trong UI được lưu trong
  experiment settings và truyền xuống runner.
- Cấu hình thật: max attempts, repeat tests, concurrency, rate limit, pytest args, max metric calls,
  evaluation replicates và reflection temperature.
- Review cấu hình và xóa experiment.

### CoverUp trong GEPA

- Không có baseline job riêng; baseline prompt được GEPA đánh giá như candidate số 0.
- Auto-setup ba sample repo trước khi gọi model:
  - tạo distribution metadata an toàn mà không chạy setup script của repo;
  - kiểm tra import package và dependency bắt buộc;
  - `isort`: metadata + `tomli`, bỏ `_vendored` và `deprecated` theo coverage config;
  - `mlxtend`: kiểm tra NumPy/SciPy/Pandas/scikit-learn/Matplotlib/joblib;
  - `typesystem`: kiểm tra Jinja2 và YAML.
- Target contract dùng chính xác `source_file + qualified_name`, không match rộng theo tên hàm.
- Web runner dùng dataset và prompt tải riêng từ GCS; source lấy từ sample repo trong image.
- Structured attempt trace giữ outcome như `test_error`, `coverage_gain_saved` và
  `max_attempts_exhausted`.
- Pytest exit code 5 là zero-test baseline hợp lệ nếu denominator của mọi target vẫn hợp lệ.
- Không báo branch coverage ảo khi không statement nào được chạy.
- Artifacts gồm prompt, setup report, CoverUp logs, structured trace, coverage và kết quả GEPA.

### DSPy/GEPA optimization

- Train/validation search; locked test split không được dùng để chọn candidate.
- Seed candidate luôn là baseline prompt thật.
- Cache tách theo prompt digest, evaluation digest, split và replicate.
- Workspace tách theo candidate/split; target được xác định bằng source file + qualname.
- Candidate prompt chỉ gồm `initial` và `error`, giữ placeholder bắt buộc.
- Candidate và baseline prompt được lưu riêng; optimization không tự ghi đè production prompt.
- Cloud Tasks chỉ trigger/poll ngắn; GEPA Cloud Run Job có timeout tối đa 86400 giây.

### Comparison và prompt review

- Paired baseline/candidate evaluation trên cùng locked targets và replicates.
- Strict promotion gate: candidate phải tốt hơn baseline và không fail/timeout/flaky/regress pass rate.
- Nếu GEPA giữ nguyên baseline digest thì skip final comparison không cần thiết.
- Lưu `final_validation.json`, absolute/relative gain và promotion decision.
- Prompt version `in_review`, owner-scoped list/filter/pagination, approve/reject idempotent với
  reviewer/comment/timestamp.

### Frontend screens

- Login/Register, Dashboard, Projects, Project Detail/Analysis, Create Experiment, Experiments,
  Run/Comparison, Review & Approval, Prompt Registry, Datasets, Playground và Settings.
- Projects, experiments, optimization, comparison và prompt review luôn dùng HTTP
  repositories.
- `VITE_DATA_MODE` hiện chỉ quyết định Dashboard dùng mock hay HTTP. Workflow production đang build
  với `VITE_DATA_MODE=demo`, nên production là **hybrid**: Dashboard dùng fixture; các workflow chính
  vẫn gọi API thật.
- Datasets vẫn import fixture trực tiếp. Playground vẫn là UI tĩnh. Đây là mock còn lại cần xử lý.

## Experiment execution contract

Một experiment lưu snapshot bất biến đủ để tái hiện lựa chọn:

- project IDs và runner-safe project names;
- source file, function ID và qualified symbol;
- sampling method, seed và dataset splits;
- CoverUp/GEPA settings và selected models;
- optimization, comparison và prompt-version IDs.

GEPA web workflow dùng prefix riêng `runner-jobs/gepa/<execution-id>/`, upload dataset/prompt nhưng
không upload source ZIP. Không dùng prefix `prompt_optimization_v3`.

## Frontend development

```powershell
cd codebase\frontend
npm ci
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run build
npm run dev
```

Local environment nằm trong `codebase/frontend/.env.local` và không được commit. Các mode:

| Auth | Data | Ý nghĩa |
| --- | --- | --- |
| `demo` | `demo` | Local UI/demo auth; Dashboard fixture |
| `firebase` | `demo` | Firebase auth; Dashboard fixture; core repositories vẫn dùng API |
| `firebase` | `connected` | Firebase auth và Dashboard API |

## Backend development

```powershell
cd codebase
..\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:PYTHONPATH = (Resolve-Path .).Path
..\.venv\Scripts\python.exe -m ruff format --check src tests sandbox
..\.venv\Scripts\python.exe -m ruff check src tests sandbox
..\.venv\Scripts\python.exe -m pytest tests -q
..\.venv\Scripts\python.exe -m uvicorn src.main:app --reload --port 8000
```

Mặc định local dùng auth disabled, memory repositories, local storage và inline dispatch. Xem
`codebase/.env.example` và `codebase/src/config.py` trước khi đổi backend mode.

## CoverUp/GEPA development

```powershell
cd D:\VinAI\P-002
uv sync --frozen --group dev
uv run ruff check src/optimization tests/test_coverage_optimization.py tests/test_dataset_builder.py cloud/run_job.py
uv run python -m py_compile src/coverup/coverup.py src/optimization/gepa.py src/optimization/metrics.py src/optimization/cli.py src/optimization/runner.py src/optimization/prompts.py cloud/run_job.py
uv run pytest -p no:pytest_isolate tests -q
```

Đọc `Agent.md` trước khi sửa optimizer. Các invariant quan trọng gồm locked holdout, strict promotion,
per-target feedback, exact target identity, cache isolation và zero-test denominator validity.

Không tự chạy live Gemini benchmark vì phát sinh chi phí. Unit test pass không chứng minh prompt mới
tốt hơn; benchmark quyết định phải dùng artifacts directory mới và cùng evaluation protocol.

## Docker verification

Chạy từ repository root:

```powershell
docker build --file codebase/Dockerfile --tag promptopt-api:local .
docker build --file cloud/Dockerfile.web --tag promptopt-gepa-runner:local .
```

API container không cần Docker socket. Docker chỉ cần cho local isolated baseline/build verification;
commit/push không yêu cầu Docker vì GitHub Actions tự build image.

## CI/CD

| Workflow | Trigger | Việc thực hiện |
| --- | --- | --- |
| `frontend-ci.yml` | PR/main khi frontend đổi | format, lint, typecheck, test, build, npm audit |
| `frontend-deploy.yml` | merge/push main khi frontend đổi | WIF auth, lấy Firebase web config, build và deploy Hosting |
| `ci.yml` | PR/main khi backend/runner đổi | backend tests, optimizer tests, build API/CoverUp/GEPA images |
| `backend-deploy.yml` | merge/push main khi backend/runner đổi | WIF auth, push 3 images, deploy 2 Jobs và API |

Feature branch chỉ CI; `main` là production. Deployment dùng Workload Identity Federation, không dùng
service-account JSON key.

## Production resources

| Resource | Value |
| --- | --- |
| GCP/Firebase project | `vinaip002` |
| Region | `asia-southeast1` |
| Hosting/API | `https://vinaip002.web.app`, `/api/v1` |
| Cloud Run API | `promptopt-api` |
| CoverUp Job | `promptopt-coverup-runner` |
| GEPA Job | `promptopt-gepa-runner` |
| Artifact Registry | `asia-southeast1-docker.pkg.dev/vinaip002/promptopt` |
| Private bucket | `vinaip002-promptopt-sources` |
| Cloud Tasks queues | `promptopt-analysis`, `promptopt-baseline` |
| Runtime identity | `promptopt-api@vinaip002.iam.gserviceaccount.com` |
| Runner identity | `promptopt-runner@vinaip002.iam.gserviceaccount.com` |

Firebase Hosting rewrite là public, nhưng API business endpoints vẫn yêu cầu Firebase bearer token.
Runner identity chỉ được cấp quyền tối thiểu trên opaque runner exchange objects và Vertex AI.

## Production smoke

Script cần Firebase **ID token**; `gcloud auth login` không tạo Firebase user session.

```powershell
# GEPA smoke on bundled isort
.\codebase\scripts\smoke_production.ps1

# GEPA (candidate zero is baseline) -> optional locked comparison/review
.\codebase\scripts\smoke_production.ps1 -FullPipeline -ReviewDecision approve
```

Sanitized output được ghi vào ignored `codebase/.smoke-results/`. Không commit raw response hoặc UID.

## Verification snapshot

Tại lần cập nhật 2026-08-08:

- Backend Ruff/pytest: **38 passed**.
- CoverUp/GEPA invariant tests: **51 passed**.
- API image và GEPA runner image dùng cùng sample repo đóng gói sẵn.
- Production vẫn cần deploy commit mới và chạy lại smoke 10-target/ba sample repo.
- Live Gemini benchmark không được chạy tự động trong lần kiểm tra tài liệu.

## Việc tiếp theo

Thứ tự ưu tiên được theo dõi chi tiết trong `Checklist.md`:

1. Deploy exact-target/prompt-contract runner và smoke isort mới; không tái sử dụng experiment cũ.
2. Smoke `typesystem`, rồi `mlxtend`; xác nhận setup report, accepted tests và metrics.
3. Chạy full optimize -> comparison -> review trên production.
4. Hoàn thiện idempotency, cancellation, GEPA checkpoint/resume và immutable checksums.
5. Thêm quota, cost ceiling, artifact retention, structured monitoring và alerts.
6. Xóa mock Dashboard/Datasets/Playground hoặc định nghĩa API/product semantics tương ứng.
7. Thêm staging, browser E2E, tenant-isolation/security tests và rollback drill.
