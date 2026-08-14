# P1 E41/E43 — Live context ablation result

Ngày: 2026-08-14

Model duy nhất: `vertex_ai/gemini-3.5-flash-lite`

Protocol: baseline prompt cố định, 4 target mỗi split, 3 replicate, `repeat_tests=5`,
`max_concurrency=4`. Validation được dùng để chọn policy; split `test` chỉ được đọc sau khi
contract-only thắng validation.

## Validation

| Policy | Aggregate | Statement | Branch | Replicate scores | SD |
|---|---:|---:|---:|---|---:|
| Control, không context | 94,66% | 95,75% | 94,19% | 86,60 / 99,19 / 98,18 | 6,99 điểm |
| E41 contract-only | 98,58% | 99,79% | 98,06% | 98,18 / 99,19 / 98,37 | 0,53 điểm |
| E41 + E43 tests/fixtures | 92,70% | 91,93% | 93,02% | 99,19 / 79,72 / 99,19 | 11,24 điểm |

E41 contract-only so với control: aggregate `+3,92`, statement `+4,03`, branch `+3,88` điểm.

E41 + E43 so với control: aggregate `-1,96` điểm. Nó tạo 11 `test_error` so với 3 của control
và làm `isort::sort_stream` hết ba repair attempts ở một replicate. Vì vậy E43 bị reject.

## Locked holdout

| Policy | Aggregate | Statement | Branch | Replicate scores |
|---|---:|---:|---:|---|
| Control | 67,19% | 75,89% | 63,46% | 63,75 / 90,97 / 46,85 |
| E41 contract-only | 81,17% | 85,11% | 79,49% | 98,33 / 98,33 / 46,85 |

E41 contract-only thắng holdout: aggregate `+13,98`, statement `+9,22`, branch `+16,03` điểm.

Theo target:

- `isort::PathFinder.find`: 66,67% -> 100%.
- `mimesis::BaseField.perform`: giữ 100%.
- `mlxtend::StackingClassifier.fit`: 54,06% -> 64,61%; cả hai policy vẫn có một replicate rơi 0.
- `typesystem::Object.__init__`: giữ 100%.

## Kiểm tra protocol

- Control: 0 target-context marker.
- Contract-only: 12/12 initial prompt có `[TARGET CONTRACT]`, 0 existing-test marker.
- Contract + tests: 12/12 có contract; 6/12 có test/fixture section do chỉ hai repo tìm được snippet liên quan.
- Một contract-only run ban đầu tại `e41_contract_only_context6000_r3` bị loại bỏ vì runner chưa
  forward cờ opt-in xuống CoverUp. Wiring đã được sửa, cache tăng lên schema 17 và kết quả quyết
  định chỉ lấy từ directory `e41_contract_only_context6000_r3_v2`.

## Quyết định

- Promote E41 contract-only thành mặc định của generation pipeline.
- Giữ E43 repository tests/fixtures mặc định tắt, chỉ bật explicit cho ablation.
- Đây là cải thiện của generation context quanh baseline prompt, chưa chứng minh GEPA optimized
  prompt tự nó hơn baseline prompt 13,98 điểm. Benchmark GEPA tiếp theo phải dùng E41 cho cả seed
  baseline và candidate để đo riêng phần gain do search.
