$ErrorActionPreference = 'Stop'
$buildingRoot = Split-Path -Parent $PSScriptRoot
$buildingPython = Join-Path $buildingRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $buildingPython)) { $buildingPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' }
if (-not (Test-Path -LiteralPath $buildingPython)) { $buildingPython = (Get-Command python -ErrorAction Stop).Source }
try {
    $buildingHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -TimeoutSec 2
    if ($buildingHealth.status -eq 'ok') { Write-Output 'BuildingWorld is already running: http://127.0.0.1:8765'; exit 0 }
} catch {}
$buildingOutput = Join-Path $buildingRoot 'work/runtime/web_server'
New-Item -ItemType Directory -Force -Path $buildingOutput | Out-Null
$buildingServer = Join-Path $PSScriptRoot 'server.py'
$buildingProcess = Start-Process -FilePath $buildingPython -ArgumentList @('-X','utf8',('"' + $buildingServer + '"'),'--port','8765') -WorkingDirectory $buildingRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $buildingOutput 'stdout.log') -RedirectStandardError (Join-Path $buildingOutput 'stderr.log') -PassThru
$buildingProcess.Id | Set-Content -LiteralPath (Join-Path $buildingOutput 'pid.txt')
Write-Output 'BuildingWorld starting: http://127.0.0.1:8765'
