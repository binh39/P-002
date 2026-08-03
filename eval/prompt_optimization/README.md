# Tối ưu prompt sinh unit test cho CoverUp

Pipeline này dùng CoverUp làm engine sinh và sửa unit test, `coverage.py` làm bộ
đánh giá deterministic, và DSPy GEPA dùng Gemini để tìm prompt tốt hơn. Mục tiêu
hiện tại là tối đa hóa statement coverage và branch coverage trên từng hàm Python.

## Tổng quan kiến trúc

```mermaid
flowchart TD
    A[Dataset các symbol] --> B[Prompt candidate]
    B --> C[CoverUp + Gemini]
    A --> C
    C --> D[Generated pytest tests]
    D --> E[pytest]
    E --> F[coverage.py --branch]
    F --> G[coverage_after.json]
    H[Zero-coverage start] --> I[Symbol coverage analyzer]
    G --> I
    I --> J[Statement/branch metric]
    J --> K[Structured feedback]
    K --> L[GEPA + Gemini reflection LM]
    L --> B
    J --> M[Prompt leaderboard]
```

Các trách nhiệm được tách như sau:

- CoverUp đọc source, xác định phần coverage còn thiếu, gọi Gemini và sửa test qua
  nhiều attempt.
- `coverage.py` chạy test suite trước và sau khi sinh test, sau đó xuất JSON có
  coverage theo file và function.
- Symbol analyzer chỉ lấy coverage của hàm đang đánh giá, không dùng phần trăm
  coverage toàn repository làm reward.
- Metric và hard gate được tính bằng code, không dùng LLM judge.
- GEPA nhận score cùng feedback về line/branch còn thiếu để cải thiện prompt.

## Thành phần mã nguồn

```text
src/optimization/
├── cli.py          # CLI init, evaluate và optimize
├── coveragepy.py   # Chạy coverage.py và đọc coverage từng symbol
├── dataset.py      # Đọc dataset JSONL
├── gepa.py         # Direct PromptBundle adapter và GEPA core optimizer
├── metrics.py      # Coverage gain, score và feedback
├── models.py       # SymbolTarget, ExperimentConfig và RunRecord
├── prompts.py      # PromptBundle và baseline prompt
└── runner.py       # Một experiment CoverUp cô lập hoàn chỉnh
```

CoverUp được mở rộng bằng option:

```text
--prompt-template-file <prompt.json>
```

Option này chỉ áp dụng cho prompt family `gpt-v2`. File JSON có thể override ba
template:

```json
{
  "initial": "...",
  "error": "...",
  "missing_coverage": "..."
}
```

Cả ba template đều bắt buộc đối với `evaluate` và `optimize`. Pipeline tối ưu toàn
bộ vòng hội thoại: sinh test lần đầu, sửa lỗi pytest và nhắm lại coverage còn thiếu.
Candidate thiếu một template hoặc placeholder bắt buộc sẽ nhận score 0 trước khi
CoverUp được gọi.

## Chuẩn bị môi trường

Từ thư mục gốc repository:

```powershell
$env:PYTHONPATH = "src"
```

Các dependency chính:

```text
coverage>=7.15.2
dspy==3.2.1
gepa==0.0.27
litellm[google]>=1.94.0
```

Gemini được cấu hình giống CoverUp qua `.env`:

```dotenv
COVERUP_MODEL=vertex_ai/gemini-3.6-flash
OPTIMIZE_MODEL=vertex_ai/gemini-3.6-flash
VERTEXAI_PROJECT=<google-cloud-project>
VERTEXAI_LOCATION=global
```

`COVERUP_MODEL` sinh và sửa unit test. `OPTIMIZE_MODEL` đọc score/feedback và
reflection để đề xuất ba prompt template mới. Hai biến có thể trỏ tới hai model
khác nhau. Optimization CLI chỉ đọc hai model từ `.env` và không nhận model qua
command line, nhờ đó mỗi run có một nguồn cấu hình duy nhất.

Vertex AI dùng Application Default Credentials. Cần đăng nhập ADC trước khi chạy
evaluate hoặc optimize có gọi LLM.

Source isort hiện nằm tại:

```text
src/sample_repo/isort/isort
```

Test suite nằm tại:

```text
src/sample_repo/isort/tests
```

## Khởi tạo prompt và dataset

```powershell
python -m src.optimization.cli init
```

Lệnh tạo:

```text
eval/prompt_optimization/
├── datasets/isort_symbols.jsonl
└── prompts/gpt_v2_baseline.json
```

Nếu file đã tồn tại, CLI sẽ dừng để tránh ghi đè. Muốn tạo lại:

