# Kế hoạch bước tiếp + Phân tích thiếu thí nghiệm

> Kế hoạch sau khi chạy E49 (full-validation 8-target, CAND). Kết quả chi tiết xem
> `PHASE1_E49_FULL_VALIDATION_RESULT.md`. Mọi hành động chạy model cần duyệt chi phí.

---

## 1. Tổng hợp kết quả đạt được sau các thí nghiệm

| Thí nghiệm | Phạm vi | Kết quả | Ý nghĩa |
|---|---|---|---|
| E42–E44/E46 failure-context | train smoke + validation 8 | validation baseline **0.0804**, tie do-not-promote | SFS là target zero duy nhất kéo aggregate |
| E47 (–) | SFS | SFS 0.0 | bẫy clone + cấu trúc test sai |
| **E48** probe SFS | 1 target | BASE **0.7064** / CAND **0.8150** (3-rep) | lever B làm SFS chạy được; lever C +10.9 |
| **E49** full validation | 8 target (2-rep) | aggregate **0.6055**, pass-rate **87.5%**; 7/8 full, SFS **0.574** | 7 target giữ full; SFS là rào duy nhất còn lại |

**Điểm mấu chốt đã tìm ra (2 blocker thật, verify bằng code + record.json):**

1. **sklearn 1.9.0 không estimator nào có `_estimator_type`** — probe từng loại
   (`KNeighborsClassifier`, `LogisticRegression`, `LinearRegression`, `DecisionTreeClassifier`,
   `RandomForestClassifier`, `GaussianNB`, `SVC`, `LDA`) đều `hasattr==False`; `ClassifierMixin`
   source không có assignment, MRO `DecisionTreeClassifier` không chứa attr.
   ⇒ `SFS.__init__` nhánh `scoring=None` (`if not hasattr(self.est_,"_estimator_type")`) **luôn
   văng AttributeError bất kể estimator nào**, khi `scoring` không được truyền.
   ⇒ **Cách duy nhất: truyền `scoring="<string>"` tường minh** (model đã tự đúng ở try3:
   `LinearRegression` + `scoring="r2"` → constructor hết lỗi).
2. **Blocker thứ hai đốt budget**: sau khi sửa `scoring`, model viết test dùng hook private
   `_TESTING_INTERRUPT_MODE = True` + `pytest.raises(KeyboardInterrupt)` — hook **không tồn tại**
   trong API thật → `DID NOT RAISE KeyboardInterrupt` → 1 test fail chặn toàn bộ module → coverage
   không lưu.
   ⇒ Cần hint: **đừng probe private `_TESTING_*` hook**, thay bằng assertion trên hành vi thật
   (vd `fitted`, `k_feature_idx_`, `subsets_`), hoặc chia nhỏ test và để salvage giữ các test pass.

## 2. Rào cản hiện tại

- 8/8 target: 7 đã full, **duy nhất SFS ≠ 1.0** (bước D trung bình 2-rep = 0.796; r1 = 0.911, r0 = 0.681).
- SFS cần ≥ 0.9 **bền vững** để pass-rate đủ 90%.
- ✅ Lever A **đã sửa** (Bước A): bỏ khuyến nghị vô dụng `_estimator_type` class-scope; giờ khuyến
  **truyền `scoring="<chuỗi>"` tường minh** (đường duy nhất hợp lệ trong sklearn 1.9.0) + cảnh báo
  private `_TESTING_*` hook. Đã xác nhận **kích hoạt thật** trong Bước C & D (hint `scoring='accuracy'`
  xuất hiện trong repair trace của SFS, lỗi `_estimator_type` constructor hết).
- Rào còn lại: **phương sai SFS giữa các replicate** (0.68 → 0.91). Cần thêm replicate để chứng minh
  ≥0.9 bền, trước khi promote.

## 3. Bước tiếp theo (theo thứ tự ưu tiên)

### Bước A — ✅ ĐÃ HOÀN THÀNH (code, KHÔNG tốn model)
1. ✅ Sửa `_clone_pitfall_context` trong `src/coverup/target_context.py`:
   - Bỏ khuyến nghị sai "use an estimator that declares `_estimator_type` at class scope"
     (không estimator nào đạt trong sklearn 1.9.0, đã probe).
   - Thêm khuyến nghị đúng: **truyền `scoring="<chuỗi>"` tường minh** vào
     `SequentialFeatureSelector(...)` — đường duy nhất để SFS nhận `scoring != None`.
   - Thêm `_private_test_hook_context` + section `[PRIVATE TEST HOOK]`: cảnh báo đừng probe
     private `_TESTING_*` hook (gây `DID NOT RAISE KeyboardInterrupt` → 1 test fail chặn module).
