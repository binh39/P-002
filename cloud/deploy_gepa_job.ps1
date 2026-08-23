# Deploy the GEPA/CoverUp optimization pipeline to Cloud Run Jobs.
#
# Usage:
#   .\cloud\deploy_gepa_job.ps1                              # build image + create/update job
#   .\cloud\deploy_gepa_job.ps1 -SkipBuild -Execute          # reuse image, deploy + start job
#   .\cloud\deploy_gepa_job.ps1 -MetricCalls 20              # small test budget
#
# After deploy, run:
#   .\cloud\run_gepa_job.ps1                                 # start, wait, download results
#
# See cloud\README.md for details.

[CmdletBinding()]
param(
    [string]$ProjectId = "project-7df9f963-9fe0-4b76-b3d",
    [string]$VertexProjectId = "",
    [string]$Region = "asia-southeast1",
    [string]$Bucket = "p002-gepa-artifacts",
    [string]$Image = "",
    [string]$JobName = "p002-gepa",
    [string]$ServiceAccountName = "p002-gepa-sa",
    [string]$ArtifactsName = "prompt_optimization_v3",
    [int]$MaxConcurrency = 10,
    [int]$RepeatTests = 5,
    [int]$MetricCalls = 450,
    [int]$Cpu = 8,
    [string]$Memory = "8Gi",
    [int]$TaskTimeoutSeconds = 86400,
    [string]$DatasetInImage = "/app/inputs/data_symbols.jsonl",
    [string]$PromptInImage = "/app/inputs/gpt_v2_baseline.json",
    [switch]$SkipBuild,
    [switch]$Execute
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Get-EnvValue {
    param([string]$Name)
    $envFile = Join-Path $root ".env"
    if (Test-Path -LiteralPath $envFile) {
        $line = Get-Content -LiteralPath $envFile |
            Where-Object { $_ -match "^$Name\s*=" } |
            Select-Object -First 1
        if ($line) {
            return ($line -replace "^$Name\s*=", "").Trim().Trim('"')
        }
    }
    return $null
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
# Resolve the model project independently from the deployment project.
# ---------------------------------------------------------------------------
if (-not $VertexProjectId) {
    $VertexProjectId = Get-EnvValue "VERTEXAI_PROJECT"
}
if (-not $VertexProjectId -or $VertexProjectId -eq "your-google-cloud-project") {
    throw "VertexProjectId not set. Pass -VertexProjectId or set VERTEXAI_PROJECT in .env"
}
if (-not $Image) {
    $Image = "asia-southeast1-docker.pkg.dev/$ProjectId/promptopt/gepa:dev"
}

Write-Host "==> Deploy project : $ProjectId"
Write-Host "==> Model project  : $VertexProjectId"
Write-Host "==> Region         : $Region"
Write-Host "==> Bucket         : gs://$Bucket (artifacts root)"

# ---------------------------------------------------------------------------
# Sync dataset + prompt into cloud/inputs (they must end up inside the image)
# ---------------------------------------------------------------------------
$inputsDir = Join-Path $PSScriptRoot "inputs"
New-Item -ItemType Directory -Force -Path $inputsDir | Out-Null
$inputPairs = @(
    @{
        Source = Join-Path $root "eval\prompt_optimization\datasets\data_symbols.jsonl"
        Dest   = Join-Path $inputsDir "data_symbols.jsonl"
    },
    @{
        Source = Join-Path $root "eval\prompt_optimization\prompts\gpt_v2_baseline.json"
        Dest   = Join-Path $inputsDir "gpt_v2_baseline.json"
    }
)
foreach ($pair in $inputPairs) {
    if (-not (Test-Path -LiteralPath $pair.Source)) {
        throw "Missing input: $($pair.Source). The dataset/prompt must exist before deploy."
    }
    Copy-Item -LiteralPath $pair.Source -Destination $pair.Dest -Force
}
Write-Host "==> Inputs synced to cloud/inputs"

# ---------------------------------------------------------------------------
# Enable APIs
# ---------------------------------------------------------------------------
Write-Host "==> Enabling required APIs..."
Invoke-Gcloud services enable run.googleapis.com cloudbuild.googleapis.com storage.googleapis.com --project $ProjectId
Invoke-Gcloud services enable aiplatform.googleapis.com --project $VertexProjectId

# ---------------------------------------------------------------------------
# Artifacts bucket
# ---------------------------------------------------------------------------
if (Test-Gcloud storage buckets describe "gs://$Bucket" --project $ProjectId --format="value(name)") {
    Write-Host "==> Bucket exists: gs://$Bucket"
} else {
    Write-Host "==> Creating bucket gs://$Bucket ..."
    Invoke-Gcloud storage buckets create "gs://$Bucket" --location $Region --project $ProjectId
}

# ---------------------------------------------------------------------------
# Service account (used for Vertex AI + GCS from inside the job)
# ---------------------------------------------------------------------------
$saEmail = "$ServiceAccountName@$ProjectId.iam.gserviceaccount.com"
if (Test-Gcloud iam service-accounts describe $saEmail --project $ProjectId) {
    Write-Host "==> Service account exists: $saEmail"
} else {
    Write-Host "==> Creating service account $saEmail ..."
    Invoke-Gcloud iam service-accounts create $ServiceAccountName --display-name "GEPA Cloud Run job SA" --project $ProjectId
}

Write-Host "==> Granting Vertex AI + GCS permissions (idempotent)..."
Invoke-Gcloud projects add-iam-policy-binding $VertexProjectId `
    --member "serviceAccount:$saEmail" --role roles/aiplatform.user --quiet
Invoke-Gcloud projects add-iam-policy-binding $VertexProjectId `
    --member "serviceAccount:$saEmail" --role roles/serviceusage.serviceUsageConsumer --quiet
Invoke-Gcloud storage buckets add-iam-policy-binding "gs://$Bucket" `
    --member "serviceAccount:$saEmail" --role roles/storage.objectUser --quiet

# ---------------------------------------------------------------------------
# Build image
# ---------------------------------------------------------------------------
if ($SkipBuild) {
    Write-Host "==> Skipping build (-SkipBuild); using $Image"
} else {
    Write-Host "==> Building image $Image (can take several minutes)..."
    Invoke-Gcloud builds submit --config cloud/cloudbuild.web.yaml --substitutions="_IMAGE=$Image" --project $ProjectId .
}

# ---------------------------------------------------------------------------
# Environment variables for the job (model config read from .env)
# ---------------------------------------------------------------------------
$coverupModel = Get-EnvValue "COVERUP_MODEL"
if (-not $coverupModel) { $coverupModel = "vertex_ai/gemini-3.5-flash-lite" }
$optimizeModel = Get-EnvValue "OPTIMIZE_MODEL"
if (-not $optimizeModel) { $optimizeModel = "vertex_ai/gemini-3.1-pro-preview" }
$vertexLocation = Get-EnvValue "VERTEXAI_LOCATION"
if (-not $vertexLocation) { $vertexLocation = "global" }

$envPairs = @(
    "COVERUP_MODEL=$coverupModel",
    "OPTIMIZE_MODEL=$optimizeModel",
    "VERTEXAI_PROJECT=$VertexProjectId",
    "VERTEXAI_LOCATION=$vertexLocation"
)
foreach ($key in @("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY")) {
    $value = Get-EnvValue $key
    if ($value) { $envPairs += "$key=$value" }
}
$envVars = ($envPairs -join ",")

# ---------------------------------------------------------------------------
# CLI arguments: run via cloud/run_job.py with LOCAL artifacts, then upload to GCS
# ---------------------------------------------------------------------------
$cliArgs = @(
    "-m", "cloud.run_job",
    "--bucket", $Bucket,
    "--artifacts-name", $ArtifactsName,
    "--",
    "--max-concurrency", "$MaxConcurrency",
    "--repeat-tests", "$RepeatTests",
    "optimize",
    "--dataset", $DatasetInImage,
    "--prompt", $PromptInImage,
    "--max-metric-calls", "$MetricCalls"
) -join ","

$jobFlags = @(
    "--image", $Image,
    "--command", "python",
    "--args=$cliArgs",
    "--cpu", "$Cpu",
    "--memory", $Memory,
    "--task-timeout", "$TaskTimeoutSeconds",
    "--max-retries", "0",
    "--service-account", $saEmail,
    "--set-env-vars", $envVars,
    "--region", $Region,
    "--project", $ProjectId
)

if (Test-Gcloud run jobs describe $JobName --region $Region --project $ProjectId --format="value(metadata.name)") {
    Write-Host "==> Updating job $JobName ..."
    Invoke-Gcloud run jobs update $JobName @jobFlags
} else {
    Write-Host "==> Creating job $JobName ..."
    Invoke-Gcloud run jobs create $JobName @jobFlags
}

Write-Host ""
Write-Host "Job ready: $JobName ($Region)"
Write-Host "  - command : python -m cloud.run_job --bucket $Bucket --artifacts-name $ArtifactsName -- --max-concurrency $MaxConcurrency optimize --dataset $DatasetInImage --prompt $PromptInImage --max-metric-calls $MetricCalls"
Write-Host "  - cpu/mem : $Cpu vCPU / $Memory"
Write-Host "  - timeout : $TaskTimeoutSeconds s (max 604800 = 7 days)"
Write-Host "  - artifacts run on local disk, then uploaded to gs://$Bucket/$ArtifactsName/"

if ($Execute) {
    Write-Host ""
    Write-Host "==> Starting job execution..."
    & (Join-Path $PSScriptRoot "run_gepa_job.ps1") `
        -JobName $JobName -Region $Region -ProjectId $ProjectId `
        -Bucket $Bucket -ArtifactsName $ArtifactsName -NoWait
} else {
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1) Start + wait + download results:  .\cloud\run_gepa_job.ps1"
    Write-Host "  2) Or run with a small budget first:  .\cloud\deploy_gepa_job.ps1 -MetricCalls 20 -Execute"
}