```powershell
python -m src.optimization.cli init --force
```

## Dataset symbol

Mỗi dòng trong `datasets/isort_symbols.jsonl` là một JSON object:

```json
{"project":"isort","source_file":"isort/core.py","symbol":"process","split":"train"}
```

Các trường:

| Trường | Ý nghĩa |
|---|---|
| `project` | Tên project dùng trong run ID và artifact |
| `source_file` | Đường dẫn file như xuất hiện hoặc là suffix duy nhất trong coverage JSON |
| `symbol` | Tên function hoặc qualified method, ví dụ `process`, `Config.__init__` |
| `split` | `train`, `validation` hoặc `test` |

Khuyến nghị không đưa cùng một symbol vào nhiều split. `test` là locked split,
chỉ nên chạy sau khi đã chọn prompt bằng validation.

Dataset mới do `init` tạo có 25 train, 10 validation và 10 locked-test symbols. Train
lớn hơn giúp reflection thấy nhiều failure mode; validation nhỏ hơn dành budget cho
exploration; test chỉ được dùng một lần ở promotion gate. Dataset cũ không có split
`test` vẫn chạy được nhưng final comparison phải fallback về validation.

Generator của dataset isort loại `isort/_vendored/`. Vendored code thường bị coverage
config bỏ qua và import path có thể đổi theo Python version; đưa nó vào validation làm
metric mất denominator và có thể tạo score 0 giả.

## Prompt baseline

Prompt `gpt_v2_baseline.json` chứa ba template với placeholder bắt buộc:

```text
initial:            {filename}, {missing_coverage}, {source_excerpt}
error:              {error}
missing_coverage:   {missing_coverage}
```

Các placeholder của initial prompt là:

```text
{filename}
{missing_coverage}
{source_excerpt}
```

Trước khi chạy CoverUp, pipeline thay chúng bằng:

- đường dẫn source file;
- line và branch chưa được thực thi;
- code excerpt của function/class đang xử lý.

Candidate thiếu placeholder hoặc có placeholder không hợp lệ nhận score 0 và không
được chạy CoverUp.

## Luồng của một experiment

Một lần gọi `CoverUpExperimentRunner.evaluate_batch()` thực hiện các bước sau.

### 1. Tạo run cô lập

Pipeline tạo run ID dạng:

```text
isort-train-batch-a1b2c3d4
```

Mỗi candidate có một thư mục test rỗng, độc lập cho từng split:

```text
src/sample_repo/isort/tests_candidate_<candidate-id>_train
src/sample_repo/isort/tests_base_line_<baseline-digest>_validation
src/sample_repo/isort/tests_candidate_<candidate-id>_validation
```

Baseline prompt dùng prefix `tests_base_line_` để phân biệt với các candidate do GEPA
đề xuất. CoverUp sinh toàn bộ test cho các symbol của split trong đúng một lần gọi.
Train và validation không dùng chung test; không sao chép test suite gốc.

### 2. Khởi tạo coverage

Mỗi candidate bắt đầu từ coverage 0. Pipeline không chạy pytest trên folder rỗng và
không tạo `coverage_before.json`; coverage-before được biểu diễn nội bộ với toàn bộ line
và branch của target ở trạng thái chưa được thực thi.

### 3. Chạy CoverUp cho nhiều symbol

Runner gọi:

```powershell
python -m coverup `
  --package-dir src/sample_repo/isort/isort `
  --tests-dir <isolated-tests> `
  --target-symbols process,Trie.search,Config.is_supported_filetype,grid `
  --prompt gpt-v2 `
  --prompt-template-file <run-dir>/prompt.json `
  --model vertex_ai/gemini-3.6-flash `
  --max-attempts 3 `
  --max-concurrency 10 `
  --prefix opt `
  --repeat-tests 2 `
  --no-checkpoint
