# PHASE 1 — BÀN GIAO KẾT QUẢ (đo xong, trung thực)

> Trạng thái: ✅ **ĐÃ ĐO XONG với no-lever control x6 vs lever A+D x6** (2026-08-16).
> File này là bản cuối, thay cho bản "PHẢI SỬA LẠI" trước đó.

---

## 1. Tóm tắt điều hành — kết luận cuối

| Câu hỏi | Kết luận |
|---|---|
| Lever A+D có tăng coverage đáng kể so với no-lever không? | **KHÔNG.** Δ = −0.042, CI 95% (−0.115 .. +0.032), chạm cả 2 phía 0. |
| Mục tiêu +10–15% có đạt không? | **KHÔNG đạt trên validation 8-target bằng lever A+D.** |
| Vì sao? | 7/8 target vốn đã 1.0; target duy nhất chưa 1.0 là SFS.fit, và lever không đẩy nó lên — chỉ thêm variance. |
| Có gì chắc chắn đúng? | Lever framework chạy ổn; benchmark floor đã sạch; SFS thoát đáy 0.0%; 7/8 target 1.0 bền vững. |

**Kết luận hành động: KHÔNG promote lever A+D.**

---

## 2. Đo lường thật (2026-08-16) — validation 8-target, n=6 mỗi nhánh

Config nhất quán giữa 2 nhánh: cùng dataset `binh/e70_failure_stratified_32.jsonl`
(validation, 8 target), cùng prompt `cloud/inputs/gpt_v2_baseline.json`, max-attempts 5,
repeat-tests 2, max-concurrency 1, salvage on, `--evaluation-replicates 6`. Khác biệt **duy nhất**
là lever gate `--failure-context` (tắt ở control, bật ở leverAD → kích hoạt clone-pitfall + SFS
branch + private-hook hint).

| Nhánh | artifacts-dir | mean | sd | dải replicate (aggregate) |
|---|---|---|---|---|
| **No-lever control** | `eval/prompt_optimization_nolever` | **0.8754** | 0.018 | 0.846, 0.8735, 0.8735, 0.8753, 0.8827, 0.9011 |
| **Lever A+D** | `eval/prompt_optimization_leverAD6` | **0.8336** | 0.090 | 0.684, 0.7908, 0.835, 0.8442, 0.9173, 0.9304 |

- **Δ = leverAD − no-lever = −0.0417**
- **CI 95% ≈ (−0.1153 .. +0.0319)** — trùm 0, không đủ bằng chứng lever > control.
- **Mann-Whitney U1 = 24** (U1 = n1·n2 = 36 là "lever luôn cao"; 24 = không phân tách; và mean
  lever còn thấp hơn) → **không có hiệu ứng tăng.**
- CLI-printed aggregate: no-lever `0.87536`, leverAD `0.83363` (khớp).

**Metric:** `aggregate_coverage_score` (src/optimization/metrics.py) — micro-average
`0.3*stmt_cov + 0.7*br_cov` trên `covered_*/num_*`, không phải `statement_gain`.

---

## 3. Vì sao không tăng — phân rã theo target

Phân rã `SequentialFeatureSelector.fit` (target duy nhất < 1.0; 143 stmt / 90 branch):

| Nhánh | SFS.fit mean | SFS.fit sd | replicate SFS.fit |
|---|---|---|---|
| No-lever | **0.8652** | 0.019 | 0.834, 0.863, 0.863, 0.865, 0.873, 0.893 |
| Lever A+D | **0.8205** | 0.097 | 0.660, 0.774, 0.822, 0.831, 0.911, 0.925 |

- **No-lever SFS rất ổn định** (sd 0.019): 7 target khác = 1.0 + SFS ~0.865 ⇒ no-lever aggregate 0.875.
- **Lever A+D SFS rất loạn** (sd 0.097, dải 0.66–0.92): lever **không đưa SFS lên** — điểm cao nhất
  (0.925) cũng chỉ ngang no-lever max (0.893), còn điểm thấp tụt sâu (0.66).

