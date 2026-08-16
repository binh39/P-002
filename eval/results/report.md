# Evaluation evidence

Snapshot gần nhất: **2026-08-16**.

## Kết luận

Repository hiện có cả hai loại evidence:

1. **Live optimizer evidence:** Cloud Run execution `promptopt-gepa-runner-dev-55s8j` hoàn tất thành công và đánh giá paired trên **40 locked-test targets**. Candidate được promote với micro coverage score tăng từ **42.8611% lên 52.5045%**.
2. **Software/API evidence:** 5 local API integration cases với response thực tế, lưu ở [local_api_evidence_2026-08-16.json](local_api_evidence_2026-08-16.json).

Live execution summary có provenance/checksum tại [promptopt-gepa-runner-dev-55s8j-evidence.json](promptopt-gepa-runner-dev-55s8j-evidence.json).
Nội dung JSON của hai artifact nhỏ được snapshot tại [job result](promptopt-gepa-runner-dev-55s8j-job-result.json) và [coverage report](promptopt-gepa-runner-dev-55s8j-coverage-report.json); full `final_validation.json` 2.97 MB được giữ trong private GCS và nhận diện bằng generation/MD5 trong evidence summary.

## Live GEPA evidence: `promptopt-gepa-runner-dev-55s8j`

### Execution provenance

| Field | Actual value |
| --- | --- |
| Cloud project / region | `project-7df9f963-9fe0-4b76-b3d` / `asia-southeast1` |
| Execution UID | `9ac15423-d2b6-4879-bd61-7b5361031dd0` |
| Source commit | `459935e` |
| Start / completion | `2026-08-15T17:16:18Z` / `2026-08-15T19:52:00Z` |
| Duration | `2h35m42.12s` |
| Cloud Run result | `1/1` task succeeded |
| Job manifest | `status=succeeded`, return code `0`, no missing artifacts, protocol `2` |
| GCS run prefix | `runner-jobs/gepa/5cb215d2fbae4ce4a9ec50ac9bac7a5f/artifacts` |

Execution dùng CoverUp `vertex_ai/gemini-3.5-flash-lite`, reflection `vertex_ai/gemini-3.6-flash`, 600 metric-call budget, 605 calls thực tế, 7 candidates, repeat-tests 5 và evaluation replicate 1.

### Locked-test result

| Metric | Baseline | Optimized | Gain |
| --- | ---: | ---: | ---: |
| Micro score | 42.8611% | **52.5045%** | **+9.6435 pp** / +22.50% relative |
| Statement coverage | 44.4265% (825/1857) | **54.9812% (1021/1857)** | **+196 statements** |
| Branch coverage | 42.1902% (497/1178) | **51.4431% (606/1178)** | **+109 branches** |

`final_validation.json` xác nhận `final_split=test`, `used_locked_holdout=true`, `final_evaluation_skipped=false` và `promoted=true`. Baseline digest là `43e38a9d339ce664`; optimized digest là `31da49166afd20d5`. `gepa_proposed.json` và `gepa_optimized.json` có cùng MD5 `z7m2x6COJj5fMkd0k6psmA==`, xác nhận proposal thắng chính là production decision.

### Test-case evidence

Final split gồm **40 cases**: 9 isort, 27 mlxtend và 4 typesystem. Baseline và optimized đều có 40/40 result hợp lệ, không có generator exit code khác 0. Kết quả theo target: 9 tăng, 29 hòa, 2 giảm.

Một số paired outputs thực tế:

| Project / symbol | Baseline | Optimized | Coverage thay đổi |
| --- | ---: | ---: | --- |
| isort `find` | 0.9563 | **1.0000** | branches 15/16 → 16/16 |
| isort `main` | 0.0000 | **0.9269** | statements 0/139 → 136/139; branches 0/84 → 76/84 |
| mlxtend `fpg_step` | 0.9650 | **1.0000** | branches 19/20 → 20/20 |
| mlxtend `signature` | 0.0000 | **0.8782** | statements 0/61 → 56/61; branches 0/36 → 31/36 |
| mlxtend `repel_text_from_axes` | 0.9189 | **1.0000** | statements 26/27 → 27/27; branches 18/20 → 20/20 |
| mlxtend `plot_linear_regression` | 0.0000 | **0.9500** | statements 0/27 → 27/27; branches 0/14 → 13/14 |
| mlxtend `permutation_test` | 0.9582 | **0.9632** | statements 58/60 → 59/60 |

Không che giấu regression: `mlxtend.preprocessing.standardize` giảm từ 0.9102 xuống 0.0 và `ColumnSelector.transform` giảm từ 1.0 xuống 0.9324. Promotion là quyết định theo micro-average locked holdout, không có nghĩa mọi target đều tăng.

