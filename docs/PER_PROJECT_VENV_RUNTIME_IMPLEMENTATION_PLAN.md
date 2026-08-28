# Kế hoạch hoàn thiện runtime venv riêng cho từng project

## 1. Trạng thái và quyết định kiến trúc

Tài liệu này mô tả hướng hoàn thiện runtime cho project upload trên nhánh
`fix/import-project-v3`, đồng thời ghi rõ phần nào đã có, phần nào cần giữ,
phần nào cần thay đổi và tiêu chí nghiệm thu trước khi deploy.

Quyết định kiến trúc:

1. Mỗi project upload có một venv riêng. Không project nào resolve hoặc dùng
   chung dependency environment với project khác.
2. GEPA/DSPy tiếp tục chạy như control plane: quản lý candidate prompt,
   reflection, search, cache, score aggregation và promotion gate.
3. CoverUp có thể chạy orchestration trong worker tool environment, nhưng mọi
   thao tác import project, pytest, SlipCover, coverage và diagnostic test phải
   dùng interpreter của venv thuộc đúng project.
4. Dùng một generic immutable worker image/job cho mỗi Python minor được hỗ trợ,
   ví dụ Python 3.10, 3.11, 3.12 và 3.13.
5. Runtime riêng của project được lưu dưới dạng content-addressed source archive
   và venv bundle có SHA-256, không bắt buộc tạo OCI image hoặc Cloud Run Job
   riêng cho từng project.
6. Project-specific OCI image/job chỉ là chế độ nâng cao trong tương lai cho
   project cần OS dependency riêng hoặc yêu cầu compliance/isolation đặc biệt;
   không phải đường chạy mặc định.

Phân biệt hai khái niệm:

- **Immutable worker**: image chứa code PromptOpt/CoverUp và được pin bằng image
  digest. Worker này có thể dùng chung cho nhiều project cùng Python minor.
- **Immutable project runtime**: source ZIP, venv bundle, dependency fingerprint,
  Python version và checksum cố định của một project. Runtime không dùng chung
  với project khác dù worker image được dùng chung.

## 2. Vì sao chọn generic worker + per-project venv

Per-project venv giải quyết trực tiếp các vấn đề cần xử lý:

- Hai project yêu cầu hai version khác nhau của cùng dependency.
- Hai project dùng Python minor khác nhau.
- Dependency của project này không làm project khác bị `runtime_failed`.
- Baseline và candidate của cùng project luôn được chấm bằng cùng runtime.
- Diagnostic test của reflection và final generated suite chạy trong đúng môi
  trường đã admission.

Không cần project-specific image để đạt các invariant trên. Cloud Run Job tạo
mỗi execution trong container/filesystem tạm độc lập. Generic worker có thể tải,
kiểm tra checksum và giải nén một runtime bundle khác nhau cho mỗi execution.

Project-specific image/job mặc định gây thêm chi phí:

- Mỗi upload hoặc rebuild phải chạy Cloud Build.
- Tăng số image, Cloud Run Job, IAM binding và quota cần quản lý.
- Phải dọn image/job cũ khi project bị xóa hoặc runtime được rebuild.
- Upload có thể fail do Cloud Build, Artifact Registry hoặc factory IAM dù venv
  đã được chuẩn bị thành công.
- Source riêng tư bị lưu thêm một bản trong Artifact Registry.
- Implementation hiện tại vẫn copy `runtime.tar.gz` vào image rồi giải nén khi
  execution bắt đầu; image riêng không loại bỏ bước restore venv.

## 3. Kiến trúc đích

### 3.1 Upload và runtime preparation

```text
Browser upload ZIP
        |
        v
Static analysis (không import/execute source)
        |
        v
Select preparer theo Python minor
        |
        v
Isolated runtime preparation job, đúng một project
        |
        +-- safe extract ZIP
        +-- detect source/test layout
        +-- validate requires-python
        +-- create venv riêng
        +-- resolve project dependencies
        +-- install pytest/coverage/SlipCover toolchain
        +-- pip/uv check
        +-- bounded admission diagnostics
        |
        v
Seal project runtime
        |
        +-- source archive SHA-256
        +-- runtime bundle SHA-256
        +-- dependency fingerprint
        +-- runtime digest
        +-- Python version
        +-- pinned generic worker image/job identity
        |
        v
Project runtime_ready
```

