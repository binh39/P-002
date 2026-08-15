# P1 — E67 cost-aware sequential portfolio

Ngày: 2026-08-15

## Mục tiêu

Giảm chi phí của candidate-test portfolio E67 mà vẫn giữ gain coverage. Policy phải chạy baseline trước,
chỉ mở stage tiếp theo cho target còn dưới ngưỡng coverage và dừng riêng từng target khi đã đủ tốt.

Thí nghiệm chỉ dùng cache validation E25. Không gọi Gemini và không đọc/chạy holdout `test`.

## Implementation

Command mới `sequential-archive` nhận một danh sách `--stage PROMPT_DIGEST:REPLICATE` có thứ tự cố định.
Sau mỗi stage, policy:

1. cộng các coverage unit của test hợp lệ vào trạng thái target;
2. loại target đã đạt `target_stop_score` khỏi stage sau;
3. content-deduplicate và greedy set-cover toàn bộ test đã thu được;
4. chạy suite hợp nhất 5 lần rồi mới chấp nhận coverage.

Report lưu stage order, target đủ điều kiện ở từng stage, marginal units, target-generation calls và hai cost
baseline: chạy hết stage đã yêu cầu và chạy toàn bộ cohort prompt × replicate. Một target-generation chỉ là
cost proxy; chưa bao gồm retry, token hoặc độ dài response.

Stage order được calibration trên validation:

1. baseline `d8123dc403839c22`, replicate 0;
2. pure-Pareto `cc77e6b43adcbdee`, replicate 0;
3. 50/50 `60e345515e31d517`, replicate 0;
4. shared proposal `38e9aea1f8872c09`, replicate 0;
5. 50/50 `60e345515e31d517`, replicate 1;
6. baseline `d8123dc403839c22`, replicate 1;
7. baseline `d8123dc403839c22`, replicate 2, chỉ cho target khó còn lại.

Các stage proposal không tạo marginal gain trong calibration đã bị loại khỏi schedule. Đây là policy đã tune
trên validation, vì vậy không được tiếp tục sửa sau khi mở holdout.

## Threshold sweep từ cache

| Stop score | Estimated score | Target-generations | Tiết kiệm so với full 180 |
|---:|---:|---:|---:|
| 0,50–0,70 | 91,84% | 22 | 87,78% |
| 0,75 | 92,17% | 27 | 85,00% |
| **0,80** | **96,09%** | **29** | **83,89%** |
| 0,90 | 96,09% | 32 | 82,22% |
| 0,95 | 96,09% | 36 | 80,00% |
| 0,98 | 96,42% | 40 | 77,78% |
| 1,00 | 96,42% | 48 | 73,33% |

Ngưỡng 0,80 là knee point: tăng từ 0,75 lên 0,80 thêm 3,92 điểm estimated coverage với 2 calls; tăng
từ 0,80 lên 0,98 chỉ thêm 0,33 điểm estimated với 11 calls.

## Verified results

| Policy | Calls / full cohort | Verified score | Statements | Branches | Gain vs best single |
|---|---:|---:|---:|---:|---:|
| Full prompt pool, replicate 0+1 | 120 / 120 | 96,32% | 315/319 | 202/212 | +33,74 điểm |
| Sequential replicate 0+1, stop 0,98 | 37 / 120 | 96,32% | 315/319 | 202/212 | +33,74 điểm |
| Sequential + hard-target baseline r2, stop 0,98 | 40 / 180 | **97,26%** | 318/319 | 204/212 | +19,61 điểm |
| **Sequential + hard-target baseline r2, stop 0,80** | **29 / 180** | **96,93%** | **318/319** | **203/212** | **+19,28 điểm** |

Policy 0,80 giữ 13 test, pass toàn bộ project khi chạy chung 5 lần, đưa cả 12 target qua ngưỡng estimated
0,80 và tiết kiệm 83,89% target-generations so với chạy đủ 5 prompt × 3 replicate. So với policy 0,98,
nó bỏ 11 calls và chỉ mất một branch outcome, tương đương 0,33 điểm aggregate.

## Quyết định

1. Chọn `target_stop_score=0.80` làm default calibration candidate.
2. Freeze stage order và threshold ở trên; không tune thêm bằng holdout.
3. Không dùng kết quả để khẳng định prompt GEPA tốt hơn baseline: gain đến từ portfolio test có verification.
4. Bước kế tiếp cần model call thật để chạy đúng một one-shot holdout gate. Chỉ mở khi chấp nhận chi phí và
   cam kết không sửa policy theo kết quả holdout.

## Verification

- Sequential archive 0,80 và 0,98: `verified=true`, `repeat_tests=5`.
- Archive cũ sau refactor vẫn tái tạo đúng score 79,82% trên replicate 0.
- Targeted archive tests: 19 passed.
- Repository suite đúng phạm vi `tests/`: 128 passed.
- Không tạo evaluation/artifact split `test`.
- Raw archive outputs nằm trong ignore pattern `binh/phase1_candidate_archive_e25*/`.
