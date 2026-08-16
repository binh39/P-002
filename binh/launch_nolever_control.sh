#!/usr/bin/env bash
set -u
cd /d/VinAI/P-002
# STEP 1 (2026-08-16): no-lever 8-target control.
# --failure-context is the ONLY gate for all lever hints (clone-pitfall,
# SFS branch, private-hook live inside build_failure_context). Dropping it
# yields a clean no-lever run. All else identical to launch_fullval_ad.sh.
# --evaluation-replicates 6 -> 6 independent aggregate scores for CI.
.venv/Scripts/python.exe -m src.optimization.cli \
  --sample-repos-dir src/sample_repo \
  --artifacts-dir eval/prompt_optimization_nolever \
  --max-attempts 5 --repeat-tests 2 --max-concurrency 1 \
  --target-context \
  --salvage-failing-tests --salvage-max-prunes 8 \
  evaluate \
  --dataset binh/e70_failure_stratified_32.jsonl \
  --prompt cloud/inputs/gpt_v2_baseline.json \
  --split validation --evaluation-replicates 6