2. ✅ Thêm 3 test mới `tests/test_clone_pitfall.py` (6 test) → **6 passed**.
3. ✅ Verify: `pytest tests -q` = **154 passed**, `ruff` sạch, `py_compile` OK. Không regression.

### Bước B — (ĐÃ LOẠI) verify estimator có `_estimator_type`
Probe kết luận **không estimator nào đạt trong sklearn 1.9.0** — vô nghĩa. Hint `scoring=` bắt buộc.

### Bước C — ✅ ĐÃ CHẠY probe SFS 1-target với lever A mới (3-rep, cache lạnh)
1. ✅ Chạy SFS probe (`e70_e42_e44_validation_sfs_probe.jsonl`) với config CAND + lever A mới,
   **artifacts-dir mới `eval/prompt_optimization_leverA`** (ep cache replay E48).
2. **Kết quả (mean 0.7485):**
   | rep | score | stmt | branch |
   |---|---|---|---|
   | r0 | 0.5331 | 0.636 | 0.489 |
   | r1 | 0.8315 | 0.853 | 0.822 |
   | r2 | 0.8809 | 0.888 | 0.878 |
   | **mean** | **0.7485** | — | — |
   → **CHƯA đạt 0.9** (0/3 ≥ 0.9).
3. **Lever A đã kích hoạt thật**: cả 3 replicate có `[CLONE/REBUILD PITFALL]` ở trace repair
   (r0@t1, r1@t1, r2@t1); `[PRIVATE TEST HOOK]` bắn ở r1@t3. → **lever A giờ chạy thật trên model**.
4. So E48 CAND (0.8150) / E49 SFS (0.574): lever A mean 0.7485 nằm giữa, **chưa vượt 0.9**.
   Kết quả này **không đủ promotable cho SFS** và **thấp hơn E48 CAND mean (0.8150)** —
   cần điều tra (nhưng lever A đã chứng minh kích hoạt + đổi hành vi model: r1/r2 đều >0.83).
   ⚠️ Lưu ý: 2 lần chạy đầu tiên của lệnh này bị **cache replay trả về E48 (c101ff14, score 0.8150)**
   vì digest không hash `target_context.py` (lever A runtime). Bản ghi này dùng cache lạnh nên là thật.

### Bước D — ✅ ĐÃ CHẠY lại full validation 8-target với lever A mới (2-rep, cache lạnh)
Chạy với artifacts-dir mới `eval/prompt_optimization_leverA_fullval` (tránh cache replay E49).
Runs: `multi-project-validation-batch-8ac7b6fe` (r0), `448891ea` (r1).

| target | r0 | r1 | mean |
|---|---|---|---|
| isort::find_imports_in_file | 1.000 | 1.000 | 1.000 |
| isort::get_output | 1.000 | 1.000 | 1.000 |
| mimesis::SchemaBuilder.__repr__ | 1.000 | 1.000 | 1.000 |
| mimesis::override_locale | 1.000 | 1.000 | 1.000 |
| mlxtend::BootstrapOutOfBag.split | 1.000 | 1.000 | 1.000 |
| **mlxtend::SFS.fit** | 0.681 | **0.911** | 0.796 |
| typesystem::ValidationResult.__iter__ | 1.000 | 1.000 | 1.000 |
| typesystem::EmailFormat.serialize | 1.000 | 1.000 | 1.000 |

- Per-replicate aggregate: **r0 = 0.7046**, **r1 = 0.9173** → mean **0.8109** (stmt 0.866, branch 0.787).
- **7/8 target giữ full-score 1.0 cả 2 replicate (không hồi quy).**
- **SFS target r1 đạt 0.911 ≥ 0.9** — lever A hint (`scoring='accuracy'`) đã loại lỗi `_estimator_type`
  ở constructor (generated test giờ bỏ `scoring=` đúng); lỗi còn lại chuyển sang `k_features tuple`.
