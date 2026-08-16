#!/usr/bin/env bash
set -u
cd /d/VinAI/P-002
.venv/Scripts/python.exe -m src.optimization.cli \
  --sample-repos-dir src/sample_repo \
  --artifacts-dir eval/prompt_optimization_remeasure_baseline \
  --max-attempts 5 --repeat-tests 2 --max-concurrency 1 \
  --target-context --failure-context --failure-context-max-chars 4000 \
  --salvage-failing-tests --salvage-max-prunes 8 \
  evaluate \
  --dataset binh/e70_failure_stratified_32.jsonl \
  --prompt cloud/inputs/gpt_v2_baseline.json \
  --split validation --evaluation-replicates 2
