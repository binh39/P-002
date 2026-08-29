# Project Sandbox Protocol v1

## Trạng thái

- Contract version: `1`
- Production runtime protocol hiện tại: `8` (không thay đổi trong Giai đoạn 0)
- Python compatibility của contract module: 3.10–3.13
- Implementation: [`cloud/sandbox_contract.py`](../../cloud/sandbox_contract.py)

Protocol này định nghĩa biên giao tiếp giữa optimizer/orchestrator và project sandbox. Nó chưa được nối vào production runtime trong Giai đoạn 0.

## Nguyên tắc

- Payload JSON là strict: field không biết bị reject.
- Command shell tự do không thuộc contract.
- Mọi path là relative POSIX path và không được thoát project workspace.
- Secret chỉ xuất hiện dưới dạng reference đã allowlist; không gửi secret value.
- Baseline và candidate dùng `RunSpec` riêng nhưng phải có cùng environment fingerprint để so điểm.
- Field chẩn đoán mới trong `SandboxResult` là optional để worker/client chuyển đổi dần.

## SandboxSpec

`SandboxSpec` mô tả cách build/chạy một project sandbox:

- `protocol_version`: luôn là `1`.
- `project_id` và `archive_sha256`: định danh input bất biến.
- `requested_python` và optional `detected_python`.
- `source_directory` và `test_directory`.
- `dependency_policy`: mode, manifest/lock, groups, extras và package-index references.
- `runner_profile`: `project_native`, `sandbox_managed` hoặc `compatibility_fallback`.
- `coverage_mode`: statement hoặc statement-and-branch.
- `allowed_environment_variables`: chỉ tên biến; value được resolve bên orchestrator theo policy.
- `resource_limits`: CPU, RAM, timeout, process và output limit.

Ví dụ: [`sandbox_spec.v1.json`](examples/sandbox_spec.v1.json).

## RunSpec

Mỗi baseline/candidate execution có `RunSpec` riêng:

- `run_id`: định danh duy nhất.
- `kind`: `baseline` hoặc `candidate`.
- `environment_fingerprint`: artifact/runtime identity dự kiến.
- `test_paths`: path cụ thể được phép chạy.
- `test_pattern`: filename pattern, không phải arbitrary pytest args.

Ví dụ baseline và candidate:

- [`run_spec.baseline.v1.json`](examples/run_spec.baseline.v1.json)
- [`run_spec.candidate.v1.json`](examples/run_spec.candidate.v1.json)

## SandboxResult

Kết quả tối thiểu chỉ cần version, run ID, status và fingerprint. Các field còn lại optional trong migration:

- `exit_code`
- `failure_stage`
- `error_code`
- `retryable`
- `test_counts`
- `coverage`
- `coverage_artifact`
- bounded `stdout`/`stderr`
- `duration_seconds` và `peak_memory_mb`

Kết quả `failed` bắt buộc có `failure_stage` và `error_code`. Kết quả `succeeded` không được mang failure diagnostics.

Ví dụ:

- [`sandbox_result.success.v1.json`](examples/sandbox_result.success.v1.json)
- [`sandbox_result.failure.v1.json`](examples/sandbox_result.failure.v1.json)

## Failure stages

- `build`: metadata/dependency/environment artifact.
- `collect`: test discovery/config/plugin.
- `test`: test execution.
- `coverage`: instrumentation/export/parse.
- `timeout`: execution vượt budget.
- `internal`: lỗi sandbox agent/orchestrator không thuộc project.

`retryable` chỉ đúng với lỗi transient. Dependency conflict và incompatible Python không retry.

## Compatibility và migration

- Giai đoạn 0 không thay `RUNTIME_PROTOCOL_VERSION` hoặc `MINIMUM_RUNTIME_PROTOCOL_VERSION`.
- Backend tiếp tục đọc runtime report v8 trong khi contract sandbox v1 được phát triển sau feature flag.
- Field mới ở result là optional để client mới đọc được payload tối thiểu.
- Worker/client chỉ nâng minimum sandbox protocol sau khi jobs mới rollout hoàn tất.
- Evaluation phải gọi `require_matching_fingerprint()` trước scoring.

## Validation

[`tests/test_sandbox_contract.py`](../../tests/test_sandbox_contract.py) kiểm tra:

- Toàn bộ JSON examples deserialize và round-trip.
- Baseline/candidate có cùng environment fingerprint.
- Unknown fields, path traversal, arbitrary path pattern và secret-like environment names bị reject.
- Locked mode phải có lock file.
- Failure diagnostics và optional migration fields đúng contract.
- Fingerprint/run ID mismatch bị chặn trước scoring.