- **Lever A kích hoạt thật** trong run này (xác nhận trong prompt_input trace repair).
- So E49 (0.6055): tăng lên 0.8109; nhưng **r0 SFS 0.681 <0.9** nên pass-rate **chưa bền 100%** ở 2-rep:
  pass-rate theo r1 = 100% (8/8), theo r0 = 87.5% (SFS 0.681). → **promotion cần thêm replicate để xác nhận
  SFS vượt 0.9 bền vững.**

### Bước E — Decision & rollout
1. Áp decision-rule pass-rate ≥ 90% → nếu đạt: **promotte**.
2. Rollout lever ra dòng chính. **Mở holdout `test` tối đa 1 lần** (Agent.md) — cần duyệt
   chi phí riêng, chỉ sau khi full validation thắng.

---

## 4. Còn thiếu những thí nghiệm nào để chứng minh "tool tốt hơn baseline 10–15%"?

Để khẳng định **phương pháp cải thiện** (không chỉ một số may mắn), cần lấp các khoảng sau:

1. **Full validation post-fix (lặp lại ít nhất 2–3 replicate)** — chứng minh cải thiện vượt
   90% pass-rate là **bền vững**, không phải 1 lần. *(Quan trọng nhất.)*
2. **Replicates đủ cho SFS** — hiện 2-rep mean SFS 0.796 (r0 0.681 / r1 0.911); cần 3+ rep
   để bớt phương sai.
   - **Diagnosis từ disk (source + record) cho phương sai r0/r1:** gap của SFS
     không còn là lỗi `scoring` (đã hết) mà là **độ phủ của nhánh input-validation/error-case**
     và **nhánh floating-backward hiếm** trong `SequentialFeatureSelector.fit`:
     - r0: còn **37 lines / 31 branches** — test chạm các nhánh *validation-error* đầu `fit`
       (`fixed_features` mixed types, `feature_groups` mappers/union, `k_features` tuple/int
       invalid, dòng 353–479), nhưng **không vào được vòng float-backward** (đuôi 556–617).
     - r1: còn **9 lines / 9 branches** — chỉ thiếu nhánh hiếm: `k_features=='parsimonious'`
       (497), verbose stderr (570), rẽ break/accept trong vòng floating (579/605/611/614).
     - ⇒ Tín hiệu: test càng chạm **error-case + floating-backward** thì SFS càng áp 0.9;
       r1 áp 0.911 vì test bao đủ path hợp lệ lẫn nhánh hiếm; r0 thiếu mảng flag
       floating/parsimonious nên dừng 0.68.
   - ✅ **ĐÃ THÊM lever D** (`_sfs_branch_completion_context`) — tốn code, KHÔNG tốn model:
     hint nhắc model **chạm nhánh `k_features` string (`'best'`/`'parsimonious'`) +
     forward-with-floating** + `verbose` + error-case `fixed_features`/`feature_groups`.
     Fires khi target là SFS-style `fit` (có đủ marker `k_features/feature_groups/floating/forward`)
     và error là `AttributeError`/`ValueError`. Verify:
     `test_clone_pitfall.py` 10 passed (thêm 4 test), full suite **158 passed**, py_compile + ruff sạch.
   - ✅ **ĐÃ CHẠY SFS probe 3-rep lever A+D** (`eval/prompt_optimization_leverAD`, cache lạnh,
     model vertex_ai/gemini-3.5-flash-lite, prompt digest 3a5a78e405676b45):
     | rep | SFS | stmt | branch | n_attempts |
     |---|---|---|---|---|
     | r0 | 0.8851 | 0.9021 | 0.8778 | 4 |
     | r1 | 0.8456 | 0.8741 | 0.8333 | 5 |
     | r2 | 0.8908 | 0.8951 | 0.8889 | 3 |
     | **mean** | **0.8738** | — | — | 4.0 |
     → **0/3 ≥ 0.9** → chưa promotable (dưới ngưỡng). Tuy nhiên: mean 0.8738 > E48 CAND
     (0.8150) và > Bước D mean SFS (0.796); phương sai thu hẹp (0.846–0.891 so với
     Bước D 0.681–0.911); r0=0.8851 (sát 0.9). Lever D kích hoạt thật (3× `[SFS BRANCH
     COMPLETION]` trong repair prompt r0) và `[CLONE/REBUILD PITFALL]` 2×.
   - **Blocker còn lại (từ disk, chính xác):** 9–11 branch ổn định ở **vòng floating-backward**
     đuôi fit (556–617). Model ĐÃ viết `forward=True, floating=True, verbose=1` và
     `k_features='parsimonious'` (theo lever D), nhưng **vòng floating body chưa chạy** vì guard
     tại dòng 570–575: `if self.forward and (len(k_idx) - len(fixed)) <= 2: break` — test dùng
     `k_features=2` + 3 cột X → `2-0 <= 2` → **luôn break ngay, không vào body 579–621**.
   - ✅ **ĐÃ tinh chỉnh lever D** (code, 0 model): hint giờ chỉ dẫn dùng đủ cột + target đủ cao
     (vd `k_features=3` với X ≥ 4 cột, hoặc forward+floating với `len(k_idx) - len(fixed) > 2`)
     để vòng floating body được đi vào. Verified: clone_pitfall 10 passed, full **158 passed**,
     py_compile + ruff sạch.
   - ✅ **ĐÃ CHẠY SFS probe 3-rep lever A+D tinh chỉnh** (`eval/prompt_optimization_leverAD2`):
     | rep | SFS | stmt | branch | n_attempts |
     |---|---|---|---|---|
     | r0 | **0.9626** | 0.9790 | 0.9556 | 5 |
     | r1 | 0.7363 | 0.7692 | 0.7222 | 3 |
     | r2 | 0.7025 | 0.7343 | 0.6889 | 4 |
     | **mean** | **0.8005** | — | — | — |
     → **1/3 ≥ 0.9** (chỉ r0). Mean 0.8005 **thấp hơn** pre-refinement (0.8738) và **cao hơn**
     Bước D (0.796). Phương sai **rộng trở lại** (0.703–0.963). r1/r2 hồi quy nặng (25–28 branch
     còn) — test không cover cả error-branch lẫn floating.
   - **Đọc trung thực:** refinement giúp r0 đạt 0.96 (test dùng `k_features=3` + đủ cột → chạm
     floating body), NHƯNG r1/r2 tệ hơn (generation variance lấn át tín hiệu). Không phải cải
     thiện bền vững trên decision-rule (cần mọi replicate ≥0.9).
   - ✅ **ĐÃ CHẠY round 2 (3 rep nữa, `eval/prompt_optimization_leverAD3`)**: [0.9069, 0.9210, 0.9210]
     → **3/3 ≥ 0.9**, mean 0.9163. r0 dùng `k_features=3` + đủ cột + `floating=True` (theo hint)
     → còn 8 branch (đuôi float edge 556/570/579/605/611/614).
   - **Gộp 6 draw lever A+D tinh chỉnh** (AD2 + AD3): scores=[0.7025, 0.7363, 0.9069, 0.9210, 0.9210, 0.9626]
     mean **0.8584**, median **0.914**, **count≥0.9 = 4/6 (67%)**, min/max 0.7025/0.9626.
   - **Đọc trung thực:** refinement rõ là có tác dụng (round 2 = 3/3 ≥0.9, median 0.914), nhưng variance
     cross-round vẫn lớn (AD2 round 1 tệ 0.70��0.74; AD3 round 2 tốt 0.91). Tỉ lệ hit ≥0.9 gom 6 draw ≈ 67%,
     **chưa đủ bền vững để promote theo hard decision-rule mọi replicate ≥0.9** (1 replicate sẽ fail gate).
   - ✅ **User chọn: chạy thêm replicate xác nhận** (a). Khởi chạy AD4 round 3:
     `--artifacts-dir eval/prompt_optimization_leverAD4`, `--evaluation-replicates 3`, cùng dataset
     `binh/e70_e42_e44_validation_sfs_probe.jsonl` + `cloud/inputs/gpt_v2_baseline.json` (digest
     3a5a78e405676b45), max-attempts 5, repeat 2, concurrency 1, failure-context max 4000, salvage 8,
     target-context on, model vertex_ai/gemini-3.5-flash-lite. Artifacts dir MỚI để tránh cache replay.
     (launcher: `binh/launch_ad4.sh`)
   - ✅ **ĐÃ CHẠY round 3 (`eval/prompt_optimization_leverAD4`, 3 rep, cache lạnh - batch id mới
     84bd7839/e6af2787/5af784bc)**: scores = [0.5642, 0.7166, 0.8746] → **0/3 ≥0.9**.
     - r0 0.5642: 4 attempt đều `test_error` → salvage; còn 52 lines / 42 branches — test chỉ cover path
       cơ bản, KHÔNG chạm block error-case validation (343–492) lẫn floating tail (611–617).
     - r1 0.7166: vẫn thiếu error-case 431–492 + floating 576–617 (còn 35 lines).
     - r2 0.8746: cover được hầu hết error-validations nhưng còn 19 lines (470/473/480/483 = tuple max
       out-of-range, floating accept tail 611–617, verbose 624).
   - **Gộp 9 draw post-refinement lever D (AD2+AD3+AD4):**
     scores=[0.5642, 0.7025, 0.7166, 0.7363, 0.8746, 0.9069, 0.9210, 0.9210, 0.9626]
     mean **0.7895**, median **0.8746**, **count≥0.9 = 4/9 (44%)**, min/max 0.5642/0.9626.
   - **Đọc trung thực (kết luận):** variance cross-round GIỜ RÕ LÀ YẾU TỐ CHỦ ĐẠO, không phải cải thiện
     bền vững. Refinement có tác dụng đúng hướng nhưng chỉ thể hiện khi model tình cờ viết đủ bộ test
     error-case + floating; round 3 cho thấy hết lần này đến lần khác model rơi vào `test_error` loop rồi
     salvage (vẫn dương nhưng thấp). E round-2 3/3 ≥0.9 là **lucky streak**, không lặp lại.
     → **Không promote lever D theo hard decision-rule mọi replicate ≥0.9** (rd hit-rate ≈44-67%, không bền).
   - ✅ **User quyết định (b): thư giãn gate → promote lever A+D theo aggregate.** Không claim per-replicate
     bền; ghi rõ là improvement theo aggregate (median 0.875, 6/9 ≥0.85, mean 0.789 vs baseline SFS 0.574).
   - ✅ **ĐÃ CHẠY full 8-target validation với lever A+D** (`eval/prompt_optimization_leverAD_fullval`,
     2 rep, cache lạnh - eval digest a592e6b46564):
     | target | r0 | r1 | mean |
     |---|---|---|---|---|
     | isort::find_imports_in_file | 1.000 | 1.000 | 1.000 |
     | isort::get_output | 1.000 | 1.000 | 1.000 |
     | mimesis::SchemaBuilder.__repr__ | 1.000 | 1.000 | 1.000 |
     | mimesis::override_locale | 1.000 | 1.000 | 1.000 |
     | mlxtend::BootstrapOutOfBag.split | 1.000 | 1.000 | 1.000 |
     | **mlxtend::SFS.fit** | 0.6855 | **0.9309** | 0.8082 |
     | typesystem::ValidationResult.__iter__ | 1.000 | 1.000 | 1.000 |
     | typesystem::EmailFormat.serialize | 1.000 | 1.000 | 1.000 |
     - Per-replicate pass-rate (target ≥0.9): r0 = 7/8 (87.5%, SFS 0.6855 fail), r1 = 8/8 (100%) →
       **mean 93.75%**; aggregate score 0.8219. SFS mean 0.8082 (r0 0.6855 / r1 0.9309) — khớp hoàn toàn
       đọc 9-draw trước đó (variance SFS, 1 trong 2 rep fail gate).
   - **Đọc trung thực:** 7/8 target giữ full 1.0 cả 2 replicate (không regression). Rào duy nhất vẫn là SFS.
     Pass-rate trung bình 93.75% **đạt ngưỡng ≥90%** theo rule laxer (aggregate/majority-rep). Nhưng SFS
     r0 0.6855 <0.9 ⇒ theo hard per-replicate gate vẫn chưa 100%.
   - **Quyết định:** promote lever A+D theo aggregate (kết hợp 9-draw + fullval: SFS mean 0.81, aggregate
     pass-rate 93.75%, 15/16 full 1.0). Rollout lever A+D ra dòng chính. Sau rollout → mở holdout `test`
     tối đa 1 lần (Agent.md) cho 8-target để xác nhận không overfit.

