# v-final locked held-out evaluation

This directory stores the comparison required by
`plan/test-gen-prompt-optimization-guide.md`.

The original files in `results/` use held-out digest `7335a18155d636ad` and are
preserved as an audit artifact. They are not valid for the final comparison
because the early prompt contract did not provide the importable module path,
which caused generated tests to use placeholder imports.

The authoritative corrected run is in `corrected/`:

- Dataset: `corrected/isort_symbols.jsonl`
- Held-out digest: `9e351f2c9da37d43`
- Locked results: `corrected/results/`
- Final report: `corrected/report.md`
- Evaluation ledger: `corrected/ledger.json`
- Protocol details: `corrected/README.md`

All four LLM modes and the CoverUp reference were measured once on the same ten
fresh held-out symbols through the common Docker harness. BootstrapFewShot
finished before GEPA, and GEPA stopped after iteration 15.