Dependency installation chỉ diễn ra khi upload, thay đổi settings hoặc rebuild
runtime. GEPA không được chạy `pip install` lại cho mỗi candidate/replicate.

### 3.2 GEPA optimization

```text
GEPA/DSPy coordinator
        |
        +-- candidate prompt
        +-- project + source_file + symbol + split
        +-- evaluation config
        |
        v
RemoteEvaluationBackend groups targets by project
        |
        +--> generic worker py310 + runtime project A
        +--> generic worker py312 + runtime project B
        +--> generic worker py313 + runtime project C
        |
        v
Per-project worker execution
        |
        +-- verify worker image/job identity
        +-- download source/runtime objects
        +-- verify object generation/checksums
        +-- restore venv in isolated workspace
        +-- CoverUp generates tests
        +-- project venv runs pytest/coverage
        |
        v
Per-symbol score + feedback + coverage + attempt traces
        |
        v
GEPA reflection/search/promotion
```

Coordinator được phép đọc immutable source snapshot để tạo numbered source
context. Coordinator không được import project hoặc chạy test của project.

### 3.3 Diagnostic reflection test

```text
Reflection LM writes diagnostic pytest module
        |
        v
run_test_experiment request for one project/symbol
        |
        v
Generic worker restores that project's venv
        |
        v
pytest + coverage in project venv
        |
        v
Result returned to reflection LM
```

Diagnostic test là teacher evidence. Nó không được copy vào candidate workspace
và không được dùng trực tiếp làm GEPA candidate score.

### 3.4 Final test-suite generation

```text
Immutable prompt snapshot
        |
        v
Targets grouped by project
        |
        v
CoverUp final_generation on each project's worker execution
        |
        +-- generated tests run in project venv
        +-- project coverage measured in project venv
        +-- generated tests + coverage + manifest archived
        |
        v
Artifacts uploaded and merged by coordinator
```

Final generated tests không cần được bake vào worker image. Container image là
read-only base layer nhưng Cloud Run execution vẫn có writable ephemeral
workspace. Test artifacts phải được upload trước khi execution kết thúc.

## 4. Phần nhánh hiện tại đã làm và cần giữ

| Hạng mục | Trạng thái | File chính | Hành động |
| --- | --- | --- | --- |
| Một runtime preparation chỉ nhận đúng một project | Đã làm | `cloud/runtime_workspace.py`, `app/backend/modules/projects/runtime.py` | Giữ invariant và test |
| Chọn preparer theo Python 3.10-3.13 | Đã làm | `app/backend/config.py`, `app/backend/modules/projects/runtime.py` | Giữ |
| Detect `src`, `lib`, `python` và package layout | Đã làm | `cloud/runtime_workspace.py` | Giữ và bổ sung fixture |
| Đọc `uv.lock`, `pyproject.toml`, requirements và legacy static metadata | Đã làm | `cloud/runtime_workspace.py` | Giữ, mở rộng có kiểm soát |
| Cài pytest, pytest plugins, coverage và SlipCover vào project runtime | Đã làm | `cloud/runtime_workspace.py` | Giữ, pin/version digest đầy đủ |
| Upstream test collection/failure là diagnostic | Đã làm | `cloud/runtime_workspace.py` | Giữ |
| Zero baseline fallback khi upstream suite không dùng được | Đã làm | `cloud/runtime_workspace.py` | Giữ |
| Runtime bundle, source hash, bundle hash và runtime digest | Đã làm | `cloud/prepare_runtime.py`, `cloud/runtime_workspace.py` | Giữ và chuyển object sang content-addressed path |
| `ProjectLayout.python_executable` | Đã làm | `src/optimization/models.py` | Giữ |
| `TESTGEN_PYTHON` cho pytest/coverage/import checks | Đã làm | `src/optimization/runner.py`, `src/optimization/coveragepy.py`, `src/coverup/testrunner.py`, `src/coverup/coverup.py` | Audit để không còn đường chạy sai interpreter |
| `EvaluationBackend` tách GEPA khỏi execution | Đã làm | `src/optimization/models.py`, `src/optimization/runner.py` | Giữ |
| Remote evaluation group target theo project | Đã làm | `cloud/evaluation_dispatcher.py` | Giữ |
| Remote diagnostic test | Đã làm | `cloud/evaluation_dispatcher.py`, `cloud/run_evaluation_worker.py` | Giữ |
| Remote final generation theo project | Đã làm | `cloud/run_test_generation.py`, `cloud/run_evaluation_worker.py` | Giữ |
| Request identity/cache có runtime digest và config | Đã làm | `cloud/evaluation_dispatcher.py` | Giữ và thêm generic worker digest |
| Hash/image/job validation trước execution | Đã làm | `cloud/run_evaluation_worker.py` | Giữ, điều chỉnh cho generic worker |
| Checkpoint/pause-resume qua GCS | Đã làm | `cloud/evaluation_dispatcher.py`, `cloud/run_evaluation_worker.py` | Giữ |
| Bỏ constraint mọi project trong experiment phải cùng environment | Đã làm | `app/backend/modules/experiments/service.py` | Giữ |

