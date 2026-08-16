# E49 — Full-validation 8-target replicate run kit (CAND)

> **Trạng thái: CHƯA CHẠY.** Đây là bộ soạn (run kit) để người dùng duyệt **phạm vi chi phí**
> trước khi chạy. Không tự chạy khi chưa có xác nhận chi phí (chính sách đứng đầu phiên).
> Mục đích: áp dụng config CAND (đã đo tốt trên SFS) ra **toàn bộ 8 target split validation**,
> so sánh aggregate với baseline lịch sử E42/E46, rồi áp decision-rule (pass-rate ≥ 90%).

---

## 1. Mục tiêu & lý do

E48 xác nhận trên **1 target** (SFS) rằng bộ lever A+B+C làm SFS thoát 0.0% một cách bền vững
(BASE mean **0.7064**, CAND mean **0.8150**; baseline lịch sử 0.0%).

Nhưng theo decision-rule hệ thống: **không promote chỉ vì 1 target**. Need đo **toàn bộ 8 target
validation** với config CAND, tính aggregate, và chỉ promote khi **overall pass-rate ≥ 90%**.

Baseline lịch sử (E42/E44 failure-triggered-context, digest `d8123dc403839c22`):
trên 8-target validation, aggregate **0.0804** = statement 0.1686, branch 0.0426,
**7 target full-score (1.0) + 1 target zero (SFS = 0.0)**. Đó là mảnh duy nhất kéo aggregate
xuống; bẫy clone + cấu trúc test sai khiến SFS không đo được chút nào.

## 2. Cấu hình (khớp E48 CAND, mở rộng ra 8 target)

| Tham số | Giá trị | Ghi chú |
|---|---|---|
| repo root | `D:\VinAI\P-002` | cwd |
| sample repos | `src/sample_repo` | `--sample-repos-dir` |
| artifacts | `eval/prompt_optimization` | `--artifacts-dir` |
| model | `vertex_ai/gemini-3.5-flash-lite` | từ `COVERUP_MODEL` trong `.env` |
| prompt | `cloud/inputs/gpt_v2_baseline.json` | digest mới `3a5a78e405676b45` (đã có lever B nudge) |
| dataset | `binh/e70_failure_stratified_32.jsonl` | **split `validation`** = 8 target |
| target-context | on, max 6000 | khớp |
| failure-context | on, max 4000 | khớp |
| salvage-failing-tests | on, max-prunes 8 | khớp |
| repeat-tests | 2 | khớp |
| **max-attempts** | **5** | lever C |
| **evaluation-replicates** | **1** (khuyến nghị đầu) | xem §5 về lựa chọn replicate |

> Lưu ý digest: `3a5a78e405676b45` (baseline đã sửa) **khác** digest lịch sử `d8123dc403839c22`.
> So sánh phải dựa trên **cùng dataset + split + tham số**, không dựa digest.

## 3. Dataset — 8 target split validation

| # | project::symbol | path (src/sample_repo/…) |
|---|---|---|
| 1 | isort::find_imports_in_file | isort/api.py |
| 2 | isort::get_output | isort/hooks.py |
| 3 | mimesis::SchemaBuilder.__repr__ | mimesis/builder/core.py |
| 4 | mimesis::BaseDataProvider.override_locale | mimesis/providers/base.py |
| 5 | mlxtend::BootstrapOutOfBag.split | mlxtend/evaluate/bootstrap_outofbag.py |
| 6 | mlxtend::SequentialFeatureSelector.fit | mlxtend/feature_selection/sequential_feature_selector.py |
| 7 | typesystem::ValidationResult.__iter__ | typesystem/base.py |
| 8 | typesystem::EmailFormat.serialize | typesystem/formats.py |

