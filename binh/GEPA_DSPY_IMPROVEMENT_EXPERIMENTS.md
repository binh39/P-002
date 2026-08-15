# Kế hoạch thực nghiệm cải thiện PromptOpt so với baseline

## 1. Mục tiêu và nguyên tắc đánh giá

Mục tiêu dài hạn là tìm cách tăng coverage ổn định so với baseline hiện tại, thay vì chỉ đạt một lần chạy tốt do ngẫu nhiên. Mốc `69% -> 71%` là tăng **2 điểm phần trăm**. Mục tiêu `+10 đến +15 điểm phần trăm` tương ứng khoảng `79% đến 84%` nếu baseline vẫn là 69%.

Không coi mục tiêu 10–15 điểm là cam kết của GEPA. Trước tiên phải chứng minh rằng các target còn đủ khả năng cải thiện. Nếu toàn bộ test từng được sinh ra chỉ có thể đạt 73%, tăng budget hoặc đổi prompt không thể đưa kết quả lên 80%.

Các nguyên tắc không được thay đổi giữa hai vế so sánh:

- Dùng cùng project, target, split, model sinh test, dependency và runner image.
- Giữ nguyên công thức metric chính: statement/branch coverage hiện tại.
- Baseline luôn là candidate đầu tiên và là fallback.
- Chỉ dùng train để reflection, validation để chọn candidate.
- Không dùng test holdout để sửa prompt hoặc chọn hyperparameter.
- Chỉ chạy test holdout sau khi đã chốt candidate.
- So sánh theo **điểm phần trăm tuyệt đối**, đồng thời lưu số tương đối để tham khảo.
- Mỗi experiment phải dùng artifacts directory mới hoặc digest cấu hình mới để tránh cache cũ.
- Không sửa nhiều nhóm biến trong một ablation nếu chưa có run đối chứng.

## 2. Trạng thái hiện tại cần ghi làm mốc

Pipeline hiện tại có các đặc điểm cần giữ trong manifest của run đối chứng:

- GEPA là search engine; DSPy đang chủ yếu cung cấp `OPTIMIZE_MODEL` cho reflection/proposal.
- Candidate chỉ gồm hai prompt component: `initial` và `error`.
- Backend mặc định `max_metric_calls=30`.
- Optimization mặc định `evaluation_replicates=1`.
- GEPA seed đang cố định là `7`.
- Reflection minibatch tối đa 8 target.
- Candidate selector chọn current-best khoảng 70%, Pareto khoảng 30%.
- Frontier là `hybrid`, merge được bật.
- Metric tổng hợp ưu tiên branch: 30% statement và 70% branch.
- Generation của CoverUp giữ temperature 0; reflection mặc định temperature 0.7.
- Candidate cuối là một global prompt bundle, chưa phải portfolio/router theo loại target.

Trước mỗi benchmark, lưu tối thiểu:

- Git commit và branch.
- Dataset digest, danh sách target và split.
- Random seed của dataset và GEPA.
- `COVERUP_MODEL` và `OPTIMIZE_MODEL` (không ghi credential).
- `max_metric_calls`, minibatch size, replicate count, concurrency, rate limit.
- `max_attempts`, `repeat_tests`, pytest args và timeout.
- Prompt digest của baseline và optimized candidate.
- Runner/container image digest và dependency lock digest.
- Tổng số LLM calls, token, thời gian và chi phí ước lượng.

## 3. Pha 0 — Xác nhận phép đo có đáng tin cậy

### E00 — Reproduce baseline nhiều lần

**Trạng thái:** có thể chạy bằng pipeline hiện tại.

**Mục tiêu:** đo độ nhiễu của việc sinh test và runner trước khi đánh giá optimizer.

**Cách thử:**

- Chạy cùng baseline trên cùng locked dataset ít nhất 5 lần.
- Không thay prompt, model, target hoặc project setup.
- Lưu coverage theo từng target, không chỉ aggregate.
- Ghi pass/collection/error rate, số target không có coverage và runtime.

**Kết luận:**

- Nếu khoảng dao động baseline đã lớn hơn 2 điểm, kết quả `69 -> 71` chưa đủ chứng minh prompt tốt hơn.
- Nếu baseline ổn định trong khoảng dưới 1 điểm, mức tăng 2 điểm có khả năng là gain thật nhưng vẫn cần paired evaluation.

### E01 — Paired repeated comparison

**Trạng thái:** pipeline đã có paired baseline/proposal; cần tăng replicate ở run quyết định.

**Cách thử:**

- Chạy baseline và proposal trên cùng target set.
- Dùng 3–5 generation replicates cho top candidate.
- Báo cáo delta của từng target, median delta, micro-average delta và độ lệch chuẩn.
- Tách số target thắng, hòa, thua.

**Điều kiện promote đề xuất:**

- Mean optimized lớn hơn mean baseline.
- Cận dưới của khoảng tin cậy không âm, hoặc tối thiểu đa số replicate thắng theo paired comparison.
- Không tăng collection/runtime failure đáng kể.

### E02 — Kiểm tra denominator và metric

**Trạng thái:** phân tích artifacts hiện có.

Xác minh:

- Baseline và candidate dùng cùng statement/branch denominator.
- Target lỗi nhận 0 covered units nhưng không làm mất denominator.
- Aggregate là micro-average đúng theo executable units.
- Không có target bị bỏ khỏi candidate result vì lỗi.
- Không so coverage report của hai protocol hoặc hai split khác nhau.

