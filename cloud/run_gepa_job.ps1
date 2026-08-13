# Run the deployed GEPA job on Cloud Run and fetch eval results once it finishes.
#
# Usage:
#   .\cloud\run_gepa_job.ps1                  # start, wait for completion, download results
#   .\cloud\run_gepa_job.ps1 -NoWait          # start and return immediately
#   .\cloud\run_gepa_job.ps1 -SkipDownload    # wait but skip the download
#   .\cloud\run_gepa_job.ps1 -Cleanup         # after download: delete GCS artifacts + job + image
#   .\cloud\run_gepa_job.ps1 -ExecutionName <NAME>   # attach to an existing execution (no new charge)
#   .\cloud\run_gepa_job.ps1 -NewExecution    # start a new execution even if one is already running
#
# Results land in eval\prompt_optimization_v3_cloud by default.

[CmdletBinding()]
param(
    [string]$JobName = "p002-gepa",
    [string]$Region = "asia-southeast1",
    [string]$ProjectId = "project-7df9f963-9fe0-4b76-b3d",
    [string]$Bucket = "p002-gepa-artifacts",
    [string]$ArtifactsName = "prompt_optimization_v3",
    [string]$DownloadTo = "eval/prompt_optimization_v3_cloud",
    [string]$Image = "",
    [string]$ExecutionName = "",
    [switch]$NoWait,
    [switch]$NewExecution,
    [switch]$SkipDownload,
    [switch]$Cleanup
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

if (-not $Image) {
    $Image = "gcr.io/$ProjectId/p002-gepa"
}
if ($Cleanup -and $NoWait) {
    throw "-Cleanup cannot be combined with -NoWait (the execution may still be running)."
}
if ($Cleanup -and $SkipDownload) {
    throw "-Cleanup cannot be combined with -SkipDownload (results would be deleted without a local copy)."
}

function Invoke-Gcloud {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GcloudArgs)
    & gcloud @GcloudArgs
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud failed (exit $LASTEXITCODE): gcloud $($GcloudArgs -join ' ')"
    }
}

function Test-Gcloud {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GcloudArgs)
    $savedErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        & gcloud @GcloudArgs 2>&1 | Out-Null
    } catch {
        # Never expected, but never let a probe kill the script
    } finally {
        $ErrorActionPreference = $savedErrorActionPreference
    }
    return ($LASTEXITCODE -eq 0)
}

# ---------------------------------------------------------------------------
# Resolve which execution to track: attach to an existing one or start a new one
# ---------------------------------------------------------------------------
if ($ExecutionName) {
    $executionName = $ExecutionName.Trim()
    Write-Host "==> Attaching to execution: $executionName"
    if (-not (Test-Gcloud run jobs executions describe $executionName --region $Region --project $ProjectId --format="value(metadata.name)")) {
        throw "Execution '$executionName' not found in $Region."
    }
} else {
    if (-not (Test-Gcloud run jobs describe $JobName --region $Region --project $ProjectId --format="value(metadata.name)")) {
        throw "Job '$JobName' not found in $Region. Deploy it first with .\cloud\deploy_gepa_job.ps1"
    }
    # Safety guard: refuse to start a second execution while one is still running.
    $activeJson = (& gcloud run jobs executions list --job $JobName --region $Region --project $ProjectId --format="json" 2>$null) -join "`n"
    if ($activeJson) {
        try {
            $active = @(($activeJson | ConvertFrom-Json) | Where-Object {
                $completed = @($_.status.conditions | Where-Object { $_.type -eq "Completed" })
                $completed.Count -eq 0
            })
            if ($active.Count -gt 0 -and -not $NewExecution) {
                $activeNames = ($active | ForEach-Object { $_.metadata.name }) -join ", "
                throw ("An execution is already running: $activeNames. " +
                       "Attach with -ExecutionName <name>, or force a new one with -NewExecution.")
            }
            if ($active.Count -gt 0) {
                Write-Host "==> NOTE: $($active.Count) execution(s) still running; -NewExecution given, starting another one anyway."
            }
        } catch {
            if ($_ -is [System.Management.Automation.RuntimeException]) { throw }
        }
    }
    Write-Host "==> Executing job $JobName ..."
    $executionName = & gcloud run jobs execute $JobName --region $Region --project $ProjectId --format="value(metadata.name)"
    if ($LASTEXITCODE -ne 0 -or -not $executionName) {
        throw "Failed to start job execution."
    }
    $executionName = $executionName.Trim()
    Write-Host "==> Execution started: $executionName"
}

if ($NoWait) {
    Write-Host ""
    Write-Host "Monitor with:"
    Write-Host "  gcloud run jobs executions describe $executionName --region $Region --project $ProjectId"
    Write-Host "  gcloud logging read ""resource.type=cloud_run_job AND resource.labels.job_name=$JobName"" --limit 50 --project $ProjectId"
    Write-Host ""
    Write-Host "To wait + download results later (safe, no new execution):"
    Write-Host "  .\cloud\run_gepa_job.ps1 -ExecutionName $executionName"
    exit 0
}

