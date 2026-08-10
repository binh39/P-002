param(
    [string]$ApiBase = "https://vinaip002.web.app/api/v1",
    [ValidateSet("isort", "mimesis", "mlxtend", "typesystem")][string]$Sample = "isort",
    [switch]$FullPipeline,
    [ValidateSet("approve", "reject")][string]$ReviewDecision = "approve",
    [int]$PollSeconds = 10,
    [int]$OptimizationTimeoutMinutes = 1440,
    [int]$ComparisonTimeoutMinutes = 60,
    [string]$ResultDirectory = (Join-Path $PSScriptRoot "..\.smoke-results")
)

$ErrorActionPreference = "Stop"
if ($PollSeconds -lt 1) { throw "PollSeconds must be at least 1" }
$ResultDirectory = [System.IO.Path]::GetFullPath($ResultDirectory)
$Token = (Read-Host "Paste Firebase token after 'Bearer ' (visible input)").Trim().Trim('"').Trim("'")
if ($Token.StartsWith("Bearer ", [System.StringComparison]::OrdinalIgnoreCase)) {
    $Token = $Token.Substring(7).Trim()
}
$Token = ($Token -replace "\s", "") -replace "[\x00-\x1F\x7F]", ""
if (($Token.Split(".").Count) -ne 3) { throw "A Firebase ID token JWT is required" }

$Headers = @{ Authorization = "Bearer $Token" }
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ResultPath = Join-Path $ResultDirectory "production-smoke-$Timestamp.json"

function Invoke-PromptOptJson {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [ValidateSet("GET", "POST")][string]$Method = "GET",
        [object]$Body = $null
    )
    $Parameters = @{ Uri = $Uri; Method = $Method; Headers = $Headers }
    if ($null -ne $Body) {
        $Parameters.ContentType = "application/json"
        $Parameters.Body = $Body | ConvertTo-Json -Depth 20
    }
    Invoke-RestMethod @Parameters
}

function Wait-PromptOptRun {
    param(
        [string]$Uri,
        [string[]]$ActiveStatuses,
        [int]$TimeoutMinutes,
        [string]$Label,
        $InitialRun
    )
    $Run = $InitialRun
    $Deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    while ($Run.status -in $ActiveStatuses) {
        if ((Get-Date) -gt $Deadline) { throw "$Label timed out; run_id=$($Run.id)" }
        Start-Sleep -Seconds $PollSeconds
        $Run = Invoke-PromptOptJson -Uri $Uri
        Write-Host "  $(Get-Date -Format T) status=$($Run.status)"
    }
    $Run
}

Write-Host "[1/5] Checking production API..."
$Health = Invoke-RestMethod "$ApiBase/health"
if ($Health.status -ne "ok") { throw "Production API health check failed" }

Write-Host "[2/5] Verifying bundled sample..."
$ProjectId = "sample:$Sample"
$Samples = Invoke-PromptOptJson -Uri "$ApiBase/projects/samples"
if ($ProjectId -notin @($Samples.items | Select-Object -ExpandProperty id)) {
    throw "Bundled sample is unavailable: $ProjectId"
}

Write-Host "[3/5] Creating experiment..."
$Experiment = Invoke-PromptOptJson -Uri "$ApiBase/experiments" -Method POST -Body @{
    project_ids = @($ProjectId)
    name = "$Sample GEPA smoke $Timestamp"
    sampling_method = "random"
    max_targets = 3
    random_seed = 42
}
if (-not $Experiment.optimization_eligible) { throw "Sample experiment is not optimization eligible" }

Write-Host "[4/5] Queueing GEPA (baseline prompt is candidate zero)..."
$OptimizationRun = Invoke-PromptOptJson -Uri "$ApiBase/experiments/$($Experiment.id)/optimize" -Method POST
$OptimizationRun = Wait-PromptOptRun `
    -Uri "$ApiBase/experiments/optimization-runs/$($OptimizationRun.id)" `
    -ActiveStatuses @("optimization_queued", "optimizing", "candidate_evaluating") `
    -TimeoutMinutes $OptimizationTimeoutMinutes -Label "Optimization" -InitialRun $OptimizationRun

$ComparisonRun = $null
$PromptVersion = $null
if ($FullPipeline -and $OptimizationRun.status -eq "optimization_succeeded") {
    Write-Host "[5/5] Running paired locked-test comparison..."
    $ComparisonRun = Invoke-PromptOptJson -Uri "$ApiBase/experiments/$($Experiment.id)/compare" -Method POST
    $ComparisonRun = Wait-PromptOptRun `
        -Uri "$ApiBase/experiments/comparison-runs/$($ComparisonRun.id)" `
        -ActiveStatuses @("comparison_queued", "comparing") `
        -TimeoutMinutes $ComparisonTimeoutMinutes -Label "Comparison" -InitialRun $ComparisonRun
    if ($ComparisonRun.status -eq "in_review" -and $ComparisonRun.prompt_version_id) {
        $PromptVersion = Invoke-PromptOptJson `
            -Uri "$ApiBase/prompt-versions/$($ComparisonRun.prompt_version_id)/$ReviewDecision" `
            -Method POST -Body @{ comment = "Automated production smoke $Timestamp" }
    }
} else {
    Write-Host "[5/5] Comparison skipped (use -FullPipeline to enable)."
}

New-Item -ItemType Directory -Force -Path $ResultDirectory | Out-Null
$Output = [ordered]@{
    schema_version = 2
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    sample = $ProjectId
    experiment_status = $Experiment.status
    optimization_status = $OptimizationRun.status
    comparison_status = if ($ComparisonRun) { $ComparisonRun.status } else { $null }
    review_status = if ($PromptVersion) { $PromptVersion.status } else { $null }
}
$Output | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $ResultPath -Encoding UTF8
$Output | ConvertTo-Json -Depth 10

if ($OptimizationRun.status -ne "optimization_succeeded") { exit 1 }
if ($FullPipeline -and $ComparisonRun.status -notin @("comparison_succeeded", "in_review")) { exit 1 }