## 5. Phần hiện tại cần thay đổi

### 5.1 Không bắt buộc runtime image factory

Hiện tại backend đi theo chuỗi:

```text
prepare venv bundle
  -> start trusted runtime image factory
  -> Cloud Build project-specific image
  -> create project-specific Cloud Run Job
  -> accept protocol 12
```

Cần đổi đường mặc định thành:

```text
prepare venv bundle
  -> seal content-addressed runtime manifest
  -> attach pinned generic worker identity for Python minor
  -> accept runtime
```

Việc cần làm:

- Cho `RuntimePreparationService` accept một complete generic runtime report mà
  không gọi `CloudRunRuntimeImageFactory`.
- Bỏ điều kiện factory phải trả image/job khác generic preparation worker.
- Không yêu cầu `runtime_factory_prefix` cho runtime mới.
- Chuyển factory thành optional feature flag trong giai đoạn migration.
- Sau khi generic path ổn định, xóa factory job, service account và IAM không còn
  cần thiết.

### 5.2 Không tái sử dụng semantic của protocol 12

Protocol 11 hiện đại diện prepared venv capsule. Protocol 12 hiện đại diện
project-specific OCI image/job. Không nên đổi ý nghĩa protocol 12 tại chỗ vì
artifact/cache cũ có thể bị hiểu sai.

Khuyến nghị tạo protocol mới, ví dụ protocol 13:

```text
protocol 13 = content-addressed project venv + pinned generic worker identity
```

Protocol mới phải có execution mode rõ ràng, ví dụ:

```json
{
  "runtime_protocol_version": 13,
  "execution_mode": "generic_worker_bundle"
}
```

Trong rollout:

- Worker có thể dual-read protocol 12 và 13.
- API mới chỉ emit protocol 13.
- Project protocol 12 có thể tiếp tục chạy trong thời gian migration hoặc bị
  yêu cầu rebuild tùy môi trường chưa deploy production.
- Cache/evaluation digest phải bao gồm protocol và execution mode.

### 5.3 Thay project-specific worker identity bằng generic worker identity

Runtime snapshot vẫn cần lưu worker identity để pause/resume không đổi toolchain,
nhưng identity sẽ thuộc deployment/Python version, không thuộc project.

Manifest đề xuất:

```json
{
  "schema_version": 3,
  "projects": [
    {
      "kind": "uploaded",
      "project": "runner-project-name",
      "python_version": "3.12",
      "source_directory": "src",
      "test_directory": "tests",
      "archive_object": "project-runtimes/<source-sha>/source.zip",
      "archive_generation": "gcs-object-generation",
      "source_archive_sha256": "...",
      "runtime_bundle_object": "project-runtimes/<runtime-sha>/runtime.tar.gz",
      "runtime_bundle_generation": "gcs-object-generation",
      "runtime_bundle_sha256": "...",
      "dependency_fingerprint": "...",
      "runtime_digest": "...",
      "runtime_protocol_version": 13,
      "execution_mode": "generic_worker_bundle",
      "worker_image": ".../runtime-py312@sha256:...",
      "worker_job": "projects/.../jobs/promptopt-evaluation-py312-<deploy-version>"
    }
  ]
}
```

