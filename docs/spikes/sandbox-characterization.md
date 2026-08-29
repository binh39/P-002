# Giai đoạn 1: Sandbox characterization report

- Ngày chạy: 2026-08-26
- Trạng thái: Completed
- Fixture catalog: [`tests/fixtures/sandbox_projects.json`](../../tests/fixtures/sandbox_projects.json)
- Test suite: [`tests/test_sandbox_characterization.py`](../../tests/test_sandbox_characterization.py)
- Resolver classifier: [`cloud/sandbox_errors.py`](../../cloud/sandbox_errors.py)

## Fixture coverage

Catalog chứa 15 project cases, bao phủ:

- Python 3.12 tối giản có test pass.
- Project coverage 7.10.7 trong khi optimizer hiện pin 7.15.2.
- Hai project pin `shared-dependency` 1.0.0 và 2.0.0.
- `uv.lock` và Poetry lock/metadata.
- `setup.cfg`-only và `setup.py`-only.
- `setup.py` có side effect sentinel để chứng minh metadata characterization chỉ AST-parse, không execute.
- Dev/docs/release groups conflict nhưng test group rỗng/an toàn.
- Project không pytest/coverage và project dùng runner/plugin cũ.
- Python `>=99`, no-tests, coverage `fail_under = 99` và pytest `addopts`.

Catalog là JSON text deterministic. Test materialize file tree/ZIP trong temporary workspace; ZIP entry order, timestamp và mode được cố định, nên cùng case tạo cùng SHA-256.

## Characterization results

Lệnh:

```powershell
py -3.13 -m pytest tests/test_sandbox_characterization.py -q -rxX
```

Kết quả:

- 15 passed.
- 1 expected-red (`xfail(strict=True)`): project `fail_under = 99` vẫn bị runtime v8 reject ở coverage export.
- Không unit test nào truy cập package registry hoặc internet.

Expected-red là regression contract có chủ đích cho Giai đoạn 4. `strict=True` bảo đảm khi production behavior được sửa, test sẽ XPASS và làm suite fail cho tới khi bỏ marker/chuyển thành test pass bình thường.

## Invariant evidence

### Shared resolver failure

Test materialize hai ZIP có requirements conflict, ép nhánh uv bằng fake subprocess và xác nhận command hiện tại gom:

- requirements của cả hai project;
- toàn bộ `RUNTIME_TOOL_PACKAGES` của optimizer;
- sau đó trả dependency conflict.

Không gọi resolver/network thật.

### Isolated sandbox proof

Hai temporary sandbox processes nhận hai `PYTHONPATH` riêng và import cùng module name ở version 1.0.0/2.0.0 thành công. Đây là offline isolation proof; production builder integration vẫn thuộc Giai đoạn 3.

### Project dependency input

Fixture coverage giữ `coverage==7.10.7`; không tự nhận coverage 7.15.2, slipcover, pytest-repeat hoặc pytest-timeout từ optimizer. Pytest 9.1.1 có mặt vì chính fixture khai báo, không phải do inheritance.

Dependency Plan implementation và end-to-end assertion vẫn thuộc Giai đoạn 2; characterization này khóa expected input boundary.

### Fingerprint gate

`RunSpec` fingerprint `a...` và `SandboxResult` fingerprint `b...` bị `require_matching_fingerprint()` reject trước scoring.

### Atomic bundle và no-tests

Các targeted suites có sẵn được chạy lại:

- `app/tests/test_runtime_preparation.py`: 6 passed.
- Runtime no-tests và incompatible-Python tests: 2 passed.

Backend test xác nhận candidate fail không thay active bundle. No-tests test xác nhận zero coverage và `.promptopt-empty-tests` vẫn tạo runtime-ready result.

### Resolver error classification

Classifier mới tách:

- unsatisfiable/no-solution thành `DEPENDENCY_CONFLICT`, không retry;
- HTTP 503/DNS temporary failure thành `DEPENDENCY_NETWORK_TRANSIENT`, retryable.

Classifier chưa được production runtime v8 import; wiring thuộc sandbox builder/error handling ở giai đoạn sau.

## Quality checks

- Characterization: 15 passed, 1 expected-red.
- Contract/runner suite từ Giai đoạn 0: 22 passed.
- Backend atomic bundle: 6 passed.
- Runtime no-tests/Python incompatibility: 2 passed.
- Ruff cho files Giai đoạn 1: pass.
- Full root fallback suite: 165 tests, 4 failures nền đã biết, 1 strict xfail, 0 errors trong 156.793 giây. Bốn failure là optimizer subprocess fallback, isort thiếu `tomli`, và workspace thiếu sample directories `mlxtend`/`typesystem`; không failure nào thuộc files Giai đoạn 1.
- Không live GEPA benchmark hoặc network dependency resolution.

## Giới hạn còn lại

- Isolated sandbox proof là process-level fixture, chưa phải production artifact builder.
- Dependency Plan chưa được implement; test hiện khóa project input boundary.
- `fail_under` vẫn là lỗi production có chủ đích chưa sửa ở characterization stage.
- Docker/security/network policy integration thuộc các giai đoạn sau.
