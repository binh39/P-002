# Đặc tả triển khai RBAC: Prompt Engineer và Prompt Reviewer

## 1. Mục tiêu

Triển khai hai vai trò đăng nhập thực sự cho PromptOpt:

- `prompt_engineer` — Create Project, Phân tích source code, Create và cấu hình experiment, chạy resume cancel experiment/optimization, Xem kết quả và artifacts của mình, Xem baseline/candidate diff, Xem locked-holdout coverage lỗi regression, Gửi candidate sang review, Xóa project/experiment của mình, Xem lịch sử quyết định/audit của mình  và tạo Test Suite.
- `prompt_reviewer` — kiểm tra evidence, approve hoặc reject prompt candidate. Xem kết quả và artifacts experiment được giao review. Đưa prompt vào production registry thông qua approve hoặc reject, Xem lịch sử quyết định/audit các review được giao.

Phân quyền phải được kiểm tra ở backend. Việc ẩn nút trên frontend chỉ phục vụ trải nghiệm người dùng, không được xem là biện pháp bảo mật.

Luồng nghiệp vụ sau khi hoàn thành:

```text
Prompt Engineer
  -> tạo project và experiment
  -> chạy optimization/comparison
  -> candidate tốt hơn baseline được đưa vào trạng thái in_review

Prompt Reviewer trong cùng workspace
  -> xem prompt diff, coverage và artifacts
  -> approve hoặc reject

Nếu approved
  -> Prompt Engineer có thể tạo Test Suite bằng prompt optimized đã duyệt
```

Quy tắc bắt buộc:

> Người tạo experiment/candidate không bao giờ được review candidate của chính mình, kể cả khi tài khoản đó có nhiều quyền.

## 2. Phạm vi và quyết định đã chốt

### 2.1. Vai trò

Sử dụng enum ổn định, không dùng chuỗi chức danh hiển thị tùy ý:

```python
class UserRole(str, Enum):
    PROMPT_ENGINEER = "prompt_engineer"
    PROMPT_REVIEWER = "prompt_reviewer"
```

Tên hiển thị:

- `prompt_engineer`: **Prompt Engineer** / **Kỹ sư Prompt**.
- `prompt_reviewer`: **Reviewer** / **Người kiểm duyệt Prompt**.

Không dùng email để suy ra role. `FULL_ACCESS_EMAILS` và `has_full_access` hiện tại chỉ liên quan quota/model/billing đặc biệt; chúng phải độc lập với RBAC và không làm một Engineer trở thành Reviewer.

### 2.2. Workspace

Reviewer chỉ được xem dữ liệu trong cùng workspace, không được xem toàn bộ dữ liệu của mọi người dùng.

Mỗi identity cần có:

- `uid`
- `email`
- `name`
- `role`
- `workspace_id`

Mỗi record cần chia sẻ cho Reviewer phải có `workspace_id`, tối thiểu gồm:

- experiment;
- prompt version;
- optimization/comparison run nếu không thể suy ra an toàn từ experiment;
- test-generation run;
- project nếu Reviewer cần mở source context trực tiếp.

`owner_id` vẫn là người tạo và không được thay bằng `workspace_id`. Hai trường có ý nghĩa khác nhau:

- `owner_id`: quyền sở hữu, sửa và xóa.
- `workspace_id`: phạm vi đọc/review được chia sẻ.

Mỗi Workspace có thể có nhiều người dùng, có thể có 1-nhiều Prompt Engineer, 1-nhiều Reviewer

### 2.3. Test Suite

Chỉ `prompt_engineer` được tạo Test Suite.

- Engineer được tạo suite từ baseline hợp lệ.
- Engineer chỉ được tạo suite từ optimized prompt khi prompt version đã ở trạng thái `approved`.
- Reviewer được xem danh sách, chi tiết, manifest, coverage, log và tải artifact của suite trong cùng workspace.
- Reviewer không được tạo, cancel hoặc delete Test Suite.
- Reviewer không được sửa model, targets hoặc cấu hình generation.

Không thêm quyền tạo Test Suite chung cho cả hai role. Nếu sau này cần Reviewer chạy kiểm chứng độc lập, phải xây một chức năng riêng tên `Run verification`, cấu hình cố định, audit riêng và không thay thế locked-holdout promotion gate. Chức năng này nằm ngoài phạm vi hiện tại.