`runtime_digest` phải hash ít nhất:

- Runtime protocol và execution mode.
- Source archive SHA-256.
- Runtime bundle SHA-256.
- Python major/minor và, nếu cần, patch version.
- Dependency/tool package versions.
- Generic worker image digest.
- Source/test layout.
- Các evaluation-relevant project settings.

Cloud Run Job name có thể versioned theo deployment SHA. Không được resume một
run bằng worker deployment khác nếu execution manifest đã khóa worker cũ.

### 5.4 Generic worker selection

`RemoteEvaluationBackend._job_for()` cần ưu tiên worker identity đã pin trong
execution manifest và xác nhận worker tương ứng với `python_version`.

Không lấy một mutable job alias rồi giả định image bên dưới chưa đổi. Có hai cách
hợp lệ:

1. Deploy job có version trong tên và giữ job cũ cho các run đang resume.
2. Lưu image digest trong manifest và xác nhận job execution thực tế đang dùng
   đúng digest trước khi chạy.

Khuyến nghị dùng cả hai.

### 5.5 Worker restore path và tính relocatable của venv

Venv hiện được tạo ở một absolute path rồi giải nén sang workspace tạm khác.
`python -m pytest` thường hoạt động, nhưng entry-point scripts trong `venv/bin`
có thể giữ shebang trỏ về path cũ.

Cần chọn và test một chiến lược:

- Ưu tiên: tạo và restore venv ở cùng absolute path cố định bên trong mỗi
  container execution, ví dụ `/tmp/promptopt-runtime/<runtime-digest>/.venv`.
- Hoặc rewrite entry-point shebang sau restore.
- Luôn set `VIRTUAL_ENV` và prepend đúng `venv/bin` vào `PATH`.
- Tiếp tục set `TESTGEN_PYTHON` bằng absolute path đã verify.
- Không dựa vào activation shell script.

Cần có test project gọi một console script dependency qua `subprocess` để phát
hiện regression path/PATH.

### 5.6 Audit toàn bộ project-code execution

Mọi đường chạy dưới đây phải dùng project interpreter:

- Initial coverage measurement của CoverUp.
- Generated test validation bằng SlipCover.
- Error-repair attempt.
- Missing-coverage attempt.
- Final coverage.py scoring.
- `run_test_experiment` của reflection.
- Final test-suite generation và final project coverage.
- Import availability/preflight.
- Bất kỳ subprocess nào do project test gọi qua console entry point.

CoverUp parent process có thể dùng worker base interpreter nếu nó chỉ parse source,
gọi model và điều phối. Parent process không được import package của project.

### 5.7 Dependency settings và package index

Hiện schema có các field như `install_command`, `requirements_file`, `lock_file`,
`extra_package_index` và `network_access`, nhưng runtime preparation chưa dùng
đầy đủ.

Cần quyết định contract an toàn:

- Hỗ trợ explicit relative `requirements_file` và `lock_file` sau khi validate
  path không thoát project root.
- Hỗ trợ PEP 621 `pyproject.toml`, `uv.lock` và các requirements file hiện tại.
- Không chạy arbitrary `install_command` từ người dùng trong trusted API/factory.
- Nếu hỗ trợ custom command, chỉ chạy trong untrusted preparer với command policy,
  timeout, output limit và network policy rõ ràng.
- Private index credential phải đi qua Secret Manager/reference; không ghi URL có
  credential vào artifact, log hoặc Firestore.
- Evaluation worker mặc định không được `pip install` thêm package trong GEPA run.
- Dependency resolution failure phải trả diagnostic đầu tiên có ý nghĩa, không
  chỉ trả wrapper `runtime_failed`.

### 5.8 Content-addressed storage và lifecycle

Source/runtime object nên được lưu theo digest, không theo mutable run prefix duy
nhất:

```text
project-runtimes/sources/<source-sha256>/source.zip
project-runtimes/bundles/<runtime-bundle-sha256>/runtime.tar.gz
```

Yêu cầu:

- Upload với generation precondition để không overwrite object đã tồn tại.
- Manifest lưu cả object generation và SHA-256.
- Worker verify SHA-256 sau download và trước extract.
- Không dùng cache chỉ dựa trên project ID.
- Rebuild có cùng digest có thể reuse immutable object.
- Thiết kế reference tracking hoặc retention policy trước khi xóa object.
- Project deletion không được xóa bundle còn được experiment snapshot/run khác
  tham chiếu.

### 5.9 Project settings và runtime invalidation

Thay đổi các field sau phải làm runtime cũ stale và yêu cầu rebuild:

- Python version.
- Source directory/test directory.
- Dependency/lock manifest selection.
- Package index policy có ảnh hưởng dependency.
- Runtime tool versions.
- Worker base image digest.
- Runtime protocol.

Không nhất thiết rebuild khi chỉ đổi metadata như project display name hoặc mô
tả.

## 6. Các file cần chỉnh sửa

### Backend

- `app/backend/modules/projects/schemas.py`
  - Thêm execution mode/protocol mới.
  - Phân biệt generic worker identity với project-specific worker identity.
  - Bổ sung object generation nếu storage implementation hỗ trợ.
- `app/backend/modules/projects/runtime.py`
  - Accept generic sealed runtime ngay sau preparation.
  - Không bắt buộc start image factory.
  - Giữ factory sau feature flag trong migration rồi loại bỏ.
- `app/backend/modules/projects/service.py`
  - Giữ automatic runtime request sau analysis.
  - Bảo đảm retry tạo fresh attempt và không dùng artifact cũ sai digest.
- `app/backend/modules/experiments/schemas.py`
  - Snapshot đầy đủ runtime protocol, execution mode và worker identity.
- `app/backend/modules/experiments/service.py`
  - Gate experiment theo complete generic runtime contract.
  - Không tái thêm same-environment restriction.
- `app/backend/modules/experiments/cloud_optimizer.py`
  - Emit execution manifest schema mới.
  - Copy/reference đúng immutable runtime objects.
- `app/backend/modules/experiments/cloud_test_generator.py`
  - Dùng cùng manifest contract với optimization.
- `app/backend/services/container.py`
  - Factory optional trong migration; sau đó bỏ wiring và config thừa.
- `app/backend/config.py`
  - Giữ Python-specific preparer/evaluation jobs.
  - Deprecate factory job/image repository/service-account settings.

### Cloud runtime và worker

- `cloud/runtime_workspace.py`
  - Giữ single-project preparation.
  - Hoàn thiện relocatable/fixed-path venv.
  - Audit dependency selection/settings.
- `cloud/prepare_runtime.py`
  - Publish sealed generic runtime report/protocol mới.
  - Upload content-addressed bundle với checksum/generation.
- `cloud/run_evaluation_worker.py`
  - Generic worker restore source/runtime bundle.
  - Verify protocol, execution mode, Python, worker digest, object generation và
    checksums.
  - Set `TESTGEN_PYTHON`, `VIRTUAL_ENV`, `PATH` chính xác.
- `cloud/evaluation_dispatcher.py`
  - Resolve generic versioned job theo project snapshot.
  - Giữ project-grouped dispatch, durable result và checkpoint.
- `cloud/run_job.py`
  - Stage source context cho coordinator nhưng không restore project runtime.
  - Pin execution manifest khi bắt đầu/resume.
- `cloud/run_test_generation.py`
  - Dùng cùng generic worker backend cho final generation.
- `cloud/Dockerfile.runtime`
  - Tiếp tục là generic worker/preparer image theo Python minor.
  - Pin đầy đủ tool dependencies cần bởi outer CoverUp process và venv runtime.
- `cloud/runtime_image_factory.py`
- `cloud/Dockerfile.runtime-factory`
  - Giữ tạm sau feature flag trong migration, sau đó xóa nếu không còn enhanced mode.