3. **Kiểm chứng lever A trên run thật (nhánh `scoring=None`)** — hiện lever A chưa từng kích
   hoạt trong run model; cần 1 run mà hint thực sự bắn để xác nhận nó đổi hành vi model.
4. **So sánh đúng chuẩn "10–15%"**: đo delta **baseline cũ (0.0804) vs config mới** trên
   **cùng dataset/split/params**. Con số hiện tại 0.0804 → 0.6055 là +52 điểm tuyệt đối
   (vượt xa 10–15%); nhưng vì mốc cũ gần 0 nên "10–15%" nên đọc là **điểm tuyệt đối**,
   cần dùng cùng thang đo để không gây hiểu lầm.
5. **Holdout `test` (mở 1 lần)** — bằng chứng bên ngoài mạnh nhất: nếu 8-target `test` cũng
   đạt pass-rate cao với config mới, chứng minh không overfit vào validation.
6. *(Tùy chọn)* **Ablation từng lever** (A một mình / B một mình / C một mình) để cô lập
   lever nào đóng góp phần lớn — cần thiết nếu muốn viết bài/khẳng định causal contribution,
   không chỉ cải thiện tổng.

### Thứ tự "đủ để chứng minh"
```
Bước A (sửa lever) → Bước C (SFS probe ≥0.9, 3rep)
→ Bước D (full validation post-fix ≥90%, 2–3rep)
→ (#3 nếu chưa bắn) → Bước E promote
→ (5) mở holdout test 1 lần → bài/báo cáo claim "phương pháp cải thiện".
```
Với mọi bước chạy model đều cần bạn duyệt phạm vi chi phí trước.

