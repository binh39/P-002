# P1 — GEPA budget 30 sau khi bật E41

Ngày: 2026-08-14

## Protocol

- Model generation và reflection: `vertex_ai/gemini-3.5-flash-lite`.
- Dataset: 8 train / 4 validation / 4 locked test targets, trải trên isort, mimesis,
  mlxtend và typesystem.
- E41 exact contract context bật; E43 repository tests/fixtures tắt.
- GEPA seed 7, reflection minibatch 3, requested max metric calls 30.
- GEPA dùng 32 metric calls vì một full evaluation là khối nguyên tử.
- Final gate được chạy lại với 3 replicate cho **cả baseline và proposal**; GEPA search không chạy lại.

## Search result

GEPA sinh bốn reflection decisions và chọn proposal digest `d52af1a676ec8d78`. Proposal thay đổi
cả `initial` và `error`:

- Initial prompt: 616 -> 2.178 ký tự.
- Error prompt: 327 -> 2.053 ký tự.
- Nội dung chủ yếu nhấn mạnh valid configuration/type, platform paths và sửa test có chọn lọc.

Single-generation coverage trong search:

| Split | Baseline | Proposal | Delta |
|---|---:|---:|---:|
| Train | 40,39% | 61,40% | +21,00 |
| Validation | 77,90% | 95,36% | +17,46 |
| Locked test r0 | 46,85% | 22,26% | -24,59 |

Safety gate r0 đã reject proposal và giữ baseline. Tuy nhiên vì generation variance lớn, `finalize`
được sửa để lặp đồng đều cả hai phía rồi final gate được chạy lại từ cache.

## Paired 3-replicate holdout

| Prompt | Replicate scores | Mean | Sample SD |
|---|---|---:|---:|
| Baseline | 46,85 / 70,73 / 98,33 | 71,97% | 25,77 điểm |
| GEPA proposal | 22,26 / 98,33 / 65,35 | 61,98% | 38,15 điểm |

Absolute gain của proposal: `-9,99 điểm`; `promoted=false`.

Theo target:

- `isort::PathFinder.find`: 66,67% -> 33,33% (`-33,33`). Proposal tạo assertion sai giữa
  `FIRSTPARTY` và `THIRDPARTY` ở hai replicate.
- `mimesis::BaseField.perform`: giữ 100%.
- `mlxtend::StackingClassifier.fit`: 62,81% -> 59,69% (`-3,11`).
- `typesystem::Object.__init__`: giữ 100%.

`gepa_optimized.json` vẫn đúng bằng baseline digest `d8123dc403839c22`; proposal bị reject vẫn
được lưu riêng trong artifact để chẩn đoán.

## Kết luận

E41 làm generation baseline mạnh hơn, nhưng GEPA budget 30 vẫn overfit train/validation và prompt
phình khoảng 3,5–6,3 lần. Kết quả này không ủng hộ tăng budget lên 120/300 ngay.

Bước hợp lý tiếp theo là E26:

1. Giữ top-K proposal thay vì chỉ best single validation sample.
2. Rerank top-K bằng ít nhất 3 validation replicate.
3. Chỉ mở locked holdout một lần cho candidate thắng rerank.
4. Thêm prompt-bloat penalty hoặc giới hạn strategy playbook trước khi thử budget lớn hơn.

## Verification

- Finalize paired-replicate invariant đã có unit test.
- Full repository suite: 108 passed.
- Ruff, py_compile và `git diff --check`: pass.
