# E49 — Full-validation 8-target (CAND): kết quả + chẩn đoán SFS blocker

> **Trạng thái: ĐÃ CHẠY** replicate r0 + r1 (2-replicate), theo config CAND kế thừa E48.
> Người dùng đã duyệt chi phí ("Ổn rồi chạy đi"). Toàn bộ số liệu dưới đây là **thật**,
> trích từ `record.json` trên đĩa (`eval/prompt_optimization/runs/3a5a78e405676b45-a592e6b46564*/`),
> không phải ước lượng. Ghi chú: **lớp transport/proxy tiếp tục bóp méo tool output** trong
> phiên này; dữ liệu trên đĩa vẫn sạch.

---

## 1. Mục tiêu

Áp dụng config CAND (đã đo tốt trên SFS: E48 mean 0.8150) ra **toàn bộ 8 target split
validation**, so aggregate với baseline lịch sử E42 (0.0804), và áp decision-rule:
promotte chỉ khi **overall pass-rate ≥ 90%** (mỗi target ≥ 0.9, không phải aggregate mean).

## 2. Cấu hình chạy

| Tham số | Giá trị |
|---|---|
| model | `vertex_ai/gemini-3.5-flash-lite` (từ `COVERUP_MODEL`) |
| prompt | `cloud/inputs/gpt_v2_baseline.json` (digest `3a5a78e405676b45`, có lever B nudge) |
| dataset | `binh/e70_failure_stratified_32.jsonl`, split **validation** (8 target) |
| evaluation-replicates | **2** (r0 + r1 trung bình) |
| max-attempts | **5** (lever C) |
| repeat-tests / concurrency | 2 / 1 |
| target-context / failure-context | on, 6000 / on, 4000 |
| salvage-failing-tests | on, max-prunes 8 |

Runs: `multi-project-validation-batch-2a087a1b` (rep 0), `multi-project-validation-batch-0b88fe57` (rep 1).

## 3. Kết quả (mean 2 replicate)

**Aggregate: `0.6055`** — statement 0.7151, branch 0.5585.

| target | score |
|---|---|
| isort::find_imports_in_file | **1.000** |
| isort::get_output | **1.000** |
| mimesis::SchemaBuilder.__repr__ | **1.000** |
| mimesis::override_locale | **1.000** |
| mlxtend::BootstrapOutOfBag.split | **1.000** |
| mlxtend::SequentialFeatureSelector.fit | **0.574** |
| typesystem::ValidationResult.__iter__ | **1.000** |
| typesystem::EmailFormat.serialize | **1.000** |

**Pass-rate (each ≥ 0.9): 7/8 = 87.5%** → **CHƯA promotable** (dưới ngưỡng 90%).

### So với baseline E42 (0.0804)
- Aggregate tăng **0.0804 → 0.6055**.
- **7 target vốn full-score (1.0) giữ nguyên 1.0 — không hồi quy.**
- Target duy nhất từng zero (SFS) lên **~0.574**, nhưng chưa qua ngưỡng.

### Đếm model calls (từ attempt_traces, khác tiền)
- r0: 6 SFS-traces = 1 initial + 4 error + 1 salvage (SFS dùng hết budget).
- r1: 3 SFS-traces = 1 initial + 1 error + 1 salvage (thành công sớm hơn).
- Toàn bộ 8 target **không dùng hết** 5×8 trần — hầu hết thành công ở attempt đầu.

## 4. Chẩn đoán SFS blocker (root cause — khác với giả định ban đầu!)

### Lỗi chặn (lặp lại ở cả 2 replicate, attempt 2):

```
File src/sample_repo/mlxtend/mlxtend/feature_selection/sequential_feature_selector.py:229
AttributeError: Estimator must have an ._estimator_type for infering `scoring`
```

Code tại dòng 223–229:
```python
self.clone_estimator = clone_estimator
if self.clone_estimator:
    self.est_ = clone(self.estimator)   # dòng ~223: clone estimator
else:
    self.est_ = self.estimator

self.scoring = scoring
if self.scoring is None:
    if not hasattr(self.est_, "_estimator_type"):   # dòng 229
        raise AttributeError("Estimator must have an ._estimator_type for infering `scoring`")
```

