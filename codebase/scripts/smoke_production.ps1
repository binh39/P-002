param(
    [string]$ApiBase = "https://vinaip002.web.app/api/v1",
    [string]$ArchivePath = (Join-Path $PSScriptRoot "..\fixtures\isort-smoke.zip"),
    [string]$TargetFunction = "_infer_line_separator",
    [switch]$FullPipeline,
    [ValidateSet("approve", "reject")][string]$ReviewDecision = "approve",
    [int]$PollSeconds = 10,
    [int]$BaselineTimeoutMinutes = 25,
    [int]$OptimizationTimeoutMinutes = 35,
    [int]$ComparisonTimeoutMinutes = 25,
    [string]$ResultDirectory = (Join-Path $PSScriptRoot "..\.smoke-results")
)

$ErrorActionPreference = "Stop"
$ArchivePath = [System.IO.Path]::GetFullPath($ArchivePath)
$ResultDirectory = [System.IO.Path]::GetFullPath($ResultDirectory)
if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf)) {
    throw "Smoke archive was not found: $ArchivePath"
}
if ($PollSeconds -lt 1) {
    throw "PollSeconds must be at least 1"
}

$Token = Read-Host "Paste Firebase token after 'Bearer ' (visible input)"
$Token = $Token.Trim().Trim('"').Trim("'")
if ($Token.StartsWith("Bearer ", [System.StringComparison]::OrdinalIgnoreCase)) {
    $Token = $Token.Substring(7).Trim()
}
$Token = $Token -replace "\s", ""
$Token = $Token -replace "[\x00-\x1F\x7F]", ""
if (-not $Token) {
    throw "Firebase token is required"
}
if (($Token.Split(".").Count) -ne 3) {
    throw "The pasted value is not a Firebase ID token JWT. Paste only the token after 'Bearer '."
}

$Headers = @{ Authorization = "Bearer $Token" }
$ContentType = "application/zip"
$Archive = Get-Item -LiteralPath $ArchivePath
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ResultPath = Join-Path $ResultDirectory "production-smoke-$Timestamp.json"

function Invoke-PromptOptJson {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [ValidateSet("GET", "POST", "PATCH")][string]$Method = "GET",
        [object]$Body = $null
    )

    $Parameters = @{
        Uri = $Uri
        Method = $Method
        Headers = $Headers
    }
    if ($null -ne $Body) {
        $Parameters.ContentType = "application/json"
        $Parameters.Body = $Body | ConvertTo-Json -Depth 20
    }
    try {
        return Invoke-RestMethod @Parameters
    }
    catch {
        $ResponseBody = ""
        if ($_.Exception.Response -and $_.Exception.Response.GetResponseStream()) {
            $Reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $ResponseBody = $Reader.ReadToEnd()
        }
        throw "PromptOpt request failed: $Method $Uri`n$ResponseBody`n$($_.Exception.Message)"
    }
}

function Wait-PromptOptRun {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string[]]$ActiveStatuses,
        [Parameter(Mandatory = $true)][int]$TimeoutMinutes,
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)]$InitialRun
    )

    $Run = $InitialRun
    $Deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    while ($Run.status -in $ActiveStatuses) {
        if ((Get-Date) -gt $Deadline) {
            throw "$Label did not finish within $TimeoutMinutes minutes; run_id=$($Run.id)"
        }
        Start-Sleep -Seconds $PollSeconds
        $Run = Invoke-PromptOptJson -Uri $Uri
        Write-Host "  $(Get-Date -Format T) status=$($Run.status)"
    }
    return $Run
}

function Get-SanitizedRun {
    param([object]$Run)

    if ($null -eq $Run) {
        return $null
    }
    return [ordered]@{
        status = $Run.status
        created_at = $Run.created_at
        started_at = $Run.started_at
        finished_at = $Run.finished_at
        coverage_score = $Run.coverage_score
        statement_coverage = $Run.statement_coverage
        branch_coverage = $Run.branch_coverage
        baseline_validation_score = $Run.baseline_validation_score
        candidate_validation_score = $Run.candidate_validation_score
        candidate_count = $Run.candidate_count
        metric_calls = $Run.metric_calls
        absolute_gain = $Run.absolute_gain
        relative_gain = $Run.relative_gain
        promotion_eligible = $Run.promotion_eligible
        decision_reason = $Run.decision_reason
        target_count = $Run.target_count
        replicate_count = $Run.replicate_count
        prompt_version_created = [bool]$Run.prompt_version_id
        artifact_count = @($Run.artifact_objects.psobject.Properties).Count
        error_present = -not [string]::IsNullOrWhiteSpace($Run.error_message)
    }
}

