# PromptOpt

PromptOpt là nền tảng tối ưu prompt sinh Python unit test. Hệ thống phân tích source code, tạo dataset theo symbol, dùng CoverUp để sinh test và DSPy/GEPA để đề xuất prompt mới. Candidate chỉ được đưa vào review khi tốt hơn baseline trên locked holdout theo phép so sánh paired.

- Production UI: <https://project-7df9f963-9fe0-4b76-b3d.web.app>
- API docs khi chạy local: <http://127.0.0.1:8000/docs>
- Sơ đồ components/dataflow: [docs/architecture_diagram.md](docs/architecture_diagram.md)
- Evaluation evidence: [eval/results/report.md](eval/results/report.md)

## Luồng chính

1. Đăng nhập và chọn một bundled sample (`isort`, `mimesis`, `mlxtend`, `typesystem`) hoặc upload ZIP Python để phân tích.
2. Chọn function/symbol và tạo train/validation/test split. Test split bị khóa trong lúc GEPA search.
3. Chạy CoverUp + GEPA. Baseline prompt luôn là candidate số 0 và là fallback.
4. So sánh paired baseline/proposal trên locked holdout. Chỉ candidate **strictly better** mới được tạo prompt version `in_review`.
5. Reviewer approve/reject; quyết định và artifact được lưu để audit.

Không có LangGraph agent, vector database hay PostgreSQL trong application hiện tại. Frontend là React/Vite; backend là FastAPI; production dùng Firebase Auth, Firestore, GCS, Cloud Tasks, Cloud Run và Vertex AI.

## Yêu cầu

