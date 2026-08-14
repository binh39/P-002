# Kết quả combined-suite verification Pha 0

- Ngày chạy: 2026-08-14.
- Nguồn: hai replicate trong `calibration16_gemini35_flash_lite_r2`.
- Không gọi LLM; chỉ ghép test đã sinh và chạy pytest + coverage.
- 26 test module được đổi tên theo replicate để tránh module collision.

| Repo | Test module | Pytest |
| --- | ---: | --- |
| isort | 4 | Pass |
| mimesis | 8 | Pass |
| mlxtend | 8 | Pass |
| typesystem | 6 | Pass |

Kết quả coverage của suite ghép:

- Aggregate score: **86.75%**.
- Statement coverage: **89.62%** (259/289).
- Branch coverage: **85.53%** (130/152).

Kết luận: coverage-unit oracle đã được xác nhận bằng một lần chạy suite thật. Các test của hai replicate không xung đột hoặc gây pollution trong lần kiểm chứng này. Output chi tiết nằm trong thư mục local `binh/phase0_combined_verification/` và được ignore vì chứa coverage report dung lượng lớn.

Chạy lại bằng lệnh:

```powershell
python -m src.optimization.combined_suite `
  --artifacts binh/phase0_runs/calibration16_gemini35_flash_lite_r2 `
  --output-dir binh/phase0_combined_verification-new
```
