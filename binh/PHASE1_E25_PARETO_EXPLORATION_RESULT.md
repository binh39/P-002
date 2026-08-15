# P1 — E25 Pareto exploration

Ngày: 2026-08-15

## Mục tiêu

Đo ảnh hưởng của parent selector tới candidate diversity và khả năng tạo một global prompt tốt hơn
baseline. Thử tỷ lệ chọn aggregate current-best/Pareto `70/30`, `50/50` và pure Pareto.

## Protocol

- Dataset: `binh/phase1_stratified_24.jsonl`, 8 train / 12 validation / 4 test mới.
- Test split tiếp tục khóa và không được gọi.
- Generation/reflection: `vertex_ai/gemini-3.5-flash-lite`.
- Seed 7, reflection minibatch 3, temperature 0,7, requested budget 60.
- E41 target contract bật; E43 repository tests/fixtures tắt.
- Mỗi selector chạy `search-only` trong artifact/cache namespace riêng.
- Baseline reference cache được dùng chung; proposal cache và GEPA state không dùng chung.
- Pool cuối được deduplicate rồi rerank trên 3 validation replicate.
- E28 gate: penalty 0,02/1.000 ký tự vượt baseline, hard cap 4.000 ký tự.

## Search result

| Current-best probability | Calls | Finalists | Best single | Pareto-oracle | Parent của proposal |
|---:|---:|---:|---:|---:|---|
| 0,7 | 60 | 3 | baseline 56,73% | 65,50% | baseline, baseline |
| 0,5 | 60 | 3 | baseline 56,73% | 73,42% | baseline, baseline |
| 0,0 | 66 | 3 | baseline 56,73% | **78,88%** | baseline, proposal 1 |

Pure Pareto vượt requested budget vì GEPA hoàn tất một atomic minibatch/full evaluation. Nó là cấu
hình duy nhất tiếp tục mutate từ non-baseline parent và tạo Pareto-oracle cao nhất. Tuy nhiên không
selector nào tạo global prompt thắng baseline trong single validation.

Ba program có 5 prompt unique: baseline và 4 proposal. Một proposal xuất hiện ở cả ba run nhưng
single score dao động 33,03–43,59%, tiếp tục cho thấy một sample không đủ để xếp hạng.

## Pooled repeated rerank

| Rank | Digest | Nguồn | Replicate scores | Mean | SD | Chars | Selection score |
|---:|---|---|---|---:|---:|---:|---:|
| 1 | `d8123dc403839c22` | baseline | 56,73 / 49,42 / 77,66 | **61,27%** | 11,96 điểm | 943 | **61,27%** |
| 2 | `cc77e6b43adcbdee` | pure Pareto | 40,43 / 54,80 / 60,51 | 51,91% | 8,45 điểm | 3.674 | 46,45% |
| 3 | `60e345515e31d517` | 50/50 | 32,89 / 62,58 / 36,37 | 43,95% | 13,25 điểm | 3.244 | 39,35% |
| 4 | `38e9aea1f8872c09` | shared | 43,59 / 35,96 / 39,44 | 39,66% | 3,12 điểm | 3.134 | 35,28% |
| 5 | `2cd44ca58511044d` | 70/30 | 27,52 / 40,43 / 38,31 | 35,42% | 5,65 điểm | 3.630 | 30,04% |

Proposal tốt nhất thua baseline 9,36 điểm raw mean và 14,82 điểm sau length penalty. Vì baseline
thắng repeated validation, E25 dừng trước holdout; không có final test generation nào được chạy.

## Tín hiệu specialization

Pure-Pareto winner không yếu trên mọi target. So với baseline mean theo target, nó:

- tăng `PathFinder.find` từ 33,33% lên 66,67%;
- tăng `Payment.credit_card_number` từ 66,67% lên 100%;
- tăng `valid_input_check` từ 0% lên 32,21%;
- nhưng làm `sort_file` giảm từ 80,50% xuống 0%;
- và làm `Number.validate` giảm từ 32,45% xuống 0%.

Vì vậy Pareto đang tạo strategy chuyên biệt nhưng việc ép chúng thành một global prompt làm mất
coverage ở target có denominator lớn.

## Post-hoc target-router upper bound

Chọn prompt có score cao nhất cho từng target trong cùng replicate, chỉ để đo trần và không dùng làm
promotion decision:

| Replicate | Baseline | Target-router oracle |
|---:|---:|---:|
| 0 | 56,73% | 79,40% |
| 1 | 49,42% | 93,35% |
| 2 | 77,66% | 96,84% |
| Mean | **61,27%** | **89,86%** |

Oracle cao hơn baseline **28,59 điểm**. Đây là post-hoc upper bound nên có selection leakage và chưa
thể deploy trực tiếp, nhưng là tín hiệu mạnh nhất đến nay rằng portfolio/routing có thể vượt mục tiêu
10–15 điểm trong khi global prompt optimization không làm được.

## Quyết định

1. Reject cả ba selector cho mục tiêu tạo một global prompt; baseline tiếp tục được giữ.
2. Không tăng budget 120/300 và chưa chạy E27: chi phí ba search + rerank cao nhưng mọi proposal
   vẫn thua baseline.
3. Giữ `best_candidate_probability` thành cấu hình thật để tái lập experiment.
4. Ưu tiên E67 inference-time Pareto outputs: xây validation-only target router hoặc candidate-test
   portfolio, đánh giá bằng cross-validation trước khi mở test mới.

## Implementation và verification

- CLI mới: `--best-candidate-probability` (`0.7` mặc định, `0` pure Pareto).
- Optimizer config và run digest schema 16 lưu selector probability.
- Multi-program rerank cho phép pool seed/probability khác nhau nhưng vẫn từ chối khác temperature,
  minibatch hoặc budget.
- Rerank artifact ghi lại toàn bộ source optimizer configs.
- Không có thư mục/artifact split `test` trong bốn run E25.
- Full repository suite: 116 passed.
- Ruff trên optimization/tests, compileall và `git diff --check`: pass.