# ---------------------------------------------------------------------------
# Wait for completion
# ---------------------------------------------------------------------------
Write-Host "==> Waiting for completion (polling every 30s)..."
$waitedSeconds = 0
$finalCondition = $null
while ($waitedSeconds -lt 604800) {
    Start-Sleep -Seconds 30
    $waitedSeconds += 30

    $json = (& gcloud run jobs executions describe $executionName --region $Region --project $ProjectId --format="json" 2>$null) -join "`n"
    if ($json) {
        try {
            $execution = $json | ConvertFrom-Json
            $condition = $execution.status.conditions |
                Where-Object { $_.type -eq "Completed" } |
                Select-Object -First 1
            if ($condition) {
                $finalCondition = $condition
                break
            }
        } catch {
            # transient parse failure -> keep polling
        }
    }

    if ($waitedSeconds % 300 -eq 0) {
        Write-Host "  ... still running ($([int]($waitedSeconds / 60)) min)"
    }
}

if (-not $finalCondition) {
    throw "Timed out while waiting for execution. Check logs manually."
}

$succeeded = ($finalCondition.status -eq "True")
Write-Host "==> Completion: $($finalCondition.status) ($($finalCondition.reason))"

Write-Host "--- last log lines (job-wide; may include earlier executions) ---"
& gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=$JobName" `
    --limit 40 --order=desc --project $ProjectId --format="value(textPayload)" 2>$null |
    Select-Object -First 40

if (-not $succeeded) {
    Write-Host ""
    Write-Host "Job FAILED. Full logs:"
    Write-Host "  gcloud logging read ""resource.type=cloud_run_job AND resource.labels.job_name=$JobName"" --limit 500 --project $ProjectId"
    exit 1
}

# ---------------------------------------------------------------------------
# Download results
# ---------------------------------------------------------------------------
if ($SkipDownload) {
    Write-Host ""
    Write-Host "==> Skipping download (-SkipDownload)."
    Write-Host "==> Results remain at gs://$Bucket/$ArtifactsName/"
    exit 0
}

if (Test-Path -LiteralPath $DownloadTo) {
    throw "Download target already exists: $DownloadTo. Use -DownloadTo <new path> or remove the folder first."
}

# gcloud storage cp requires the destination directory to exist, and nests the
# source directory inside it. Create the dir, copy, then flatten the nesting.
New-Item -ItemType Directory -Force -Path $DownloadTo | Out-Null
Write-Host "==> Downloading gs://$Bucket/$ArtifactsName to $DownloadTo ..."
Invoke-Gcloud storage cp -r "gs://$Bucket/$ArtifactsName" $DownloadTo
$nested = Join-Path $DownloadTo ([IO.Path]::GetFileName($ArtifactsName.TrimEnd('/')))
if ((Test-Path -LiteralPath $nested) -and -not (Test-Path -LiteralPath (Join-Path $DownloadTo "optimized_program.json"))) {
    Get-ChildItem -LiteralPath $nested -Force | Move-Item -Destination $DownloadTo -Force
    Remove-Item -LiteralPath $nested -Force
}
Write-Host "==> Downloaded."

$keyFiles = @(
    "optimized_program.json",
    "prompts/gepa_optimized.json",
    "prompts/gepa_proposed.json",
    "final_validation.json",
    "gepa_direct_logs"
)
Write-Host "Key results:"
foreach ($relative in $keyFiles) {
    $candidates = @(
        (Join-Path $DownloadTo $relative),
        (Join-Path (Join-Path $DownloadTo $ArtifactsName) $relative)
    )
    foreach ($path in $candidates) {
        if (Test-Path -LiteralPath $path) {
            Write-Host "  - $path"
            break
        }
    }
}

# ---------------------------------------------------------------------------
# Optional cleanup (opt-in): stop all ongoing cloud costs for this run
# ---------------------------------------------------------------------------
if ($Cleanup) {
    Write-Host ""
    Write-Host "==> Cleaning up cloud resources (-Cleanup)..."
    Write-Host "    Deleting gs://$Bucket/$ArtifactsName ..."
    Invoke-Gcloud storage rm -r "gs://$Bucket/$ArtifactsName"
    Write-Host "    Deleting Cloud Run job $JobName ..."
    Invoke-Gcloud run jobs delete $JobName --region $Region --project $ProjectId --quiet
    Write-Host "    Deleting container image $Image ..."
    Invoke-Gcloud container images delete $Image --quiet --force-delete-tags
    Write-Host "==> Cleanup done. No job, image or GCS artifacts remain."
    Write-Host "    Next run requires redeploying first: .\cloud\deploy_gepa_job.ps1"
}
