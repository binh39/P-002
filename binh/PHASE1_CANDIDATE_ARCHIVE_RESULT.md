# Kết quả P1 — Candidate test archive

- Ngày chạy: 2026-08-14.
- Split: `validation`.
- Evaluation digest: `8db9cac8b395`.
- Nguồn: hai replicate Gemini 3.5 Flash-Lite của calibration 16 target.
- Không gọi LLM trong bước archive.
- Verification: pytest + coverage, `repeat_tests=5`.

## Kết quả

| Chỉ số | Kết quả |
| --- | ---: |
| Candidate test đầu vào | 26 |
| Test được greedy archive giữ lại | 14 |
| Test loại do coverage trùng lặp | 12 |
| Single-best aggregate | 80.98% |
| Verified archive aggregate | **86.75%** |
| Gain so với single-best | **+5.77 điểm** |
| Statement coverage | 89.62% (259/289) |
| Branch coverage | 85.53% (130/152) |

Phân bổ 14 test được chọn: isort 3, mimesis 4, mlxtend 4 và typesystem 3.

## Kết luận

Candidate archive khai thác được headroom do stochastic generation tạo ra và giảm 46.15% số test module mà không mất coverage. Suite ghép pass năm lần, nên gain không chỉ là phép hợp coverage-unit.

Archive không thay thế prompt metric và không tham gia promotion gate. Nó được khóa theo `split + evaluation_digest`; split `test` bị từ chối mặc định để tránh holdout leakage.

Lệnh tái tạo:

```powershell
python -m src.optimization.cli `
  --sample-repos-dir src/sample_repo `
  --artifacts-dir binh/phase0_runs/calibration16_gemini35_flash_lite_r2 `
  --repeat-tests 5 `
  archive `
  --split validation `
  --output-dir binh/phase1_candidate_archive-new
```
