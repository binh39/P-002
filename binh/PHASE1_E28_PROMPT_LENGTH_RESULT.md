# P1 — E28 prompt length objective

Ngày: 2026-08-15

## Mục tiêu

Kiểm tra proposal GEPA dài có thực sự đáng giá hơn baseline và bổ sung safety control để prompt
phình không thắng chỉ nhờ một validation sample thuận lợi.

## Protocol

- Replay candidate pool E22 seed 7/17/37 trên evaluation cache; không gọi model mới.
- Validation rerank: 3 replicate, 4 locked validation targets.
- Baseline bắt buộc nằm trong pool.
- So sánh bốn cấu hình trong một fixed replay grid:
  - Không phạt độ dài.
  - Penalty 0,01 selection score cho mỗi 1.000 ký tự vượt baseline.
  - Penalty 0,02/1.000 ký tự.
  - Hard cap tổng 4.000 ký tự.
- Raw coverage không thay đổi; penalty chỉ tác động `selection_score`.

## Prompt size

| Prompt | Total chars | So với baseline |
|---|---:|---:|
| Baseline `d8123dc403839c22` | 943 | 1,00x |
| Proposal `d52af1a676ec8d78` | 4.231 | 4,49x |

Proposal dài hơn 3.288 ký tự.

## Validation replay

| Configuration | Proposal raw mean | Proposal selection | Baseline selection | Winner |
|---|---:|---:|---:|---|
| No penalty | 97,51% | 97,51% | 91,21% | Proposal |
| Penalty 0,01/1k | 97,51% | 94,22% | 91,21% | Proposal |
| Penalty 0,02/1k | 97,51% | 90,93% | 91,21% | Baseline |
| Hard cap 4.000 | filtered | filtered | 91,21% | Baseline |

Break-even trên đúng validation pool này khoảng `0,0192/1k`; đây là diagnostic post-hoc, không
phải hyperparameter production hợp lệ.

Holdout của benchmark đã được quan sát từ E26 trước khi E28 được thiết kế, nên ablation này chỉ là
exploratory safety analysis, không phải confirmatory evidence.

## Holdout interpretation

Paired 3-replicate holdout đã đo trước đó:

- Baseline: 71,97%.
- Proposal: 61,98% (`-9,99 điểm`).

Vì vậy no-penalty và penalty 0,01 vẫn chọn candidate regression. Penalty 0,02 và cap 4.000 giữ
baseline, tránh regression nhưng không tạo gain coverage.

## Kết luận

Độ dài 4,49x không generalize tốt hơn dù validation raw mean cao hơn. E28 là safety/control hữu
ích, không phải phương pháp tạo prompt tốt hơn baseline. Default vẫn là penalty 0 và không cap để
tránh tune theo holdout đã lộ; trước khi bật production phải preregister ngưỡng và xác nhận trên
dataset/holdout mới.

Bước tiếp theo nên là E24 reflection-temperature ablation với budget nhỏ nhằm tạo proposal ngắn và
đa dạng hơn, giữ E28 chỉ làm report/safety gate. Chưa có cơ sở tăng GEPA budget.

## Implementation và verification

- Reranker lưu `prompt_chars`, `length_penalty`, `selection_score` và filtered candidate reason.
- Hard cap chạy trước generation evaluation để tránh chi phí candidate chắc chắn bị loại.
- `--report-output` cho phép replay nhiều ablation mà không ghi đè artifact.
- Full repository suite: 114 passed.
- Ruff, py_compile và `git diff --check`: pass.
