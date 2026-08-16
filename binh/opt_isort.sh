#!/usr/bin/env bash
# Optimize the isort CoverUp prompt with GEPA and report baseline vs optimized
# coverage on the validation and locked test splits.
#
# Usage:
#   ./binh/opt_isort.sh                # default 160 most-branch-heavy functions
#   ./binh/opt_isort.sh 100            # 100 most-branch-heavy functions
#
# The split is seeded (default 115, 20/40/40 train/validation/test) so the test
# split is deterministic.  Both the CoverUp generator and the GEPA optimizer use
# gemini-3.5-flash-lite.
set -euo pipefail
cd "$(dirname "$0")/.."

# ---- Fill in the number of most-branch-heavy isort functions to run ---------
FUNCTIONS="${1:-160}"
SEED="${2:-115}"
EVAL_REPLICATES="${EVAL_REPLICATES:-3}"   # replicate-aware coverage comparison
RERANK_TOP_K="${RERANK_TOP_K:-3}"          # re-validate top-K finalists (+ baseline)

export COVERUP_MODEL="${COVERUP_MODEL:-vertex_ai/gemini-3.5-flash-lite}"
export OPTIMIZE_MODEL="${OPTIMIZE_MODEL:-vertex_ai/gemini-3.5-flash-lite}"

DATASET="binh/isort_my_dataset.jsonl"
ARTIFACTS="eval/prompt_optimization_opt_isort"

echo "==> Building isort dataset: ${FUNCTIONS} most-branch-heavy, seed ${SEED}"
.venv/Scripts/python.exe scripts/build_my_isort_dataset.py \
  --functions "${FUNCTIONS}" --seed "${SEED}" --output "${DATASET}"

echo "==> Running GEPA optimize (coverup/optimize = ${COVERUP_MODEL} / ${OPTIMIZE_MODEL})"
.venv/Scripts/python.exe -m src.optimization.cli \
  --sample-repos-dir src/sample_repo \
  --artifacts-dir "${ARTIFACTS}" \
  --max-attempts 3 --repeat-tests 5 --max-concurrency 1 \
  --no-target-context --failure-context --failure-context-max-chars 4000 \
  optimize \
  --dataset "${DATASET}" \
  --prompt cloud/inputs/gpt_v2_baseline.json \
  --evaluation-replicates "${EVAL_REPLICATES}" \
  --rerank-top-k "${RERANK_TOP_K}" \
  --report-splits validation,test

echo "==> Done. Coverage report was printed above for validation and test."
