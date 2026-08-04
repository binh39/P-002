# Corrected v-final evaluation

This directory is the authoritative v-final evaluation for
`plan/test-gen-prompt-optimization-guide.md`.

## Protocol

- Dataset: deterministic 20 train / 10 validation / 10 fresh held-out symbols.
- Locked held-out digest: `9e351f2c9da37d43`.
- Every method is evaluated through the same Docker pytest, coverage.py, and
  focal-symbol mutation harness.
- The four primary LLM modes are zero-shot, static SymPrompt,
  BootstrapFewShot, and GEPA.
- CoverUp is retained as the required external-tool reference.
- Bootstrap completed before GEPA started.
- GEPA was stopped after user-visible iteration 15. Its final checkpoint has
  internal `i=14`, which is GEPA's zero-based representation of 15 completed
  search iterations.
- Cost and latency include compilation/generation and held-out evaluation.

The first GEPA attempt exposed an off-by-one callback interpretation and reached
iteration 16. It is excluded from the ledger and report and preserved under
`invalid_runs/gepa_iteration16/` for auditability.

Generate the report with:

```powershell
python -m evaluation.cli report eval/v_final/corrected/results `
  --output eval/v_final/corrected/report.md
```

Do not delete or reuse `ledger.json` with another held-out dataset.
