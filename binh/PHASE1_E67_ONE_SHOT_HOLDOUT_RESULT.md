# P1 — E67 one-shot holdout result

Ngày: 2026-08-15

## Kết luận

E67 **không vượt qua promotion gate về coverage**. Cost-aware sequential policy giảm số lượt sinh test,
nhưng toàn bộ coverage cuối cùng đến từ baseline replicate 0. Các prompt Pareto/proposal và các replicate
bổ sung không tạo thêm một statement hoặc branch nào trên holdout mới.

Không chạy lại, không đổi threshold và không tune prompt theo kết quả này. Split `test` hiện đã được dùng và
không còn là holdout hợp lệ cho một phương pháp E67 sửa đổi.

## Điều kiện đã khóa trước khi chạy

- Freeze commit: `44baed8` (`feat: freeze live sequential holdout policy`).
- Dataset: `binh/phase1_stratified_24.jsonl`.
- Dataset SHA-256: `15dd9247ede13a1566346069f8418b378200c57551749125b2743080f44a878e`.
- Split: `test`, 4 target thuộc 4 project.
- Model sinh test: `vertex_ai/gemini-3.5-flash-lite`.
- Stop score: `0.80`.
- Schedule: 7 stage đã khóa từ validation, tối đa 5 prompt × 3 replicate.
- Verification: chạy suite hợp nhất 5 lần.
- Policy digest: `3659267d3242fbea3dfd4cd67d0b7d868538e1654576355860ace2c06ecf267e`.

## Kết quả tổng hợp

| Cấu hình | Score | Statements | Branches | Gain so với baseline |
|---|---:|---:|---:|---:|
| Baseline `d8123dc403839c22`, replicate 0 | **89,48%** | 93/101 (92,08%) | 76/86 (88,37%) | — |
| Sequential portfolio sau verification | **89,48%** | 93/101 (92,08%) | 76/86 (88,37%) | **0,00 điểm** |

Suite cuối có 4 test, tất cả đều xuất phát từ baseline replicate 0. Verification thành công trên cả bốn
project và toàn bộ test được chạy lặp 5 lần.

## Chi phí theo target-generation proxy

| Chỉ số | Kết quả |
|---|---:|
| Calls thực tế | 10 |
| Full cohort 5 prompt × 3 replicate × 4 target | 60 |
| Calls tránh được | 50 |
| Tiết kiệm proxy | **83,33%** |

Proxy này chỉ đếm một lần sinh cho một target tại một prompt/replicate. Nó không đại diện chính xác cho token,
provider retry hoặc chi phí tiền thật.

## Diễn biến theo stage

| Stage | Prompt / replicate | Target được chạy | Test hợp lệ | Marginal coverage units |
|---:|---|---:|---:|---:|
| 0 | baseline / 0 | 4 | 4 | 168 |
| 1 | pure Pareto / 0 | 1 | 1 | 0 |
| 2 | 50/50 / 0 | 1 | 0 | 0 |
| 3 | shared proposal / 0 | 1 | 1 | 0 |
| 4 | 50/50 / 1 | 1 | 0 | 0 |
| 5 | baseline / 1 | 1 | 1 | 0 |
| 6 | baseline / 2 | 1 | 1 | 0 |

Sau stage đầu, ba target đã vượt stop score. Sáu stage sau chỉ chạy target khó
`typesystem/json_schema.py::from_json_schema`, nhưng không stage nào bổ sung coverage.

## Coverage theo target

| Project / target | Verified score | Statements | Branches |
|---|---:|---:|---:|
| isort — `section_key` | 89,38% | 27/28 | 19/22 |
| mimesis — `SchemaBuilder._resolve_value` | 100,00% | 11/11 | 10/10 |
| mlxtend — `EnsembleVoteClassifier.fit` | 96,34% | 30/31 | 25/26 |
| typesystem — `from_json_schema` | 79,19% | 25/31 | 22/28 |

## Phân tích thất bại

- Hai lượt của prompt 50/50 đạt 0 và hết retry do assertion sai quanh `Reference`, `String`, `AllOf` và
  `Union`; không có test được lưu.
- Pure Pareto, shared proposal và baseline replicate 1/2 tạo test hợp lệ cho target typesystem, nhưng đều
  phủ đúng tập coverage mà baseline replicate 0 đã phủ.
- Gain 19,28 điểm trên validation không tổng quát hóa sang bốn target holdout. Kết quả validation có dấu hiệu
  phụ thuộc target/selection và không chứng minh được một policy inference tốt hơn baseline.
- Mục tiêu cải thiện 10–15 điểm trên dữ liệu chưa thấy **chưa đạt**.

## Quyết định

1. Reject E67 portfolio khỏi production promotion với tư cách cải tiến coverage.
2. Giữ baseline global prompt hiện tại; không thay bằng prompt Pareto/proposal của E67.
3. Có thể giữ executor cost-aware như hạ tầng thử nghiệm vì gate chi phí hoạt động đúng, nhưng không quảng bá
   nó là cải tiến chất lượng.
4. Nếu thử phương pháp mới, phải thiết kế và khóa một benchmark/holdout mới trước khi đánh giá. Không dùng kết
   quả của split `test` này để sửa E67 rồi báo lại như một kiểm định độc lập.

## Artifacts

Raw artifacts được ignore khỏi Git:

- `binh/phase1_candidate_archive_e67_holdout/candidate_test_archive.json`
- `binh/phase1_runs/e67_holdout_one_shot/`
