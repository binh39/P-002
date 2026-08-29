# ADR 0001: Tách optimizer environment và project sandbox

- Trạng thái: Accepted
- Ngày quyết định: 2026-08-26
- Phạm vi: Upload project, runtime admission và evaluation execution
- Liên quan: [Kế hoạch Project Sandbox](../UPLOAD_ENVIRONMENT_IMPLEMENTATION_PLAN.md)

## Bối cảnh

Container hiện tại đồng thời chứa CoverUp, GEPA, cloud job và runtime preparation. File [`cloud/Dockerfile.web`](../../cloud/Dockerfile.web) đồng bộ toàn bộ dependency của tool vào `/app/.venv`, sau đó dùng cùng image cho các job tối ưu, sinh test và chuẩn bị runtime.

Trong runtime admission, [`prepare_environment()`](../../cloud/runtime_workspace.py) thực hiện các việc sau trong cùng một virtual environment:

1. Nhận tất cả project đang thuộc một runtime environment.
2. Gom manifest/lock/dependency group của các project.
3. Tạo một shared virtual environment.
4. Ép thêm `RUNTIME_TOOL_PACKAGES`, gồm pytest, coverage và slipcover được pin bởi tool.
5. Dùng chính environment đó để collect test, chạy baseline và xuất coverage.
6. Đóng gói shared virtual environment thành runtime bundle.

Hành vi này thể hiện tại các điểm chính:

- `RUNTIME_TOOL_PACKAGES` pin `coverage==7.15.2` và các test tools khác.
- Runtime export tất cả lock groups hoặc thêm tất cả dependency groups/extras.
- Dependency của tất cả project và dependency của tool được đưa vào cùng một lệnh cài đặt.
- Backend gửi tất cả project ready trong environment cùng project candidate vào một lần preparation tại [`app/backend/modules/projects/runtime.py`](../../app/backend/modules/projects/runtime.py).

Sự cố thực tế với isort cho thấy resolver đồng thời nhận `coverage==7.15.2` từ tool và `coverage==7.10.7` từ project/dependency input, nên project bị reject trước khi test chạy. Retry không thể giải quyết vì đây là conflict xác định. Việc nới một pin cụ thể cũng không giải quyết conflict giữa các project hoặc các package khác trong tương lai.

Ngoài lỗi dependency, chạy code project trong môi trường chứa optimizer làm tăng phạm vi ảnh hưởng nếu project độc hại hoặc test có side effect. Sandbox không cần và không nên nhìn thấy LLM credentials, prompt artifacts, optimizer cache hoặc dependency nội bộ của tool.

## Quyết định

Tách hệ thống thành hai trust boundary và hai dependency domain độc lập:

### 1. Optimizer/Test Generator

Optimizer giữ các trách nhiệm:

- Chạy CoverUp và GEPA.
- Gọi model và quản lý prompt/search/promotion.
- Đọc source/context cần thiết để sinh test.
- Tạo test candidate và yêu cầu đánh giá bằng contract có version.
- Kiểm tra environment fingerprint trước khi so baseline với candidate.
- Tổng hợp score bên ngoài sandbox.

Optimizer không được:

- Cài dependency project vào environment của optimizer.
- Chạy pytest/coverage của project trực tiếp.
- Đưa pin từ `RUNTIME_TOOL_PACKAGES` vào Dependency Plan của project.
- Truyền LLM/cloud credentials vào project sandbox.

### 2. Project Sandbox

Project sandbox là execution boundary dùng để:

- Chạy đúng Python version đã resolve cho project.
- Cài dependency theo manifest/lock và policy của chính project.
- Nhận source revision và test files từ orchestrator.
- Collect test, chạy test và đo coverage.
- Trả kết quả có cấu trúc, bounded logs, artifacts và environment fingerprint.

Sandbox không chứa CoverUp, GEPA, LLM SDK hoặc credentials của optimizer. Một sandbox failure chỉ tạo kết quả thất bại cho evaluation tương ứng; nó không được thay đổi active bundle hoặc environment artifact đã publish.

### 3. Giao tiếp qua contract khai báo

Hai phía giao tiếp bằng request/result có version thay vì command shell tùy ý:

```text
Optimizer
  -> SandboxSpec + RunSpec + source identity + generated tests
Sandbox
  -> SandboxResult + coverage artifact + environment fingerprint
```

Contract phải có allowlist cho paths, environment variables, test selection, coverage mode và resource limits. Result phải phân biệt tối thiểu build, collection, test, coverage, timeout và internal failure.

### 4. Dependency isolation là invariant

Dependency resolver của project chỉ nhận Dependency Plan của project và dependency tối thiểu thuộc sandbox runner profile đã được quyết định riêng. Nó không được đọc `pyproject.toml`, `uv.lock` hoặc virtual environment của optimizer.

Runner/coverage có thể dùng project-native hoặc sandbox-managed profile, nhưng lựa chọn chi tiết chưa thuộc ADR này. ADR riêng và compatibility spike phải chứng minh profile được chọn không đưa optimizer dependency vào resolver của project.