⇒ Toàn bộ "thế giới đang di chuyển" giữa các replicate là **SFS variance**; lever không chinh phục
nó được, thậm chí còn làm rộng biến động.

---

## 4. Đối chiếu với các con số cũ (tự sửa)

| Con số trước đây | Thật ra là | Đúng |
|---|---|---|
| "+0.216 đạt nhờ lever A+D" | Δ giữa 2 cache đều đã có Lever A live (`prompt_optimization` 0.6055 → `leverA_fullval` 0.811) | **replicate variance SFS** (+0.2055 với cùng 1 lever) |
| "baseline = no-lever 0.6055" | cache `prompt_optimization` chạy với **Lever A** live (record.json SFS prompt_input có `[CLONE/REBUILD PITFALL]`) | không phải no-lever |
| "marginal D ≈ +0.011" | AD − A trên cache cũ n=2 | nhỏ, trong noise |

Giờ đã có no-lever control đo thẳng: **no-lever aggregate 0.875 thậm chí cao hơn cả leverAD 0.834.**
Mọi tuyên bố "lever đạt +10–15%" đều không đứng vững.

---

## 5. Điều vẫn trụ vững và có giá trị thật

1. **Lever framework chạy ổn** — không crash, không hồi quy 7 target dễ.
2. **Benchmark floor đã được dọn sạch (GĐ1)**: fix `find_filegroups.py` (lib bug `from . import
   find_files`), add `setuptools` (thiếu dep isort `finalize_options`), fix Windows prune crash
   (`_on_rm_error`). Đây là công việc độc lập, giá trị thật.
3. **7/8 target đạt 1.0 bền vững ở cả 2 nhánh** — tool giỏi trên target tự nhiên dễ.
4. **Hiểu rõ frontier thật**: mục tiêu khó nằm ở SFS.fit (chưa 1.0, hay nhảy) và các target cứng
   khác (CLI/FS, holdout) — không phải các target dễ đã bão hòa.

---

## 6. Khuyến nghị nếu muốn tiếp tục tăng +10–15%

Lever A+D trên frontier hiện tại **không phải đòn bẩy**. Hướng thật sự có tiềm năng:

1. **Giảm variance / ép SFS.fit**: tìm cách làm SFS.fit ổn định hơn (cô lập paired no-lever vs lever
   trên cùng replicate, hoặc chấp nhận aggregate theo phân phối thay vì kỳ vọng mỗi replicate ≥0.9).
   Nhưng cần lưu ý: đo này cho thấy lever không giúp → cân nhắc lever khác thay vì thêm hint.
2. **Nhắm frontier cứng đang thấp**: `SequentialFeatureSelector.fit` + target CLI/FS, nơi có chỗ
   tăng thật (khác 1.0).
3. **Không promote lever A+D ra phase 2** với bằng chứng hiện tại.

---

## 7. File bàn giao & how to reproduce

- **Bản bàn giao:** `binh/PHASE1_FINAL_RESULT.md` (file này).
- **Protocol + kết luận:** `binh/phase1_benchmark_protocol.json` (`decision_outcome` = REVISED/measured).
- **Task list:** `binh/TASK_LIST.md` (T3.3/T4.3 để trống — chưa đạt).
- **Launchers:** `binh/launch_nolever_control.sh`, `binh/launch_leverad6.sh`.
- **Log:** `binh/log_nolever_control.txt` (aggregate 0.87536), `binh/log_leverad6.txt` (aggregate 0.83363).
- **Raw:** `eval/prompt_optimization_nolever/runs/.../record.json` (6 bản), `eval/prompt_optimization_leverAD6/runs/.../record.json` (6 bản).

**Nhắc lại constraint:** `test`/holdout chỉ mở tối đa 1 lần (đã dùng) — mọi đánh giá tương lai
dùng `validation`. Không commit file nào cho tới khi bạn yêu cầu.
