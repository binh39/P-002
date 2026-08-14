# P1 — E30 structured failure taxonomy

## Trạng thái

Phần code và live control của E30 đã được triển khai. Integration schema 3 thành công nhưng candidate không thắng validation và không được promote. Xem `binh/PHASE1_E30_LIVE_CONTROL_RESULT.md`. Không đụng tới `prompt_optimization_v3`.

## Thay đổi

- Thêm `src/optimization/failures.py` để chuẩn hóa mỗi CoverUp attempt thành failure record nhỏ và ổn định.
- Reflection trace tăng từ schema 2 lên schema 3.
- `initial_attempts`, repair transition và terminal outcome nhận taxonomy trước khi được gửi cho reflection model.
- Raw traceback vẫn được giữ dạng clip để kiểm chứng, nhưng proposer được yêu cầu chẩn đoán từ taxonomy trước.
- Không thay đổi CoverUp generation, pytest, coverage, metric, split hoặc promotion gate.

Các trường có thể xuất hiện:

- `failure_stage`: generation, collection, execution, assertion, repair hoặc coverage.
- `failure_type`: ví dụ `import_error`, `type_error`, `assertion_error`, `timeout`, `no_coverage_gain`, `partial_coverage`, `max_attempts_exhausted`.
- `error_type` và `error_message` đã rút gọn.
- `actionable_frame`: path, line và function ưu tiên generated test/repository code, bỏ qua frame nội bộ pytest/site-packages.
- `actual`, `expected`, `comparison` khi pytest cung cấp assertion expression có thể phân tích an toàn.
- `root_failure_stage` và `root_failure_type` khi terminal outcome là exhausted repair.

Execution episode vẫn giữ failing test, repair prompt, repaired test, remaining statement/branch và outcome. Candidate/parent/baseline delta cùng source context tiếp tục nằm ở reflection record bên ngoài taxonomy.

## Quy tắc phân loại chính

| Tín hiệu | Stage | Type |
| --- | --- | --- |
| Model request/response không dùng được | generation | outcome tương ứng |
| Import, syntax hoặc collection error | collection | import/syntax/collection error |
| AssertionError | assertion | assertion_error |
| TypeError, AttributeError, NameError… | execution | loại exception dạng snake_case |
| Test pass nhưng không tạo gain | coverage | no_coverage_gain |
| Có gain nhưng còn executable units | coverage | partial_coverage |
| Hết repair attempts | repair | max_attempts_exhausted + root cause |

## Kiểm tra không dùng model

Taxonomy đã được áp dụng lên trace E01 có sẵn của `mlxtend::valid_input_check`. Terminal record nhận đúng:

- stage `repair`;
- type `max_attempts_exhausted`;
- root stage `execution`;
- root type `type_error`;
- actionable frame trỏ vào dòng generated test gây lỗi.

## Tiêu chí đã dùng cho live control

Đã chạy cùng dataset/model/seed/budget với E21 và chỉ thay reflection evidence schema. Các chỉ số được so sánh:

- tỷ lệ target-replicate `max_attempts_exhausted`;
- số `test_error` episode trước một `coverage_gain_saved`;
- validation mean/variance qua paired replicate;
- coverage gain và regression theo target;
- input token của reflection để kiểm tra taxonomy có thực sự giảm phụ thuộc vào raw log hay không.

E30 không đạt tiêu chí thắng: best candidate có 2/4 target exhausted, 8 test-error event và validation 38,20%, thấp hơn baseline 26,54 điểm. Không chạy candidate holdout.
