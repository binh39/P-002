# ADR 0003: Chiến lược test runner và coverage adapter

- Trạng thái: Accepted
- Ngày quyết định: 2026-08-26
- Bằng chứng: [Sandbox runner compatibility spike](../spikes/sandbox-runner-compatibility.md)
- Phụ thuộc: [ADR 0001](0001-separate-optimizer-and-project-sandbox.md)

## Bối cảnh

Sandbox cần pytest/coverage để chấm điểm nhưng không được ép pin của optimizer vào project resolver. Dùng duy nhất một runner version có thể phá plugin của project; dùng hoàn toàn toolchain project lại cần contract output ổn định.

## Quyết định

Chọn profile theo inventory đã resolve, trước khi chạy baseline:

1. `project_native`: project có pytest major 7–9 và coverage major 7. Dùng nguyên version của project.
2. `sandbox_managed`: project không có cả pytest lẫn coverage. Dùng immutable runner layer riêng của sandbox image, không cài chúng vào project Dependency Plan.
3. `compatibility_fallback`: project chỉ có một tool hoặc version ngoài matrix. Không tự inject/upgrade; trả lỗi có cấu trúc.

Selector nằm tại [`cloud/sandbox_runner_profiles.py`](../../cloud/sandbox_runner_profiles.py). Policy ban đầu của managed layer là pytest 9.1.1 và coverage 7.15.3; đây là sandbox platform dependency, không phải optimizer dependency và không tham gia resolver project.

## Coverage contract

- Scoring dùng config trung lập do sandbox tạo.
- `coverage run` và `coverage json` dùng cùng config/data identity.
- Project `fail_under`, output path và report formatting không quyết định admission.
- Output từ coverage version khác nhau được normalize về statement/branch unit counts trong `SandboxResult`.
- Exit code pytest 0, 1 và 5 vẫn thử export coverage khi denominator đo được.
- Exit 1 giữ denominator nhưng covered units dùng để score là 0 theo optimizer invariant.

## Plugin và config

- Project-native giữ `conftest.py`, markers và plugin từ Dependency Plan.
- Sandbox không nhận arbitrary pytest command; `RunSpec` chỉ chọn allowlisted test paths/pattern.
- Runner profile/version là thành phần fingerprint.
- Không fallback từ native sang managed sau failure trong cùng evaluation.

## Bằng chứng spike

Ngày 2026-08-26, cả native coverage 7.10.7 và managed coverage 7.15.3 chạy pass hai tests trên Python 3.13.14, gồm custom marker, conftest hook, native sqlite3 và async behavior. Fallback với pytest-only trả `INCOMPLETE_PROJECT_RUNNER` và không inject coverage. Inventory digest trước/sau không đổi.

Matrix Python 3.10–3.13 và plugin bên thứ ba vẫn là integration gate trước rollout từng image, không phải bằng chứng đã hoàn tất trong local spike.

## Hệ quả

- Project isort có thể giữ coverage 7.10.7 dù optimizer dùng version khác.
- Trạng thái toolchain thiếu bị reject sớm và có thể sửa được, thay vì resolver âm thầm đổi dependency.
- Sandbox-managed cần cơ chế expose project site-packages cho runner mà không merge package inventory; implementation phải có integration test.
- Mọi thay đổi managed runner version làm fingerprint đổi và yêu cầu rebaseline.

## Tiêu chí xác minh

- Unit tests selector không mutate input inventory.
- Native/managed spike chạy coverage JSON thành công.
- Fallback không thực thi test hoặc cài package.
- Baseline/candidate không được dùng profile/version khác nhau.
