# P1 — E22 multi-seed GEPA search

Ngày: 2026-08-15

## Mục tiêu

Tăng candidate diversity bằng ba GEPA seed nhưng giữ nguyên dataset, model, budget và reflection
minibatch. Mỗi seed chỉ được dùng train/validation; pool chung được rerank trước khi đúng một winner
đi qua locked holdout.

## Protocol

- Seeds: 7, 17, 37.
- Generation và reflection model: `vertex_ai/gemini-3.5-flash-lite`.
- Dataset: 8 train / 4 validation / 4 locked test targets.
- E41 exact contract context bật; E43 repository tests/fixtures tắt.
- Mỗi seed: requested budget 30, reflection minibatch 3, evaluation replicate 1 trong search.
- Seed 17/37 chạy `--search-only`; không đánh giá holdout.
- Pool dùng E26 top-K rerank, 3 validation replicate, baseline bắt buộc nằm trong pool.
- Chỉ reranked winner được đưa vào final gate 3-replicate holdout.

## Search result

| Seed | Actual metric calls | GEPA finalists | Best validation score |
|---:|---:|---:|---:|
| 7 | 32 | 2 | 95,36% |
| 17 | 34 | 1 (baseline) | 77,90% |
| 37 | 34 | 1 (baseline) | 77,90% |

Reflection tool calls vẫn sinh proposal hợp lệ: shared strategy log có 14 unique proposal digests
(4 từ run seed 7 và 5 cho mỗi run seed 17/37). Tuy nhiên, proposal của seed 17/37 không vượt
minibatch/selection để đi vào GEPA finalist list. Sau khi deduplicate ba program, pool hiệu dụng chỉ
còn hai prompt:

- Baseline `d8123dc403839c22`.
- Proposal seed 7 `d52af1a676ec8d78`.

## Multi-seed validation rerank

| Rank | Prompt | Replicate scores | Mean | Population SD |
|---:|---|---|---:|---:|
| 1 | Seed-7 proposal | 95,36 / 99,19 / 97,99 | 97,51% | 1,60 điểm |
| 2 | Baseline | 77,90 / 97,56 / 98,18 | 91,21% | 9,42 điểm |

Winner không đổi so với E26.

## Locked holdout

| Prompt | Mean (3 replicate) |
|---|---:|
| Baseline | 71,97% |
| Multi-seed winner | 61,98% |
| Delta | -9,99 điểm |

`promoted=false`; production prompt tiếp tục là baseline.

## Kết luận

Thay seed đơn thuần ở budget 30 không tạo thêm finalist diversity. Bottleneck hiện tại không phải
thiếu cơ chế pooling/rerank mà là proposal quality/exploration: reflection sinh prompt mới nhưng
chúng bị loại trước full validation. Không có cơ sở tăng budget 120/300 với cùng proposer.

Bước tiếp theo nên đo E28 prompt length/objective và E24 reflection temperature trên control nhỏ,
hoặc E27 parallel proposals sau khi đánh giá tương thích GEPA. Không mở rộng holdout cho đến khi
validation pool có ít nhất 3 non-baseline finalist thực sự khác nhau.

## Implementation và verification

- `optimize --search-only --program-output ...`: lưu từng seed mà không mở holdout.
- `rerank --optimized-program ...` có thể lặp option để pool nhiều seed.
- CLI kiểm tra budget/minibatch giống nhau ngoài `gepa_seed` và deduplicate theo prompt digest.
- Full repository suite: 113 passed.
- Ruff, py_compile và `git diff --check`: pass.