```

Luồng nội bộ của CoverUp:

1. Đọc coverage hiện có bằng execution engine của CoverUp.
2. Tạo `CodeSegment` chứa excerpt, missing lines và missing branches.
3. Render initial prompt candidate.
4. Gọi Gemini sinh một pytest module hoàn chỉnh.
5. Chạy candidate test tạm.
6. Nếu pytest fail, gửi traceback qua error repair prompt.
7. Nếu test pass nhưng không tăng coverage, gửi missing-coverage repair prompt.
8. Khi candidate có coverage gain, lưu thành `test_opt_<n>.py` trong test suite cô lập.

Nếu provider trả `finish_reason="stop"` nhưng `content=null`, hoặc trả text không có
Python code block, CoverUp ghi log và retry riêng segment đó trong giới hạn
`--max-attempts`. Một response hỏng không được làm hủy các task concurrent còn lại.

### 4. Đo coverage sau generation

Runner chạy lại toàn bộ test suite của split bằng `coverage.py --branch` đúng một lần và xuất:

```text
coverage_after.json
```

Nếu generated suite fail dưới coverage.py, candidate nhận score 0.

### 5. Lấy coverage của đúng function

Parser tìm:

```text
files → <source_file> → functions → <symbol>
```

Các dữ liệu được sử dụng:

```text
executed_lines
missing_lines
executed_branches
missing_branches
summary.covered_lines
summary.num_statements
summary.covered_branches
summary.num_branches
```

Đường dẫn Windows và POSIX được chuẩn hóa trước khi lookup. `source_file` trong
dataset cũng có thể là suffix duy nhất như `isort/parse.py`.

### 6. Tính metric

Reward dùng coverage gain trên những target còn thiếu trước khi sinh test:

```text
statement_gain = newly_covered_missing_lines / initially_missing_lines
branch_gain    = newly_covered_missing_branches / initially_missing_branches

score = 0.4 × statement_gain + 0.6 × branch_gain
```

Nếu hàm không có branch:

```text
score = statement_gain
```

Hard gate đưa target về 0 khi:

- generated test suite fail khi chạy coverage.py;
- coverage.py không xuất được report;
- coverage không tìm thấy target;
- candidate prompt không giữ placeholder bắt buộc.

Exit code khác 0 của tiến trình CoverUp được lưu thành `generator_exit_code`, nhưng
không xóa coverage của những test đã sinh thành công. Nếu suite cuối cùng pass
coverage.py thì score đo được của target vẫn hợp lệ; feedback kèm warning để điều tra
các sibling target chưa hoàn tất.

### 7. Tạo feedback

Feedback trả cho GEPA có dạng:

```text
Score: 0.6250
Statement gain: 8 newly covered; 3 remain.
Branch gain: 4 newly covered; 5 remain.
Remaining lines: [42, 47, 51]
Remaining branches: [(41, 42), (46, 47), ...]
Target each remaining branch with a distinct input and a meaningful assertion.
```

Pytest stdout và CoverUp log vẫn được lưu riêng để phân tích traceback, LLM request,
response và token usage.

## Chạy đánh giá một prompt

Đánh giá baseline trên validation split:

```powershell
$env:PYTHONPATH = "src"

python -m src.optimization.cli `
  --package-dir src/sample_repo/isort/isort `
  --tests-dir src/sample_repo/isort/tests `
  evaluate `
  --dataset eval/prompt_optimization/datasets/isort_symbols.jsonl `
  --prompt eval/prompt_optimization/prompts/gpt_v2_baseline.json `
  --split validation
```

Kết quả console gồm các run ID và micro-average score có tính cả target thất bại.
Statement và branch được cộng theo số executable units; target lookup thất bại dùng
denominator của baseline và nhận coverage 0. Chi tiết từng run nằm trong `runs/`.

Có thể đánh giá train hoặc locked test bằng cách đổi `--split`.

## Chạy GEPA

```powershell
$env:PYTHONPATH = "src"

python -m src.optimization.cli `
  --package-dir src/sample_repo/isort/isort `
  --tests-dir src/sample_repo/isort/tests `
  optimize `
  --dataset eval/prompt_optimization/datasets/isort_symbols.jsonl `
  --prompt eval/prompt_optimization/prompts/gpt_v2_baseline.json
```

Mặc định CLI dùng `--auto medium`. Có thể chọn budget tự động khác:

```powershell
python -m src.optimization.cli `
  --package-dir src/sample_repo/isort/isort `
  --tests-dir src/sample_repo/isort/tests `
  optimize `
  --dataset eval/prompt_optimization/datasets/isort_symbols.jsonl `
  --prompt eval/prompt_optimization/prompts/gpt_v2_baseline.json `
  --auto light
```

Hoặc tắt auto bằng budget thủ công:

```powershell
$env:PYTHONPATH = "src"

python -m src.optimization.cli `
  --package-dir src/sample_repo/isort/isort `
  --tests-dir src/sample_repo/isort/tests `
  optimize `
  --dataset eval/prompt_optimization/datasets/isort_symbols.jsonl `
  --prompt eval/prompt_optimization/prompts/gpt_v2_baseline.json `
  --max-metric-calls 20
```

GEPA tối ưu trực tiếp ba text component `initial`, `error` và `missing_coverage`; không
còn một LLM trung gian viết lại cả bundle trước khi optimization bắt đầu. Baseline chính
là candidate số 0 và luôn nằm trong Pareto population.

