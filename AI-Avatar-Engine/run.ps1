#requires -Version 5
<#
  One-command launcher for the AI-Avatar-Engine dev stack.
  Starts BOTH servers in this one window and stops BOTH on Ctrl+C:
    - AI photo analyzer  ->  http://127.0.0.1:8100   (powers the Photos tab)
    - Avatar Sandbox     ->  http://localhost:5173   (the web UI, auto-opened)

  Usage (from anywhere -- paths resolve relative to this file):
    powershell -ExecutionPolicy Bypass -File AI-Avatar-Engine\run.ps1
  or just double-click AI-Avatar-Engine\run.cmd
#>
$ErrorActionPreference = 'Stop'
$here   = $PSScriptRoot
$py     = Join-Path $here 'ai\.venv\Scripts\python.exe'
$server = Join-Path $here 'ai\photo_analyzer\server.py'
$web    = Join-Path $here 'frontend\threejs-viewer'

if (-not (Test-Path $py)) {
    throw "Python venv not found at $py -- see ai/photo_analyzer/README.md for setup."
}
if (-not (Test-Path (Join-Path $web 'node_modules'))) {
    Write-Host '[setup] installing frontend dependencies (first run only)...' -ForegroundColor Yellow
    npm install --prefix $web
}

Write-Host '[1/2] AI analyzer    -> http://127.0.0.1:8100' -ForegroundColor Cyan
$backend = Start-Process -FilePath $py -ArgumentList $server -PassThru -NoNewWindow

try {
    Start-Sleep -Seconds 3
    Write-Host '[2/2] Avatar Sandbox -> http://localhost:5173   (Ctrl+C stops BOTH)' -ForegroundColor Cyan
    Start-Process 'http://localhost:5173'
    Push-Location $web
    npm run dev
} finally {
    Pop-Location -ErrorAction SilentlyContinue
    if ($backend -and -not $backend.HasExited) {
        Write-Host "`n[stop] shutting down AI analyzer (pid $($backend.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    }
}
