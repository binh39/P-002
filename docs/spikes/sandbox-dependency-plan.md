# Giai đoạn 2: Python metadata và Dependency Plan

- Ngày triển khai: 2026-08-26
- Trạng thái: Completed
- Metadata resolver: [`cloud/sandbox_metadata.py`](../../cloud/sandbox_metadata.py)
- Dependency planner: [`cloud/sandbox_dependency_plan.py`](../../cloud/sandbox_dependency_plan.py)
- Tests: [`tests/test_sandbox_dependency_plan.py`](../../tests/test_sandbox_dependency_plan.py)

## Python metadata resolution

Resolver chỉ đọc project files như data và không import/execute `setup.py`.

Nguồn được thu thập theo thứ tự ổn định:

1. `[project].requires-python`.
2. `[tool.poetry.dependencies].python`.
3. `uv.lock` `requires-python`.
4. Poetry lock `python-versions` nếu có.
5. `setup.cfg` `[options].python_requires`.
6. Static literal `setup(python_requires=...)` trong AST của `setup.py`.
7. `.python-version`.
8. `runtime.txt`.

Mọi nguồn được kết hợp thành một constraint chung. Nếu không có Python minor 3.10–3.13 thỏa tất cả nguồn, error `CONFLICTING_PYTHON_METADATA` liệt kê file, field và raw value. Khi không có metadata, policy chọn 3.12 và đặt `inferred=true`.

Poetry caret/tilde constraints được normalize sang PEP 440. Exact patch constraints trong practical range của một Python minor được nhận diện, không chỉ sample patch 0–30.

## Dependency source priority

Planner tạo đúng một source strategy:

1. Explicit supported lock selection.
2. Root `uv.lock` + `pyproject.toml`.
3. Root `poetry.lock` + `pyproject.toml`.
4. Explicit requirements selection.
5. Root `requirements.txt`.
6. `pyproject.toml`.
7. `setup.cfg`.
8. Static `setup.py`.
9. No dependency metadata.

Lock hiện chỉ chấp nhận `uv.lock` hoặc `poetry.lock`, bắt buộc có `pyproject.toml`. Invalid/stale high-priority source fail rõ ràng và không rơi xuống requirements khác.

## Groups, extras và install target

- Không có `all-groups`/`all-extras`.
- Group `test` được chọn mặc định nếu tồn tại.
- Group/extra explicit phải tồn tại trong manifest.
- Group/extra được sort để input order không đổi fingerprint.
- `dev`, `docs`, `release` không được tự động chọn.
- `InstallTarget` phân biệt dependencies-only với install project.

## Requirements và package indexes

- Chỉ một requirements file được chọn.
- Không cộng `requirements-dev.txt`, `requirements-test.txt` và các file khác.
- Reject nested `-r`, constraints, index options và mọi requirements directive.
- Reject direct URL/path requirement; package phải đến từ index reference được allowlist.
- `package_index_refs` chỉ nhận identifier, không nhận URL, credential hoặc assignment.
- Không có field arbitrary `install_command` trong `DependencySelection`.
- Không thêm `RUNTIME_TOOL_PACKAGES` của optimizer vào declared requirements.

## Canonical fingerprint

SHA-256 được tính trên canonical JSON gồm:

- plan version/source/mode;
- selected manifest/lock;
- canonical groups/extras/index references;
- install target;
- declared requirements;
- Python resolution và mọi metadata source;
- SHA-256 của selected manifest/lock contents.

Absolute project root không nằm trong payload. Hai project tree giống nhau ở hai path khác nhau có fingerprint giống nhau. Thay lock content, group, extra, Python metadata hoặc install target làm fingerprint đổi.

## Test coverage đã viết

Targeted suite bao phủ:

- PEP 621, uv lock, Poetry, setup.cfg/setup.py và hints.
- Conflict diagnostics và inferred default.
- Exact Python patch ngoài sampling cũ.
- Toàn bộ source priority và no-accumulation behavior.
- Safe test group, explicit selection và canonical order.
- Poetry dependency normalization.
- Optimizer pin isolation và absence of arbitrary install command.
- Index references, path escape, unknown lock và requirements smuggling.
- Fingerprint stability/change invariants.
- Invalid lock/metadata và dynamic setup.py without execution.

## Verification status

- Ruff targeted: pass.
- Targeted DependencyPlan suite: 40 passed trong 3.14 giây.
- Toàn bộ sandbox suites: 77 passed, 1 strict expected-red trong 23.12 giây.
- Full root fallback suite: 205 tests, 4 failures nền đã biết, 1 strict xfail, 0 errors trong 122.094 giây. Bốn failure vẫn là optimizer subprocess fallback, isort thiếu `tomli`, và workspace thiếu sample directories `mlxtend`/`typesystem`; không failure nào thuộc Giai đoạn 2.
- Ruff và py_compile quality gates: pass.
- Không production runtime v8 nào import planner/resolver mới.
- Không network resolution hoặc live GEPA benchmark.