- Python 3.12
- [uv](https://docs.astral.sh/uv/) để tạo môi trường Python từ `uv.lock`
- Node.js >= 22.12 và npm
- PowerShell cho các lệnh bên dưới (có thể đổi sang cú pháp shell tương đương)
- Google Cloud ADC chỉ cần khi chạy workflow cloud/LLM thật

## Setup local đầy đủ

### 1. Python dependencies

Từ repository root:

```powershell
uv sync --frozen --group dev
uv pip install --python .\.venv\Scripts\python.exe -r app\requirements-dev.txt
```

Lệnh đầu cài CoverUp/GEPA và test tools theo lockfile; lệnh sau bổ sung dependencies của FastAPI/Firebase/Google Cloud backend.

### 2. Backend

```powershell
Copy-Item app\.env.example app\.env
Set-Location app
$env:PYTHONPATH = (Resolve-Path .).Path
..\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Profile mặc định trong `app/.env.example` là local-safe:

- `AUTH_MODE=disabled`: API chấp nhận `Bearer dev-token`;
- metadata dùng repository in-memory;
- upload/artifact nằm dưới `app/data/uploads`;
- project analysis chạy inline;
- không gọi Cloud Run Job hoặc Vertex AI.

Kiểm tra:

```powershell
curl.exe -s http://127.0.0.1:8000/health
```

Output mong đợi:

```json
{"status":"ok","service":"promptopt-api","env":"development"}
```

### 3. Frontend

Mở terminal khác từ repository root:

```powershell
Copy-Item app\frontend\.env.example app\frontend\.env.local
Set-Location app\frontend
npm ci
npm run dev
```

Mở <http://127.0.0.1:5173>. Profile mặc định dùng demo login, gửi `dev-token`, và Vite proxy `/api` tới backend local ở port 8000. Firebase values chỉ cần cho connected/production mode.

## Environment variables

Ba file có phạm vi khác nhau; không gộp chúng thành một `.env`:

| File | Dùng bởi | Nội dung |
| --- | --- | --- |
| `app/.env` | FastAPI | auth, repository/storage backend, Cloud Tasks/Run, giới hạn GEPA |
| `app/frontend/.env.local` | Vite | auth/data mode, API base URL, Firebase web config, dev proxy |
| `.env` ở root | CoverUp/GEPA CLI hoặc deploy script | model IDs và Vertex AI project/location |

Tạo từ các file `.env.example` tương ứng. Không commit token, Firebase ID token, ADC/service-account JSON, signed URL hoặc raw production smoke output.

Các biến backend production bắt buộc:

```dotenv
APP_ENV=production
AUTH_MODE=firebase
REPOSITORY_BACKEND=firestore
STORAGE_BACKEND=gcs
ANALYSIS_DISPATCHER=cloud_tasks
EXPERIMENT_DISPATCHER=cloud_tasks
OPTIMIZATION_EXECUTION_BACKEND=cloud_run_job
GCP_SERVICE_ACCOUNT_EMAIL=...
GCS_BUCKET=...
ANALYSIS_WORKER_URL=...
ANALYSIS_TASK_AUDIENCE=...
EXPERIMENT_WORKER_URL=...
EXPERIMENT_TASK_AUDIENCE=...
```

Model cho mỗi experiment nằm trong request snapshot (`settings.coverup_model`, `settings.optimize_model`). Cloud Run Job nhận chúng thành `COVERUP_MODEL` và `OPTIMIZE_MODEL`; model calls dùng `VERTEXAI_PROJECT`, không dùng project triển khai API để tính billing/quota.

## Sample API queries

Các lệnh sau giả định backend local đang chạy. Trong production, thay base URL và dùng Firebase ID token thật.

```powershell
$api = "http://127.0.0.1:8000/api/v1"
$headers = @{ Authorization = "Bearer dev-token" }

# 1. Liệt kê bundled samples
Invoke-RestMethod "$api/projects/samples" -Headers $headers

# 2. Liệt kê symbols có thể chọn của isort
$functions = Invoke-RestMethod "$api/projects/sample:isort/functions" -Headers $headers
$functions.items | Select-Object -First 5 file, qualified_name, statements, branches

# 3. Tạo experiment 5 targets (dataset split được snapshot ngay khi tạo)
$body = @{
  project_ids = @("sample:isort")
  name = "isort local sample"
  max_targets = 5
  random_seed = 7
  split_percentages = @{ train = 20; validation = 40; test = 40 }
} | ConvertTo-Json -Depth 5
$experiment = Invoke-RestMethod "$api/experiments" -Method Post -Headers $headers -ContentType "application/json" -Body $body
$experiment | Select-Object id, status, optimization_eligible, dataset_splits

# 4. Đọc lại experiment
Invoke-RestMethod "$api/experiments/$($experiment.id)" -Headers $headers
```

Không chạy `POST /experiments/{id}/optimize` bằng local-safe profile: endpoint đó cần GCS, Cloud Tasks, Cloud Run Job, Vertex AI credentials và phát sinh chi phí model. Dùng production profile đã provision hoặc CLI benchmark có chủ đích.

## Kiểm tra

Backend/API:

```powershell
Set-Location app
$env:PYTHONPATH = (Resolve-Path .).Path
..\.venv\Scripts\python.exe -m ruff check backend tests
..\.venv\Scripts\python.exe -m pytest tests -q
```

Frontend:

```powershell
Set-Location app\frontend
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run build
```

CoverUp/GEPA invariants (từ root):

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\ruff.exe check src\optimization tests\test_coverage_optimization.py
.\.venv\Scripts\python.exe -m py_compile src\coverup\coverup.py src\optimization\gepa.py src\optimization\metrics.py src\optimization\cli.py src\optimization\runner.py src\optimization\prompts.py src\optimization\subprocesses.py
git diff --check
```

Unit/integration tests không chứng minh prompt mới thắng benchmark. Quyết định promotion phải dùng artifact directory mới, cùng model/config/replicate protocol và locked holdout.

## Repository map

```text
app/frontend/       React 19 + TypeScript + Vite UI
app/backend/        FastAPI API, services, repositories và dispatchers
app/infra/          GCP runtime/provisioning configuration
cloud/run_job.py    Cloud Run Job wrapper cho GEPA
src/coverup/        Engine sinh/repair Python tests
src/optimization/   Dataset evaluation, DSPy/GEPA search, cache, promotion gate
src/sample_repo/    Bundled snapshots: isort/mimesis/mlxtend/typesystem
tests/              CoverUp/GEPA invariant tests
app/tests/          Backend/API tests
eval/results/       Evaluation evidence và output đã sanitize
```

Xem [app/Readme.md](app/Readme.md) cho handoff production và [AGENTS.md](AGENTS.md) trước khi sửa optimizer.