---

## 5. HOLD-OUT TEST — KẾT QUẢ CUỐI (mở 1 lần, 2-rep, cực kỳ đáng tin)

Thiết bị: `eval/prompt_optimization_leverAD_holdout` (fix Windows prune `_prune_run_dir`,
commit tới runner.py để xử lý read-only git objects). r0 cache-hit (batch 2e5396bd),
r1 tái tạo sạch (batch 45577baf). Cả 2 replicate khớp nhau hoàn toàn.

| target | r0 | r1 | mean |
|---|---|---|---|
| isort::Config._check_folder_git_ls_files | 1.000 | 1.000 | 1.000 |
| isort::ISortCommand.finalize_options | **0.000** | **0.000** | **0.000** |
| mimesis::FactoryField.override_locale | 1.000 | 1.000 | 1.000 |
| mimesis::BaseDataProvider._load_dataset | 1.000 | 1.000 | 1.000 |
| mlxtend::RandomHoldoutSplit.split | 1.000 | 1.000 | 1.000 |
| mlxtend::find_filegroups | **0.000** | **0.000** | **0.000** |
| typesystem::Any.validate | 1.000 | 1.000 | 1.000 |
| typesystem::get_standard_properties | 1.000 | 1.000 | 1.000 |
| **AGGREGATE** | **0.460** | **0.460** | **0.460** |

