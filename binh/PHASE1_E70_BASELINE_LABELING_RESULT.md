# P1 — E70 baseline failure labeling

Ngày: 2026-08-15

## Kết luận

Baseline labeling trên 24 target train + validation đã tìm thấy headroom tập trung rất rõ. Có 20/24 target
đạt 100%, hai target đạt partial coverage và hai target hard đạt 0%. Hai target bằng 0 chiếm 99,64% statement
headroom và 95,24% branch headroom.

Đây là bằng chứng mới cho thấy mục tiêu +10–15 điểm có thể đạt bằng cách sửa đường sinh test cho một nhóm hard
target rất nhỏ, thay vì tiếp tục tối ưu một global prompt trên toàn bộ target.

Split `test` E70 không được nạp, không sinh test và không đo coverage.

## Protocol đã khóa

- Protocol commit: `18bf91f`.
- Dataset SHA-256: `8876d578f2b65e64ca113fa3e27586fce2be6956ff1e2ff238e4930ffda94fdd`.
- Prompt baseline: `d8123dc403839c22`.
- Model: `vertex_ai/gemini-3.5-flash-lite`.
- Splits: chỉ train + validation; test bị cấm.
- Replicates: 1.
- `max_attempts=3`, `repeat_tests=2`, `max_concurrency=4`.
- E41 target-contract context bật; repository-test context tắt.

## Coverage

| Split | Targets | Aggregate | Statements | Branches |
|---|---:|---:|---:|---:|
| Train | 16 | 48,95% | 144/280 (51,43%) | 91/190 (47,89%) |
| Validation | 8 | 8,04% | 29/172 (16,86%) | 4/94 (4,26%) |
| Combined calibration | 24 | **34,90%** | 173/452 (38,27%) | 95/284 (33,45%) |

Mean target score của combined calibration là 91,09%. Chênh lệch lớn giữa mean target và aggregate micro-score
đến từ hai hàm rất lớn bằng 0; aggregate đúng chủ đích vì executable units của các hàm này không bị làm nhẹ đi.

## Kết quả theo difficulty

| Difficulty | Targets | Micro-score | Mean target | Zero | Full |
|---|---:|---:|---:|---:|---:|
| Easy | 6 | 100,00% | 100,00% | 0 | 6 |
| Medium | 12 | 100,00% | 100,00% | 0 | 12 |
| Hard | 6 | **29,06%** | 64,36% | 2 | 2 |

Static difficulty band đã phân tách đúng failure risk trong lượt này: mọi easy/medium target đạt full coverage,
còn toàn bộ zero và exhausted event nằm trong hard band.

## Hai bottleneck quyết định

### isort — `Config.__init__`

- Train, 0/135 statements và 0/90 branches.
- Strata: async/I/O, branch-heavy, exception, fixture/mock-dependent, stateful, statement-heavy.
- Ba repair lần lượt thất bại vì assertion sai, import `pkg_resources` không tồn tại và giả định sai về path/cwd.
- Terminal: `max_attempts_exhausted`.

### mlxtend — `SequentialFeatureSelector.fit`

- Validation, 0/143 statements và 0/90 branches.
- Strata: async/I/O, branch-heavy, exception, stateful, statement-heavy.
- Cả ba attempt dùng estimator không có `._estimator_type`; repair lặp lại cùng lỗi thay vì retrieve contract
  của estimator/scoring.
- Terminal: `max_attempts_exhausted`.

Hai target này có tổng denominator 278 statements và 180 branches. Chúng chiếm 99,64% trong 279 statement
chưa phủ và 95,24% trong 189 branch chưa phủ.

## Failure taxonomy quan sát

- 35 model generation/repair attempts cho 24 target.
- 22 terminal `coverage_gain_saved`.
- 2 terminal `max_attempts_exhausted`.
- 13 `test_error` trước terminal outcome.
- Failure events: 5 assertion, 5 attribute, 2 import, 1 type, 4 partial-coverage và 2 exhausted marker.

## Khả năng đạt +10–15 điểm

Nếu hai zero target cùng đạt khoảng 10% statement/branch coverage, combined aggregate dự kiến tăng khoảng
6,28 điểm. Nếu đạt khoảng 20%, gain dự kiến khoảng **12,56 điểm**. Đây là phép tính denominator-based, không
phải kết quả candidate đã chạy, nhưng nó xác định một mục tiêu kỹ thuật cụ thể và đủ headroom.

## Quyết định kỹ thuật

1. Không ưu tiên tăng GEPA budget hoặc sửa global prompt chung: 22/24 target đã có test hợp lệ và 20 target
   đã full coverage.
2. E40 exact branch/path context chỉ hữu ích sau khi test setup chạy được; nó không tự sửa hai root failure
   hiện tại.
3. Ưu tiên một ablation hẹp kết hợp E42/E44: failure-triggered retrieval cho constructor/callee/usage contract,
   estimator protocol, filesystem/environment semantics và module exports.
4. Retrieval chỉ kích hoạt sau failure phù hợp; không bật lại E43 repository-test dump toàn cục đã bị reject.
5. Chạy ablation trước trên train hard targets, rồi paired validation. Không mở E70 test trước khi candidate
   và protocol được freeze.

## Artifacts

- Tracked summary: `binh/e70_baseline_labeling_summary.json`.
- Analyzer: `scripts/analyze_failure_stratified_baseline.py`.
- Raw runs (Git-ignored): `binh/phase1_runs/e70_baseline_labeling_r1/`.
- Train evaluation digest: `a44da3d67f1d`.
- Validation evaluation digest: `709c5d9915c1`.
