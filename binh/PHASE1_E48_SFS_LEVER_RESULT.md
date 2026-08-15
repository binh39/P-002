# E48 — SFS paired-replicate result (baseline vs lever A+B+C)

> **Trạng thái: KẾT THÚC — đã chạy Smoke A + B, dừng trước full-validation.**
> Người dùng yêu cầu dừng chạy thêm chi phí và ghi lại kết quả + tiến trình.
> Toàn bộ số liệu dưới đây là **thật, trích xuất từ `record.json`** (engine `eval/prompt_optimization/runs/3a5a78e405676b45-*/`), không phải ước lượng.

---

## 1. Mục tiêu & ngữ cảnh

Bước 2 chẩn đoán (đã verify offline): `SequentialFeatureSelector.fit` (mlxtend) giữ nguyên
**0.0% coverage** trong mọi baseline lịch sử (E42/E46/E47) vì hai lý do độc lập:

1. **Bẫy `clone()`**: model cứ monkey-patch `_estimator_type` trực tiếp lên instance được
   truyền vào. `sklearn.base.clone()` bên trong `SFS.__init__` (khi `clone_estimator=True`)
   tái dựng estimator từ `get_params()` → mất attr gán tay → cùng lỗi lặp lại từng attempt.
2. **Cấu trúc test sai**: model viết một function khổng lồ ~19 scenario nối tiếp — một lỗi
   sớm chặn việc đo coverage của mọi scenario sau; ngay cả salvage AST nâng cấp cũng không
   cứu được vì mọi scenario dùng chung một setup hỏng.

**Ba lever được thiết kế để đối phó (Bước 3):**
- **(A)** Clone/rebuild pitfall hint — `src/coverup/target_context.py`:
  `_clone_pitfall_context()` + section `[CLONE/REBUILD PITFALL]`, kích hoạt khi lỗi chứa
  `_estimator_type` và source segment chứa tín hiệu `clone(`/`clone_estimator`. Khuyên:
  không gắn tay lên instance; dùng kwarg constructor (vd `scoring=...`), estimator có
  `_estimator_type` ở class scope, hoặc `clone_estimator=False`.
- **(B)** Test-structure nudge — "prefer several small, independent test_* functions…" thêm
  vào: `src/coverup/prompt/gpt_v2.py` (fallback), `src/coverup/prompt/claude.py`,
  `src/optimization/prompts.py` (`BASELINE_INITIAL`), và **3 JSON template thực thi**
  (`cloud/inputs/gpt_v2_baseline.json`, `eval/prompt_optimization/prompts/gpt_v2_baseline.json`,
  `binh/e67_prompts/d8123dc403839c22.json`).
- **(C)** Tăng `--max-attempts` 3 → 5 cho target đa-lớp lỗi.

**Điểm mấu chốt về pipeline:** runner luôn chèn `--prompt-template-file` (JSON override),
bỏ qua fallback template trong code. Vì vậy lever (B) **chỉ có hiệu lực trong run thật khi
JSON template cũng được cập nhật** — đây là lý do phải sửa cả 3 JSON chứ không chỉ code.

---

## 2. Cấu hình chạy (đồng nhất hai arm)

| Tham số | Giá trị |
|---|---|
| repo root | `D:\VinAI\P-002` |
| sample-repos-dir | `src/sample_repo` |
| artifacts-dir | `eval/prompt_optimization` |
| model | `vertex_ai/gemini-3.5-flash-lite` (từ `COVERUP_MODEL`) |
| prompt | `cloud/inputs/gpt_v2_baseline.json` (đã có lever B nudge) |
| dataset | `binh/e70_e42_e44_validation_sfs_probe.jsonl` (1 target, split validation) |
| target-context | on, max 6000 |
| failure-context | on, root auto `src/sample_repo/mlxtend`, max 4000 |
| salvage-failing-tests | on, max-prunes 8 |
| repeat-tests | 2 |
| max-concurrency | 1 |
| **BASE** | `--max-attempts 3` |
| **CAND** | `--max-attempts 5` |

Prompt digest mới **`3a5a78e405676b45`** (SHA-256 mới của baseline đã sửa — khác
`d8123dc403839c22` cũ, không ghi đè archive lịch sử).

---

## 3. Kết quả đo (3 replicate / arm)

### Arm BASE (`max-attempts 3`, lever B)

| Replicate | Score | Statements | Branches | valid |
|---|---|---|---|---|
| r0 | 0.6813 | 106/143 (74.1%) | 59/90 (65.6%) | True |
| r1 | 0.7941 | 119/143 (83.2%) | 70/90 (77.8%) | True |
| r2 | 0.6439 | 103/143 (72.0%) | 55/90 (61.1%) | True |
| **Mean** | **0.7064** | — | — | — |

### Arm CAND (`max-attempts 5`, lever B + C)

| Replicate | Score | Statements | Branches | valid |
|---|---|---|---|---|
| r0 | 0.6313 | 97/143 (67.8%) | 55/90 (61.1%) | True |
| r1 | 0.8908 | 128/143 (89.5%) | 80/90 (88.9%) | True |
| r2 | 0.9231 | 136/143 (95.1%) | 82/90 (91.1%) | True |
| **Mean** | **0.8150** | — | — | — |