## 3. Ma trận quyền


| Resource / hành động                             | Prompt Engineer                                     | Prompt Reviewer                                    |
| --------------------------------------------------- | --------------------------------------------------- | -------------------------------------------------- |
| Đăng ký/đăng nhập/đăng xuất/reset password | Có                                                 | Có                                                |
| Xem hồ sơ và role của chính mình              | Có                                                 | Có                                                |
| Tạo/upload project                                 | Có                                                 | Không                                             |
| Xem project/source trong workspace                  | Project của mình                                  | Chỉ đọc khi phục vụ review                    |
| Sửa/xóa project                                   | Project của mình                                  | Không                                             |
| Tạo/sửa/xóa draft experiment                     | Có, với dữ liệu của mình                      | Không                                             |
| Chạy/resume/cancel optimization                    | Có, với experiment của mình                     | Không                                             |
| Chạy comparison                                    | Có, với experiment của mình                     | Không                                             |
| Xem run/evolution/artifact                          | Dữ liệu của mình                                | Chỉ đọc trong cùng workspace                   |
| Xem Prompt Registry                                 | Dữ liệu của mình                                | Chỉ đọc trong cùng workspace                   |
| Xem review queue                                    | Có, với queue của mình gửi đến các reviewer | Có                                                |
| Approve/reject candidate                            | Không                                              | Có, cùng workspace và không phải người tạo |
| Tạo Test Suite                                     | Có                                                 | Không                                             |
| Xem/download Test Suite                             | Suite của mình                                    | Có, trong cùng workspace                        |
| Cancel/delete Test Suite                            | Suite của mình                                    | Không                                             |
| Quản lý role người khác                        | Không                                              | Không                                             |

Quản trị role là thao tác quản trị hệ thống, không tự động thuộc về Reviewer. Nếu cần UI quản trị tài khoản, hãy thiết kế role `admin` riêng ở một yêu cầu sau.

## 4. Hiện trạng cần sửa

Các điểm hiện tại chưa phải RBAC thực sự:

1. `app/backend/core/security.py`
   - `AuthenticatedUser` chưa có `role` và `workspace_id`.
   - `has_full_access` dựa trên whitelist email, không phải role.
2. `app/frontend/src/auth/FirebaseAuthService.ts`
   - Tất cả Firebase users đang bị gán cứng nhãn `AI Engineer`.
3. `app/frontend/src/auth/DemoAuthService.ts`
   - Chỉ có một demo identity và mọi credential đều kích hoạt cùng identity.
4. `app/backend/modules/experiments/router.py`
   - Endpoint approve/reject truyền `user.uid` vào service nhưng không yêu cầu role Reviewer.
5. `app/backend/modules/experiments/service.py`
   - `review_prompt_version()` gọi `_owned(...)`, vì vậy chỉ owner mới review được.
   - Owner hiện có thể tự approve/reject.
6. Repository hiện chủ yếu query theo `owner_id`; chưa có query review theo `workspace_id`.
7. Frontend `AuthUser.role` là `string`, chỉ dùng để hiển thị và chưa điều khiển route/action theo policy.

Không được sửa promotion gate của GEPA để triển khai RBAC. Candidate chỉ xuất hiện `in_review` sau khi pipeline hiện tại xác nhận điều kiện promotion.

## 5. Thiết kế authentication và role source

### 5.1. Production Firebase

Dùng Firebase custom claims do môi trường tin cậy cấp:

```json
{
  "role": "prompt_reviewer",
  "workspace_id": "workspace-example"
}
```

Yêu cầu:

- Client không được tự đặt hoặc gửi role để backend tin tưởng.
- Firebase token verifier đọc `role` và `workspace_id` từ token đã verify.
- Tài khoản không có role claim mặc định là `prompt_engineer` để giữ tương thích cho người dùng hiện tại.
- `workspace_id` thiếu thì mặc định an toàn là chính `uid`; không mặc định vào một workspace dùng chung.
- Chỉ môi trường admin tin cậy mới được gán `prompt_reviewer`.
- Sau khi thay claims, yêu cầu người dùng refresh ID token hoặc đăng nhập lại.
- Không commit Firebase token, service-account key hay thông tin đăng nhập thật.

Nếu tạo script gán role, script phải:

- nhận UID/email, role và workspace rõ ràng;
- validate role theo enum;
- hỗ trợ `--dry-run`;
- in UID/role/workspace nhưng không in token hoặc secret;
- từ chối role không hợp lệ.

### 5.2. Development/demo

Demo mode phải cho kiểm thử hai identity độc lập:

- Engineer: UID `local-engineer`, role `prompt_engineer`.
- Reviewer: UID `local-reviewer`, role `prompt_reviewer`.
- Cả hai dùng `workspace_id="local-workspace"`.

`DevelopmentTokenVerifier` nên hỗ trợ token riêng cho từng identity. Có thể giữ `dev-token` làm alias tạm thời cho Engineer để không phá các test/local script cũ, nhưng Reviewer phải có token riêng.

`DemoAuthService` phải chọn đúng identity dựa trên tài khoản demo đã nhập, không được bỏ qua email rồi đăng nhập tất cả thành một user. Session chỉ lưu định danh profile demo; không lưu Firebase token hay production secret.

Trang Login dùng chung cho cả hai role. Không thêm dropdown “chọn role” mà backend sẽ tin tưởng. Vai trò gắn với tài khoản đăng nhập.

### 5.3. API hồ sơ hiện tại

Thêm endpoint authenticated:

```http
GET /api/v1/me
```

Response tối thiểu:

```json
{
  "id": "local-reviewer",
  "name": "Local Reviewer",
  "email": "reviewer@promptopt.dev",
  "role": "prompt_reviewer",
  "workspace_id": "local-workspace",
  "permissions": ["reviews:read", "reviews:decide", "test_suites:read"]
}
```

Frontend dùng response này để render navigation. Backend vẫn kiểm tra quyền riêng cho từng request.

## 6. Authorization backend

### 6.1. Policy tập trung

Tạo policy/dependency tập trung, ví dụ `app/backend/core/authorization.py`, thay vì rải so sánh chuỗi role khắp router và service.

Policy cần biểu diễn tối thiểu:

- `require_engineer(user)`
- `require_reviewer(user)`
- `require_same_workspace(user, resource_workspace_id)`
- `require_owner(user, owner_id)`
- `forbid_self_review(user, creator_id)`

HTTP semantics:

- Chưa đăng nhập hoặc token sai: `401`.
- Đã đăng nhập nhưng sai role: `403 ROLE_FORBIDDEN`.
- Cùng role nhưng khác workspace: trả `404` để tránh tiết lộ resource tồn tại.
- Reviewer tự duyệt: `403 SELF_REVIEW_FORBIDDEN`.
- Optimized prompt chưa approved mà tạo suite: `409 PROMPT_NOT_APPROVED`.

Không chỉ kiểm tra role ở router. Service phải duy trì invariant quan trọng, đặc biệt self-review và workspace boundary, để code nội bộ không thể bỏ qua bảo vệ.

### 6.2. Endpoint mutation dành cho Engineer

Yêu cầu `prompt_engineer` cho các mutation sau:

- upload/create/update/delete project;
- analyze/re-analyze nếu hành động tạo job hoặc thay state;
- create/delete experiment;
- optimize/resume/cancel;
- compare;
- create/cancel/delete Test Suite;
- các mutation provider credential nếu credential thuộc người tạo.

Các owner check hiện tại vẫn được giữ nguyên sau role check.

### 6.3. Review API

Thêm review queue tách biệt để không làm thay đổi semantics owner-scoped hiện tại:

```http
GET  /api/v1/reviews?status=in_review&offset=0&limit=50
GET  /api/v1/reviews/{version_id}
POST /api/v1/prompt-versions/{version_id}/approve
POST /api/v1/prompt-versions/{version_id}/reject
```

`GET /reviews` và `GET /reviews/{id}` chỉ cho Reviewer, query theo `workspace_id`.

Review detail phải trả đủ dữ liệu để ra quyết định, hoặc trả các URL/API con an toàn để lấy:

- experiment name và creator;
- baseline và candidate prompt bundle;
- diff của `initial`, `error`, `missing_coverage`;
- model/config snapshot và digest;
- final split được dùng;
- baseline/proposal aggregate coverage;
- absolute/relative gain;
- replicate count;
- promotion decision;
- failure, timeout, flaky và regression evidence;
- artifact names/links đã được allowlist.