## 4. Pha 1 — Đo trần có thể đạt (oracle headroom)

### E10 — Oracle union coverage

**Trạng thái:** hoàn thành script/report, coverage-unit oracle và combined-suite verification trên calibration 16 target.

**Mục tiêu:** xác định các candidate đã từng tạo được bao nhiêu coverage hữu ích, kể cả khi không candidate đơn lẻ nào giữ được toàn bộ.

**Cách tính theo từng target:**

1. Thu thập coverage của mọi test hợp lệ từ baseline và mọi GEPA candidate/replicate.
2. Lấy hợp của executed statements và executed branch arcs.
3. Tính oracle statement, branch và aggregate score trên denominator cố định.
4. Sau đó ghép các test tạo gain vào một suite thật và chạy lại để phát hiện xung đột, pollution hoặc flaky test.

Không chỉ nối các phần trăm. Phải hợp trên tập statement và branch arc cụ thể.

**Cách diễn giải:**

- `oracle <= best candidate + 2 điểm`: generation/context đã gần chạm trần; search tốt hơn khó tạo gain lớn.
- `oracle cao hơn best candidate 5–10 điểm`: selection/merge đang làm mất test hoặc chiến lược chuyên biệt.
- `oracle >= 80%` trong khi best candidate khoảng 71%: có cơ sở theo đuổi portfolio, routing hoặc test archive.
- `oracle chỉ 72–74%`: ưu tiên sửa context, setup, model hoặc thêm phương pháp sinh input; không tăng budget GEPA một cách mù quáng.

### E11 — Headroom theo failure family

Phân mỗi target chưa đạt thành một hoặc nhiều nhóm:

- Import/collection/setup failure.
- Dependency hoặc plugin không tương thích.
- Model response rỗng, malformed hoặc thiếu code block.
- Test chạy lỗi và repair không thành công.
- Test pass nhưng không tạo coverage gain.
- Statement còn thiếu.
- Branch còn thiếu và chưa tìm được input.
- Exception/error path khó kích hoạt.
- Stateful/global side effect hoặc I/O cần mock.
- Async/thread/process/time/random behavior.
- C-extension, platform-specific hoặc external service không thể cô lập.
- Test có coverage nhưng assertion yếu.

Báo cáo số target và số executable units còn thiếu trong từng nhóm. Nhóm chiếm nhiều uncovered units nhất là nơi cần ưu tiên, không nhất thiết là nhóm có nhiều target nhất.

### E12 — Human/strong-model upper-bound sample

Chọn 10–20 target khó đại diện. Cho một người hoặc model mạnh có đầy đủ repo context viết test thủ công, không giới hạn bởi prompt hiện tại.

- Nếu vẫn không tăng coverage: target/setup có thể không khả thi.
- Nếu tăng mạnh: pipeline đang thiếu context, tool hoặc chiến lược, không phải thiếu headroom.

## 5. Pha 2 — Các thử nghiệm GEPA có thể chạy sớm

Chỉ chạy pha này sau khi E00–E12 cho thấy phép đo ổn định và còn headroom.

### E20 — Tăng metric budget đúng theo validation set

**Trạng thái:** chạy được qua cấu hình hiện tại.

Thử lần lượt:

- Control: 30 calls.
- Light: 120 calls.
- Medium: 300 calls.
- Heavy: 600 calls nếu kết quả 300 vẫn còn tăng và chi phí chấp nhận được.

Quy tắc tham khảo: `max_metric_calls = 15–30 × len(validation_targets)`. Phải lưu số candidate proposal thực tế vì full validation có thể tiêu thụ một khối metric calls lớn.

**Dừng sớm:** nếu 10 proposal liên tiếp không cải thiện validation hoặc oracle cho thấy không còn headroom.

### E21 — Reflection minibatch cho code

**Trạng thái:** cần expose/configure nếu frontend/backend chưa cho chọn.

So sánh trên cùng budget:

- Minibatch 1: reflection rất sâu cho từng failure.
- Minibatch 2–3: phương án ưu tiên.
- Minibatch 5.
- Minibatch 8: control hiện tại.

Theo dõi input tokens của reflection. Hiện mỗi trajectory có thể chứa source, feedback, test code và repair episodes; batch 8 có nguy cơ làm model bỏ sót chi tiết.

### E22 — Nhiều GEPA seed

**Trạng thái:** đã triển khai và chạy live seed 7/17/37. Seed 17/37 tạo các proposal hợp lệ ở
reflection nhưng không proposal nào vượt selection để vào finalist list; pool hiệu dụng vẫn chỉ
có baseline + proposal seed 7. Rerank/final gate không đổi và proposal bị reject. Xem
`binh/PHASE1_E22_MULTI_SEED_RESULT.md`.

- Chạy tối thiểu seed 7, 17 và 37.
- Mỗi seed dùng cùng split, budget và model.
- Gom top candidate của cả ba run.
- Rerank trên cùng locked validation với 3 replicate.
- Chỉ candidate thắng cuối cùng mới được chạy test holdout.

### E23 — Strong reflection model

**Trạng thái:** chạy được nếu model đã nằm trong allowlist và Vertex/API hỗ trợ.

Giữ nguyên `COVERUP_MODEL`, chỉ đổi `OPTIMIZE_MODEL`:

- Control: model reflection đang dùng.
- Pro-tier: model mạnh hơn để chẩn đoán trace và đề xuất prompt.