### Optimization/CoverUp

- `src/optimization/models.py`
  - Giữ per-project interpreter/runtime digest contract.
- `src/optimization/runner.py`
  - Audit không có pytest/coverage project path nào fallback nhầm sang
    `sys.executable` khi project runtime đã được khai báo.
- `src/optimization/coveragepy.py`
  - Giữ project interpreter là authoritative.
- `src/optimization/project_setup.py`
  - Import preflight dùng project interpreter.
- `src/coverup/testrunner.py`
  - Test/coverage bằng project interpreter.
- `src/coverup/coverup.py`
  - Import availability dùng project interpreter.
  - Không bật dynamic `--install-missing-modules` trong evaluation mặc định.
- `src/optimization/gepa.py`
  - Không cần thay search logic nếu `EvaluationBackend` contract không đổi.
  - Giữ diagnostic experiment chạy qua backend đúng project.

### Deployment

- `.github/workflows/backend-deploy.yml`
  - Deploy generic immutable evaluation worker trước coordinator/API.
  - Giữ versioned worker job cho mỗi Python minor.
  - Bỏ deploy runtime factory sau migration.
- `app/infra/provision-production.ps1`
- `app/infra/provision-production-runner.ps1`
  - Loại bỏ factory/builder service accounts và roles không còn dùng.
  - Giữ least-privilege preparer và evaluation worker accounts.
- `app/infra/cloud-run-env.yaml`
- `app/infra/cloud-run-env.dev.yaml`
  - Cập nhật generic worker names/protocol.
  - Gỡ factory settings sau migration.

### UI và tài liệu, có thể làm sau backend/cloud

- `app/frontend/src/pages/Projects.tsx`
  - Bỏ mô tả “resolved together” hoặc shared environment.
  - Hiển thị mỗi project có runtime riêng.
- `app/frontend/src/pages/ProjectDetail.tsx`
  - Đổi thông báo rejection không nói active shared bundle.
  - Nối thực sự settings form với backend nếu giữ các controls dependency/runtime.
- `app/frontend/src/pages/CreateExperiment.tsx`
  - Không yêu cầu project cùng environment.
- `app/Readme.md`, `docs/architecture_diagram.md`, `docs/GEPA_CURRENT_FLOW.md`
  - Cập nhật kiến trúc sau khi implementation ổn định.

## 7. Phần nên xóa hoặc deprecate

Chỉ xóa sau khi protocol mới và generic worker E2E đã pass:

- Mandatory `CloudRunRuntimeImageFactory` path.
- Project-specific Cloud Build context/image creation.
- Project-specific Cloud Run evaluation Job creation.
- Factory/builder service accounts và IAM bindings.
- Config bắt buộc `CLOUD_RUN_RUNTIME_FACTORY_JOB`.
- Runtime gate yêu cầu project worker job phải khác generic worker job.
- Tests chỉ xác nhận project-specific image/job là invariant bắt buộc.

Nếu muốn giữ enhanced mode, isolate nó bằng enum/feature flag rõ ràng:

```text
generic_worker_bundle   # default
project_image           # optional future mode
```

Không để generic path vô tình phụ thuộc factory availability.

## 8. Security và isolation invariants

1. API/static analyzer không import hoặc execute source upload.
2. Dependency resolution có thể chạy build backend code; nó phải nằm trong
   untrusted preparer identity, không phải trusted API identity.
3. Evaluation worker chỉ có quyền đọc đúng runtime inputs cần thiết, ghi artifact
   prefix của execution và gọi model theo policy.
4. Runtime bundle không được mount trực tiếp từ gcsfuse để chạy; tải về local disk,
   verify rồi extract.
5. ZIP/tar extraction phải tiếp tục chặn traversal, link và device entry.
6. Worker không được chạy nếu Python minor, protocol, worker image/job, object
   generation hoặc checksum không khớp manifest.
7. Source và generated tests phải nằm trong workspace tạm riêng của execution.
8. Không share writable tests workspace hoặc coverage database giữa project.
9. Không log secret, credential-bearing index URL hoặc source contents ngoài
   artifact policy.
