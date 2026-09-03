$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pidFile = Join-Path $repositoryRoot "app\data\local-visual-test\processes.json"

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Output "No local visual test process file was found."
    exit 0
}

$records = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
foreach ($record in $records) {
    $process = Get-Process -Id ([int]$record.id) -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        continue
    }
    $expected = [DateTime]::Parse($record.started_at).ToUniversalTime()
    $actual = $process.StartTime.ToUniversalTime()
    if ([Math]::Abs(($actual - $expected).TotalSeconds) -gt 2) {
        Write-Warning "Refusing to stop reused PID $($record.id) for $($record.name)."
        continue
    }
    Stop-Process -Id $process.Id -Force
    Write-Output "Stopped $($record.name) process $($process.Id)."
}

Remove-Item -LiteralPath $pidFile
