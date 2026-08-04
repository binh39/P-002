# Test-generation prompt optimization - held-out evaluation

All methods were measured once on the same locked held-out functions through the common Docker harness.

## Methodology

- Coverage and mutation are scoped to the focal function. Mutation testing uses a generated mutmut patch so unrelated symbols do not affect the score.
- A mutation timeout or mutation-infrastructure failure is assigned a conservative mutation score of 0 while valid build, test, and coverage measurements are retained.
- Cost and latency include optimizer compilation plus held-out test generation. CoverUp cost/latency include its external generation run and replay through the same harness.

## Aggregate results

| Baseline | Build rate | Pass rate | Statement coverage | Branch coverage | Mutation score | Cost/run | Latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| zero_shot | 70.0% | 26.3% | 43.3% | 33.7% | 4.0% | $0.0030 | 199.30s |
| static_symprompt | 80.0% | 28.2% | 57.0% | 49.7% | 4.5% | $0.0041 | 387.70s |
| coverup | 100.0% | 100.0% | 32.8% | 33.9% | 17.4% | $0.0075 | 728.10s |
| bootstrap_few_shot | 100.0% | 27.3% | 68.5% | 58.7% | 0.0% | $0.0554 | 1526.64s |
| gepa | 90.0% | 32.0% | 60.4% | 50.5% | 20.3% | $0.4100 | 2271.11s |

## Four LLM modes

The primary comparison contains zero-shot, static SymPrompt, BootstrapFewShot, and GEPA. CoverUp is retained separately as the required external-tool reference.

| Rank | LLM mode | Mutation score | Branch coverage | Pass rate |
|---:|---|---:|---:|---:|
| 1 | gepa | 20.3% | 50.5% | 32.0% |
| 2 | static_symprompt | 4.5% | 49.7% | 28.2% |
| 3 | zero_shot | 4.0% | 33.7% | 26.3% |
| 4 | bootstrap_few_shot | 0.0% | 58.7% | 27.3% |

## Paired analysis

- GEPA vs `zero_shot` mutation delta: +16.3% (95% paired-bootstrap CI +0.0% to +38.3%); 3 improved, 0 regressed, 7 tied.
- GEPA vs `static_symprompt` mutation delta: +15.8% (95% paired-bootstrap CI +0.0% to +38.3%); 2 improved, 0 regressed, 8 tied.
- GEPA vs `bootstrap_few_shot` mutation delta: +20.3% (95% paired-bootstrap CI +0.0% to +42.5%); 3 improved, 0 regressed, 7 tied.
- GEPA vs `coverup` mutation delta: +2.9% (95% paired-bootstrap CI -27.8% to +32.9%); 3 improved, 2 regressed, 5 tied.

## Qualitative examples

GEPA is compared below with the strongest non-GEPA LLM mode (`static_symprompt`). The 3-5 examples with the largest measured per-function changes are shown; no LLM-as-judge is used.

- `isort/_vendored/tomli/_parser.py::Flags.is_` improved: mutation +91.7%, branch +0.0%, pass rate +42.9%.
- `isort/deprecated/finders.py::KnownPatternFinder.__init__` improved: mutation +66.7%, branch +100.0%, pass rate +100.0%.
- `isort/_vendored/tomli/_parser.py::parse_key_part` regressed: mutation +0.0%, branch -50.0%, pass rate -20.0%.
- `isort/format.py::format_simplified` regressed: mutation +0.0%, branch -25.0%, pass rate -71.4%.
- `isort/_vendored/tomli/_re.py::match_to_datetime` regressed: mutation +0.0%, branch -16.7%, pass rate +20.0%.

## Scope and next steps

Memory/warm-start, full multi-role authorization, and real-time cost alerts are intentionally post-v-final extensions.
