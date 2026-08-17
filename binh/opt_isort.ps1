[CmdletBinding()]
param(
    [ValidateRange(24, 200)]
    [int]$Functions = 32,

    [ValidateRange(0, [int]::MaxValue)]
    [int]$Seed = 115,

    [ValidateRange(1, [int]::MaxValue)]
    [int]$MetricBudget = 100,

    [ValidateRange(1, [int]::MaxValue)]
    [int]$ReflectionMinibatchSize = 6,

    [ValidateRange(1, [int]::MaxValue)]
    [int]$RerankTopK = 3,

    [ValidateRange(2, [int]::MaxValue)]
    [int]$RerankReplicates = 2,

    [ValidateRange(1, [int]::MaxValue)]
    [int]$MaxPromptChars = 3000,

    [ValidateRange(0.0, 1.0)]
    [double]$MaxTargetRegression = 0.30,

    [ValidateRange(0.0, [double]::MaxValue)]
    [double]$LengthPenaltyPer1K = 0.002,

    [string]$ArtifactsDir,

    [switch]$Resume
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
$MaxTargetRegressionArg = $MaxTargetRegression.ToString(
    [System.Globalization.CultureInfo]::InvariantCulture
)
$LengthPenaltyPer1KArg = $LengthPenaltyPer1K.ToString(
    [System.Globalization.CultureInfo]::InvariantCulture
)
if ((Test-Path -LiteralPath $ArtifactsDir) -and
    (Get-ChildItem -LiteralPath $ArtifactsDir -Force | Select-Object -First 1) -and
    -not $Resume) {
    throw "Artifacts directory already contains files: $ArtifactsDir"
}
New-Item -ItemType Directory -Force -Path (Join-Path $ArtifactsDir "prompts") | Out-Null

function Move-IncompletePromptOptWorkspaces {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RunArtifactsDir
    )

    $GeneratedRoot = Join-Path $RunArtifactsDir "generated_tests"
    if (-not (Test-Path -LiteralPath $GeneratedRoot)) {
        return
    }
    $QuarantineRoot = Join-Path $RunArtifactsDir (
        "interrupted_workspaces\" + (Get-Date -Format "yyyyMMdd-HHmmss")
    )
    foreach ($SplitDir in Get-ChildItem -LiteralPath $GeneratedRoot -Directory) {
        foreach ($Workspace in Get-ChildItem -LiteralPath $SplitDir.FullName -Directory) {
            if ($Workspace.Name -notmatch '^tests_(candidate|base_line)_([0-9a-f]+)-([0-9a-f]+)(?:-r([0-9]+))?$') {
                continue
            }
            $WorkspaceKind = $Matches[1]
            $PromptDigest = $Matches[2]
            $EvaluationDigest = $Matches[3]
            $Replicate = if ($Matches[4]) { [int]$Matches[4] } else { 0 }
            $CacheStem = if ($WorkspaceKind -eq "base_line") { "baseline_batch" } else { "batch" }
            $CacheName = if ($Replicate -eq 0) {
                "$CacheStem.json"
            }
            else {
                "${CacheStem}_r$Replicate.json"
            }
            $CachePath = Join-Path $RunArtifactsDir (
                "candidates\evaluations\$PromptDigest\$EvaluationDigest\" +
                "$($SplitDir.Name)\$CacheName"
            )
            $HasFiles = Get-ChildItem -LiteralPath $Workspace.FullName -Force |
                Select-Object -First 1
            if ((-not (Test-Path -LiteralPath $CachePath)) -and $HasFiles) {
                $DestinationDir = Join-Path $QuarantineRoot $SplitDir.Name
                New-Item -ItemType Directory -Force -Path $DestinationDir | Out-Null
                Write-Host "==> Quarantining interrupted workspace: $($Workspace.FullName)"
                Move-Item -LiteralPath $Workspace.FullName -Destination $DestinationDir
            }
        }
    }
}

function Invoke-PromptOptPython {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    # Python/tqdm writes progress bars to stderr. When the outer command uses
    # `2>&1 | Tee-Object`, PowerShell wraps those normal progress writes in a
    # NativeCommandError. Do not treat stderr itself as a terminating error;
    # the native exit code remains authoritative.
    $PreviousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $Python @Arguments 2>&1 | ForEach-Object { $_.ToString() }
        $NativeExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $PreviousPreference
    }
    if ($NativeExitCode -ne 0) {
        throw "$FailureMessage with exit code $NativeExitCode"
    }
}

Write-Host "==> Artifacts: $ArtifactsDir"
if ($Resume) {
    Write-Host "==> Resume enabled; compatible cached evaluations will be reused"
    Move-IncompletePromptOptWorkspaces -RunArtifactsDir $ArtifactsDir
}
Write-Host "==> Building a difficulty-stratified $Functions-target dataset"
Invoke-PromptOptPython -FailureMessage "Dataset build failed" -Arguments @(
    "scripts/build_my_isort_dataset.py",
    "--functions", "$Functions",
    "--seed", "$Seed",
    "--stratum-size", "4",
    "--output", $Dataset
)

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
Invoke-PromptOptPython -FailureMessage "GEPA search failed" -Arguments @(
    $CommonArgs
    "optimize",
    "--dataset", $Dataset,
    "--prompt", "cloud/inputs/gpt_v2_baseline.json",
    "--search-only", "--program-output", $Program,
    "--evaluation-replicates", "1",
    "--reflection-minibatch-size", "$ReflectionMinibatchSize",
    "--proposal-max-prompt-chars", "$MaxPromptChars",
    "--max-metric-calls", "$MetricBudget"
)

Write-Host "==> Reranking baseline + finalists on validation only"
Invoke-PromptOptPython -FailureMessage "Candidate rerank failed" -Arguments @(
    $CommonArgs
    "rerank",
    "--dataset", $Dataset,
    "--prompt", "cloud/inputs/gpt_v2_baseline.json",
    "--optimized-program", $Program,
    "--top-k", "$RerankTopK",
    "--replicates", "$RerankReplicates",
    "--length-penalty-per-1k", $LengthPenaltyPer1KArg,
    "--max-prompt-chars", "$MaxPromptChars",
    "--max-target-regression", $MaxTargetRegressionArg,
    "--report-output", $RerankReport,
    "--output-prompt", $RerankedPrompt
)

Write-Host "==> Pilot complete; locked test split was NOT opened."
Write-Host "Artifacts: $ArtifactsDir"
Write-Host "Review: $RerankReport"
Write-Host "Candidate: $RerankedPrompt"
