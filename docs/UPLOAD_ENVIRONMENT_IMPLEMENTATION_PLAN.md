# Kế hoạch triển khai: Project Sandbox độc lập cho upload và chấm điểm

## Thông tin theo dõi

- Nhánh triển khai: `fix-environment-upload-prj`
- Trạng thái: Giai đoạn 9 đã có feature flag, dual-read, shadow/canary controller, metrics endpoint và rollback runbook pass local; deploy/canary/rollback drill thật còn là bước vận hành
- Visual validation: có development-only `local_docker` adapter để chạy UI upload → isolated build/test/coverage trên Docker Desktop; production vẫn fail-closed
- Kiến trúc đích: Một sandbox độc lập cho mỗi project/environment fingerprint
- Phạm vi hiện tại: Builder, execution sandbox, optimizer scoring, API/UI upload và fingerprint-guarded artifact reuse đã tích hợp
- Mục tiêu: Tool tối ưu chỉ sinh test và điều phối; dependency của tool không tham gia dependency resolution của project

## Quy ước checklist

- `[ ]`: Chưa thực hiện
- `[x]`: Đã hoàn thành và có bằng chứng kiểm thử/review
- Chỉ đánh dấu hoàn thành khi task đạt tiêu chí nghiệm thu và có link commit, PR, CI log hoặc artifact.
- Ghi bằng chứng vào mục **Nhật ký hoàn thành** ở cuối tài liệu.

## 1. Vấn đề cần giải quyết

Runtime hiện tạo một shared virtual environment, gom dependency của nhiều project và ép thêm tooling của hệ thống như pytest/coverage. Cách này gây ra các lỗi:

- Project và tool khóa hai phiên bản khác nhau của cùng package, ví dụ `coverage==7.10.7` và `coverage==7.15.2`.
- Hai project hợp lệ riêng lẻ vẫn có thể conflict khi bị cài chung một environment.
- Resolver đang cài quá rộng từ groups, extras và requirements files.
- Python version mà API/UI cho phép có thể không trùng với Python thật trong runtime image.
- Retry không thể sửa conflict có tính xác định.
- Lỗi dependency, network, test và coverage chưa được phân loại rõ.
- Một project bị lỗi không được phép làm thay đổi active bundle của environment.

## 2. Kiến trúc đích

```text
Optimizer / Test Generator
  - CoverUp, GEPA, LLM SDK
  - đọc source/context
  - sinh candidate tests
  - điều phối baseline/candidate evaluation
  - không cài dependency project vào môi trường của tool
                    |
                    | SandboxSpec + source archive + generated tests
                    v
Sandbox Orchestrator
  - xác thực request
  - chọn Python image
  - build/reuse Project Environment Artifact
  - tạo sandbox execution cô lập
                    |
                    v
Project Sandbox
  - đúng Python version của project
  - dependency/lock của chính project
  - test runner adapter tối thiểu
  - chạy test và đo coverage
  - không chứa CoverUp, GEPA hoặc LLM credential
                    |
                    | SandboxResult + coverage artifact + fingerprint
                    v
Optimizer / Scoring
  - kiểm tra fingerprint
  - chấm điểm theo baseline denominator
  - tổng hợp kết quả nhiều project bên ngoài sandbox
```

### Ranh giới trách nhiệm

#### Optimizer/Test Generator

- Sinh test, quản lý prompt, search, scoring và promotion gate.
- Không thực thi code project trực tiếp.
- Không áp pin pytest/coverage của tool lên project.
- Không truyền credential LLM/cloud vào sandbox.

#### Sandbox Orchestrator

- Chọn image theo Python version.
- Dựng và cache environment artifact theo fingerprint.
- Quản lý lifecycle, resource limit, timeout, network và artifact.
- Không tự suy diễn dependency ngoài policy đã ghi trong `SandboxSpec`.

#### Project Sandbox

- Chỉ chứa source, dependency của project và runner contract tối thiểu.
- Chạy baseline tests và generated tests.
- Trả kết quả có cấu trúc; không quyết định promote prompt.
- Bị hủy sau mỗi execution; environment artifact có thể được cache bất biến.

## 3. Invariant không được phá

