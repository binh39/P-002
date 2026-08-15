# P1 — E24 reflection temperature ablation

Ngày: 2026-08-15

## Mục tiêu

Đo ảnh hưởng của reflection temperature tới candidate diversity, validation coverage, variance và
prompt length mà không thay generation model, dataset, seed, budget hoặc minibatch.

## Protocol

- Temperatures: 0,2 / 0,5 / 0,7 / 1,0.
- Seed 7, requested budget 30, reflection minibatch 3.
- Generation và reflection: `vertex_ai/gemini-3.5-flash-lite`.
- Dataset: 8 train / 4 validation / 4 locked test targets.
- Mỗi temperature chạy `search-only`; holdout không được dùng trong search/rerank.
- Mỗi finalist pool được rerank riêng trên 3 validation replicate.
- Temperature có winner mean cao nhất mới được mở paired 3-replicate holdout.

## Search result

| Temperature | Metric calls | Finalists incl. baseline | Best single validation | Prompt chars |
|---:|---:|---:|---:|---:|
| 0,2 | 32 | 2 | 99,19% | 3.584 |
| 0,5 | 36 | 3 | 98,18% | 3.884 |
| 0,7 | 32 | 2 | 95,36% | 4.231 |
| 1,0 | 34 | 1 | 77,90% (baseline) | 943 |

Temperature 0,5 tạo nhiều finalist nhất. Temperature 1,0 không tạo proposal sống qua selection.

## Repeated validation rerank

| Temperature | Winner | Replicate scores | Mean | Population SD |
|---:|---|---|---:|---:|
| 0,2 | `b13c9b82c8e1babb` | 99,19 / 95,36 / 98,80 | 97,78% | 1,72 điểm |
| 0,5 | `c434c53be569db2a` | 97,56 / 86,79 / 99,19 | 94,51% | 5,50 điểm |
| 0,7 | `d52af1a676ec8d78` | 95,36 / 99,19 / 97,99 | 97,51% | 1,60 điểm |
| 1,0 | baseline | 77,90 / 97,56 / 98,18 | 91,21% | 9,42 điểm |

Temperature 0,2 thắng 0,7 chỉ 0,27 điểm nhưng prompt ngắn hơn 647 ký tự. Candidate 0,2 vẫn thắng
baseline validation sau E28 penalty 0,02/1.000 ký tự, nên được chọn làm winner trước khi mở holdout.

## Locked holdout

| Prompt | Mean (3 replicate) |
|---|---:|
| Baseline | 71,97% |
| Temperature-0,2 winner | 44,05% |
| Delta | -27,92 điểm |

Theo target:

- `isort::PathFinder.find`: 66,67% -> 33,33%.
- `mimesis::BaseField.perform`: giữ 100%.
- `mlxtend::StackingClassifier.fit`: 62,81% -> 25,86%.
- `typesystem::Object.__init__`: giữ 100%.

`promoted=false`; production prompt tiếp tục là baseline.

## Kết luận

Temperature thấp hơn tạo proposal ngắn và validation mạnh hơn, nhưng không cải thiện khả năng
generalize. Chênh lệch 0,27 điểm giữa 0,2 và 0,7 nhỏ hơn rất nhiều variance và không dự đoán được
holdout. Temperature tuning trên validation 4 target không giải quyết bottleneck chính.

Không chạy thêm temperature hoặc tăng budget trên split hiện tại. Bước tiếp theo cần tăng độ đại
diện của validation (tối thiểu 8–12 target, stratified theo repo/branch difficulty) trước E25/E27;
nếu không, optimizer tiếp tục chọn prompt overfit dù rerank và safety gate hoạt động đúng.

## Implementation và verification

- Reflection temperature được lưu trong optimizer config và optimization run digest schema 15.
- Bốn search dùng log namespace riêng; temperature 0,2/0,5/1,0 đều chạy search-only.
- Chỉ winner 0,2 được mở holdout; các temperature còn lại không được đánh giá test.
- Full repository suite: 114 passed.
- Ruff, py_compile và `git diff --check`: pass.
