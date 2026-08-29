# Runbook: GEPA Prompt Optimization

Tài liệu này là ghi chú vận hành ngắn cho các agent/lần làm việc tiếp theo. Đọc file này trước khi sửa pipeline tối ưu prompt.

## Mục tiêu

Tối ưu ba thành phần `initial`, `error` và `missing_coverage` của CoverUp bằng GEPA và chỉ đưa prompt mới vào production khi nó **thực sự tốt hơn baseline trên holdout bị khóa**. Hệ thống phải ưu tiên khả năng khái quát, khả năng tái lập và không làm hỏng baseline đang tốt.

## Các file chính

- `src/optimization/gepa.py`: adapter GEPA, proposer, đánh giá lặp, cache và tối ưu.
- `src/optimization/metrics.py`: tổng hợp coverage và phạt kết quả thiếu/không hợp lệ.
- `src/optimization/cli.py`: CLI, chia dữ liệu, holdout và promotion gate.
- `src/optimization/prompts.py`: `PromptBundle` và chuyển đổi candidate.
- `src/optimization/runner.py`: chạy CoverUp với concurrency/rate limit.
- `tests/test_coverage_optimization.py`: các invariant quan trọng của pipeline.
- `eval/prompt_optimization/README.md`: tài liệu sử dụng chi tiết.

## Invariant không được phá

1. Candidate GEPA phải là prompt thật dưới dạng dict gồm `initial`, `error`, và `missing_coverage`; không tối ưu một meta-prompt rồi rewrite toàn bộ bundle ngoài vòng lặp.
2. `seed_candidate` phải đúng bằng baseline đầu vào. Baseline luôn nằm trong search space và là phương án fallback.
3. Feedback theo example phải là score riêng của symbol đó. Không trả cùng một aggregate score cho mọi example. Trung bình các score theo symbol phải khớp final micro-average coverage.
4. Reflection record phải có target path/symbol, source context được đánh số dòng, lỗi/coverage feedback và score của từng replicate. Nếu thiếu target context, proposer gần như chỉ đoán mò.
5. Mỗi proposal có thể thay đổi `initial`, `error`, `missing_coverage`, hoặc cả ba khi reflection chọn `all`; `all` luôn là lựa chọn hợp lệ dù direct failure evidence chỉ có ở một stage. Update `all` phải hợp lệ nguyên tử cho cả ba component. Không cho prompt phình vô hạn hoặc hard-code tên file, symbol hay số dòng từ tập train.
6. Giữ chính xác các placeholder bắt buộc:
   - `initial`: `{filename}`, `{coverage_targets}`, `{source_excerpt}`
   - `error`: `{error}`
   - `missing_coverage`: `{missing_coverage}`
7. Split `test` bị khóa: GEPA không được nhìn thấy hoặc dùng nó để chọn candidate. Chỉ đánh giá một lần ở promotion gate sau khi search kết thúc. Nếu không có test thì fallback sang validation và phải ghi rõ trong artifact.
8. Chỉ promote proposal khi nó **strictly better** hơn paired generated baseline trên final split. Nếu hòa hoặc kém hơn, `gepa_optimized.json` phải chứa baseline; proposal vẫn được lưu riêng để chẩn đoán.
   Nếu GEPA chọn lại đúng baseline (bundle digest không đổi), bỏ toàn bộ final split evaluation vì không có proposal mới để so sánh; report phải ghi rõ evaluation đã được skip.