- [ ] Baseline và candidate phải chạy trên cùng một environment fingerprint.
- [ ] Nếu fingerprint khác, không so điểm trực tiếp; phải chạy lại baseline.
- [ ] Dependency của optimizer không tham gia dependency resolution của project.
- [ ] Mỗi project có environment artifact riêng; không dùng shared venv giữa các project.
- [ ] Điểm nhiều project được tổng hợp bên ngoài sandbox.
- [ ] Active bundle chỉ đổi sau khi mọi validation bắt buộc thành công.
- [ ] Upload/build/test thất bại không làm thay đổi active bundle hoặc sandbox artifact đang dùng.
- [ ] Pytest exit code 5 là zero-test hợp lệ nếu coverage denominator đo được.
- [ ] Test fail không được làm denominator biến mất hoặc làm điểm tăng giả.
- [ ] GEPA không nhìn final holdout trước promotion gate và mọi invariant trong `AGENTS.md` vẫn giữ nguyên.
- [ ] Sandbox không nhận LLM key, cloud credential, Docker socket hoặc host workspace ngoài phạm vi cho phép.
- [ ] Python version chỉ được hiển thị là hỗ trợ khi có image và contract test tương ứng.
- [ ] Schema/request cũ tiếp tục mặc định Python 3.12 trong thời gian migration.

## 4. Đơn vị cô lập và vòng đời

### Project Environment Artifact

Artifact bất biến, có thể cache và tái sử dụng, bao gồm:

- Python implementation/version.
- OS/platform và base image digest.
- Dependency đã resolve/cài theo project.
- Project package nếu policy yêu cầu install editable/wheel.
- Metadata và dependency fingerprint.
- Không chứa generated tests, result hoặc secret.

### Sandbox Execution

Một container/process cô lập, tồn tại trong một lần đánh giá:

1. Mount/copy source revision đã xác định.
2. Gắn Project Environment Artifact tương ứng.
3. Copy baseline tests hoặc generated tests vào vùng ghi tạm.
4. Chạy collect/test/coverage theo `RunSpec`.
5. Xuất `SandboxResult` và artifact.
6. Hủy execution workspace.

### Environment Fingerprint

Fingerprint tối thiểu phải bao gồm:

- Python implementation và full version.
- Platform/architecture.
- Base image digest.
- Nội dung lock/manifest và dependency selection policy.
- Project source revision/hash nếu project được cài vào environment artifact.
- Runner adapter protocol/version.
- Test runner và coverage implementation/version thực tế.
- Biến cấu hình có ảnh hưởng đến import/test/coverage, không bao gồm secret value thô.

## 5. Giai đoạn 0 — Chốt contract và quyết định kiến trúc

### 5.1. Viết ADR bắt buộc

- [x] ADR: Tách optimizer environment và project sandbox — [ADR 0001](adr/0001-separate-optimizer-and-project-sandbox.md).
- [x] ADR: Một environment artifact cho một project fingerprint, không shared venv — [ADR 0002](adr/0002-project-environment-artifact-per-fingerprint.md).
- [x] ADR: Chiến lược test runner/coverage adapter — [ADR 0003](adr/0003-sandbox-runner-and-coverage-strategy.md).
- [x] ADR: Dependency source priority và group/extra policy — [ADR 0004](adr/0004-dependency-source-and-selection-policy.md).
- [x] ADR: Sandbox security/network policy — [ADR 0005](adr/0005-sandbox-security-and-network-policy.md).
- [x] ADR: Cache key, lifecycle và invalidation — [ADR 0006](adr/0006-environment-artifact-cache-policy.md).
- [x] ADR: Python image routing và protocol migration — [ADR 0007](adr/0007-python-image-routing-and-protocol-migration.md).

### 5.2. Chốt runner strategy bằng spike

Đánh giá ba profile, không chọn chỉ dựa trên lý thuyết:

- [x] **Project-native:** dùng pytest/coverage do project khai báo nếu đáp ứng output contract — spike pass với coverage 7.10.7.
- [x] **Sandbox-managed:** project không có tooling thì dùng runner do sandbox cung cấp, không dùng pin của optimizer — spike pass với coverage 7.15.3.
- [x] **Compatibility fallback:** project tooling quá cũ/không tương thích thì trả lỗi có hướng dẫn; spike xác nhận `INCOMPLETE_PROJECT_RUNNER` và không inject package.
- [x] Test plugin discovery, `conftest.py`, custom marker, native extension và async behavior ở native/managed; fallback không chạy test theo thiết kế.
- [x] Chứng minh runner không làm thay đổi dependency resolution của project — inventory digest trước/sau giữ nguyên.
- [x] Chọn profile priority và ghi rõ [compatibility matrix](spikes/sandbox-runner-compatibility.md).

### 5.3. Định nghĩa protocol

- [x] Định nghĩa versioned [`SandboxSpec`](../cloud/sandbox_contract.py):
  - project/archive identity
  - requested/detected Python
  - source/test paths
  - dependency policy
  - environment variables allowlist
  - resource/time limits
  - test selection
  - coverage mode
- [x] Định nghĩa `RunSpec` riêng cho baseline và candidate tests, có ví dụ cho cả hai.
- [x] Định nghĩa versioned `SandboxResult`:
  - status và exit code
  - failure stage/error code/retryable
  - test counts
  - statement/branch coverage
  - per-file/per-symbol coverage artifact
  - stdout/stderr đã giới hạn
  - environment fingerprint
  - duration/resource usage
