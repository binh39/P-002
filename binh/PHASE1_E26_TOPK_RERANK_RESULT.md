# P1 — E26 top-K repeated validation reranking

Ngày: 2026-08-14

## Mục tiêu

Không chọn prompt từ một validation generation nhiễu. Baseline luôn nằm trong finalist pool;
chỉ validation được dùng để rerank, sau đó đúng một winner mới đi qua locked holdout.

## Protocol

- Generation model: `vertex_ai/gemini-3.5-flash-lite`.
- Nguồn candidate: E41 GEPA budget 30, seed 7, reflection minibatch 3.
- Dataset: 8 train / 4 validation / 4 locked test targets.
- Yêu cầu top-K: 5; hiệu dụng: 2 vì GEPA chỉ tạo baseline và một proposal hợp lệ.
- Validation rerank: 3 independent generation replicate; r0 tái sử dụng cache.
- Ranking: mean coverage giảm dần, failure rate tăng dần, variance tăng dần, prompt length tăng dần.
- Final gate: 3 replicate cho cả baseline và winner; dùng cache có sẵn, không chạy lại search.

## Validation leaderboard

| Rank | Prompt | Replicate scores | Mean | Population SD | Failures | Chars |
|---:|---|---|---:|---:|---:|---:|
| 1 | Proposal `d52af1a676ec8d78` | 95,36 / 99,19 / 97,99 | 97,51% | 1,60 điểm | 0% | 4.231 |
| 2 | Baseline `d8123dc403839c22` | 77,90 / 97,56 / 98,18 | 91,21% | 9,42 điểm | 0% | 943 |

Proposal thắng rerank validation `+6,30 điểm` và có variance thấp hơn baseline trong ba sample.

## Locked holdout

| Prompt | Mean (3 replicate) |
|---|---:|
| Baseline | 71,97% |
| Reranked proposal | 61,98% |
| Delta | -9,99 điểm |

`promoted=false`; `gepa_optimized.json` tiếp tục chứa baseline.

## Kết luận

E26 đã sửa đúng vấn đề đánh giá một sample, nhưng chưa thể thay đổi quyết định vì run này chỉ có
một non-baseline proposal. Validation lặp vẫn không dự đoán được generalization sang bốn holdout
target. Không tăng budget 120/300 từ kết quả này.

Bước tiếp theo là E22 multi-seed với budget nhỏ để tạo candidate pool đa dạng, gom candidate của
nhiều seed rồi mới dùng E26 rerank. Chỉ winner sau multi-seed rerank mới được mở một holdout mới.

## Implementation và verification

- `optimize --rerank-top-k K --rerank-replicates N`: opt-in, không tự tăng chi phí workflow cũ.
- `rerank`: tái sử dụng `optimized_program.json` và evaluation cache mà không chạy lại GEPA.
- Artifact: `candidate_rerank.json`, `prompts/gepa_reranked.json`.
- Full repository suite: 110 passed.
- Ruff, py_compile và `git diff --check`: pass.
