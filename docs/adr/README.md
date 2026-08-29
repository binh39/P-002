# Architecture Decision Records: Project Sandbox

## Phase 0 decision set

| ADR | Trạng thái | Quyết định |
|---|---|---|
| [0001](0001-separate-optimizer-and-project-sandbox.md) | Accepted | Tách dependency/trust boundary optimizer và sandbox |
| [0002](0002-project-environment-artifact-per-fingerprint.md) | Accepted | Một immutable project artifact cho một fingerprint |
| [0003](0003-sandbox-runner-and-coverage-strategy.md) | Accepted | Project-native ưu tiên, managed khi thiếu cả hai tool, fallback có cấu trúc |
| [0004](0004-dependency-source-and-selection-policy.md) | Accepted | Một canonical Dependency Plan, không all-groups/all-extras |
| [0005](0005-sandbox-security-and-network-policy.md) | Accepted | Build network allowlist; execution egress deny và resource isolation |
| [0006](0006-environment-artifact-cache-policy.md) | Accepted | Content-addressed immutable cache và atomic publish |
| [0007](0007-python-image-routing-and-protocol-migration.md) | Accepted | Image riêng theo Python minor, dual protocol migration |

## Review Giai đoạn 0

- Ngày review: 2026-08-26
- Reviewer: Codex, theo yêu cầu hoàn thành Giai đoạn 0 của người dùng
- Kết quả: Approved for implementation planning

### Consistency review

- [x] ADR 0001 đặt trust/dependency boundary; không ADR sau nào đưa optimizer package trở lại project resolver.
- [x] ADR 0002 và ADR 0006 thống nhất artifact bất biến, fingerprint key và atomic manifest publish.
- [x] ADR 0003 và ADR 0004 thống nhất runner selection xảy ra sau project dependency resolution và không mutate inventory.
- [x] ADR 0003 khớp kết quả [runner spike](../spikes/sandbox-runner-compatibility.md).
- [x] ADR 0005 không cho execution network/credential mặc định; `SandboxSpec` chỉ nhận environment variable names và package-index references.
- [x] ADR 0007 giữ runtime protocol v8 trong migration và đưa sandbox contract mới vào namespace/version riêng.
- [x] [Protocol v1](../contracts/project-sandbox-protocol-v1.md) biểu diễn đủ ranh giới, dependency policy, runner profile, resource limits, diagnostics và fingerprint gate đã quyết định.
- [x] Không file production hiện tại import contract/selector mới; Giai đoạn 0 chưa thay runtime behavior.

### Evidence review

- Contract/selector targeted tests: 22 passed trên Python 3.13.14.
- Ruff cho contract, selector, spike và tests: pass.
- `py_compile` cho contract, selector và spike: pass.
- Runner spike:
  - project-native, coverage 7.10.7: pass;
  - sandbox-managed, coverage 7.15.3: pass;
  - compatibility fallback: pass, trả `INCOMPLETE_PROJECT_RUNNER`.
- Exact runbook `.venv` pytest command chưa chạy được vì `.venv` thiếu `pyvenv.cfg`; fallback dùng Python 3.13 với packages từ `.venv313`.
- Full fallback suite chạy nhưng còn 4 failure ngoài code Giai đoạn 0:
  - optimizer subprocess test không pass trong fallback interpreter;
  - sample isort preflight thiếu `tomli` trong subprocess;
  - workspace hiện thiếu sample directories `mlxtend` và `typesystem`.
  Targeted contract/runner tests không có failure.

### Rủi ro chuyển sang giai đoạn implementation

- Local spike mới chứng minh Python 3.13.14; Docker matrix 3.10–3.13 vẫn là rollout gate.
- Sandbox-managed site-package bridging cần integration test với wheel native và plugins bên thứ ba.
- Network/seccomp/resource policies cần xác minh trên hạ tầng Cloud Run thực tế.
- Retention/quota trong ADR 0006 là default policy và cần map sang storage budget production.

Các rủi ro trên không thay đổi quyết định Giai đoạn 0; chúng đã có checklist ở các giai đoạn build, security và CI trước production rollout.