- [x] Field diagnostics/result mới là optional trong giai đoạn tương thích ngược và có minimal-payload test.
- [x] Không nâng minimum runtime protocol; sandbox dùng namespace `SANDBOX_PROTOCOL_VERSION = 1` riêng.

### Tiêu chí hoàn thành giai đoạn 0

- [x] ADR được [review nhất quán](adr/README.md); 7/7 ADR Accepted và không có link hỏng.
- [x] Có [compatibility matrix](spikes/sandbox-runner-compatibility.md) cho runner, ghi rõ phạm vi đã test và giới hạn.
- [x] Contract có [schema tests](../tests/test_sandbox_contract.py) và [ví dụ request/result](contracts/project-sandbox-protocol-v1.md); targeted suite 22 tests pass.
- [x] Chưa thay đổi hành vi production — worktree hiện chỉ thêm/cập nhật tài liệu kế hoạch và ADR.

---

## 6. Giai đoạn 1 — Characterization và regression fixtures

### 6.1. Fixture dependency/environment

- [x] Project Python 3.12 tối giản, tests pass.
- [x] Project `coverage==7.10.7` trong khi optimizer dùng `coverage==7.15.2`.
- [x] Hai project khóa hai phiên bản package mâu thuẫn nhưng chạy độc lập đều hợp lệ.
- [x] Project có `uv.lock`.
- [x] Project có Poetry lock/metadata.
- [x] Project chỉ dùng `setup.cfg`.
- [x] Project chỉ dùng `setup.py` và metadata được AST-parse, không execute side effect sentinel.
- [x] Project có conflicting dev/docs/release groups không cần cho test.
- [x] Project không có pytest/coverage.
- [x] Project dùng pytest/plugin cũ.
- [x] Project yêu cầu Python không tương thích.
- [x] Project không có tests.
- [x] Project có `fail_under = 99`.
- [x] Project có `pytest.ini` hoặc `addopts` đặc biệt.

### 6.2. Invariant tests

- [x] Chứng minh lỗi shared venv hiện tại bằng deterministic regression reproduction, không gọi resolver/network thật.
- [x] Chứng minh hai project conflict chạy thành công trong hai offline process sandbox riêng; production builder integration vẫn thuộc Giai đoạn 3.
- [x] Khóa project dependency input không tự nhận optimizer pins; Dependency Plan end-to-end thuộc Giai đoạn 2.
- [x] Chứng minh baseline/candidate khác fingerprint bị từ chối trước scoring.
- [x] Chứng minh active bundle giữ nguyên khi build/test candidate thất bại — backend targeted suite 6 tests pass.
- [x] Chứng minh no-tests vẫn cung cấp denominator hợp lệ — targeted runtime test pass.
- [x] Thêm expected-red `xfail(strict=True)` chứng minh `fail_under` hiện còn làm admission fail; marker phải được bỏ khi Giai đoạn 4 sửa xong.
- [x] Chứng minh lỗi network khác dependency conflict bằng structured classifier, không dùng network thật.

### Tiêu chí hoàn thành giai đoạn 1

- [x] Mỗi lỗi mục tiêu có fixture deterministic trong [`sandbox_projects.json`](../tests/fixtures/sandbox_projects.json).
- [x] Không dùng network thật trong unit tests; resolver/network outputs đều fake hoặc static.
- [x] Fixture ZIP deterministic thật được materialize, SHA-256 kiểm tra và extract bằng runtime `safe_extract_zip`.

---

## 7. Giai đoạn 2 — Project metadata và Dependency Plan

### 7.1. Phát hiện Python version

- [x] Đọc `[project].requires-python`.
- [x] Đọc metadata từ `uv.lock`/Poetry lock khi có.
- [x] Hỗ trợ Poetry metadata và normalize caret/tilde constraint.
- [x] Hỗ trợ `setup.cfg` và AST-parse `setup.py` an toàn, không execute.
- [x] Đọc `.python-version` và `runtime.txt` như hint có priority rõ ràng.
- [x] Báo đầy đủ file, field và raw value khi metadata mâu thuẫn.
- [x] Không có metadata thì dùng default 3.12 và đánh dấu `inferred=true`.

### 7.2. Dependency Plan chuẩn hóa

