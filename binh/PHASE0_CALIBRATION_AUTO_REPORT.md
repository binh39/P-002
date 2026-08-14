# Phase 0 calibration report

- Replicates: 2
- Targets: 16
- Mean aggregate score: 76.55%
- Aggregate score range: 8.87%

## Replicates

| Replicate | Score | Statement | Branch | Elapsed |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 80.98% | 79.58% | 81.58% | 161.5s |
| 1 | 72.11% | 76.12% | 70.39% | 169.4s |

## Paired target deltas

| Project | Target | Scores | Last - first |
| --- | --- | --- | ---: |
| isort | `isort/deprecated/finders.py::KnownPatternFinder.__init__` | 0.00%, 0.00% | 0.00% |
| isort | `isort/main.py::sort_imports` | 0.00%, 100.00% | 100.00% |
| isort | `isort/wrap.py::line` | 89.13%, 0.00% | -89.13% |
| isort | `isort/wrap_modes.py::_wrap_mode` | 100.00%, 100.00% | 0.00% |
| mimesis | `mimesis/providers/internet.py::Internet.cloud_region` | 100.00%, 100.00% | 0.00% |
| mimesis | `mimesis/providers/internet.py::Internet.url` | 100.00%, 100.00% | 0.00% |
| mimesis | `mimesis/providers/person.py::Person._validate_birth_year_params` | 88.33%, 88.33% | 0.00% |
| mimesis | `mimesis/providers/person.py::Person.username` | 100.00%, 100.00% | 0.00% |
| mlxtend | `mlxtend/classifier/ensemble_vote.py::EnsembleVoteClassifier.predict` | 100.00%, 100.00% | 0.00% |
| mlxtend | `mlxtend/data/wine.py::wine_data` | 100.00%, 100.00% | 0.00% |
| mlxtend | `mlxtend/frequent_patterns/apriori.py::apriori` | 92.08%, 97.67% | 5.59% |
| mlxtend | `mlxtend/frequent_patterns/apriori.py::generate_new_combinations_low_memory` | 100.00%, 100.00% | 0.00% |
| typesystem | `typesystem/fields.py::Array.validate` | 98.06%, 98.06% | 0.00% |
| typesystem | `typesystem/fields.py::Boolean.validate` | 0.00%, 0.00% | 0.00% |
| typesystem | `typesystem/json_schema.py::type_from_json_schema` | 100.00%, 100.00% | 0.00% |
| typesystem | `typesystem/tokenize/tokens.py::Token._get_position` | 100.00%, 100.00% | 0.00% |

## Failure taxonomy

- `coverage_gain_saved`: 26
- `max_attempts_exhausted`: 2
- `test_error`: 23

## Coverage-unit oracle

**Preliminary union of covered lines/branches; not combined-suite proof.**

- Score: 86.75%
- Statement coverage: 89.62%
- Branch coverage: 85.53%
