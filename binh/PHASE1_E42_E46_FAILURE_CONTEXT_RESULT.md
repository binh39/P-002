# P1 — E42/E46 failure-triggered context result

## Outcome

Bounded failure-triggered retrieval is implemented and works mechanically, but it did **not** improve the frozen
eight-target E70 validation aggregate. The result is a tie, so this policy is not promoted and the E70 test holdout
remains locked and unevaluated.

The original frozen protocols call the experiment E42/E44. The delivered behavior maps more precisely to:

- E42: retrieve the enclosing constructor, direct callee contract, and relevant usage examples.
- E46: route retrieval by the observed failure family and add it only to repair prompts.
- E44 is only partial: import/export evidence exists, but a full project setup manifest is still pending.

## Guardrails

- Model: `vertex_ai/gemini-3.5-flash-lite` only.
- Prompt: frozen baseline `d8123dc403839c22`.
- Initial prompt: exact target contract enabled; repository test context disabled.
- Repair prompt: context enabled only after `test_error`, capped at 4,000 characters.
- Evaluation: one replicate, three attempts, two repeat-test executions.
- E70 test split: never loaded or evaluated.

Implementation and the first protocol were frozen in commit `e0ff52a`; exact assertion evidence and the SFS R2
protocol were frozen in `ffca5c9`, both before their corresponding model calls.

## Results

| Evaluation | Baseline | Treatment | Delta | Interpretation |
|---|---:|---:|---:|---|
| Train smoke — `Config.__init__` | 0.00% | 82.44% | +82.44 pp | Strong local repair signal, one target only |
| E70 validation — 8 targets | 8.04% | 8.04% | 0.00 pp | Tie; no promotion |
| Validation R2 — `SequentialFeatureSelector.fit` | 0.00% | 0.00% | 0.00 pp | Repair chain progressed but never produced a fully passing module |

The train smoke covered 119/135 target statements and 72/90 target branches. Its trace contains two repair prompts
with `[FAILURE-TRIGGERED CONTEXT]` and terminates in `coverage_gain_saved`, proving the gain was not a stale cache.

On validation, all seven already-easy targets remained at full target coverage. The only zero target, SFS, stayed at
zero, so the micro aggregate remained exactly equal to baseline. This is directional evidence from one replicate,
not a stable population estimate.

## What the traces show

For `Config.__init__`, the policy repaired two assertion/behavior errors and saved a valid suite. For SFS R1, it
repaired the original missing `._estimator_type` setup, then exhausted the budget on an exact regex/message mismatch.
R2 exposed the exact runtime message and regex-safe alternatives; the chain then advanced through:

1. missing estimator protocol;
2. invalid fixed-feature group setup;
3. `n_splits=5` exceeding the samples per class.

This is useful causal evidence: retrieval can fix the current error, but a large generated module exposes another
independent failing test on the next run. With three attempts, only two repair generations are available.

## Bottleneck and next experiment

The current acceptance unit is the entire generated test module. A module may contain many useful passing tests, but
one remaining failure makes the target score zero and discards all of their potential coverage. Increasing attempts
would be costly and would only postpone this all-or-nothing failure mode.

The next high-value experiment should isolate and salvage generated test functions:

1. split a generated module into executable test units while preserving imports, fixtures, classes, and decorators;
2. run units independently in isolated workspaces;
3. retain passing units and their incremental coverage;
4. send only the failing unit plus its traceback to the repair loop;
5. rebuild and repeat-check the retained suite before scoring.

Do not run E70 test until this candidate policy has shown a strict, repeated validation gain and has been frozen in a
separate commit.
