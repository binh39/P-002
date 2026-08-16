#!/usr/bin/env bash
# Low-cost isort GEPA pilot. This script searches and reranks on validation only;
# it never opens the locked test split.
#
# Usage (Git Bash):
#   ./binh/opt_isort.sh          # 32 targets, budget 40
#   ./binh/opt_isort.sh 24 115 30
#   ./binh/opt_isort.sh 40 115 50
set -euo pipefail
cd "$(dirname "$0")/.."

FUNCTIONS="${1:-32}"
SEED="${2:-115}"
METRIC_BUDGET="${3:-40}"
RERANK_TOP_K="${RERANK_TOP_K:-3}"
RERANK_REPLICATES="${RERANK_REPLICATES:-2}"

if (( FUNCTIONS < 24 || FUNCTIONS > 40 )); then
  echo "FUNCTIONS must be between 24 and 40 for the pilot" >&2
  exit 2
fi
if (( METRIC_BUDGET < 1 )); then
  echo "METRIC_BUDGET must be positive" >&2
  exit 2
fi

export COVERUP_MODEL="${COVERUP_MODEL:-vertex_ai/gemini-3.5-flash-lite}"
export OPTIMIZE_MODEL="${OPTIMIZE_MODEL:-vertex_ai/gemini-3.5-flash-lite}"

RUN_ID="$(date +%Y%m%d-%H%M%S)"
ARTIFACTS="${ARTIFACTS_DIR:-eval/prompt_optimization_isort_pilot_${RUN_ID}}"
DATASET="${ARTIFACTS}/isort_dataset.jsonl"
PROGRAM="${ARTIFACTS}/optimized_program.json"
RERANK_REPORT="${ARTIFACTS}/candidate_rerank.json"
RERANKED_PROMPT="${ARTIFACTS}/prompts/gepa_reranked.json"
PYTHON=".venv/Scripts/python.exe"

if [[ -d "${ARTIFACTS}" ]] && [[ -n "$(find "${ARTIFACTS}" -mindepth 1 -print -quit)" ]]; then
  echo "Artifacts directory already contains files: ${ARTIFACTS}" >&2
  echo "Choose a new ARTIFACTS_DIR or omit it to generate a timestamped directory." >&2
  exit 2
fi
mkdir -p "${ARTIFACTS}/prompts"

echo "==> Artifacts: ${ARTIFACTS}"
echo "==> Building a difficulty-stratified ${FUNCTIONS}-target dataset"
"${PYTHON}" scripts/build_my_isort_dataset.py \
  --functions "${FUNCTIONS}" --seed "${SEED}" --stratum-size 5 \
  --output "${DATASET}"

echo "==> GEPA search-only on train/validation (budget=${METRIC_BUDGET})"
"${PYTHON}" -m src.optimization.cli \
  --sample-repos-dir src/sample_repo \
  --artifacts-dir "${ARTIFACTS}" \
  --max-attempts 3 --repeat-tests 2 --max-concurrency 1 \
  --target-context --no-repository-test-context --no-failure-context \
  --salvage-failing-tests --salvage-max-prunes 8 \
  optimize \
  --dataset "${DATASET}" \
  --prompt cloud/inputs/gpt_v2_baseline.json \
  --search-only --program-output "${PROGRAM}" \
  --evaluation-replicates 1 \
  --max-metric-calls "${METRIC_BUDGET}"

echo "==> Reranking baseline + finalists on validation only"
"${PYTHON}" -m src.optimization.cli \
  --sample-repos-dir src/sample_repo \
  --artifacts-dir "${ARTIFACTS}" \
  --max-attempts 3 --repeat-tests 2 --max-concurrency 1 \
  --target-context --no-repository-test-context --no-failure-context \
  --salvage-failing-tests --salvage-max-prunes 8 \
  rerank \
  --dataset "${DATASET}" \
  --prompt cloud/inputs/gpt_v2_baseline.json \
  --optimized-program "${PROGRAM}" \
  --top-k "${RERANK_TOP_K}" --replicates "${RERANK_REPLICATES}" \
  --report-output "${RERANK_REPORT}" \
  --output-prompt "${RERANKED_PROMPT}"

echo "==> Pilot complete; locked test split was NOT opened."
echo "Artifacts: ${ARTIFACTS}"
echo "Review: ${RERANK_REPORT}"
echo "Candidate: ${RERANKED_PROMPT}"
