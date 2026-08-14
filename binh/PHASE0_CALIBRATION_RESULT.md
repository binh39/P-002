# Kết quả calibration Pha 0 — Gemini 3.5 Flash-Lite

- Ngày chạy: 2026-08-14
- Git commit: `daddca9`
- Dataset: `binh/phase0_calibration_16.jsonl`
- Artifacts local: `binh/phase0_runs/calibration16_gemini35_flash_lite_r2/`

## Phạm vi

- 16 target, cân bằng 4 target cho mỗi repo: isort, mimesis, mlxtend và typesystem.
- Hai generation replicates trên cùng locked target set.
- `COVERUP_MODEL=vertex_ai/gemini-3.5-flash-lite`.
- `OPTIMIZE_MODEL=vertex_ai/gemini-3.5-flash-lite` nhưng không được gọi trong Pha 0.
- `max_concurrency=4`.
- `repeat_tests=2`.
- Baseline prompt digest: `d8123dc403839c22`.
- Không chạy GEPA optimization và không chạy full dataset hàng trăm target.

## Readiness trước khi phát sinh batch LLM calls

- 81 test liên quan đến project setup, dataset builder và coverage optimization đều pass.
- Bốn sample repo đều import/setup thành công:
  - isort 6.0.1;
  - mimesis 21.0.0;
  - mlxtend 0.23.4;
  - typesystem 0.4.1.
- 16/16 source file và qualified symbol trong calibration dataset tồn tại.
- Docker daemon không hoạt động, nhưng evaluation local không phụ thuộc Docker.
- Local venv ban đầu thiếu `pytest-repeat`; package đã có trong `requirements.txt` và `pyproject.toml`, nên đã cài `pytest-repeat==0.9.4` vào `.venv` trước khi chạy lại smoke.
- `.env` vẫn chứa `VERTEXAI_PROJECT=vinaip002`, nhưng billing của project này đã tắt. Calibration chỉ override trong process sang `vinbuildphase`, là project có billing và Vertex API đang bật. Không sửa `.env` và không thay đổi tài nguyên cloud.
- Smoke cuối bằng đúng Flash-Lite đạt 100% statement coverage trên `isort/wrap_modes.py::_wrap_mode`.

## Kết quả aggregate

| Run | Aggregate | Statement | Branch | Thời gian |
| --- | ---: | ---: | ---: | ---: |
| Replicate 0 | 80.98% | 79.58% | 81.58% | 161.5 giây |
| Replicate 1 | 72.11% | 76.12% | 70.39% | 169.4 giây |
| Trung bình | **76.55%** | **77.85%** | **75.99%** | 340.6 giây tổng wall time |

Chênh lệch aggregate giữa hai replicate là **8.87 điểm phần trăm**. Đây là mức nhiễu lớn hơn nhiều so với gain `69% -> 71%` đang được quan sát.

## Kết quả theo repo

| Repo | Replicate 0 | Replicate 1 | Nhận xét |
| --- | ---: | ---: | --- |
| isort | 62.71% | 19.31% | Rất không ổn định do hai target đảo kết quả |
| mimesis | 97.31% | 97.31% | Ổn định trên sample hiện tại |
| mlxtend | 94.12% | 98.25% | Ổn định tương đối, còn một ít branch headroom |
| typesystem | 75.74% | 75.74% | Ổn định nhưng có một target luôn 0 |

## Target không ổn định

| Target | Replicate 0 | Replicate 1 | Delta tuyệt đối |
| --- | ---: | ---: | ---: |
| `isort/main.py::sort_imports` | 0.00% | 100.00% | 100.00 điểm |
| `isort/wrap.py::line` | 89.13% | 0.00% | 89.13 điểm |
| `mlxtend/frequent_patterns/apriori.py::apriori` | 92.08% | 97.67% | 5.59 điểm |

13/16 target có kết quả giống nhau giữa hai replicate. Hai target isort lớn làm aggregate thay đổi mạnh vì micro-average được trọng số theo số executable units.

## Target luôn 0 và không có generation attempt

- `isort/deprecated/finders.py::KnownPatternFinder.__init__`.
- `typesystem/fields.py::Boolean.validate`.

Cả hai target có denominator hợp lệ nhưng không có attempt trace trong cả hai replicate. Không nên kết luận model thất bại trên hai target này. Cần kiểm tra target-to-segment discovery/filtering hoặc thay chúng khỏi calibration set trước benchmark tiếp theo.

## Repair behavior

| Outcome | Replicate 0 | Replicate 1 |
| --- | ---: | ---: |
| `coverage_gain_saved` | 13 | 13 |
| `test_error` cần repair | 9 | 14 |
| `max_attempts_exhausted` | 1 | 1 |

Số `test_error` lớn cho thấy component `error` và context dùng cho repair là nguồn cải thiện quan trọng. Có ít nhất 51 generation/repair attempts trong trace; provider request thực tế có thể cao hơn nếu model gọi `get_info`.

## Oracle union sơ bộ

Oracle được tính bằng hợp các executed statement và branch arc của hai replicate trên từng target, với denominator cố định:

- Oracle aggregate: **86.75%**.
- Oracle statement: **89.62%**.
- Oracle branch: **85.53%**.
- 259/289 statements.
- 130/152 branch arcs.

Khoảng cách:

- Oracle cao hơn mean baseline khoảng **10.21 điểm**.
- Oracle cao hơn replicate tốt nhất khoảng **5.77 điểm**.

Đây mới là oracle trên coverage unit, chưa phải một test suite đã được ghép và chạy chung. Cần chạy combined-suite verification để loại test xung đột, pollution và flaky behavior trước khi xem 86.75% là trần khả thi thật.

## Kết luận

1. Không cần và chưa nên chạy Pha 0 trên hàng trăm target.
2. Gain 2 điểm chưa đủ đáng tin nếu chỉ dựa trên một baseline và một optimized run; calibration này có aggregate variance 8.87 điểm.
3. Headroom tồn tại: các test từ hai replicate đã cùng nhau chạm oracle 86.75%.
4. Candidate test archive/portfolio có tín hiệu mạnh hơn việc chỉ giữ một generation hoặc một global prompt.
5. isort là nguồn nhiễu chính trong sample này; cần paired repeated evaluation và target-level reporting.
6. Hai target không tạo attempt phải được chẩn đoán trước khi mở rộng benchmark.

## Bước tiếp theo tiết kiệm chi phí

- [ ] Chẩn đoán target-to-segment discovery cho hai target không có attempt; không gọi LLM để kiểm tra bước này.
- [ ] Chạy replicate thứ ba chỉ cho ba target không ổn định và hai target thay thế, không chạy lại toàn bộ 16 target.
- [ ] Ghép các successful generated tests hiện có và chạy combined-suite coverage để xác nhận oracle thực tế; bước này không cần gọi LLM.
- [ ] Tạo report tự động cho per-replicate, paired delta, repo aggregate và oracle union.
- [ ] Sau khi phép đo ổn định, thử một thay đổi duy nhất có ưu tiên cao: branch/path context hoặc candidate test archive.
- [ ] Chỉ mở rộng lên 50–100 target khi phương pháp thắng ổn định trên calibration set.

## Lưu ý cấu hình trước lần chạy sau

Lệnh local sẽ tiếp tục fail với `BILLING_DISABLED` nếu đọc trực tiếp `VERTEXAI_PROJECT=vinaip002` từ `.env`. Cần xác nhận project đích rồi cập nhật cấu hình hoặc tiếp tục override process. Không nên tự động chuyển project production chỉ dựa trên calibration local.