9. `--baseline-tests-dir` chỉ là historical reference bổ sung, không được dùng làm promotion gate thay cho paired baseline/proposal.
10. Kết quả CoverUp không hợp lệ hoặc thiếu coverage phải nhận 0 covered units nhưng vẫn giữ denominator tham chiếu của baseline, tránh việc lỗi lại làm score tăng giả.
11. Cache evaluation phải tách theo prompt digest, evaluation digest, split và replicate. Mỗi target sinh test trong workspace tạm cô lập và chạy trọn vòng đời bằng bounded worker pool; chỉ các test được trace bằng `source_file + qualname` mới được gom vào một workspace lưu bền chung của candidate rồi chấm riêng với coverage data, pytest basetemp và cache cô lập. Workspace tạm phải được xóa sau khi gom. Không dùng cache per-example integer-ID của GEPA chung cho train/validation. Evaluation digest phải phản ánh model/config, target identity và source hash. Khi nghi ngờ benchmark cũ, dùng artifacts directory mới.
12. Generation của CoverUp giữ temperature mặc định 0 để ổn định; reflection model có thể dùng temperature 0.7 để tăng độ đa dạng proposal.
13. Provider có thể trả `finish_reason=stop` với `content=null`. CoverUp phải retry/bỏ riêng segment, tuyệt đối không để một response rỗng làm crash toàn batch.
14. Exit code của tiến trình sinh test không được tự động xóa score của các test đã pass coverage.py. Coverage pass là nguồn xác nhận validity; lưu exit code riêng để chẩn đoán.
15. Trước khi gọi GEPA, baseline preflight phải cung cấp coverage/denominator hợp lệ cho mọi train và validation target; final holdout reference cũng phải đầy đủ. Nếu không, dừng sớm và sửa dataset thay vì tối ưu trên signal 0 giả.

## Zero-test baseline preflight

- Pytest exit code `5` (`NO_TESTS_COLLECTED`) is a valid zero-coverage outcome for a fresh CoverUp workspace, not a broken measurement.
- `coverage run --source=...` still creates coverage data for unexecuted package files. Always run `coverage json` for exit codes `0` and `5` so symbol statement/branch denominators remain measurable.
- Pytest exit code `1` (tests failed) still exports `coverage json`: keep the
  symbol denominators, force covered units and score to zero, and retain the
  failure output as GEPA feedback. Collection/internal/usage errors remain
  unmeasurable and invalid.
- A baseline with zero covered units may enter GEPA as long as every target has valid non-zero statement denominators. Candidate failures are then scored as zero against those fixed reference units.
- Evaluation cache schema `14` invalidates older caches that discarded zero-test denominators, omitted structured traces, scored a target with another target's tests, stored generated workspaces outside the artifacts tree, ran CoverUp and coverage with different randomized hash ordering, or used the slower project-wide CoverUp process and redundant final-suite coverage pass.
- When reporting repeated evaluation failures, skip wrapper lines such as `Replicate 0:` and show the first substantive feedback line.

## Cấu hình khuyến nghị

- Dataset mặc định: 50 train / 100 validation / 100 test.
- `--repeat-tests 5`: giảm nhiễu do test execution.
- `--evaluation-replicates 2`: giảm nhiễu do LLM generation khi đánh giá candidate quan trọng.
- `--max-concurrency 10`: trần mặc định cho CoverUp; hạ xuống nếu gặp HTTP 429 hoặc giới hạn quota.
- Budget: `light=120`, `medium=300`, `heavy=600` metric calls.
- Search dùng Pareto selection, hybrid frontier, reflection minibatch tối đa 5 target có coverage dưới 100%, merge candidates và evaluation cache. Target baseline đã đạt 100% không được đưa vào train minibatch; target vừa đạt 100% ở candidate hiện tại cũng không được đưa vào context reflection. Mỗi proposal có tối đa 5 diagnostic experiments cho minibatch. Khi có failure, reflection LM trước tiên phải viết một test chẩn đoán qua `run_test_experiment`; chỉ khi pytest pass và score của chính target tăng, nó mới được rút bài học và gọi `update_prompt_component`. Test chẩn đoán không được chép vào candidate workspace hoặc dùng để chấm GEPA; CoverUp phải sinh test mới từ prompt candidate. Reflection tái dựng đầy đủ `failing test -> error -> repaired test -> outcome`, gồm mọi lời gọi/kết quả `get_info`, và không đưa baseline test vào từng record.