> Lưu ý r0 của cả hai arm là replicate "smoke" đầu tiên (BASE r0 = run `baeb484a`,
> CAND r0 = run `c101ff14`). Các `-r1`/`-r2` trong path là batch cache của replicate 1/2.

---

## 4. Phân tích

- **Thoát khỏi đáy 0.0%**: baseline lịch sử của SFS = 0.0% (E42/E46/E47). Cả BASE lẫn
  CAND đều > 0 ở **3/3 replicate** — tín hiệu dương rõ rệt, không phải một lần may mắn.
- **CAND (B+C) thắng BASE ~10.9 điểm** (0.8150 vs 0.7064).
- **CAND có 2/3 replicate trên 89%** (r1 0.8908, r2 0.9231) — lever C (thêm attempt) giúp
  model cắn qua thêm các lớp lỗi và chạm ~95% statement, ~91% branch.
- **Lever A chưa được exercise trong các replicate này**: bộ test initial thành công sớm,
  không dính lỗi `_estimator_type`, nên `_clone_pitfall_context` không bị gọi. Nó là
  "lưới an toàn" cho những replicate mà model gặp lỗi estimator-protocol ở repair.

### Câu hỏi "tăng bao nhiêu % so với baseline"
- So với baseline lịch sử **0.0%**:
  - BASE: **+70.6 điểm tuyệt đối** (0 → 70.6%).
  - CAND: **+81.5 điểm tuyệt đối** (0 → 81.5%).
- Giữa hai arm mới: CAND hơn BASE **+10.9 điểm**.
- Lưu ý: "tăng % so với 0" chỉ có nghĩa ở thang điểm tuyệt đối 0–100; con số so sánh có
  ý nghĩa là **điểm tuyệt đối** chứ không phải tỉ lệ phần trăm tương đối.

---

## 5. Code đã commit-tự-do / trạng thái

Toàn bộ thay đổi code là **chưa commit** (người dùng chưa yêu cầu commit):

| Mục | File | Trạng thái |
|---|---|---|
| Lever A | `src/coverup/target_context.py` | mới, verified |
| Lever B | `src/coverup/prompt/gpt_v2.py`, `src/coverup/prompt/claude.py`, `src/optimization/prompts.py` | mới, verified |
| Lever B (JSON) | `cloud/inputs/gpt_v2_baseline.json`, `eval/.../gpt_v2_baseline.json`, `binh/e67_prompts/d8123dc403839c22.json` | mới |
| Test mới | `tests/test_clone_pitfall.py` (3 tests) | mới, verified |
| (pre-existing, không phải của session này) | `src/coverup/testrunner.py`, `tests/test_coverage_optimization.py` | salvage upgrade đã có sẵn |

Verification: `pytest tests -q` = **151 passed**; `ruff check` sạch; `py_compile` OK.

---

## 6. Rủi ro còn lại & bước tiếp theo

### Đã dừng trước full-validation
Người dùng yêu cầu **dừng chạy thêm chi phí** → ghi file thay vì chạy full validation 8-target.
Nếu sau này tiếp tục hướng (a), cần:
1. Chạy **full validation 8-target** với CAND config (`--max-attempts 5`), so với baseline.
2. Apply decision-rule hệ thống: **promotion chỉ khi overall pass-rate ≥ 90%** trên toàn
   validation (không chỉ riêng SFS).
3. **Chỉ khi toàn validation thắng** thì mới cân nhắc mở holdout `test` — **tối đa 1 lần**,
   theo Agent.md.

### Cảnh báo môi trường (quan trọng)
Trong phiên chạy này, transport (proxy `ltnproxy.com`, model `deepseek/deepseek-v4-flash-0731`
trong `.claude/settings.json`) thể hiện **dấu hiệu bóp méo/ký tự lạ bám vào tool output** và
một phần lời model bị biến dạng. Dữ liệu `record.json` không bị ảnh hưởng (sạch, nhất quán).
Đây là lý do người dùng quyết định dừng trước khi đốt thêm chi phí. Nếu tiếp tục sau này:
**nên xác thực/ổn định kênh model trước** (ví dụ endpoint trực tiếp hoặc proxy ổn định),
đảm bảo lệnh và kết quả đáng tin cậy.

---

## 7. Kết luận

- E48 SFS là **thí điểm thành công có thể đo được**: SFS thoát khỏi 0.0% một cách bền vững,
  đạt **70.6% (BASE)** và **81.5% (CAND)** trung bình 3 replicate.
- **Lever B (nudge) đã làm SFS chạy được ngay ở max-attempts 3** (trước kia 0%).
- **Lever C (thêm attempt) tăng thêm ~10.9 điểm** và đẩy 2/3 replicate lên trên 89%.
- **Lever A (clone-hint) chưa được exercise** — cần một run mà model gặp lỗi estimator để xác nhận.
- Code **sẵn sàng**, nhưng **chưa đủ để rollout**: cần full-validation theo decision-rule
  trước khi mở rộng và trước khi chạm holdout `test`.
