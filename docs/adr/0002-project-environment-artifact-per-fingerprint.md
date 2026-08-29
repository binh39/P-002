# ADR 0002: Một project environment artifact cho một fingerprint

- Trạng thái: Accepted
- Ngày quyết định: 2026-08-26
- Phụ thuộc: [ADR 0001](0001-separate-optimizer-and-project-sandbox.md)

## Bối cảnh

Runtime v8 đóng gói một shared venv cho toàn bộ project trong một logical environment. Hai project hợp lệ riêng lẻ vì vậy có thể reject nhau khi dependency conflict. Việc dùng lại cùng persistent venv còn làm identity của môi trường phụ thuộc vào thứ tự/membership project.

## Quyết định

Mỗi project được admission bằng một logical `ProjectEnvironmentArtifact` bất biến, định danh bởi environment fingerprint. Không resolve hoặc cài dependency của hai project vào cùng một venv mặc định.

Fingerprint bao gồm tối thiểu:

- Sandbox contract/runner protocol version.
- Python implementation và full version.
- OS, architecture và base image digest.
- Dependency Plan canonical digest: manifest/lock content, groups, extras và index identities không chứa secret.
- Runner profile và pytest/coverage version thực tế.
- Build/install mode và project wheel hash nếu source được build/cài vào artifact.

Source revision không nằm trong dependency fingerprint khi source chỉ được mount/copy lúc execution. Khi project phải build wheel hoặc cài editable/source vào artifact, wheel/source digest bắt buộc nằm trong fingerprint.

Artifact metadata luôn chứa `project_id`, nhưng storage có thể deduplicate content-addressed layers giữa hai project nếu security policy chứng minh không rò rỉ source/secret. Việc deduplicate không biến chúng thành một shared mutable venv.

Baseline và candidate dùng cùng artifact/fingerprint. Một logical runtime environment có nhiều project chỉ giữ danh sách artifact references; aggregate score được tính ngoài sandbox.

Cross-project tests không được âm thầm merge venv. Nếu được hỗ trợ sau này, chúng phải khai báo dependency graph và tạo một composite artifact có fingerprint riêng.

## Publish và atomicity

- Build diễn ra ở staging path/object.
- Chỉ artifact đã hoàn thành consistency check mới có immutable manifest.
- Manifest/fingerprint được publish cuối cùng.
- Failure không ghi đè artifact tốt hoặc active bundle.
- Artifact không được mutate; thay dependency tạo fingerprint mới.

## Hệ quả

### Tích cực

- Conflict của một project không reject project khác.
- Cache/reuse có identity rõ và baseline/candidate tái lập.
- Rollback chỉ đổi reference, không rebuild hoặc sửa artifact cũ.

### Chi phí

- Tăng số artifact và cần quota/garbage collection.
- Project có dependency giống nhau không còn chia sẻ writable venv; chỉ được deduplicate immutable layer.
- Cross-project integration cần contract riêng.

## Phương án không chọn

- Shared venv theo runtime environment: giữ nguyên nguyên nhân conflict.
- Mutate artifact hiện có khi upload/retry: phá fingerprint và paired evaluation.
- Fingerprint chỉ từ tên file lock: không phát hiện nội dung/policy/image thay đổi.

## Tiêu chí xác minh

- Hai project pin hai phiên bản package mâu thuẫn tạo hai fingerprint/artifact khác nhau.
- Cache hit trả artifact bất biến và không chạy resolver lại.
- Thay Python, lock, group, runner hoặc image digest làm fingerprint đổi.
- Candidate build fail không đổi active artifact reference.