### 5. Evaluation consistency

Baseline và candidate chỉ được so sánh khi cùng environment fingerprint. Nếu Python, base image, dependency plan, runner profile hoặc coverage implementation thay đổi, baseline phải được chạy lại hoặc evaluation bị đánh dấu invalid.

## Sơ đồ ranh giới

```text
Trust boundary A                         Trust boundary B

+---------------------------+           +---------------------------+
| Optimizer image           | request   | Project sandbox image     |
| - CoverUp / GEPA           |---------> | - sandbox agent           |
| - LLM SDK / credentials    |           | - project Python/deps     |
| - prompt/evaluation cache  | <---------| - test/coverage execution |
+---------------------------+  result   +---------------------------+
        no shared venv, no shared credentials, no dependency merge
```

## Hệ quả

### Tích cực

- Pin pytest/coverage của optimizer không còn conflict với project.
- Hai project có dependency mâu thuẫn có thể được đánh giá độc lập.
- Python version và dependency của project có thể tái lập bằng fingerprint.
- Giảm blast radius khi chạy code không tin cậy.
- Build dependency, test execution và scoring có lifecycle/metric riêng.
- Có thể cache environment artifact mà không cache generated tests hoặc secrets.

### Chi phí và rủi ro

- Cần sandbox orchestrator, image lifecycle và artifact cache mới.
- Cold build sẽ chậm hơn trước khi cache hiệu quả.
- Cần chuẩn hóa output giữa nhiều pytest/coverage version.
- Project-native plugins có thể không tương thích với sandbox-managed runner.
- Phải quản lý migration protocol và rollback trong thời gian executor cũ còn tồn tại.
- Việc chặn network và giới hạn resource cần được kiểm thử ở hạ tầng thật, không chỉ unit test.

## Các phương án không chọn

### Giữ shared venv và đổi pin coverage

Không chọn vì chỉ giải quyết sự cố package/version hiện tại. Conflict giữa project với tool hoặc giữa hai project sẽ tái diễn với package khác.

### Giữ shared venv nhưng bỏ toàn bộ pin tooling

Không chọn vì test/coverage behavior sẽ phụ thuộc ngẫu nhiên vào project cuối cùng tham gia resolver, làm điểm thiếu tái lập và có thể phá plugin compatibility.

### Chạy project tests trực tiếp trong optimizer environment

Không chọn vì tiếp tục trộn dependency và trust boundary, đồng thời để code project tiếp cận process/filesystem có optimizer credentials và artifacts.

### Cho phép project cung cấp Dockerfile và command tùy ý

Không chọn làm mặc định vì làm tăng rủi ro supply-chain, khó áp resource/network policy và làm fingerprint kém ổn định. Có thể nghiên cứu như một capability riêng sau này với policy nghiêm ngặt.

## Phạm vi chưa quyết định trong ADR này

Các quyết định sau phải được chốt ở ADR/spike tiếp theo:

- Một environment artifact ánh xạ chính xác thế nào tới project/source revision.
- Priority giữa lock/manifest và dependency groups/extras.
- Project-native, sandbox-managed và compatibility fallback runner.
- Cache key, TTL, quota và invalidation.
- Python image routing và protocol migration chi tiết.
- Hạ tầng cụ thể để thực thi sandbox và network isolation.

## Kế hoạch chuyển đổi

1. Giữ executor/protocol hiện tại hoạt động trong khi thêm contract mới.
2. Tạo sandbox image Python 3.12 tối thiểu, không chứa optimizer stack.
3. Thêm orchestrator/client phía backend và chạy shadow build/evaluation.
4. So sánh kết quả trên regression fixtures, đặc biệt conflict coverage và two-project conflict.
5. Bật canary bằng feature flag cho project mới.
6. Chỉ chuyển traffic sau khi admission, scoring và atomic bundle tests pass.
7. Giữ đường rollback về executor cũ trong rollout window.

Không migrate hoặc tái sử dụng shared virtual environment cache trong sandbox architecture.

## Tiêu chí xác minh quyết định

- Optimizer và sandbox được build/deploy bằng dependency graph riêng.
- `coverage==7.15.2` của optimizer không xuất hiện trong project Dependency Plan trừ khi chính project yêu cầu nó.
- Project `coverage==7.10.7` có thể build và chạy dù optimizer dùng phiên bản khác.
- Hai project pin dependency mâu thuẫn không được resolve vào cùng một venv mặc định.
- Sandbox execution không đọc được LLM/cloud credentials của optimizer.
- Baseline/candidate fingerprint mismatch ngăn việc so điểm hoặc kích hoạt rebaseline.
- Sandbox failure không thay đổi active bundle.

## Quy tắc sửa đổi quyết định

Mọi thay đổi cho phép optimizer dependency đi vào project resolver, dùng lại shared venv giữa các project, hoặc chạy project code trong trust boundary của optimizer phải tạo ADR thay thế và chứng minh đồng thời tính tái lập, khả năng cô lập dependency và security boundary.
