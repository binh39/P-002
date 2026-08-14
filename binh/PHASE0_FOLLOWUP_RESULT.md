# Kết quả follow-up Pha 0.5

- Model duy nhất: `vertex_ai/gemini-3.5-flash-lite`.
- Phạm vi: 5 target có variance cao hoặc từng không có attempt.
- Không chạy GEPA và không chạy lại toàn bộ calibration set.

| Target | Score |
| --- | ---: |
| `isort/main.py::sort_imports` | 100.00% |
| `isort/wrap.py::line` | 92.52% |
| `isort/deprecated/finders.py::KnownPatternFinder.__init__` | 100.00% |
| `mlxtend/frequent_patterns/apriori.py::apriori` | 89.28% |
| `typesystem/fields.py::Boolean.validate` | 100.00% |

Aggregate hợp nhất:

- Score: **93.36%**.
- Statement: **96.27%** (155/161).
- Branch: **92.11%** (70/76).

Hai method từng không có attempt nay đều được CoverUp nhận diện và sinh test đạt 100%. `Boolean.validate` cần hai vòng repair trước khi lưu test thành công. Kết quả này chỉ xác nhận measurement/generation pipeline đã ổn định hơn; chưa phải bằng chứng một prompt optimized thắng baseline.