Approve/reject chỉ thành công khi:

- caller có role Reviewer;
- resource cùng workspace;
- `caller.uid != experiment.owner_id` và khác `created_by` nếu prompt version có trường này;
- version đang `in_review`, hoặc request idempotent lặp lại đúng quyết định trước của cùng reviewer;
- reject có comment không rỗng sau khi trim.

Approve comment có thể optional nhưng nên được lưu nếu có.

Hai Reviewer đua nhau quyết định phải được xử lý nguyên tử trong repository transaction:

- quyết định đầu tiên thắng;
- retry cùng quyết định trả record hiện tại;
- quyết định khác sau đó trả `409 PROMPT_VERSION_ALREADY_REVIEWED`;
- không được ghi đè `reviewer_id`, `reviewed_at` hoặc comment của quyết định đầu tiên.

### 6.4. Audit fields

Prompt version/review record phải lưu:

- `created_by`
- `workspace_id`
- `status`
- `reviewer_id`
- `review_comment`
- `reviewed_at`
- `decision`
- digest của baseline và candidate tại thời điểm review

Không cho client gửi `reviewer_id`, `reviewed_at`, `created_by` hoặc `workspace_id` tùy ý; backend lấy từ authenticated identity và resource gốc.

## 7. Repository, Firestore và migration

### 7.1. Repository contract

Bổ sung các method rõ nghĩa, không tải toàn bộ collection rồi lọc ở Python trong production:

- list prompt versions theo `workspace_id + status`;
- get reviewable prompt version theo ID;
- list Test Suite runs theo workspace cho Reviewer;
- atomic decision có precondition `status == in_review`.

In-memory repository và Firestore repository phải có cùng semantics.

Thêm Firestore composite indexes nếu query yêu cầu, ví dụ:

- prompt versions: `workspace_id`, `status`, `created_at`;
- test-generation runs: `workspace_id`, `created_at`.

### 7.2. Backfill

Record mới luôn phải ghi `workspace_id` khi tạo.

Với record cũ thiếu `workspace_id`:

- mặc định backfill thành `owner_id` để không vô tình chia sẻ dữ liệu;
- cung cấp script dry-run và apply rõ ràng;
- không tự gom tất cả record cũ vào `default` workspace;
- báo số record đọc, thay đổi, bỏ qua và lỗi;
- không log prompt content, source code hoặc secret.

Nếu chưa chạy backfill, service phải fail closed cho Reviewer thay vì cấp quyền rộng. Engineer vẫn được truy cập record cũ của mình qua owner check.

## 8. Frontend

### 8.1. Kiểu dữ liệu và auth state

Thay `role: string` bằng union/enum:

```ts
export type UserRole = "prompt_engineer" | "prompt_reviewer";
```

`AuthUser` cần có `workspaceId` và permissions nếu frontend dùng permission-based rendering.

Không hard-code `"AI Engineer"` cho Firebase user. Sau khi Firebase sign-in thành công, frontend lấy `/api/v1/me` và tạo auth state từ response đã được backend xác nhận.

### 8.2. Navigation theo role

Engineer thấy:

- Dashboard
- Projects
- Experiments
- Prompt Registry
- Test Suites
- Docs/Settings

Reviewer thấy:

- Review Queue
- Prompt Registry ở chế độ read-only
- Test Suites ở chế độ read-only
- Docs/Settings

Reviewer không thấy CTA:

- New Project
- Create Experiment
- Optimize/Resume/Cancel
- Run Comparison
- Create/Cancel/Delete Test Suite

Ẩn CTA không thay thế backend authorization.

### 8.3. Review Queue

Tạo trang Review Queue có:

- filter `in_review`, `approved`, `rejected`;
- pagination;
- candidate, experiment, creator, created time;
- coverage gain và final split badge;
- empty/loading/error state;
- link tới review detail.

Review detail cần có:

- prompt diff cho đủ ba component;
- bảng baseline/proposal coverage;
- status của promotion gate;
- replicate/config metadata;
- artifact viewer/download;
- approve/reject dialog;
- comment bắt buộc khi reject;
- confirmation trước quyết định;
- UI khóa sau khi có quyết định.

Nếu API trả `409` do Reviewer khác đã xử lý, frontend refresh record và hiển thị quyết định hiện tại; không giả vờ request vừa rồi thành công.

