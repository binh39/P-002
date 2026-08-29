# ADR 0004: Dependency source priority và group/extra policy

- Trạng thái: Accepted
- Ngày quyết định: 2026-08-26
- Phụ thuộc: [ADR 0002](0002-project-environment-artifact-per-fingerprint.md)

## Bối cảnh

Runtime hiện có thể export tất cả lock groups, bật tất cả extras hoặc cộng nhiều requirements files. Cài dependency ngoài phạm vi runtime/test tạo conflict không cần thiết và làm fingerprint khó giải thích.

## Quyết định

Mỗi project tạo đúng một canonical `DependencyPlan`. Không cộng dồn nhiều chiến lược cài đặt mặc định.

### Priority nguồn dependency

1. Lock file do settings/API chọn rõ ràng, sau khi xác minh path thuộc project.
2. `uv.lock` đi cùng `pyproject.toml`.
3. `poetry.lock` đi cùng Poetry metadata trong `pyproject.toml`.
4. Requirements file do settings chọn rõ ràng.
5. Root `requirements.txt`.
6. `pyproject.toml` không có supported lock.
7. Static metadata từ `setup.cfg`.
8. Static, không execute, metadata từ `setup.py`; nếu không parse an toàn thì trả `UNSUPPORTED_SETUP_METADATA`.
9. Không có dependency manifest: mode `none`.

Nếu nguồn priority cao có mặt nhưng invalid/stale, build fail rõ ràng; không âm thầm rơi xuống nguồn khác vì sẽ thay dependency graph ngoài ý muốn.

### Groups và extras

- Chỉ chọn group/extra được settings khai báo và validate.
- Nếu không khai báo, có thể auto-select đúng một group tên `test` khi manifest định nghĩa nó.
- Không auto-select `dev`, `docs`, `release`, `lint` hoặc mọi group.
- Không dùng `--all-groups` hay `--all-extras`.
- Test requirements nested chỉ được chọn khi map trực tiếp tới selected test suite và không trùng source chính.
- Group/extra thực tế là thành phần Dependency Plan và fingerprint.

### Index và credentials

- Contract chỉ mang `package_index_refs`, không mang URL có credential hoặc secret value.
- Orchestrator resolve reference theo allowlist ở build stage.
- Không log URL credential hoặc bake credential vào artifact/layer.

### Cấm command tự do

`install_command`/`test_command` dạng shell không được execute trong sandbox v2. Mọi lựa chọn cài đặt phải được biểu diễn bằng field có schema và allowlist.

## Conflict diagnostics

Resolver output được phân loại tối thiểu thành dependency conflict, package not found, incompatible Python, index auth, transient network, timeout và internal. Khi resolver cung cấp nguồn, result phải chỉ ra package/version/manifest hoặc project gây constraint.

## Hệ quả

- Plan tái lập, audit được và không cài dependency ngoài ý muốn.
- Một số project phụ thuộc dev group ngầm phải chọn group rõ ràng hoặc đổi thành `test`.
- Legacy setup.py động không được execute để lấy metadata, nên cần hướng dẫn migrate manifest.

## Tiêu chí xác minh

- Cùng input tạo canonical plan/fingerprint giống nhau.
- Thay lock/group/extra/index identity làm fingerprint đổi.
- Dev/docs conflict không ảnh hưởng project nếu group không được chọn.
- Optimizer `RUNTIME_TOOL_PACKAGES` không xuất hiện trong plan.
