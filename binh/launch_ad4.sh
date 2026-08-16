#!/usr/bin/env bash
set -u
cd /d/VinAI/P-002
.venv/Scripts/python.exe -m src.optimization.cli \
  --sample-repos-dir src/sample_repo \
  --artifacts-dir eval/prompt_optimization_leverAD4 \
  --max-attempts 5 --repeat-tests 2 --max-concurrency 1 \
  --target-context --failure-context --failure-context-max-chars 4000 \
  --salvage-failing-tests --salvage-max-prunes 8 \
  evaluate \
  --dataset binh/e70_e42_e44_validation_sfs_probe.jsonl \
  --prompt cloud/inputs/gpt_v2_baseline.json \
  --split validation --evaluation-replicates 3