- [x] Tạo `DependencyPlan` mô tả manifest, lock, groups, extras, index references và install target.
- [x] Quy định/test priority giữa explicit lock, `uv.lock`, Poetry lock, requirements, `pyproject.toml`, `setup.cfg` và `setup.py`.
- [x] Không cộng dồn mọi requirements file mặc định; selected source là duy nhất.
- [x] Không tự động bật `--all-groups` hoặc `--all-extras`; chỉ auto-select group `test` nếu tồn tại.
- [x] Tôn trọng supported lock file và group/extra được settings chọn rõ ràng.
- [x] Không đưa package từ `RUNTIME_TOOL_PACKAGES` của optimizer vào plan.
- [x] Không có hoặc thực thi `install_command` dạng shell tự do; requirements directives/direct URLs bị reject.
- [x] Validate package-index reference không chứa URL/credential/assignment; chỉ fingerprint identifier.
- [x] Dependency Plan canonical hóa bằng stable JSON và SHA-256 content digests.

### Tiêu chí hoàn thành giai đoạn 2

- [x] Plan cùng input/content ở project roots khác nhau tạo cùng fingerprint.
- [x] Thay đổi lock content, group/extra, Python hoặc install target làm fingerprint đổi.
- [x] Dependency/dev/docs/release files hoặc groups không liên quan không được chọn mặc định.
- [x] Lỗi metadata có error code và file/field source cụ thể trong diagnostic.

---

## 8. Giai đoạn 3 — Sandbox Builder và cache artifact

### 8.1. Python images

- [x] Build base image Python 3.12 trước.
- [x] Base image chỉ chứa sandbox agent tối thiểu, không chứa CoverUp/GEPA/LLM SDK.
- [x] Pin image bằng digest khi tạo fingerprint.
- [ ] Chạy image contract test trong CI.
- [x] Sau khi 3.12 ổn định, build matrix 3.10, 3.11 và 3.13.

### 8.2. Build environment artifact

- [x] Build trong workspace tạm.
- [x] Cho phép network chỉ trong bước resolve/install theo policy.
- [x] Dùng đúng Python image đã route.
- [x] Cài dependency đúng Dependency Plan.
- [x] Chạy package consistency check.
- [x] Ghi resolved package inventory và hash vào metadata.
- [x] Chỉ publish artifact/cache sau khi build hoàn tất.
- [x] Build fail không ghi đè artifact tốt đang tồn tại.

### 8.3. Cache

- [x] Cache key dùng environment fingerprint.
- [x] Có lock chống hai worker publish cùng key.
- [x] Có TTL/quota/garbage collection.
- [x] Cache corruption được phát hiện và rebuild.
- [x] Cache không chứa source/secret ngoài policy.
- [x] Có metric hit/miss/build duration/corruption.

### 8.4. Error classification và retry

- [x] Phân loại incompatible Python, conflict, package missing, index auth, transient network, timeout và internal.
- [x] Chỉ retry lỗi transient với exponential backoff, jitter và tổng deadline.
- [x] Không retry conflict hoặc Python incompatible.
- [x] Error chỉ rõ manifest/package gây conflict khi resolver cung cấp được.

### Tiêu chí hoàn thành giai đoạn 3

- [x] Project isort build được sandbox dù optimizer dùng coverage version khác.
- [x] Hai project dependency mâu thuẫn tạo hai artifact độc lập.
- [x] Cache hit không chạy resolver lại.
- [x] Artifact lỗi không được publish.

---

## 9. Giai đoạn 4 — Sandbox Execution và đo coverage

### 9.1. Lifecycle và isolation

- [x] Tạo execution container mới từ environment artifact.
- [x] Source mount read-only; generated tests/artifacts dùng vùng ghi riêng.
- [x] Chặn network trong lúc chạy test.
- [x] Không mount Docker socket, host home hoặc cloud credential.
- [x] Giới hạn CPU, RAM, process, file size, output và wall-clock timeout.
- [x] Dọn execution workspace dù pass, fail hoặc timeout.

### 9.2. Test runner adapter

- [x] Sandbox agent nhận `RunSpec`, không nhận command shell tùy ý.
- [x] Chọn project-native hoặc sandbox-managed profile theo contract đã chốt.
- [x] Hỗ trợ `conftest.py`, fixtures và plugins nằm trong Dependency Plan.
- [x] Cô lập pytest config hệ thống nhưng không vô hiệu hóa hành vi project đã được policy cho phép.
- [x] Ghi runner profile/version thực tế vào fingerprint/result.
- [x] Collection error, test failure và internal runner error có error code khác nhau.

### 9.3. Coverage

- [x] Dùng coverage config do evaluation contract kiểm soát cho scoring.
- [x] Không để project `fail_under` quyết định admission.
- [x] Vẫn cho project dùng coverage version riêng nếu profile project-native được chọn.
- [x] Chuẩn hóa output các coverage version về một `SandboxResult` schema.
- [x] Pytest exit code 0, 1 và 5 đều thử xuất coverage khi denominator còn đo được.
- [x] Exit code 1 giữ denominator nhưng covered units/score bằng 0 theo invariant.
- [x] Coverage artifact được validate source path và symbol identity trước khi trả về.