Không đổi đồng thời task model và reflection model. Nếu đổi cả hai, không xác định được gain đến từ test generator hay optimizer.

### E24 — Reflection temperature

**Trạng thái:** đã chạy live `0,2 / 0,5 / 0,7 / 1,0` với seed 7, budget 30. Temperature 0,2
thắng repeated validation nhưng thua paired holdout 27,92 điểm; reject. Xem
`binh/PHASE1_E24_REFLECTION_TEMPERATURE_RESULT.md`.

So sánh `0.2`, `0.5`, `0.7`, `1.0` trên budget nhỏ trước.

- Quá thấp: proposal ít đa dạng, dễ lặp lại baseline.
- Quá cao: proposal dài, không ổn định hoặc phá invariant.

Chọn theo tỷ lệ proposal hợp lệ, diversity digest và validation gain, không chỉ theo candidate tốt nhất.

### E25 — Pareto exploration

**Trạng thái:** đã triển khai selector configurable và chạy live `70/30`, `50/50`, pure Pareto trên
validation 12 target. Pure Pareto tăng Pareto-oracle lên 78,88% nhưng mọi global proposal đều thua
baseline repeated rerank; reject và không mở holdout. Post-hoc target-router oracle đạt 89,86%, cao
hơn baseline 28,59 điểm. Xem `binh/PHASE1_E25_PARETO_EXPLORATION_RESULT.md`.

**Dataset quyết định:** sau E24, validation đã được mở rộng từ 4 lên 12 target có phân tầng theo
repo và độ khó. Baseline 3 replicate đạt 68,55%, sample SD giảm từ 11,54 xuống 5,43 điểm; 4 test
target mới vẫn khóa. Xem `binh/PHASE1_STRATIFIED_VALIDATION_RESULT.md`.

So sánh:

- Current-best 70% / Pareto 30% hiện tại.
- Current-best 50% / Pareto 50%.
- Pure Pareto/default.
- Epsilon-greedy nếu phiên bản GEPA hiện tại hỗ trợ ổn định.

Theo dõi:

- Single-best validation score.
- Oracle/Pareto per-target score.
- Khoảng cách giữa Pareto score và single-best score.
- Số strategy family khác nhau được khám phá.

Khoảng cách Pareto lớn nhưng single-best thấp là tín hiệu nên merge thêm hoặc dùng portfolio/router.

### E26 — Top-K reranking

**Trạng thái:** đã triển khai và chạy live trên run E41 budget 30. Search chỉ có baseline + một
proposal nên top-5 hiệu dụng là 2. Rerank 3 replicate vẫn chọn proposal (+6,30 điểm validation),
nhưng proposal thua holdout 9,99 điểm và bị reject. Xem `binh/PHASE1_E26_TOPK_RERANK_RESULT.md`.

- Không lấy ngay `result.best_candidate` sau một noisy evaluation.
- Lấy top 5 candidate theo validation.
- Chạy lại mỗi candidate 3–5 replicate.
- Chọn theo mean coverage, rồi dùng failure rate và variance làm tie-breaker.

### E27 — Parallel/multiple proposals

**Trạng thái:** cần đánh giá nâng `gepa==0.0.27` và kiểm thử tương thích trước.

Sau khi upgrade an toàn, thử:

- Nhiều mutation của cùng một strong parent.
- Nhiều parent khác nhau trên Pareto frontier.
- Kết hợp explore/exploit và giữ top-K improvement.

Không nâng dependency cùng lúc với thay metric hoặc dataset. Chạy toàn bộ unit/integration tests và một control benchmark sau migration.

### E28 — Prompt length/token objective

**Trạng thái:** đã triển khai raw/adjusted score, penalty theo 1.000 ký tự, hard cap trước
generation và replay cache. Penalty 0,02 hoặc cap 4.000 tránh proposal regression nhưng chưa tạo
gain so với baseline. Xem `binh/PHASE1_E28_PROMPT_LENGTH_RESULT.md`.

Current proposer yêu cầu playbook đầy đủ nên prompt có thể ngày càng dài. So sánh:

- Không phạt độ dài.
- Hard cap ký tự/token.
- Multi-objective: coverage cao, prompt ngắn, chi phí generation thấp.

Kiểm tra xem prompt dài hơn có thật sự tăng coverage hay chỉ làm model phân tán khỏi source và coverage target.

## 6. Pha 3 — Bổ sung Actionable Side Information cho reflection

### E30 — Failure taxonomy có cấu trúc

**Trạng thái:** đã triển khai schema 3 và chạy live control. Integration thành công nhưng best candidate không giảm repair exhaustion và thua baseline validation 26,54 điểm. Xem `binh/PHASE1_E30_LIVE_CONTROL_RESULT.md`.

Thay vì chỉ gửi log dài, tạo record có trường rõ ràng:

- `failure_stage`: generation, collection, execution, assertion, coverage.
- `failure_type`: import, fixture, timeout, malformed, no_gain, uncovered_branch...
- `expected` và `actual`.
- First actionable traceback frame.
- Test code gây lỗi và repair code kế tiếp.
- Remaining statements/branches.
- Candidate vs parent delta.
- Repo/setup context liên quan.

So sánh cùng budget giữa raw-log reflection và structured reflection.

### E31 — Contrastive win/loss evidence

**Trạng thái:** pipeline đã có một phần candidate/parent evidence; cần kiểm tra completeness.

Cho reflection thấy theo cặp:

- Baseline test.
- Parent test.
- Candidate test.
- Coverage arc được thêm/mất.
- Failure được sửa hoặc mới xuất hiện.

Yêu cầu proposer rút ra một quy tắc tổng quát, không chép tên repo, file, symbol hoặc line number vào prompt.

### E32 — Reflection theo failure cluster

**Trạng thái:** cần custom batch sampler hoặc bước gom nhóm.

Thay epoch-shuffled thuần túy bằng minibatch có chủ đích:

- Một batch import/setup failures.
- Một batch no-coverage-gain.
- Một batch branch-input failures.
- Một batch repair failures.
- Một batch regression của candidate trước.

Sau đó so với shuffled minibatch 2–3. Mục tiêu là tạo proposal tập trung thay vì một prompt cố sửa nhiều nguyên nhân không liên quan.

### E33 — Positive exemplars và regression guards

Lưu các trace tạo gain thật theo failure family. Reflection nhận:

- Một ví dụ thành công gần nhất.
- Một ví dụ thất bại tương phản.
- Quy tắc nào từ parent cần giữ.

Không đưa nguyên test/file cụ thể vào global prompt. Chỉ đưa summary hoặc retrieve exemplar lúc chạy task tương tự.

## 7. Pha 4 — Bổ sung context cho CoverUp lúc sinh test

Thông tin đặc thù repo phải được retrieve động cho từng target, không bake cứng vào optimized global prompt.

### E40 — Exact branch arcs và path condition

**Ưu tiên cao nhất vì metric hiện ưu tiên branch 70%.**

Cho generator biết:

- Arc nguồn -> đích còn thiếu.
- Biểu thức `if/elif/match/loop` tạo arc.
- Điều kiện cần true/false.
- Dominating conditions trước branch.
- Exception path và early return liên quan.

Nếu có thể, dùng AST/control-flow analysis để diễn giải thành constraint đơn giản. Đo branch coverage gain riêng.

### E41 — Signature, type và behavior contract

Bổ sung có chọn lọc:

- Function/class signature.
- Type hints và default values.
- Docstring, raises và return semantics.
- Constants/enum liên quan.
- Decorator và inheritance cần thiết.

Không dump toàn bộ file nếu phần lớn không liên quan.

**Trạng thái 2026-08-14:** đã implement và promote contract-only retrieval động theo target cho
exact signature, type/default/return annotation, decorator, docstring rút gọn và inheritance.
Validation 3 replicate tăng 3,92 điểm; locked holdout 3 replicate tăng 13,98 điểm so với control.
Context không được bake vào global prompt và bị chặn bởi budget ký tự.

### E42 — Relevant callers/callees

**Trạng thái 2026-08-15:** đã implement retrieval có giới hạn cho constructor, direct callee và usage example,
chỉ kích hoạt sau `test_error`. Train hard-target smoke tăng từ 0 lên 82,44%, nhưng E70 validation 8 target hòa
baseline ở 8,04%; chưa promote. Bottleneck mới là module test nhiều case bị loại toàn bộ chỉ vì một case còn lỗi.
Xem `binh/PHASE1_E42_E46_FAILURE_CONTEXT_RESULT.md`.

Retrieve source của:

- Callee trực tiếp xuất hiện trong branch khó.
- Constructor/model cần tạo input.
- Caller hoặc usage example thể hiện cách dùng đúng.
- Global/config object được đọc bởi target.

So sánh fixed excerpt hiện tại với call-graph-aware context ở cùng token budget.

### E43 — Existing tests và fixtures

Bổ sung:

- `conftest.py` liên quan.
- Fixture gần target.
- Existing tests import cùng module/class.
- Monkeypatch/mock pattern của repo.
- Async marker và plugin cần thiết.

Mục tiêu chính là giảm collection/import/runtime failure và làm test phù hợp convention của project.

**Trạng thái 2026-08-14:** retrieval tĩnh có giới hạn đã implement nhưng bị reject và mặc định tắt.
Contract + existing tests/fixtures giảm 1,96 điểm validation, tăng test-error từ 3 lên 11 và có một
target hết repair attempts. Runner vẫn hỗ trợ ablation explicit; cache schema 17 tách policy này
khỏi contract-only và hash cây test để tránh tái dùng kết quả sai context.

### E44 — Project setup manifest

Tạo manifest tự động từ:

- `pyproject.toml`, `setup.cfg`, `tox.ini`, `pytest.ini`.
- Dependency/version quan trọng.
- Package root và import path.
- Pytest plugins/markers.
- Python version và OS constraints.
- Setup warnings hoặc package không cài được.

Chỉ truyền phần manifest liên quan vào target prompt; lưu manifest đầy đủ làm artifact.

### E45 — Runtime probes/tool use

Cho agent quyền hỏi thông tin giới hạn và an toàn:

- `inspect.signature`.
- In danh sách enum/constants.
- Khởi tạo object nhỏ trong sandbox.
- Chạy một probe để quan sát output/exception.
- Đọc source dependency nội bộ liên quan.

Ghi mọi tool call/output vào trace để GEPA reflection học được lúc nào nên yêu cầu thêm thông tin.

### E46 — Retrieval theo lỗi

**Trạng thái 2026-08-15:** đã implement failure-family routing cho attribute/protocol, import/export,
assertion/behavior, constructor/type và filesystem/setup; context bị cap 4.000 ký tự và không xuất hiện ở initial
prompt. Validation chưa có gain, nên policy mặc định vẫn tắt và E70 test chưa được mở.

