# Luong GEPA hien tai trong pipeline CoverUp

Tai lieu nay mo ta dung luong dang duoc cai dat trong `src/optimization`, khong
phai mo hinh GEPA tong quat. Tat ca so do dung ASCII de co the doc truc tiep trong
terminal va diff Git.

## 1. Muc tieu toi uu

Mot candidate runtime la mot `PromptBundle` gom dung hai text component:

```text
PromptBundle
|
+-- initial
|   Prompt tao test o attempt dau tien.
|
+-- error
    Prompt sua test khi pytest/collection bi loi.
```

Baseline JSON chinh la candidate so 0. GEPA chi sua `initial` va `error`; khong co
mot lop prompt trung gian viet lai bundle truoc khi search.

## 2. Dau vao

Lenh `optimize` nhan cac nhom dau vao sau:

```text
CLI
|
+-- --dataset <jsonl>
|   Moi dong: project, source_file, symbol, split.
|   Split bat buoc cho search: train va validation.
|   Split final: test; neu khong co test thi fallback validation.
|
+-- --prompt <baseline.json>
|   Chua initial va error.
|
+-- --artifacts-dir <dir>
|   Noi luu candidate, cache, generated tests, run log va final report.
|
+-- --max-metric-calls N hoac --auto light|medium|heavy
|   Budget GEPA. Auto hien tai: 120 / 300 / 600.
|
+-- --evaluation-replicates R
|   So lan generate doc lap cho cung candidate-target.
|
+-- CoverUp config
    package_dir, tests_dir, max_attempts, repeat_tests,
    max_concurrency, rate_limit, pytest_args.

Environment
|
+-- COVERUP_MODEL
|   Model sinh pytest.
|
+-- OPTIMIZE_MODEL
    Model reflection de de xuat prompt moi.
```

## 3. Tong quan end-to-end

```text
                         +----------------------+
                         | baseline PromptBundle|
                         +----------+-----------+
                                    |
                                    v
                +-----------------------------------------+
                | Baseline preflight                      |
                | - full train                            |
                | - full validation                       |
                | - lay denominator statement/branch      |
                | - dung neu target khong do duoc coverage |
                +-------------------+---------------------+
                                    |
                                    v
                +-----------------------------------------+
                | GEPA search                             |
                | seed candidate = baseline               |
                | 70% best / 30% Pareto + hybrid frontier|
                | causal selector: initial or error       |
                | reflection minibatch <= 5 examples      |
                | merge enabled                           |
                +-------------------+---------------------+
                                    |
                      +-------------+-------------+
                      |                           |
                      v                           v
            +-------------------+       +-------------------+
            | evaluate candidate|       | reflect + propose |
            | on requested data |------>| revised component |
            +---------+---------+       +---------+---------+
                      ^                           |
                      +---------------------------+
                                    |
                                    v
                      +---------------------------+
                      | GEPA best candidate       |
                      +-------------+-------------+
                                    |
                   digest(best) == digest(baseline)?
                         / yes                 \ no
                        v                       v
       +--------------------------------+  +--------------------------+
       | Save baseline as production    |  | Paired final evaluation  |
       | Skip final test/holdout entirely|  | baseline vs proposal     |
       | final_evaluation_skipped=true  |  | on locked final split    |
       +--------------------------------+  +------------+-------------+
                                                     |
                                         proposal score > baseline?
                                             / yes       \ no
                                            v             v
                                      promote proposal  keep baseline
```

## 4. “Batch” va “example” thuc su la gi?

Day la phan quan trong nhat cua implementation hien tai.

### 4.1 Example cua GEPA

Mot `SymbolTarget` la mot example:

```text
(project, source_file, symbol, split)

Vi du:
(isort, isort/parse.py, parse.file_contents, train)
```

Score tra ve cho GEPA la score rieng cua symbol nay, khong phai mot score chung
duoc gan lap lai cho moi example.

### 4.2 Batch ma GEPA goi

GEPA goi:

```text
adapter.evaluate(batch=[example A, example B, ...], candidate=C)
```

`batch` co the la:

- reflection minibatch nho, toi da 5 example theo cau hinh hien tai;
- mot tap example train/validation ma GEPA can cham;
- khong nhat thiet la toan bo split.

Tat ca example trong mot lan goi phai cung split. Adapter tu choi batch tron train va
validation.

### 4.3 Batch cache cua adapter

Adapter danh gia dung target trong batch GEPA yeu cau va cache chinh batch do:

```text
GEPA asks for [A, B] from train
            |
            v
cache key =
  prompt_digest
  + evaluation_digest(model/config/targets/source hashes)
  + split
  + workspace_kind
  + replicate
```

Neu cache da co:

```text
load exact-batch batch.json
       |
       +--> return only score A and B to GEPA
```

Neu cache chua co:

```text
evaluate only unique targets [A, B]
       |
       +--> write exact-batch batch.json
       |
       +--> return only score A and B to GEPA
```

Baseline preflight van chay toan bo train/validation de co dinh denominator. Candidate
trong reflection chi ton chi phi cua minibatch duoc yeu cau. Candidate thang cuoc moi
duoc danh gia lai tren full train khi tao coverage report.

### 4.4 Cach mot batch duoc chay vat ly

Moi target trong batch dung mot CoverUp process va mot workspace tam rieng. Mot bounded
thread pool chay song song tron vong doi target voi so worker
`min(targets trong batch, max_concurrency)`. CoverUp con dung `--max-concurrency 1` de
khong nhan binh phuong so process/API request. Sau generation, chi cac file co
trace `saved_test` dung `source_file + qualname` duoc copy vao mot generated-tests
workspace luu ben chung cua candidate; workspace tam duoc xoa ngay. Luot coverage
whole-suite cuoi cua CoverUp duoc bo qua vi runner se cham target ngay sau do:

```text
batch targets [A, B, C, D]
            |
            v
bounded target lifecycle pool
   | CoverUp(A) in temp-A -> trace(A) -> copy test_A.py
   | CoverUp(B) in temp-B -> trace(B) -> copy test_B.py
   | CoverUp(C) in temp-C -> trace(C) -> copy test_C.py
   | CoverUp(D) in temp-D -> trace(D) -> copy test_D.py
            |
            v
one persistent candidate workspace
            |
            +==> pytest test_A.py -> coverage/feedback A
            +==> pytest test_B.py -> coverage/feedback B
            +==> pytest test_C.py -> coverage/feedback C
            +==> pytest test_D.py -> coverage/feedback D
            |
            v
exact-batch batch.json
```

Neu mot target khong luu duoc test, runner dung mot collector file rong de lay denominator
zero-coverage. Neu test cua mot target fail, chi target do nhan score 0; cac target khac
van giu score va feedback doc lap. Moi target worker co `COVERAGE_FILE`, pytest
`--basetemp` rieng, tat cache provider va khong ghi bytecode, nen khong tranh chap file.
Neu co `rate_limit`, runner dung mot worker vi limiter cua CoverUp la process-local;
neu khong, generation va local coverage deu tan dung pool chung cua Cloud Run task.

### 4.5 Ket luan ngan gon

```text
Logical API seen by GEPA : per requested batch of examples
Adapter cache unit       : exact requested batch per candidate/replicate
Physical CoverUp unit    : one temporary process/workspace per target
Persistent artifact unit: one consolidated workspace per candidate/split
Coverage unit            : traced test file(s) of one target
Score returned to GEPA   : one weighted score per requested example
```

## 5. Mot target duoc cham nhu the nao?