Trước khi GEPA bắt đầu search, pipeline chạy baseline preflight trên toàn train và
validation split. Final holdout reference cũng được kiểm tra trước promotion. Mọi target
phải có coverage hợp lệ để cung cấp denominator. Nếu một target bị thiếu hoặc invalid,
pipeline dừng trước khi tiêu search budget và liệt kê chính xác `file::symbol` cần
sửa/thay thế.

Trong mỗi vòng reflection:

1. GEPA chọn một component để sửa theo round-robin; merge có thể ghép các component tốt.
2. Cả bundle được validate và hash để tạo candidate ID ổn định.
3. Lần gọi đầu của mỗi split chạy batch toàn bộ symbol; các lần sau đọc cache.
4. Mỗi example nhận score riêng của symbol, được scale theo số statement/branch để mean
   của GEPA đúng bằng micro-average cuối cùng.
5. Feedback chứa file, symbol, source lines liên quan, coverage còn thiếu và kết quả từng
   replicate; reflection không còn nhìn các số dòng không có ngữ cảnh.
6. Proposal phải giữ placeholder, có giới hạn độ dài và chỉ thay đổi một component để
   giảm prompt inflation và cải thiện credit assignment.

Kết quả metric được cache theo `prompt hash + split` tại
`candidates/evaluations/<candidate-id>/<evaluation-digest>/<split>/batch.json`.
`evaluation-digest` bao gồm model/config, target set và source hashes nên cache cũ không
thể âm thầm được dùng sau khi code hoặc protocol thay đổi. Các replicate bổ sung dùng
`batch_r1.json`, `batch_r2.json`, ... và workspace riêng. Khi GEPA gọi metric cho từng
example, pipeline lấy đúng score symbol từ batch đã lưu thay vì trả cùng aggregate score
cho mọi example.

Failure semantics hiện dùng cache schema 5. Artifact từ schema cũ không được tái sử
dụng; với benchmark quyết định vẫn nên chọn một `--artifacts-dir` mới.

Sau khi compile xong, pipeline lưu:

```text
eval/prompt_optimization/optimized_program.json
eval/prompt_optimization/prompts/gepa_proposed.json
eval/prompt_optimization/prompts/gepa_optimized.json
eval/prompt_optimization/final_validation.json
```

Prompt mới được lưu trước dưới tên `gepa_proposed.json`. Nếu dataset có split `test`,
baseline và proposal được so sánh trên locked test; nếu không thì CLI ghi rõ rằng nó phải
fallback về validation. `gepa_optimized.json` luôn chứa prompt production thắng: proposal
khi cải thiện nghiêm ngặt, ngược lại là baseline. Vì vậy một proposal kém không thể thay
thế baseline.

Nếu đã có test suite baseline hợp lệ, `--baseline-tests-dir <path>` chấm suite đó như một
reference bổ sung trong report. Promotion gate vẫn dùng baseline/proposal được sinh theo
cùng protocol để tránh so sánh một historical lucky sample với một generation mới.

`--auto light|medium|heavy` tương ứng budget 120/300/600 prompt-symbol calls. Dùng
`--max-metric-calls` để override. Có thể thêm `--evaluation-replicates 2` hoặc `3` cho
run quyết định; mỗi replicate làm tăng gần tuyến tính chi phí nhưng giảm variance.

## Artifact của từng run

```text
runs/<candidate-id>/<split>/<run-id>/
├── prompt.json
├── coverup.log
├── coverup.stdout.log
├── coverage_after.json
├── coverage_after.data
├── record.json
```

Mỗi prompt candidate có một `<candidate-id>` riêng (digest của toàn bộ prompt bundle).
Runner tạo các workspace sibling độc lập dạng `tests_candidate_<candidate-id>_<split>`;
riêng baseline prompt dùng `tests_base_line_<baseline-digest>_validation`.
Mỗi workspace nhận một lệnh CoverUp chứa tất cả symbol của split. Candidate không nhận
file test từ test suite gốc, prompt baseline, split khác hoặc candidate khác.

`record.json` là structured summary chính:

```json
{
  "run_id": "isort-train-batch-a1b2c3d4",
  "split": "train",
  "targets": [
    {"project": "isort", "source_file": "isort/core.py", "symbol": "process", "split": "train"},
    {"project": "isort", "source_file": "isort/utils.py", "symbol": "Trie.search", "split": "train"}
  ],
  "exit_code": 0,
  "elapsed_seconds": 12.4,
  "generated_tests": ["work/tests/test_opt_1.py"],
  "coverage_after": "coverage_after.json",
  "results": [
    {"target": {"symbol": "process"}, "score": {"score": 0.7}, "feedback": "..."},
    {"target": {"symbol": "Trie.search"}, "score": {"score": 0.5}, "feedback": "..."}
  ]
}
```

