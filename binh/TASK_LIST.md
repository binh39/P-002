# TASK LIST — Đạt mục tiêu +10–15% coverage so với baseline

> Quy trình: làm đến đâu tick `[x]` đến đó. **⚠️ SỬA LẠI 2026-08-16:** Δ +0.216 trước đây
> KHÔNG chứng minh được lever — cache "baseline" (`eval/prompt_optimization/.../a592e6b46564`)
> thực ra đã chạy với **Lever A** (record.json SFS prompt_input có `[CLONE/REBUILD PITFALL]`).
> Ba cache cùng digest `a592`, cùng config, n=2:
> - Lever A  (cache 'baseline'): 0.6055
> - Lever A  (`leverA_fullval`): 0.811   ← cùng lever, khác run ⇒ spread SFS +0.2055
> - Lever A+D(`leverAD_fullval`): 0.8219 ← marginal D ≈ +0.011 (trong noise)
>
> ⇒ Mục tiêu +10–15% **chưa kết luận được** với cache hiện có: thiếu no-lever control và
> đủ replicate (SFS variance chủ đạo). Cần no-lever 8-target × ≥6 rep + leverAD × ≥6 rep
> so phân phối (CI), không so từng mean.
> (Lưu ý: `b945579a8238` là SFS-PROBE 1-target — không phải 8-target baseline.)
>
> Metric chính: `delta aggregate (0.3*stmt + 0.7*branch)` trên **cùng split validation 8-target**,
> N≥2 replicate. Baseline cố định `cloud/inputs/gpt_v2_baseline.json` (digest `3a5a78e405676b45`).

---

## Giai đoạn 1 — Dọn benchmark floor (0 model cost)

- [x] **T1.1** Patch `src/sample_repo/mlxtend/mlxtend/file_io/find_filegroups.py`:
  `from . import find_files` → `from .find_files import find_files` (fix lỗi `'module' object is not callable`).
  Verified E2E PASS. *(Src `src/sample_repo` gitignored, edit vẫn trên disk.)*
- [x] **T1.2** Commit fix prune Windows `src/optimization/runner.py` (`_on_rm_error`). → commit `58ca0fd`.
  *(Làm sớm để mọi run model trên Windows không crash giữa chừng.)*
- [x] **T1.3** Thêm `setuptools` vào môi trường eval (pyproject.toml + requirements.txt) & cài vào venv.
  Verify `import setuptools` OK ⇒ target isort `ISortCommand.finalize_options` cover được.
  → cài setuptools==84.0.0; `finalize_options()` chạy OK; suite 158 passed.
- [x] **T1.4** Kiểm tra `find_filegroups` + `finalize_options` cover được thật sau T1.1+T1.3
  (dùng cache replay qua run model, hoặc test thủ công).
  → PK import/call-level: find_filegroups E2E PASS; finalize_options import + chạy OK; suy ra blocker đã dỡ.

## Giai đoạn 2 — Khóa measurement protocol (0 model cost)

- [x] **T2.1** Viết `binh/phase1_benchmark_protocol.json`: baseline `gpt_v2_baseline.json`,
  dataset `e70_failure_stratified_32.jsonl`, metric delta aggregate + pass-rate ≥0.9,
  split validation, N≥2, model `vertex_ai/gemini-3.5-flash-lite`, max-attempts 5, repeat 2.

## Giai đoạn 3 — Re-measure baseline vs candidate (model cost)

> ⚠️ **SỬA LẠI 2026-08-16:** cache "baseline" (`eval/prompt_optimization/.../a592e6b46564`)
> KHÔNG phải no-lever — record.json xác nhận **Lever A đã live** (SFS prompt_input chứa
> `[CLONE/REBUILD PITFALL]`). Cần **no-lever 8-target control** mới để đo Δ đúng.

- [x] **T3.1** (tick = đã chẩn đoán, KHÔNG coi là đủ) Re-run **baseline** 8-target sau khi dỡ floor.
  → Cache `eval/prompt_optimization/.../a592e6b46564` = **Lever A live** (không phải no-lever),
  mean 0.6055. Cần artifacts-dir mới `nolever` + replicate ≥6.
- [x] **T3.2** (tick = đã chẩn đoán, KHÔNG coi là đủ) Re-run **lever A+D** 8-target.
  → Cache `leverAD_fullval` mean 0.8219. Marginal D vs A (so với `leverA_fullval` 0.811) = **+0.011**.
- [x] **T3.3** Tính delta tin cậy (đã đo xong 2026-08-16).
  → Đã chạy no-lever control ×6 + leverAD ×6 (validation 8-target):
  no-lever mean **0.8754** (sd 0.018) vs leverAD mean **0.8336** (sd 0.090).
  **Δ = −0.042**, CI 95% (−0.115 .. +0.032), Mann-Whitney U1=24 → **KHÔNG có hiệu ứng lever,
  không đạt +10–15%.** SFS.fit riêng: no-lever 0.865 (ổn) vs leverAD 0.820 (loạn) →
  lever không đưa SFS lên, chỉ thêm variance. ⇒ **KHÔNG promote lever A+D.**

## Giai đoạn 4 — Mở rộng frontier (đã chẩn đoán; KHÔNG promote, xem GĐ5)

- [x] **T4.1** Diagnostic `find_filegroups` — model viết test ĐÚNG; lỗi do lib bug
  (`from . import find_files`). Đã vá + E2E verify → cover được, không thêm hint.
- [x] **T4.2** Diagnostic isort CLI-class target (`finalize_options`) — do thiếu setuptools
  (missing_imports), không phải model; setuptools đã cài.
- [x] **T4.3** Structure-nudge test-authoring đã thêm vào prompt (gpt_v2.py + optimization/prompts.py).
  → Đo xong: lever không raise coverage (xem T3.3). Nudge không đủ để +10–15%; frontier thật
  là SFS.fit (giảm variance) + target cứng CLI/FS — không phải 7 target dễ vốn đã 1.0.

## Giai đoạn 5 — Báo cáo

- [x] **T5.1** Cập nhật `binh/NEXT_STEPS_PLAN.md` + viết `binh/PHASE1_FINAL_RESULT.md`:
  baseline vs candidate aggregate, pass-rate, delta, kết luận trung thực về SFS variance,
  về benchmark artifacts đã sửa, về frontier còn lại.

---

### Ghi chú
- Không commit file nào nữa cho tới khi tất cả GĐ1-3 xong (trừ T1.2 đã commit sẵn — để user quyết giữ/bỏ).
- Mọi run model đều dùng artifacts-dir MỚI để tránh cache replay.
- `find_filegroups.py`/`finalize_options` ở TEST split — floor của TEST, không ảnh hưởng baseline/candidate
  validation (nơi đo +10–15%). GĐ1 đúng về mặt "làm sạch benchmark tổng thể" nhưng delta chính đo trên validation.