## Lệnh kiểm tra bắt buộc sau khi sửa

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\ruff.exe check src\optimization tests\test_coverage_optimization.py
python -m py_compile src\coverup\coverup.py src\optimization\gepa.py src\optimization\metrics.py src\optimization\cli.py src\optimization\runner.py src\optimization\prompts.py src\optimization\subprocesses.py
git diff --check
```

LangSmith có thể báo `403` khi upload trace trong môi trường hiện tại; nếu test vẫn pass thì đây là cấu hình telemetry ngoài phạm vi optimizer, không phải lỗi test.

## Chạy benchmark

Smoke test rẻ hơn:

```powershell
python -m src.optimization.cli `
  --sample-repos-dir src/sample_repo `
  --artifacts-dir eval/prompt_optimization_smoke `
  --max-concurrency 10 `
  --repeat-tests 5 `
  optimize `
  --dataset eval/prompt_optimization/datasets/isort_mlxtend_symbols.jsonl `
  --prompt eval/prompt_optimization/prompts/gpt_v2_baseline.json `
  --auto light `
  --evaluation-replicates 1 `
  --reflection-temperature 0.7
```

Benchmark chất lượng cao:

```powershell
python -m src.optimization.cli `
  --sample-repos-dir src/sample_repo `
  --artifacts-dir eval/prompt_optimization_v3 `
  --max-concurrency 10 `
  --repeat-tests 5 `
  optimize `
  --dataset eval/prompt_optimization/datasets/isort_mlxtend_symbols.jsonl `
  --prompt eval/prompt_optimization/prompts/gpt_v2_baseline.json `
  --auto heavy `
  --evaluation-replicates 2 `
  --reflection-temperature 0.7
```

Benchmark gọi Vertex/CoverUp thật, tốn thời gian và chi phí. Không tự chạy full benchmark nếu người dùng chưa yêu cầu hoặc chưa xác nhận phạm vi chi phí. Cần các biến môi trường như `COVERUP_MODEL`, `OPTIMIZE_MODEL` và Vertex ADC; xem `.env.example`, tuyệt đối không ghi secret vào log hay tài liệu.

## Ý nghĩa artifact

- `gepa_proposed.json`: proposal tốt nhất do search sinh ra, kể cả khi không được promote.
- `gepa_optimized.json`: prompt production cuối cùng; có thể chính là baseline nếu proposal không thắng holdout.
- `gepa_direct_logs/`: log trực tiếp của GEPA theo optimization digest.
- `candidates/evaluations/<prompt-digest>/<evaluation-digest>/<split>/`: cache đánh giá; replicate có file riêng.

Luôn đọc leaderboard/report cùng split, replicate count, model/config và digest. Không so hai con số nếu protocol đánh giá khác nhau.

## Bài học từ pipeline cũ

Prompt mới thường tệ hơn baseline vì pipeline cũ tối ưu meta-prompt thay vì prompt thật, cấp context gần như giống nhau cho các example, dùng aggregate score làm local feedback, không neo baseline trong quần thể, cho prompt dài dần và đánh giá một lần trong điều kiện có 429. Các artifact trong `eval/prompt_optimization_batch_v2/` chỉ nên dùng để chẩn đoán lịch sử, không xem là benchmark chuẩn của kiến trúc hiện tại.


### Report coverage sau khi optimize

- `src/optimization/gepa.py`: thêm `build_coverage_report()` (+ helper `_bundle_split_summary`) — gom statement/branch coverage theo từng split (train/validation/test) cho hai prompt (baseline/optimized); optimized được score với reference denominator của baseline, tái sử dụng cache `candidates/evaluations` nên không tốn thêm LLM call sau một run hoàn tất.
- `src/optimization/cli.py`: cuối nhánh final comparison của `tune()` tự động ghi `coverage_report.json` vào artifacts và in bảng tóm tắt qua `_print_coverage_report()`.
- Report không được tạo khi GEPA giữ nguyên baseline (không có prompt thứ hai để so sánh).
- **Lưu ý budget:** GEPA đếm theo per-example; với valset 100, mỗi iteration được chấp nhận tốn ~116 calls (16 minibatch + 100 full eval), cộng seed eval 100. `MaxMetricCallsStopper` chỉ kiểm tra giữa các iteration và full eval là khối nguyên tử nên dễ vượt budget; `--max-metric-calls 150` chỉ cho phép đúng 1 iteration.

## Quy trình Deploy Môi trường Dev Cloud

Khi được yêu cầu deploy hệ thống lên môi trường Dev Cloud (Project `project-7df9f963-9fe0-4b76-b3d`, Region `asia-southeast1`), cần lưu ý hệ thống gồm **2 thành phần độc lập**:

1. **GEPA Optimization Runner Job (`promptopt-gepa-runner-dev`)**:
   - Dùng cho batch prompt optimization pipeline (`src/optimization/`, CoverUp).
   - Script deploy (build Docker image + update Cloud Run Job):
     ```powershell
     powershell -ExecutionPolicy Bypass -File .\cloud\deploy_gepa_job.ps1 -JobName "promptopt-gepa-runner-dev"
     ```
   - Kích hoạt / theo dõi job:
     ```powershell
     .\cloud\run_gepa_job.ps1 -JobName "promptopt-gepa-runner-dev"
     ```

2. **Web Backend API Service (`promptopt-api-dev`)**:
   - Dùng cho Web Backend REST API service (`app/backend/main.py`).
   - Lệnh build & deploy Cloud Run Service:
     ```powershell
     gcloud builds submit --config cloud/cloudbuild.api.yaml --substitutions=_IMAGE=asia-southeast1-docker.pkg.dev/project-7df9f963-9fe0-4b76-b3d/promptopt/api:dev --project project-7df9f963-9fe0-4b76-b3d .
     gcloud run deploy promptopt-api-dev --image asia-southeast1-docker.pkg.dev/project-7df9f963-9fe0-4b76-b3d/promptopt/api:dev --region asia-southeast1 --project project-7df9f963-9fe0-4b76-b3d
     ```
   - Kiểm tra sức khỏe: `https://promptopt-api-dev-861862240028.asia-southeast1.run.app/health`

