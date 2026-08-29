# ADR 0005: Sandbox security và network policy

- Trạng thái: Accepted
- Ngày quyết định: 2026-08-26
- Phụ thuộc: [ADR 0001](0001-separate-optimizer-and-project-sandbox.md)

## Bối cảnh

Uploaded source, package build hooks, pytest plugins và tests đều là code không tin cậy. Dependency install cần network có kiểm soát, nhưng test execution không cần tiếp cận registry, LLM endpoint, metadata service hoặc optimizer credentials.

## Quyết định

Tách sandbox thành hai security phase với policy khác nhau.

### Build phase

- Chạy non-root trong ephemeral workspace.
- Network chỉ tới registry/index allowlist được resolve từ `package_index_refs`.
- Credential ngắn hạn được cấp theo reference, không truyền qua command line hoặc ghi vào layer/log.
- Không mount optimizer cache, prompt artifacts, host home, Docker socket hoặc cloud credential mặc định.
- Build output chỉ publish sau consistency/inventory check.

### Execution phase

- Egress deny mặc định, gồm cloud metadata endpoint.
- Non-root, no-new-privileges, drop capabilities và seccomp/runtime policy tối thiểu.
- Root filesystem read-only khi platform cho phép.
- Source read-only; generated tests, pytest temp/cache và coverage artifacts có writable mounts riêng.
- Giới hạn CPU, RAM, PIDs/processes, wall-clock, disk/file size và stdout/stderr.
- Chỉ environment variable names trong allowlist; secret value của optimizer không bao giờ được resolve cho execution.
- Không cho arbitrary shell command; sandbox agent nhận versioned `RunSpec`.

### Archive và filesystem

- Reject absolute path, `..`, symlink/hardlink escape, archive bomb, quá số entry và quá size limit.
- Resolve/canonicalize mọi configured path dưới project root.
- Artifact path phải được validate ownership/scope trước upload/download.

### Logging và audit

- Redact token, credential URL, environment values và signed query.
- Bound output trước khi persist.
- Audit build, execution, retry, artifact publish, activation và rollback bằng IDs/fingerprint, không bằng secret.

## Threats nằm ngoài scope

Sandbox không cam kết chống kernel/container-runtime escape chưa vá. Hạ tầng phải cập nhật base image/runtime và có vulnerability policy riêng. Supply-chain provenance/signing có thể bổ sung sau nhưng không thay network/isolation controls trên.

## Hệ quả

- Dependency install và test execution cần hai lifecycle/network policy rõ ràng.
- Test dựa vào internet sẽ fail trừ khi capability sau này được phê duyệt riêng; mặc định này là chủ ý.
- Một số filesystem/plugin behavior cần writable paths được khai báo cụ thể.

## Tiêu chí xác minh

- Integration test chứng minh execution không gọi internet/metadata service.
- Sandbox không đọc được optimizer credential hoặc host path ngoài mount.
- Fork bomb, timeout và output overflow bị giới hạn.
- Malicious archive không ghi file ngoài workspace.