### Tiêu chí hoàn thành giai đoạn 4

- [x] Generated tests chạy được trong sandbox không có optimizer package.
- [x] Kết quả statement/branch coverage tái lập trên cùng fingerprint.
- [x] `coverage==7.10.7` của project không conflict với optimizer `7.15.2`.
- [x] Sandbox không truy cập được credential/network bị cấm.

Bằng chứng chạy Docker thật: `docs/spikes/sandbox-execution-validation.md`.

---

## 10. Giai đoạn 5 — Tích hợp optimizer và scoring

### 10.1. Evaluation flow

- [x] Optimizer gửi source identity, generated tests và `RunSpec` qua sandbox client.
- [x] Optimizer không gọi pytest/coverage project trực tiếp.
- [x] Baseline preflight chạy trong cùng environment artifact với candidate.
- [x] Cache evaluation tách theo prompt digest, evaluation digest, split, replicate và environment fingerprint.
- [x] Test workspace mỗi target vẫn cô lập theo invariant GEPA.
- [x] Final holdout chỉ chạy tại promotion gate.

### 10.2. Fingerprint gate

- [x] So sánh fingerprint trước khi tính paired baseline/candidate score.
- [x] Fingerprint mismatch làm evaluation invalid, không mặc định score 0 hoặc tiếp tục promote.
- [x] Tự chạy lại baseline khi environment thay đổi và policy cho phép.
- [x] Ghi fingerprint vào report, leaderboard và coverage artifact.

### 10.3. Nhiều project trong một environment

- [x] Mỗi project chạy sandbox riêng.
- [x] Aggregate score chỉ tính từ `SandboxResult` đã validate.
- [x] Một project fail không làm dependency environment của project khác thay đổi.
- [x] Nếu có test cross-project, yêu cầu khai báo workspace/dependency graph rõ ràng và tạo một composite sandbox riêng; không âm thầm merge venv.

### Tiêu chí hoàn thành giai đoạn 5

- [x] Baseline/candidate comparison chỉ xảy ra trên cùng fingerprint.
- [x] Invariant feedback per-symbol và micro-average vẫn đúng.
- [x] Promotion gate và baseline fallback không thay đổi ý nghĩa.
- [x] Không cần live GEPA benchmark để merge unit/integration implementation; benchmark chỉ chạy khi được duyệt chi phí.

Bằng chứng triển khai và Docker acceptance:
`docs/spikes/sandbox-optimizer-integration-validation.md`.

---

## 11. Giai đoạn 6 — API, UI và trải nghiệm upload

### 11.1. API/backend

- [x] API lưu requested, detected và resolved Python version.
- [x] API trả build/execution status tách biệt.
- [x] Runtime report bổ sung optional `failure_stage`, `error_code`, `retryable`, fingerprint và runner profile.
- [x] Có endpoint retry build cho transient failure và retry execution cho test/runtime failure.
- [x] Retry dùng lại artifact tốt khi fingerprint không đổi.
- [x] Active bundle chỉ cập nhật sau admission thành công.

### 11.2. Frontend

- [x] Settings Save/Validate có handler thật.
- [x] Upload request gửi settings đã validate.
- [x] Chỉ hiển thị Python version có image/job healthy.
- [x] Hiển thị từng stage: detect, resolve, build, test, coverage, admitted.
- [x] Conflict hiển thị package, version và manifest/project nguồn nếu có.
- [x] Phân biệt nút retry transient với lỗi cần sửa dependency.
- [x] Không khuyến nghị Retry cho conflict có tính xác định.
- [x] Không cho nhập arbitrary runtime image hoặc shell install command.

### Tiêu chí hoàn thành giai đoạn 6

- [x] Người dùng biết lỗi nằm ở metadata, build, test hay coverage.
- [x] Refresh trang vẫn giữ đúng settings và status.
- [x] Upload schema cũ mặc định 3.12 tiếp tục hoạt động.
- [x] Project reject không ảnh hưởng active bundle.

---

## 12. Giai đoạn 7 — Security hardening

- [x] Threat model cho archive extraction, dependency install và test execution.
- [x] Chặn Zip Slip, symlink escape, archive bomb và file quá lớn.
- [x] Chạy sandbox bằng non-root user.
- [x] Read-only root filesystem khi execution cho phép.
- [x] Seccomp/capability policy tối thiểu.
- [x] Egress deny mặc định ở execution stage.
- [ ] Dependency install chỉ truy cập registry/index allowlist.
- [ ] Secret truyền bằng reference ngắn hạn, không bake vào image/cache.
- [x] Log redaction cho token, URL credential và environment variables.
- [x] Giới hạn subprocess/fork bomb, disk và output.
- [ ] Artifact được kiểm tra ownership/path trước publish/download.
- [ ] Có audit log cho build, execution, retry, activation và rollback.