### 8.4. Test Suites

Engineer:

- thấy nút Create Test Suite;
- có thể chọn baseline;
- chỉ thấy optimized prompt trong lựa chọn khi version đã approved;
- có thể cancel/delete suite của mình theo quy tắc hiện tại.

Reviewer:

- không có nút Create/Cancel/Delete;
- được xem manifest, coverage, log và download artifact trong cùng workspace;
- màn hình phải có nhãn `Read-only` rõ ràng.

### 8.5. Route guard

Route guard frontend phải:

- chờ auth/me load trước khi quyết định;
- Reviewer mở URL Engineer phải được chuyển tới Review Queue hoặc trang Forbidden;
- Engineer mở URL Review Queue phải thấy Forbidden;
- không tạo redirect loop khi token hết hạn;
- sign-out xóa auth state/demo session phù hợp.

## 9. Quy tắc nghiệp vụ không được phá

1. Baseline luôn là fallback của GEPA.
2. Locked test split không được lộ vào search hoặc dùng chọn candidate.
3. Chỉ candidate strictly better mới vào `in_review` theo promotion gate hiện tại.
4. Reviewer không thể override promotion gate để approve một candidate không đủ điều kiện hoặc không có prompt version `in_review`.
5. Reviewer không thể sửa prompt bundle, comparison data hoặc artifacts.
6. Approve/reject không chạy lại benchmark và không phát sinh model call.
7. Tạo Test Suite không được thay đổi prompt version đã approve.
8. Mọi owner/workspace query phải giữ tenant isolation.
9. Không đổi `has_full_access` thành role check; quota access và business role là hai policy độc lập.
10. Không ghi token, credential, signed URL hoặc raw source nhạy cảm vào log/audit.

## 10. Test bắt buộc

### 10.1. Backend unit/API tests

Tối thiểu phải có các test sau:

#### Authentication

- Firebase claims hợp lệ map đúng Engineer/Reviewer và workspace.
- Role không hợp lệ bị từ chối hoặc fallback an toàn theo quyết định đã chốt.
- User thiếu role mặc định Engineer.
- User thiếu workspace mặc định workspace riêng là UID.
- Dev Engineer và Dev Reviewer trả identity khác nhau.
- `/api/v1/me` trả đúng role/permissions.

#### Engineer permissions

- Engineer tạo project/experiment/optimization/Test Suite thành công khi là owner.
- Engineer không gọi được review queue.
- Engineer không approve hoặc reject được, kể cả candidate của mình.
- Engineer không truy cập resource owner khác.
- Engineer không tạo optimized Test Suite khi prompt chưa approved.
- Engineer tạo optimized Test Suite sau approve thành công.

#### Reviewer permissions

- Reviewer xem queue cùng workspace.
- Reviewer không thấy record workspace khác.
- Reviewer xem prompt diff/evidence/artifacts cùng workspace.
- Reviewer approve/reject candidate của Engineer khác thành công.
- Reviewer không tự review candidate do chính UID đó tạo.
- Reviewer không tạo/sửa/xóa project hoặc experiment.
- Reviewer không optimize/resume/cancel/compare.
- Reviewer không tạo/cancel/delete Test Suite.
- Reviewer xem/download Test Suite cùng workspace ở chế độ read-only.

#### Review consistency

- Reject thiếu comment trả validation error.
- Retry cùng quyết định là idempotent.
- Quyết định ngược sau khi hoàn thành trả `409`.
- Hai concurrent decisions chỉ ghi một quyết định.
- `reviewer_id` và timestamp lấy từ server.
- Không thể truyền workspace khác qua payload.

#### Migration/repository

- Record cũ thiếu workspace vẫn owner-readable nhưng reviewer không được cấp quyền rộng.
- Backfill mặc định workspace bằng owner ID.
- Repository query theo workspace/status có pagination và ordering ổn định.

### 10.2. Frontend tests

- Login Engineer render đúng role/navigation.
- Login Reviewer render Review Queue và read-only Test Suites.
- Firebase auth không gán cứng `AI Engineer`.
- Engineer không thấy approve/reject.
- Reviewer không thấy create/cancel/delete actions.
- Reject yêu cầu comment.
- Approve/reject gọi đúng endpoint và refresh state.
- `403`, `404`, `409` có thông báo phù hợp.
- Direct route access bị guard đúng cho cả hai role.
- Session demo giữ đúng identity sau reload và được xóa khi logout.

