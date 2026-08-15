# P1 — E67 Pareto output portfolio

Ngày: 2026-08-15

## Mục tiêu

Biến tín hiệu target specialization của E25 thành một output có thể chạy thật, thay vì cố ép mọi chiến
lược thành một global prompt. Thí nghiệm dùng các generated test đã cache, không gọi Gemini thêm và
không đọc/chạy split `test`.

## Protocol

- Dataset: `binh/phase1_stratified_24.jsonl`; chỉ dùng 12 validation targets thuộc 4 project.
- Prompt pool: baseline và 4 proposal unique của E25.
- Model tạo artifact gốc: `vertex_ai/gemini-3.5-flash-lite`.
- Mỗi replicate gồm output của cả 5 prompt trên cùng target set/evaluation digest `4ccf7ec798f1`.
- Chỉ nhận attempt `coverage_gain_saved`; test được deduplicate theo content trong từng project.
- Greedy weighted set-cover dùng đúng trọng số 30% statement / 70% branch.
- Suite đã chọn được chạy chung và lặp `pytest` 5 lần trước khi báo coverage.
- Bộ lọc mới `--source-replicate` cho phép đo riêng từng replicate hoặc một tập replicate.
- Holdout 4 target mới tiếp tục khóa.

## Kết quả một replicate

| Source replicate | Candidate tests | Tests giữ lại | Verified score | Gain so với best single cùng cohort |
|---:|---:|---:|---:|---:|
| 0 | 35 | 12 | 79,82% | +23,09 điểm |
| 1 | 39 | 13 | 93,78% | +31,19 điểm |
| 2 | 40 | 12 | 96,84% | +19,18 điểm |
| **Mean** | — | — | **90,15%** | — |

Ngay cả replicate yếu nhất vẫn vượt baseline cùng replicate 23,09 điểm. Mức dao động còn lớn, nên một
replicate chưa phải cấu hình ổn định để production hóa.

## Kết quả hai và ba replicate

| Source replicates | Candidate tests | Tests giữ lại | Verified score | Gain so với best single cùng cohort |
|---:|---:|---:|---:|---:|
| 0 + 1 | 74 | 13 | 96,32% | +33,74 điểm |
| 0 + 2 | 75 | 12 | 96,51% | +18,85 điểm |
| 1 + 2 | 79 | 13 | **97,59%** | +19,94 điểm |
| 0 + 1 + 2 | 114 | 13 | 97,26% | +19,61 điểm |

Mọi cặp hai replicate đều vượt 96% và cao hơn single candidate tương ứng ít nhất 18,85 điểm. Replicate
thứ ba không tạo gain rõ ràng. Kết quả ba replicate thấp hơn cặp 1+2 khoảng 0,33 điểm vì greedy set-cover
là xấp xỉ và coverage thật của suite có tương tác không được trace attribution mô hình hóa hoàn toàn;
do đó coverage sau khi chạy suite mới là số quyết định.

Suite ba replicate đạt 318/319 statements và 204/212 branch outcomes, tương ứng statement 99,69%,
branch 96,23% và aggregate 97,26%. Tất cả project đều pass khi các test được chạy chung 5 lần.

## Điều đã chứng minh và chưa chứng minh

Đã chứng minh trên validation rằng output từ các prompt chuyên biệt bổ sung coverage thật cho nhau. Đây
là cách đầu tiên trong chuỗi thí nghiệm vượt mục tiêu +10–15 điểm một cách lặp lại sau verification.

Chưa chứng minh rằng một prompt GEPA mới tốt hơn baseline, cũng chưa chứng minh generalization sang
target/repository chưa thấy. Portfolio tăng inference cost vì chạy nhiều prompt và có thể nhiều replicate.
Không dùng kết quả này để promote prompt hoặc tuyên bố production-ready.

## Quyết định

1. Chọn **hai replicate** làm cấu hình E67 ứng viên; không mặc định ba replicate.
2. Không xây classifier router ở thời điểm này: archive đã tạo suite chạy được và mạnh hơn oracle chỉ dùng
   để phân tích.
3. Bước tiếp theo là cost-aware sequential portfolio: chạy baseline trước, chỉ chạy prompt/replicate bổ sung
   cho target còn uncovered và dừng khi marginal verified gain bằng 0.
4. Chỉ sau khi policy trên được đóng băng mới mở 4-target holdout đúng một lần để quyết định có tích hợp
   vào production pipeline hay không.

## Verification

- 7 archive variants đều `verified=true` với `repeat_tests=5`.
- Targeted archive tests: 12 passed.
- Repository suite đúng phạm vi `tests/`: 121 passed.
- Không có artifact hoặc thư mục evaluation split `test` được tạo.
- Raw generated tests/archive outputs nằm trong ignore pattern `binh/phase1_candidate_archive_e25*/`.