### Checklist bắt buộc sau khi deploy Web Backend API dev

- Không kết luận deploy thành công chỉ dựa vào `/health`: endpoint này không chạm Firebase Auth, Firestore hay repository thật.
- `app/requirements.txt` phải giữ `google-api-core[grpc]>=2.25.0,<2.35.0` cho đến khi regression upstream được xác nhận đã sửa. `google-api-core==2.35.0` làm `path_template.expand()` percent-encode database đặc biệt `(default)` thành `%28default%29`; mọi Firestore query khi đó trả `400 Invalid database id %28default%29`.
- Trong log Cloud Build, xác nhận resolver cài `google-api-core` phiên bản `<2.35.0`. Dependency dùng range có thể kéo bản mới gây lỗi dù source code không đổi.
- Sau khi deploy, xác nhận revision mới ở trạng thái Ready và nhận 100% traffic; không chỉ xác nhận image đã build/push.
- Chạy đủ ba smoke check trên URL public:
  1. `GET /health` phải trả `200`.
  2. `OPTIONS /api/v1/experiments` với `Origin: http://localhost:5173`, `Access-Control-Request-Method: GET` và header yêu cầu `authorization,content-type` phải trả `200` cùng `Access-Control-Allow-Origin: http://localhost:5173`.
  3. `GET /api/v1/experiments` không token phải trả `401` có cùng CORS header; sau đó kiểm tra endpoint với Firebase ID token thật từ frontend hoặc theo dõi request có xác thực trong Cloud Run logs để chắc chắn repository Firestore không trả `500`.
