# Báo cáo triển khai Sandbox Builder và artifact cache

- Ngày: 2026-08-26
- Phạm vi: Giai đoạn 3
- Trạng thái: code/unit/local Docker integration hoàn tất; remote CI run đang chờ PR

## Thành phần đã triển khai

- `cloud/Dockerfile.sandbox`: image tham số hóa Python 3.10–3.13, chỉ có agent, `uv`, Poetry export và các module sandbox; không copy CoverUp, GEPA hay LLM SDK.
- `cloud/sandbox_agent.py`: lệnh `contract` kiểm tra image và lệnh `build` nhận Dependency Plan canonical, image digest và runner identity.
- `cloud/sandbox_builder.py`: resolve dependency trong staging riêng, `uv pip check`, inventory/hash, archive venv và atomic publish.
- `FileArtifactCache`: key theo environment fingerprint; lease per-key; cache hit/miss; hash validation; quarantine/rebuild corruption; TTL/quota/GC; access metadata tách khỏi artifact bất biến.
- `UvProjectResolver`: chỉ dựng command allowlist; network marker chỉ bật cho install; package-index credential được inject qua environment và redact khỏi diagnostic.
- Retry: chỉ lỗi có `retryable=True` mới dùng exponential backoff, jitter và deadline. Conflict, Python mismatch và package-index configuration error không retry.

## Boundary và tính bất biến

Environment fingerprint gồm Dependency Plan fingerprint, toàn bộ image identity (kể cả digest) và runner identity. Artifact chỉ chứa thư mục `venv`; source project, `.env` và package-index secret không được copy vào cache. Manifest chỉ được publish sau resolve, consistency check, inventory và archive hash thành công. Build lỗi chỉ xóa staging của key đang build, không sửa object tốt khác.

Docker image không phải GEPA runtime. Agent trong image không import hoặc cài `coverup`, `dspy`, `gepa`, `litellm`, `openai` hay Vertex SDK. CI đã có matrix build/contract cho Python 3.10, 3.11, 3.12 và 3.13.

Local Docker matrix đã build và contract-pass:

| Python | Full version | Local image ID |
|---|---|---|
| 3.10 | 3.10.21 | `sha256:7bfe7a0e...991727` |
| 3.11 | 3.11.16 | `sha256:437e6b99...0ea591` |
| 3.12 | 3.12.14 | `sha256:3d649015...d4195` |
| 3.13 | 3.13.15 | `sha256:20b38cb7...2328c4` |

Mỗi contract xác nhận có `uv`/Poetry và `forbidden_modules_present=[]`. Python 3.10 dùng `tomli` fallback vì stdlib `tomllib` chỉ có từ Python 3.11.

## Bằng chứng kiểm thử local

Lệnh:

```powershell
.\.venv313\Scripts\python.exe -m pytest -p no:pytest_isolate `
  tests\test_sandbox_builder.py `
  tests\test_sandbox_dependency_plan.py `
  tests\test_sandbox_characterization.py `
  tests\test_sandbox_contract.py `
  tests\test_sandbox_runner_profiles.py -q
```

Kết quả cuối: sandbox suites `100 passed, 1 xfailed`; phần còn lại của regression suite `223 passed, 4 deselected, 1 xfailed`. Bốn node deselected là các lỗi baseline/môi trường đã ghi từ trước: optimizer subprocess, isort host thiếu `tomli`, và hai sample repo `mlxtend`/`typesystem` chưa giải nén. Sau khi integration phát hiện stderr của `uv` làm nhiễu JSON inventory, builder có thêm regression test tách stdout/stderr.

Test builder xác nhận:

- project fixture giữ `coverage==7.10.7` trong inventory dù runner identity dùng coverage `7.15.2`;
- hai dependency plan xung đột tạo fingerprint và object directory khác nhau;
- cache hit không gọi resolver lần hai;
- build lỗi không publish và không làm thay đổi artifact tốt;
- artifact corruption bị quarantine rồi rebuild;
- manifest identity/inventory bị sửa cũng bị coi là corruption và rebuild;
- source và `.env` không nằm trong archive;
- conflict/Python mismatch không retry, transient retry đúng backoff/deadline;
- subprocess timeout được chuẩn hóa thành lỗi retryable có source;
- resolver diagnostic giữ manifest liên quan và redact package-index credential.

## Docker integration isort

Dependency Plan thật của `src/sample_repo/isort` chọn Python 3.12, `uv.lock` và group `dev`. Container nhận source read-only, resolve thành công và publish:

- environment fingerprint: `4a503254ebd3213e62e92e2dda526d5f9c9d8bab604190fa31bb376d5886b740`;
- artifact SHA-256: `c74ddd23f54db24ffeb5f9693dbb67b330ad74a4bf9549caae128d71053abde6`;
- project inventory: `coverage==7.10.7`;
- runner identity: coverage `7.15.2`;
- archive có 23,605 entries và tất cả nằm dưới `venv/`;
- chạy lại cùng request với `--network none` vẫn trả đúng artifact, chứng minh cache hit không chạy resolver.

Bằng chứng máy đọc được nằm tại [`eval/sandbox_phase3_isort/integration-result.json`](../../eval/sandbox_phase3_isort/integration-result.json). Lần chạy đầu cũng phát hiện JSON inventory bị lẫn status trên stderr của `uv`; builder đã tách stdout/stderr và thêm regression test trước khi chạy lại thành công. Failed staging không publish object.

## Gate còn mở

CI workflow đã cấu hình nhưng chưa có remote CI run trong phiên này, nên checklist “chạy image contract test trong CI” vẫn mở. Local image ID có thể đổi khi rebuild do BuildKit attestation; production phải dùng registry digest đã push. Production v8 chưa import builder theo ranh giới rollout đã chốt.
