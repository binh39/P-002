# Kết quả P1 — E30 structured failure taxonomy live control

- Ngày chạy: 2026-08-14.
- Artifact: `binh/phase1_runs/e30_structured_budget30_seed7_mb3`.
- Dataset: `binh/phase1_ablation_16_v2.jsonl`, split 8 train / 4 validation / 4 test.
- `COVERUP_MODEL=vertex_ai/gemini-3.5-flash-lite`.
- `OPTIMIZE_MODEL=vertex_ai/gemini-3.5-flash-lite`.
- GEPA seed 7, reflection minibatch 3, temperature 0.7.
- Budget cấu hình và thực tế: 30 metric calls.
- `repeat_tests=2`, `max_attempts=3`, `max_concurrency=4`.
- Biến chủ đích thay đổi so với E21 là reflection evidence schema 3 có structured failure taxonomy.
- Không đọc, sửa hoặc ghi vào `prompt_optimization_v3`.

## Xác nhận integration

Live run tạo ba reflection trace, tất cả có `schema_version=3`. Payload gửi tới reflection model thực sự chứa `failure_stage`, `failure_type`, `actionable_frame` và root failure khi repair exhausted.

Sau khi deduplicate cùng target/replicate/attempt, reflection evidence có 12 failure event:

| Stage | Số event |
| --- | ---: |
| Coverage | 6 |
| Execution | 3 |
| Assertion | 2 |
| Repair | 1 |

Sáu event có actionable frame trỏ vào generated test hoặc repository code. Như vậy E30 đã hoạt động end-to-end, không chỉ trong unit test.

## Search result

GEPA chấm ba program gồm baseline và hai candidate full-validation:

| Program | Validation score |
| --- | ---: |
| Baseline `d8123dc…` | **64,74%** |
| Candidate `c0f85bd4…` | 12,63% |
| Candidate `88da8067…` | 38,20% |

Best index là 0, tức baseline. GEPA giữ `gepa_optimized.json` bằng baseline và bỏ qua candidate holdout đúng invariant.

So sánh baseline với candidate E30 tốt nhất:

| Validation metric | Baseline | Candidate | Delta |
| --- | ---: | ---: | ---: |
| Aggregate | 64,74% | 38,20% | **-26,54 điểm** |
| Statement | 58,65% | 36,84% | -21,80 điểm |
| Branch | 67,35% | 38,78% | -28,57 điểm |

Candidate làm `typesystem::String.validate` giảm từ 97,67% xuống 0%; gain nhỏ của `mlxtend::valid_input_check` không bù được regression này.

## Repair outcome

| Full validation batch | Test-error events | Exhausted targets |
| --- | ---: | ---: |
| E30 baseline | 5 | 1/4 |
| E30 best candidate | 8 | 2/4 |
| E21 best candidate | 7 | 2/4 |

Structured taxonomy giúp reflection gọi đúng tên các failure family trong strategy playbook, nhưng ở control một seed này chưa giảm số lỗi hoặc repair exhaustion. Candidate E30 gần bằng E21 candidate về score (`38,20%` so với `38,46%`) và có thêm một test-error event.

## Holdout và quyết định

Locked test chỉ sinh baseline reference, đạt 56,84%. Candidate không qua validation nên không được chấm holdout. Không có prompt mới được promote.

Kết luận:

1. Chấp nhận E30 là integration thành công: schema 3 hoạt động thật và giữ nguyên safety gate.
2. Reject giả thuyết “taxonomy một mình sẽ tăng coverage/repair success” trên control hiện tại.
3. Không chạy thêm seed hoặc budget lớn cho đúng cấu hình E30 này.
4. Bước có expected value cao hơn là E41/E43: đưa exact API signature và existing-test/fixture usage vào context, vì taxonomy chỉ mô tả lỗi nhưng chưa cung cấp thông tin để sửa API mismatch.
5. Giữ E40 sau E41/E43; exact branch context chỉ hữu ích khi generated test đã collection/execution thành công.