### Tiêu chí hoàn thành giai đoạn 7

- [x] Security tests chứng minh sandbox không đọc host/credential ngoài scope.
- [x] Network policy được test, không chỉ cấu hình trên giấy.
- [ ] Không có secret trong image layer, cache metadata hoặc log fixture.

---

## 13. Giai đoạn 8 — CI, kiểm thử và quality gates

### 13.1. Unit/contract tests

- [x] Metadata parser và source priority.
- [x] Dependency Plan canonicalization/fingerprint.
- [x] SandboxSpec/RunSpec/SandboxResult compatibility.
- [x] Error classification/retry policy.
- [x] Cache atomic publish/invalidation.
- [x] Fingerprint scoring gate.
- [x] Bundle activation atomicity.
- [x] Frontend state và error mapping.

### 13.2. Docker integration matrix

- [ ] Build sandbox image trong CI.
- [x] Upload/extract ZIP thật.
- [x] Build environment artifact xuyên suốt.
- [x] Chạy baseline và generated test trong hai execution riêng.
- [x] Test project/tool coverage-version conflict.
- [ ] Test two-project dependency conflict nhưng sandbox độc lập.
- [ ] Test no-tests, fail-under, setup-only và incompatible Python.
- [x] Test cache hit và cache corruption recovery.
- [ ] Test timeout, output limit và network denial.
- [ ] Sau Release Python 3.12, mở matrix 3.10–3.13.

### 13.3. Lệnh kiểm tra bắt buộc sau khi sửa code

- [x] `.\.venv\Scripts\python.exe -m pytest tests -q`
- [x] `.\.venv\Scripts\ruff.exe check src\optimization tests\test_coverage_optimization.py`
- [x] `python -m py_compile src\coverup\coverup.py src\optimization\gepa.py src\optimization\metrics.py src\optimization\cli.py src\optimization\runner.py src\optimization\prompts.py src\optimization\subprocesses.py`
- [x] Backend tests liên quan upload/runtime/sandbox.
- [x] Frontend tests liên quan upload/settings/status.
- [x] `git diff --check`
- [x] Không chạy live/full GEPA benchmark khi chưa có xác nhận chi phí.

### Tiêu chí hoàn thành giai đoạn 8

- [ ] Tất cả quality gates pass.
- [x] Không skip test để làm CI xanh nếu không có ticket/rationale.
- [x] Docker integration artifacts được lưu để điều tra failure.
- [x] Review xác nhận mọi invariant trong `AGENTS.md` còn được bảo vệ.

---

## 14. Giai đoạn 9 — Migration và rollout

### 14.1. Migration khỏi shared venv

- [x] Thêm feature flag `project_sandbox_v2`.
- [x] Dual-read report protocol cũ/mới trong giai đoạn chuyển tiếp.
- [x] Shadow build sandbox mới cho project nội bộ, chưa dùng kết quả để activate.
- [ ] So sánh kết quả cũ/mới trên fixture và project đại diện.
- [x] Không migrate cache shared venv sang sandbox cache.
- [x] Giữ active bundle hiện tại trong toàn bộ migration.
- [x] Cho phép rollback về executor cũ trong cửa sổ rollout.

### 14.2. Thứ tự rollout

- [ ] Deploy sandbox images/agent.
- [ ] Deploy orchestrator và artifact cache.
- [ ] Deploy backend sandbox client/report handling.
- [ ] Bật shadow mode.
- [ ] Bật canary Python 3.12 cho project mới.
- [ ] Bật Python 3.12 cho toàn bộ upload sau khi metric ổn định.
- [ ] Sau đó lần lượt bật Python 3.11, 3.10 và 3.13 khi từng image đạt contract tests.
- [ ] UI advertise version sau cùng.

### 14.3. Metrics và alert

- [ ] Admission success/reject rate theo Python/version/image.
- [ ] Build/execution failure theo stage/error code.
- [ ] Resolve, build, collect, test và coverage duration percentile.
- [ ] Cache hit/miss/corruption.
- [ ] Retry count và transient recovery rate.
- [ ] Fingerprint mismatch/rebaseline count.
- [ ] Sandbox security-policy violation.
- [x] Active bundle activation/rollback count.

### 14.4. Rollback

- [ ] Tắt UI advertise/version routing mới.
- [ ] Tắt `project_sandbox_v2` cho upload mới.
- [x] Không xóa environment artifact hoặc bundle trong lúc rollback.
- [ ] Giữ worker/image cũ suốt rollback window.
- [x] Xác minh protocol cũ vẫn đọc được.
- [x] Có runbook và owner cho rollback drill.