### Coverage across splits

| Split | Targets | Baseline score | Optimized score |
| --- | ---: | ---: | ---: |
| Train | 20 | **43.5390%** | 37.7156% |
| Validation | 40 | 61.0822% | **73.3341%** |
| Locked test | 40 | 42.8611% | **52.5045%** |

Candidate giảm trên train nhưng tăng trên validation và locked test. Điều này phải được giữ trong evidence để tránh diễn giải chọn lọc.

## Local API: năm cases đã chạy

| # | Request/scenario | Actual output được kiểm tra | Kết quả |
| --- | --- | --- | --- |
| 1 | `GET /health` | `200`, service `promptopt-api`, env `test` | Pass |
| 2 | `GET /api/v1/projects` không token | `401`, `AUTHENTICATION_REQUIRED` | Pass |
| 3 | `GET /api/v1/projects/samples` với `dev-token` | `200`, đủ 4 sample IDs, tất cả `ready` | Pass |
| 4 | `GET /api/v1/dashboard` với repository rỗng | `200`, owner-scoped KPI = `0`, experiments/coverage rỗng | Pass |
| 5 | Tạo experiment với baseline thiếu placeholder | `422`, `INVALID_BASELINE_PROMPT` | Pass |

Các field nondeterministic như `X-Request-ID` được bỏ khỏi snapshot; status code, error contract và business payload được giữ nguyên.

## Cách tái lập output

Từ repository root:

```powershell
.\.venv\Scripts\python.exe eval\run_local_api_evidence.py
```

Script tạo FastAPI app ở test profile qua ASGI transport, dùng memory repositories và không gọi network, Cloud Run hay Vertex AI.

Năm pytest cases tương ứng cũng đã chạy trực tiếp:

```powershell
Set-Location app
..\.venv\Scripts\python.exe -m pytest `
  tests/test_api/test_health.py::test_health_endpoints `
  tests/test_api/test_projects.py::test_projects_require_authentication `
  tests/test_api/test_projects.py::test_sample_catalog_creates_experiment_without_persisting_projects `
  tests/test_api/test_dashboard.py::test_dashboard_endpoint_returns_owner_scoped_empty_snapshot `
  tests/test_api/test_experiments.py::test_create_experiment_rejects_invalid_custom_baseline `
  -vv
```

Actual runner summary:

```text
collected 5 items
test_health_endpoints                                             PASSED
test_projects_require_authentication                              PASSED
test_sample_catalog_creates_experiment_without_persisting_projects PASSED
test_dashboard_endpoint_returns_owner_scoped_empty_snapshot       PASSED
test_create_experiment_rejects_invalid_custom_baseline             PASSED
5 passed in 16.36s
```

Verification mở rộng cùng ngày:

| Suite/check | Actual result |
| --- | --- |
| Backend/API `pytest app/tests -q` | **44 passed** |
| CoverUp/GEPA/root `pytest tests -q` | **86 passed**, 11 dependency deprecation warnings |
| Frontend Vitest | **15 files, 35 tests passed** |
| Frontend ESLint + TypeScript | Pass |
| Frontend production build | Pass |

Các số trên là software verification; chúng vẫn không thay thế live paired coverage evaluation.

## Audit các production smoke artifact cũ

`app/scripts/` có 4 JSON snapshots ngày 2026-08-06. Chúng không đủ làm “5 successful eval cases”:

| Artifact | Trạng thái thực tế |
| --- | --- |
| `production-smoke-result-20260806-205824.json` | Failed: asyncio/gRPC future attached to a different loop |
| `production-smoke-result-20260806-211233.json` | Failed: Cloud Run Job không publish result manifest |
| `production-smoke-result-20260806-212955.json` | Failed: thiếu quyền `run.operations.get` |
| `production-smoke-result-20260806-213644.json` | Run hoàn tất nhưng coverage score = `0.0` trên 1 target |

Các file này là evidence chẩn đoán lịch sử, không phải benchmark hiện tại và không chứng minh proposal thắng baseline.

## Giới hạn của live evidence

- Final evaluation chỉ có **1 generation replicate**. Run này chứng minh candidate thắng protocol đã chạy, nhưng độ tin cậy thấp hơn benchmark khuyến nghị 2 replicates.
- Có 2/40 per-target regressions dù aggregate được promote; không tuyên bố candidate tốt hơn trên mọi symbol.
- 605 metric calls vượt budget 600 vì stopper chỉ kiểm tra giữa iterations và full evaluation là một khối nguyên tử.
- Artifact trong GCS là nguồn đầy đủ; file evidence trong repository là bản tóm tắt sanitize kèm generation, size và MD5 để truy nguyên.