7 target này trong baseline E42 đã đạt full-score (1.0); target duy nhất zero là SFS (#6).
TH1 quan trọng: lever B/C **không được hạ** điểm các target vốn **đã full-score** — nếu 7 đó
giữ nguyên hoặc cao hơn aggregate ~0.87×(0.3·stmt+0.7·branch) cũng là pass mạnh; rủi ro chính là
lever làm **rối một target đang full** (hồi quy). Phải quan sát per-target, không chỉ aggregate.

## 4. Lệnh đề xuất

Readiness check (không tốn chi phí — chỉ đọc + build):
```bash
cd /d/VinAI/P-002
./.venv/Scripts/python.exe -c "import json,hashlib; p='cloud/inputs/gpt_v2_baseline.json'; d=json.load(open(p,encoding='utf-8'));
assert '{filename}' in d['prompt']['initial'] and '{source_excerpt}' in d['prompt']['initial']; print('placeholders OK, digest', hashlib.sha256(open(p,'rb').read()).hexdigest()[:12])"
```

Run thật (khi đã duyệt chi phí):
```bash
cd /d/VinAI/P-002
./.venv/Scripts/python.exe -m src.optimization.cli \
  --sample-repos-dir src/sample_repo \
  --artifacts-dir eval/prompt_optimization \
  --max-attempts 5 --repeat-tests 2 --max-concurrency 1 \
  --target-context --failure-context --failure-context-max-chars 4000 \
  --salvage-failing-tests --salvage-max-prunes 8 \
  evaluate \
  --dataset binh/e70_failure_stratified_32.jsonl \
  --prompt cloud/inputs/gpt_v2_baseline.json \
  --split validation --evaluation-replicates 1
```

## 5. Phạm vi chi phí & lựa chọn replicate

- 8 target, mỗi target tối đa **1 initial + (5−1)=4 repair** = **tối đa 5 model calls/target**.
- Với `--evaluation-replicates 1`: trần **8×5 = 40** model calls; thực tế thường less
  (nhiều target thành công sớm không dùng hết attempt budget).
- Khuyến nghị **chạy replicate 1 trước** (batch r0). Chỉ mở rộng lên r1/r2 khi cần giảm
  phương sai ~10.9 điểm quan sát thấy ở SFS giữa các replicate.
- Mọi số là **thật, không ước lượng** — không hứa % trước khi chạy.

**So sánh dự kiến với baseline** (con số để hình dung, KHÔNG phải kết quả):
- Nếu **8/8 ≥ 0.9** → pass-rate 100%, rõ ràng promote.
- Nếu SFS giữ ~0.815 (E48 CAND) và 7 target còn lại giữ full-score → aggregate ≈
  (7×1.0 + 0.815)/8 ≈ **0.977**, pass-rate ~87.5% (SFS <0.9). Lúc đó bàn tiếp lever A
  (clone-hint) đưa SFS qua ngưỡng, hoặc chấp nhận threshold theo target.

## 6. Decision rule (đã có trong hệ thống)

- **Promotion chỉ khi overall pass-rate ≥ 90%** trên toàn validation (≥ 7.2/8, tức ít nhất
  mọi target ≥ 0.9 trong thực tế rời rạc).
- Pass-rate tính trên **từng target** ≥ 0.9, KHÔNG phải aggregate mean (tránh 1 target đỉnh
  bù cho 1 target zero).
- Nếu đạt → rollout + mở holdout `test` **tối đa 1 lần** (Agent.md), cần xác nhận chi phí riêng.
- Nếu chưa đạt → xác định target dưới ngưỡng, dùng lever A nếu là lỗi estimator, tinh chỉnh
  prompt/tham số, chạy lại vòng lặp. Không promote.

## 7. Rủi ro

- **Hồi quy target đang full-score**: 7 target vốn 1.0 phải giữ ≥0.9 — theo dõi per-target,
  không chỉ aggregate.
- **Kênh model**: phiên E48 có dấu hiệu transport/proxy bóp méo output (kéo lệnh Bash lặp,
  ký tự lạ). Dữ liệu record.json không bị ảnh hưởng, nhưng nên xác thực kênh ổn định trước
  khi đốt chi phí full-validation.
- **Budge chi phí**: 40 model calls trần/replicate-1. Khi kênh xác thực và user duyệt.
- **Lever A chưa exercise**: nếu run này gặp lỗi `_estimator_type` ở repair, `_clone_pitfall_context`
  sẽ bắn — đây là cơ hội xác nhận nó hoạt động trên run thật.

## 8. Sau khi có kết quả

1. Ghi số liệu thật vào `PHASE1_FULL_VALIDATION_RESULT.md` (aggregate + per-target bảng).
2. Áp decision-rule §6 → quyết định promote/không.
3. Nếu promote → bàn rollout + holdout `test` (mở 1 lần) với user, chờ xác nhận chi phí.
4. Nếu cần thêm replicate để giảm phương sai → chạy r1/r2, trung bình aggregate.