```text
Minibatch [SymbolTarget A, SymbolTarget B, ...]
    |
    v
Create one persistent candidate workspace
<artifacts>/generated_tests/<split>/<candidate-batch-id>/
    |
    v
Run bounded target workers; each creates a temporary workspace
    +-- initial prompt
    +-- error prompt when generated test fails
    +-- exact target_spec: source_file + qualname
    +-- append target-specific attempt_trace.jsonl
    |
    v
Copy traced test to the persistent workspace and rewrite trace.saved_test
    +-- delete temporary workspace
    |
    v
Run coverage.py on only the mapped test file(s) of one target
    |
    +-- invalid pytest/collection --> score 0
    |
    +-- valid coverage report
            |
            +-- lookup exact source_file + symbol
            +-- count covered statements/branches
            +-- construct feedback and remaining coverage
```

Coverage truoc generation duoc mo hinh hoa la 0 tren chinh denominator cua target.
Test suite goc khong duoc copy vao generated workspace.

## 6. Score cua tung example va aggregate

Raw symbol score:

```text
raw = 0.3 * statement_coverage + 0.7 * branch_coverage
```

Neu toan bo target/split khong co executable branch, trong so duoc chuan hoa ve
100% statement de khong tao 0.7 diem ao cho target khong cover duoc statement nao.

GEPA khong nhan raw score truc tiep. Adapter scale moi example de trung binh score
GEPA bang micro-average cua ca split:

```text
weighted(example i) =
    N * 0.3 * covered_statements_i / total_reference_statements
  + N * 0.7 * covered_branches_i   / total_reference_branches

mean_i(weighted(example i)) = micro-average coverage cua split
```

Trong do:

- `N` la so target cua full split;
- denominator lay tu baseline preflight va duoc co dinh cho moi candidate;
- candidate invalid nhan 0 covered units, khong duoc lam denominator nho di;
- neu co nhieu replicate, score/coverage duoc lay trung binh qua cac replicate.

Adapter con tra hai objective phu cho Pareto frontier:

```text
statement_gain
branch_gain
```

## 7. Vong reflection va sinh candidate

```text
Select component from causal failure evidence
          |
          v
Evaluate selected train examples with capture_traces=true
          |
          v
Keep weak trajectories (raw score < 1 when available)
          |
          v
Reconstruct labelled execution episodes
          |
          +-- initial generated test
          +-- execution error
          +-- each repaired test and its outcome
          |
          v
Compact evidence
    +-- source context <= 12,000 chars
    +-- feedback <= 6,000 chars
    +-- every ordered attempt grouped by replicate
    +-- failing test / repair / traceback / remaining coverage
          |
          v
OPTIMIZE_MODEL writes a diagnostic pytest for one weak target
          |
          v
Run the test in an isolated teacher experiment workspace
          |
          +-- pytest fails: record result and try another experiment
          +-- target score does not improve: record result and try another experiment
          +-- at most 3 experiments without success: keep prompt unchanged
          |
          v
Keep only experiments whose test passes and target score beats baseline
          |
          v
OPTIMIZE_MODEL extracts a reusable lesson and proposes one complete revised template
          |
          v
Validate
    +-- required placeholders are preserved
    +-- no unsupported placeholders
    +-- cited experiment IDs are real successful experiments
    +-- no target-specific file/symbol/line leakage
    +-- component length <= max(600, 3 * baseline length)
          |
          +-- invalid or generic: keep prompt unchanged
          |
          v
Create candidate digest and evaluate candidate
```

Diagnostic tests are teacher-side evidence only. They are saved under
`optimizer_experiments/`, never copied into the candidate test workspace, and never
counted as GEPA coverage. The candidate must improve only when CoverUp independently
generates a new test from the revised prompt. Successful experiment lessons and prompt
lineage are persisted for audit.

Neu `initial` hoac `error` khong co trace thuc su trong trajectory, reflection dataset
cua component do rong va adapter giu nguyen text; model reflection khong duoc goi.

## 8. GEPA search va selection

Cau hinh hien tai:

```text
seed_candidate              = exact baseline bundle
candidate_selection_strategy = 70% current aggregate best + 30% Pareto
frontier_type               = hybrid
module_selector             = causal(initial or exercised error)
reflection_minibatch_size   = min(5, number_of_train_targets)
use_merge                   = true
max_merge_invocations       = 5
skip_perfect_score          = false
seed                        = 7
GEPA per-example cache      = false
adapter artifact cache      = true
```