### 10.3. Security regression tests

- Thay role trong body/header tùy ý không thay đổi quyền.
- Không thể dùng UID/version ID đoán được để đọc workspace khác.
- Response lỗi CORS vẫn giữ header theo invariant hiện tại.
- Reviewer read-only không có đường mutation gián tiếp qua service khác.

## 11. Acceptance criteria

Chỉ xem là hoàn thành khi đáp ứng đủ:

- Có hai tài khoản/identity demo đăng nhập độc lập với role khác nhau.
- Role do backend/token verified quyết định, không do dropdown/client payload.
- Engineer thực hiện được workflow hiện tại nhưng không thể approve/reject.
- Reviewer thấy Review Queue cùng workspace và approve/reject được candidate của người khác.
- Self-review bị chặn ở backend.
- Reviewer không tạo được Test Suite bằng API, không chỉ bị ẩn nút.
- Reviewer xem được Test Suite evidence trong cùng workspace.
- Engineer chỉ tạo optimized Test Suite sau khi prompt approved.
- Cross-workspace access bị chặn và có test.
- Review decision nguyên tử, idempotent và có audit.
- Existing GEPA/promotion tests vẫn pass.
- Không deploy hoặc chạy live benchmark/Vertex nếu người dùng chưa yêu cầu rõ.

## 12. Thứ tự triển khai đề xuất

1. Thêm role/workspace models và verified claims vào backend auth.
2. Thêm policy authorization tập trung và `/api/v1/me`.
3. Ghi `workspace_id` vào record mới; cập nhật in-memory/Firestore repositories.
4. Xây review queue queries và review authorization nguyên tử.
5. Áp Engineer-only policy cho mutations và Test Suite creation.
6. Cho Reviewer đọc evidence/Test Suite trong cùng workspace.
7. Cập nhật frontend auth types, demo identities và navigation.
8. Xây Review Queue/Review Detail và read-only Test Suites.
9. Thêm migration/backfill và Firestore indexes nếu cần.
10. Chạy toàn bộ test/lint/compile; sửa regression trước khi bàn giao.

Không thay đổi nhiều lớp cùng lúc mà không có test policy trước. Ưu tiên backend enforcement, sau đó mới nối UI.

## 13. Kiểm tra trước khi bàn giao

Đọc `AGENTS.md` ở repository root và `app/frontend/AGENTS.md` trước khi sửa. Giữ nguyên mọi thay đổi không liên quan trong worktree.

Backend/API:

```powershell
Set-Location app
$env:PYTHONPATH = (Resolve-Path .).Path
..\.venv\Scripts\python.exe -m ruff check backend tests
..\.venv\Scripts\python.exe -m pytest tests -q
```

Frontend:

```powershell
Set-Location app\frontend
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run build
```

Root regression checks theo runbook:

```powershell
Set-Location ..\..
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\ruff.exe check src\optimization tests\test_coverage_optimization.py
.\.venv\Scripts\python.exe -m py_compile src\coverup\coverup.py src\optimization\gepa.py src\optimization\metrics.py src\optimization\cli.py src\optimization\runner.py src\optimization\prompts.py src\optimization\subprocesses.py
git diff --check
```

Bàn giao phải báo rõ:

- file và endpoint đã thay đổi;
- role/workspace source trong production và demo;
- migration/index nào cần chạy;
- toàn bộ lệnh kiểm tra và kết quả;
- chưa deploy/chưa chạy live benchmark nếu chưa được yêu cầu;
- giới hạn hoặc phần còn lại, nếu có.

## 14. Ngoài phạm vi

- Role `admin` và UI quản trị người dùng.
- Reviewer tự chạy diagnostic/verification suite.
- Chuyển quyền sở hữu project/experiment.
- Nhiều role đồng thời trên cùng một tài khoản.
- Fine-grained permission editor do người dùng tự cấu hình.
- Thay đổi GEPA search, metrics, locked holdout hoặc promotion gate.
- Tự động deploy Cloud Run/Firebase hay chạy benchmark tốn chi phí.
- Không thay đổi logic lõi upload project, chạy optimize, hay tạo test suite nếu không cần thiết.