10. Generated test không được tự động cài package mới trong evaluation.
11. Timeout, output limit, pytest basetemp và cache isolation phải giữ nguyên.
12. Pause/resume phải khóa cùng runtime digest và worker deployment identity.

## 9. Test plan bắt buộc

### 9.1 Runtime workspace tests

- Hai project có dependency version xung đột vẫn prepare độc lập thành công.
- `prepare_environment()` với nhiều project bị từ chối trước dependency resolution.
- Python 3.10/3.11/3.12/3.13 được route đúng preparer.
- `requires-python` không tương thích trả diagnostic rõ.
- Source/test layout `src`, `lib`, package root và no-tests hoạt động.
- Upstream test fail, collection fail/timeout và suite quá lớn dùng diagnostic/zero
  baseline đúng invariant.
- Dependency resolution hoặc `pip check` fail làm đúng project fail, không ảnh
  hưởng project khác.
- Runtime bundle restore được ở execution mới.
- Console entry-point của dependency chạy được sau restore venv.
- `PATH`, `VIRTUAL_ENV` và `TESTGEN_PYTHON` trỏ đúng runtime.

### 9.2 Manifest/storage tests

- Runtime object path content-addressed và không overwrite digest cũ.
- Source hash mismatch bị từ chối.
- Bundle hash mismatch bị từ chối.
- GCS object generation mismatch bị từ chối.
- Runtime digest đổi khi source, dependency, Python, toolchain hoặc worker image đổi.
- Resume bằng runtime/worker identity khác bị từ chối.
- Protocol 12/13 dual-read hoạt động trong migration.

### 9.3 Evaluation worker tests

- Generic worker chọn đúng Python minor.
- Coordinator không restore venv hoặc chạy project test.
- Worker restore đúng project runtime trước CoverUp.
- CoverUp generated test chạy bằng project interpreter.
- coverage.py chạy bằng project interpreter.
- `run_test_experiment` chạy bằng project interpreter.
- Final generation chạy và đo coverage bằng project interpreter.
- Hai project chạy song song không share tests, coverage data, pytest temp hoặc
  import cache.
- Worker luôn publish terminal result hoặc paused checkpoint.

### 9.4 GEPA integration tests

- Một candidate batch chứa nhiều project được group và merge đúng target order.
- Per-symbol score/feedback không bị gán nhầm giữa project.
- Evaluation cache tách theo runtime digest, worker digest, split và replicate.
- Diagnostic experiment được gửi tới đúng project worker.
- Baseline preflight giữ denominator hợp lệ cho mọi target.
- Holdout chỉ chạy ở final promotion gate.
- Final suite artifact ghi runtime/prompt/source digests đầy đủ.

### 9.5 Cloud smoke test

Tạo tối thiểu hai fixture project:

```text
project-a: Python 3.11, dependency-X==1
project-b: Python 3.12, dependency-X==2
```

Smoke flow:

1. Upload cả hai ZIP.
2. Chờ static analysis và runtime preparation.
3. Xác nhận hai runtime digest và bundle object khác nhau.
4. Xác nhận không tạo project-specific image/job ở default mode.
5. Tạo một experiment chứa target của cả hai project.
6. Chạy baseline evaluation.
7. Chạy ít nhất một GEPA reflection iteration có diagnostic test.
8. Xác nhận log mỗi target dùng đúng Python/venv.
9. Sinh final suite cho cả hai project.
10. Tải artifact và rerun từng suite trong runtime tương ứng.
11. Xác nhận không có cross-project import hoặc dependency contamination.

## 10. Rollout và migration

### Giai đoạn 1: thêm generic protocol, chưa xóa factory

- Thêm protocol/execution mode mới.
- Worker dual-read project-image và generic-bundle manifests.
- Backend có feature flag chọn generic mode ở dev.
- Deploy versioned generic workers trước API/coordinator.
- Chạy unit/integration tests.

### Giai đoạn 2: dev E2E

- Bật generic mode trên dev.
- Upload fixture xung đột dependency/Python.
- Chạy optimization và final generation.
- Kiểm tra pause/resume.
- Theo dõi install latency, worker startup, GCS transfer và artifact size.

