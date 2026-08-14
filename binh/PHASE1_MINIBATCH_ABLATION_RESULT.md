# Kết quả P1 — E21 reflection minibatch 3 so với 8

- Ngày chạy: 2026-08-14.
- Dataset chính: `binh/phase1_ablation_16_v2.jsonl`, gồm 8 train / 4 validation / 4 test.
- Mỗi split chứa target của isort, mimesis, mlxtend và typesystem.
- `COVERUP_MODEL=vertex_ai/gemini-3.5-flash-lite`.
- `OPTIMIZE_MODEL=vertex_ai/gemini-3.5-flash-lite`.
- Baseline prompt: `eval/prompt_optimization/prompts/gpt_v2_baseline.json`.
- GEPA seed: 7; reflection temperature: 0.7.
- Budget cấu hình: 30 metric calls.
- `repeat_tests=2`, `max_attempts=3`, `max_concurrency=4`, một generation replicate.
- Biến duy nhất chủ đích thay đổi giữa hai run là reflection minibatch: 3 và 8.
- Không đọc, sửa hoặc ghi vào `prompt_optimization_v3`.

## Chuẩn bị dataset

Dataset thử đầu tiên `binh/phase1_ablation_16.jsonl` có baseline validation 99,19%, nên không còn headroom để đo optimizer. Run này giữ nguyên baseline và không chạy final candidate. Dataset v2 đã chuyển các target bão hòa ra khỏi validation và được kiểm tra setup 16/16 target thành công trước khi chạy.

Baseline probe của v2 trên validation đạt 69,74%, xác nhận split có headroom. Tuy nhiên các lần generation độc lập sau đó dao động lớn, vì vậy probe chỉ dùng để sàng lọc dataset chứ không dùng làm số đối chứng cuối.

## Kết quả minibatch 3

Artifact: `binh/phase1_runs/e21_ablation16_v2_budget30_seed7_mb3`.

GEPA chọn candidate index 1 trong hai program được chấm. Budget kết thúc ở 32 metric calls vì một minibatch/full-validation được xử lý như khối nguyên tử.

| Split | Baseline | Candidate | Delta |
| --- | ---: | ---: | ---: |
| Train | 67,94% | 84,73% | +16,79 điểm |
| Validation | 37,74% | 38,46% | +0,71 điểm |
| Test holdout | 79,23% | 56,57% | **-22,65 điểm** |

Trên holdout, candidate thắng isort `PathFinder.find`, hòa mimesis `BaseField.perform`, tăng nhẹ mlxtend `StackingClassifier.fit`, nhưng làm typesystem `Number.validate` giảm từ 100% xuống 0%. Tổng thể là 2 thắng / 1 hòa / 1 thua theo target, nhưng regression lớn của một target làm micro-average giảm mạnh. Promotion gate đã từ chối candidate đúng như thiết kế.

## Kết quả minibatch 8

Artifact: `binh/phase1_runs/e21_ablation16_v2_budget30_seed7_mb8`.

Baseline validation đạt 62,82%. Candidate được chấm đạt 12,63%, thấp hơn baseline 50,19 điểm, nên GEPA giữ candidate index 0 là baseline và bỏ qua việc sinh/chấm candidate trên holdout. Locked baseline holdout của run này đạt 42,29%.

Run kết thúc ở 40 metric calls dù cấu hình là 30. Với minibatch 8, phần metric budget còn lại không đủ cho cả batch nhưng GEPA vẫn hoàn tất batch nguyên tử. Do đó hai cấu hình có cùng budget khai báo nhưng không có cùng số metric call thực tế: minibatch 3 dùng 32, minibatch 8 dùng 40.

## Nhiễu quan sát được

Cùng baseline prompt, model, dataset và runner nhưng các generation độc lập cho kết quả rất khác nhau:

| Phép đo baseline | Aggregate score |
| --- | ---: |
| Holdout probe trước E21 | 22,26% |
| Minibatch 3 — validation | 37,74% |
| Minibatch 8 — validation | 62,82% |
| Validation probe trước E21 | 69,74% |
| Minibatch 8 — test | 42,29% |
| Minibatch 3 — test | 79,23% |

Các hàng thuộc split khác nhau không được so trực tiếp như cùng một benchmark; bảng này chỉ chứng minh variance generation lớn. Riêng cùng validation v2, baseline probe 69,74%, run minibatch 3 đạt 37,74% và run minibatch 8 đạt 62,82%. Một replicate chưa đủ để tách ảnh hưởng của minibatch khỏi nhiễu sinh test.

## Kết luận E21

1. Minibatch 3 có khả năng tạo proposal cải thiện train, nhưng gain validation chỉ +0,71 điểm và không khái quát sang holdout.
2. Minibatch 8 không thắng baseline ở run này; ưu điểm là fallback an toàn đã hoạt động.
3. Không promote prompt của cả hai run.
4. Chưa thể kết luận minibatch 3 tốt hơn hoặc kém hơn minibatch 8 về mặt thống kê.
5. Không nên chạy budget 120/300 trên phép đo một replicate hiện tại; chi phí tăng nhưng tín hiệu có thể vẫn bị variance lấn át.

## Bước tiếp theo

Ưu tiên E00/E01 trên dataset v2: chạy lại baseline và top candidate theo paired protocol 3–5 replicate, báo cáo mean, median, độ lệch chuẩn và target win/tie/loss. Sau đó mới:

- chạy E22 với seed 7/17/37 nếu gain lặp lại được;
- hoặc chuyển sang E30/E40 nếu lỗi tập trung ở no-gain/branch-path context;
- chỉ tăng budget E20 khi validation có headroom ổn định và candidate thắng qua repeated evaluation.