Không đưa mọi loại context vào mọi request. Dùng policy:

- Import error -> retrieve setup/import examples.
- Fixture error -> retrieve `conftest.py` và nearby tests.
- No branch gain -> retrieve exact branch condition/callees.
- Wrong assertion -> retrieve docstring, behavior examples hoặc mutation survivor.

Đo coverage gain trên mỗi 1.000 input tokens để tránh context càng nhiều càng tốt giả tạo.

## 8. Pha 5 — Tối ưu kiến trúc prompt thay vì chỉ hai component

### E50 — Tách prompt thành các module có trách nhiệm rõ ràng

**Trạng thái:** cần thay đổi kiến trúc candidate và CoverUp integration.

Candidate đề xuất:

1. `context_policy`: quyết định cần đọc thêm gì.
2. `branch_planner`: lập danh sách path/test case.
3. `test_generator`: sinh pytest module hoàn chỉnh.
4. `execution_repair`: sửa syntax/import/collection/runtime.
5. `coverage_repair`: test đã pass nhưng vẫn thiếu branch/statement.

GEPA chỉ mutate component có causal evidence. Chạy ablation `2 components` vs `5 components` với cùng tổng metric-call budget.

### E51 — Plan-before-code

Trước khi sinh pytest, yêu cầu model lập structured plan:

- Mỗi uncovered branch cần input nào.
- Fixture/mocks nào cần tạo.
- Expected assertion lấy từ đâu.
- Rủi ro side effect nào cần cô lập.

Plan không phải output cuối; test generator nhận plan đã validate. So sánh với one-shot generation.

### E52 — Separate coverage repair

Current `error` chủ yếu xử lý test lỗi. Thêm vòng riêng khi:

- Pytest pass.
- Coverage đo được.
- Vẫn còn uncovered arcs.

Prompt vòng này phải nhận previous passing test, gained/remaining arcs và yêu cầu mở rộng test mà không làm mất behavior đã pass.

### E53 — Diagnose -> propose -> critic

Thay one-shot reflection bằng ba vai trò logic:

1. Diagnoser tạo failure hypotheses có evidence.
2. Proposer sửa component.
3. Critic kiểm tra placeholder, generalization, prompt bloat và regression risk.

Chỉ evaluate candidate qua CoverUp nếu qua deterministic validator và critic gate. Đo tỷ lệ proposal bị loại và metric calls tiết kiệm được.

## 9. Pha 6 — Các phương pháp hệ thống có cơ hội tạo gain 10–15 điểm

Những phương pháp này không còn là “chỉ tối ưu một global prompt”, nhưng có thể cải thiện KPI coverage mạnh hơn.

### E60 — Candidate test archive

**Ưu tiên cao nếu oracle union lớn.**

**Trạng thái:** đã triển khai greedy archive khóa theo split/evaluation digest và bộ lọc source replicate.
Calibration ban đầu chọn 14/26 test, đạt 86,75%. Trên pool E25, archive hai replicate đạt
96,32–97,59%, pass `repeat_tests=5` và hơn single-best tương ứng ít nhất 18,85 điểm. Xem
`binh/PHASE1_E67_PARETO_OUTPUT_PORTFOLIO_RESULT.md`.

- Giữ mọi generated test tạo thêm statement/branch mà không regression.
- Không vứt test tốt chỉ vì aggregate candidate prompt không thắng.
- Dùng greedy set-cover để chọn tập test nhỏ phủ nhiều uncovered units nhất.
- Chạy suite hợp nhất để loại pollution/flakiness.

So sánh single-best prompt output với archived-union test suite.

### E61 — Prompt portfolio/router

Thay một prompt chung bằng portfolio theo target/failure family:

- Parsing/string/data transformation.
- Stateful/object lifecycle.
- Exception/error handling.
- I/O/mocking.
- Async/concurrency.
- Numeric/boundary-heavy logic.

Router có thể dùng static features hoặc một classifier nhỏ. Selection/router chỉ được train trên train/validation, không nhìn test holdout.

### E62 — Best-of-K generation cho target khó

- Target dễ: một generation.
- Target khó hoặc có nhiều branches: sinh K candidate tests.
- Chạy từng candidate trong sandbox.
- Giữ test tạo marginal coverage gain tốt nhất.

Đo gain theo cost. Không áp dụng K lớn cho mọi target.

### E63 — Property-based testing

Cho target phù hợp, sinh Hypothesis strategies từ:

- Type hints.
- Boundary constants.
- Branch predicates.
- Input validation conditions.

Đặc biệt hữu ích cho numeric, parser và combinatorial branches. Phải kiểm soát deadline, flaky examples và lưu failing example ổn định.

### E64 — Constraint/symbolic-assisted input generation

Trích điều kiện branch bằng AST hoặc symbolic execution đơn giản, sau đó cho LLM chuyển nghiệm thành pytest fixture/assertion. Phù hợp khi model hiểu test structure nhưng đoán input không đi vào branch.

### E65 — Fuzz/search-assisted generation

Dùng random/fuzz/search để tìm input tăng coverage, rồi cho LLM:

- Biến input thành deterministic regression test.
- Thêm assertion có ý nghĩa.
- Loại dependency vào seed hoặc timing.

### E66 — Mutation-guided test improvement