### Tiêu chí hoàn thành giai đoạn 9

- [ ] Canary ổn định trong cửa sổ theo dõi đã thống nhất.
- [ ] Python 3.12 không tăng reject rate so với baseline.
- [ ] Rollback drill không làm mất project/bundle/artifact đang active.
- [ ] Chỉ gỡ executor cũ sau khi protocol usage về ngưỡng đã thống nhất.

---

## 15. Thứ tự PR đề xuất

- [ ] PR 1: ADR, protocol schemas và characterization fixtures.
- [ ] PR 2: Metadata detection, Dependency Plan và fingerprint.
- [ ] PR 3: Sandbox agent/base image Python 3.12 và contract tests.
- [ ] PR 4: Environment builder, atomic artifact cache và error classification.
- [ ] PR 5: Sandbox execution, runner profiles và normalized coverage result.
- [ ] PR 6: Optimizer sandbox client, fingerprint gate và evaluation cache integration.
- [ ] PR 7: Backend API/report/status và atomic admission flow.
- [ ] PR 8: Frontend settings, progress stages và actionable errors.
- [ ] PR 9: Security hardening và Docker integration gates.
- [ ] PR 10: Shadow/canary rollout Python 3.12.
- [ ] PR 11: Python image/job matrix 3.10, 3.11 và 3.13.
- [ ] PR 12: Migration cleanup sau rollback window.

Mỗi PR phải rollback độc lập, không trộn refactor không liên quan và không tự động chạy live GEPA benchmark.

## 16. Checklist nghiệm thu cuối cùng

- [ ] Optimizer `coverage==7.15.2` và project `coverage==7.10.7` cùng tồn tại nhưng không resolve chung.
- [ ] Hai project có dependency mâu thuẫn vẫn được build/chạy trong sandbox riêng.
- [ ] Project Python 3.12 hiện hữu upload, validate và activate thành công.
- [ ] Project no-tests có zero coverage với denominator hợp lệ.
- [ ] `fail_under` của project không làm admission fail sai.
- [ ] Lock file/group/extra của project được tôn trọng theo Dependency Plan.
- [ ] Baseline và candidate chỉ được so trên cùng fingerprint.
- [ ] Fingerprint thay đổi kích hoạt rebaseline hoặc dừng comparison rõ ràng.
- [ ] Generated tests chạy trong sandbox không có optimizer/LLM credential.
- [ ] Network bị chặn khi chạy test.
- [ ] Lỗi transient được retry; conflict không bị retry vô ích.
- [ ] Mỗi Python version được quảng bá có image và integration test tương ứng.
- [ ] Một sandbox thất bại không thay đổi active bundle hoặc project khác.
- [ ] Protocol cũ vẫn dùng được trong migration window.
- [ ] Không regression ở GEPA search, scoring, holdout và promotion gate.
- [ ] Unit, contract, Docker integration, backend, frontend, Ruff, py_compile và diff checks pass.
- [ ] Dashboard, alert và rollback runbook sẵn sàng trước production rollout.

## 17. Các câu hỏi phải chốt trước PR triển khai đầu tiên

- [ ] Project-native runner hỗ trợ tối thiểu những phiên bản pytest/coverage nào?
- [ ] Khi project không khai báo test tooling, sandbox-managed runner dùng version/policy nào?
- [ ] Test dependency group được auto-detect hay bắt buộc người dùng chọn?
- [ ] Source được cài vào artifact hay mount lúc execution; ảnh hưởng fingerprint/cache ra sao?
- [ ] Có yêu cầu test cross-project thực tế hay mọi project hoàn toàn độc lập?
- [ ] Registry/index nào được allowlist và credential được cấp bằng cơ chế nào?
- [ ] Retention/quota của environment artifact và result artifact là bao lâu?
- [ ] Ngưỡng metric nào dừng rollout hoặc kích hoạt rollback?

## 18. Nhật ký hoàn thành

