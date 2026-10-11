$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$pidFile = Join-Path $root ".flask.pid"

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Host "No project server PID file found."
    exit 0
}

$serverId = 0
[void][int]::TryParse((Get-Content -LiteralPath $pidFile -Raw), [ref]$serverId)
$server = Get-Process -Id $serverId -ErrorAction SilentlyContinue
if ($server -and $server.Path -and $server.Path.Equals($python, [System.StringComparison]::OrdinalIgnoreCase)) {
    Stop-Process -Id $serverId
    Write-Host "Stopped the placement server (PID $serverId)."
} else {
    Write-Host "The saved PID is no longer the project server. Removed the stale PID file."
}

Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
