# ADR 0007: Python image routing và protocol migration

- Trạng thái: Accepted
- Ngày quyết định: 2026-08-26
- Phụ thuộc: [ADR 0001](0001-separate-optimizer-and-project-sandbox.md)
- Contract: [Project Sandbox Protocol v1](../contracts/project-sandbox-protocol-v1.md)

## Bối cảnh

API hiện cho phép Python 3.10–3.13 nhưng cloud image thực tế dùng Python 3.12. Runtime v8 reject khi requested minor khác interpreter đang chạy. Cần multi-version thật mà không nâng protocol tối thiểu trước khi workers mới sẵn sàng.

## Quyết định

### Image/job routing

- Mỗi Python minor 3.10, 3.11, 3.12 và 3.13 có sandbox base image/job riêng.
- Route bằng allowlisted `(python_minor, image_digest, job_name)`, không nhận runtime image tùy ý từ project/UI.
- Bắt đầu Python 3.12; chỉ advertise minor khác sau contract/security/integration tests và health check.
- Requested Python phải thỏa detected requirement. Mâu thuẫn bị reject trước dependency install.
- Image digest và full interpreter version nằm trong environment fingerprint/result.
- Optimizer/test-generation image không được dùng làm project sandbox image.

### Protocol migration

- Sandbox contract mới bắt đầu ở `SANDBOX_PROTOCOL_VERSION = 1` và không thay runtime bundle protocol v8 trong Giai đoạn 0.
- Backend/client dual-read runtime report v8 và sandbox result v1 trong migration window.
- Các field chẩn đoán mới là optional; client phải đọc payload tối thiểu.
- Sandbox v1 chỉ chạy sau feature flag `project_sandbox_v2`.
- Deploy images/workers trước, orchestrator/backend sau, UI advertise cuối cùng.
- Không tăng minimum protocol đến khi metric xác nhận workers cũ không còn traffic cần hỗ trợ và rollback window kết thúc.

### Version negotiation

Orchestrator chọn highest mutually supported sandbox protocol trong allowlist. Worker từ chối version cao hơn nó hỗ trợ bằng error có cấu trúc; không cố parse rồi chạy. Protocol version, image digest và runner version là fingerprint inputs.

### Rollback

- Tắt UI/version routing mới trước.
- Tắt feature flag cho upload mới.
- Giữ runtime v8 reader/executor và active bundle references trong rollback window.
- Không convert/mutate artifact v1 thành bundle v8; rebuild qua executor tương ứng nếu thực sự cần.

## Hệ quả

- Hỗ trợ Python là năng lực được chứng minh theo từng image, không chỉ schema option.
- Tăng số image/job và CI matrix.
- Dual protocol làm backend phức tạp tạm thời nhưng tránh big-bang migration.
- Thay patch version/image digest làm fingerprint đổi và có thể cần rebaseline.

## Tiêu chí xác minh

- UI/API chỉ advertise healthy images đã test.
- Project 3.11 không chạy nhầm image 3.12.
- Payload v8 vẫn đọc được khi sandbox v1 rollout.
- Worker v1 reject protocol không hỗ trợ rõ ràng.
- Rollback feature flag không mất active bundle/project data.