Cache per-example cua GEPA bi tat vi train va validation loader co the dung integer ID
trung nhau. Cache artifact cua adapter moi la nguon cache chinh xac, vi khoa cua no chua
prompt, split, target set, source hash, config va replicate.

`max_metric_calls` la budget logic cua GEPA. No khong bang truc tiep so subprocess
CoverUp, vi mot metric request co the gay exact-batch cache miss hoac chi doc lai cache.

## 9. Final decision va nhanh skip moi

Sau search, pipeline luu:

```text
optimized_program.json
prompts/gepa_proposed.json
```

Sau do so sanh digest noi dung:

```text
best candidate == baseline
|
+-- YES
|   +-- KHONG generate test split final
|   +-- KHONG chay baseline/proposal tren test holdout
|   +-- save baseline -> prompts/gepa_optimized.json
|   +-- final_validation.json:
|       final_evaluation_skipped = true
|       promoted = false
|       scores/aggregates = null
|       run_ids/workspaces/results = []
|
+-- NO
    +-- evaluate generated baseline on final split
    +-- validate every reference denominator
    +-- evaluate proposal using same targets and reference units
    +-- promote only if proposal aggregate > baseline aggregate
        +-- strictly greater: production = proposal
        +-- equal or lower: production = baseline
```

Khong the bo final test khi candidate khac baseline: “khong cai thien” chi duoc biet sau
khi baseline va proposal da duoc cham tren locked holdout. Nhanh skip chi ap dung khi GEPA
da chon dung baseline, nghia la khong co prompt moi can so sanh.

## 10. Artifact layout

```text
<artifacts>/
|
+-- candidates/
|   +-- <prompt-digest>.json
|   +-- evaluations/
|       +-- <prompt-digest>/
|           +-- <evaluation-digest>/
|               +-- <split>/
|                   +-- batch.json
|                   +-- batch_r1.json
|                   +-- baseline_batch.json
|
+-- generated_tests/
|   +-- train/<candidate-batch-id>/
|   +-- validation/<candidate-batch-id>/
|   +-- test/<candidate-batch-id>/
|
+-- runs/<candidate-batch-id>/<split>/<run-id>/
|   +-- prompt.json
|   +-- target_spec.json
|   +-- coverup.log
|   +-- coverup.stdout.log
|   +-- attempt_trace.jsonl
|   +-- coverage_after.json
|   +-- coverage_after.data
|   +-- record.json
|
+-- gepa_direct_logs/<optimization-run-digest>/
+-- optimized_program.json
+-- prompts/gepa_proposed.json
+-- prompts/gepa_optimized.json
+-- final_validation.json
```

## 11. Dataset hien tai va snapshot run cu

Dataset duoc tao tu `src/coverage.json` hien tai:

```text
Train      : 50 targets
Validation : 30 targets
Test       : 30 targets
Total      : 110 targets
```

Coverage report chi co 99 function co branch. Bo chon uu tien 99 target nay, sau do
bo sung 11 function khong co branch nhung co nhieu statement nhat. Vendored code va
function nam ngoai package `isort/` bi loai.

Run trong `eval/prompt_optimization_v2` cho thay:

```text
Dataset                  : train 25, validation 20, test 20
Physical target runs     : 165
Unique test workspaces   : 165
Generated candidates     : 4 candidates moi + baseline
Best GEPA candidate      : baseline (best_index = 0)
Train aggregate baseline : 0.784834
Best candidate moi       : 0.768203
Final test gain          : 0.0
Promotion                : false
```

Day la artifact cu voi dataset 25/20/20. Run moi se dung dataset 50/30/30,
reflection minibatch 5, causal selection `initial/error`, va neu `best_index=0` thi dung
ngay sau GEPA search ma khong tao run test.
