# Kết quả P1 — GEPA control budget 30

- Ngày chạy: 2026-08-14.
- Dataset: `binh/phase1_control_12.jsonl`, gồm 4 train / 4 validation / 4 test.
- Mỗi split có một target từ isort, mimesis, mlxtend và typesystem.
- `COVERUP_MODEL=vertex_ai/gemini-3.5-flash-lite`.
- `OPTIMIZE_MODEL=vertex_ai/gemini-3.5-flash-lite`.
- GEPA seed: 7.
- Reflection minibatch: 3.
- Budget cấu hình: 30 metric calls; GEPA hoàn tất ở 32 do full-validation là khối nguyên tử.
- `repeat_tests=2`, `max_attempts=3`, `max_concurrency=4`.
- Artifact: `binh/phase1_runs/e20_budget30_seed7_mb3`.
- Không đọc, sửa hoặc ghi vào `prompt_optimization_v3`.

## Search và comparison một replicate

GEPA tạo 2 candidate và chọn candidate index 1.

| Split | Baseline | GEPA proposal | Delta |
| --- | ---: | ---: | ---: |
| Train | 92.94% | 93.85% | +0.91 điểm |
| Validation | 53.40% | 96.82% | +43.42 điểm |
| Test holdout | 100.00% | 100.00% | 0.00 điểm |

Validation proposal đạt 100% statement và 95.45% branch. Test holdout đã bão hòa ở 100% cho cả hai prompt, vì vậy promotion gate giữ baseline. Đây là hành vi đúng: proposal phải **strictly better** trên holdout mới được promote.

## Kiểm tra validation hai replicate

Sau search, chỉ sinh thêm replicate 1 cho baseline và proposal; replicate 0 được tái sử dụng từ cache.

| Prompt | Mean validation score | Statement | Branch |
| --- | ---: | ---: | ---: |
| Baseline | 61.64% | 62.28% | 61.36% |
| GEPA proposal | **96.82%** | **100.00%** | **95.45%** |
| Delta | **+35.18 điểm** | +37.72 điểm | +34.09 điểm |

Target-level replicate scores:

| Target | Baseline | GEPA proposal |
| --- | --- | --- |
| `isort/main.py::sort_imports` | 100%, 0% | 100%, 100% |
| `mimesis/providers/internet.py::Internet.url` | 100%, 100% | 100%, 100% |
| `mlxtend/classifier/ensemble_vote.py::EnsembleVoteClassifier.predict` | 100%, 100% | 100%, 100% |
| `typesystem/fields.py::Boolean.validate` | 0%, 94.17% | 94.17%, 94.17% |

Proposal ổn định hơn baseline trên hai target nhiễu của validation. Tuy vậy validation là split GEPA đã dùng để chọn candidate, nên kết quả này chứng minh search signal và khả năng fit validation, chưa chứng minh khả năng khái quát.

## Quyết định

1. Chấp nhận P1 control budget 30 là một kết quả kỹ thuật thành công: GEPA tạo prompt khác baseline và cải thiện validation lặp lại hơn 10–15 điểm.
2. Không promote prompt vì locked test hòa 100%.
3. Chưa chạy budget 120/300: holdout hiện tại không thể đo thêm gain, nên tăng chi phí chưa trả lời được câu hỏi quan trọng.
4. Trước E20 budget 120 hoặc E21 minibatch 3-vs-8, cần tạo calibration dataset lớn hơn nhưng vẫn rẻ, có train ít nhất 8 target và holdout chứa target có headroom thay vì toàn target baseline 100%.
5. Sau khi khóa dataset mới, chạy cùng seed/model và chỉ thay đúng một biến; final comparison cần ít nhất 2 replicate.

## Lệnh control đã chạy

```powershell
python -m src.optimization.cli `
  --sample-repos-dir src/sample_repo `
  --artifacts-dir binh/phase1_runs/e20_budget30_seed7_mb3 `
  --max-concurrency 4 `
  --repeat-tests 2 `
  --max-attempts 3 `
  optimize `
  --dataset binh/phase1_control_12.jsonl `
  --prompt eval/prompt_optimization/prompts/gpt_v2_baseline.json `
  --max-metric-calls 30 `
  --evaluation-replicates 1 `
  --reflection-temperature 0.7 `
  --gepa-seed 7 `
  --reflection-minibatch-size 3
```
