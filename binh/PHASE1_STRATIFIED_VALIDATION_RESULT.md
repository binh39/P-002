# P1 — Mở rộng validation có phân tầng

Ngày: 2026-08-15

## Lý do thay dataset

Dataset `phase1_ablation_16_v2.jsonl` chỉ có 4 validation target. Bốn target test của dataset đó đã
được mở trong nhiều ablation E21–E24 và kết quả đã ảnh hưởng quyết định tiếp theo, vì vậy chúng
không còn là holdout độc lập về mặt thống kê.

Dataset mới `binh/phase1_stratified_24.jsonl` có:

- 8 train target: giữ nguyên 2 target/repo từ dataset v2.
- 12 validation target: 3 target/repo, gồm validation cũ, test cũ đã bị mở và một target bổ sung.
- 4 test target mới: 1 target/repo, chưa được gọi trong calibration này.
- Không trùng identity giữa các split; tất cả source file và qualified symbol tồn tại.

Validation bổ sung được chọn để không chỉ giữ các hàm lớn: mỗi repo có thêm một target thuộc mức
branch thấp hoặc trung bình. Bốn test mới là `isort::section_key`,
`mimesis::SchemaBuilder._resolve_value`, `mlxtend::EnsembleVoteClassifier.fit` và
`typesystem::from_json_schema`.

## Protocol calibration

- Chỉ chạy split `validation`; test mới tiếp tục khóa.
- Prompt baseline digest: `d8123dc403839c22`.
- Model: `vertex_ai/gemini-3.5-flash-lite`.
- E41 target-contract context bật; E43 repository test context tắt.
- 3 independent replicate, `repeat_tests=2`, `max_attempts=3`, `max_concurrency=4`.
- Cả bốn sample repo đều qua import preflight trước khi gọi model.

## Baseline result

| Replicate | Coverage score |
|---:|---:|
| 0 | 63,34% |
| 1 | 68,14% |
| 2 | 74,17% |
| Mean | **68,55%** |

- Statement coverage mean: 71,47%.
- Branch coverage mean: 67,30%.
- Sample SD: **5,43 điểm**.
- Range: **10,83 điểm**.

Để so sánh, baseline E24 trên validation 4 target có mean 91,21%, sample SD 11,54 điểm và range
20,28 điểm. Mở rộng lên 12 target giảm hơn một nửa độ lệch aggregate và không còn tạo cảm giác
baseline gần bão hòa.

## Theo repo

| Repo | Replicate scores | Mean | Sample SD |
|---|---|---:|---:|
| isort | 43,08 / 45,47 / 56,12 | 48,22% | 6,94 điểm |
| mimesis | 100 / 100 / 100 | 100% | 0 điểm |
| mlxtend | 77,59 / 92,79 / 51,97 | 74,12% | 20,63 điểm |
| typesystem | 45,24 / 44,18 / 96,69 | 62,04% | 30,02 điểm |

Aggregate ổn định hơn nhưng target-level variance vẫn lớn. Các target nhị phân như
`PathFinder.find`, `sort_imports`, `generate_new_combinations_low_memory` và `Number.validate`
vẫn đảo giữa 0% và gần 100%. Vì vậy mọi candidate vẫn phải rerank paired trên ít nhất 3 replicate.

## Failure signal

Trong 36 target-replicate:

- 28 kết thúc bằng `coverage_gain_saved`.
- 8 kết thúc bằng `max_attempts_exhausted`.
- Có 50 episode `test_error` trước khi thành công hoặc hết attempts.

Mimesis đã bão hòa trên ba target; headroom nằm chủ yếu ở isort, mlxtend và typesystem. Dataset
này phù hợp hơn để phát hiện gain 10–15 điểm nhưng không đủ để chấp nhận candidate từ một sample.

## Quyết định

1. Dùng `phase1_stratified_24.jsonl` làm dataset mặc định cho ablation tiếp theo.
2. Không chạy lại các ablation temperature/budget trên dataset 4-validation cũ.
3. Chưa mở 4 test mới. Chỉ winner sau search-only và repeated validation rerank mới được vào final
   paired holdout.
4. Bước tiếp theo là E25 Pareto exploration với cùng model; mỗi variant phải tách run digest và chỉ
   dùng train/validation.

## Verification

- Project preflight: 4/4 passed.
- Dataset contract test: 9 passed.
- Full repository suite: 115 passed.
- Ruff trên `src/optimization` và dataset test, compileall và `git diff --check`: pass.
- Live calibration hoàn tất trong 468,6 giây, không gặp quota/retry loop.
