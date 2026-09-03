param(
    [switch]$RebuildSandbox
)

$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
$frontendRoot = Join-Path $repositoryRoot "app\frontend"
$dataRoot = Join-Path $repositoryRoot "app\data\local-visual-test"
$pidFile = Join-Path $dataRoot "processes.json"
$sandboxImage = "promptopt-sandbox:py3.12"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing project Python environment: $python"
}
if (Test-Path -LiteralPath $pidFile) {
    throw "Local visual test may already be running. Run scripts\stop_local_visual_test.ps1 first."
}

$docker = Get-Command docker -ErrorAction Stop
$imageDigest = $null
if (-not $RebuildSandbox) {
    $imageInspect = & $docker.Source image inspect --format "{{.Id}}" $sandboxImage 2>$null
    if ($LASTEXITCODE -eq 0 -and $imageInspect) {
        $imageDigest = ($imageInspect | Select-Object -Last 1).Trim()
    }
}
if ($RebuildSandbox -or $imageDigest -notmatch '^sha256:[0-9a-f]{64}$') {
    Write-Output "Building $sandboxImage..."
    & $docker.Source build `
        --file (Join-Path $repositoryRoot "cloud\Dockerfile.sandbox") `
        --build-arg "PYTHON_VERSION=3.12" `
        --tag $sandboxImage `
        $repositoryRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Could not build sandbox image $sandboxImage"
    }
    $imageInspect = & $docker.Source image inspect --format "{{.Id}}" $sandboxImage
    if ($LASTEXITCODE -ne 0 -or -not $imageInspect) {
        throw "Sandbox image $sandboxImage is unavailable after build"
    }
    $imageDigest = ($imageInspect | Select-Object -Last 1).Trim()
}
if ($imageDigest -notmatch '^sha256:[0-9a-f]{64}$') {
    throw "Sandbox image $sandboxImage did not resolve to an immutable digest"
}
$contract = (& $docker.Source run --rm $imageDigest contract | ConvertFrom-Json)
if (
    $LASTEXITCODE -ne 0 -or
    $contract.python_minor -ne "3.12" -or
    @($contract.forbidden_modules_present).Count -ne 0
) {
    throw "Sandbox image contract failed"
}

New-Item -ItemType Directory -Path $dataRoot -Force | Out-Null
$fixture = Join-Path $repositoryRoot "app\data\coverage-conflict-project.zip"
& $python (Join-Path $repositoryRoot "scripts\create_local_docker_upload_fixture.py") --output $fixture
if ($LASTEXITCODE -ne 0) {
    throw "Could not create the local upload fixture"
}

if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot "node_modules"))) {
    Push-Location $frontendRoot
    try {
        npm.cmd ci
        if ($LASTEXITCODE -ne 0) {
            throw "npm ci failed"
        }
    }
    finally {
        Pop-Location
    }
}

$env:APP_ENV = "development"
$env:AUTH_MODE = "disabled"
$env:REPOSITORY_BACKEND = "memory"
$env:STORAGE_BACKEND = "local"
$env:ANALYSIS_DISPATCHER = "inline"
$env:RUNTIME_EXECUTION_BACKEND = "local_docker"
$env:LOCAL_SANDBOX_IMAGE = $sandboxImage
$env:LOCAL_RUNTIME_DIR = "./data/local-runtime"
$env:LOCAL_DOCKER_EXECUTABLE = $docker.Source
$env:PYTHONPATH = $repositoryRoot
$env:VITE_AUTH_MODE = "demo"
$env:VITE_DATA_MODE = "connected"
$env:VITE_API_BASE_URL = "/api/v1"
$env:VITE_API_PROXY_TARGET = "http://127.0.0.1:8000"

$backendOut = Join-Path $dataRoot "backend.stdout.log"
$backendErr = Join-Path $dataRoot "backend.stderr.log"
$frontendOut = Join-Path $dataRoot "frontend.stdout.log"
$frontendErr = Join-Path $dataRoot "frontend.stderr.log"

$backend = Start-Process `
    -FilePath $python `
    -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000") `
    -WorkingDirectory (Join-Path $repositoryRoot "app") `
    -WindowStyle Hidden `
    -RedirectStandardOutput $backendOut `
    -RedirectStandardError $backendErr `
    -PassThru

$frontend = $null
try {
    $backendReady = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 2
            if ($health.status -eq "ok") {
                $backendReady = $true
                break
            }
        }
        catch {
            if ($backend.HasExited) {
                throw "Backend exited early. Read $backendErr"
            }
        }
    }
    if (-not $backendReady) {
        throw "Backend did not become healthy. Read $backendErr"
    }

    $frontend = Start-Process `
        -FilePath "npm.cmd" `
        -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1") `
        -WorkingDirectory $frontendRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $frontendOut `
        -RedirectStandardError $frontendErr `
        -PassThru

    $frontendReady = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $response = Invoke-WebRequest "http://127.0.0.1:5173" -TimeoutSec 2 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                $frontendReady = $true
                break
            }
        }
        catch {
            if ($frontend.HasExited) {
                throw "Frontend exited early. Read $frontendErr"
            }
        }
    }
    if (-not $frontendReady) {
        throw "Frontend did not become ready. Read $frontendErr"
    }

    $records = @(
        [PSCustomObject]@{
            name = "backend"
            id = $backend.Id
            started_at = $backend.StartTime.ToUniversalTime().ToString("O")
        },
        [PSCustomObject]@{
            name = "frontend"
            id = $frontend.Id
            started_at = $frontend.StartTime.ToUniversalTime().ToString("O")
        }
    )
    $records | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8
}
catch {
    if ($null -ne $frontend -and -not $frontend.HasExited) {
        Stop-Process -Id $frontend.Id -Force
    }
    if (-not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force
    }
    throw
}

Write-Output "PromptOpt visual test is running: http://127.0.0.1:5173"
Write-Output "Upload fixture: $fixture"
Write-Output "Backend logs: $backendOut and $backendErr"
Write-Output "Frontend logs: $frontendOut and $frontendErr"
Write-Output "Stop with: .\scripts\stop_local_visual_test.ps1"