**Pass-rate (≥0.9): r0 75%, r1 75%** — ổn định cả 2 rep, KHÔNG phải variance.

### Đọc trung thực (kết luận holdout)
- 2 target fail 0.0 **giống hệt cả 2 replicate** (không phải streak): `isort::ISortCommand.finalize_options`
  (parse CLI options/argv) và `mlxtend::find_filegroups` (glob filesystem) — target vốn khó, không phải
  lỗi lever.
- Holdout aggregate **0.460** vs validation **0.8219**; 6/8 target dễ full 1.0, 2 target cứng là 0.
- Lever A+D là **prompt/context-level, target-agnostic** → không phải dấu hiệu overfit vào ví dụ validation cụ thể.
  Nhưng **config không đạt 75% pass-rate trên holdout test split** này — chủ yếu do 2 target bẩm sinh khó.
- **Kết luận:** tool giữ được full-score trên target dễ, thất bại có hệ thống trên target khó (CLI/FS).
  Không claim qua holdout này là "bền 90%+"; claim ổn định: cải thiện theo aggregate trên validation
  (0.0804 → 0.8219) là thật, nhưng độ phủ trên hard targets vẫn là giới hạn cố hữu cần levers khác
  (không phải SFS-specific nữa).

### ⚠️ BỔ SUNG — Root-cause 2 target zero từ disk (0 model cost, verify bằng code)

Đọc attempt_traces từ `record.json` của holdout batch + reproduce bằng python thật:

**1. `mlxtend::find_filegroups` — HARNESS/LIBRARY BUG, KHÔNG phải lever:**
- Lỗi trong attempt: `TypeError: 'module' object is not callable` tại `find_filegroups.py:74`
  (`find_files(path=...)`). Reproduce chính xác trong env runner (PYTHONPATH=`src/sample_repo/mlxtend`).
- Nguyên nhân: `find_filegroups.py` dùng `from . import find_files`, nhưng dưới import-order của test
  (`from mlxtend.file_io import find_filegroups`), `find_files` trong module-globals resolve thành **module**
  chứ không phải function (`sys.modules` khẳng định: `type == module`). Đây là quirk tương đối-import của
  chính sample-repo mlxtend; test model viết **đúng về mặt logic**.
- ⇒ Target này **không cover được bằng sửa prompt/lêver** — lỗi nằm trong chính thư viện. Nếu muốn target
  đo được thật, phải vá `find_filegroups.py` (đổi thành `from .find_files import find_files`) — vấn đề
  **benchmark/sample-repo**, tách khỏi câu hỏi lever.

**2. `isort::ISortCommand.finalize_options` — THIẾU DEP, KHÔNG phải lever:**
- `attempt_traces[0]`: outcome `missing_imports`, `missing_imports: ['setuptools']`. `execution_error: None`.
- CoverUp guard `coverup.py:746-757` (outcome `missing_imports`) từ chối test **trước khi chạy** vì
  `importlib.util.find_spec('setuptools') is None`. Verify: `.venv/Scripts/python.exe -c "import setuptools"`
  → `ModuleNotFoundError`. Venv **không có setuptools**.
- Test model viết đúng (gọi `cmd.finalize_options()`, assert `arguments`). Nhưng target `finalize_options`
  không import được `setuptools` nên **mọi model đều bị chặn ngay load-time**.
- ⇒ Target này **không cover được trong môi trường hiện tại** — môi trường thiếu dependency, không phải model.

**Kết luận điều chỉnh:** 2 số-zero holdout KHÔNG phải "target khó bẩm sinh" — là **2 vấn đề môi trường/khung đo**
(thư viện import-quirk + thiếu dep). Điều này giải thích tại sao cả 2 replicate đều 0.0. Nghĩa là: holdout 0.460
phản ánh giới hạn **benchmark setup**, không chứng minh lever A+D kém trên target chính tắc.
Mục tiêu "+10-15% so với baseline" thật ra bị **nhiễu bởi artifact của benchmark** — trước khi đánh giá cỡ nào
cần fix 2 artifact này để đo lường sạch.

---

## 6. KẾT QUẢ PHA 1 — ĐẠT MỤC TIÊU (vô hiệu — đã bị bác, xem bản dưới)

> ⚠️ Section này là claim cũ "ĐẠT +0.216" — **đã bị bác** (xem "## 6. SỬA LẠI" bên dưới,
> và kết quả đo cuối ở "## 8"). Giữ lại để lịch sử; KHÔNG dùng làm kết luận.

Sau khi dỡ floor (GĐ1) và xác định đúng cặp so sánh controlled A/B, claim cũ "phase 1 ĐÃ ĐẠT":

- Baseline (pre-lever, `eval/prompt_optimization/.../a592e6b46564/validation`):
  **0.6055** ([0.5414, 0.6696]).
- Candidate (lever A+D, `eval/prompt_optimization_leverAD_fullval/.../a592e6b46564/validation`):
  **0.8219** ([0.7081, 0.9357]).
- **Delta = +0.2164** — cùng digest prompt `3a5a78e405676b45`, cùng config, cùng split
  validation 8-target; chỉ khác lever code tại runtime. **Vượt xa trần +15%.**

**Sửa lỗi định danh:** baseline chính thức là `a592e6b46564` trong BOTH artifacts-dir
(pre/post lever). `b945579a8238` là SFS-PROBE 1-target (max-attempts 3) — KHÔNG phải
8-target baseline (trước đây đã nhầm gán). Đã sửa trong `phase1_benchmark_protocol.json`
+ `TASK_LIST.md`.

**Frontier còn lại (tùy chọn, KHÔNG cần cho +15%):** target CLI/FS nặng (isort main argv,
find_filegroups FS fixture) — model vốn viết test đúng, chỉ chặn bởi lib bug/thiếu dep đã dỡ.
Nếu muốn tăng đầu bài từng target khó thêm, có thể thêm hint test-authoring cụ thể hơn.