### Nguyên nhân thật (đã verify offline, không tốn chi phí)
[QUAN TRỌNG — verify lại bằng code, chẩn đoán ban đầu trong bản nháp ĐÃ SAI, đây là bản đúng.]

Trong môi trường venv **sklearn 1.9.0**, probe trực tiếp từng estimator:
`KNeighborsClassifier`, `LogisticRegression`, `LinearRegression`, `DecisionTreeClassifier`,
`RandomForestClassifier`, `GaussianNB`, `SVC`, `LinearDiscriminantAnalysis` — **KHÔNG estimator
nào có `_estimator_type`** (`hasattr(...)==False`). Kiểm sâu: `ClassifierMixin` source KHÔNG có
assignment `_estimator_type` nào, MRO của `DecisionTreeClassifier` không chứa attr.

⇒ **Trong sklearn 1.9.0, KHÔNG có estimator nào khai báo `_estimator_type` ở class scope.**
Đây là khác biệt so với sklearn <1.6 (nơi `ClassifierMixin._estimator_type = "classifier"`).
Hệ quả: mlxtend `SFS.__init__` nhánh `scoring=None` → `if not hasattr(self.est_, "_estimator_type")`
luôn đúng → **luôn văng `AttributeError`** khi `scoring` không được truyền, **bất kể model chọn
estimator nào**.

Cách duy nhất để SFS chạy: **truyền `scoring="<string>"` tường minh** vào `SequentialFeatureSelector(...)`
(vd `scoring="accuracy"`/`scoring="r2"`). Khi `scoring != None` nhánh trên không bước vào → hết lỗi.
(Model đã tự phát hiện đúng ở try3+ với `LinearRegression` + `scoring="r2"` → constructor hết lỗi.)

### Chuỗi đốt budget thật (r0 7a1b)
- **try2:** `KNeighborsClassifier`, `scoring=None` → `AttributeError: _estimator_type` ở constructor.
- **try3/4/5:** model sửa thành `LinearRegression` + `scoring="r2"` → **constructor hết lỗi**, nhưng
  model lại thêm test `test_sfs_fit_keyboard_interrupt` dùng **`_TESTING_INTERRUPT_MODE = True`** +
  `pytest.raises(KeyboardInterrupt)`. Hook `_TESTING_INTERRUPT_MODE` **không tồn tại trong API thật**
  của SFS → không raise KeyboardInterrupt → `Failed: DID NOT RAISE KeyboardInterrupt` → test module
  bị coi là fail (vì có 1 test fail), salvage giữ lại các test pass nhưng **coverage gain không đủ**
  → SFS dừng ở ~0.50–0.64, không qua ngưỡng. (r1 fe57 thành công sớm hơn: try3 = coverage_gain_saved.)
- Một test fail trong module **chặn toàn bộ** (liên kết kết luận E42/E46 "module accepted/rejected as a whole").

### Kết luận cho lever A — SAI LỆCH CẦN SỬA TRONG CODE
Lever A (`_clone_pitfall_context`) đã **kích hoạt** trong các replicate này (lỗi chứa `_estimator_type`
✓, source chứa `clone_estimator`/`clone(` ✓), nhưng lời khuyên của nó **có phần vô dụng trong env này**:
nó nói "use an estimator that already declares `_estimator_type` at class scope" — mà **không estimator
nào trong sklearn 1.9.0 có attr đó**. Đây là điểm code cần sửa (mục kế hoạch): khuyến **truyền
`scoring="<string>"` tường minh** là con đường khả dụng duy nhất, đồng thời cảnh báo đừng viết test
private-hook như `_TESTING_INTERRUPT_MODE`.

---

## 5. Verdict & ghi nhận

- E49 xác nhận **toàn validation cải thiện lớn**: 7/8 target giữ full-score, SFS thoát 0
  lên ~0.574, aggregate 0.0804 → 0.6055.
- **CHƯA promotable** theo decision-rule (pass-rate 87.5% < 90%) vì SFS chưa qua 0.9.
- Root cause mới rõ: cần fix nhánh `scoring=None` (truyền `scoring=` hoặc dùng estimator có
  `_estimator_type`). Lever A hiện chưa xử lý đúng trường hợp này — đây là bước kế.