Các thư mục run, GEPA log và candidate được `.gitignore` vì có thể rất lớn.

## Kiểm tra không gọi LLM

Kiểm tra wiring CoverUp, target symbol và prompt template mà không gọi Gemini:

```powershell
$env:PYTHONPATH = "src"

python -m coverup `
  --package-dir src/sample_repo/isort/isort `
  --tests-dir src/sample_repo/isort/tests `
  --target-symbols process `
  --prompt gpt-v2 `
  --prompt-template-file eval/prompt_optimization/prompts/gpt_v2_baseline.json `
  --model vertex_ai/gemini-3.6-flash `
  --dry-run `
  --no-repeat-tests `
  --no-checkpoint
```

## Kiểm thử code

```powershell
python -m pytest tests -q
ruff check src/optimization tests/test_coverage_optimization.py
```

Không nên chạy `pytest` không chỉ định thư mục ở root hiện tại vì pytest sẽ thu thập
cả test suite vendored trong `src/sample_repo/mlxtend`, gây trùng tên module test.

## Lưu ý vận hành

- Một lượt `evaluate` có gọi Gemini và phát sinh chi phí.
- Một lượt GEPA gọi CoverUp và coverage.py nhiều lần; chi phí tăng theo
  `max-metric-calls`, số symbol và số repair attempt.
- Giữ CoverUp generation temperature bằng 0 để giảm variance, nhưng để reflection
  temperature khoảng `0.7` nhằm duy trì exploration giữa các mutation.
- Mặc định giới hạn `--max-concurrency 10`; giảm thêm hoặc đặt `--rate-limit` nếu log có
  lỗi 429. Không dùng mặc định CoverUp 50 cho một batch optimization lớn.
- Không chỉnh test suite gốc trong lúc một experiment đang chạy.
- Không chọn prompt theo train score. Chọn bằng validation rồi báo cáo đúng một lần
  trên locked test split.
- Coverage cao không tự đảm bảo assertion tốt. Pipeline hiện tối ưu đúng hai metric
  được yêu cầu: statement và branch coverage.
- `gemini-3.6-flash` là model mới; CoverUp cho phép họ `vertex_ai/gemini-*` đi qua
  local capability check và để Vertex API xác nhận function calling thực tế.

## Hướng mở rộng

Các bước tiếp theo hợp lý:

1. Mở rộng dataset lên nhiều function/class và cân bằng độ khó giữa các split.
2. Cache baseline coverage theo hash của source và test suite để giảm thời gian.
3. Parse token usage từ `coverup.log` thành trường riêng trong `record.json`.
4. Thêm failure taxonomy: syntax, import, assertion, timeout và no-gain.
5. Sau khi joint optimization ổn định, chạy thêm ablation theo từng prompt để đo
   đóng góp riêng của `initial`, `error` và `missing_coverage`.
6. Thêm MIPROv2 sau khi đã có demonstration bank đủ lớn từ các run thành công.

## Lệnh benchmark chất lượng cao

```powershell
python -m src.optimization.cli `
  --package-dir src/sample_repo/isort/isort `
  --tests-dir src/sample_repo/isort/tests `
  --artifacts-dir eval/prompt_optimization_v3 `
  --max-concurrency 10 `
  --repeat-tests 2 `
  optimize `
  --dataset eval/prompt_optimization/datasets/isort_symbols.jsonl `
  --prompt eval/prompt_optimization/prompts/gpt_v2_baseline.json `
  --auto heavy `
  --evaluation-replicates 2 `
  --reflection-temperature 0.7
```

python -m src.optimization.cli `
  --package-dir src/sample_repo/isort/isort `
  --tests-dir src/sample_repo/isort/tests `
  --artifacts-dir eval/prompt_optimization_batch_v2 `
  optimize `
  --dataset eval/prompt_optimization/datasets/isort_symbols.jsonl `
  --prompt eval/prompt_optimization/prompts/gpt_v2_baseline.json `
  --max-metric-calls 50


## Không được xóa
  python -m src.optimization.cli `
  --package-dir src/sample_repo/isort/isort `
  --tests-dir src/sample_repo/isort/tests `
  --artifacts-dir eval/prompt_optimization_v2 `
  --max-concurrency 10 `
  optimize `
  --dataset eval/prompt_optimization/datasets/isort_symbols.jsonl `
  --prompt eval/prompt_optimization/prompts/gpt_v2_baseline.json `
  --max-metric-calls 50