- Nếu browser báo thiếu `Access-Control-Allow-Origin` nhưng preflight đã pass, không vội sửa danh sách origin. Kiểm tra Cloud Run logs của đúng revision trước: một exception backend không được xử lý có thể tạo response `500` không qua CORS middleware và bị browser trình bày như lỗi CORS.
- Middleware xử lý request phải chuyển unexpected exception thành JSON `INTERNAL_ERROR`, và CORS middleware phải nằm ngoài nó để cả response `500` vẫn có CORS headers. Test `app/tests/test_main.py::test_unexpected_error_response_keeps_cors_headers` phải pass.
- Khi gặp `Invalid database id %28default%29`, kiểm tra phiên bản `google-api-core` và database path trước; database thật vẫn có thể tồn tại đúng dưới tên `(default)`, nên không xóa/tạo lại Firestore database để chữa triệu chứng này.

### Pause/resume khi model bị rate limit

- CoverUp tự yêu cầu pause sau 5 phản hồi HTTP 429 liên tiếp cho cùng model request; reflection request pause sau khi retry của provider đã cạn. Worker phải ghi `pause_signal.json`, dừng hợp tác và upload toàn bộ artifacts với `job_result.json` có `status=paused`; không coi đây là run failed.
- Mỗi target đã hoàn tất được checkpoint nguyên tử trong `runs/.../target_checkpoints/`. Khi resume, không gọi model hoặc chấm lại target đó; chỉ target đang dở/chưa chạy được thực hiện lại.
- GEPA tự resume Pareto/search state từ `gepa_direct_logs/<digest>/gepa_state.bin`. Cloud Run execution mới phải tải artifact prefix cũ về local disk trước khi gọi CLI; không chạy trực tiếp trên gcsfuse.
- Backend giữ cùng logical optimization run, trạng thái `paused`, và endpoint `POST /api/v1/experiments/optimization-runs/{run_id}/resume`. Mỗi lần resume tạo Cloud Run execution/prefix output mới và dùng prefix paused làm `--resume-artifacts-name`, tránh đọc nhầm sentinel cũ.
- UI chỉ hiển thị **Resume optimization** khi trạng thái là `paused`. Dataset, baseline prompt, model và evaluation config phải giữ nguyên; digest mismatch phải dừng thay vì resume sai state.

*Lưu ý:* Lệnh deploy Job `promptopt-gepa-runner-dev` không tự động deploy Service `promptopt-api-dev`. Khi được yêu cầu deploy lại toàn bộ môi trường dev, agent cần triển khai cả hai tài nguyên trên.

## Checklist bàn giao

- Xác nhận toàn bộ invariant phía trên vẫn được test.
- Chạy pytest, Ruff, py_compile và `git diff --check`.
- Dùng artifacts directory mới cho benchmark quyết định.
- Báo rõ đã hay chưa chạy live benchmark; unit test pass không đồng nghĩa proposal đã thắng thực nghiệm.
- Không sửa hoặc xóa các thay đổi không liên quan trong worktree của người dùng.
## Runtime contract for uploaded projects (protocol 13)

- New uploads default to `execution_mode=generic_worker_bundle` and
  `runtime_protocol_version=13`. Each project is prepared in exactly one
  project-only virtual environment; dependency resolution never receives more
  than one project.
- The generic worker image/job is pinned by Python minor and image digest. The
  source archive and venv bundle are content-addressed objects with SHA-256 and,
  when GCS provides it, object-generation checks. Workers verify both before
  extraction. Every subprocess that imports or executes uploaded code (initial
  coverage, diagnostic tests, pytest, SlipCover, coverage, and final-suite
  replay) runs through the restored project's interpreter (`TESTGEN_PYTHON`,
  `VIRTUAL_ENV`, and `PATH`). The outer CoverUp control process may use the
  pinned worker interpreter, but it must not import the uploaded package.
- GEPA/DSPy remains a control plane and must not import or execute uploaded
  source. Its cache/request identity includes the project runtime digest and
  worker identity. Runtime objects are immutable and are not deleted with the
  project record while experiment snapshots may reference them.
- Protocol 12 project-image workers remain dual-read only during migration. They
  require the explicit `RUNTIME_PROJECT_IMAGE_MODE=project_image` flag; do not
  make the image factory a dependency of the generic upload path.
