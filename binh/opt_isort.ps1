[CmdletBinding()]
param(
    [ValidateRange(24, 40)]
    [int]$Functions = 32,

    [ValidateRange(0, [int]::MaxValue)]
    [int]$Seed = 115,

    [ValidateRange(1, [int]::MaxValue)]
    [int]$MetricBudget = 40,

    [ValidateRange(1, [int]::MaxValue)]
    [int]$RerankTopK = 3,

    [ValidateRange(2, [int]::MaxValue)]
    [int]$RerankReplicates = 2,

    [string]$ArtifactsDir
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $RepoRoot

if (-not $env:COVERUP_MODEL) {
    $env:COVERUP_MODEL = "vertex_ai/gemini-3.5-flash-lite"
}
if (-not $env:OPTIMIZE_MODEL) {
    $env:OPTIMIZE_MODEL = "vertex_ai/gemini-3.5-flash-lite"
}

if (-not $ArtifactsDir) {
    $RunId = Get-Date -Format "yyyyMMdd-HHmmss"
    $ArtifactsDir = "eval/prompt_optimization_isort_pilot_$RunId"
}

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Dataset = Join-Path $ArtifactsDir "isort_dataset.jsonl"
$Program = Join-Path $ArtifactsDir "optimized_program.json"
$RerankReport = Join-Path $ArtifactsDir "candidate_rerank.json"
$RerankedPrompt = Join-Path $ArtifactsDir "prompts\gepa_reranked.json"
if ((Test-Path -LiteralPath $ArtifactsDir) -and
    (Get-ChildItem -LiteralPath $ArtifactsDir -Force | Select-Object -First 1)) {
    throw "Artifacts directory already contains files: $ArtifactsDir"
}
New-Item -ItemType Directory -Force -Path (Join-Path $ArtifactsDir "prompts") | Out-Null

Write-Host "==> Artifacts: $ArtifactsDir"
Write-Host "==> Building a difficulty-stratified $Functions-target dataset"
& $Python scripts/build_my_isort_dataset.py `
    --functions $Functions --seed $Seed --stratum-size 5 `
    --output $Dataset
if ($LASTEXITCODE -ne 0) { throw "Dataset build failed with exit code $LASTEXITCODE" }

$CommonArgs = @(
    "-m", "src.optimization.cli",
    "--sample-repos-dir", "src/sample_repo",
    "--artifacts-dir", $ArtifactsDir,
    "--max-attempts", "3",
    "--repeat-tests", "2",
    "--max-concurrency", "1",
    "--target-context",
    "--no-repository-test-context",
    "--no-failure-context",
    "--salvage-failing-tests",
    "--salvage-max-prunes", "8"
)

Write-Host "==> GEPA search-only on train/validation (budget=$MetricBudget)"
& $Python @CommonArgs optimize `
    --dataset $Dataset `
    --prompt cloud/inputs/gpt_v2_baseline.json `
    --search-only --program-output $Program `
    --evaluation-replicates 1 `
    --max-metric-calls $MetricBudget
if ($LASTEXITCODE -ne 0) { throw "GEPA search failed with exit code $LASTEXITCODE" }

Write-Host "==> Reranking baseline + finalists on validation only"
& $Python @CommonArgs rerank `
    --dataset $Dataset `
    --prompt cloud/inputs/gpt_v2_baseline.json `
    --optimized-program $Program `
    --top-k $RerankTopK --replicates $RerankReplicates `
    --report-output $RerankReport `
    --output-prompt $RerankedPrompt
if ($LASTEXITCODE -ne 0) { throw "Candidate rerank failed with exit code $LASTEXITCODE" }

Write-Host "==> Pilot complete; locked test split was NOT opened."
Write-Host "Artifacts: $ArtifactsDir"
Write-Host "Review: $RerankReport"
Write-Host "Candidate: $RerankedPrompt"
