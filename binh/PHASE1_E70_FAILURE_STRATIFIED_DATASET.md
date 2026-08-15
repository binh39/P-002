# P1 — E70 failure-stratified benchmark

Ngày: 2026-08-15

## Mục tiêu

Tạo benchmark mới sau khi holdout E67 đã được sử dụng. Dataset phải cân bằng theo project và độ khó,
bao phủ các failure/challenge family quan trọng, không trùng target cũ và không cần gọi model để chọn
holdout.

E70 ở bước này dùng **static challenge proxy**, chưa dùng kết quả coverage để gán nhãn failure. Cách này
cho phép khóa holdout trước khi evaluation, tránh chọn target dựa trên việc model đã làm tốt hay kém.

## Artifacts đã khóa

- Dataset: `binh/e70_failure_stratified_32.jsonl`.
- Manifest: `binh/e70_failure_stratified_32_manifest.json`.
- Selection-policy commit: `0319f2c`.
- Dataset SHA-256: `8876d578f2b65e64ca113fa3e27586fce2be6956ff1e2ff238e4930ffda94fdd`.
- Holdout SHA-256: `fa029ed3f1bb2203b28a712d2d67f0c78a03d25d1aaebf2316473fd0879a815c`.
- Trạng thái holdout: `locked_unevaluated`.
- Model calls trong quá trình chọn: **0**.

## Cấu trúc dataset

| Split | Targets | Mỗi project | Easy | Medium | Hard |
|---|---:|---:|---:|---:|---:|
| Train | 16 | 4 | 4 | 8 | 4 |
| Validation | 8 | 2 | 2 | 4 | 2 |
| Locked test | 8 | 2 | 2 | 4 | 2 |

Bốn project gồm isort, mimesis, mlxtend và typesystem. Tất cả 32 identity và structural fingerprint đều
riêng biệt.

## Failure strata tĩnh

| Stratum | Train | Validation | Locked test |
|---|---:|---:|---:|
| Async/I/O | 8 | 6 | 6 |
| Branch-heavy | 4 | 1 | 2 |
| Easy regression | 3 | 1 | 2 |
| Exception paths | 5 | 3 | 2 |
| Fixture/mock-dependent proxy | 5 | 2 | 3 |
| Stateful method | 11 | 5 | 5 |
| Statement-heavy | 4 | 2 | 2 |

Một target có thể thuộc nhiều strata. `fixture_mock_dependent` là proxy từ filesystem, environment,
subprocess hoặc external dependency access; nó chưa khẳng định target chắc chắn cần fixture/mock khi chạy.

## Chống leakage

- Loại 35 identity từng xuất hiện trong `phase1_control_12`, `phase1_ablation_16`,
  `phase1_ablation_16_v2` hoặc `phase1_stratified_24`.
- Bốn target holdout E67 nằm trong tập bị loại.
- Loại cả structural fingerprint của target cũ và không cho hai target mới có cùng fingerprint.
- Selection chỉ dùng AST, static complexity và project identity; không đọc score, generated tests hoặc
  failure outcome.
- Contract test khóa dataset digest, holdout digest, split quotas, strata, difficulty và disjointness.

## Repository preflight

| Project | Import/setup |
|---|---|
| isort 6.0.1 | Passed |
| mimesis 21.0.0 | Passed |
| mlxtend 0.23.4 | Passed |
| typesystem 0.4.1 | Passed |

Preflight chỉ kiểm tra môi trường/import. Không chạy model, generated test hoặc coverage trên holdout.

## Holdout access rule

Không được dùng split `test` để sinh test, đo coverage, chọn prompt, chọn threshold hoặc sửa policy. Chỉ mở
đúng một lần sau khi candidate và baseline protocol đã được freeze trong một commit. Một phương pháp mới sau
lần mở đó phải có holdout khác.

## Bước tiếp theo

1. Chạy baseline trên **chỉ train + validation**, dùng
   `vertex_ai/gemini-3.5-flash-lite`, để gắn observed failure taxonomy và đo headroom.
2. Kiểm tra static strata nào thật sự tương quan với `test_error`, `max_attempts_exhausted`, partial coverage
   và low branch coverage.
3. Giữ hoặc điều chỉnh curriculum bằng train/validation; không thay membership của locked test.
4. Sau đó mới triển khai E40 branch/path-condition context và đánh giá repeated paired validation.

## Verification

- E70 targeted tests: 4 passed.
- Repository suite trước khi sinh artifacts: 134 passed.
- Ruff cho builder/script/tests: passed.
- Bốn project import/setup preflight: passed.
- Holdout model/coverage evaluation: chưa chạy.
