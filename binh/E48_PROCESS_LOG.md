# E48 — Nhật ký tiến trình (process log)

> Ghi lại **thứ tự bước đã thực hiện**, quyết định, và phát hiện môi trường trong phiên
> hoàn thiện SFS. Số liệu kết quả nằm ở `PHASE1_E48_SFS_LEVER_RESULT.md`.
> Trạng thái: **dừng theo yêu cầu người dùng** — không chạy thêm chi phí.

---

## 1. Điểm xuất phát (bối cảnh trước phiên này)

- Nhiệm vụ tổng: hoàn thiện 4 bước (bỏ qua quyết định commit/tách `.claude/settings.json`).
- Bước 1 đã xong (verify code bằng pytest/ruff/py_compile).
- Bước 2 đã xong (chẩn đoán SFS 0% là do bẫy `clone()` + cấu trúc test sai).
- Bước 3: thiết kế 3 lever (A clone-hint, B test-structure nudge, C max-attempts).

## 2. Các bước đã làm trong phiên này

### Bước 3 — Thực thi code (lever A, B)

1. **Xử lý plan-mode nhầm**: vào nhầm plan mode; ghi plan tối thiểu và thoát ngay để tiếp tục
   thực thi (hợp với chỉ dẫn rõ ràng "Code và sửa prompt").
2. **Kiểm tra test mới `tests/test_clone_pitfall.py`**: sửa lỗi collection ban đầu
   (`ModuleNotFoundError: coverup`) bằng cách defer import sau `sys.path.insert("src")`
   theo đúng idiom repo (`tests/test_coverage_optimization.py`).
3. **Sửa lỗi `CodeSegment.__init__()`**: nhận đối số **positional** (`filename, name,
   begin, end, qualname, lines_of_interest, ...`), không phải keyword `path`. Sửa `_segment_for`.
4. **Sửa test negative thứ 3**: giữ lỗi nhưng thay source sang thật sự không có tín hiệu
   clone (trước đó thay `clone_estimator=0` nhưng chuỗi vẫn còn `_estimator_type`/`clone_estimator`
   → vẫn khớp signal). Đổi sang class SFS không có clone machine. → **3/3 test pass**.
5. **Chuẩn hóa naming**: ruff báo `N806`/`N803` (biến `CodeSegment` phải lowercase) →
   đổi thành `code_segment` khớp idiom repo. → **ruff sạch**.
6. **Rà soát cấu hình prompter**: `--prompt` mặc định là `gpt-v2`; `claude.py` không trong
   default path. **Phát hiện quan trọng**: runner luôn chèn `--prompt-template-file`
   (JSON override) → sửa fallback template trong code là **KHÔNG đủ**; lever (B) phải nằm
   trong các JSON template thực thi.
7. **Cập nhật lever (B) vào 3 JSON template** (đã verify placeholder còn nguyên, JSON hợp lệ,
   hai file canonical giống hệt nhau):
   - `cloud/inputs/gpt_v2_baseline.json`
   - `eval/prompt_optimization/prompts/gpt_v2_baseline.json`
   - `binh/e67_prompts/d8123dc403839c22.json`
8. **Đồng bộ `claude.py`** cùng nudge cho 3 prompter thống nhất.
9. **Verify toàn diện**: `pytest tests -q` = **151 passed**, `ruff` sạch, `py_compile` OK,
   `test_clone_pitfall.py` = 3 passed. **Không regression.**

### Bước 4 (tiền-trì) — Thiết kế & chạy E48 trên SFS

10. **Soạn bộ run-kit** `binh/e48_sfs_paired_replicate.md` (chưa chạy) — 2 arm (BASE vs CAND).
11. **Giải thích cơ chế A/B** theo yêu cầu: số hàm (1 target SFS), có train/valid/test
    (dataset strat là train16/valid8/test8; E48 dùng split **validation**, không đụng test),
    tiêu chí chấm (`0.3·stmt + 0.7·branch`).
12. **Người dùng duyệt chi phí → chạy Smoke A**:
    - BASE r0 (max-attempts 3): **0.6813**
    - CAND r0 (max-attempts 5): **0.6313** (kèm `salvaged_failures: 1`)
13. **Người dùng yêu cầu chạy luôn B** → chạy 3 replicate/arm:
    - BASE: [0.6813, 0.7941, 0.6439] → **mean 0.7064**
    - CAND: [0.6313, 0.8908, 0.9231] → **mean 0.8150**
14. **So sánh với baseline lịch sử 0.0%**: kết quả dương rõ rệt (cả hai arm > 0 ở 3/3 replicate).

### Dừng & ghi hồ sơ

15. **Phát hiện bất thường môi trường**: transport (proxy `ltnproxy.com`, model
    `deepseek/deepseek-v4-flash-0731`) thể hiện ký tự lạ bám vào tool output + một phần
    lời model bị biến dạng + vài lệnh Bash bị lặp. Dữ liệu `record.json` không bị ảnh hưởng.
16. **Người dùng quyết định DỪNG**, không chạy thêm chi phí full-validation, yêu cầu ghi
    file md. → Tạo `PHASE1_E48_SFS_LEVER_RESULT.md` và file này.

---

## 3. Quyết định chưa giải quyết / còn mở

- **Commit code?** Các thay đổi (lever A/B + test + JSON) đang chưa commit. Người dùng chưa
  yêu cầu commit. Để lộ, an toàn.
- **Lever A chưa được exercise trong run**: cần một replicate mà model gặp lỗi estimator
  để xác nhận hint hoạt động.
- **Full-validation 8-target**: chưa chạy (dừng theo yêu cầu). Cần khi muốn quyết định
  rollout theo decision-rule.
- **Holdout `test`**: chưa mở (đúng — mở tối đa 1 lần, chỉ khi full validation thắng).
- **Kênh model ổn định**: nên xác thực trước khi chạy thêm chi phí.

---

## 4. Số liệu tóm tắt (đã verify)

| Arm | max-attempts | mean score | 3/3 > 0? |
|---|---|---|---|
| BASE (lever B) | 3 | 0.7064 | ✅ |
| CAND (lever B+C) | 5 | 0.8150 | ✅ |
| Baseline lịch sử | — | 0.0 | — |

Xem đầy đủ bảng replicate ở `PHASE1_E48_SFS_LEVER_RESULT.md`.
