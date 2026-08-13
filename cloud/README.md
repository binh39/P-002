# Deploy GEPA/CoverUp pipeline to Google Cloud Run Jobs

Chạy lệnh optimization (GEPA + CoverUp) trên Google Cloud và lấy kết quả eval về máy.

## Các file

| File | Vai trò |
|---|---|
| `cloud/inputs/` | Dataset + prompt được copy vào Docker image (vì `.dockerignore` loại `eval/`) |
| `cloud/deploy_gepa_job.ps1` | Build image, tạo bucket + service account, tạo/cập nhật job |
| `cloud/run_gepa_job.ps1` | Chạy job, chờ kết thúc, tải kết quả về máy |
| `cloud/run_job.py` | Wrapper chạy trong container: artifacts ghi ổ local, xong upload lên GCS |
| `Dockerfile` | Python 3.12 + uv, `uv sync --frozen` từ `pyproject.toml` + `uv.lock`; thêm `COPY cloud/inputs /app/inputs` |
| `pyproject.toml` + `uv.lock` | Nguồn cài dependencies cho Docker (và cho `uv sync` local) — cùng version với venv hiện tại |
| `requirements.freeze.txt` | Snapshot tham khảo của venv hiện tại (không còn được Docker dùng) |

## Cách dùng

```powershell
# 1. Deploy (build image + tạo job) — chạy lần đầu
.\cloud\deploy_gepa_job.ps1

# 2. Chạy, chờ, tải kết quả
.\cloud\run_gepa_job.ps1
```

Chạy thử nhỏ trước khi chạy full 450 metric calls (tốn tiền LLM):

```powershell
.\cloud\deploy_gepa_job.ps1 -MetricCalls 20 -Execute
```

## Cấu hình mặc định

- Project deploy mặc định: `project-7df9f963-9fe0-4b76-b3d` (hoặc truyền `-ProjectId`)
- Project gọi model: đọc từ `VERTEXAI_PROJECT` trong `.env` (hoặc truyền `-VertexProjectId`)
- Region: `asia-southeast1` · Job: `p002-gepa` · Bucket: `p002-gepa-artifacts`
- 4 vCPU / 8 GiB, timeout 24h, `--max-retries 0`
- Model: đọc từ `COVERUP_MODEL` / `OPTIMIZE_MODEL` trong `.env`

Có thể ghi đè tất cả bằng tham số, ví dụ:

```powershell
.\cloud\deploy_gepa_job.ps1 -JobName p002-gepa-test -MetricCalls 20 -Memory 4Gi -Cpu 2
.\cloud\run_gepa_job.ps1 -JobName p002-gepa-test -DownloadTo eval/prompt_optimization_v3_test_cloud
```

Dọn dẹp toàn bộ tài nguyên cloud sau khi đã tải kết quả về (xóa artifacts trên GCS, job, và image):

```powershell
.\cloud\run_gepa_job.ps1 -Cleanup
```

`-Cleanup` là tùy chọn chủ động — script không tự xóa gì. Không dùng chung với `-NoWait` hoặc `-SkipDownload`.

## Tắt terminal khi đang chạy

Job chạy hoàn toàn trên Google Cloud — đóng terminal hoặc tắt máy cá nhân **không dừng job**.

Lưu ý: khi quay lại, **đừng chạy lại script không tham số** — nó sẽ tạo execution mới (tốn tiền gấp đôi).
Thay vào đó, attach vào đúng execution đang chạy:

```powershell
# Lúc bắt đầu — có thể đóng terminal ngay sau đó
.\cloud\run_gepa_job.ps1 -NoWait

# Lúc quay lại — chờ + tải kết quả của đúng execution đó
.\cloud\run_gepa_job.ps1 -ExecutionName p002-gepa-jm7jq
```

Muốn xem execution nào đang chạy: `gcloud run jobs executions list --region asia-southeast1`.

Từ bản mới nhất, script đã có lớp bảo vệ: nếu phát hiện một execution đang chạy, nó **từ chối**
tạo execution mới và hướng dẫn dùng `-ExecutionName`. Nếu bạn thực sự muốn chạy song song,
truyền `-NewExecution`.

## Chi phí

- Cloud Run Jobs chỉ tính phí **trong lúc execution chạy** (vCPU-giây + memory-giây + startup cost mỗi task).
  Job đã tạo nhưng không chạy = 0 đồng. Chạy lại script = chạy execution mới = tính phí mới.
