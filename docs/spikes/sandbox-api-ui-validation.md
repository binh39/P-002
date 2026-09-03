# Giai đoạn 6 — API/UI upload validation

Ngày kiểm tra: 2026-08-27

## Phạm vi đã triển khai

- Project record lưu `requested_python_version`, `detected_python_version` và `resolved_python_version`; record cũ tiếp tục mặc định requested Python 3.12.
- Upload record giữ snapshot Python đã chọn, mặc định 3.12 cho schema/record cũ; project creation từ chối snapshot không khớp.
- API trả riêng `runtime_build_status` và `runtime_execution_status`.
- Runtime report hỗ trợ stage, error code, retryability, environment fingerprint, runner identity và dependency conflict có cấu trúc.
- API có capability, validate settings, retry build và retry execution endpoints.
- Execution retry truyền immutable bundle và expected fingerprint vào worker; worker tính lại fingerprint, bỏ qua dependency install khi khớp và từ chối artifact stale.
- UI chỉ liệt kê capability healthy (hiện release 3.12), gửi Python settings cùng upload/project request, hiển thị sáu admission stage và ẩn retry cho deterministic dependency conflict.
- Project settings có Save/Validate thật và không cho nhập runtime image hay dependency shell command.
- Active bundle chỉ được thay sau khi toàn bộ candidate report đạt `runtime_ready`; rejection giữ bundle cũ.

## Bằng chứng kiểm thử

```text
Backend targeted: 13 passed, 1 deselected (known missing mimesis fixture)
Runtime workspace regression: 17 passed
Backend full app: 75 passed, 1 failed (known missing src/sample_repo/mimesis)
Frontend targeted: 9 passed
Frontend full: 53 passed
Frontend typecheck: passed
Frontend ESLint: passed
Frontend production build: passed
Backend Ruff (projects/uploads/tests): passed
git diff --check: passed
```

Docker Desktop không cần cho API/frontend/unit tests của giai đoạn này. Docker chỉ cần khi chạy lại image contract hoặc acceptance end-to-end trong container.

## Artifact reuse

`POST /projects/{id}/retry-execution` chỉ dùng bundle đã có khi kèm fingerprint. Worker tính fingerprint từ source/config hiện tại trước khi giải nén artifact; mismatch dừng trước execution. Trong nhánh reuse, dependency install bị bỏ qua và bundle cũ chỉ trở thành kết quả admission sau khi test/coverage thành công. Active bundle đang dùng không bị thay trong lúc retry.

Remote image-contract CI của Giai đoạn 3 vẫn là merge/deploy gate riêng; việc chưa chạy remote CI không làm mất hiệu lực của các test API/UI local ở trên.

Root suite bắt buộc cũng đã được chạy bằng Python Store hiện tại và đạt 240 pass/1 xfail. Bốn lỗi baseline vẫn là teacher workspace, thiếu `tomli`, `mlxtend` và `typesystem`. Năm lỗi sandbox execution bổ sung đều có cùng nguyên nhân môi trường: launcher `.venv313` cũ không còn được Windows cho chạy, còn Python hệ thống không thấy module `coverage` trong subprocess cô lập. Các targeted sandbox/Docker acceptance của Giai đoạn 3–5 không bị thay đổi bởi code API/UI này.
