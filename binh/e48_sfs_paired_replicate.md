# E48 — SFS paired-replicate run kit

> **Trạng thái cập nhật: đã thực thi Smoke A + B. Dừng trước full-validation theo yêu cầu**
> người dùng (lo ngại ổn định kênh model) — không chạy thêm chi phí hiện tại.
> **Kết quả đo:** xem `PHASE1_E48_SFS_LEVER_RESULT.md` (BASE mean 0.7064, CAND mean 0.8150).
> **Tiến trình:** xem `E48_PROCESS_LOG.md`.
> Phần dưới giữ nguyên như mô tả thiết kế và lệnh đã dùng; một vài lưu ý vận hành được ghi chú.

---

## 1. Mục tiêu

Đo **score tuyệt đối** của target `SequentialFeatureSelector.fit` (mlxtend) khi dùng bộ ba lever A+B+C (clone-pitfall hint + test-structure nudge + tăng max-attempts), so với baseline `d8123dc403839c22` (chỉ có nudge từ JSON đã cập nhật).

Lý do chạy riêng probe 1-target này: mọi baseline lịch sử (E42/E46/E47) đều = **0.0%** trên SFS. Chúng ta cần một con số đo thật (không phải ước lượng) trước khi quyết định rollout ra validation 8-target.

## 2. Các tham số cố định (khớp lịch sử E42/E47)

| Tham số | Giá trị | Ghi chú |
|---|---|---|
| repo root | `D:\VinAI\P-002` | cwd |
| sample repos | `src/sample_repo` | `--sample-repos-dir` |
| artifacts | `eval/prompt_optimization` | `--artifacts-dir` (mặc định) |
| model | `vertex_ai/gemini-3.5-flash-lite` | từ `COVERUP_MODEL` trong `.env` |
| failure-context | `on`, root `src/sample_repo/mlxtend`, max 4000 | khớp E42/E47 |
| target-context | `on`, max 6000 | khớp |
| salvage | `on`, max-prunes 8 | khớp |
| repeat-tests | 2 | khớp E42/E47 (`--repeat-tests 2`) |
| max-concurrency | 1 | khớp E47 (`--max-concurrency 1`) |

**Lever C (thay đổi duy nhất so với baseline):** `--max-attempts 5` (baseline E42/E47 dùng 3).

## 3. Dataset

`binh/e70_e42_e44_validation_sfs_probe.jsonl` — một target duy nhất (SFS), split `validation`. Xác nhận split hợp lệ: **validation** (không đụng holdout `test`).

## 4. Prompt archetypes (2 arms)

- **Arm BASE**: `cloud/inputs/gpt_v2_baseline.json` (đã cập nhật nudge lever B).
- **Arm CAND A+B**: cùng prompt đó, nhưng chạy với `--max-attempts 5` (lever C). Hai lever **A (clone-pitfall hint)** hoạt động qua `target_context.py` runtime, **không cần ở trong file JSON** — nó được `build_failure_context()` chèn vào prompt repair khi lỗi `_estimator_type` xuất hiện. Vậy cùng một file prompt vận hành cả A, B, C; chỉ khác tham số run (max-attempts).

> **Lưu ý quan trọng về digest:** `cloud/inputs/gpt_v2_baseline.json` đã đổi so với bản cũ → digest SHA-256 mới (`candidates/` sẽ tạo candidate_id mới, **không** phải `d8123…`). Baseline lịch sử vẫn còn nguyên trong `phase0_runs`/`phase1_runs` archives — không ghi đè.

## 5. Đề xuất chạy (paired, ≥3 replicate mỗi arm)

Replicate = một lần `evaluate` độc lập trên probe dataset. Vì max-concurrency 1 và 1 target, mỗi replicate = 1 coverup subprocess = **1 initial + tối đa (max-attempts − 1) = 4 repair calls** thật tối đa.

Để chi phí tối thiểu trước khi commit, đề xuất **2 bước**:

### Bước A — Smoke 1-replicate (chi phí nhỏ nhất)
Kiểm tra pipeline chạy end-to-end, lever đều active, không lỗi config.

```bash
# Root:
cd /d/VinAI/P-002
# Arm BASE – 1 replicate, max-attempts 3 (mô phỏng đúng E47 baseline)
.venv/Scripts/python.exe -m src.optimization.cli \
  --sample-repos-dir src/sample_repo \
  --artifacts-dir eval/prompt_optimization \
  --max-attempts 3 --repeat-tests 2 --max-concurrency 1 \
  --target-context --failure-context --failure-context-max-chars 4000 \
  --salvage-failing-tests --salvage-max-prunes 8 \
  evaluate \
  --dataset binh/e70_e42_e44_validation_sfs_probe.jsonl \
  --prompt cloud/inputs/gpt_v2_baseline.json \
  --split validation --evaluation-replicates 1
```

```bash
# Arm CAND – 1 replicate, max-attempts 5 (lever C)
.venv/Scripts/python.exe -m src.optimization.cli \
  --sample-repos-dir src/sample_repo \
  --artifacts-dir eval/prompt_optimization \
  --max-attempts 5 --repeat-tests 2 --max-concurrency 1 \
  --target-context --failure-context --failure-context-max-chars 4000 \
  --salvage-failing-tests --salvage-max-prunes 8 \
  evaluate \
  --dataset binh/e70_e42_e44_validation_sfs_probe.jsonl \
  --prompt cloud/inputs/gpt_v2_baseline.json \
  --split validation --evaluation-replicates 1
```

> Lưu ý: `--failure-context-root` trong CLI evaluate được `_resolve_project_layouts` tự suy từ `sample_repos_dir/project/…`; flag `--failure-context-root` là cấp coverup, CLI cao hơn lo rồi. Nếu cần thiết có thể chỉnh thêm.

### Bước B — Replicates đầy đủ (chỉ khi smoke ổn)
Nâng `--evaluation-replicates 3` (hoặc 5) cho mỗi arm; aggregate tự trung bình các replicate.

## 6. Decision rule (đã có trong hệ thống)

- Không promote chỉ vì một target; **promotion dựa vào overall pass-rate ≥ 90% trên toàn validation** sau khi có tín hiệu SFS.
- Với E48 này: chỉ ghi nhận **score tuyệt đối SFS** (mục tiêu > 0 bền vững, lý tưởng cao), và so paired delta BASE vs CAND.
- **Không mở holdout `test`** — giữ nguyên locked (mở tối đa 1 lần, chỉ khi toàn validation thắng).

## 7. Rủi ro / chi phí

- Mỗi replicate = 1 lần `initial` + tối đa (max-attempts−1) repair. Với max-attempts 5 → tối đa 5 model calls/replicate/target.
- Smoke (Bước A): 1+1 = 2 replicate → ~2–10 model calls trần.
- Bước B (3 replicate/arm): 6 replicate → ~6–30 model calls trần.
- Mọi kết quả là **thật, không ước lượng** — không thể báo % trước khi chạy.