- Sau khi kết thúc còn 2 chi phí lưu trữ nhỏ: image trong Artifact Registry và artifacts trong GCS
  (cỡ vài cent/tháng tùy dung lượng). Muốn dừng hẳn, dùng `-Cleanup`.

## Nhiều người dùng (team)

Job, bucket và service account mặc định là **dùng chung** — nhiều người chạy cùng một tên sẽ đè dữ liệu
và "ai deploy sau thì thắng" (kể cả env vars như OPENAI_API_KEY). Mỗi thành viên nên dùng bộ thông số riêng:

```powershell
.\cloud\deploy_gepa_job.ps1 `
  -JobName p002-gepa-duy `
  -ServiceAccountName p002-gepa-duy `
  -ArtifactsName duy/prompt_optimization_v3 `
  -Image gcr.io/vinaip002/p002-gepa-duy

.\cloud\run_gepa_job.ps1 `
  -JobName p002-gepa-duy `
  -ArtifactsName duy/prompt_optimization_v3 `
  -DownloadTo eval/prompt_optimization_v3_duy_cloud
```

Lý do:

- **`-JobName` riêng**: guard "chặn chạy song song" là theo job — job riêng thì không chặn nhau.
- **`-ArtifactsName` có prefix tên**: tránh đụng `generated_tests/`, `runs/`, `candidates/` giữa các người.
- **`-ServiceAccountName` riêng**: script tự tạo SA và phân quyền; env vars (API key) không bị người khác ghi đè.
- **`-Image` riêng**: để `-Cleanup` xóa image không ảnh hưởng người khác.

Lưu ý chung:

- Chi phí Vertex AI + Cloud Run vẫn **gộp chung vào project `vinaip002`**, không tách theo người — nên đặt
  budget alert trên GCP.
- Quota Vertex AI là **dùng chung theo region** — nhiều job lớn chạy đồng thời có thể bị 429.
- Không dùng `-Cleanup` với image/job chung — nó sẽ xóa tài nguyên của người khác. Chỉ cleanup artifacts của mình.

## Kết quả nhận được

Sau khi job chạy xong, script tải toàn bộ `gs://p002-gepa-artifacts/prompt_optimization_v3/` về
`eval/prompt_optimization_v3_cloud/`:

- `optimized_program.json` — chương trình tối ưu (best candidate)
- `prompts/gepa_proposed.json`, `prompts/gepa_optimized.json` — prompt đề xuất / được chọn
- `final_validation.json` — so sánh baseline vs optimized trên split cuối
- `runs/` — log CoverUp + attempt trace từng target
- `candidates/`, `generated_tests/` — cache + test sinh ra
- `gepa_direct_logs/` — log vòng GEPA

## Lưu ý

- **Chi phí**: 450 metric calls = rất nhiều lần evaluate full train (49) + validation (100) — tốn tiền
  Vertex AI thật. Luôn chạy `-MetricCalls 20` trước.
- **Secrets**: các key (`OPENAI_API_KEY`, ...) nếu có trong `.env` sẽ được đưa vào env của job —
  nhìn được qua `gcloud run jobs describe`. Nếu cần an toàn hơn, dùng Secret Manager.
- **Artifacts chạy local rồi upload**: pipeline ghi artifacts lên ổ local của container (tránh lỗi GCS FUSE
  với sqlite coverage), xong upload toàn bộ lên GCS. Mỗi execution bắt đầu với workspace sạch — không còn
  guard "incomplete workspace". Không tự tái dùng cache giữa các lần chạy; muốn so sánh nhiều lần, đổi
  `-ArtifactsName` mỗi lần.
- **Vertex AI auth**: job dùng service account `p002-gepa-sa`, đã gán `roles/aiplatform.user`
  và `roles/serviceusage.serviceUsageConsumer` trên project gọi model — không cần API key khi model là
  `vertex_ai/...`.
- **Chạy lại khi code thay đổi**: chạy lại `deploy_gepa_job.ps1` (build image mới + update job).

## Lệnh xóa Storage
gcloud storage rm -r gs://p002-gepa-artifacts/prompt_optimization_v3

.\cloud\deploy_gepa_job.ps1 -MetricCalls 4500 -Execute

```powershell
# Lúc bắt đầu — có thể đóng terminal ngay sau đó
.\cloud\run_gepa_job.ps1 -NoWait

# Lúc quay lại — chờ + tải kết quả của đúng execution đó
.\cloud\run_gepa_job.ps1 -ExecutionName p002-gepa-d5r6z
```