- Chạy mutation testing có giới hạn trên target được chọn.
- Lấy surviving mutants đại diện.
- Gửi original vs mutant behavior vào generator.
- Yêu cầu test phân biệt hai behavior.
- Dùng mutation score làm secondary objective, không thay coverage metric chính giữa benchmark.

### E67 — Inference-time Pareto outputs

**Trạng thái:** đã chạy one-shot holdout và **reject**. Pool 5 prompt từng cho validation proof bằng candidate-test portfolio. Pool được
chạy theo từng replicate, test có coverage gain được content-deduplicate, greedy set-cover và chạy lại cùng
nhau 5 lần. Một replicate đạt trung bình 90,15%; mọi cặp hai replicate đạt 96,32–97,59%, trong khi
baseline repeated mean là 61,27%. Đây là gain của portfolio test, không phải một global prompt tốt hơn.

GEPA đã theo dõi best outputs/Pareto nhưng pipeline cuối hiện ưu tiên một best prompt. Thử:

- Lấy best output theo từng validation/task family.
- Gom strategy hoặc test tạo gain.
- So single-best score với Pareto-oracle score.
- Chỉ triển khai routing nếu gain lặp lại trên holdout.

**Quyết định ban đầu (đã được follow-up thay thế):** dùng hai replicate làm cấu hình E67 ứng viên vì ba replicate chỉ đạt 97,26% và
không tạo lợi ích rõ so với hai. Bước kế tiếp là tự động hóa chiến lược chạy baseline trước, chỉ mở replicate
thứ hai cho target còn thiếu coverage, rồi dùng đúng một one-shot holdout gate trước khi production hóa.

**Follow-up cost-aware trên validation:** đã triển khai `sequential-archive`. Schedule 7 stage với stop score 0,80 chỉ mở
29/180 target-generations nhưng suite thật vẫn đạt 96,93%, hơn best single 19,28 điểm và pass 5 lần. Policy
và threshold được freeze trên validation. Xem
`binh/PHASE1_E67_COST_AWARE_SEQUENTIAL_RESULT.md`.

**One-shot holdout:** policy được commit/freeze trước khi mở holdout. Nó chỉ dùng 10/60 target-generations
(tiết kiệm proxy 83,33%), nhưng score 89,48% bằng đúng baseline replicate 0; cả 4 test được chọn đều từ
baseline và sáu stage bổ sung có marginal gain bằng 0. E67 không chứng minh được gain 10–15 điểm trên dữ liệu
chưa thấy, vì vậy không promote và không tune lại trên holdout đã dùng. Xem
`binh/PHASE1_E67_ONE_SHOT_HOLDOUT_RESULT.md`.

## 10. Dataset và sampling

### E70 — Failure-stratified train set

**Trạng thái 2026-08-15:** đã implement static failure-stratified builder và khóa dataset mới 32 target:
16 train / 8 validation / 8 test, cân bằng 4 project và difficulty 25/50/25. Mỗi split có đủ bảy strata,
32 target không trùng identity hoặc structural fingerprint với nhau và không trùng 35 target từng dùng.
Holdout mới có SHA-256 `fa029ed3...a815c`, trạng thái `locked_unevaluated`; selection dùng 0 model calls.
Static strata là challenge proxy, observed failure labeling mới chỉ được chạy trên train/validation. Xem
`binh/PHASE1_E70_FAILURE_STRATIFIED_DATASET.md`.

**Baseline labeling follow-up:** đã chạy đúng một replicate trên 16 train + 8 validation bằng Gemini 3.5
Flash-Lite; E70 test vẫn khóa. Combined aggregate là 34,90%, nhưng 20/24 target full coverage. Hai hard target
bằng 0 chiếm 99,64% statement headroom và 95,24% branch headroom. Đưa cả hai lên khoảng 20% coverage tương
ứng gain ước tính +12,56 điểm. Ưu tiên failure-triggered E42/E44 retrieval thay vì tăng global GEPA budget.
Xem `binh/PHASE1_E70_BASELINE_LABELING_RESULT.md`.

Không chỉ chọn random hoặc nhiều branch nhất. Tạo train set có đủ:

- Branch-heavy.
- Statement-heavy.
- Exception paths.
- Fixture/mock dependent.
- Stateful/class methods.
- Async/I/O.
- Easy successes để giữ regression guard.

### E71 — Hard-target curriculum

- Giai đoạn đầu học trên target có feedback rõ và setup hợp lệ.
- Giai đoạn sau tăng tỷ lệ target khó/no-gain.
- Không để toàn bộ minibatch là lỗi setup không thể sửa bằng prompt.

### E72 — Leave-one-repository-out

Với ba sample repo:

1. Train/validation trên repo A+B, test trên C.
2. Train/validation trên A+C, test trên B.
3. Train/validation trên B+C, test trên A.

Báo cáo cả ba fold. Đây là phép thử quan trọng nếu prompt production phải dùng được cho repo upload mới.

### E73 — Kiểm tra leakage và duplicate

- Không để cùng qualified symbol ở nhiều split.
- Hạn chế function gần như giống nhau nằm cả train và test.
- Nếu đo generalization liên-repo, split theo project thay vì random symbol.
- Không retrieve test từ locked test split vào reflection.

## 11. Metric mở rộng nhưng không làm sai benchmark

Coverage vẫn là primary metric để so với baseline hiện tại. Các metric sau dùng làm secondary objective hoặc tie-breaker:

- Pytest pass rate.
- Collection success rate.
- Statement coverage.
- Branch coverage.
- Mutation score.
- Flaky rate qua repeated execution.
- Runtime/timeout rate.
- Prompt input/output tokens.
- Cost trên mỗi target và cost trên mỗi điểm coverage tăng.
- Prompt length.
- Số test và thời gian chạy suite.
- Regression: executable units từng được baseline cover nhưng candidate làm mất.

Không gộp các metric mới vào một scalar tùy ý rồi so trực tiếp với con số baseline 69%. Luôn giữ bảng metric thành phần.

## 12. Ma trận ablation đề xuất

Chạy theo thứ tự để xác định nguồn gain:

| Run | Search config | Evidence/context | Architecture | Mục đích |
| --- | --- | --- | --- | --- |
| A0 | Hiện tại | Hiện tại | 2 component | Control |
| A1 | Budget đúng | Hiện tại | 2 component | Đo ảnh hưởng budget |
| A2 | Budget + batch 2–3 | Hiện tại | 2 component | Đo chất lượng reflection |
| A3 | A2 + multi-seed/top-K | Hiện tại | 2 component | Đo search variance |
| B1 | Như A0 | Structured failures | 2 component | Đo ASI |
| B2 | Như A0 | Branch/path context | 2 component | Đo context cho coverage |
| B3 | Như A0 | Repo tests/setup context | 2 component | Đo setup/import gain |
| C1 | A3 | B1+B2+B3 | 2 component | Search + evidence |
| C2 | A3 | B1+B2+B3 | 5 component | Đo modular prompt |
| D1 | C2 | C2 | Test archive | Đo oracle exploitation |
| D2 | C2 | C2 | Portfolio/best-of-K | Đo system-level gain |
| D3 | C2 | Mutation feedback | Portfolio | Đo test effectiveness |

Mỗi run cần ít nhất ba seed ở bước xác nhận cuối. Không cần ba seed cho mọi smoke ablation nếu chi phí cao; có thể chạy một seed để loại phương án rõ ràng kém, sau đó mới xác nhận.

## 13. Thứ tự triển khai khuyến nghị

### P0 — Bắt buộc trước khi tối ưu tiếp

- [x] E00: đã đo 6 baseline validation độc lập; mean 56,57%, sample SD 21,78 điểm, range 53,50 điểm.
- [x] E01: đã paired baseline/candidate trên 3 replicate; candidate thua mean 16,49 điểm và bị reject trước holdout lặp.
- [x] E02: audit denominator/metric.
- [x] E10: oracle union coverage.
- [x] E11: đã có failure-family/headroom report cho repeated validation; 10/24 target-replicate hết attempts, ưu tiên E30 repair taxonomy.
- [ ] Tạo experiment manifest và bảng leaderboard chuẩn.

### P1 — Ít thay đổi kiến trúc, khả năng có gain sớm

- [x] E20 budget 30 với E41: proposal tăng validation 17,46 điểm nhưng thua paired 3-replicate holdout 9,99 điểm; reject. Chưa có lý do chạy 120/300.
- [x] E21: đã chạy minibatch 3 so với 8 trên calibration 16 target. Chưa có cấu hình thắng: batch 3 overfit holdout, batch 8 giữ baseline; cần repeated paired evaluation vì variance lớn. Xem `binh/PHASE1_MINIBATCH_ABLATION_RESULT.md`.
- [x] E22: multi-seed seed 7/17/37 đã chạy. Pool chỉ còn 2 unique finalist; winner validation vẫn thua holdout 9,99 điểm, reject.
- [x] E24: reflection temperature 0,2/0,5/0,7/1,0 đã chạy. Winner 0,2 đạt validation 97,78% nhưng thua holdout 27,92 điểm, reject.
- [x] Dataset sau E24: khóa split 8 train / 12 validation / 4 test mới; baseline validation 3 replicate đạt 68,55% với sample SD 5,43 điểm. Test mới chưa được mở.
- [x] E25: selector 70/30, 50/50 và pure Pareto đã chạy. Global winner vẫn là baseline; pure Pareto tăng oracle diversity và target-router upper bound đạt +28,59 điểm. Không mở holdout.
- [ ] E23: strong reflection model.
- [x] E26: top-K repeated reranking đã triển khai và chạy live. Candidate pool chỉ có 2 nên winner không đổi; validation +6,30 điểm nhưng paired holdout -9,99 điểm, reject.
- [x] E30: taxonomy/schema 3 và live control hoàn tất; không có gain, chuyển sang E41/E43 để bổ sung API/test context.
- [ ] E40: exact branch/path context.

### P2 — Nâng chất lượng context và reflection

- [ ] E31–E33: contrastive/clustered reflection.
- [x] E41: exact signature/type/default/docstring/decorator/inheritance context đã thắng validation và locked holdout; promote thành mặc định.
- [x] E42: callers/callees context (implemented; validation tie, not promoted).
- [x] E43: relevant existing tests/fixtures đã implement nhưng live ablation thua; reject và giữ mặc định tắt.
- [ ] E44–E46: E46 failure-triggered retrieval đã implement nhưng chưa thắng validation; E44 manifest và E45 runtime probes còn thiếu.
- [ ] E25: Pareto exploration ablation.
- [x] E28: prompt length objective/hard cap đã triển khai và replay. Penalty 0,02/1k hoặc cap 4.000 chọn baseline, tránh regression nhưng chưa tạo coverage gain.

### P3 — Thay đổi kiến trúc để hướng tới gain lớn

