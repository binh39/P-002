# Sandbox runner compatibility spike

- Ngày chạy: 2026-08-26
- Trạng thái: Completed cho quyết định Giai đoạn 0
- Script: [`scripts/sandbox_runner_spike.py`](../../scripts/sandbox_runner_spike.py)
- Selector: [`cloud/sandbox_runner_profiles.py`](../../cloud/sandbox_runner_profiles.py)
- Unit tests: [`tests/test_sandbox_runner_profiles.py`](../../tests/test_sandbox_runner_profiles.py)

## Mục tiêu

Kiểm tra runner có thể chạy test/coverage mà không đưa dependency optimizer vào dependency resolution của project, đồng thời chốt hành vi cho ba profile:

1. Project đã có pytest và coverage tương thích.
2. Project không khai báo cả pytest lẫn coverage.
3. Project có toolchain thiếu hoặc ngoài compatibility policy.

## Fixture dùng trong spike

Mỗi execution tạo workspace tạm với:

- Package `demo` dưới `src/`.
- `pytest.ini` khai báo custom marker.
- `conftest.py` cung cấp plugin hook và được test xác nhận đã load.
- Test import native extension `sqlite3` và thực thi truy vấn in-memory.
- Test thực thi coroutine bằng `asyncio`.
- Coverage config trung lập do sandbox tạo, `fail_under = 0`.
- Hai lệnh tách biệt: `coverage run -m pytest`, sau đó `coverage json`.

## Kết quả thực nghiệm

| Profile | Python | Pytest | Coverage | Kết quả | Inventory project |
|---|---:|---:|---:|---|---|
| Project-native | 3.13.14 | 9.1.1 | 7.10.7 | 2 tests pass; 2/2 statements; marker/conftest/native/async pass | Không đổi |
| Sandbox-managed | 3.13.14 | 9.1.1 | 7.15.3 | 2 tests pass; 2/2 statements; marker/conftest/native/async pass | Không đổi |
| Compatibility fallback | 3.13.14 | 9.1.1 | Không có | Không chạy test; trả `INCOMPLETE_PROJECT_RUNNER` | Không inject coverage |

Project-native dùng coverage 7.10.7 được cài vào thư mục tạm, đứng trước runner packages trên `PYTHONPATH`. Sandbox-managed dùng runner layer từ `.venv313/Lib/site-packages`. Cả hai chạy trong temporary workspace và không ghi package vào project inventory.

## Compatibility matrix được chọn

| Tình trạng project | Profile | Hành vi |
|---|---|---|
| Có pytest major 7–9 và coverage major 7 | `project_native` | Dùng nguyên phiên bản project đã resolve; không upgrade/downgrade |
| Không có cả pytest và coverage | `sandbox_managed` | Dùng runner layer riêng theo sandbox image; project resolver không nhận các pin này |
| Chỉ có một trong pytest/coverage | `compatibility_fallback` | Reject có cấu trúc `INCOMPLETE_PROJECT_RUNNER`; không inject package còn thiếu |
| Pytest/coverage ngoài range đã chấp nhận | `compatibility_fallback` | Reject `UNSUPPORTED_PROJECT_RUNNER`; hướng dẫn chọn dependency/profile phù hợp |

Range major 7–9/7 là admission policy ban đầu, không phải tuyên bố mọi minor/plugin combination đã được chứng minh. Exact pair đã chạy trong spike được ghi ở bảng kết quả. Matrix Docker Python 3.10–3.13 và plugin packages phổ biến thuộc quality gate ở giai đoạn sau.

## Profile priority

1. Project-native khi project có đủ pytest và coverage tương thích.
2. Sandbox-managed chỉ khi project không khai báo cả hai tool.
3. Compatibility fallback cho trạng thái hỗn hợp hoặc không tương thích.

Không tự động chuyển từ project-native sang managed sau khi test fail, vì việc đó thay environment fingerprint và làm baseline/candidate không còn paired.

## Cách tái chạy

Mỗi profile cần Python có pytest/coverage tương ứng trên `PYTHONPATH`:

```powershell
py -3.13 scripts/sandbox_runner_spike.py --profile native
py -3.13 scripts/sandbox_runner_spike.py --profile managed
py -3.13 scripts/sandbox_runner_spike.py --profile fallback
```

Schema/selector tests:

```powershell
py -3.13 -m pytest tests/test_sandbox_contract.py tests/test_sandbox_runner_profiles.py -q
```

## Giới hạn đã biết

- Local spike chỉ có Python 3.13.14; chưa thay thế Docker integration matrix 3.10–3.13.
- Native extension được kiểm tra bằng `sqlite3` thuộc standard library, chưa kiểm tra wheel bên thứ ba cho mọi platform.
- `conftest.py`/plugin hook đã được discovery; chưa chứng minh mọi pytest plugin bên thứ ba tương thích.
- Security/network isolation không được chứng minh bởi spike này và thuộc ADR/security integration tests riêng.
