# P1 E41/E43 — Target contract và repository test context

Ngày: 2026-08-14

## Mục tiêu

Giảm lỗi do model đoán sai API, constructor, fixture và convention của repo mà không hard-code
thông tin target vào global prompt được GEPA tối ưu.

## Đã implement

- E41: exact function/class signature, type hints, default values, return annotation, decorators,
  docstring rút gọn và enclosing-class inheritance.
- E43: chọn tối đa bốn test function liên quan theo symbol/module và tối đa hai fixture thực sự
  được các test đó tham chiếu, trên tối đa bốn file.
- Context mặc định bị giới hạn 6.000 ký tự và được nối động sau khi render prompt template.
- `--context-tests-dir` là nguồn chỉ đọc từ test repo gốc; `--tests-dir` tiếp tục là workspace sinh
  test cô lập.
- Có `--no-target-context` để chạy control ablation và `--target-context-max-chars` để khóa budget.
- Cache schema 16 fingerprint model/config, source target và toàn bộ cây test Python của từng repo.

## Verification

- Full repository suite: 107 passed (targeted optimizer suite: 79 passed).
- Ruff cho module context, optimizer và test optimizer: pass.
- Chưa gọi Gemini và chưa có kết quả coverage live trong bước implementation này.

## Thực nghiệm tiếp theo

Chạy paired ablation cùng dataset, split, seed 7, minibatch 3, budget 30 và
`gemini-3.5-flash-lite`:

1. Control: `target_context=false`.
2. Treatment: `target_context=true`, budget 6.000 ký tự.
3. So sánh validation lặp và locked holdout; chỉ giữ treatment nếu gain vượt nhiễu đo được và
   collection/import/runtime failures giảm.