function Get-SmokeTargetSelection {
    param([object[]]$Functions)

    $Preferred = @($Functions | Where-Object {
        $_.name -eq $TargetFunction -or $_.qualified_name -eq $TargetFunction
    })
    if ($Preferred.Count -ne 1) {
        $Candidates = ($Functions | Where-Object { $_.name -like "*$TargetFunction*" } |
            Select-Object -ExpandProperty qualified_name) -join ", "
        throw "Expected one target '$TargetFunction', found $($Preferred.Count). Candidates: $Candidates"
    }
    if (-not $FullPipeline) {
        return @($Preferred[0])
    }

    $OtherTargets = @($Functions | Where-Object {
        $_.id -ne $Preferred[0].id -and $_.status -eq "Valid"
    } | Sort-Object @{ Expression = "loc"; Descending = $false }, qualified_name)
    $Selection = @($Preferred[0]) + @($OtherTargets | Select-Object -First 2)
    if ($Selection.Count -lt 3) {
        throw "FullPipeline requires at least three valid functions in the uploaded project"
    }
    return $Selection
}

Write-Host "[1/9] Checking production API..."
$Health = Invoke-RestMethod "$ApiBase/health"
if ($Health.status -ne "ok") {
    throw "Production API health check failed"
}

Write-Host "[2/9] Creating signed upload..."
$Upload = Invoke-PromptOptJson -Uri "$ApiBase/uploads" -Method POST -Body @{
    filename = "isort-smoke-$Timestamp.zip"
    content_type = $ContentType
    size_bytes = $Archive.Length
}

Write-Host "[3/9] Uploading $([math]::Round($Archive.Length / 1KB, 1)) KiB to private storage..."
Invoke-WebRequest -Uri $Upload.upload_url -Method Put -InFile $ArchivePath -ContentType $ContentType -UseBasicParsing | Out-Null
Invoke-PromptOptJson -Uri "$ApiBase/uploads/$($Upload.id)/complete" -Method POST | Out-Null

Write-Host "[4/9] Creating project..."
$Project = Invoke-PromptOptJson -Uri "$ApiBase/projects" -Method POST -Body @{
    name = "isort production smoke $Timestamp"
    description = if ($FullPipeline) { "Full production pipeline smoke fixture" } else { "Baseline production smoke fixture" }
    upload_id = $Upload.id
    branch = "smoke"
    settings = @{ runtime = @{ source_directory = "isort" } }
}

Write-Host "[5/9] Starting analysis..."
$Project = Invoke-PromptOptJson -Uri "$ApiBase/projects/$($Project.id)/analyze" -Method POST
$AnalysisDeadline = (Get-Date).AddMinutes(5)
while ($Project.status -in @("uploaded", "analyzing")) {
    if ((Get-Date) -gt $AnalysisDeadline) {
        throw "Project analysis did not finish within 5 minutes"
    }
    Start-Sleep -Seconds 3
    $Project = Invoke-PromptOptJson -Uri "$ApiBase/projects/$($Project.id)"
    Write-Host "  analysis status=$($Project.status)"
}
if ($Project.status -notin @("ready", "warning")) {
    throw "Project analysis failed with status=$($Project.status)"
}

Write-Host "[6/9] Selecting target functions..."
$Functions = Invoke-PromptOptJson -Uri "$ApiBase/projects/$($Project.id)/functions"
$Targets = Get-SmokeTargetSelection -Functions @($Functions.items)
Write-Host "  selected $($Targets.Count) function(s): $(($Targets | Select-Object -ExpandProperty qualified_name) -join ', ')"

Write-Host "[7/9] Creating experiment and queueing baseline..."
$Experiment = Invoke-PromptOptJson -Uri "$ApiBase/experiments" -Method POST -Body @{
    project_id = $Project.id
    name = "isort $(if ($FullPipeline) { 'full pipeline' } else { 'baseline' }) smoke $Timestamp"
    target_function_ids = @($Targets | Select-Object -ExpandProperty id)
}
$BaselineRun = Invoke-PromptOptJson -Uri "$ApiBase/experiments/$($Experiment.id)/runs" -Method POST
Write-Host "  experiment_id=$($Experiment.id)"
Write-Host "  baseline_run_id=$($BaselineRun.id)"