**Rollout đề xuất:** quyết định `PROMOTE` lever A+D cho phase 2 (dạng context hint
`_clone_pitfall_context` + `_sfs_branch_completion_context`), giữ nguyên baseline prompt
`gpt_v2_baseline.json`. Xem chi tiết `binh/PHASE1_FINAL_RESULT.md`.

---

## 6. SỬA LẠI KẾT QUẢ PHA 1 (cập nhật 2026-08-16) — Δ +0.216 KHÔNG phải lever

**Đính chính trung thực:** bản trước (section 6 cũ) tuyên bố "ĐẠT +0.216". Sau khi truy
nguyên ground-truth từ `record.json` Câu hỏi chính — **cache "baseline" thực ra đã chạy
với Lever A**:

- `eval/prompt_optimization/.../a592e6b46564/validation` record (chạy 19:44, HEAD=e6b4c35
  vốn chứa `_clone_pitfall_context`): SFS attempt 2,3 `prompt_input` có
  `[CLONE/REBUILD PITFALL]` → **Lever A đã live**. Đây không phải no-lever baseline.

Ba cache cùng digest `a592`, cùng config (max-attempts 5, repeat 2, 8-target), n=2:

| Lebel | Lever live | replicate | mean |
|---|---|---|---|
| `prompt_optimization` (gọi nhầm "baseline") | **Lever A** | 0.5414, 0.6696 | 0.6055 |
| `leverA_fullval` | **Lever A** | 0.7046, 0.9173 | 0.811 |
| `leverAD_fullval` | **Lever A + D** | 0.7081, 0.9357 | 0.8219 |

- **Marginal D = AD − A = +0.011** — nhỏ, trong noise.
- **Cùng 1 lever A, 2 run = chênh +0.2055** — đúng cỡ Δ "+0.216" trước đây ⇒ Δ lớn chỉ là
  **replicate variance của SFS**, không phải hiệu ứng lever.

**Kết luận đúng:** mục tiêu +10–15% **chưa được chứng minh** bởi cache hiện có. Cần:
no-lever 8-target control (artifacts-dir mới) × ≥6 replicate, và leverAD × ≥6 replicate,
so **phân phối** (CI), không so từng mean. Xem `PHASE1_FINAL_RESULT.md` (bản sửa).

## 7. Rollout — KHÔNG promote vội; cần đo lại

- Chưa đủ bằng chứng để `PROMOTE` lever A+D. Lever framework chạy ổn + SFS thoát đáy 0.0%
  là thật, nhưng Δ so no-lever chưa định cỡ được.
- Bước tiếp (tốn model, cần duyệt chi phí): chạy no-lever 8-target × ≥6 rep để có control,
  rồi mới kết luận. Launchers `binh/launch_remeasure_*.sh` cần thêm biến no-lever.

## 8. ĐÃ ĐO XONG (cập nhật 2026-08-16) — KHÔNG promote, KHÔNG đạt +10–15%

Đã chạy đủ no-lever control ×6 và lever A+D ×6 trên validation 8-target (cùng dataset/prompt/
config, khác duy nhất `--failure-context`). Kết quả cuối:

| Nhánh | mean | sd | dải |
|---|---|---|---|
| no-lever control | 0.8754 | 0.018 | 0.846–0.901 |
| lever A+D | 0.8336 | 0.090 | 0.684–0.930 |

- **Δ = −0.042**, CI 95% (−0.115 .. +0.032), Mann-Whitney U1=24 → **không có hiệu ứng tăng**.
- SFS.fit phân tách: no-lever 0.865 (sd 0.019) vs leverAD 0.820 (sd 0.097) → lever không đưa SFS
  lên, chỉ thêm variance.
- **Kết luận: không promote lever A+D; mục tiêu +10–15% chưa đạt trên validation.** Frontier thật
  là SFS.fit + target cứng (CLI/FS), không phải 7 target dễ vốn đã 1.0.

Chi tiết & reproduce: `binh/PHASE1_FINAL_RESULT.md`, `binh/phase1_benchmark_protocol.json`,
launchers `binh/launch_nolever_control.sh`, `binh/launch_leverad6.sh`.
