# Kết quả P1 — E00/E01 repeated evaluation và E11 failure headroom

- Ngày chạy: 2026-08-14.
- Dataset: `binh/phase1_ablation_16_v2.jsonl`.
- Split đánh giá lặp: validation, 4 target.
- Baseline digest: `d8123dc403839c22`.
- Candidate digest: `9b5fe39795a80b1f`, sinh bởi E21 minibatch 3.
- Cả generation và reflection đều dùng `vertex_ai/gemini-3.5-flash-lite`.
- `repeat_tests=2`, `max_attempts=3`, `max_concurrency=4`.
- Artifact tóm tắt: `binh/phase1_runs/e21_ablation16_v2_budget30_seed7_mb3/repeated_validation_summary.json`.

## E00 — Độ nhiễu baseline

Sáu lần baseline độc lập trên cùng validation v2 đạt:

`69,74%`, `37,74%`, `62,82%`, `91,02%`, `40,60%`, `37,52%`.

| Chỉ số | Kết quả |
| --- | ---: |
| Mean | 56,57% |
| Median | 51,71% |
| Sample standard deviation | **21,78 điểm** |
| Min / max | 37,52% / 91,02% |
| Range | **53,50 điểm** |

Variance này lớn hơn rất nhiều mức cải thiện 2 điểm từng quan sát. Vì vậy một run `69% → 71%` không đủ chứng minh prompt tốt hơn; thậm chí một run tăng 10–15 điểm vẫn cần repeated paired validation.

## E01 — Paired baseline/candidate trên ba replicate

| Replicate | Baseline | Candidate | Paired delta |
| ---: | ---: | ---: | ---: |
| 0 | 91,02% | 38,46% | -52,56 điểm |
| 1 | 40,60% | 40,60% | 0,00 điểm |
| 2 | 37,52% | 40,60% | +3,08 điểm |

| Thống kê | Baseline | Candidate | Delta |
| --- | ---: | ---: | ---: |
| Mean | **56,38%** | 39,89% | **-16,49 điểm** |
| Median | 40,60% | 40,60% | 0,00 điểm |
| Sample standard deviation | 30,04 điểm | 1,24 điểm | 31,27 điểm |

Trên 12 cặp target-replicate, candidate có 2 thắng / 8 hòa / 2 thua. Hai lần thua ở replicate 0 làm mất gần toàn bộ coverage của `mlxtend::valid_input_check` và `typesystem::String.validate`, lớn hơn hai gain nhỏ còn lại.

Candidate không qua validation gate, nên không gọi thêm holdout. Holdout một replicate từ E21 đã cho delta -22,65 điểm và chỉ được giữ như bằng chứng phụ, không dùng để chọn hyperparameter.

## E11 — Failure family và headroom

Trong 24 target-replicate của paired evaluation:

- 14 kết quả tạo và lưu được coverage gain.
- 10 kết quả hết cả 3 lần sửa test (`max_attempts_exhausted`).
- Có 42 episode `test_error` trước khi lưu thành công hoặc hết attempts.
- Nhóm exhausted giữ lại tổng cộng 407 statement và 282 branch chưa cover, tính theo target-replicate.
- Các kết quả đã chạy thành công nhưng còn thiếu chỉ giữ lại 10 statement và 22 branch.

Số lần exhausted theo target:

| Target | Exhausted / 6 lần |
| --- | ---: |
| `isort::sort_file` | 4 |
| `mlxtend::valid_input_check` | 5 |
| `typesystem::String.validate` | 1 |
| `mimesis::Payment.credit_card_number` | 0 |

Phần lớn headroom bị khóa bởi test runtime/assertion/API mismatch và repair không hội tụ, không phải bởi test đã pass nhưng thiếu vài branch. Do đó ưu tiên tiếp theo là:

1. E30: biến traceback dài thành failure taxonomy có cấu trúc và first actionable frame.
2. E43/E41: đưa đúng API signature, existing-test usage và fixture liên quan vào repair context.
3. E40: bổ sung exact branch/path context sau khi test đã chạy được; đây là ưu tiên thứ hai trên calibration hiện tại.

## Quyết định

- Hoàn thành E00 trên calibration validation v2: phép đo hiện tại có variance rất cao.
- Hoàn thành E01 cho candidate E21: reject candidate, không promote và không chạy thêm holdout.
- Không chạy E22 multi-seed hoặc E20 budget 120/300 ở thời điểm này.
- Bước code có expected value cao nhất là E30 structured failure taxonomy; sau đó chạy control cùng dataset để đo giảm `max_attempts_exhausted` trước khi kỳ vọng coverage gain.