### Giai đoạn 3: default generic mode

- API emit generic protocol cho runtime mới.
- Existing project-specific runtime được dual-read hoặc yêu cầu rebuild.
- Không tạo image/job riêng cho project mới.
- Cập nhật UI và documentation.

### Giai đoạn 4: loại bỏ factory

- Xác nhận không còn active runtime/run phụ thuộc project-specific factory path.
- Xóa factory deployment/config/IAM/code.
- Dọn orphan project images/jobs theo danh sách đã verify.
- Không xóa source/runtime artifacts còn được experiment snapshot tham chiếu.

## 11. Tiêu chí nghiệm thu

Implementation chỉ được coi là hoàn tất khi:

- [ ] Mỗi uploaded project có runtime bundle và digest riêng.
- [ ] Không có dependency resolution nào nhận nhiều project cùng lúc.
- [ ] Default upload không gọi Cloud Build để tạo project image.
- [ ] Default upload không tạo Cloud Run Job riêng cho project.
- [ ] Generic worker image được pin digest và version theo Python minor.
- [ ] Worker verify source/bundle checksum và object generation.
- [ ] Mọi pytest/coverage/diagnostic/final-generation execution dùng đúng project
      interpreter.
- [ ] GEPA coordinator không import hoặc execute uploaded project.
- [ ] Multi-project experiment chạy được với dependency/Python khác nhau.
- [ ] Per-target score và feedback vẫn giữ đúng symbol attribution.
- [ ] Evaluation cache bao gồm project runtime và worker identity.
- [ ] Pause/resume từ chối mọi runtime identity mismatch.
- [ ] Final suite chạy pass trong runtime tương ứng và được persist ngoài ephemeral
      worker filesystem.
- [ ] Dependency/network failure trả diagnostic có thể hành động được.
- [ ] Runtime cleanup/retention không xóa artifact còn được tham chiếu.
- [ ] UI không còn mô tả shared venv/environment.
- [ ] Dev Cloud E2E pass trước khi deploy production.

## 12. Lệnh kiểm tra sau khi sửa

Chạy các lệnh bắt buộc của repository:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\ruff.exe check src\optimization tests\test_coverage_optimization.py
python -m py_compile src\coverup\coverup.py src\optimization\gepa.py src\optimization\metrics.py src\optimization\cli.py src\optimization\runner.py src\optimization\prompts.py src\optimization\subprocesses.py
git diff --check
```

Chạy backend tests tách khỏi root `tests` trên Windows để tránh import collision
giữa hai package `tests.conftest`:

```powershell
.\.venv\Scripts\python.exe -m pytest app\tests -q
.\.venv\Scripts\ruff.exe check app\backend app\tests cloud
```

Chạy riêng các test runtime/worker quan trọng:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_runtime_workspace.py `
  tests\test_evaluation_dispatcher.py `
  tests\test_evaluation_worker.py `
  tests\test_deployment_architecture.py `
  -q

.\.venv\Scripts\python.exe -m pytest app\tests\test_runtime_preparation.py -q
```

Các test runtime có thể cần tải package từ PyPI. Nếu môi trường test chặn network,
phải phân biệt network/sandbox failure với assertion failure của implementation;
Cloud dev smoke vẫn phải chứng minh preparer có egress cần thiết.

## 13. Handoff checklist

- [ ] Ghi runtime protocol/execution mode cuối cùng vào `AGENTS.md`.
- [ ] Cập nhật `docs/GEPA_CURRENT_FLOW.md` sau khi code merge.
- [ ] Cập nhật architecture diagram và deployment documentation.
- [ ] Báo rõ unit test nào đã chạy và cloud smoke nào chưa chạy.
- [ ] Không coi unit test pass là bằng chứng live Cloud Run E2E đã pass.
- [ ] Không chạy full GEPA benchmark tốn chi phí nếu chưa được yêu cầu.
- [ ] Dùng artifacts directory mới khi benchmark protocol/runtime mới.
- [ ] Giữ nguyên các invariant GEPA về baseline, per-symbol feedback, locked
      holdout, strict promotion và cache isolation.

