$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$pythonFolder = Join-Path $root "PYTHON_FOLDER"
$pidFile = Join-Path $root ".flask.pid"
$stdoutLog = Join-Path $root ".flask.stdout.log"
$stderrLog = Join-Path $root ".flask.stderr.log"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Project Python environment not found. Create .venv and install PYTHON_FOLDER\requirements.txt first."
}

if (Test-Path -LiteralPath $pidFile) {
    $savedId = 0
    [void][int]::TryParse((Get-Content -LiteralPath $pidFile -Raw), [ref]$savedId)
    $savedProcess = Get-Process -Id $savedId -ErrorAction SilentlyContinue
    $resolvedPython = (Get-Item -LiteralPath $python).Target
    if (-not $resolvedPython) { $resolvedPython = $python }
    if ($savedProcess -and ($savedProcess.Path.Equals($python, [System.StringComparison]::OrdinalIgnoreCase) -or $savedProcess.Path.Equals($resolvedPython, [System.StringComparison]::OrdinalIgnoreCase) -or $savedProcess.ProcessName -eq "python")) {
        Write-Host "Placement server is already running at http://127.0.0.1:5000/ (PID $savedId)."
        exit 0
    }
    Remove-Item -LiteralPath $pidFile -Force
}

$listener = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $listenProc = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
    if ($listenProc -and $listenProc.ProcessName -eq "python") {
        Set-Content -LiteralPath $pidFile -Value $listener.OwningProcess -NoNewline
        Write-Host "Placement server is already running at http://127.0.0.1:5000/ (PID $($listener.OwningProcess))."
        exit 0
    }
    throw "Port 5000 is already in use by PID $($listener.OwningProcess). Close that server before starting this project."
}

$process = Start-Process -FilePath $python -ArgumentList "main.py" -WorkingDirectory $pythonFolder -WindowStyle Hidden -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru
Set-Content -LiteralPath $pidFile -Value $process.Id -NoNewline
Start-Sleep -Seconds 2
$process.Refresh()
if ($process.HasExited) {
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    $details = Get-Content -LiteralPath $stderrLog -Raw -ErrorAction SilentlyContinue
    throw "Flask exited during startup. $details"
}

Write-Host "Placement server is running at http://127.0.0.1:5000/ (PID $($process.Id))."
Write-Host "It will keep running after you close VS Code. Use stop.ps1 to stop it."