Write-Host "[8/9] Polling Cloud Tasks -> Cloud Run Job -> GCS baseline result..."
$BaselineRun = Wait-PromptOptRun -Uri "$ApiBase/experiments/runs/$($BaselineRun.id)" `
    -ActiveStatuses @("baseline_queued", "baseline_running") `
    -TimeoutMinutes $BaselineTimeoutMinutes -Label "Baseline" -InitialRun $BaselineRun

$OptimizationRun = $null
$ComparisonRun = $null
$PromptVersion = $null
if ($BaselineRun.status -eq "baseline_succeeded" -and $FullPipeline) {
    Write-Host "[9/9] Queueing and polling optimization..."
    $OptimizationRun = Invoke-PromptOptJson -Uri "$ApiBase/experiments/$($Experiment.id)/optimize" -Method POST
    Write-Host "  optimization_run_id=$($OptimizationRun.id)"
    $OptimizationRun = Wait-PromptOptRun -Uri "$ApiBase/experiments/optimization-runs/$($OptimizationRun.id)" `
        -ActiveStatuses @("optimization_queued", "optimizing", "candidate_evaluating") `
        -TimeoutMinutes $OptimizationTimeoutMinutes -Label "Optimization" -InitialRun $OptimizationRun

    if ($OptimizationRun.status -eq "optimization_succeeded") {
        Write-Host "  queueing paired comparison..."
        $ComparisonRun = Invoke-PromptOptJson -Uri "$ApiBase/experiments/$($Experiment.id)/compare" -Method POST
        Write-Host "  comparison_run_id=$($ComparisonRun.id)"
        $ComparisonRun = Wait-PromptOptRun -Uri "$ApiBase/experiments/comparison-runs/$($ComparisonRun.id)" `
            -ActiveStatuses @("comparison_queued", "comparing") `
            -TimeoutMinutes $ComparisonTimeoutMinutes -Label "Comparison" -InitialRun $ComparisonRun

        if ($ComparisonRun.status -eq "in_review" -and $ComparisonRun.prompt_version_id) {
            Write-Host "  $ReviewDecision prompt version..."
            $PromptVersion = Invoke-PromptOptJson -Uri "$ApiBase/prompt-versions/$($ComparisonRun.prompt_version_id)/$ReviewDecision" `
                -Method POST -Body @{ comment = "Automated production smoke $Timestamp" }
        }
    }
}

New-Item -ItemType Directory -Force -Path $ResultDirectory | Out-Null
$Output = [ordered]@{
    schema_version = 1
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    api_base = $ApiBase
    mode = if ($FullPipeline) { "full_pipeline" } else { "baseline" }
    health = @{ status = $Health.status; service = $Health.service; env = $Health.env }
    selected_target_count = $Targets.Count
    selected_target_names = @($Targets | Select-Object -ExpandProperty qualified_name)
    experiment = @{ status = $Experiment.status; optimization_eligible = $Experiment.optimization_eligible }
    baseline = Get-SanitizedRun $BaselineRun
    optimization = Get-SanitizedRun $OptimizationRun
    comparison = Get-SanitizedRun $ComparisonRun
    review = if ($PromptVersion) {
        @{ status = $PromptVersion.status; reviewed_at = $PromptVersion.reviewed_at; reviewer_recorded = [bool]$PromptVersion.reviewer_id }
    } else { $null }
}
$Output | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ResultPath -Encoding UTF8

Write-Host ""
Write-Host "Smoke test summary: baseline=$($BaselineRun.status), optimization=$($OptimizationRun.status), comparison=$($ComparisonRun.status), review=$($PromptVersion.status)"
Write-Host "Sanitized result file: $ResultPath"
$Output | ConvertTo-Json -Depth 20

if ($BaselineRun.status -ne "baseline_succeeded") {
    exit 1
}
if ($FullPipeline -and $OptimizationRun.status -ne "optimization_succeeded") {
    exit 1
}
if ($FullPipeline -and $ComparisonRun.status -notin @("comparison_succeeded", "in_review")) {
    exit 1
}
if ($FullPipeline -and $ComparisonRun.status -eq "in_review" -and $PromptVersion.status -ne $ReviewDecision) {
    exit 1
}
if ($FullPipeline -and $ComparisonRun.status -eq "comparison_succeeded") {
    Write-Warning "Comparison completed but candidate was not promotion-eligible; review API was intentionally not called."
}