- [ ] E50–E53: modular prompt pipeline.
- [x] E60: candidate test archive.
- [ ] E61: prompt portfolio/router.
- [ ] E62: adaptive best-of-K.
- [ ] E63–E66: property, constraint, fuzz và mutation assistance.

### P4 — Chứng minh khả năng generalize

- [ ] E72: ba fold leave-one-repository-out.
- [ ] Chạy locked test đúng một lần cho mỗi cấu hình đã chốt.
- [ ] Báo cáo mean/median/variance, paired delta, cost và failure rate.
- [ ] Chỉ promote khi gain ổn định và không phá regression gate.

## 14. Điều kiện quyết định và điều kiện dừng

### Tiếp tục đầu tư GEPA search khi

- Oracle union cao hơn single-best đáng kể.
- Validation vẫn cải thiện khi tăng budget.
- Reflection tạo proposal đa dạng, hợp lệ và gắn với failure thật.
- Pareto frontier có candidate chuyên biệt tạo gain trên nhiều target.

### Chuyển sang sửa context/harness khi

- Oracle gần bằng best candidate nhưng thấp hơn mục tiêu.
- Phần lớn uncovered units thuộc import/setup/no-context/path-input failures.
- Tăng budget chỉ tạo prompt dài hơn mà coverage không tăng.

### Chuyển sang portfolio/test archive khi

- Pareto-oracle cao nhưng single global prompt thấp.
- Candidate khác nhau thắng trên các failure family khác nhau.
- Gộp test tạo coverage gain và vẫn pass ổn định.

### Dừng theo đuổi mục tiêu 10–15 điểm trên dataset hiện tại khi

- Human/strong-model upper-bound và oracle đều không đạt mục tiêu.
- Gain chỉ xuất hiện trên validation nhưng không lặp lại ở project holdout.
- Chi phí tăng quá nhanh so với coverage gain.
- Gain đến từ thay đổi target/split/denominator hoặc làm baseline yếu đi.

## 15. Mẫu ghi chép một experiment

```markdown
### Experiment ID: E__-YYYYMMDD-seed__

- Hypothesis:
- Git commit:
- Artifacts directory:
- Dataset/split digest:
- Train/validation/test counts:
- COVERUP_MODEL:
- OPTIMIZE_MODEL:
- Baseline prompt digest:
- GEPA seed:
- Dataset seed:
- Max metric calls:
- Reflection minibatch:
- Evaluation/final replicates:
- Other changed variable:
- Variables intentionally held constant:
- Baseline statement/branch/aggregate:
- Candidate statement/branch/aggregate:
- Paired delta:
- Win/tie/loss targets:
- Oracle union score:
- Pass/collection/failure rate:
- Tokens/cost/runtime:
- Result: accept / reject / rerun
- Evidence-backed conclusion:
- Next experiment:
```

## 16. File và tài liệu liên quan trong repo

- `src/optimization/gepa.py`: adapter, reflection evidence, selector, budget, seed và GEPA call.
- `src/optimization/metrics.py`: statement/branch scoring và aggregate coverage.
- `src/optimization/cli.py`: baseline, optimize, final comparison và promotion gate.
- `src/optimization/runner.py`: isolated CoverUp execution và generated-test workspace.
- `src/optimization/project_setup.py`: setup của sample repository.
- `src/coverup/`: generation, coverage feedback, tool/context và repair loop.
- `tests/test_coverage_optimization.py`: invariant của optimizer/evaluation.
- `tests/test_dataset_builder.py`: dataset selection/splitting.
- `tests/test_project_setup.py`: repository setup behavior.
- `eval/prompt_optimization/`: dataset, baseline prompt và hướng dẫn benchmark.

## 17. Tài liệu nghiên cứu tham khảo

- GEPA paper: <https://arxiv.org/abs/2507.19457>
- GEPA guides: <https://gepa-ai.github.io/gepa/guides/>
- GEPA FAQ về budget, model, ASI và Pareto: <https://gepa-ai.github.io/gepa/guides/faq/>
- GEPA batch sampling: <https://gepa-ai.github.io/gepa/guides/batch-sampling/>
- GEPA parallel proposals: <https://gepa-ai.github.io/gepa/guides/parallel-proposals/>
- DSPy GEPA overview: <https://github.com/stanfordnlp/dspy/blob/main/docs/docs/api/optimizers/GEPA/overview.md>
- CoverUp paper: <https://arxiv.org/abs/2403.16218>
- MuTAP mutation-guided test generation: <https://arxiv.org/abs/2308.16557>

## 18. Kết quả mong đợi thực tế

Không giả định một phương pháp riêng lẻ sẽ tạo `+10–15 điểm`. Kỳ vọng cần kiểm chứng là:

- Search tuning giúp GEPA khai thác tốt hơn phần headroom đã tồn tại.
- Structured feedback và branch-aware context giúp model tạo test mới mà search hiện tại chưa từng tìm thấy.
- Modular prompts giúp quy trách nhiệm đúng cho planning/generation/repair.
- Portfolio, best-of-K và test archive khai thác các lời giải chuyên biệt mà một global prompt làm mất.
- Mutation feedback cải thiện chất lượng assertion, tránh tối ưu coverage bằng test rỗng hoặc assertion yếu.

Con đường có xác suất cao nhất để đạt khoảng cách lớn là kết hợp **evidence tốt hơn + search đáng tin cậy + lưu/ghép các test tạo gain**, không phải chỉ làm prompt dài hơn hoặc tăng temperature.