| Ngày | Task/PR | Người thực hiện | Bằng chứng | Ghi chú/rủi ro còn lại |
|---|---|---|---|---|
| 2026-08-28 | Giai đoạn 9 — Migration/rollout controls (đợt local) | Codex | [Rollout runbook](runbooks/project-sandbox-v2-rollout.md), `app/backend/modules/projects/rollout.py`, `app/tests/test_runtime_rollout.py` | Feature flag, dual-read v8/v1, shadow legacy-only activation, deterministic canary, metrics endpoint và non-destructive rollback pass local. Deploy, observation window, representative-project comparison và production rollback drill vẫn cần operator thực hiện. |
| 2026-08-28 | Giai đoạn 8 — CI quality gates (đợt local) | Codex | [CI validation](spikes/sandbox-ci-quality-gates.md), [Docker acceptance](../eval/sandbox_phase8_current/acceptance-summary.json), `.github/workflows/ci.yml` | Docker Python 3.12 E2E pass cho upload/build/baseline/candidate/cache corruption recovery; root 256 pass/1 expected-red, backend 84 pass. Remote CI và ba nhóm Docker edge-case còn mở nên chưa tuyên bố hoàn tất Giai đoạn 8. |
| 2026-08-28 | Giai đoạn 7 — Security hardening (đợt local) | Codex | [Threat model](security/project-sandbox-threat-model.md), `tests/test_sandbox_security.py`, `tests/test_runtime_workspace.py`, `tests/test_sandbox_execution.py` | Archive validation, diagnostic redaction, actionable network-denied classification và audit state events đã thêm. Sandbox suite 61 pass; backend 84 pass; full regression 256 pass/1 expected-red. Bốn control hạ tầng và secret-scan acceptance còn mở nên chưa tuyên bố hoàn tất Giai đoạn 7. |
| 2026-08-27 | Hoàn thành Giai đoạn 6 — API/UI upload | Codex | [API/UI validation](spikes/sandbox-api-ui-validation.md), `app/tests/test_runtime_preparation.py`, `app/frontend/src/pages/ProjectDetail.test.tsx` | Backend app 75 pass/1 baseline fixture fail trước hai retry tests mới; targeted cuối 13 pass/1 baseline deselected. Frontend 53/53 pass, lint/typecheck/build pass. Execution retry tái sử dụng immutable artifact và từ chối fingerprint stale. Docker không cần cho các kiểm tra này. |
| 2026-08-27 | Hoàn thành Giai đoạn 5 | Codex | [Optimizer sandbox validation](spikes/sandbox-optimizer-integration-validation.md), [acceptance result](../eval/sandbox_phase5_integration/acceptance-summary.json), [tests](../tests/test_optimizer_sandbox.py) | Docker acceptance 2/2 test pass bằng project-native coverage 7.10.7; cache schema 15 và paired fingerprint gate pass. Không chạy live GEPA benchmark; remote CI vẫn mở. |
| 2026-08-27 | Hoàn thành Giai đoạn 4 | Codex | [Execution validation](spikes/sandbox-execution-validation.md), [acceptance result](../eval/sandbox_phase4_integration/results/acceptance-summary.json) | Native/managed/repeat Docker pass; isolation, resource limits, normalized coverage và credential/network denial đã xác nhận local. |
| 2026-08-26 | Docker integration Giai đoạn 3 | Codex | [Integration result](../eval/sandbox_phase3_isort/integration-result.json), [Builder/cache report](spikes/sandbox-builder-cache.md) | Local matrix 3.10–3.13 contract-pass; isort giữ coverage 7.10.7 dù runner là 7.15.2; cache hit pass với `--network none`; sandbox 100 pass/1 expected-red và regression còn lại 223 pass/1 expected-red. Remote CI run còn mở. |
| 2026-08-26 | Triển khai code Giai đoạn 3 | Codex | [Builder/cache report](spikes/sandbox-builder-cache.md), [tests](../tests/test_sandbox_builder.py) | Unit/contract code hoàn tất; Docker integration sau đó phát hiện và đã sửa uv stderr inventory cùng Python 3.10 tomli fallback. |
| 2026-08-26 | Hoàn thành Giai đoạn 2 | Codex | [Metadata/DependencyPlan report](spikes/sandbox-dependency-plan.md), [tests](../tests/test_sandbox_dependency_plan.py) | 40 targeted tests pass; toàn bộ sandbox suites 77 pass/1 expected-red; production v8 chưa import planner. |
| 2026-08-26 | Hoàn thành Giai đoạn 1 | Codex | [Characterization report](spikes/sandbox-characterization.md), [fixture catalog](../tests/fixtures/sandbox_projects.json) | 15 pass, 1 strict xfail cho lỗi `fail_under`; builder/Dependency Plan production vẫn thuộc Giai đoạn 2–4. |
| 2026-08-26 | Hoàn thành Giai đoạn 0 | Codex | [ADR review](adr/README.md), [Protocol v1](contracts/project-sandbox-protocol-v1.md), [Runner spike](spikes/sandbox-runner-compatibility.md) | 22 targeted tests pass; full fallback suite còn 4 lỗi môi trường/baseline được ghi trong ADR review. |
| 2026-08-26 | Giai đoạn 0 / ADR 0001 | Codex | [ADR 0001](adr/0001-separate-optimizer-and-project-sandbox.md) | Chốt dependency/trust boundary; runner strategy và artifact granularity còn ở ADR tiếp theo. |
| _YYYY-MM-DD_ | _Ví dụ: PR 1_ | _Tên_ | _Link commit/CI/artifact_ | _Kết quả_ |
