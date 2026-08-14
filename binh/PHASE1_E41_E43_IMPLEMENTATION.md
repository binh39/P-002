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
- Existing tests/fixtures được điều khiển độc lập bằng `--repository-test-context` và mặc định tắt.
- Cache schema 17 fingerprint model/config, source target, context policy và cây test Python.

## Verification

- Full repository suite: 107 passed (targeted optimizer suite: 79 passed).
- Ruff cho module context, optimizer và test optimizer: pass.
- Live ablation đã chạy hoàn toàn bằng `vertex_ai/gemini-3.5-flash-lite`; xem
  `binh/PHASE1_E41_E43_LIVE_ABLATION_RESULT.md`.

## Quyết định sau thực nghiệm

1. Promote E41 contract-only thành mặc định: validation `+3,92` điểm và locked holdout `+13,98`.
2. Reject E43 existing tests/fixtures ở dạng hiện tại: validation `-1,96` điểm và nhiều repair error hơn.
3. Giữ cả hai cờ độc lập để các benchmark sau có control đúng protocol.
