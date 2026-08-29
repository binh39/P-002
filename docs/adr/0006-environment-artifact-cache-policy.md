# ADR 0006: Cache key, lifecycle và invalidation

- Trạng thái: Accepted
- Ngày quyết định: 2026-08-26
- Phụ thuộc: [ADR 0002](0002-project-environment-artifact-per-fingerprint.md)

## Bối cảnh

Dựng project environment cho mỗi evaluation sẽ chậm và tốn network. Cache chỉ an toàn nếu artifact bất biến, key phản ánh toàn bộ input ảnh hưởng và publish nguyên tử. Shared mutable venv hiện tại không đáp ứng các điều kiện này.

## Quyết định

### Cache key

Primary key là SHA-256 của canonical environment descriptor, gồm:

- Sandbox/build protocol version.
- Python implementation/full version.
- Platform/architecture và base image digest.
- Canonical Dependency Plan digest.
- Runner profile và exact runner versions.
- Build/install mode.
- Project wheel/source digest nếu code được cài vào artifact.

Không hash secret value. Index identity/reference và policy version được hash để thay registry policy làm key đổi.

### Lifecycle

1. Lookup immutable manifest theo fingerprint.
2. Verify manifest, object hashes và compatibility.
3. Cache miss lấy distributed lease theo fingerprint.
4. Build vào staging namespace duy nhất.
5. Chạy consistency check và tạo package inventory.
6. Upload blobs; publish signed/hash manifest cuối cùng.
7. Release lease. Worker khác lookup lại thay vì dùng staging path.

Chỉ cache successful artifact. Failure/transient result không trở thành environment artifact; diagnostic có thể lưu theo execution retention riêng.

### Concurrency và recovery

- Lease có owner, heartbeat và expiry; default build lease tối đa bằng build deadline cộng safety window.
- Worker mất lease không được publish manifest.
- Staging object không có committed manifest được garbage-collect.
- Hash/manifest mismatch đánh dấu corrupt, cách ly object và rebuild; không phục vụ stale artifact.

### Retention và quota

- Default retention: 30 ngày kể từ lần sử dụng cuối, cấu hình được theo deployment.
- Artifact đang được active bundle/reference giữ pin và không bị GC.
- Khi vượt quota, evict LRU artifact không pin; không xóa active/staging artifact còn lease.
- Result/log artifacts có retention riêng, ngắn hơn environment artifacts.

### Invalidation

Không mutate hoặc xóa hàng loạt theo tên project. Thay input tạo fingerprint mới. Protocol/image bị thu hồi được denylist bằng digest/version; lookup không trả artifact denylisted dù object còn tồn tại để rollback/audit.

## Hệ quả

- Cache hit không chạy resolver và tái lập đúng environment.
- Cần object metadata/lease store đáng tin cậy và GC job.
- Storage tăng nhưng có thể deduplicate immutable blobs.
- Rollback giữ reference artifact cũ thay vì rebuild.

## Tiêu chí xác minh

- Concurrent builders chỉ publish một committed manifest.
- Crash giữa upload và manifest publish không tạo cache hit giả.
- Thay image/lock/group/runner tạo miss.
- Corrupt hash bị reject và rebuild.
- GC không xóa artifact đang active hoặc có lease.
