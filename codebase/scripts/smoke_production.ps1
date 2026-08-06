param(
    [string]$ApiBase = "https://vinaip002.web.app/api/v1",
    [string]$ArchivePath = (Join-Path $PSScriptRoot "..\fixtures\isort-smoke.zip"),
    [string]$TargetFunction = "_infer_line_separator",
    [int]$PollSeconds = 10,
    [int]$TimeoutMinutes = 25
)

$ErrorActionPreference = "Stop"
$ArchivePath = [System.IO.Path]::GetFullPath($ArchivePath)
if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf)) {
    throw "Smoke archive was not found: $ArchivePath"
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
$ResultPath = Join-Path $PSScriptRoot "production-smoke-result-$Timestamp.json"

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

Write-Host "[1/8] Checking production API..."
$Health = Invoke-RestMethod "$ApiBase/health"
if ($Health.status -ne "ok") {
    throw "Production API health check failed"
}

Write-Host "[2/8] Creating signed upload..."
$Upload = Invoke-PromptOptJson -Uri "$ApiBase/uploads" -Method POST -Body @{
    filename = "isort-smoke-$Timestamp.zip"
    content_type = $ContentType
    size_bytes = $Archive.Length
}

Write-Host "[3/8] Uploading $([math]::Round($Archive.Length / 1KB, 1)) KiB to private storage..."
Invoke-WebRequest -Uri $Upload.upload_url -Method Put -InFile $ArchivePath -ContentType $ContentType -UseBasicParsing | Out-Null
Invoke-PromptOptJson -Uri "$ApiBase/uploads/$($Upload.id)/complete" -Method POST | Out-Null

Write-Host "[4/8] Creating project..."
$Project = Invoke-PromptOptJson -Uri "$ApiBase/projects" -Method POST -Body @{
    name = "isort production smoke $Timestamp"
    description = "Minimal production Cloud Run Job smoke fixture"
    upload_id = $Upload.id
    branch = "smoke"
    settings = @{
        runtime = @{
            source_directory = "isort"
        }
    }
}

Write-Host "[5/8] Starting analysis for project $($Project.id)..."
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

Write-Host "[6/8] Selecting target function '$TargetFunction'..."
$Functions = Invoke-PromptOptJson -Uri "$ApiBase/projects/$($Project.id)/functions"
$Matches = @($Functions.items | Where-Object {
    $_.name -eq $TargetFunction -or $_.qualified_name -eq $TargetFunction
})
if ($Matches.Count -ne 1) {
    $Candidates = ($Functions.items | Where-Object { $_.name -like "*$TargetFunction*" } | Select-Object -ExpandProperty qualified_name) -join ", "
    throw "Expected one target '$TargetFunction', found $($Matches.Count). Candidates: $Candidates"
}
$Target = $Matches[0]
Write-Host "  selected $($Target.qualified_name) in $($Target.file)"

Write-Host "[7/8] Creating experiment and queueing baseline..."
$Experiment = Invoke-PromptOptJson -Uri "$ApiBase/experiments" -Method POST -Body @{
    project_id = $Project.id
    name = "isort baseline smoke $Timestamp"
    target_function_ids = @($Target.id)
}
$Run = Invoke-PromptOptJson -Uri "$ApiBase/experiments/$($Experiment.id)/runs" -Method POST
Write-Host "  experiment_id=$($Experiment.id)"
Write-Host "  run_id=$($Run.id)"

Write-Host "[8/8] Polling Cloud Tasks -> Cloud Run Job -> GCS result..."
$RunDeadline = (Get-Date).AddMinutes($TimeoutMinutes)
while ($Run.status -in @("baseline_queued", "baseline_running")) {
    if ((Get-Date) -gt $RunDeadline) {
        throw "Baseline did not finish within $TimeoutMinutes minutes; run_id=$($Run.id)"
    }
    Start-Sleep -Seconds $PollSeconds
    $Run = Invoke-PromptOptJson -Uri "$ApiBase/experiments/runs/$($Run.id)"
    Write-Host "  $(Get-Date -Format T) status=$($Run.status)"
}

$Output = [ordered]@{
    api_base = $ApiBase
    project_id = $Project.id
    experiment_id = $Experiment.id
    run_id = $Run.id
    target = $Target
    run = $Run
}
$Output | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $ResultPath -Encoding UTF8

Write-Host ""
Write-Host "Smoke test finished with status=$($Run.status)"
Write-Host "Result file: $ResultPath"
$Output | ConvertTo-Json -Depth 30

if ($Run.status -ne "baseline_succeeded") {
    exit 1
}
